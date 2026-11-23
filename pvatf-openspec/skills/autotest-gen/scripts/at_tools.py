#!/usr/bin/env python3
"""Инструменты генерации автотеста по плану (скилл autotest-gen). Запуск из корня проекта:

  python3 <скилл>/scripts/at_tools.py rules <ключ ТК>              - правила кода и конспект в rules-now.md, docs-now.md
  python3 <скилл>/scripts/at_tools.py next <ключ ТК>               - задание агенту pvatf-generator на следующий G
  python3 <скилл>/scripts/at_tools.py mark <ключ ТК> <G-n> <статус> - статус G в плане: ok / stub / blocked / todo
  python3 <скилл>/scripts/at_tools.py compile <ключ ТК> <G-n>      - компиляция после G (mvn -q test-compile из ENV.json)
  python3 <скилл>/scripts/at_tools.py assemble <ключ ТК>           - собрать тест-класс из фрагментов
  python3 <скилл>/scripts/at_tools.py check <ключ ТК> [--no-compile] - самопроверка кода, покрытие шагов, компиляция
  python3 <скилл>/scripts/at_tools.py run <ключ ТК> [--dry-run | --report-only] - запуск тест-класса, разбор отчёта JUnit

run: команда - из команды компиляции ENV.json (Maven: test -Dtest=<класс>, Gradle: test --tests <класс>),
таймаут 540 секунд; падения делит на СТЕНД (сеть, доступ), ПРОВЕРКА (ассерты), КОД (остальное);
--dry-run - только печать команды, --report-only - разобрать отчёт прогона, который запускал человек.
Пишет RUN.md, run.log и run_status в шапку плана (design.md изменения).

Файлы - в openspec/changes/<имя>/: design.md (план), outputs/: fragments/G-<n>.md (фрагменты от
агента), rules-now.md, docs-now.md, CHECK.md (итог проверки). Повторный запуск любой команды
ничего не ломает: assemble переписывает только файл, который сам создал (есть строка-метка).
Python 3.8+, только стандартная библиотека. Код выхода: 0 - выполнено / чисто, 1 - есть
находки или нечего делать, 2 - неверные аргументы или нет файлов.
"""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from java_checks import CHECKS, TEST_ONLY, compile_project, scan  # noqa: E402 - общий модуль набора
import pvatf_paths as pp  # noqa: E402 - копия shared/scripts

DATA = Path(".gigacode") / "data" / "autotest"
SKILL = Path(__file__).resolve().parent.parent
NOTE_DIRS = [pp.root() / "doc-notes", pp.migration_notes()]
MARK = "// Сгенерировано autotest-gen по тест-кейсу "
GEN_RULES = ["MR-1", "MR-2", "MR-3", "MR-4", "MR-5", "MR-8", "MR-12", "MR-13", "MR-14", "MR-15", "MR-19", "MR-20",
             "MR-21", "MR-22", "MR-29", "MR-48", "MR-41", "MR-43", "MR-42", "MR-30", "MR-49", "MR-50", "MR-33", "MR-34",
             "MR-35", "MR-46", "MR-47", "MR-37", "MR-38", "MR-39", "MR-40", "MR-45"]
STATUSES = ("todo", "ok", "stub", "blocked")
GLOSSARY = """Правила общие с миграцией. При генерации автотеста слова в них значат:
- «карточка», «юнит», «подшаг» - задание агенту на один G и план design.md;
- «Файлы юнита», «файлы подшага» - файлы, которые ты создаёшь или меняешь в этом G (классы шагов,
  страниц, файлы данных); существующие методы проекта не меняешь, только добавляешь новые;
- «Таблица подтверждений», «конспект» - docs-now.md (записи D-<tech>-<n>);
- «Входящие», «решить человеку» - строка «Причина» фрагмента со статусом stub или blocked;
- «старый код», «legacy», «удаляется» - к генерации не относится: ничего не удаляешь;
- исключение MR-29 (оставить стандартный ассерт) при генерации не действует: matcher нет в
  конспекте -> статус blocked с вопросом документации.

"""
def fail(message, code=2):
    print(message)
    return code


def folder(key):
    return pp.autotest_dir(key, create=False)


def plan_path(key):
    return pp.plan_file(key, create=False)


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def head_of(text):
    return dict(re.findall(r"(?m)^(\w+):[ \t]*(.*)$", text.split("\n---", 1)[0]))


def set_head(text, name, value):
    return re.sub(r"(?m)^" + name + r":[ \t]*.*$", name + ": " + value, text, count=1)


def section_rows(text, title):
    sect = re.search(r"(?ms)^## " + re.escape(title) + r"\s*\n(.*?)(?=^## |\Z)", text)
    rows = []
    for line in (sect.group(1) if sect else "").split("\n"):
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if cells and not set(cells[0]) <= set("-:") and cells[0] not in ("Шаг", "G", "Имя", "Значение", "Файл", "Ключ"):
            rows.append(cells)
    return rows


def journal(text, what):
    return text.rstrip("\n") + "\n| at_tools | " + what + " |\n"


def plan(key):
    path = plan_path(key)
    text = read(path)
    if not text:
        return None, None, None
    head = head_of(text)
    return path, text, head


# ---------- rules ----------

def cmd_rules(key):
    path, text, head = plan(key)
    if text is None:
        return fail("НЕТ ПЛАНА (design.md изменения): сначала артефакт design / autotest-plan")
    source = read(SKILL / "references" / "code-rules.md")
    if not source:
        return fail("НЕТ references/code-rules.md в скилле autotest-gen - переустанови набор")
    ids = list(GEN_RULES) + (["MR-44"] if head.get("step_style") == "flow" else [])
    out, copying, found = ["# Правила кода для генерации " + key + "\n\n" + GLOSSARY], False, []
    for line in source.split("\n"):
        rule = re.match(r"^- \*\*(MR-[0-9H]+) ·", line)
        if rule:
            copying = rule.group(1) in ids
            if copying:
                found.append(rule.group(1))
        elif line.startswith("## ") or line.startswith("---"):
            copying = False
        if copying:
            out.append(line + "\n")
    human = re.search(r"(?m)^## Правила: добавлено человеком", source)
    if human:
        out.append("\n" + source[human.start():])
    (folder(key) / "rules-now.md").write_text("".join(out), encoding="utf-8")
    labels = sorted({r[4] for r in section_rows(text, "3. Порядок генерации") if len(r) > 4} | {"common"})
    docs, count = ["# Конспект документации для " + key + "\n\n"], 0
    for label in labels:
        for base in NOTE_DIRS:
            notes = read(base / (label + ".md"))
            for rec in re.finditer(r"(?ms)^#{2,3} (D-[A-Za-z0-9-]+-\d+)\b.*?(?=^#{1,3} |\Z)", notes):
                if "НЕТ В ДОКЕ" not in rec.group():
                    docs.append(rec.group().rstrip() + "\n\n")
                    count += 1
    (folder(key) / "docs-now.md").write_text("".join(docs), encoding="utf-8")
    print("ПРАВИЛА: " + str(len(found)) + " - " + ", ".join(found))
    missing = [i for i in ids if i not in found]
    if missing:
        print("ОШИБКА: нет в code-rules.md: " + ", ".join(missing))
    print("КОНСПЕКТ: записей " + str(count) + " по меткам " + ", ".join(labels))
    print("ФАЙЛЫ: " + str(folder(key) / "rules-now.md") + ", " + str(folder(key) / "docs-now.md"))
    return 1 if missing else 0


