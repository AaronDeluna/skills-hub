#!/usr/bin/env python3
"""Проверка и оптимизация существующего автотеста (скилл autotest-review). Запуск из корня проекта:

  python3 <скилл>/scripts/review.py find <файл теста>                 - находки и план правок REVIEW-PLAN.md
  python3 <скилл>/scripts/review.py approve <файл> all|none|R-1,R-3 [--target-only] - какие правки делать
  python3 <скилл>/scripts/review.py start <файл> [--no-compile]       - компиляция до правок, копия, правки скрипта
  python3 <скилл>/scripts/review.py next <файл>                       - задание агенту pvatf-generator на следующую правку
  python3 <скилл>/scripts/review.py mark <файл> <R-n> <статус>         - статус правки: done / failed / blocked
  python3 <скилл>/scripts/review.py check <файл> [--no-compile]       - проверка после правок, компиляция, REVIEW.md
  python3 <скилл>/scripts/review.py rollback <файл>                   - вернуть все файлы к копии до правок

Файлы - в .gigacode/data/autotest-review/<имя класса>/: REVIEW-PLAN.md (план и статусы),
backup/ (копия исходников до правок), rules-now.md, docs-now.md, REVIEW.md (итог).
Повторный запуск любой команды ничего не ломает. Python 3.8+, только стандартная библиотека.
Код выхода: 0 - выполнено, 1 - есть находки или нельзя по состоянию, 2 - неверные аргументы.
"""
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from java_checks import CHECKS, TEST_ONLY, compile_project, read, scan_items  # noqa: E402 - общий модуль набора

DATA = Path(".gigacode") / "data" / "autotest-review"
SKILL = Path(__file__).resolve().parent.parent
NOTE_DIRS = [Path(".gigacode") / "data" / "doc-notes", Path(".gigacode") / "data" / "migration" / "doc-notes"]
SKIP_DIRS = {".git", ".gigacode", ".idea", "target", "build", "out", "node_modules", ".gradle"}
REVIEW_STATUSES = ("found", "approved", "fixing", "checked", "rolled-back")
ITEM_STATUSES = ("todo", "approved", "skipped", "done", "failed", "blocked")
DUP_LINES = 5            # MR-39: блок из 5 и более строк
SHARED_FILES = 2         # литерал ещё в 2 и более других тестах -> общий класс констант
COMPILE_TIMEOUT = 900
MAX_ROUNDS = 3           # кругов check -> исправление; после - rollback
# правила кода для агента при правках (выписывает start в rules-now.md)
REVIEW_RULES = ["MR-1", "MR-2", "MR-4", "MR-5", "MR-7", "MR-9", "MR-10", "MR-11", "MR-12", "MR-13", "MR-14", "MR-15",
                "MR-18", "MR-19", "MR-21", "MR-22", "MR-29", "MR-33", "MR-39", "MR-40", "MR-41", "MR-42", "MR-43",
                "MR-45", "MR-47", "MR-48"]
# находки правил, которые правит агент; остальные - только в отчёт человеку
AGENT_RULES = {"MR-4", "MR-14", "MR-15", "MR-29", "MR-33", "MR-41", "MR-42", "MR-43", "MR-45", "MR-47", "MR-48"}
EXTRA = [
    ("SQL", r"\"[^\"]*\b(SELECT|INSERT|UPDATE|DELETE|WHERE)\b[^\"]*\"\s*\+|\+\s*\"[^\"]*\b(WHERE|AND|OR|VALUES|SET)\b", "SQL собирается склейкой строк - параметры запроса"),
    ("MR-22", r"catch\s*\([^)]*\)\s*\{\s*\}", "пустой catch глушит ошибку"),
    ("DISABLED", r"@(Disabled|Ignore)\s*(\(\s*\))?\s*$", "тест отключён без причины"),
    ("STATIC-STATE", r"^\s*(private |protected |public )?static (?!final)[A-Za-z<>\[\], .]+ [a-z][A-Za-z0-9]* *(=|;)", "изменяемое static-поле - состояние между тестами"),
]
GLOSSARY = """Правила общие с миграцией. При проверке существующего автотеста слова в них значат:
- «карточка», «юнит», «подшаг» - одна правка R-n из задания;
- «Файлы юнита» - тест-класс из задания и файлы, которые называет правка; другие файлы не меняешь;
- «Таблица подтверждений», «конспект» - docs-now.md (записи D-<tech>-<n>);
- «Входящие», «решить человеку» - строка «Причина» ответа со статусом blocked;
- «старый код», «legacy», «удаляется» - к проверке не относится: ничего не удаляешь, кроме кода,
  который правка переносит в другое место.

"""
TEMPLATE_REPORT = """# Проверка автотеста {cls}

- Файл: {file}
- Статус: {status}
- Компиляция до правок: {before}
- Компиляция после правок: {after}
- Правки: сделано {done} · не сделано {failed} · пропущено {skipped} · человеку {human}

## Правки

| R | Тип | Где | Что сделано | Статус |
|---|-----|-----|-------------|--------|
{rows}

## Изменённые файлы

{changed}

## Зависимые тесты

{dependents}

## Осталось человеку

{left}
"""


