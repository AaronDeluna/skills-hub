#!/usr/bin/env python3
"""Механическая проверка карточек юнитов (скилл migration-map). Запуск из корня проекта:

  python3 <каталог скилла>/scripts/card.py M-007   - одна карточка
  python3 <каталог скилла>/scripts/card.py all     - все карточки todo

Проверяет то, что можно проверить без модели: поля подшагов, пустые слова, лимиты,
покрытие потребителей, legacy, записи конспекта, «создал - подключи», число строк.
Смысл шагов не проверяет - это работа сабагента «проверяющий карточки».
Python 3.8+, только стандартная библиотека. Код выхода 0 - чисто, 1 - есть находки, 2 - неверные аргументы.
"""
import re
import sys
from pathlib import Path

MIGRATION = Path(".gigacode") / "data" / "migration"
SKILL_DIR = Path(__file__).resolve().parent.parent
EMPTY_WORDS = re.compile(
    r"\b(мигрировать|адаптировать|привести в порядок|при необходимости|и так далее|соответствующ\S*|доработать)\b",
    re.IGNORECASE)
LIMITS = {"env": 6, "core": 6, "usage": 3, "cleanup": 15, "review": 15}

problems = []
_rule_table = {}
flow_style = False


def read(path):
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else ""
    except OSError:
        return ""


def cells(line):
    trimmed = line.strip()
    if not trimmed.startswith("|"):
        return []
    raw = trimmed[1:].split("|")
    while raw and raw[-1] == "":
        raw.pop()
    return [c.strip() for c in raw]


def parse_int(value):
    try:
        return int(value.strip())
    except ValueError:
        return 0


def front(text, key):
    m = re.search(r"(?m)^" + re.escape(key) + r":\s*(.*)$", text)
    return m.group(1).strip() if m else "-"


def sections(text):
    result = {}
    name = None
    body = []
    for line in text.split("\n"):
        if line.startswith("## "):
            if name is not None:
                result[name] = "".join(body)
            name = line[3:].strip()
            body = []
        elif name is not None:
            body.append(line + "\n")
    if name is not None:
        result[name] = "".join(body)
    return result


def field(body, name):
    value = []
    inside = False
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
        if len(row) >= 3 and re.search(r"изменить|создать|удалить", row[2]):
            path = row[0].replace("`", "").strip()
            if path and not path.startswith("<"):
                files[path] = row[2]
    return files


def line_count(body, path):
    for line in body.split("\n"):
        row = cells(line)
        if len(row) >= 3 and row[0].replace("`", "") == path:
            return re.sub(r"[^0-9]", "", row[1])
    return "0"


# ---------- tech ----------

def check_tech(text, map_text):
    global flow_style
    parts = sections(text)
    core_mode = front(text, "core_mode")
    flow_style = re.search(r"(?m)^- Стиль шагов: flow", map_text) is not None
    steps = [row for row in (cells(line) for line in parts.get("Подшаги", "").split("\n"))
             if len(row) >= 5 and re.fullmatch(r"S-[0-9]+", row[0])]
    if not steps:
        problems.append("нет таблицы «Подшаги»")
        return
    bodies, files = {}, {}
    for step in steps:
        sid, kind = step[0], step[1]
        body = None
        for key, value in parts.items():
            if key.startswith(sid + " "):
                body = value
        if body is None:
            problems.append(sid + ": нет раздела «## " + sid + " · ...»")
            continue
        bodies[sid] = body
        files[sid] = file_table(body)
        check_title(sid, step[2])
        if kind in ("разбор", "review"):
            continue
        check_step(sid, kind, core_mode, body, files[sid])
    check_consumers(parts.get("Разбор технологии", ""), steps, files)
    check_created_are_used(steps, files, bodies, front(text, "tech"))
    check_legacy(text, map_text, front(text, "tech"))


def check_title(sid, title):
    empty = EMPTY_WORDS.search(title)
    if empty:
        problems.append(sid + ": в названии слово без содержания «" + empty.group() + "» - напиши, что станет, с именами")


