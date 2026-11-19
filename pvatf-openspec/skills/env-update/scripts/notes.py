#!/usr/bin/env python3
"""Поиск по конспекту документации (doc-notes/). Запуск из корня проекта:

  python3 <каталог скилла>/scripts/notes.py list <tech>             - оглавление: ID, статус, вопрос
  python3 <каталог скилла>/scripts/notes.py find <tech> <слова...>  - записи, где есть эти слова
  python3 <каталог скилла>/scripts/notes.py show D-rest-3 D-rest-5  - записи целиком
  python3 <каталог скилла>/scripts/notes.py next <tech>             - следующий свободный ID записи (D-<tech>-<n>)
  python3 <каталог скилла>/scripts/notes.py task <tech> <каталог>   - две строки для задания агенту pvatf-docs:
      куда он пишет ответ и с какого ID нумерует записи; <каталог> - doc-notes или migration/doc-notes
  python3 <каталог скилла>/scripts/notes.py merge <tech> <каталог> [<где записано>]
      - проверяет файл, который записал агент pvatf-docs (<каталог>/inbox/<tech>.md), дописывает
        записи в конспект <каталог>/<tech>.md, обновляет словарь, удаляет файл агента.
        Печатает строку ОК и по строке на запись: ID, статус, вопрос, «Что использовать»
        (до 200 знаков), «Как подключить» (до 150) и, если запись не «найден», «Чего не
        хватило» (до 150 знаков).
        <где записано> - для миграции: этап карты или юнит M-nnn (строка «- Записано:»).

Конспект лежит в двух местах, оба читаются: .gigacode/data/doc-notes/ (общий для окружения
и генерации автотестов) и .gigacode/data/migration/doc-notes/ (миграция). find и list смотрят
конспект технологии и общий (common). Слово ищется без учёта регистра
и по началу слова (matcher найдёт matchers). Ничего не меняет. Python 3.8+, только стандартная библиотека.
Код выхода: 0 - выполнено; 1 - merge: файл агента не прошёл проверку (печатает, что исправить,
файл агента не трогает); 2 - неверные аргументы.
"""
import datetime
import re
import sys
from pathlib import Path

DATA = Path(".gigacode") / "data"
NOTE_DIRS = [DATA / "doc-notes", DATA / "migration" / "doc-notes"]
HEAD = re.compile(r"^#{2,3} D-[A-Za-z0-9-]+-[0-9]+\b")
DIRS = {"doc-notes": DATA / "doc-notes", "migration/doc-notes": DATA / "migration" / "doc-notes"}
STATUSES = ("найден", "найден частично", "НЕТ В ДОКЕ")
FIELDS = ("Статус", "Что использовать", "Формулировки запросов")
DICT_HEAD = "### Ключевые слова документации"


class Record:
    def __init__(self, rid, question):
        self.id = rid
        self.question = question
        self.status = "-"
        self.text = ""
        self.score = 0

    def field(self, name):
        for line in self.text.split("\n"):
            if line.startswith("- " + name):
                return line[line.index(":") + 1:].strip() if ":" in line else ""
        return ""


def parse(path):
    records = []
    if not path.is_file():
        return records
    current = None
    body = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if HEAD.match(line):
            if current is not None:
                current.text = "".join(body)
                records.append(current)
            head = re.sub(r"^#+\s*", "", line, count=1)
            dot = head.find("·")
            current = Record(head.split()[0], head[dot + 1:].strip() if dot >= 0 else head)
            body = []
        if current is not None:
            body.append(line + "\n")
            if line.startswith("- Статус:"):
                current.status = line[line.index(":") + 1:].strip()
    if current is not None:
        current.text = "".join(body)
        records.append(current)
    return records


def records_for(tech):
    found = []
    for folder in NOTE_DIRS:
        found += parse(folder / (tech + ".md"))
        if tech != "common":
            found += parse(folder / "common.md")
    return found


def by_id(rid):
    for folder in NOTE_DIRS:
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            for record in parse(path):
                if record.id == rid:
                    return record
    return None


def next_id(tech):
    numbers = [0]
    for folder in NOTE_DIRS:
        for record in parse(folder / (tech + ".md")):
            tail = record.id.rsplit("-", 1)[-1]
            if record.id.startswith("D-" + tech + "-") and tail.isdigit():
                numbers.append(int(tail))
    return "D-" + tech + "-" + str(max(numbers) + 1)


def shorten(text):
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return "-"
    return compact[:220] + "..." if len(compact) > 220 else compact


def note_dir(name):
    folder = DIRS.get(name.strip("/"))
    if folder is None:
        print("Неизвестный каталог: " + name + ". Можно: " + ", ".join(DIRS))
    return folder


