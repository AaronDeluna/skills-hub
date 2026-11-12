#!/usr/bin/env python3
"""Поиск по конспекту документации (doc-notes/). Запуск из корня проекта:

  python3 <каталог скилла>/scripts/notes.py list <tech>             - оглавление: ID, статус, вопрос
  python3 <каталог скилла>/scripts/notes.py find <tech> <слова...>  - записи, где есть эти слова
  python3 <каталог скилла>/scripts/notes.py show D-rest-3 D-rest-5  - записи целиком
  python3 <каталог скилла>/scripts/notes.py next <tech>             - следующий свободный ID записи (D-<tech>-<n>)

Конспект лежит в двух местах, оба читаются: .gigacode/data/doc-notes/ (общий для окружения
и генерации автотестов) и .gigacode/data/migration/doc-notes/ (миграция). find и list смотрят
конспект технологии и общий (common). Слово ищется без учёта регистра
и по началу слова (matcher найдёт matchers). Ничего не меняет. Python 3.8+, только стандартная библиотека.
Код выхода: 0 - выполнено, 2 - неверные аргументы.
"""
import re
import sys
from pathlib import Path

DATA = Path(".gigacode") / "data"
NOTE_DIRS = [DATA / "doc-notes", DATA / "migration" / "doc-notes"]
HEAD = re.compile(r"^#{2,3} D-[A-Za-z0-9-]+-[0-9]+\b")


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


def main(args):
    if len(args) < 2:
        print("Использование: notes.py list <tech> | find <tech> <слова...> | show <D-id...> | next <tech>")
        return 2
    command = args[0]
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
            print("Конспекта по " + args[1] + " и common пока нет.")
        for record in records:
            print(record.id + " · " + record.status + " · " + record.question)
        return 0
    if command == "find":
        words = []
        for word in args[2:]:
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
