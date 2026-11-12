#!/usr/bin/env python3
"""Следующее действие процесса (скилл orchestrator). Запуск из корня проекта:

  python3 <каталог скилла>/scripts/next_action.py              - миграция: что делать дальше
  python3 <каталог скилла>/scripts/next_action.py M-012        - миграция: можно ли взять этот юнит
  python3 <каталог скилла>/scripts/next_action.py M-001..M-005 - миграция: пачка (или список через запятую)
  python3 <каталог скилла>/scripts/next_action.py autotest     - генерация автотестов: что делать дальше
  python3 <каталог скилла>/scripts/next_action.py autotest TC-123 - генерация: состояние этого тест-кейса
  python3 <каталог скилла>/scripts/next_action.py env [check|setup|update] - окружение: что делать дальше
  python3 <каталог скилла>/scripts/next_action.py review [файл теста] - проверка существующего автотеста

Печатает строку «ДЕЙСТВИЕ: ...» и строку «ПОЧЕМУ: ...», иногда «ЗАМЕТКА: ...». Файлы процессов не
меняет. Единственное, что пишет, - агенты набора: копирует <каталог скилла>/agents/*.md в
.gigacode/agents/ проекта, если их там нет или они отличаются.
Python 3.8+, только стандартная библиотека. Код выхода: 0 всегда, кроме неверных аргументов (2).
"""
import json
import re
import sys
from pathlib import Path

# interactive - pvatf-skillkit (вопросы человеку), auto - pvatf-skillkit-auto (решения без человека)
KIT_MODE = "interactive"

DATA = Path(".gigacode") / "data"
MIGRATION = DATA / "migration"
AUTOTEST = DATA / "autotest"
REVIEW = DATA / "autotest-review"
AGENTS = Path(".gigacode") / "agents"
BATCH_LIMIT = 5
STATUSES = ["todo", "in-progress", "done", "blocked"]
SKILL_DIR = Path(__file__).resolve().parent.parent


def say(action, why):
    print("ДЕЙСТВИЕ: " + action)
    print("ПОЧЕМУ: " + why)


def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


# ---------- общий разбор markdown ----------

def front_matter(text):
    head = {}
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return head
    for line in lines[1:]:
        if line.strip() == "---":
            break
        colon = line.find(":")
        if colon > 0:
            head[line[:colon].strip()] = line[colon + 1:].strip()
    return head


def section(text, number):
    start = re.search(r"(?m)^## " + re.escape(number), text)
    if not start:
        return ""
    end = re.compile(r"(?m)^## ").search(text, start.end())
    return text[start.start():end.start() if end else len(text)]


def cells(line):
    trimmed = line.strip()
    if not trimmed.startswith("|"):
        return []
    raw = trimmed[1:].split("|")
    while raw and raw[-1] == "":
        raw.pop()  # хвостовые пустые ячейки отбрасываются
    return [c.strip() for c in raw]


def parse_int(value):
    try:
        return int(str(value).strip())
    except ValueError:
        return 0


# ---------- агенты ----------

def normalized(content):
    text = content.decode("utf-8", errors="replace")
    if text.startswith("﻿"):
        text = text[1:]
    return re.sub(r"[ \t]+\n", "\n", text.replace("\r", "")).strip()


def install_agents():
    source = SKILL_DIR / "agents"
    if not source.is_dir():
        print("ЗАМЕТКА: не нашёл каталог agents скилла orchestrator - агенты pvatf-* не проверены;"
              " запускай как python3 <каталог скилла>/scripts/next_action.py")
        return []
    home_agents = Path.home() / ".gigacode" / "agents"
    written = []
    for path in sorted(source.glob("*.md")):
        content = path.read_bytes()
        expected = normalized(content)
        target = AGENTS / path.name
        if target.is_file() and normalized(target.read_bytes()) == expected:
            continue
        in_home = home_agents / path.name
        # такой же агент уже стоит у пользователя и в проекте его нет - GigaCode его видит
        if not target.exists() and in_home.is_file() and normalized(in_home.read_bytes()) == expected:
            continue
        existed = target.exists()
        AGENTS.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        written.append(path.name + (" (обновлён: текст отличался)" if existed else " (новый)"))
    return written