def cmd_task(tech, folder):
    inbox = folder / "inbox" / (tech + ".md")
    # полный путь: инструмент записи файла у агентов принимает только абсолютный
    print("- Записать в: " + (Path.cwd() / inbox).as_posix())
    print("- Номер первой записи: " + next_id(tech))
    return 0


def split_inbox(text):
    """Файл агента -> (записи [(id, вопрос, строки)], слова словаря)."""
    records, words, current, in_dict = [], [], None, False
    for line in text.split("\n"):
        if line.strip().startswith(DICT_HEAD):
            in_dict, current = True, None
            continue
        if HEAD.match(line):
            in_dict = False
            head = re.sub(r"^#+\s*", "", line, count=1)
            dot = head.find("·")
            current = [head.split()[0], head[dot + 1:].strip() if dot >= 0 else "", []]
            records.append(current)
            continue
        if in_dict:
            if line.strip().startswith("- ") and line.strip()[2:].strip():
                words.append(line.strip()[2:].strip())
        elif current is not None:
            current[2].append(line)
    return records, words


def word_name(entry):
    return entry.split(" - ")[0].strip().strip("`")


def check_records(tech, records, words, first):
    errors = []
    if not records:
        errors.append("в файле нет ни одной записи «## D-" + tech + "-<n> · <вопрос>»")
    expected = int(first.rsplit("-", 1)[-1])
    for i, (rid, question, lines) in enumerate(records):
        want = "D-" + tech + "-" + str(expected + i)
        if rid != want:
            errors.append(rid + ": ожидался ID " + want + " (ID идут подряд с " + first + ")")
        if not question:
            errors.append(rid + ": в заголовке нет вопроса после «·»")
        body = "\n".join(lines)
        for field in FIELDS:
            if not re.search(r"(?m)^- " + field + ":", body):
                errors.append(rid + ": нет поля «- " + field + ":»")
        status = re.search(r"(?m)^- Статус:\s*(.+?)\s*$", body)
        if status and status.group(1) not in STATUSES:
            errors.append(rid + ": статус «" + status.group(1) + "», можно только: " + " | ".join(STATUSES))
        use = re.search(r"(?m)^- Что использовать:\s*(.*?)\s*$", body)
        if status and status.group(1) == "найден" and use and use.group(1) in ("", "-"):
            errors.append(rid + ": статус «найден», а «Что использовать» пусто")
    found_any = any(re.search(r"(?m)^- Статус:\s*найден", "\n".join(r[2])) for r in records)
    if found_any and not words:
        errors.append("нет раздела «" + DICT_HEAD + "» со списком «- <слово> - <что это>»")
    return errors


def merge_migration(target, tech, records, words, where):
    lines = target.read_text(encoding="utf-8").rstrip("\n").split("\n") if target.is_file() else [
        "# Конспект документации PVATF: " + tech, "Ключевые слова: "]
    if len(lines) < 2 or not lines[1].startswith("Ключевые слова:"):
        lines.insert(1, "Ключевые слова: ")
    old = [w.strip() for w in lines[1].split(":", 1)[1].split(",") if w.strip()]
    new = [word_name(w) for w in words]
    lines[1] = "Ключевые слова: " + ", ".join(old + [w for w in dict.fromkeys(new) if w not in old])
    today = datetime.date.today().isoformat()
    for rid, question, body in records:
        lines += ["", "### " + rid + " · " + question] + [b for b in body if b.strip()]
        lines.append("- Записано: " + today + " · " + (where or "-"))
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def merge_autotest(target, records, words):
    text = target.read_text(encoding="utf-8") if target.is_file() else ""
    old = []
    if DICT_HEAD in text:
        text, tail = text.split(DICT_HEAD, 1)
        old = [l.strip()[2:] for l in tail.split("\n") if l.strip().startswith("- ")]
    text = text.rstrip("\n")
    for rid, question, body in records:
        text += ("\n\n" if text else "") + "## " + rid + " · " + question + "\n" + "\n".join(b for b in body if b.strip())
    names = [word_name(o) for o in old]
    words_lines = old + [w for w in words if word_name(w) not in names]
    text += "\n\n" + DICT_HEAD + "\n" + "\n".join("- " + w for w in words_lines) + "\n"
    target.write_text(text, encoding="utf-8")