def check_step(sid, kind, core_mode, body, step_files):
    if not step_files:
        problems.append(sid + ": нет таблицы файлов (Файл | Строк | Действие)")
    limit = LIMITS.get(kind)
    if limit is not None and len(step_files) > limit:
        problems.append(sid + ": файлов " + str(len(step_files)) + " при лимите " + str(limit) + " для " + kind + " - раздели подшаг")
    todo = field(body, "Что сделать")
    if not re.search(r"\b1\.", todo):
        problems.append(sid + ": «Что сделать» без пронумерованных действий")
    result = field(body, "Итоговый результат")
    for empty in EMPTY_WORDS.finditer(todo + " " + result):
        problems.append(sid + ": слово без содержания «" + empty.group() + "» - замени конкретным действием с именами")
    if len(result) < 10:
        problems.append(sid + ": пустой «Итоговый результат»")
    checkpoint = field(body, "Чекпоинт")
    if "`" not in checkpoint or "->" not in checkpoint:
        problems.append(sid + ": «Чекпоинт» должен быть одной командой в `...` и ожидаемым выводом после ->")
    if kind in ("usage", "fix"):
        criteria = {}
        for line in field(body, "Критерии по файлам").split("\n"):
            row = cells(line)
            if len(row) >= 4 and row[0] != "Файл" and not row[0].startswith("-") and not row[0].startswith("<"):
                criteria[row[0].replace("`", "")] = row[1]
        for path, action in step_files.items():
            if "изменить" not in action:
                continue
            was = criteria.get(path)
            if was is None:
                problems.append(sid + ": нет строки «Критерии по файлам» для " + path)
            elif not re.search(r"[0-9]", was):
                problems.append(sid + ": в «Было» для " + path + " нет чисел из разбора")
        if not re.search(r"assert|Matcher|JsonNode", checkpoint):
            problems.append(sid + ": в «Чекпоинте» usage/fix нет команды MR-48 (ассерты, свои matchers, JsonNode)")
    check_rules(sid, kind, core_mode, field(body, "Правила подшага"))
    for name, action in step_files.items():
        path = Path(name)
        if "создать" in action:
            if path.exists():
                problems.append(sid + ": " + name + " помечен «создать», но уже есть")
            continue
        if not path.exists():
            problems.append(sid + ": " + name + " - файла нет в проекте")
            continue
        declared = parse_int(line_count(body, name))
        try:
            real = len(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            problems.append(sid + ": " + name + " - не читается")
            continue
        if declared > 0 and abs(real - declared) > max(10, real // 5):
            problems.append(sid + ": " + name + " - в карточке " + str(declared) + " строк, в файле " + str(real))


def rule_table():
    """Таблица references/substep-rules.md: вид подшага -> обязательные номера; «то же, что core new, плюс ...»."""
    if "table" in _rule_table:
        return _rule_table["table"]
    path = SKILL_DIR / "references" / "substep-rules.md"
    if not path.is_file():
        print("ВНИМАНИЕ: нет " + str(path) + " - состав «Правила подшага» не проверяется")
        _rule_table["table"] = None
        return None
    table = {}
    for line in read(path).split("\n"):
        if not line.startswith("| `"):
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        head = parts[1]
        first = head.index("`")
        kind = head[first + 1:head.index("`", first + 1)]
        key = "core " + ("in-place" if "in-place" in head else "new") if kind == "core" else kind
        numbers = []
        if "то же, что `core` `new`" in parts[2] and "core new" in table:
            numbers.extend(table["core new"])
        numbers.extend(re.findall(r"MR-[0-9]+", parts[2]))
        table[key] = numbers
    _rule_table["table"] = table
    return table


def check_rules(sid, kind, core_mode, text):
    """«Правила подшага» - строго по таблице references/substep-rules.md: все номера строки вида
    подшага (плюс MR-44 при стиле flow для core и usage), лишних нет. Сверх строки разрешены
    только MR-46 и правила человека MR-H. У fix обязательны номера строки, остальное - по находкам."""
    present = list(dict.fromkeys(re.findall(r"MR-[0-9H]+", text)))
    if not present:
        problems.append(sid + ": пустое поле «Правила подшага»")
        return
    table = rule_table()
    key = "core " + ("in-place" if core_mode == "in-place" else "new") if kind == "core" else kind
    if table is None or key not in table:
        return
    required = list(dict.fromkeys(table[key]))
    if flow_style and kind in ("core", "usage") and "MR-44" not in required:
        required.append("MR-44")
    missing = [n for n in required if n not in present]
    if missing:
        problems.append(sid + ": в «Правила подшага» нет обязательных для " + key + ": " + ", ".join(missing)
                        + " (references/substep-rules.md)")
    if kind == "fix":
        return
    extra = [n for n in present if n not in required and n != "MR-46" and not n.startswith("MR-H")]
    if extra:
        problems.append(sid + ": лишние номера в «Правила подшага»: " + ", ".join(extra)
                        + " - для " + key + " их нет в references/substep-rules.md")


def check_consumers(analysis, steps, files):
    """Каждый потребитель - ровно в одном usage, и в колонке «Подшаг» стоит этот usage."""
    for line in analysis.split("\n"):
        row = cells(line)
        if len(row) < 6 or row[0].startswith("Потребитель") or row[0].startswith("-") or row[0].startswith("<"):
            continue
        consumer = row[0].replace("`", "")
        declared = row[-1]
        if "уже нет" in declared:
            continue
        found = [s[0] for s in steps if s[1] == "usage" and consumer in files.get(s[0], {})]
        if not found:
            problems.append("потребитель " + consumer + " не стоит ни в одном подшаге usage")
        elif len(found) > 1:
            problems.append("потребитель " + consumer + " стоит в нескольких usage: " + ", ".join(found))
        elif found[0] not in declared:
            problems.append("потребитель " + consumer + ": в колонке «Подшаг» " + declared + ", а в таблице файлов - " + found[0])


def check_created_are_used(steps, files, bodies, tech):
    """Создал - подключи: класс из core упоминается в каком-нибудь usage."""
    usage = "".join(bodies.get(s[0], "") for s in steps if s[1] == "usage")
    has_usage = any(s[1] == "usage" for s in steps)
    for step in steps:
        if step[1] != "core":
            continue
        for path, action in files.get(step[0], {}).items():
            if "создать" not in action:
                continue
            name = re.sub(r"\.(java|kt)$", "", Path(path).name)
            base_layer = name.lower() == (tech.replace("-", "") + "Steps").lower()
            other_step = any(k != step[0] and name in v for k, v in bodies.items())
            if (has_usage and not base_layer and not other_step and name not in usage
                    and not name.startswith("Base") and not name.endswith("Configuration")):
                problems.append(step[0] + ": создаётся " + name + ", но ни один подшаг usage на него не переводит (создал - подключи)")


def check_legacy(text, map_text, tech):
    """Строки L этой технологии из карты упомянуты в карточке."""
    body = re.sub(r"(?s)^---.*?\n---\n", "", text, count=1)
    for line in map_text.split("\n"):
        row = cells(line)
        if len(row) >= 3 and re.fullmatch(r"L-[0-9]+", row[0]) and row[1] == tech:
            if not re.search(r"\b" + row[0] + r"\b", body):
                problems.append(row[0] + " (" + row[2] + ") технологии " + tech + " не удаляется ни в одном подшаге")


# ---------- обычный юнит ----------

def check_plain(text):
    parts = sections(text)
    if not file_table(parts.get("Файлы юнита", "")):
        problems.append("нет таблицы «Файлы юнита»")
    todo = parts.get("Что сделать", "")
    if not re.search(r"\b1\.", todo):
        problems.append("«Что сделать» без пронумерованных действий")
    for empty in EMPTY_WORDS.finditer(todo):
        problems.append("слово без содержания «" + empty.group() + "» в «Что сделать»")
    if not re.search(r"MR-[0-9H]+", parts.get("Правила юнита", "")):
        problems.append("пустой раздел «Правила юнита»")
    if "<точный grep" in parts.get("Критерии готовности", ""):
        problems.append("в «Критериях готовности» не подставлен grep-шаблон")


def check_doc_refs(text):
    """Каждая ссылка D-<tech>-n есть в конспекте."""
    notes, seen = {}, set()
    for ref in re.finditer(r"\bD-([a-z0-9-]+?)-([0-9]+)\b", text):
        if ref.group() in seen:
            continue
        seen.add(ref.group())
        tech = ref.group(1)
        if tech not in notes:
            notes[tech] = read(MIGRATION / "doc-notes" / (tech + ".md"))
        if not re.search(r"(?m)^#{2,3} " + re.escape(ref.group()) + r"\b", notes[tech] or ""):
            problems.append("ссылка " + ref.group() + " - такой записи нет в doc-notes/" + tech + ".md")


def main(args):
    if not args:
        print("Использование: card.py <M-nnn | all>")
        return 2
    map_text = read(MIGRATION / "MIGRATION-MAP.md")
    units = MIGRATION / "units"
    if args[0] == "all":
        if not units.is_dir():
            print("Карточек нет: папки " + str(units) + " нет. Запускай из корня проекта, где лежит .gigacode/")
            return 1
        cards = sorted(p for p in units.iterdir() if re.fullmatch(r"M-[0-9]+\.md", p.name))
    else:
        cards = [units / (args[0] + ".md")]
    total = 0
    for path in cards:
        text = read(path)
        if not text:
            print(str(path) + ": карточки нет")
            total += 1
            continue
        if args[0] == "all" and front(text, "status") != "todo":
            continue
        del problems[:]
        if front(text, "type") == "tech":
            check_tech(text, map_text)
        else:
            check_plain(text)
        check_doc_refs(text)
        print(front(text, "id") + ": " + ("чисто" if not problems else "находок " + str(len(problems))))
        for problem in problems:
            print("  - " + problem)
        total += len(problems)
    print("ИТОГ: находок " + str(total))
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
