#!/usr/bin/env python3
"""Очередь генерации автотестов по нескольким тест-кейсам (скилл orchestrator). Запуск из корня проекта:

  python3 <каталог скилла>/scripts/autotest_queue.py add <каталог | файл со списком ключей | ключ ...> - добавить в очередь
  python3 <каталог скилла>/scripts/autotest_queue.py status                - сводка очереди
  python3 <каталог скилла>/scripts/autotest_queue.py skip <№ | ключ> <причина> - пропустить пункт (решил человек)
  python3 <каталог скилла>/scripts/autotest_queue.py block <№ | ключ> <причина> - разбор ТК не удался (ошибка autotest-plan)
  python3 <каталог скилла>/scripts/autotest_queue.py clear                 - удалить очередь (пункты в работе не трогает)

Очередь - .gigacode/data/autotest/QUEUE.md, таблица «№ | Источник | Ключ | Статус | Примечание».
Статус пункта скрипт сам выводит из файлов генерации (.gigacode/data/autotest/<ключ>/):
todo - не начат, in-progress - есть TC.md или PLAN.md, done - plan_status checked, blocked - проверка ТК FAIL
или разбор не удался (команда block, примечание «разбор: ...»), skipped - пропущен человеком. Ключ у файла ТК находится по строке
«Файл источника» в TC.md (её пишет tc_convert.py).
Каталог: каждый файл .md .xml .json .log .txt .java .kt - один пункт; каталог с *-result.json (Allure) -
один пункт. Файл .txt, где каждая непустая строка - ключ ТК, - список ключей.
Повторный add не дублирует пункты. Python 3.8+, только стандартная библиотека.
Код выхода: 0 - выполнено, 1 - нечего добавить или очереди нет, 2 - неверные аргументы.
"""
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pvatf_paths as pp  # noqa: E402 - копия shared/scripts

QUEUE = pp.env_dir() / "QUEUE.md"
KEY = re.compile(r"[A-Z][A-Z0-9]*-T[0-9]+")
SUFFIXES = {".md", ".xml", ".json", ".log", ".txt", ".java", ".kt"}
SKIP_DIRS = {".git", ".gigacode", "openspec", ".idea", ".gradle", "target", "build", "out", "node_modules"}
HEADER = "| № | Источник | Ключ | Статус | Примечание |"


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def norm(value):
    return Path(value).as_posix().rstrip("/")


def head_of(text):
    head = {}
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return head
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            name, value = line.split(":", 1)
            head[name.strip()] = value.strip()
    return head


def load():
    """Строки очереди: список dict(n, source, key, status, note)."""
    rows = []
    for line in read(QUEUE).split("\n"):
        cells = [c.strip() for c in line.strip().split("|")[1:-1]]
        if len(cells) == 5 and cells[0].isdigit():
            rows.append(dict(zip(("n", "source", "key", "status", "note"), cells)))
    return rows


def save(rows):
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    created = head_of(read(QUEUE)).get("created") or date.today().isoformat()
    out = ["---", "created: " + created, "---", "", "# Очередь генерации автотестов", "",
           "Статусы выводит скрипт из файлов генерации; руками меняется только skipped (команда skip).", "",
           HEADER, "|---|----------|------|--------|------------|"]
    for r in rows:
        out.append("| %s | %s | %s | %s | %s |" % (r["n"], r["source"], r["key"], r["status"], r["note"].replace("|", "/")))
    QUEUE.write_text("\n".join(out) + "\n", encoding="utf-8")


def origins():
    """Файл источника из TC.md -> ключ ТК."""
    found = {}
    for key in pp.autotest_keys():
        m = re.search(r"(?m)^- Файл источника:\s*(.+?)\s*$", read(pp.autotest_dir(key, create=False) / "TC.md"))
        if m and m.group(1) != "-":
            found[norm(m.group(1))] = key
    return found


def state_of(key):
    """Статус и примечание пункта по файлам генерации ключа."""
    folder = pp.autotest_dir(key, create=False)
    head = head_of(read(pp.plan_file(key, create=False)))
    check = read(folder / "TC-CHECK.md")
    if head.get("tc_status") == "FAIL" or re.search(r"(?m)^\W*СТАТУС:\s*FAIL", check):
        return "blocked", "проверка ТК FAIL - нужен исправленный ТК (TC-CHECK.md)"
    if head.get("plan_status") == "checked":
        run = head.get("run_status", "")
        return "done", ("запуск: " + run) if run else "-"
    if head:
        return "in-progress", "plan_status: " + head.get("plan_status", "-")
    if (folder / "TC.md").is_file():
        return "in-progress", "ТК разобран, плана нет"
    return "todo", "-"


def sync(rows):
    """Ключи у файлов ТК и статусы - из файлов генерации. skipped не трогает."""
    links = origins()
    for r in rows:
        if r["status"] == "skipped":
            continue
        if r["key"] == "-" and norm(r["source"]) in links:
            r["key"] = links[norm(r["source"])]
        if r["key"] != "-":
            status, note = state_of(r["key"])
            if not (status == "todo" and r["status"] == "blocked" and r["note"].startswith("разбор:")):
                r["status"], r["note"] = status, note
        elif r["status"] not in ("todo", "blocked"):
            r["status"] = "todo"
    return rows