def fail(message, code=2):
    print(message)
    return code


def norm(path):
    return Path(path).as_posix().lstrip("./") if not Path(path).is_absolute() else Path(path).as_posix()


def folder(target):
    return DATA / Path(target).stem


def head_of(text):
    body = text[4:] if text.startswith("---\n") else text
    return dict(re.findall(r"(?m)^(\w+):[ \t]*(.*)$", body.split("\n---", 1)[0]))


def set_head(text, name, value):
    return re.sub(r"(?m)^" + name + r":[ \t]*.*$", name + ": " + value, text, count=1)


def journal(text, what):
    return text.rstrip("\n") + "\n| review | " + what + " |\n"


def esc(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def rows_of(text, title):
    sect = re.search(r"(?ms)^## " + re.escape(title) + r"\s*\n(.*?)(?=^## |\Z)", text)
    rows = []
    for line in (sect.group(1) if sect else "").split("\n"):
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if cells and not set(cells[0]) <= set("-:") and cells[0] != "R":
            rows.append(cells)
    return rows


def load(target):
    path = folder(target) / "REVIEW-PLAN.md"
    text = read(path)
    return (path, text, head_of(text)) if text else (path, None, {})


# ---------- поиск по проекту ----------

def walk(root, suffixes):
    for path in sorted(Path(root).rglob("*")):
        if path.is_file() and path.suffix in suffixes and not (set(path.parts) & SKIP_DIRS):
            yield path


def test_files():
    return [p for p in walk(".", {".java"}) if "/src/test/" in "/" + p.as_posix() and "@Test" in read(p)]


def source_roots():
    roots = set()
    for path in Path(".").rglob("src"):
        if path.is_dir() and not (set(path.parts) & SKIP_DIRS):
            roots.add(path)
    return sorted(roots)


# ---------- литералы и константы ----------

STRING = re.compile(r'"(?:[^"\\\n]|\\.)*"')
NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?[LlDdFf]?(?![\w.])")


def segments(line):
    """Строка кода -> [(код | строка, текст)] без строк внутри строк."""
    out, pos = [], 0
    for m in STRING.finditer(line):
        out.append(("code", line[pos:m.start()]))
        out.append(("str", m.group()))
        pos = m.end()
    out.append(("code", line[pos:]))
    return out


def literal_lines(lines):
    """Номера строк, где литералы оставляем как есть: комментарии, аннотации, объявления констант,
    имена шагов FlowRunner и @Step, package/import."""
    skip, in_block = set(), False
    for number, line in enumerate(lines, 1):
        t = line.strip()
        if t.startswith("/*"):
            in_block = True
        if (in_block or t.startswith("//") or t.startswith("*") or t.startswith("@") or t.startswith("import ")
                or t.startswith("package ") or re.search(r"\bstatic\s+final\b", t)):
            skip.add(number)
        if "*/" in t:
            in_block = False
    return skip


def class_body_start(lines):
    for number, line in enumerate(lines, 1):
        if re.search(r"\b(class|interface|enum)\s+[A-Z]\w*", line) and "{" in line:
            return number
    return 0


def literals(lines):
    """{литерал: [номера строк]} в коде тест-класса, без строк из literal_lines."""
    found, skip, start = {}, literal_lines(lines), class_body_start(lines)
    for number, line in enumerate(lines, 1):
        if number <= start or number in skip:
            continue
        code = re.sub(r"\.step\(\s*\"(?:[^\"\\]|\\.)*\"", ".step(", line)
        for kind, part in segments(code):
            if kind == "str":
                if len(part) > 3:
                    found.setdefault(part, []).append(number)
            else:
                for m in NUMBER.finditer(part):
                    if m.group().lstrip("-") not in ("0", "1"):
                        found.setdefault(m.group(), []).append(number)
    return found


def upper_snake(text):
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    words = [w for w in re.split(r"[^A-Za-z0-9]+", text) if w][:4]
    name = "_".join(words).upper()
    return name if name and not name[0].isdigit() else ""


def const_type(literal):
    if literal.startswith('"'):
        return "String"
    if literal[-1] in "Ll":
        return "long"
    if literal[-1] in "Ff":
        return "float"
    if literal[-1] in "Dd" or "." in literal:
        return "double"
    return "int"


def const_name(literal, line):
    """Имя константы по правилу references/review-rules.md, раздел «Имя константы»; "" - имя даёт агент."""
    m = re.search(r"\b([a-z][A-Za-z0-9]*)\s*=\s*" + re.escape(literal) + r"\s*;", line)
    if m:
        return upper_snake(m.group(1))
    value = literal[1:-1] if literal.startswith('"') else ""
    if value and re.fullmatch(r"[A-Za-z][A-Za-z0-9 ._/-]{0,40}", value):
        return upper_snake(value)
    before = line[:line.find(literal)]
    call = re.findall(r"\b([a-z][A-Za-z0-9]*)\s*\([^()]*$", before)
    if call:
        name = re.sub(r"^(with|set|get|by|for|send|add|put|select|check|should)(?=[A-Z])", "", call[-1])
        snake = upper_snake(name)
        return snake if snake else ""
    return ""


# ---------- дубли ----------

def windows(lines, skip):
    """{нормализованный блок из DUP_LINES строк кода: [первые строки]}."""
    code = [(n, re.sub(r"\s+", " ", l.strip())) for n, l in enumerate(lines, 1)
            if l.strip() and n not in skip and l.strip() not in ("{", "}", "});", ");")]
    out = {}
    for i in range(len(code) - DUP_LINES + 1):
        block = "\n".join(c for _, c in code[i:i + DUP_LINES])
        if any(c.startswith("@") or re.match(r"(public|private|protected|void)\b", c) for _, c in code[i:i + DUP_LINES]):
            continue
        out.setdefault(block, []).append(code[i][0])
    return out


# ---------- find ----------

def cmd_find(target):
    target = Path(target)
    if not target.is_file() or target.suffix != ".java":
        return fail("НЕТ ФАЙЛА: " + str(target) + " - нужен путь к .java тест-классу от корня проекта")
    text = read(target)
    if "@Test" not in text:
        return fail("НЕ ТЕСТ: в " + str(target) + " нет @Test - проверяются только тест-классы", 1)
    path, old, head = load(target)
    if old is not None and head.get("review_status") == "fixing":
        return fail("ПРАВКИ ИДУТ: review_status fixing - сначала check или rollback", 1)
    lines = text.splitlines()
    rel = norm(target)
    others = [p for p in test_files() if p.resolve() != target.resolve()]
    other_text = {norm(p): read(p) for p in others}
    items = []

    def add(kind, where, what, who, deps="-"):
        items.append(["R-" + str(len(items) + 1), kind, where, what, who, deps, "todo"])

    rule_lines = set()
    for rule, number, message, code in scan_items(lines, CHECKS + TEST_ONLY + EXTRA):
        rule_lines.add(number)
        who = "agent" if rule in AGENT_RULES or rule in ("SQL", "MR-22") else "human"
        add(rule, rel + ":" + str(number), message + ": `" + code + "`", who)
    for number, line in enumerate(lines, 1):
        if re.match(r"\s*@Test\b", line):
            block = "\n".join(lines[max(0, number - 8):number + 4])
            missing = [a for a in ("@TmsLink", "@DisplayName") if a not in block]
            if missing:
                add("MARKUP", rel + ":" + str(number), "у теста нет " + ", ".join(missing) + " - разметка тестов", "human")
    taken = set(re.findall(r"\b[A-Z][A-Z0-9_]*\b", text))
    for literal, where in sorted(literals(lines).items(), key=lambda kv: kv[1][0]):
        where = [n for n in where if n not in rule_lines]  # строку и так перепишет правка правила
        if not where:
            continue
        shared = [f for f, body in other_text.items() if literal in body]
        is_number = not literal.startswith('"')
        if not (len(where) >= 2 or is_number or re.search(r"\d", literal) or len(shared) >= SHARED_FILES):
            continue
        name = const_name(literal, lines[where[0] - 1])
        if name and name in taken:
            name = ""
        if name:
            taken.add(name)
        place = rel + ":" + ",".join(str(n) for n in where)
        if len(shared) >= SHARED_FILES:
            add("SHARED-CONST", place, "литерал " + literal + " есть ещё в " + str(len(shared))
                + " тестах - общий класс констант" + (", имя " + name if name else ""), "agent", "; ".join(shared[:10]))
        else:
            decl = "private static final " + const_type(literal) + " " + (name or "<ИМЯ>") + " = " + literal + ";"
            add("CONST", place, "константа `" + decl + "`, замен " + str(len(where)), "script" if name else "agent")
    skip = literal_lines(lines)
    mine = windows(lines, skip)
    theirs = {}
    for f, body in other_text.items():
        b_lines = body.splitlines()
        for block in windows(b_lines, literal_lines(b_lines)):
            theirs.setdefault(block, []).append(f)
    seen = set()
    for block, starts in sorted(mine.items(), key=lambda kv: kv[1][0]):
        deps = sorted(set(theirs.get(block, [])))
        if (len(starts) < 2 and not deps) or any(abs(s - p) < DUP_LINES for s in starts for p in seen):
            continue
        seen.update(starts)
        add("DUP", rel + ":" + ",".join(str(s) for s in starts), "блок из " + str(DUP_LINES) + "+ строк, повторов "
            + str(len(starts) + len(deps)) + " - метод в классе шагов: `" + block.split("\n")[0][:80] + "`",
            "agent", "; ".join(deps[:10]) or "-")
    plan = ["---", "review_status: found", "file: " + rel, "class: " + target.stem, "target_only: no",
            "compile_before: -", "compile_after: -", "check_rounds: 0", "---", "", "# План проверки " + target.stem, "",
            "## Правки", "", "| R | Тип | Где | Что сделать | Кто | Зависимые тесты | Статус |",
            "|---|-----|-----|-------------|-----|-----------------|--------|"]
    plan += ["| " + " | ".join(esc(c) for c in item) + " |" for item in items] or ["| - | нет | - | находок нет | - | - | - |"]
    plan += ["", "## Журнал", "", "| Кто | Что |", "|-----|-----|", "| review | find -> находок " + str(len(items)) + " |", ""]
    folder(target).mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(plan), encoding="utf-8")
    counts = {}
    for item in items:
        counts[item[4]] = counts.get(item[4], 0) + 1
    print("НАХОДОК: " + str(len(items)) + " · скрипт " + str(counts.get("script", 0)) + " · агент "
          + str(counts.get("agent", 0)) + " · человеку " + str(counts.get("human", 0)))
    for item in items:
        print(" | ".join(item[:6]))
    print("ПЛАН: " + str(path))
    print(json.dumps({"file": rel, "items": len(items), "by": counts}, ensure_ascii=False))
    return 0 if items else 1