# ---------- next / mark ----------

def cmd_next(key):
    path, text, head = plan(key)
    if text is None:
        return fail("НЕТ ПЛАНА (design.md изменения): сначала артефакт design / autotest-plan")
    if head.get("plan_status") not in ("planned", "generating"):
        return fail("plan_status " + head.get("plan_status", "-") + " - генерация только по плану planned или generating", 1)
    if not head.get("approved", "no").startswith("yes"):
        return fail("ПЛАН НЕ ПОДТВЕРЖДЁН: approved " + head.get("approved", "no") + " - человек подтверждает разделы 11-16"
                    " design.md (tc_plan.py approve " + key + "), код до этого не пишется", 1)
    gens = section_rows(text, "3. Порядок генерации")
    steps = {r[0]: r for r in section_rows(text, "2. Шаги")}
    todo = [g for g in gens if len(g) >= 8 and g[7] == "todo"]
    if not todo:
        print("ВСЕ G ГОТОВЫ: " + ", ".join(g[0] + " " + g[7] for g in gens) + " - дальше assemble")
        return 1
    g = todo[0]
    tc = read(folder(key) / "TC.md")
    consts = [c for c in section_rows(text, "4. Константы") if c[0] != "-" and set(c[5].replace(" ", "").split(",")) & set(g[1].replace(" ", "").split(","))]
    variables = [v for v in section_rows(text, "5. Переменные") if v[0] != "-"]
    classes = [l[2:] for l in text.split("\n") if l.startswith("- " + g[2] + " · `")
               and not re.search(r"/config/|Configuration\.java`", l)]  # конфигурация окружения - не класс шагов
    root = str(Path(".").resolve())
    lines = ["ЗАДАНИЕ для агента pvatf-generator (передай дословно, всё ниже этой строки):", "",
             "- Проект: " + root,
             "- Тест-кейс: " + read(folder(key) / "TC.md").split("\n", 1)[0].lstrip("# "),
             "- Шаг генерации: " + g[0] + " · " + g[2] + " · " + g[3] + " · метка " + g[4],
             "- Справка технологии: " + str(SKILL / "references" / g[5]),
             "- Правила кода: " + root + "/" + str(folder(key) / "rules-now.md"),
             "- Конспект документации: " + root + "/" + str(folder(key) / "docs-now.md"),
             "- Как писать проверки: " + str(SKILL / "references" / "matchers.md"),
             "- Стиль шагов проекта: " + head.get("step_style", "-") + " · библиотека UI: " + head.get("ui_lib", "-"),
             "- Тест-класс (собирает скрипт, ты его не пишешь): " + head.get("test_file", "-") + " · пакет " + head.get("package", "-"),
             "- Фрагмент записать в: " + root + "/" + str(folder(key) / "fragments" / (g[0] + ".md")),
             "- Шаги тест-кейса этого G:"]
    for sid in [s.strip() for s in g[1].split(",")]:
        r = steps.get(sid)
        if r:
            number = sid.split(".")[0]
            data = re.search(r"(?m)^\| " + re.escape(number) + r" \|(?:[^|\\]|\\.)*\|((?:[^|\\]|\\.)*)\|", tc)
            lines.append("  - Шаг " + sid + " · " + r[3] + ": " + r[1] + " · данные: " + (data.group(1).strip() if data else "-")
                         + " · ожидается: " + r[2] + " · связь данных: " + r[9])
    ids = {s.strip().split(".")[0] for s in g[1].split(",")}
    service = [sid for sid in [s.strip() for s in g[1].split(",")] if steps.get(sid) and steps[sid][3] == "SERVICE"]
    if service:
        lines.append("- Служебные шаги старой реализации (кода нет, только комментарий «// Шаг <n>: <действие> - служебный шаг,"
                     " кода нет»): " + ", ".join(service))
    reqs = [r for r in section_rows(text, "9. Запросы из артефактов") if r[0] in ids and len(r) >= 8 and r[1] != "-"]
    lines.append("- Запросы из артефактов (метод, адрес, все заголовки и тело - отсюда; секрет *** - значение из сессии или"
                 " настроек по конспекту, не из артефакта):")
    lines += ["  - шаг %s · %s · %s %s · заголовки: %s · тело запроса: %s · код ответа: %s · тело ответа: %s" % (
        r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]) for r in reqs] or ["  - нет"]
    values = [v for v in section_rows(text, "10. Значения из выборки") if len(v) >= 5 and v[0] != "-"]
    lines.append("- Значения из выборки (в коде и в файлах данных - переменная шага-источника, литерал значения запрещён):")
    lines += ["  - " + v[0] + " -> переменная " + v[4] + " (шаг " + v[1] + ", поле " + v[2] + "; шаги " + v[3] + ")" for v in values] or ["  - нет"]
    lines.append("- Константы этого G (имя - значение - источник - форма):")
    lines += ["  - " + c[0] + " - " + c[1] + " - " + c[2] + " - " + c[3] for c in consts] or ["  - нет"]
    lines.append("- Переменные теста (имя - шаг - откуда):")
    lines += ["  - " + v[0] + " - " + v[1] + " - " + v[2] for v in variables] or ["  - нет"]
    lines.append("- Готовые фрагменты прошлых G (их переменные доступны): " + (", ".join(
        p.stem for p in sorted((folder(key) / "fragments").glob("G-*.md"))) or "нет"))
    files = [r for r in section_rows(text, "11. Файлы") if len(r) >= 4 and r[0] != "-"]
    if files:
        stems = {m[1] for m in section_rows(text, "12. Методы шагов") if len(m) >= 6 and m[0] == g[0]}
        lines.append("- ДОГОВОР ПЛАНА (подтверждён человеком; код только так, ничего сверх):")
        lines.append("  - файлы этого G (путь - действие - что в нём):")
        lines += ["    - " + r[0] + " - " + r[1] + " - " + r[2] for r in files
                  if r[3] == g[0] or Path(r[0]).stem in stems or (r[1] == "создать" and "testdata/" in r[0])] or ["    - нет"]
        lines.append("  - методы (класс - метод - шаги ТК - запрос - параметры):")
        lines += ["    - " + m[1] + " - " + m[2] + "() - " + m[3] + " - " + m[4] + " - " + m[5]
                  for m in section_rows(text, "12. Методы шагов") if len(m) >= 6 and m[0] == g[0]] or ["    - нет"]
        lines.append("  - проверки (шаг - объект - поле - как - ожидаемое; одна строка = одна проверка в коде):")
        lines += ["    - " + " - ".join(c[:5]) for c in section_rows(text, "13. Проверки")
                  if len(c) >= 5 and c[0].split(".")[0] in ids] or ["    - нет"]
        lines.append("  - настройки (ключ - файл - кто читает):")
        lines += ["    - " + st[0] + " - " + st[1] + " - " + st[3] for st in section_rows(text, "14. Настройки")
                  if len(st) >= 4 and st[0] != "-"] or ["    - нет"]
        sect = re.search(r"(?ms)^## 16\. Планируемые изменения\s*\n(.*?)(?=^## |\Z)", text)
        blocks = [b for b in re.split(r"(?m)^### ", sect.group(1) if sect else "")[1:]
                  if re.search(r"(?m)^- G: .*\b" + re.escape(g[0]) + r"\b", b)]
        if blocks:
            lines.append("  - планируемые изменения (design.md, раздел 16; сигнатуры и параметры - ровно так):")
            for b in blocks:
                lines += ["    " + ("### " if i == 0 else "") + l for i, l in enumerate(b.rstrip().splitlines())]
    lines.append("- Классы шагов проекта для этой технологии (переиспользуй, если подходят):")
    lines += ["  - " + c for c in classes] or ["  - нет"]
    print("\n".join(lines))
    return 0


