#!/usr/bin/env python3
"""Помощник исполнителя юнита (скилл migration-step). Запуск из корня мигрируемого проекта:

  python3 <каталог скилла>/scripts/unit.py recite M-007 [S-04]   - что делаю сейчас (напоминание)
  python3 <каталог скилла>/scripts/unit.py rules  M-007 [S-04]   - правила подшага в tmp/rules-now.md
  python3 <каталог скилла>/scripts/unit.py check  M-007 [S-04]   - самопроверка правил кода и границ

Подшаг не указан - берётся первый подшаг юнита со статусом не done.
Python 3.8+, только стандартная библиотека; из внешних команд - только git в check (таймаут 60 с).
Код выхода: 0 - чисто, 1 - есть находки или ошибка в номерах правил, 2 - неверные аргументы.
"""
import re
import subprocess
import sys
from pathlib import Path

MIGRATION = Path(".gigacode") / "data" / "migration"
SKILL_DIR = Path(__file__).resolve().parent.parent
DOC_REF = re.compile(r"\bD-[a-z0-9-]+?-[0-9]+\b")


def read(path):
    return path.read_text(encoding="utf-8")


def cells(line):
    trimmed = line.strip()
    if not trimmed.startswith("|"):
        return []
    raw = trimmed[1:].split("|")
    while raw and raw[-1] == "":
        raw.pop()
    return [c.strip() for c in raw]


def front(text, key):
    m = re.search(r"(?m)^" + re.escape(key) + r":\s*(.*)$", text)
    return m.group(1).strip() if m else "-"


def sections(text):
    result, name, body = {}, None, []
    for line in text.split("\n"):
        if line.startswith("## "):
            if name is not None:
                result[name] = "".join(body)
            name, body = line[3:].strip(), []
        elif name is not None:
            body.append(line + "\n")
    if name is not None:
        result[name] = "".join(body)
    return result


def field(body, name):
    """Значение поля «- Имя: ...» до следующего поля «- X:» верхнего уровня."""
    value, inside = [], False
    for line in body.split("\n"):
        if line.startswith("- " + name):
            inside = True
            value.append(line[line.index(":") + 1:] if ":" in line else "")
        elif inside and re.match(r"^- [А-ЯA-Z][^:]{0,60}:", line):
            break
        elif inside:
            value.append(line)
    return "\n".join(value).strip()


def file_table(body):
    files = {}
    for line in body.split("\n"):
        row = cells(line)
        if len(row) >= 3 and re.search(r"изменить|создать|удалить|добавлен|удалён", row[2]):
            path = row[0].replace("`", "").strip()
            if path and not path.startswith("<") and not path.startswith("Файл"):
                files[path] = row[2]
    return files


class Step:
    def __init__(self, sid="", kind="", title="", status=""):
        self.id, self.kind, self.title, self.status = sid, kind, title, status
        self.files, self.result, self.checkpoint, self.rules, self.body = {}, "", "", "", ""

    def fill(self, body):
        self.body = body
        self.files = file_table(body)
        self.result = field(body, "Итоговый результат")
        self.checkpoint = field(body, "Чекпоинт")
        self.rules = field(body, "Правила подшага")


class Card:
    def __init__(self, path):
        text = read(path)
        self.id = front(text, "id")
        self.type = front(text, "type")
        self.tech = front(text, "tech")
        self.core_mode = front(text, "core_mode")
        parts = sections(text)
        self.steps = []
        for line in parts.get("Подшаги", "").split("\n"):
            row = cells(line)
            if len(row) >= 5 and re.fullmatch(r"S-[0-9]+", row[0]):
                self.steps.append(Step(row[0], row[1], row[2], row[4]))
        for step in self.steps:
            for key, value in parts.items():
                if key.startswith(step.id + " "):
                    step.fill(value)
        whole = Step(kind=self.type)
        title = next((l for l in text.splitlines() if l.startswith("# ")), "")
        whole.title = re.sub(r"^# ", "", title, count=1)
        whole.files = file_table(parts.get("Файлы юнита", ""))
        whole.result = parts.get("Цель", "")
        whole.checkpoint = parts.get("Критерии готовности", "")
        whole.rules = parts.get("Правила юнита", "")
        whole.body = text
        self.whole = whole
        self.confirmations = ""
        start = text.find("### Таблица подтверждений")
        if start >= 0:
            nxt = text.find("\n#", start + 5)
            self.confirmations = text[start:nxt if nxt > 0 else len(text)]

    def step(self, sid):
        if not self.steps:
            return self.whole
        for step in self.steps:
            if (step.id == sid) if sid is not None else (step.status != "done"):
                return step
        if sid is not None:
            raise ValueError("В карточке " + self.id + " нет подшага " + sid)
        raise ValueError("В карточке " + self.id + " все подшаги done")