# ---------- approve ----------

def cmd_approve(target, choice, target_only):
    path, text, head = load(target)
    if text is None:
        return fail("НЕТ REVIEW-PLAN.md: сначала find")
    if head.get("review_status") not in ("found", "approved"):
        return fail("review_status " + head.get("review_status", "-") + " - выбор правок только до start", 1)
    items = rows_of(text, "Правки")
    ids = {i[0] for i in items}
    if choice == "all":
        wanted = ids
    elif choice == "none":
        wanted = set()
    else:
        wanted = {c.strip() for c in choice.split(",") if c.strip()}
        unknown = wanted - ids
        if unknown:
            return fail("нет таких правок: " + ", ".join(sorted(unknown)), 1)
    approved = []
    for item in items:
        if item[0] == "-":
            continue
        status = "approved" if item[0] in wanted and item[4] in ("script", "agent") else "skipped"
        if target_only and item[1] == "SHARED-CONST":
            status = "skipped"
        if status == "approved":
            approved.append(item[0])
        text = re.sub(r"(?m)^(\| " + re.escape(item[0]) + r" \|(?:(?:[^|\n\\]|\\.)*\|){5}) *\w+ *\|$",
                      lambda m: m.group(1) + " " + status + " |", text, count=1)
    text = set_head(set_head(text, "review_status", "approved"), "target_only", "yes" if target_only else "no")
    path.write_text(journal(text, "approve -> " + (", ".join(approved) or "нет")), encoding="utf-8")
    print("ОДОБРЕНО: " + (", ".join(approved) or "нет") + (" · только тест-класс" if target_only else ""))
    return 0