def cmd_mark(key, gid, status):
    path, text, head = plan(key)
    if text is None:
        return fail("НЕТ ПЛАНА (design.md изменения)")
    if status not in STATUSES:
        return fail("статус - один из: " + ", ".join(STATUSES))
    pattern = re.compile(r"(?m)^(\| " + re.escape(gid) + r" \|(?:[^|\n]*\|){6}) *\w+ *\|$")
    if not pattern.search(text):
        return fail("в разделе 3 плана нет строки " + gid, 1)
    frag = folder(key) / "fragments" / (gid + ".md")
    if status == "ok" and not frag.is_file():
        return fail("нет фрагмента fragments/" + gid + ".md - агент его не записал; статус не меняю", 1)
    if status in ("stub", "blocked") and not frag.is_file():
        # заглушка с комментарием «// Шаг <n>» на каждый шаг G: проверка покрытия видит шаг,
        # а строка STUB уходит в итог человеку
        steps = {r[0]: r for r in section_rows(text, "2. Шаги")}
        row = next((g for g in section_rows(text, "3. Порядок генерации") if g[0] == gid), None)
        body = []
        for sid in (row[1].replace(" ", "").split(",") if row else []):
            action = steps[sid][1] if sid in steps and len(steps[sid]) > 1 else "-"
            body += ["// Шаг " + sid + ": " + action,
                     "// STUB " + gid + ": фрагмент не получен, шаг дописать вручную"]
        if not body:
            body = ["// STUB " + gid + ": фрагмент не получен, шаг дописать вручную"]
        frag.parent.mkdir(parents=True, exist_ok=True)
        frag.write_text("# " + gid + "\n\n- Статус: " + status + "\n- Файлы шагов: -\n\n## imports\n```java\n```\n\n"
                        "## fields\n```java\n```\n\n## body\n```java\n" + "\n".join(body) + "\n```\n", encoding="utf-8")
    text = pattern.sub(lambda m: m.group(1) + " " + status + " |", text, count=1)
    stale = folder(key) / "compile" / (gid + ".md")
    if stale.is_file():
        stale.unlink()  # код G меняется - прошлая компиляция не в счёт
    if head.get("plan_status") == "planned" or (status == "todo" and head.get("plan_status") in ("assembled", "checked")):
        text = set_head(text, "plan_status", "generating")
    path.write_text(journal(text, gid + " -> " + status), encoding="utf-8")
    left = [g[0] for g in section_rows(text, "3. Порядок генерации") if len(g) >= 8 and g[7] == "todo"]
    print("ОТМЕЧЕНО: " + gid + " " + status + " · осталось todo: " + (", ".join(left) or "нет - дальше assemble"))
    sync_tasks(key)
    return 0


def cmd_compile(key, gid):
    """Компиляция проекта после G: классы шагов этой G уже в проекте, ошибка видна на своей группе, а не в конце."""
    path, text, head = plan(key)
    if text is None:
        return fail("НЕТ ПЛАНА (design.md изменения)")
    row = next((g for g in section_rows(text, "3. Порядок генерации") if g[0] == gid), None)
    if not row:
        return fail("в разделе 3 плана нет строки " + gid, 1)
    if len(row) < 8 or row[7] not in ("ok", "stub"):
        return fail(gid + " не готов (статус " + (row[7] if len(row) > 7 else "-") + ") - сначала задание агенту и mark " + gid + " ok", 1)
    status, details = compile_project(540)
    target = folder(key) / "compile" / (gid + ".md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Компиляция после " + gid + "\n\n- Компиляция: " + status + "\n\n" + "\n".join("- " + d for d in details) + "\n",
                      encoding="utf-8")
    for d in details if status == "failed" else []:
        print("КОМПИЛЯЦИЯ " + d)
    print("КОМПИЛЯЦИЯ: " + status + " · " + gid + (" · " + details[0] if details and status != "failed" else ""))
    if status == "failed":
        print("НУЖНО: mark " + key + " " + gid + " todo, затем next - то же задание агенту pvatf-generator, строки КОМПИЛЯЦИЯ"
              " добавь в конец задания дословно; не больше 2 кругов, потом mark " + key + " " + gid + " stub")
    sync_tasks(key)
    return 0 if status in ("ok", "skipped") else 1


