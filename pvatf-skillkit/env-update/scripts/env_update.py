#!/usr/bin/env python3
"""Обновление версии фрейма PVATF в проекте (скилл env-update). Запуск из корня проекта:

  python3 <скилл>/scripts/env_update.py versions [--json]        - где объявлена версия фрейма, текущая версия
  python3 <скилл>/scripts/env_update.py latest <файл>            - самая новая версия в сохранённых release notes
  python3 <скилл>/scripts/env_update.py bump <версия> [--only 1,3] - заменить текущую версию на новую (с копией файлов)
  python3 <скилл>/scripts/env_update.py rollback                 - вернуть файлы сборки из копии
  python3 <скилл>/scripts/env_update.py reset                    - стереть копии и состояние прошлого обновления
  python3 <скилл>/scripts/env_update.py usages <файл имён>       - где в коде проекта встречаются имена из списка
  python3 <скилл>/scripts/env_update.py errors                   - ошибки компиляции из ENV.json, сгруппированные по файлам

Копии файлов сборки и состояние - в .gigacode/data/autotest/env-update/. Повторный bump на ту же
версию ничего не меняет. Python 3.8+, только стандартная библиотека.
Код выхода: 0 - выполнено, 1 - нечего делать или не найдено, 2 - неверные аргументы.
"""
import json
import re
import shutil
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frame_versions as fv  # noqa: E402

DATA = Path(".gigacode") / "data" / "autotest"
WORK = DATA / "env-update"
STATE = WORK / "state.json"
BACKUP = WORK / "backup"
CODE_SUFFIXES = (".java", ".kt", ".properties", ".yml", ".yaml", ".xml", ".json", ".gradle", ".kts")


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state):
    WORK.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def current_version(decls):
    if not decls:
        return None
    counts = Counter(d["value"] for d in decls)
    top = max(counts.values())
    return max((v for v, c in counts.items() if c == top), key=fv.version_key)


def cmd_versions(args):
    decls = fv.declarations(".")
    current = current_version(decls)
    if "--json" in args:
        print(json.dumps({"current": current, "declarations": decls}, ensure_ascii=False, indent=2))
        return 0 if decls else 1
    if not decls:
        print("ВЕРСИЯ: не найдена - в файлах сборки нет зависимостей и свойств фрейма (метки: " + ", ".join(fv.FRAME_MARKERS) + ")")
        return 1
    print("ТЕКУЩАЯ: " + current)
    for number, d in enumerate(decls, 1):
        mark = "" if d["value"] == current else "  (другая версия - bump её не трогает без --only)"
        print("%d · %s:%d · %s · %s = %s · для %s%s" % (number, d["file"], d["line"], d["kind"], d["name"], d["value"], d["via"], mark))
    return 0


def cmd_latest(args):
    if not args:
        print("Использование: env_update.py latest <файл с release notes> [--allow-snapshot]")
        return 2
    text = fv.read(args[0])
    if not text:
        print("Файл пуст или не читается: " + args[0])
        return 1
    found = OrderedDict()
    for m in re.finditer(r"(?<![\w.])v?([0-9]+\.[0-9]+(?:\.[0-9]+){0,2}(?:-[0-9A-Za-z.]+)?)(?![\w.])", text):
        value = m.group(1)
        if "SNAPSHOT" in value.upper() and "--allow-snapshot" not in args:
            continue
        found.setdefault(value, 0)
        found[value] += 1
    if not found:
        print("ВЕРСИЙ НЕТ: в файле нет номеров версий вида 3.5.0")
        return 1
    ordered = sorted(found, key=fv.version_key, reverse=True)
    stable = [v for v in ordered if "-" not in v]
    print("САМАЯ НОВАЯ: " + (stable[0] if stable else ordered[0]))
    if stable and ordered[0] != stable[0]:
        print("ЗАМЕТКА: есть предварительная " + ordered[0] + " - берём стабильную " + stable[0])
    print("ВСЕ (по убыванию): " + ", ".join(ordered[:15]))
    return 0