# ---------- start: компиляция до, копия, правки скрипта ----------

def snapshot(dest):
    manifest = []
    for root in source_roots():
        for path in root.rglob("*"):
            if path.is_file() and not (set(path.parts) & SKIP_DIRS):
                copy = dest / "files" / path.as_posix()
                copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, copy)
                manifest.append(path.as_posix())
    (dest / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=0), encoding="utf-8")
    return manifest


def changed_files(target):
    dest = folder(target) / "backup"
    try:
        manifest = json.loads(read(dest / "manifest.json") or "[]")
    except ValueError:
        return [], []
    known = set(manifest)
    changed = [p for p in manifest
               if not Path(p).is_file() or Path(p).read_bytes() != (dest / "files" / p).read_bytes()]
    created = []
    for root in source_roots():
        for path in root.rglob("*"):
            if path.is_file() and path.as_posix() not in known and not (set(path.parts) & SKIP_DIRS):
                created.append(path.as_posix())
    return changed, sorted(created)


def apply_constants(target, items):
    """Правки CONST со статусом approved и именем: объявление после последней константы
    класса (или после строки class) и замена литерала в строках из «Где»."""
    lines = read(target).splitlines()
    done = []
    decls = []
    for item in items:
        if item[1] != "CONST" or item[4] != "script" or item[6] != "approved":
            continue
        decl = re.search(r"`(private static final .*?;)`", item[3]).group(1)
        name = re.search(r"final \S+ (\w+) =", decl).group(1)
        literal = decl.split(" = ", 1)[1][:-1]
        numbers = [int(n) for n in item[2].rsplit(":", 1)[1].split(",")]
        for n in numbers:
            parts = segments(lines[n - 1])
            new = []
            for kind, part in parts:
                if kind == "str":
                    new.append(name if part == literal else part)
                elif not literal.startswith('"'):
                    new.append(re.sub(r"(?<![\w.])" + re.escape(literal) + r"(?![\w.])", name, part))
                else:
                    new.append(part)
            lines[n - 1] = "".join(new)
        decls.append(decl)
        done.append(item[0])
    if not decls:
        return [], 0, 0
    start = class_body_start(lines)
    last = start
    for number in range(start + 1, len(lines) + 1):
        t = lines[number - 1].strip()
        if re.search(r"\bstatic\s+final\b", t) and t.endswith(";"):
            last = number
        elif t and not t.startswith("//") and not t.startswith("@") and not re.search(r"\bstatic\s+final\b", t):
            break
    indent = "    "
    block = [indent + d for d in decls] + ([""] if last == start else [])
    lines[last:last] = block
    Path(target).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return done, last, len(block)


