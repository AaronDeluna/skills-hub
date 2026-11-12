#!/usr/bin/env python3
"""Проверка тест-кейса на пригодность для автоматизации (скилл autotest-plan). Запуск из корня проекта:

  python3 <скилл>/scripts/tc_check.py <ключ ТК>

Читает .gigacode/data/autotest/<ключ>/TC.md, пишет TC-CHECK.md рядом и печатает сводку:
СТАТУС (PASS / WARNING / FAIL), BLOCKING, ОЦЕНКИ, строки НАХОДКА. Пять оценок по 100 баллов,
вычеты - по таблице правил references/tc-rules.md (правила TC-1..TC-12 там же, с примерами).
Python 3.8+, только стандартная библиотека. Код выхода: 0 - PASS или WARNING, 1 - FAIL, 2 - нет TC.md.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tc_common as tcc  # noqa: E402

REQUIRED = ["Название", "Ключ", "Цель"]
RECOMMENDED = ["КЭ", "Приоритет", "Требования к тестовым данным"]
VAGUE = ["валидные данные", "валидный", "корректный формат", "корректное значение", "корректные данные", "правильный",
         "существующий пользователь", "тестовые данные", "все поля", "любой", "любое", "какой-нибудь", "и т.д", "и так далее",
         "соответствующ", "нужные данные", "необходимые данные"]
SUBJECTIVE = ["отображается верно", "отображается корректно", "работает", "всё хорошо", "все хорошо", "удобно", "открылась",
              "данные сохранились", "интерфейс изменился", "успешн", "без ошибок", "корректно"]
OBJECTIVE_ANCHOR = re.compile(r"\b[1-5]\d\d\b|\"[^\"]+\"|«[^»]+»|=|:\s*\S|\b(true|false|null)\b|statuscode|status|поле|колон|таблиц|запис|сообщени|текст", re.I)
RANDOM = ["random", "случайн", "рандом"]
NOW = re.compile(r"\bnow\b|текущ|сегодня|сейчас", re.I)
ASYNC = ["асинхрон", "через некоторое время", "подожд", "дождаться", "после обработки"]
WAIT_ANCHOR = re.compile(r"\d+\s*(с|сек|секунд|мин|ms|мс|s)\b|timeout|таймаут", re.I)
API = re.compile(r"\b(POST|GET|PUT|PATCH|DELETE)\b|запрос", re.I)
ADDRESS = re.compile(r"(https?://|/[\w\-{}]+/|\b[a-z]+[-_][a-z]+\b\s*(топик|topic)|топик\s+\S+|таблиц\w*\s+\S+|select|insert|update)", re.I)
HARDCODE = re.compile(r"(логин|login|пароль|password)\s*[:=]\s*\S+", re.I)
PREV_REF = re.compile(r"(?:из|на|в)\s+шаг[аеу]?\s*(?:№\s*)?(\d+)", re.I)
CREATED_BEFORE = re.compile(r"созданн\w*\s+(?:ранее|на прошлом|на предыдущем)", re.I)


def main(args):
    if not args:
        print("Использование: tc_check.py <ключ ТК>")
        return 2
    path = tcc.DATA / args[0] / "TC.md"
    if not path.is_file():
        print("НЕТ TC.md: " + str(path) + " - сначала tc_convert.py")
        return 2
    tc = tcc.parse_tc(path)
    scores = {"determinism": 100, "independence": 100, "reproducibility": 100, "objective_verifiability": 100, "parametrizability": 100}
    findings = []  # (правило, где, что, вычет, критерий, critical)

    def add(rule, where, what, minus=0, criterion=None, critical=False):
        findings.append((rule, where, what, critical))
        if criterion:
            scores[criterion] = max(0, scores[criterion] - minus)

    if not tc["steps"]:
        add("TC-0", "ТК", "шагов нет или таблица шагов не читается", critical=True)
    for name in REQUIRED:
        if tc["fields"].get(name, "-") in ("", "-"):
            add("TC-1", "шапка", "нет обязательного поля «" + name + "»", critical=True)
    for name in RECOMMENDED:
        if tc["fields"].get(name, "-") in ("", "-"):
            add("TC-1", "шапка", "нет рекомендуемого поля «" + name + "»")
    title = tc["title"]
    if len(re.findall(r"[А-Яа-яA-Za-z]{3,}", title)) < 3:
        add("TC-2", "название", "название из 1-2 слов не говорит, что проверяется: «" + title + "»")
    if len({v for v in tcc.actions_in(title) if v.startswith("OPERATION")}) > 1 and re.search(r"\sи\s", title):
        add("TC-3", "название", "в названии два действия через «и» - возможно, два теста в одном (решает план)")
    pre = tc["fields"].get("Предусловия", "")
    seen_numbers = set()
    for s in tc["steps"]:
        where = "шаг " + str(s["n"])
        full = " ".join([s["action"], s["data"], s["expected"]])
        low = tcc.lower(full)
        if len({v for v in tcc.actions_in(s["action"]) if not v.startswith("ASSERT")}) > 1:
            add("TC-4", where, "в действии несколько действий - план разобьёт шаг на подшаги", 30, "reproducibility")
        for word in VAGUE:
            if word in low:
                add("TC-5", where, "размытое значение «" + word + "» - нужно конкретное", 15, "objective_verifiability")
        expected = tcc.lower(s["expected"])
        if s["expected"] and any(w in expected for w in SUBJECTIVE) and not OBJECTIVE_ANCHOR.search(s["expected"]):
            add("TC-6", where, "ожидаемый результат без проверяемого значения: «" + s["expected"][:80] + "»", 20, "objective_verifiability")
        if not s["expected"] and tcc.step_type(s["action"]) == "ASSERT" and not OBJECTIVE_ANCHOR.search(s["action"]):
            add("TC-6", where, "проверка без ожидаемого значения", 20, "objective_verifiability")
        if any(w in low for w in RANDOM):
            add("TC-7", where, "случайное значение - нужен формат или правило генерации", 30, "determinism")
        if NOW.search(low) and not re.search(r"формат|pattern|yyyy|гггг|\d{4}-\d{2}", low):
            add("TC-8", where, "текущее время без формата", 20, "determinism")
        if any(w in low for w in ASYNC) and not WAIT_ANCHOR.search(full):
            add("TC-9", where, "асинхронное ожидание без предела времени", 20, "determinism")
        if API.search(s["action"] + " " + s["data"]) and not ADDRESS.search(full):
            add("TC-10", where, "запрос без адреса (путь, топик, таблица)", critical=True)
        if HARDCODE.search(full):
            add("TC-11", where, "логин или пароль прямо в шаге - нужен ключ настроек или учётная запись из данных", 10, "parametrizability")
        for ref in PREV_REF.finditer(full):
            number = int(ref.group(1))
            if number >= s["n"] or number not in seen_numbers:
                add("TC-12", where, "ссылка на шаг " + str(number) + ", которого до этого шага нет", 30, "independence", True)
        if CREATED_BEFORE.search(full) and not pre.strip("- ") and s["n"] == 1:
            add("TC-12", where, "опирается на созданное ранее, а предусловий нет", 30, "independence", True)
        seen_numbers.add(s["n"])
    critical = any(f[3] for f in findings)
    for name in ("determinism", "objective_verifiability"):
        if scores[name] < 60:
            critical = True
            findings.append(("TC-13", "оценки", name + " = " + str(scores[name]) + " < 60", True))
    avg = sum(scores.values()) // len(scores)
    status = "FAIL" if critical else ("PASS" if avg >= 80 and not any(f[0] == "TC-1" for f in findings) else "WARNING")
    lines = ["# Проверка тест-кейса " + tc["key"], "",
             "- Статус: " + status, "- Blocking: " + ("true" if status == "FAIL" else "false"),
             "- Средняя оценка: " + str(avg), "- Оценки: " + ", ".join(k + " " + str(v) for k, v in scores.items()), "",
             "| Правило | Где | Что не так | Блокирует |", "|---------|-----|------------|-----------|"]
    for rule, where, what, crit in findings:
        lines.append("| %s | %s | %s | %s |" % (rule, where, what.replace("|", "\\|"), "да" if crit else "нет"))
    if not findings:
        lines.append("| - | - | замечаний нет | нет |")
    (path.parent / "TC-CHECK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("СТАТУС: " + status)
    print("BLOCKING: " + ("true" if status == "FAIL" else "false"))
    print("ОЦЕНКИ: среднее " + str(avg) + " · " + ", ".join(k + " " + str(v) for k, v in scores.items()))
    print("ФАЙЛ: " + str(path.parent / "TC-CHECK.md").replace("\\", "/"))
    for rule, where, what, crit in findings:
        print("НАХОДКА: %s · %s · %s%s" % (rule, where, what, " · БЛОКИРУЕТ" if crit else ""))
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