def one_line(text):
    compact = re.sub(r"\s+", " ", text).strip()
    return compact or "-"


def flow_style():
    map_file = MIGRATION / "MIGRATION-MAP.md"
    return map_file.is_file() and re.search(r"(?m)^- Стиль шагов: flow", read(map_file)) is not None


def rule_ids(card, step):
    """Номера правил: из карточки, иначе - по виду подшага из таблицы references/substep-rules.md."""
    ids = re.findall(r"MR-[0-9H]+", step.rules)
    if ids:
        return ids
    kind = step.kind
    for line in read(SKILL_DIR / "references" / "substep-rules.md").split("\n"):
        if not line.startswith("| `"):
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        head = parts[1]
        match = ("`" + kind + "`") in head
        if kind == "core":
            match = "`core`" in head and ("in-place" if card.core_mode == "in-place" else "new") in head
        if match:
            ids.extend(re.findall(r"MR-[0-9H]+", parts[2]))
            if kind == "core" and card.core_mode == "in-place":
                ids.extend(["MR-12", "MR-13", "MR-24", "MR-30", "MR-32", "MR-41", "MR-43", "MR-49", "MR-50"])
    if flow_style() and kind in ("core", "usage") and "MR-44" not in ids:
        ids.append("MR-44")
    return ids


# ---------- recite ----------

def recite(card, step):
    print("=== СЕЙЧАС ===")
    print("Юнит " + card.id + " (" + card.type + ", " + card.tech + ")"
          + ("" if not step.id else ", подшаг " + step.id + " · " + step.kind + " · " + step.title))
    if card.steps:
        done = sum(1 for s in card.steps if s.status == "done")
        nxt, passed = "-", False
        for s in card.steps:
            if passed and s.status != "done":
                nxt = s.id + " · " + s.kind
                break
            if s.id == step.id:
                passed = True
        print("Подшагов done: " + str(done) + " из " + str(len(card.steps)) + "; следующий после этого: " + nxt)
    print("Файлы (менять можно ТОЛЬКО их):")
    if not step.files:
        print("- нет (код не меняется)")
    for path, action in step.files.items():
        print("- " + path + " (" + action + ")")
    print("Итоговый результат: " + one_line(step.result))
    print("Чекпоинт: " + one_line(step.checkpoint))
    ids = rule_ids(card, step)
    doc_ids = list(dict.fromkeys(DOC_REF.findall(step.body)))
    print("Конспект подшага: " + (", ".join(doc_ids) if doc_ids else "-")
          + "  (текст - в tmp/docs-now.md после unit.py rules; поиск по конспекту - notes.py find " + card.tech + " <слова>)")
    print("Правила подшага: " + ", ".join(ids)
          + "  (текст: python3 .gigacode/skills/migration-step/scripts/unit.py rules " + card.id + " " + step.id + ")")
    print("Порядок: правила -> правки по «Что сделать» -> unit.py check -> проверяющий -> чекпоинт -> коммит")
    print("Нельзя: вопросы человеку; файлы не из списка; DTO ответа; свои matchers и списки matchers;"
          " делегаты и вложенные классы; имена фрейма не из «Таблицы подтверждений».")


# ---------- rules ----------

def record(notes, rid):
    start = re.search(r"(?m)^#{2,3} " + re.escape(rid) + r"\b", notes)
    if not start:
        return None
    nxt = re.compile(r"(?m)^#{1,3} ").search(notes, start.end())
    return notes[start.start():nxt.start() if nxt else len(notes)]