def shift_lines(text, file, after, count):
    """После вставки count строк за строкой after - сдвинуть номера строк в «Где» правок этого файла."""
    if not count:
        return text

    def move(m):
        numbers = [int(n) + (count if int(n) > after else 0) for n in m.group(2).split(",")]
        return m.group(1) + ",".join(str(n) for n in numbers)
    return re.sub(r"(" + re.escape(file) + r":)([0-9,]+)", move, text)


def write_rules(target):
    source = read(SKILL / "references" / "code-rules.md")
    out, copying, found = ["# Правила кода для проверки " + Path(target).stem + "\n\n" + GLOSSARY], False, []
    for line in source.split("\n"):
        rule = re.match(r"^- \*\*(MR-[0-9H]+) ·", line)
        if rule:
            copying = rule.group(1) in REVIEW_RULES
            if copying:
                found.append(rule.group(1))
        elif line.startswith("## ") or line.startswith("---"):
            copying = False
        if copying:
            out.append(line + "\n")
    human = re.search(r"(?m)^## Правила: добавлено человеком", source)
    if human:
        out.append("\n" + source[human.start():])
    (folder(target) / "rules-now.md").write_text("".join(out), encoding="utf-8")
    docs, count = ["# Конспект документации\n\n"], 0
    for base in NOTE_DIRS:
        for notes in sorted(base.glob("*.md")) if base.is_dir() else []:
            for rec in re.finditer(r"(?ms)^#{2,3} (D-[A-Za-z0-9-]+-\d+)\b.*?(?=^#{1,3} |\Z)", read(notes)):
                if "НЕТ В ДОКЕ" not in rec.group():
                    docs.append(rec.group().rstrip() + "\n\n")
                    count += 1
    (folder(target) / "docs-now.md").write_text("".join(docs), encoding="utf-8")
    return found, count