def sync_tasks(key):
    """OpenSpec: чекбоксы tasks.md изменения - сразу по статусам плана (os_artifacts.py sync)."""
    change = pp.find_change("autotest", key) if pp.on() else None
    script = SKILL.parent / "autotest-plan" / "scripts" / "os_artifacts.py"
    if change is None or not script.is_file() or not (change / "tasks.md").is_file():
        return
    import subprocess
    try:
        r = subprocess.run([sys.executable, str(script), "sync", change.name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        print(r.stdout.decode("utf-8", "replace").strip())
    except (OSError, subprocess.TimeoutExpired):
        print("СИНХРОНИЗАЦИЯ: не выполнена - запусти os_artifacts.py sync " + change.name)


# ---------- assemble ----------

def fragment(path):
    text = read(path)
    blocks = {}
    for name in ("imports", "fields", "body"):
        m = re.search(r"(?ms)^## " + name + r"\s*\n```(?:java|kotlin)?\n(.*?)```", text)
        blocks[name] = m.group(1).rstrip() if m else ""
    status = re.search(r"(?m)^- Статус:\s*(\w+)", text)
    files = re.search(r"(?m)^- Файлы шагов:\s*(.*)$", text)
    return {"status": status.group(1) if status else "-", "files": files.group(1) if files else "-", **blocks}


STEP_MARK = re.compile(r"^\s*//\s*Шаг\s+([0-9]+(?:\.[0-9]+)?)\s*:")
DECL = re.compile(r"^(\s*)(?:final\s+)?([A-Z][\w.]*(?:<[^=;]*>)?(?:\[\])?)\s+([a-z]\w*)\s*=\s*(.*)$")
PHASE = {"SETUP": "before", "TEARDOWN_CLEANUP": "after"}


def split_phases(parts, types):
    """Тела фрагментов -> строки трёх методов: before (SETUP), test, after (TEARDOWN_CLEANUP).
    Граница - комментарий «// Шаг <id>:»; строки до первого комментария идут с первым шагом фрагмента."""
    phases = {"before": [], "test": [], "after": []}
    for p in parts:
        lines = p["body"].split("\n")
        first = next((STEP_MARK.match(l).group(1) for l in lines if STEP_MARK.match(l)), None)
        current = PHASE.get(types.get(first, ""), "test")
        chunk = []
        for line in lines:
            mark = STEP_MARK.match(line)
            if mark:
                nxt = PHASE.get(types.get(mark.group(1), ""), "test")
                if nxt != current and chunk:
                    phases[current].append(chunk)
                    chunk = []
                current = nxt
            chunk.append(line)
        if chunk:
            phases[current].append(chunk)
    return {k: [l for c in v for l in c + [""]][:-1] if v else [] for k, v in phases.items()}


def lift_shared(phases):
    """Переменная объявлена в одном методе и нужна в другом -> поле класса, в методе - присваивание."""
    fields = []
    for name, lines in phases.items():
        others = "\n".join(l for k, v in phases.items() if k != name for l in v)
        for index, line in enumerate(lines):
            m = DECL.match(line)
            if m and re.search(r"\b" + re.escape(m.group(3)) + r"\b", others):
                fields.append("private " + m.group(2) + " " + m.group(3) + ";")
                lines[index] = m.group(1) + m.group(3) + " = " + m.group(4)
    return fields


def cmd_assemble(key):
    path, text, head = plan(key)
    if text is None:
        return fail("НЕТ ПЛАНА (design.md изменения)")
    gens = section_rows(text, "3. Порядок генерации")
    not_ready = [g[0] + " " + g[7] for g in gens if len(g) >= 8 and g[7] not in ("ok", "stub", "blocked")]
    if not_ready:
        return fail("НЕ ГОТОВЫ: " + ", ".join(not_ready) + " - сначала next/mark по каждому G", 1)
    parts = [fragment(folder(key) / "fragments" / (g[0] + ".md")) for g in gens]
    imports, fields, field_names = [], [], set()
    for p in parts:
        for line in p["imports"].split("\n"):
            line = line.strip()
            if line.startswith("import ") and line not in imports:
                imports.append(line)
        for line in p["fields"].split("\n"):
            name = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
            if line.strip() and (not name or name.group(1) not in field_names):
                fields.append(line.strip())
                if name:
                    field_names.add(name.group(1))
    tc_head = read(folder(key) / "TC.md").split("\n", 1)[0].lstrip("# ")
    title = tc_head.split("·", 1)[1].strip() if "·" in tc_head else tc_head
    types = {r[0]: r[3] for r in section_rows(text, "2. Шаги") if len(r) > 3}
    phases = split_phases(parts, types)
    for line in lift_shared(phases):
        if line not in fields:
            fields.append(line)
    for extra, phase in (("import org.junit.jupiter.api.BeforeEach;", "before"), ("import org.junit.jupiter.api.AfterEach;", "after")):
        if phases[phase] and extra not in imports:
            imports.append(extra)
    no_tc = re.fullmatch(r"NOTC-[0-9]+", key) is not None  # ТК ещё не заведён: @TmsLink не ставим, ключ не выдумываем
    for extra in ("import io.qameta.allure.TmsLink;", "import org.junit.jupiter.api.DisplayName;", "import org.junit.jupiter.api.Test;"):
        if extra not in imports and not (no_tc and "TmsLink" in extra):
            imports.append(extra)
    base_fqn = head.get("base_fqn", "-")
    if "." in base_fqn and base_fqn.rsplit(".", 1)[0] != head["package"] and ("import " + base_fqn + ";") not in imports:
        imports.append("import " + base_fqn + ";")  # BaseTest в <корень>, тест - в <корень>.tests
    name = head["class"]
    method = name[0].lower() + name[1:-4] if name.endswith("Test") and len(name) > 4 else "scenario"
    base = head.get("base_class", "-")
    out = ["package " + head["package"] + ";", ""] + sorted(imports) + ["", MARK + key,
           "public class " + name + (" extends " + base if base not in ("", "-") else "") + " {", ""]
    out += ["    " + f for f in fields] + ([""] if fields else [])
    suffix = method[0].upper() + method[1:]
    if phases["before"]:
        out += ["    @BeforeEach", "    void before" + suffix + "() {"]
        out += [("        " + l if l.strip() else "") for l in phases["before"]] + ["    }", ""]
    out += ["    @Test"] + ([] if no_tc else ["    @TmsLink(\"" + key + "\")"]) + [
            "    @DisplayName(\"" + ("" if no_tc else "[" + key + "] ") + title.replace("\\", "\\\\").replace("\"", "\\\"") + "\")",
            "    void " + method + "() {"]
    out += [("        " + l if l.strip() else "") for l in phases["test"]]
    out += ["    }"]
    if phases["after"]:
        out += ["", "    @AfterEach", "    void after" + suffix + "() {"]
        out += [("        " + l if l.strip() else "") for l in phases["after"]] + ["    }"]
    out += ["}", ""]
    target = Path(head["test_file"])
    if target.is_file() and MARK + key not in [line.strip() for line in read(target).splitlines()]:
        return fail("ФАЙЛ ЕСТЬ: " + str(target) + " создан не autotest-gen - не перезаписываю; поменяй class в плане", 1)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(out), encoding="utf-8")
    stubs = [g[0] for g, p in zip(gens, parts) if p["status"] != "ok" or not p["body"].strip() or re.search(r"//\s*STUB\b", p["body"])]
    text = set_head(text, "plan_status", "assembled")
    path.write_text(journal(text, "assemble -> " + str(target)), encoding="utf-8")
    sync_tasks(key)
    print("СОБРАНО: " + str(target) + " · фрагментов " + str(len(parts)) + " · импортов " + str(len(imports)) + " · полей " + str(len(fields)))
    print("ЗАГЛУШКИ: " + (", ".join(stubs) or "нет"))
    print("МЕТОДЫ: @BeforeEach %s · @Test · @AfterEach %s" % ("есть" if phases["before"] else "нет", "есть" if phases["after"] else "нет"))
    return 0


# ---------- check ----------

STAND_NAME = re.compile(r"(?i)(?:^|[_.\-/])(ift|psi|uat|preprod|prom|dev)(?:$|[_.\-/])")
LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')
MATCHER_PATH = re.compile(r"\b(?:have|notHave)\w*\(\s*\"([^\"]+)\"")
SHOULD = re.compile(r"^\s*(.+?)\.should\w*\(")
CONST_DEF = re.compile(r"static\s+final\s+([\w<>\[\], ?]+?)\s+([A-Z][A-Z0-9_]*)\s*=\s*(.+?);")
MATCHER_CONST = re.compile(r"\b(?:have|notHave)\w*\(\s*([A-Z][A-Z0-9_]*)\b")
EXPRESSION_FIELD = re.compile(r"^\s*\$?\.?([A-Za-z_][\w.\[\]]*)\s*(?:[!=<>]=?|>|<)")
STD_HEADERS = {"content-type", "accept", "content-length", "host", "user-agent", "accept-encoding", "connection", "accept-charset"}


def code_lines(lines):
    """(номер, строка) без комментариев, import и package."""
    skip = set()
    in_block = False
    for number, line in enumerate(lines, 1):
        t = line.strip()
        if t.startswith("/*"):
            in_block = True
        if in_block or t.startswith("//") or t.startswith("*") or t.startswith("import ") or t.startswith("package "):
            skip.add(number)
        if "*/" in t:
            in_block = False
    return [(n, re.sub(r"\s//.*$", "", l)) for n, l in enumerate(lines, 1) if n not in skip]


def file_constants(lines):
    """{ИМЯ: (тип, значение без кавычек)} констант static final файла."""
    out = {}
    for _, line in code_lines(lines):
        m = CONST_DEF.search(line)
        if m:
            value = m.group(3).strip()
            out[m.group(2)] = (m.group(1).strip(), value[1:-1] if value.startswith('"') and value.endswith('"') else value)
    return out


def checked_fields(line, consts):
    """Поля, которые проверяет строка: путь в matcher литералом или константой; выражение «code != 0» -> code."""
    fields = MATCHER_PATH.findall(line) + [consts[n][1] for n in MATCHER_CONST.findall(line) if n in consts]
    result = []
    for f in fields:
        m = EXPRESSION_FIELD.match(f)
        result.append(m.group(1) if m else f)
    return result


def repeated_checks(path, lines):
    """Одно поле одного объекта проверено дважды (и значением, и выражением по тому же полю) -> ПОВТОР."""
    found, seen, receiver = [], {}, ""
    consts = file_constants(lines)
    for number, line in code_lines(lines):
        m = SHOULD.match(line)
        if m:
            receiver = re.sub(r"\s+", "", m.group(1))
        for field in checked_fields(line, consts):
            key = (receiver, field)
            if key in seen:
                found.append("ПОВТОР %s:%d - поле «%s» у «%s» уже проверено в строке %d: оставь одну проверку, повторный шаг ТК -"
                             " только комментарий «// Шаг <n>: ... - проверено в шаге <m>»" % (path, number, field, receiver, seen[key]))
            else:
                seen[key] = number
    return found


def value_names(path, lines):
    """Константа названа по значению (EXPECTED_38_00, EXPECTED_513438364090) -> ИМЯ."""
    found = []
    for number, line in code_lines(lines):
        m = re.search(r"static\s+final\s+[\w<>\[\], ?]+\s+([A-Z][A-Z0-9_]*)\s*=\s*(.+);", line)
        if not m:
            continue
        name, value = m.group(1), m.group(2)
        literal = re.sub(r"[^A-Za-z0-9]", "", "".join(LITERAL.findall(value)) or value).upper()
        tail = re.search(r"_([0-9]+)$", name)
        if re.fullmatch(r"[A-Z]+_[0-9_]+", name) or (len(literal) >= 4 and literal in name.replace("_", "")) \
                or (tail and tail.group(1) == literal):
            found.append("ИМЯ %s:%d - константа %s названа по значению: назови по полю или смыслу (EXPECTED_ACC_STATE)" % (path, number, name))
    return found


def stand_names(path, lines):
    found = []
    for number, line in code_lines(lines):
        for lit in LITERAL.findall(line):
            if STAND_NAME.search(lit) and not lit.endswith((".json", ".sql", ".properties")):
                found.append("СТЕНД %s:%d - имя стенда в «%s»: стенд выбирается в настройках (app.properties), в коде и алиасах его нет" % (path, number, lit))
    return found


def run_literals(path, lines, values):
    found = []
    for number, line in code_lines(lines):
        for v in values:
            if re.search(r"(?<![\w.])" + re.escape(v[0]) + r"(?![\w]|\.\d)", line):
                found.append("ЛИТЕРАЛ %s:%d - значение %s из выборки шага %s (поле %s): в коде - переменная %s, не литерал" % (
                    path, number, v[0], v[1], v[2], v[4]))
    return found


def one_use_constants(path, lines, plan_values):
    """Строковая константа, которая в файле используется один раз и не взята из раздела 4 плана (данные ТК) -> РАЗОВАЯ."""
    found, text = [], "\n".join(l for _, l in code_lines(lines))
    for name, (kind, value) in file_constants(lines).items():
        if kind != "String" or value in plan_values or value.startswith("/") or value.endswith((".json", ".sql", ".xml")):
            continue
        if len(re.findall(r"\b" + name + r"\b", text)) <= 2:  # объявление + одно использование
            found.append("РАЗОВАЯ %s - константа %s = \"%s\" используется один раз и это не данные ТК: впиши значение на месте"
                         " вызова, константу удали" % (path, name, value))
    return found


def expected_in_steps(path, lines, plan_expected):
    """Ожидаемое значение ТК объявлено в классе шагов -> ОЖИДАЕМОЕ (приходит параметром из теста)."""
    found = []
    for name, (_, value) in file_constants(lines).items():
        if name.startswith("EXPECTED_") or value in plan_expected:
            found.append("ОЖИДАЕМОЕ %s - %s = %s в классе шагов: ожидаемое значение ТК объявляется в тест-классе и"
                         " передаётся в метод шага параметром" % (path, name, value))
    return found


def unused_methods(files):
    """public-методы классов шагов из этой генерации, которые нигде в тестах проекта не вызываются -> НЕ ИСПОЛЬЗУЕТСЯ."""
    texts = {}
    for p in list(Path(".").glob("**/src/test/java/**/*.java")) + [Path(f) for f in files]:
        if "target" not in p.parts and "build" not in p.parts:
            texts[str(p.resolve())] = read(p)
    found = []
    for f in files:
        text = read(f)
        if re.search(r"@(Test|ParameterizedTest)\b", text):
            continue
        for m in re.finditer(r"(?m)^\s*public\s+(?:static\s+)?[\w<>\[\], ?]+\s+([a-z]\w*)\s*\(", text):
            name = m.group(1)
            calls = sum(len(re.findall(r"\b" + name + r"\s*\(", t)) for t in texts.values())
            if calls <= 1:
                found.append("НЕ ИСПОЛЬЗУЕТСЯ %s - метод %s() нигде не вызывается: удали его" % (f, name))
    return found


def artifact_checks(key, text, target, step_files):
    """Проверки по описи артефактов и правилам набора: повтор, имена констант, стенд, литералы выборки,
    заголовки запросов, неиспользуемые методы."""
    findings = []
    files = [str(target)] + [f for f in sorted(step_files) if Path(f).is_file()]
    resources = set()
    for f in files:
        for lit in LITERAL.findall(read(f)):
            if lit.endswith(".json"):
                for found in Path(".").glob("**/src/test/resources/" + lit.lstrip("/")):
                    resources.add(str(found))
    values = [v for v in section_rows(text, "10. Значения из выборки") if len(v) >= 5 and v[0] != "-"]
    plan_consts = [c for c in section_rows(text, "4. Константы") if len(c) >= 2 and c[0] != "-"]
    plan_values = {c[1] for c in plan_consts}
    plan_expected = {c[1] for c in plan_consts if c[0].startswith("EXPECTED_")}
    for f in files:
        lines = read(f).splitlines()
        findings += repeated_checks(f, lines) + one_use_constants(f, lines, plan_values)
        if f != str(target):
            findings += expected_in_steps(f, lines, plan_expected)
        findings += value_names(f, lines) + stand_names(f, lines) + run_literals(f, lines, values)
    for f in sorted(resources):
        findings += run_literals(f, read(f).splitlines(), values)
    blob = "\n".join(read(f) for f in files + sorted(resources)).lower()
    for r in section_rows(text, "9. Запросы из артефактов"):
        if len(r) < 5 or r[1] == "-":
            continue
        for name in [h.split("=", 1)[0].strip() for h in r[4].split(",") if "=" in h]:
            if name and name.lower() not in STD_HEADERS and name.lower() not in blob:
                findings.append("ЗАГОЛОВОК шаг %s - заголовка «%s» запроса %s (%s %s) нет в коде: перенеси все заголовки из"
                                " описи артефактов" % (r[0], name, r[1], r[2], r[3]))
    code_blob = "\n".join(read(f) for f in files)
    for r in section_rows(text, "9. Запросы из артефактов"):
        if len(r) >= 6 and r[1] != "-" and r[5] not in ("-", "") and r[2].upper() in ("POST", "PUT", "PATCH") \
                and not re.search(r"\.body\s*\(", code_blob):
            findings.append("ТЕЛО шаг %s - у запроса %s (%s %s) в артефактах есть тело (%s), а в коде запроса нет .body(...):"
                            " отправь тело из файла данных" % (r[0], r[1], r[2], r[3], r[5]))
    findings += unused_methods([f for f in files if f != str(target)])
    return findings

def plan_checks(text, target, step_files):
    """Код против разделов 11-14 плана: файлы, методы, проверки, настройки. План - договор, код от него не отходит."""
    findings = []
    files = [r for r in section_rows(text, "11. Файлы") if len(r) >= 4 and r[0] != "-"]
    if not files:
        return findings  # план старого формата: разделов 11-14 нет
    planned = {r[0] for r in files}
    for f in sorted(step_files):
        if f not in planned:
            findings.append("ВНЕ ПЛАНА %s - файла нет в разделе 11 плана: код только в файлах плана (новый файл - сначала"
                            " правка плана и подтверждение человека)" % f)
    by_stem = {Path(r[0]).stem: r for r in files if r[0].endswith(".java")}
    methods = [m for m in section_rows(text, "12. Методы шагов") if len(m) >= 6 and m[0] != "-"]
    for m in methods:
        row = by_stem.get(m[1])
        if row and Path(row[0]).is_file() and not re.search(r"\b" + re.escape(m[2]) + r"\s*\(", read(row[0])):
            findings.append("МЕТОД НЕТ %s - метода %s() из раздела 12 (шаги %s) нет в классе" % (row[0], m[2], m[3]))
    for r in files:
        if r[1] == "создать" and r[0].endswith(".java") and r[0] != str(target) and Path(r[0]).is_file():
            names = {m[2] for m in methods if m[1] == Path(r[0]).stem}
            for name in re.findall(r"(?m)^\s*public\s+(?:static\s+)?[\w<>\[\], ?]+\s+([a-z]\w*)\s*\(", read(r[0])):
                if name not in names:
                    findings.append("МЕТОД ВНЕ ПЛАНА %s - public-метода %s() нет в разделе 12 плана" % (r[0], name))
    code_fields = set()
    for f in [str(target)] + sorted(step_files):
        if Path(f).is_file():
            lines = read(f).splitlines()
            consts = file_constants(lines)
            for _, line in code_lines(lines):
                code_fields.update(x.lower() for x in checked_fields(line, consts))
    plan_fields = set()
    for c in section_rows(text, "13. Проверки"):
        if len(c) < 5 or c[0] == "-" or c[3].startswith(("проверено в шаге", "статус")):
            continue
        field = c[2].strip("`").lstrip("$.").lower()
        plan_fields.add(field)
        if field not in code_fields:
            findings.append("ПРОВЕРКА НЕТ шаг %s - поле «%s» (%s %s) из раздела 13 в коде не проверяется" % (c[0], c[2], c[3], c[4]))
    for field in sorted(code_fields - plan_fields):
        findings.append("ПРОВЕРКА ВНЕ ПЛАНА - поле «%s» проверяется в коде, а в разделе 13 плана его нет: убери проверку или"
                        " добавь строку в план с подтверждением человека" % field)
    for st in section_rows(text, "14. Настройки"):
        if len(st) >= 4 and st[0] != "-" and Path(st[1]).is_file() and not re.search(r"(?m)^\s*" + re.escape(st[0]) + r"\s*[=:]", read(st[1])):
            findings.append("НАСТРОЙКА НЕТ %s - ключа %s из раздела 14 в файле нет" % (st[1], st[0]))
    return findings


def cmd_check(key, compile_on):
    path, text, head = plan(key)
    if text is None:
        return fail("НЕТ ПЛАНА (design.md изменения)")
    target = Path(head.get("test_file", "-"))
    if not target.is_file():
        return fail("НЕТ ТЕСТ-КЛАССА " + str(target) + " - сначала assemble")
    findings = []
    lines = read(target).splitlines()
    findings += scan(str(target), lines, CHECKS + TEST_ONLY)
    if head.get("package", "-") not in read(target).split("\n", 1)[0]:
        findings.append("ПАКЕТ %s - первая строка не package %s" % (target, head.get("package")))
    steps_files = set()
    for frag in sorted((folder(key) / "fragments").glob("G-*.md")):
        for item in re.findall(r"`?([\w./\\-]+\.(?:java|kt))`?", fragment(frag)["files"]):
            steps_files.add(item)
    for item in sorted(steps_files):
        if Path(item).is_file():
            findings += scan(item, read(item).splitlines(), CHECKS)
        else:
            findings.append("ФАЙЛ %s - назван во фрагменте, но его нет" % item)
    findings += artifact_checks(key, text, target, steps_files)
    findings += plan_checks(text, target, steps_files)
    body = read(target)
    for row in section_rows(text, "2. Шаги"):
        if not re.search(r"//\s*Шаг\s+" + re.escape(row[0]) + r"(?=\s|:|$)", body, re.M):
            findings.append("ПОКРЫТИЕ шаг %s - в тест-методе нет комментария «// Шаг %s: ...»: шаг не сгенерирован" % (row[0], row[0]))
    status, details = ("skipped", ["--no-compile"]) if not compile_on else compile_project(540)
    if status == "failed":
        findings += ["КОМПИЛЯЦИЯ " + d for d in details]
    report = ["# Проверка автотеста " + key, "", "- Тест-класс: " + str(target), "- Компиляция: " + status,
              "- Находок: " + str(len(findings)), "", "| Находка |", "|---------|"]
    report += ["| " + f.replace("|", "\\|") + " |" for f in findings] or ["| нет |"]
    (folder(key) / "CHECK.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    for f in findings:
        print(f)
    print("КОМПИЛЯЦИЯ: " + status + (" · " + details[0] if details else ""))
    print("ИТОГ: находок " + str(len(findings)) + (" - чисто" if not findings else " - исправь и запусти снова"))
    if not [f for f in findings if not f.startswith("STUB ")] and status in ("ok", "skipped"):
        path.write_text(journal(set_head(text, "plan_status", "checked"), "check -> чисто"), encoding="utf-8")
        print("plan_status: checked")
        sync_tasks(key)
    return 0 if not findings and status in ("ok", "skipped") else 1


# ---------- run / report ----------

RUN_TIMEOUT = 540
STAND = re.compile(r"ConnectException|Connection refused|Connection reset|UnknownHost|NoRouteToHost|No route to host|"
                   r"SocketTimeout|Read timed out|connect timed out|SSLHandshake|PKIX path|"
                   r"\b(?:status|code|статус)\D{0,12}(?:401|403|502|503|504)\b", re.I)
CHECK_FAIL = re.compile(r"AssertionError|AssertionFailedError|ComparisonFailure|MultipleFailuresError|SoftAssert", re.I)


def set_or_add_head(text, name, value):
    if re.search(r"(?m)^" + name + r":", text.split("\n---", 1)[0] if text.startswith("---") else ""):
        return set_head(text, name, value)
    return re.sub(r"(?m)^(plan_status:[^\n]*)$", r"\1\n" + name + ": " + value, text, count=1)


def module_of(test_file):
    """Каталог модуля сборки: часть пути тест-класса до src/. Корень проекта -> ''."""
    parts = Path(test_file).parts
    if "src" not in parts:
        return ""
    return "/".join(parts[:parts.index("src")])


def run_argv(env, head):
    """Команда запуска одного тест-класса из команды компиляции ENV.json. Возвращает (argv, отчёты) или (None, причина)."""
    project = env.get("project", {})
    base = project.get("compile_argv") or project.get("compile_command", "-").split()
    if not base or base == ["-"]:
        return None, "нет команды компиляции в ENV.json - запусти env-check"
    base = [shutil.which(base[0]) or base[0]] + list(base[1:])  # Windows: mvn -> полный путь к mvn.cmd
    tool = Path(base[0]).name.lower()
    module = module_of(head.get("test_file", ""))
    fqn = (head.get("package", "-") + "." if head.get("package", "-") != "-" else "") + head.get("class", "")
    root = Path(module) if module else Path(".")
    if "mvn" in tool:
        argv = [base[0], "-B"] + (["-pl", module, "-am"] if module else []) + [
            "test", "-Dtest=" + head.get("class", ""), "-Dsurefire.failIfNoSpecifiedTests=false", "-DfailIfNoTests=false"]
        return argv, [root / "target" / "surefire-reports" / ("TEST-" + fqn + ".xml")]
    if "gradle" in tool:
        task = (":" + module.replace("/", ":") + ":test") if module else "test"
        return [base[0], task, "--tests", fqn], [root / "build" / "test-results" / "test" / ("TEST-" + fqn + ".xml")]
    return None, "сборка не Maven и не Gradle (" + base[0] + ") - команду запуска даст человек"


def kind_of(text):
    if STAND.search(text):
        return "СТЕНД"
    if CHECK_FAIL.search(text):
        return "ПРОВЕРКА"
    return "КОД"


def parse_report(path):
    """JUnit XML -> (счётчики, падения [(метод, вид, сообщение)])."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.parse(str(path)).getroot()
    except (OSError, ET.ParseError):
        return None, []
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    falls = []
    for suite in suites:
        for name in counts:
            try:
                counts[name] += int(suite.get(name, "0"))
            except ValueError:
                pass
        for case in suite.iter("testcase"):
            for bad in list(case.findall("failure")) + list(case.findall("error")):
                body = (bad.get("type", "") + ": " + (bad.get("message") or "") + "\n" + (bad.text or "")).strip()
                first = next((l.strip() for l in body.splitlines() if l.strip()), "-")
                falls.append((case.get("name", "-"), kind_of(body), first[:300]))
    return counts, falls


def report_result(key, path, text, head, reports, since, run_status, command, tail):
    found = [r for r in reports if r.is_file() and r.stat().st_mtime >= since]
    counts, falls = (None, [])
    if found:
        counts, falls = parse_report(found[0])
    if counts is None:
        status = run_status if run_status != "ok" else "no-report"
    else:
        if falls:
            status = "failed"
        elif run_status in ("error", "timeout"):
            status = run_status  # сборка упала или не уложилась: XML мог остаться от прошлого запуска
        else:
            status = "passed" if counts["tests"] > counts["skipped"] else "no-tests"
    lines = ["# Запуск автотеста " + key, "", "- Тест-класс: " + head.get("test_file", "-"),
             "- Команда: " + command, "- Результат: " + status]
    if counts:
        lines.append("- Тестов: %d · упало: %d · пропущено: %d" % (counts["tests"], counts["failures"] + counts["errors"], counts["skipped"]))
    lines += ["", "| Тест-метод | Вид | Сообщение |", "|------------|-----|-----------|"]
    lines += ["| %s | %s | %s |" % (m, k, s.replace("|", "\\|")) for m, k, s in falls] or ["| нет | - | - |"]
    if status in ("no-report", "timeout", "error") and tail:
        lines += ["", "Последние строки вывода:", "", "```"] + tail + ["```"]
    (folder(key) / "RUN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.write_text(journal(set_or_add_head(text, "run_status", status), "run -> " + status), encoding="utf-8")
    print("ЗАПУСК: " + command)
    if counts:
        print("РЕЗУЛЬТАТ: %s · тестов %d · упало %d · пропущено %d" % (status, counts["tests"], counts["failures"] + counts["errors"], counts["skipped"]))
    else:
        print("РЕЗУЛЬТАТ: " + status + " - отчёта " + str(reports[0]) + " нет")
        for line in tail[-15:]:
            print("  " + line)
    for m, k, s in falls:
        print("ПАДЕНИЕ " + m + " " + k + ": " + s)
    print("ОТЧЁТ: " + str(folder(key) / "RUN.md").replace("\\", "/"))
    return 0 if status == "passed" else 1


def cmd_run(key, args):
    import json
    import subprocess
    import time
    path, text, head = plan(key)
    if text is None:
        return fail("НЕТ ПЛАНА (design.md изменения)")
    if head.get("plan_status") != "checked":
        return fail("СНАЧАЛА check: plan_status " + head.get("plan_status", "-") + " - запуск только после чистой проверки", 1)
    if not Path(head.get("test_file", "-")).is_file():
        return fail("НЕТ ТЕСТ-КЛАССА " + head.get("test_file", "-"))
    try:
        env = json.loads(read(pp.env_dir() / "ENV.json") or "{}")
    except ValueError:
        env = {}
    argv, reports = run_argv(env, head)
    if argv is None:
        return fail("НЕЛЬЗЯ ЗАПУСТИТЬ: " + reports, 1)
    command = " ".join(argv)
    env_tc = Path(__file__).resolve().parents[2] / "env-check" / "scripts" / "env_tc.py"
    if env_tc.is_file() and "--dry-run" not in args and "--report-only" not in args:
        checked = subprocess.run([sys.executable, str(env_tc), key, "--no-compile"], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, timeout=120)
        if checked.returncode != 0:
            for line in checked.stdout.decode("utf-8", "replace").splitlines():
                if line.startswith(("НУЖНО", "ОКРУЖЕНИЕ")):
                    print(line)
            return fail("ОКРУЖЕНИЕ НЕ ГОТОВО: тест не запущен - настрой окружение (env-check, режим setup с ключом "
                        + key + "), потом снова run", 1)
    if "--dry-run" in args:
        print("КОМАНДА: " + command)
        print("ОТЧЁТ СБОРКИ: " + str(reports[0]).replace("\\", "/"))
        return 0
    if "--report-only" in args:
        return report_result(key, path, text, head, reports, 0, "no-report", command + " (запускал человек)", [])
    since = time.time() - 1
    try:
        result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=RUN_TIMEOUT)
        output = result.stdout.decode("utf-8", "replace").splitlines()
        run_status = "ok" if result.returncode == 0 else "error"
    except subprocess.TimeoutExpired:
        output, run_status = ["таймаут " + str(RUN_TIMEOUT) + " с"], "timeout"
    except OSError as error:
        output, run_status = [str(error)], "error"
    (folder(key) / "run.log").write_text("\n".join(output[-400:]) + "\n", encoding="utf-8")
    tail = [l for l in output if re.search(r"\bERROR\b|error:|FAILED|Exception", l)][:20] or output[-20:]
    return report_result(key, path, text, head, reports, since, run_status, command, tail)


def main(args):
    if len(args) < 2 or args[0] not in ("rules", "next", "mark", "compile", "assemble", "check", "run"):
        print("Использование: at_tools.py rules|next|assemble|check|run <ключ ТК> | mark <ключ ТК> <G-n> <статус>"
              " | compile <ключ ТК> <G-n>")
        return 2
    if args[0] == "compile":
        return cmd_compile(args[1], args[2]) if len(args) >= 3 else fail("compile <ключ ТК> <G-n>")
    if args[0] == "mark":
        return cmd_mark(args[1], args[2], args[3]) if len(args) >= 4 else fail("mark <ключ ТК> <G-n> <статус>")
    if args[0] == "check":
        return cmd_check(args[1], "--no-compile" not in args)
    if args[0] == "run":
        return cmd_run(args[1], args[2:])
    return {"rules": cmd_rules, "next": cmd_next, "assemble": cmd_assemble}[args[0]](args[1])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