def cmd_merge(tech, folder, where):
    inbox = folder / "inbox" / (tech + ".md")
    if not inbox.is_file():
        print("ОШИБКА: файла агента нет: " + inbox.as_posix()
              + ". Агент вернул «MCP НЕДОСТУПЕН» - поступай по таблице ошибок; иначе запусти агента ещё раз с тем же заданием.")
        return 1
    records, words = split_inbox(inbox.read_text(encoding="utf-8"))
    first = next_id(tech)
    errors = check_records(tech, records, words, first)
    if errors:
        print("ОШИБКА: файл " + inbox.as_posix() + " не прошёл проверку, конспект не менялся:")
        for e in errors:
            print("- " + e)
        print("Запусти агента pvatf-docs ещё раз с тем же заданием и строкой: «Прошлый файл не прошёл проверку: <строки выше>».")
        return 1
    target = folder / (tech + ".md")
    if folder.name == "doc-notes" and folder.parent.name == "migration":
        merge_migration(target, tech, records, words, where)
    else:
        merge_autotest(target, records, words)
    inbox.unlink()
    count = {s: [] for s in STATUSES}
    for rid, _, body in records:
        m = re.search(r"(?m)^- Статус:\s*(.+?)\s*$", "\n".join(body))
        count[m.group(1)].append(rid)
    print("ОК: " + target.as_posix() + " + " + records[0][0] + ".." + records[-1][0]
          + " · найден " + str(len(count["найден"])) + " · найден частично: " + (", ".join(count["найден частично"]) or "-")
          + " · НЕТ В ДОКЕ: " + (", ".join(count["НЕТ В ДОКЕ"]) or "-"))
    for rid, question, body in records:
        print(short_line(rid, question, body))
    return 0


def cut(text, size):
    text = " ".join(text.split())
    return text if len(text) <= size else text[:size - 3].rstrip() + "..."


def short_line(rid, question, body):
    """Одна строка на запись: этого хватает для решений на этапах карты без show."""
    rec = Record(rid, question)
    rec.text = "\n".join(body)
    status = rec.field("Статус")
    line = "- " + rid + " · " + status + " · " + cut(question, 80)
    if status != "НЕТ В ДОКЕ":
        line += " · Что использовать: " + cut(rec.field("Что использовать"), 200)
        line += " · Как подключить: " + cut(rec.field("Как подключить") or "-", 150)
    if status != "найден":
        line += " · Чего не хватило: " + cut(rec.field("Чего не хватило") or "-", 150)
    return line


def main(args):
    if len(args) < 2:
        print("Использование: notes.py list <tech> | find <tech> <слова...> | show <D-id...> | next <tech>"
              " | task <tech> <каталог> | merge <tech> <каталог> [<где записано>]")
        return 2
    command = args[0]
    if command in ("task", "merge"):
        if len(args) < 3:
            print("Использование: notes.py " + command + " <tech> <каталог: doc-notes | migration/doc-notes>")
            return 2
        folder = note_dir(args[2])
        if folder is None:
            return 2
        if command == "task":
            return cmd_task(args[1], folder)
        return cmd_merge(args[1], folder, " ".join(args[3:]))
    if command == "next":
        print(next_id(args[1]))
        return 0
    if command == "show":
        for rid in args[1:]:
            record = by_id(rid)
            print(record.text.strip() if record else rid + ": такой записи в конспекте нет")
            print()
        return 0
    records = records_for(args[1])
    if command == "list":
        if not records:
            print("Конспекта по " + (args[1] if args[1] == "common" else args[1] + " и common") + " пока нет.")
        for record in records:
            print(record.id + " · " + record.status + " · " + record.question)
        return 0
    if command == "find":
        words = []
        for arg in args[2:]:
            for word in arg.split():
                clean = re.sub(r"[^\w.]", "", word.lower())
                if len(clean) >= 3:
                    words.append(clean[:-2] if len(clean) > 6 else clean)
        found = []
        for record in records:
            lower = record.text.lower()
            record.score = sum(1 for w in words if w in lower)
            if record.score > 0:
                found.append(record)
        found.sort(key=lambda r: -r.score)
        if not found:
            print("В конспекте ничего по словам: " + ", ".join(words)
                  + ". Попробуй другие слова (имя класса фрейма, раздел документации); не нашлось - сабагент документации.")
            return 0
        print("Нашлось записей: " + str(len(found)) + " (сначала лучшие совпадения). Полностью: notes.py show <ID>")
        for record in found[:8]:
            print()
            print(record.id + " · " + record.status + " · совпало слов " + str(record.score) + "/" + str(len(words)))
            print("  вопрос: " + record.question)
            print("  что использовать: " + shorten(record.field("Что использовать")))
            phrases = record.field("Формулировки запросов")
            if record.status != "найден" and phrases:
                print("  уже спрашивали так: " + shorten(phrases))
        return 0
    print("Неизвестная команда: " + command)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
