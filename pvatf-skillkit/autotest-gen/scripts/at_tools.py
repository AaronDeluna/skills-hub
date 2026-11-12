#!/usr/bin/env python3
"""Инструменты генерации автотеста по плану (скилл autotest-gen). Запуск из корня проекта:

  python3 <скилл>/scripts/at_tools.py rules <ключ ТК>              - правила кода и конспект в rules-now.md, docs-now.md
  python3 <скилл>/scripts/at_tools.py next <ключ ТК>               - задание агенту pvatf-generator на следующий G
  python3 <скилл>/scripts/at_tools.py mark <ключ ТК> <G-n> <статус> - статус G в плане: ok / stub / blocked / todo
  python3 <скилл>/scripts/at_tools.py assemble <ключ ТК>           - собрать тест-класс из фрагментов
  python3 <скилл>/scripts/at_tools.py check <ключ ТК> [--no-compile] - самопроверка кода, покрытие шагов, компиляция

Файлы - в .gigacode/data/autotest/<ключ>/: PLAN.md (план), fragments/G-<n>.md (фрагменты от
агента), rules-now.md, docs-now.md, CHECK.md (итог проверки). Повторный запуск любой команды
ничего не ломает: assemble переписывает только файл, который сам создал (есть строка-метка).
Python 3.8+, только стандартная библиотека. Код выхода: 0 - выполнено / чисто, 1 - есть
находки или нечего делать, 2 - неверные аргументы или нет файлов.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from java_checks import CHECKS, TEST_ONLY, compile_project, scan  # noqa: E402 - общий модуль набора

DATA = Path(".gigacode") / "data" / "autotest"
SKILL = Path(__file__).resolve().parent.parent
NOTE_DIRS = [Path(".gigacode") / "data" / "doc-notes", Path(".gigacode") / "data" / "migration" / "doc-notes"]
MARK = "// Сгенерировано autotest-gen по тест-кейсу "
GEN_RULES = ["MR-1", "MR-2", "MR-3", "MR-4", "MR-5", "MR-8", "MR-12", "MR-13", "MR-14", "MR-15", "MR-19", "MR-20",
             "MR-21", "MR-22", "MR-29", "MR-48", "MR-41", "MR-43", "MR-42", "MR-30", "MR-49", "MR-50", "MR-33", "MR-34",
             "MR-35", "MR-46", "MR-47", "MR-37", "MR-38", "MR-39", "MR-40", "MR-45"]
STATUSES = ("todo", "ok", "stub", "blocked")
GLOSSARY = """Правила общие с миграцией. При генерации автотеста слова в них значат:
- «карточка», «юнит», «подшаг» - задание агенту на один G и план PLAN.md;
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
    return DATA / key


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
        if cells and not set(cells[0]) <= set("-:") and cells[0] not in ("Шаг", "G", "Имя"):
            rows.append(cells)
    return rows


def journal(text, what):
    return text.rstrip("\n") + "\n| at_tools | " + what + " |\n"


def plan(key):
    path = folder(key) / "PLAN.md"
    text = read(path)
    if not text:
        return None, None, None
    head = head_of(text)
    return path, text, head


# ---------- rules ----------

def cmd_rules(key):
    path, text, head = plan(key)
    if text is None:
        return fail("НЕТ PLAN.md: сначала autotest-plan")
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
        return fail("НЕТ PLAN.md: сначала autotest-plan")
    if head.get("plan_status") not in ("planned", "generating"):
        return fail("plan_status " + head.get("plan_status", "-") + " - генерация только по плану planned или generating", 1)
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
    classes = [l[2:] for l in text.split("\n") if l.startswith("- " + g[2] + " · `")]
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
    lines.append("- Константы этого G (имя - значение - источник - форма):")
    lines += ["  - " + c[0] + " - " + c[1] + " - " + c[2] + " - " + c[3] for c in consts] or ["  - нет"]
    lines.append("- Переменные теста (имя - шаг - откуда):")
    lines += ["  - " + v[0] + " - " + v[1] + " - " + v[2] for v in variables] or ["  - нет"]
    lines.append("- Готовые фрагменты прошлых G (их переменные доступны): " + (", ".join(
        p.stem for p in sorted((folder(key) / "fragments").glob("G-*.md"))) or "нет"))
    lines.append("- Классы шагов проекта для этой технологии (переиспользуй, если подходят):")
    lines += ["  - " + c for c in classes] or ["  - нет"]
    print("\n".join(lines))
    return 0