# ---------- миграция ----------

class Unit:
    def __init__(self, uid, utype, status, deps):
        self.id, self.type, self.status, self.deps = uid, utype, status, deps


def units_of(text, broken):
    units = []
    for line in section(text, "4.").split("\n"):
        row = cells(line)
        if line.strip().startswith("| M-") and (len(row) < 8 or not re.fullmatch(r"M-[0-9]+", row[0])
                                                 or row[-1] not in STATUSES):
            broken.append(line.strip())
            continue
        if len(row) >= 8 and re.fullmatch(r"M-[0-9]+", row[0]):
            units.append(Unit(row[0], row[2], row[7], re.findall(r"M-[0-9]+", row[5])))
    return units


def archived_of(text):
    ids = []
    line = re.search(r"(?m)^В архиве[^:]*:(.*)$", text)
    if not line:
        return ids
    for part in re.finditer(r"M-([0-9]+)(?:\s*\.\.\s*M-([0-9]+))?", line.group(1)):
        start = int(part.group(1))
        stop = int(part.group(2)) if part.group(2) else start
        width = len(part.group(1))
        for i in range(start, stop + 1):
            uid = "M-" + str(i).zfill(width)
            if uid not in ids:
                ids.append(uid)
    return ids


def questions(text, markup_only):
    found = []
    current = None
    markup = False
    for line in section(text, "6.").split("\n"):
        q = re.match(r"^- (Q-[0-9]+)", line) if line.strip() else None
        if q:
            current = q.group(1)
            markup = "относится к: разметка:" in line
        elif current and re.fullmatch(r"- ответ:\s*-\s*", line.strip()) and (markup or not markup_only):
            found.append(current)
    return found


def markup_questions(text):
    return questions(text, True) if KIT_MODE == "auto" else []


def open_questions(text):
    found = questions(text, False)
    if KIT_MODE == "auto":
        marks = markup_questions(text)
        found = [q for q in found if q not in marks]
    return found


def open_questions_note(text):
    found = open_questions(text)
    if not found:
        return ""
    if KIT_MODE == "auto":
        return "; вопросы без ответа: " + ", ".join(found) + " - доведи их до решения без человека (orchestrator, references/questions.md)"
    return "; вопросы без ответа: " + ", ".join(found) + " - если пользователь ответил, передай ответы в migration-map дословно"


def card_rows(uid):
    card = read(MIGRATION / "units" / (uid + ".md"))
    if card is None:
        return None
    return [row for row in (cells(line) for line in card.split("\n"))
            if len(row) >= 5 and re.fullmatch(r"S-[0-9]+", row[0])]


def core_steps_left(uid):
    rows = card_rows(uid)
    if rows is None:
        return 0
    return sum(1 for row in rows if re.fullmatch(r"разбор|env|core", row[1]) and row[4] != "done")


def allowed(unit, core):
    if not core or unit.type == "env":
        return True
    return unit.type == "tech" and core_steps_left(unit.id) > 0


def next_step(unit):
    if unit.type != "tech":
        return ""
    rows = card_rows(unit.id)
    if rows is None:
        return "; карточки units/" + unit.id + ".md нет"
    done = sum(1 for row in rows if row[4] == "done")
    pending = [row for row in rows if row[4] != "done"]
    nxt = ", следующий " + pending[0][0] + " · " + pending[0][1] if pending else ""
    return "; подшагов done " + str(done) + " из " + str(len(rows)) + nxt


def find(units, uid):
    for unit in units:
        if unit.id == uid:
            return unit
    return None


def dep_satisfied(dep, units, archived, core):
    """Зависимость выполнена: юнит done или в архиве. При scope: core юнит tech считается
    выполненным, когда сделаны его подшаги разбор, env и core."""
    if dep in archived:
        return True
    unit = find(units, dep)
    if unit is None:
        return False
    if unit.status == "done":
        return True
    return core and unit.type == "tech" and core_steps_left(dep) == 0


def deps_done(unit, units, archived, core):
    return all(dep_satisfied(dep, units, archived, core) for dep in unit.deps)