def is_allure(folder):
    return any(folder.glob("*-result.json"))


def collect(target):
    """Аргумент add -> список источников (путь или ключ)."""
    path = Path(target)
    if KEY.fullmatch(target):
        return [target]
    if path.is_dir():
        return walk(path)
    if path.is_file():
        return keys_or_file(path)
    return []


def walk(folder):
    """Каталог Allure - один пункт; иначе файлы по расширению и вложенные каталоги по порядку имён."""
    if is_allure(folder):
        return [norm(folder)]
    items = []
    for sub in sorted(folder.iterdir()):
        if sub.name.startswith(".") or sub.name in SKIP_DIRS:
            continue
        if sub.is_dir():
            items.extend(walk(sub))
        elif sub.suffix.lower() in SUFFIXES:
            items.extend(keys_or_file(sub))
    return items


def keys_or_file(path):
    if path.suffix.lower() == ".txt":
        lines = [l.strip() for l in read(path).split("\n") if l.strip()]
        if lines and all(KEY.fullmatch(l) for l in lines):
            return lines
    return [norm(path)]


def cmd_add(targets):
    rows = load()
    known = {norm(r["source"]) for r in rows} | {r["key"] for r in rows if r["key"] != "-"}
    missing, added = [], 0
    for target in targets:
        items = collect(target)
        if not items:
            missing.append(target)
        for item in items:
            if item in known or norm(item) in known:
                continue
            known.add(item)
            rows.append({"n": str(len(rows) + 1), "source": item, "key": item if KEY.fullmatch(item) else "-",
                         "status": "todo", "note": "-"})
            added += 1
    if missing:
        print("НЕ НАЙДЕНО: " + ", ".join(missing) + " - нет такого каталога, файла или это не ключ вида CODE-T123")
    if not rows:
        print("ОЧЕРЕДЬ ПУСТА: добавлять нечего")
        return 1
    save(sync(rows))
    print("ДОБАВЛЕНО: %d · УЖЕ БЫЛО: %d · ВСЕГО: %d" % (added, len(rows) - added, len(rows)))
    print("ФАЙЛ: " + QUEUE.as_posix())
    return 0 if added else 1


def summary(rows):
    counts = {s: 0 for s in ("done", "in-progress", "todo", "blocked", "skipped")}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return "готово %d из %d · в работе %d · ждут %d · заблокировано %d · пропущено %d" % (
        counts["done"], len(rows), counts["in-progress"], counts["todo"], counts["blocked"], counts["skipped"])


def current(rows):
    """Следующий пункт: сначала в работе, потом первый todo."""
    for status in ("in-progress", "todo"):
        for r in rows:
            if r["status"] == status:
                return r
    return None


def cmd_status():
    rows = load()
    if not rows:
        print("ОЧЕРЕДИ НЕТ: " + QUEUE.as_posix())
        return 1
    save(sync(rows))
    print("ОЧЕРЕДЬ: " + summary(rows))
    for r in rows:
        if r["status"] in ("blocked", "in-progress"):
            print("%s %s · %s · %s · %s" % (r["status"].upper(), r["n"], r["source"], r["key"], r["note"]))
    nxt = current(rows)
    print("СЛЕДУЮЩИЙ: " + ("%s · %s" % (nxt["n"], nxt["source"]) if nxt else "нет"))
    return 0


def cmd_mark(which, status, reason):
    rows = sync(load())
    for r in rows:
        if which in (r["n"], r["key"], r["source"]):
            if status == "skipped":
                r["status"], r["note"] = "skipped", reason or "пропущен человеком"
            else:
                r["status"], r["note"] = "blocked", "разбор: " + (reason or "ТК не разобран")
            save(sync(rows))
            print(("ПРОПУЩЕН: " if status == "skipped" else "ЗАБЛОКИРОВАН: ") + "%s · %s" % (r["n"], r["source"]))
            return 0
    print("НЕТ ПУНКТА: " + which)
    return 1


def cmd_clear():
    rows = load()
    if not rows:
        print("ОЧЕРЕДИ НЕТ")
        return 1
    QUEUE.unlink()
    print("ОЧЕРЕДЬ УДАЛЕНА: пунктов было %d; файлы генерации .gigacode/data/autotest/<ключ>/ не тронуты" % len(rows))
    return 0


def main(args):
    if args[:1] == ["add"] and len(args) > 1:
        return cmd_add(args[1:])
    if args == ["status"]:
        return cmd_status()
    if args[:1] in (["skip"], ["block"]) and len(args) > 1:
        return cmd_mark(args[1], "skipped" if args[0] == "skip" else "blocked", " ".join(args[2:]))
    if args == ["clear"]:
        return cmd_clear()
    print("Использование: autotest_queue.py add <каталог | файл со списком ключей | ключ ...> | status | skip|block <№ | ключ> <причина> | clear")
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