def write_docs(card, step):
    """Записи конспекта, на которые ссылается подшаг и «Таблица подтверждений», - в tmp/docs-now.md."""
    ids = list(dict.fromkeys(DOC_REF.findall(step.body + "\n" + card.confirmations)))
    out = ["# Записи конспекта подшага " + card.id + " " + step.id + "\n\n"]
    found = 0
    for rid in ids:
        notes_file = MIGRATION / "doc-notes" / (rid[2:rid.rindex("-")] + ".md")
        rec = record(read(notes_file), rid) if notes_file.is_file() else None
        if rec is None:
            out.append("## " + rid + " - НЕТ В КОНСПЕКТЕ (ссылка в карточке есть, записи нет)\n\n")
        else:
            out.append(rec + "\n")
            found += 1
    target = MIGRATION / "tmp" / "docs-now.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(out), encoding="utf-8")
    return found


def rules(card, step):
    """0 - все номера найдены; 1 - какого-то правила нет в code-rules.md."""
    text = read(SKILL_DIR / "references" / "code-rules.md")
    ids = rule_ids(card, step)
    out = ["# Правила подшага " + card.id + " " + step.id + " (" + step.kind + ")\n\n"]
    found = []
    copying = False
    for line in text.split("\n"):
        rule = re.match(r"^- \*\*(MR-[0-9H]+) ·", line)
        if rule:
            copying = rule.group(1) in ids
            if copying and rule.group(1) not in found:
                found.append(rule.group(1))
        elif line.startswith("## ") or line.startswith("---"):
            copying = False
        if copying:
            out.append(line + "\n")
    human = re.search(r"(?m)^## Правила: добавлено человеком", text)
    if human:
        out.append("\n" + text[human.start():])
    target = MIGRATION / "tmp" / "rules-now.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(out), encoding="utf-8")
    docs = write_docs(card, step)
    missing = [i for i in ids if i not in found]
    if not ids:
        missing.append("(номеров нет ни в карточке, ни в substep-rules.md для вида " + step.kind + ")")
    print("Записано в " + str(target) + ": " + str(len(found)) + " правил - " + ", ".join(found))
    if missing:
        print("ОШИБКА: не найдены в code-rules.md: " + ", ".join(missing)
              + " - исправь номера в карточке (таблица - references/substep-rules.md), потом запусти снова")
    print("Записи конспекта подшага: " + str(docs) + " - в .gigacode/data/migration/tmp/docs-now.md")
    print("Прочитай оба файла целиком перед правками. Нужного имени фрейма там нет -> сначала notes.py find, потом сабагент документации.")
    return 0 if not missing else 1


# ---------- check ----------

FILE_CHECKS = [
    ("MR-33", r"(^|[^A-Za-z0-9_])var +[A-Za-z_][A-Za-z0-9_]* *(=|:)", "var вместо явного типа"),
    ("MR-29", r"Assertions\.|assert(Equals|True|False|NotNull|Null|That|All)\(|SoftAssertions",
     "ассерт вместо matcher: замени на matcher; matcher нет в документации - запиши в «Сделано» подшага «исключение MR-29: <файл>:<строка>» и строку во «Входящие»"),
    ("MR-41", r"\.as\([A-Z][A-Za-z0-9_]*\.class\)|readValue\(|fromJson\(|\.getObject\(|\.extract\(\)", "ответ превращают в объект"),
    ("MR-4", r"^(?!.*@ru\.sber\.qa\.allure\.system\.System\b)[^/*\"]*[^A-Za-z0-9_.\"](org|com|ru|io|java)\.[a-z0-9_]+\.[a-z0-9_.]+\.[A-Z]",
     "полное имя класса в коде вместо import"),
    ("MR-43", r"\b(log|logger|LOG|LOGGER)\.(info|debug|trace|warn|error)\(|System\.(out|err)\.print|\.log\(\)\.(all|body|headers|ifValidationFails)|(Request|Response)LoggingFilter|\.prettyPrint\(|\.prettyPeek\(|\.peek\(",
     "ручное логирование (остаётся только ход сценария)"),
    ("MR-48", r"implements [A-Za-z.]*(Matcher|Condition)\b|List<[A-Za-z.]*Matcher>|matchers\.add\(|\.toArray\(new [A-Za-z.]*Matcher|static [A-Za-z.<>]*(Matcher|Condition) [a-z][A-Za-z0-9]*\(",
     "своя конструкция вокруг matcher"),
    ("MR-48", r"getRestHistory\(\)\.getLast\(\)|JacksonHelper|JsonNode|\.path\(\"|textOrNull|intOrNull|longOrNull|boolOrNull|compareNumbers|assertDatesEqual|bigDecimalsEqual",
     "ответ разбирают руками или своими хелперами"),
    ("MR-48", r"equalToText\(String\.valueOf|equalToText\([^)]*\.toString\(\)", "число или дата проверяются как текст"),
    ("MR-48", r"assertAll\(", "assertAll: группа проверок - .shouldSoft(...)"),
    ("MR-49", r"^\s+(public |private |protected )?(static )?(final )?(class|interface|enum|record) [A-Z]", "вложенный класс"),
    ("MR-49", r"^\s+return [A-Z][A-Za-z0-9]*\.[a-z][A-Za-z0-9]*\([a-zA-Z, ]*\);", "метод-делегат: перевести вызывающих на настоящий метод"),
    ("MR-47", r"ConfigFactory\.create|new Properties\(\)|getResourceAsStream\(|ResourceBundle\.getBundle|System\.(getProperty|getenv)\(|@Value\(|PropertiesLoader|ConfigReader|PropertyReader",
     "своё чтение настроек"),
    ("MR-45", r"(^|[ .(])[a-z][A-Za-z0-9]*_[A-Za-z0-9_]*( *\(| *=| *;|,|\))", "имя с нижним подчёркиванием"),
    ("MR-14", r"Thread\.sleep|TimeUnit\.[A-Z]+\.sleep", "sleep вместо ожидания фрейма"),
    ("MR-21", r"\b(TODO|FIXME)\b", "TODO/FIXME в коде"),
]
TEST_CLASS_CHECKS = [
    ("MR-46", r"@ExtendWith\(PerfeccionistaExtension|@SetEnvironmentConfiguration", "аннотации фрейма на тест-классе (место - базовый тест-класс)"),
    ("MR-42", r"^\s*(private|protected|static) [^=]*\([^)]*\)\s*(throws [A-Za-z, ]+)?\{", "вспомогательный метод в тест-классе (место - класс шагов)"),
]
# re.ASCII: \b и \w как в Java - по латинице и цифрам
COMPILED = {}