def cmd_start(target, compile_on):
    path, text, head = load(target)
    if text is None:
        return fail("НЕТ REVIEW-PLAN.md: сначала find")
    status = head.get("review_status")
    if status == "fixing":
        print("УЖЕ ИДУТ ПРАВКИ: копия есть, дальше next")
        return 0
    if status != "approved":
        return fail("review_status " + str(status) + " - сначала approve", 1)
    items = rows_of(text, "Правки")
    if not [i for i in items if i[-1] == "approved"]:
        return fail("НЕЧЕГО ДЕЛАТЬ: ни одна правка не одобрена - сразу check не нужен, итог по плану", 1)
    before, details = ("skipped", ["--no-compile"]) if not compile_on else compile_project(COMPILE_TIMEOUT)
    text = set_head(text, "compile_before", before)
    if before == "failed":
        path.write_text(journal(text, "start -> компиляция до правок failed"), encoding="utf-8")
        for d in details:
            print("КОМПИЛЯЦИЯ " + d)
        return fail("ПРОЕКТ НЕ КОМПИЛИРУЕТСЯ ДО ПРАВОК - правки не начинаю", 1)
    dest = folder(target) / "backup"
    if dest.exists():
        shutil.rmtree(dest)
    files = snapshot(dest)
    found, count = write_rules(target)
    done, after, count = apply_constants(head["file"], items)
    text = shift_lines(text, head["file"], after, count)
    for rid in done:
        text = re.sub(r"(?m)^(\| " + re.escape(rid) + r" \|(?:(?:[^|\n\\]|\\.)*\|){5}) *\w+ *\|$",
                      lambda m: m.group(1) + " done |", text, count=1)
    text = set_head(text, "review_status", "fixing")
    path.write_text(journal(text, "start -> копия " + str(len(files)) + " файлов, скрипт сделал " + (", ".join(done) or "нет")), encoding="utf-8")
    print("КОМПИЛЯЦИЯ ДО ПРАВОК: " + before)
    print("КОПИЯ: " + str(len(files)) + " файлов в " + str(dest))
    print("ПРАВИЛА: " + str(len(found)) + " · КОНСПЕКТ: записей " + str(count))
    print("СКРИПТ СДЕЛАЛ: " + (", ".join(done) or "нет"))
    left = [i[0] for i in rows_of(read(path), "Правки") if i[-1] == "approved"]
    print("АГЕНТУ: " + (", ".join(left) or "нет - дальше check"))
    return 0


# ---------- next / mark ----------