def cmd_mark(key, gid, status):
    path, text, head = plan(key)
    if text is None:
        return fail("НЕТ PLAN.md")
    if status not in STATUSES:
        return fail("статус - один из: " + ", ".join(STATUSES))
    pattern = re.compile(r"(?m)^(\| " + re.escape(gid) + r" \|(?:[^|\n]*\|){6}) *\w+ *\|$")
    if not pattern.search(text):
        return fail("в разделе 3 плана нет строки " + gid, 1)
    frag = folder(key) / "fragments" / (gid + ".md")
    if status == "ok" and not frag.is_file():
        return fail("нет фрагмента fragments/" + gid + ".md - агент его не записал; статус не меняю", 1)
    if status == "stub" and not frag.is_file():
        frag.parent.mkdir(parents=True, exist_ok=True)
        frag.write_text("# " + gid + "\n\n- Статус: stub\n- Файлы шагов: -\n\n## imports\n```java\n```\n\n"
                        "## fields\n```java\n```\n\n## body\n```java\n// STUB " + gid
                        + ": фрагмент не получен, шаг дописать вручную\n```\n", encoding="utf-8")
    text = pattern.sub(lambda m: m.group(1) + " " + status + " |", text, count=1)
    if head.get("plan_status") == "planned" or (status == "todo" and head.get("plan_status") in ("assembled", "checked")):
        text = set_head(text, "plan_status", "generating")
    path.write_text(journal(text, gid + " -> " + status), encoding="utf-8")
    left = [g[0] for g in section_rows(text, "3. Порядок генерации") if len(g) >= 8 and g[7] == "todo"]
    print("ОТМЕЧЕНО: " + gid + " " + status + " · осталось todo: " + (", ".join(left) or "нет - дальше assemble"))
    return 0


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


def cmd_assemble(key):
    path, text, head = plan(key)
    if text is None:
        return fail("НЕТ PLAN.md")
    gens = section_rows(text, "3. Порядок генерации")
    not_ready = [g[0] + " " + g[7] for g in gens if len(g) >= 8 and g[7] not in ("ok", "stub")]
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
    for extra in ("import io.qameta.allure.TmsLink;", "import org.junit.jupiter.api.DisplayName;", "import org.junit.jupiter.api.Test;"):
        if extra not in imports:
            imports.append(extra)
    name = head["class"]
    method = name[0].lower() + name[1:-4] if name.endswith("Test") and len(name) > 4 else "scenario"
    base = head.get("base_class", "-")
    out = ["package " + head["package"] + ";", ""] + sorted(imports) + ["", MARK + key,
           "public class " + name + (" extends " + base if base not in ("", "-") else "") + " {", ""]
    out += ["    " + f for f in fields] + ([""] if fields else [])
    out += ["    @Test", "    @TmsLink(\"" + key + "\")",
            "    @DisplayName(\"[" + key + "] " + title.replace("\\", "\\\\").replace("\"", "\\\"") + "\")",
            "    void " + method + "() {"]
    for index, p in enumerate(parts):
        if index:
            out.append("")
        out += [("        " + l if l.strip() else "") for l in p["body"].split("\n")]
    out += ["    }", "}", ""]
    target = Path(head["test_file"])
    if target.is_file() and MARK + key not in read(target):
        return fail("ФАЙЛ ЕСТЬ: " + str(target) + " создан не autotest-gen - не перезаписываю; поменяй class в плане", 1)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(out), encoding="utf-8")
    stubs = [g[0] for g, p in zip(gens, parts) if p["status"] != "ok" or not p["body"].strip() or re.search(r"//\s*STUB\b", p["body"])]
    text = set_head(text, "plan_status", "assembled")
    path.write_text(journal(text, "assemble -> " + str(target)), encoding="utf-8")
    print("СОБРАНО: " + str(target) + " · фрагментов " + str(len(parts)) + " · импортов " + str(len(imports)) + " · полей " + str(len(fields)))
    print("ЗАГЛУШКИ: " + (", ".join(stubs) or "нет"))
    return 0


# ---------- check ----------

def cmd_check(key, compile_on):
    path, text, head = plan(key)
    if text is None:
        return fail("НЕТ PLAN.md")
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
    body = read(target)
    for row in section_rows(text, "2. Шаги"):
        number = row[0].split(".")[0]
        if not re.search(r"//\s*Шаг\s+" + re.escape(row[0]) + r"\b|//\s*Шаг\s+" + re.escape(number) + r"\b", body):
            findings.append("ПОКРЫТИЕ шаг %s - в тест-методе нет комментария «// Шаг %s: ...»: шаг не сгенерирован" % (row[0], row[0]))
    status, details = ("skipped", ["--no-compile"]) if not compile_on else compile_project(900)
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
    if not findings and status == "ok":
        path.write_text(journal(set_head(text, "plan_status", "checked"), "check -> чисто"), encoding="utf-8")
        print("plan_status: checked")
    return 0 if not findings and status in ("ok", "skipped") else 1


def main(args):
    if len(args) < 2 or args[0] not in ("rules", "next", "mark", "assemble", "check"):
        print("Использование: at_tools.py rules|next|assemble|check <ключ ТК> | mark <ключ ТК> <G-n> <статус>")
        return 2
    if args[0] == "mark":
        return cmd_mark(args[1], args[2], args[3]) if len(args) >= 4 else fail("mark <ключ ТК> <G-n> <статус>")
    if args[0] == "check":
        return cmd_check(args[1], "--no-compile" not in args)
    return {"rules": cmd_rules, "next": cmd_next, "assemble": cmd_assemble}[args[0]](args[1])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