def compiled(pattern):
    if pattern not in COMPILED:
        COMPILED[pattern] = re.compile(pattern, re.ASCII)
    return COMPILED[pattern]


def exceptions(step):
    """Разрешённые исключения: строка «исключение MR-29: <файл>:<строка>» в разделе подшага."""
    return {m.group(1) + " " + m.group(2) + ":" + m.group(3)
            for m in re.finditer(r"исключение (MR-29): `?([^`\s:]+):([0-9]+)", step.body)}


def is_builder(line):
    return re.search(r"static (final )?class [A-Za-z]*Builder\b", line) is not None


def scan(path, lines, checks, allowed):
    count = 0
    in_block = False
    for i, line in enumerate(lines):
        trimmed = line.strip()
        if trimmed.startswith("/*"):
            in_block = True
        comment = (in_block or trimmed.startswith("//") or trimmed.startswith("*")
                   or trimmed.startswith("import ") or trimmed.startswith("package "))
        if "*/" in trimmed:
            in_block = False
        for rule, pattern, message in checks:
            if comment and rule != "MR-21":
                continue
            if compiled(pattern).search(line):
                if rule == "MR-49" and message.startswith("вложенный") and is_builder(line):
                    continue
                if rule + " " + str(path).replace("\\", "/") + ":" + str(i + 1) in allowed:
                    continue
                print(rule + " " + str(path) + ":" + str(i + 1) + " - " + message + ": " + trimmed)
                count += 1
    return count


def indent(line):
    return len(line) - len(line.lstrip(" "))


def check_settings(path):
    """Файл настроек: у каждого ключа есть значение, заглушек нет (MR-47, значения - из CONNECTIONS.md)."""
    found = 0
    lines = read(path).splitlines()
    empty = re.compile(r"^\s*[^#!\s][^=:]*[=:]\s*$")
    stub = re.compile(r"TODO|changeme|change_me|<[^>]+>|\"\"\s*$", re.IGNORECASE)
    yaml = re.search(r"\.ya?ml$", str(path)) is not None
    for i, line in enumerate(lines):
        if line.strip().startswith("#") or line.strip().startswith("!"):
            continue
        yaml_parent = yaml and line.strip().endswith(":") and i + 1 < len(lines) and indent(lines[i + 1]) > indent(line)
        if (empty.match(line) and not yaml_parent) or stub.search(line):
            print("MR-47 " + str(path) + ":" + str(i + 1) + " - ключ без значения или заглушка (значение - из CONNECTIONS.md): " + line.strip())
            found += 1
    return found