def cmd_next(target):
    path, text, head = load(target)
    if text is None:
        return fail("НЕТ REVIEW-PLAN.md: сначала find")
    if head.get("review_status") != "fixing":
        return fail("review_status " + head.get("review_status", "-") + " - задания агенту только после start", 1)
    write_rules(target)
    items = [i for i in rows_of(text, "Правки") if i[-1] == "approved"]
    errors = read(folder(target) / "errors.md").strip()
    if not items and errors:
        items = [["FIX", "FIX", head["file"], "исправь ошибки последнего check: " + "; ".join(errors.splitlines()), "agent", "-", "approved"]]
    if not items:
        print("ВСЕ ПРАВКИ СДЕЛАНЫ - дальше check")
        return 1
    item = items[0]
    root = str(Path(".").resolve())
    deps = item[5] if head.get("target_only") != "yes" else "-"
    lines = ["ПРАВКА для агента pvatf-generator (передай дословно, всё ниже этой строки):", "",
             "- Проект: " + root,
             "- Тест-класс: " + head["file"],
             "- Правка: " + item[0] + " · " + item[1] + " · " + item[2],
             "- Что сделать: " + item[3],
             "- Как делать правку этого типа: " + str(SKILL / "references" / "fixes.md") + ", раздел «"
             + ("MR" if item[1].startswith("MR-") and item[1] != "MR-22" else item[1]) + "»"
             + (", строка " + item[1] if item[1].startswith("MR-") and item[1] != "MR-22" else ""),
             "- Правила кода: " + root + "/" + str(folder(target) / "rules-now.md"),
             "- Конспект документации: " + root + "/" + str(folder(target) / "docs-now.md"),
             "- Как писать проверки: " + str(SKILL / "references" / "matchers.md"),
             "- Зависимые тесты, которые эта правка тоже меняет (больше никакие): " + deps]
    if head.get("target_only") == "yes" and item[5] != "-":
        lines.append("- Зависимые тесты НЕ меняй, даже если там тот же код: " + item[5])
    print("\n".join(lines))
    return 0


def cmd_mark(target, rid, status):
    path, text, head = load(target)
    if text is None:
        return fail("НЕТ REVIEW-PLAN.md")
    if status not in ("done", "failed", "blocked", "approved"):
        return fail("статус - один из: done, failed, blocked, approved")
    pattern = re.compile(r"(?m)^(\| " + re.escape(rid) + r" \|(?:(?:[^|\n\\]|\\.)*\|){5}) *\w+ *\|$")
    if not pattern.search(text):
        return fail("в плане нет правки " + rid, 1)
    text = pattern.sub(lambda m: m.group(1) + " " + status + " |", text, count=1)
    path.write_text(journal(text, rid + " -> " + status), encoding="utf-8")
    left = [i[0] for i in rows_of(text, "Правки") if i[-1] == "approved"]
    print("ОТМЕЧЕНО: " + rid + " " + status + " · осталось агенту: " + (", ".join(left) or "нет - дальше check"))
    return 0


# ---------- check / rollback / отчёт ----------

def report(target, text, head, status, after, findings):
    items = [i for i in rows_of(text, "Правки") if i[0] != "-"]
    changed, created = changed_files(target)
    rows = ["| " + " | ".join(esc(c) for c in (i[0], i[1], i[2], i[3], i[6])) + " |" for i in items] or ["| - | - | - | находок не было | - |"]
    touched = set(changed + created)
    named = sorted({d for i in items for d in i[5].split("; ") if d != "-"})
    deps = [d + (" - изменён" if d in touched else " - не изменён") for d in named]
    skipped_deps = [d for d in named if d not in touched]
    left = ["- " + i[0] + " " + i[1] + " " + i[2] + ": " + i[3] for i in items if i[4] == "human" or i[6] in ("failed", "blocked")]
    left += ["- " + f for f in findings]
    if skipped_deps:
        left.append("- тот же код остался в зависимых тестах, они не менялись: " + ", ".join(skipped_deps))
    body = TEMPLATE_REPORT.format(
        cls=head.get("class", "-"), file=head.get("file", "-"), status=status,
        before=head.get("compile_before", "-"), after=after,
        done=sum(1 for i in items if i[6] == "done"), failed=sum(1 for i in items if i[6] in ("failed", "blocked")),
        skipped=sum(1 for i in items if i[6] == "skipped" and i[4] != "human"), human=sum(1 for i in items if i[4] == "human"),
        rows="\n".join(rows),
        changed="\n".join(["- " + c + " - изменён" for c in changed] + ["- " + c + " - создан" for c in created]) or "нет",
        dependents="\n".join("- " + d for d in deps) or "нет",
        left="\n".join(left) or "нет")
    (folder(target) / "REVIEW.md").write_text(body, encoding="utf-8")