def map_size_note(text):
    lines = len(text.splitlines())
    if lines > 600:
        print("ЗАМЕТКА: карта " + str(lines) + " строк - в итоговом ответе предложи: «напишите: сожми карту»")


def requested(request, units, archived, core):
    ids = []
    rng = re.search(r"(M-[0-9]+)\s*\.\.\s*(M-[0-9]+)", request)
    if rng:
        inside = False
        for unit in units:
            if unit.id == rng.group(1):
                inside = True
            if inside:
                ids.append(unit.id)
            if unit.id == rng.group(2):
                break
    else:
        ids = re.findall(r"M-[0-9]+", request)
    notes, batch, earlier = [], [], []
    for uid in ids:
        unit = find(units, uid)
        if unit is None:
            notes.append(uid + " нет в таблице" + (" (в архиве - done)" if uid in archived else ""))
            continue
        if unit.status == "done":
            notes.append(uid + " уже done - пропущен")
            continue
        if not allowed(unit, core):
            notes.append(uid + " недоступен при scope: core")
            continue
        if len(batch) == BATCH_LIMIT:
            notes.append(uid + " - следующей пачкой (больше " + str(BATCH_LIMIT) + ")")
            continue
        for dep in unit.deps:
            if not (dep in earlier or dep_satisfied(dep, units, archived, core)):
                dep_unit = find(units, dep)
                say("нельзя", uid + " ждёт " + dep + " (" + ("нет в таблице" if dep_unit is None else dep_unit.status) + ")"
                    + ("; " + "; ".join(notes) if notes else ""))
                return
        batch.append(uid)
        earlier.append(uid)
    tail = "; " + "; ".join(notes) if notes else ""
    if not batch:
        say("нечего делать", "; ".join(notes) if notes else "юниты не найдены")
    elif len(batch) == 1:
        say("migration-step " + batch[0], "назван пользователем" + tail)
    else:
        say("migration-step пачка: " + ", ".join(batch), "пачка проверена" + tail)


def migration(args):
    map_file = MIGRATION / "MIGRATION-MAP.md"
    text = read(map_file)
    if text is None:
        say("migration-map", "карты нет - строим с Этапа 1")
        return
    head = front_matter(text)
    status = head.get("map_status", "-")
    if KIT_MODE == "auto":
        marks = markup_questions(text)
        if marks:
            say("вопросы разметки", "ждём ответов человека: " + ", ".join(marks)
                + " - запусти migration-map: он выведет блок вопросов (Этап 2, шаг 1б) и остановится;"
                + " ответы приходят сообщением с JSON {\"answers\": {\"Q-<n>\": \"<значение>\"}}")
            return
    if status == "building":
        say("migration-map", "карта строится, продолжить с этапа " + head.get("map_stage", "?") + open_questions_note(text))
        return
    if status == "review":
        if KIT_MODE == "auto":
            say("одобрение карты", "карта построена, но не утверждена: запусти migration-map - самопроверка Этапа 6 и утверждение без человека")
        else:
            say("одобрение карты", "карта построена, но не одобрена: покажи сводку и спроси «Карту утверждаем? да/нет»")
        return
    found = open_questions(text)
    if found:
        if KIT_MODE == "auto":
            say("вопросы", "в разделе 6 без ответа: " + ", ".join(found) + " - доведи их до решения без человека (references/questions.md), потом снова next_action.py")
        else:
            say("вопросы", "в разделе 6 без ответа: " + ", ".join(found) + " - юниты не запускаются")
        return
    broken = []
    units = units_of(text, broken)
    archived = archived_of(text)
    core = head.get("scope", "full") == "core"
    if broken:
        say("карта повреждена", "в разделе 4 строки юнитов не разбираются (нужно 8 колонок и статус "
            + "/".join(STATUSES) + "): " + " | ".join(broken) + " - исправь таблицу, юниты не запускаются")
        return
    if not units and not archived:
        say("карта повреждена", "в разделе 4 нет ни одного юнита и строки «В архиве» - исправь таблицу, юниты не запускаются")
        return
    if args:
        requested(args[0], units, archived, core)
        map_size_note(text)
        return
    for unit in units:
        if unit.status == "in-progress" and allowed(unit, core):
            say("migration-step " + unit.id, "юнит in-progress - продолжить с места остановки" + next_step(unit))
            map_size_note(text)
            return
    for unit in units:
        if unit.status == "todo" and allowed(unit, core) and deps_done(unit, units, archived, core):
            say("migration-step " + unit.id, "первый todo сверху, все зависимости done" + next_step(unit))
            map_size_note(text)
            return
    all_done = all(u.status == "done" for u in units)
    if core and all(not allowed(u, True) for u in units if u.status != "done"):
        say("ядро готово", "scope: core - ядро переведено, тесты не тронуты; дальше - только по просьбе о полной миграции")
        return
    if not all_done:
        blocked = [u.id for u in units if u.status == "blocked"]
        say("заблокировано", "доступных юнитов нет; blocked: " + (", ".join(blocked) if blocked else "-")
            + "; остальные todo ждут их. Покажи блокеры из карточек и строки «решить человеку»")
        return
    review = head.get("review_status", "-")
    rnd = parse_int(head.get("review_round", "0"))
    if review == "clean":
        say("финал", "все юниты done, проверка миграции чистая (круг " + str(rnd) + ")")
    elif review == "findings" and rnd >= 3:
        say("проверка не сходится", "три круга проверки с находками - покажи сводку последнего круга, дальше решает человек")
    else:
        say("migration-review", "все юниты done, проверка миграции " + ("ещё не запускалась" if rnd == 0 else "круг " + str(rnd + 1)))
    map_size_note(text)