def check_setters(path, lines):
    """MR-34: 4 и более setXxx подряд на одну переменную."""
    setter = re.compile(r"^\s*([a-z][A-Za-z0-9]*)\.set[A-Z][A-Za-z0-9]*\(")
    current, run, start, count = None, 0, 0, 0
    for i in range(len(lines) + 1):
        m = setter.search(lines[i]) if i < len(lines) else None
        variable = m.group(1) if m else None
        if variable is not None and variable == current:
            run += 1
            continue
        if run >= 4:
            print("MR-34 " + str(path) + ":" + str(start + 1) + " - сеттеров подряд на " + str(current) + ": " + str(run) + ", нужен билдер")
            count += 1
        current = variable
        run = 0 if variable is None else 1
        start = i
    return count


def check_service_lookups(path, lines):
    """MR-35: getForCurrentThread() чаще, чем разных сервисов в файле."""
    lookups = sum(1 for line in lines if "getForCurrentThread()" in line)
    services = set()
    for line in lines:
        services.update(re.findall(r"getService\(([A-Za-z0-9_]+)\.class\)", line))
    if lookups > max(1, len(services)):
        print("MR-35 " + str(path) + " - getForCurrentThread() " + str(lookups) + " раз при " + str(len(services))
              + " сервисах: получение сервиса - один приватный метод")
        return 1
    return 0


def check_boundaries(step):
    """Изменённые файлы вне списка подшага."""
    # -z: пути как есть (пробелы, кириллица); --untracked-files=all: новые файлы поимённо
    try:
        output = subprocess.run(["git", "status", "--porcelain", "-z", "--untracked-files=all"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired) as error:
        print("ГРАНИЦЫ не проверены: git status не выполнился (" + str(error) + ")")
        return 1
    count = 0
    entries = output.split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        if "R" in status or "C" in status:
            i += 1  # следующая запись - старый путь переименования
        if path.startswith(".gigacode/"):
            continue
        if path not in step.files:
            print("ГРАНИЦЫ " + path + " - изменён, но его нет в файлах подшага: верни (git checkout -- " + path
                  + ") или допиши в карточку с пометкой «добавлен по ходу»")
            count += 1
    return count


def check(card, step):
    findings = 0
    print("CHECK " + card.id + " " + step.id + " (" + step.kind + "), файлов: " + str(len(step.files)))
    allowed = exceptions(step)
    for name, action in step.files.items():
        path = Path(name)
        if "удал" in action:
            if path.exists():
                print("ИТОГ " + name + ": файл должен быть удалён, но есть")
                findings += 1
            continue
        if not path.exists():
            print("ИТОГ " + name + ": файла нет")
            findings += 1
            continue
        if re.search(r"\.(properties|ya?ml)$", name):
            findings += check_settings(path)
            continue
        if not (name.endswith(".java") or name.endswith(".kt")):
            continue
        lines = read(path).splitlines()
        findings += scan(path, lines, FILE_CHECKS, allowed)
        if any(re.match(r"\s*@Test\b", l) for l in lines):
            findings += scan(path, lines, TEST_CLASS_CHECKS, allowed)
        findings += check_setters(path, lines)
        findings += check_service_lookups(path, lines)
    findings += check_boundaries(step)
    print("ИТОГ: находок " + str(findings) + (" - чисто" if findings == 0 else " - исправь и запусти снова"))
    return 0 if findings == 0 else 1


def main(args):
    if len(args) < 2:
        print("Использование: unit.py <recite|rules|check> M-<nnn> [S-<nn>]")
        return 2
    command = args[0]
    card_path = MIGRATION / "units" / (args[1] + ".md")
    if not card_path.is_file():
        print("НЕТ КАРТОЧКИ " + str(card_path) + " - проверь ID юнита (раздел 4 карты) и что запускаешь из корня проекта, где лежит .gigacode/")
        return 2
    card = Card(card_path)
    try:
        step = card.step(args[2] if len(args) > 2 else None)
    except ValueError as error:
        print(str(error))
        return 2
    if command == "recite":
        recite(card, step)
        return 0
    if command == "rules":
        return rules(card, step)
    if command == "check":
        return check(card, step)
    print("Неизвестная команда: " + command)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