def cmd_check(target, compile_on):
    path, text, head = load(target)
    if text is None:
        return fail("НЕТ REVIEW-PLAN.md")
    if head.get("review_status") not in ("fixing", "checked"):
        return fail("review_status " + head.get("review_status", "-") + " - check только после start", 1)
    left = [i[0] for i in rows_of(text, "Правки") if i[-1] == "approved"]
    if left:
        return fail("НЕ СДЕЛАНЫ: " + ", ".join(left) + " - сначала next/mark по каждой", 1)
    changed, created = changed_files(target)
    findings = []
    backup = folder(target) / "backup" / "files"
    for f in sorted(set(changed + created)):
        if f.endswith(".java") and Path(f).is_file():
            body = read(f)
            checks = CHECKS + (TEST_ONLY if "@Test" in body else [])
            was = {(r, c) for r, _, _, c in scan_items(read(backup / f).splitlines(), checks)}
            findings += ["%s %s:%d - %s: %s" % (r, f, n, m, c) for r, n, m, c in scan_items(body.splitlines(), checks)
                         if (r, c) not in was and r != "STUB"]
    status, details = ("skipped", ["--no-compile"]) if not compile_on else compile_project(COMPILE_TIMEOUT)
    for f in findings:
        print(f)
    for d in details if status == "failed" else []:
        print("КОМПИЛЯЦИЯ " + d)
    print("КОМПИЛЯЦИЯ: " + status)
    print("ИЗМЕНЕНО: " + (", ".join(changed + created) or "нет"))
    text = set_head(text, "compile_after", status)
    errors = findings + (["КОМПИЛЯЦИЯ " + d for d in details] if status == "failed" else [])
    if errors:
        rounds = int(head.get("check_rounds", "0") or 0) + 1
        text = set_head(text, "check_rounds", str(rounds))
        (folder(target) / "errors.md").write_text("\n".join(errors) + "\n", encoding="utf-8")
        path.write_text(journal(text, "check -> ошибок " + str(len(errors)) + ", круг " + str(rounds)), encoding="utf-8")
        if rounds >= MAX_ROUNDS:
            print("ИТОГ: круг " + str(rounds) + " из " + str(MAX_ROUNDS) + " - ошибки остались, дальше rollback")
            return 1
        print("ИТОГ: ошибок " + str(len(errors)) + " · круг " + str(rounds) + " из " + str(MAX_ROUNDS) + " - дальше next (задание на исправление) и снова check")
        return 1
    if (folder(target) / "errors.md").exists():
        (folder(target) / "errors.md").unlink()
    text = set_head(text, "review_status", "checked")
    path.write_text(journal(text, "check -> " + status + ", находок в изменённых файлах " + str(len(findings))), encoding="utf-8")
    report(target, read(path), head_of(read(path)), "checked", status, [])
    print("ИТОГ: review_status checked · отчёт " + str(folder(target) / "REVIEW.md"))
    return 0


def cmd_rollback(target):
    path, text, head = load(target)
    if text is None:
        return fail("НЕТ REVIEW-PLAN.md")
    dest = folder(target) / "backup"
    if not (dest / "manifest.json").is_file():
        return fail("НЕТ КОПИИ: правки не начинались (start не запускался) - откатывать нечего", 1)
    changed, created = changed_files(target)
    for p in changed:
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest / "files" / p, p)
    for p in created:
        Path(p).unlink()
    text = set_head(text, "review_status", "rolled-back")
    path.write_text(journal(text, "rollback -> восстановлено " + str(len(changed)) + ", удалено новых " + str(len(created))), encoding="utf-8")
    report(target, read(path), head_of(read(path)), "rolled-back", "failed", [])
    print("ОТКАТ: восстановлено " + str(len(changed)) + " · удалено новых " + str(len(created)))
    for p in changed:
        print("  восстановлен " + p)
    for p in created:
        print("  удалён " + p)
    return 0


def main(args):
    commands = ("find", "approve", "start", "next", "mark", "check", "rollback")
    if len(args) < 2 or args[0] not in commands:
        print("Использование: review.py find|start|next|check|rollback <файл теста> | approve <файл> all|none|R-1,R-3 [--target-only] | mark <файл> <R-n> <статус>")
        return 2
    command, target = args[0], args[1]
    if command == "approve":
        return cmd_approve(target, args[2], "--target-only" in args) if len(args) >= 3 else fail("approve <файл> all|none|R-1,R-3")
    if command == "mark":
        return cmd_mark(target, args[2], args[3]) if len(args) >= 4 else fail("mark <файл> <R-n> <статус>")
    if command in ("start", "check"):
        return {"start": cmd_start, "check": cmd_check}[command](target, "--no-compile" not in args)
    return {"find": cmd_find, "next": cmd_next, "rollback": cmd_rollback}[command](target)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