# ---------- окружение ----------

def env_state():
    env = AUTOTEST / "ENV.json"
    try:
        return json.loads(env.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def env(args):
    """Окружение: незаконченное обновление продолжается; иначе - запрошенный режим (check / setup / update)."""
    mode = args[0] if args and args[0] in ("check", "setup", "update") else "check"
    update = read(AUTOTEST / "ENV-UPDATE.md")
    if update is not None:
        head = front_matter(update)
        status = head.get("update_status", "-")
        if status == "in-progress":
            say("env-update", "обновление фрейма не закончено (этап " + head.get("update_stage", "?") + ", "
                + head.get("from", "-") + " -> " + head.get("to", "-") + ") - продолжить с этого этапа")
            return
    state = env_state()
    if mode == "update":
        if state is not None and state.get("compile", {}).get("status") == "failed":
            say("env-setup", "последняя проверка: компиляция failed - обновлять фрейм на неработающем проекте нельзя;"
                " сначала настройка окружения или правка человеком")
            return
        say("env-update", "обновить фрейм до последней версии из release notes")
        return
    if mode == "setup":
        say("env-setup", "проверить окружение и доставить недостающее" + (
            "" if state is None else "; последняя проверка: " + str(state.get("status", "-"))))
        return
    say("env-check", "проверка окружения" + ("" if state is None else "; прошлая: " + str(state.get("status", "-"))
        + " (" + str(state.get("checked_at", "-")) + ")"))


# ---------- генерация автотестов ----------

PLAN_STATUSES = ["draft", "planned", "generating", "assembled", "checked"]


def autotest(args):
    """Генерация автотестов: сначала окружение, потом незаконченный план или новый тест-кейс.
    Аргумент - ключ ТК (CODE-T123) или путь к файлу ТК (новый тест-кейс)."""
    state = env_state()
    if state is None or state.get("status") == "failed":
        codes = [p.get("code", "-") for p in (state or {}).get("problems", []) if p.get("severity") == "critical"]
        why = "окружение не проверено" if state is None else "проверка окружения failed: " + ", ".join(codes[:3])
        say("env-check", why + " - генерация не запускается, пока проверка не вернёт ok или warning")
        return
    want = args[0] if args else None
    if want and ("/" in want or "\\" in want or re.search(r"\.(md|xml|json)$", want)):
        say("autotest-plan", "новый тест-кейс из файла " + want + " - разбор, проверка, план")
        return
    rows = []
    for plan in sorted(AUTOTEST.glob("*/PLAN.md")) if AUTOTEST.is_dir() else []:
        head = front_matter(read(plan) or "")
        rows.append((plan.parent.name, head.get("plan_status", "-"), head.get("tc_status", "-")))
    if want:
        for tc, status, tc_status in rows:
            if tc == want:
                say(*autotest_step(tc, status, tc_status))
                return
        tc_file = AUTOTEST / want / "TC.md"
        say("autotest-plan " + want, ("тест-кейс разобран, плана нет" if tc_file.is_file() else "плана для " + want + " нет")
            + " - разбор, проверка, план")
        return
    for tc, status, tc_status in rows:
        if status != "checked" and tc_status != "FAIL":
            say(*autotest_step(tc, status, tc_status))
            return
    failed = [tc for tc, _, tc_status in rows if tc_status == "FAIL"]
    note = "; тест-кейсы с FAIL ждут исправления: " + ", ".join(failed) if failed else ""
    say("autotest-plan", "незаконченных тест-кейсов нет - нужен новый: попроси путь к файлу ТК (md, xml или json)" + note)


def autotest_step(tc, status, tc_status):
    if tc_status == "FAIL":
        return ("заблокировано", tc + ": проверка тест-кейса FAIL - покажи находки из .gigacode/data/autotest/" + tc
                + "/TC-CHECK.md, нужен исправленный ТК")
    if status not in PLAN_STATUSES or status == "draft":
        return ("autotest-plan " + tc, "plan_status: " + status + " - план не утверждён, достроить и проверить")
    if status == "planned":
        return ("autotest-gen " + tc, "план готов - сгенерировать шаги и собрать тест-класс")
    if status == "generating":
        return ("autotest-gen " + tc, "генерация не закончена - продолжить с первого G со статусом todo")
    if status == "assembled":
        return ("autotest-gen " + tc, "тест-класс собран - проверка (at_tools.py check)")
    if KIT_MODE == "auto":
        return ("финал " + tc, "тест-класс прошёл проверку - покажи итог из CHECK.md")
    return ("финал " + tc, "тест-класс прошёл проверку - покажи итог из CHECK.md и предложи разметку: «/orchestrator разметь тесты»"
            " и проверку по правилам: «/orchestrator проверь автотест <test_file>»")


# ---------- проверка существующего автотеста ----------

def review(args):
    """Проверка автотеста: окружение, потом незаконченная проверка или новая по файлу."""
    state = env_state()
    if state is None or state.get("status") == "failed":
        why = "окружение не проверено" if state is None else "проверка окружения failed"
        say("env-check", why + " - проверка автотеста компилирует проект, сначала окружение ok или warning")
        return
    want = args[0] if args else None
    rows = []
    for plan in sorted(REVIEW.glob("*/REVIEW-PLAN.md")) if REVIEW.is_dir() else []:
        head = front_matter(read(plan) or "")
        rows.append((head.get("file", "-"), head.get("review_status", "-")))
    if want:
        if not Path(want).is_file():
            say("нельзя", "файла " + want + " нет - нужен путь к тест-классу .java от корня проекта")
            return
        for file, status in rows:
            if Path(file).resolve() == Path(want).resolve() and status in ("found", "approved", "fixing"):
                say("autotest-review " + file, "review_status: " + status + " - продолжить проверку с того же места")
                return
        say("autotest-review " + want, "новая проверка - находки, план правок, правки, компиляция")
        return
    for file, status in rows:
        if status in ("found", "approved", "fixing"):
            say("autotest-review " + file, "review_status: " + status + " - проверка не закончена, продолжить")
            return
    say("autotest-review", "незаконченных проверок нет - нужен путь к тест-классу")


def main(args):
    installed = install_agents()
    if installed:
        say("агенты установлены", "в .gigacode/agents/ записаны: " + ", ".join(installed)
            + " - GigaCode читает агентов при запуске: перезапустите GigaCode (выйдите и запустите заново) и введите тот же запрос: /orchestrator <запрос человека дословно>")
        return 0
    if args and args[0] == "autotest":
        autotest(args[1:])
    elif args and args[0] == "env":
        env(args[1:])
    elif args and args[0] == "review":
        review(args[1:])
    elif args and args[0].startswith("-"):
        print("Использование: next_action.py [M-<n> | M-<a>..M-<b> | autotest [ключ ТК] | env [check|setup|update] | review [файл теста]]")
        return 2
    else:
        migration(args)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