def cmd_bump(args):
    if not args or not fv.VERSION.match(args[0]):
        print("Использование: env_update.py bump <версия, напр. 3.5.0> [--only 1,3]")
        return 2
    target = args[0]
    decls = fv.declarations(".")
    if not decls:
        print("ВЕРСИЯ: не найдена - менять нечего")
        return 1
    current = current_version(decls)
    if "--only" in args:
        index = args.index("--only")
        picked = {int(x) for x in args[index + 1].split(",") if x.strip().isdigit()} if index + 1 < len(args) else set()
        chosen = [d for n, d in enumerate(decls, 1) if n in picked]
    else:
        chosen = [d for d in decls if d["value"] == current]
    todo = [d for d in chosen if d["value"] != target]
    if not todo:
        print("УЖЕ: все выбранные объявления уже " + target + " - ничего не менял")
        return 1
    if fv.version_key(target) < fv.version_key(current):
        print("ВНИМАНИЕ: " + target + " старше текущей " + current + " - это понижение версии")
    state = load_state()
    state.setdefault("from", current)
    state["to"] = target
    state.setdefault("backups", [])
    BACKUP.mkdir(parents=True, exist_ok=True)
    by_file = OrderedDict()
    for d in todo:
        by_file.setdefault(d["file"], []).append(d)
    changed = []
    for name, items in by_file.items():
        path = Path(name)
        copy = BACKUP / name
        if not copy.exists():
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(path), str(copy))
            state["backups"].append(name)
        lines = path.read_text(encoding="utf-8").split("\n")
        for d in items:
            line = lines[d["line"] - 1]
            new = re.sub(r"(?<![\w.])" + re.escape(d["value"]) + r"(?![\w.])", target, line, count=1)
            if new == line:
                print("НЕ ЗАМЕНЕНО: " + name + ":" + str(d["line"]) + " - значение " + d["value"] + " не найдено в строке")
                continue
            lines[d["line"] - 1] = new
            changed.append({"file": name, "line": d["line"], "name": d["name"], "was": d["value"], "now": target})
            print("ИЗМЕНЕНО: %s:%d · %s · %s -> %s" % (name, d["line"], d["name"], d["value"], target))
        path.write_text("\n".join(lines), encoding="utf-8")
    state.setdefault("changed", [])
    state["changed"].extend(changed)
    save_state(state)
    print("ИТОГ: изменено строк " + str(len(changed)) + "; копии файлов - " + str(BACKUP).replace("\\", "/"))
    return 0 if changed else 1


def cmd_rollback(args):
    state = load_state()
    backups = state.get("backups", [])
    if not backups:
        print("КОПИЙ НЕТ: откатывать нечего")
        return 1
    for name in backups:
        shutil.copyfile(str(BACKUP / name), name)
        print("ВОЗВРАЩЁН: " + name)
    shutil.rmtree(str(BACKUP), ignore_errors=True)
    save_state({"rolled_back_from": state.get("to"), "version": state.get("from")})
    print("ИТОГ: файлов возвращено " + str(len(backups)))
    return 0


def cmd_usages(args):
    if not args:
        print("Использование: env_update.py usages <файл: по одному имени класса, метода или ключа на строку>")
        return 2
    names = [l.strip() for l in fv.read(args[0]).splitlines() if l.strip() and not l.strip().startswith("#")]
    if not names:
        print("Список имён пуст: " + args[0])
        return 1
    files = [f for f in fv.walk(".") if f.suffix in CODE_SUFFIXES]
    total = 0
    for name in names:
        pattern = re.compile(r"(?<![\w$])" + re.escape(name) + r"(?![\w$])")
        hits = []
        for f in files:
            for number, line in enumerate(fv.read(f).splitlines(), 1):
                if pattern.search(line):
                    hits.append(fv.rel(".", f) + ":" + str(number) + ": " + line.strip()[:160])
        total += len(hits)
        print("ИМЯ: " + name + " · мест " + str(len(hits)))
        for hit in hits[:20]:
            print("  " + hit)
        if len(hits) > 20:
            print("  ... ещё " + str(len(hits) - 20))
    print("ИТОГ: мест " + str(total))
    return 0 if total else 1


def cmd_errors(args):
    try:
        report = json.loads((DATA / "ENV.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("НЕТ ENV.json: сначала запусти env_check.py (скилл env-check)")
        return 1
    errors = report.get("compile", {}).get("errors", [])
    if report.get("compile", {}).get("status") == "ok":
        print("ОШИБОК НЕТ: компиляция ok")
        return 1
    groups = OrderedDict()
    for line in errors:
        m = re.search(r"([\w/\\.\-]+\.(?:java|kt))[:\[]\s*\[?(\d+)", line)
        key = m.group(1).replace("\\", "/") if m else "-"
        groups.setdefault(key, []).append(line)
    symbols = Counter(m.group(1) for line in errors for m in [re.search(r"symbol:\s+\w+\s+([\w.]+)", line)] if m)
    for key, lines in groups.items():
        print("ФАЙЛ: " + key + " · ошибок " + str(len(lines)))
        for line in lines[:10]:
            print("  " + line[:220])
    for name, count in symbols.most_common(20):
        print("СИМВОЛ: " + name + " · " + str(count))
    print("ИТОГ: файлов " + str(len(groups)) + ", строк ошибок " + str(len(errors)))
    return 0


def cmd_reset(args):
    shutil.rmtree(str(BACKUP), ignore_errors=True)
    if STATE.exists():
        STATE.unlink()
    print("СБРОШЕНО: копий и состояния прошлого обновления нет")
    return 0


COMMANDS = {"versions": cmd_versions, "latest": cmd_latest, "bump": cmd_bump, "rollback": cmd_rollback,
            "reset": cmd_reset, "usages": cmd_usages, "errors": cmd_errors}


def main(args):
    if not args or args[0] not in COMMANDS:
        print("Использование: env_update.py " + " | ".join(COMMANDS) + " (подробности - в начале файла)")
        return 2
    return COMMANDS[args[0]](args[1:])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
