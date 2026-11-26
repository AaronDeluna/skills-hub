#!/usr/bin/env python3
"""Опись входных артефактов автотеста (скилл de-pvatf-autotest-plan). Запуск из корня проекта:

  python3 <скилл>/scripts/artifacts.py scan <ключ ТК> [<файл или каталог> ...] [--force]  - опись ARTIFACTS.md
  python3 <скилл>/scripts/artifacts.py task <ключ ТК>   - задание агенту pvatf-artifacts
  python3 <скилл>/scripts/artifacts.py merge <ключ ТК>  - проверить ответ агента ARTIFACTS-REVIEW.md и внести в опись

scan: источники - файл из строки «Файл источника» TC.md и файлы / каталоги, которые дал человек
(лог .log .txt .out, каталог allure-results/, файл *-result.json). Каждый HTTP-обмен, SQL и топик -
строка A-n описи: метод, адрес, заголовки (секреты - ***), тело запроса и ответа - файлы
outputs/artifacts/A-n-request.*, A-n-response.*, SQL - A-n.sql. Шаги ТК связываются со строками
описи по пути запроса или таблице SQL; служебные шаги старой реализации (формирование заголовков и
тела, десериализация, проверка «объект не null») помечаются. Разбор агентом нужен, если в описи есть
строки или ТК восстановлен из лога, Allure, кода.
task: печатает задание агенту pvatf-artifacts (передать дословно).
merge: ответ агента -> опись (пропущенные скриптом запросы, связи шагов, служебные шаги, значения
из выборки); строка «Разбор агентом: готов». Ошибки шаблона - строки ОШИБКА, код 1.

Файлы - рабочий каталог автотеста (OpenSpec: openspec/changes/<имя>/outputs/): ARTIFACTS.md,
ARTIFACTS-REVIEW.md, artifacts/. Повторный scan не трогает готовый разбор без --force.
Python 3.8+, только стандартная библиотека. Код выхода: 0 - готово, 1 - нужно действие или
ошибки ответа агента, 2 - неверный запуск или нет TC.md.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import log_parse as lp  # noqa: E402
import tc_common as tcc  # noqa: E402

HEAD = "| ID | Вид | Метод | Адрес | Заголовки | Тело запроса | Код | Тело ответа | Где |"
SECTIONS = ["Опись", "Связь шагов", "Служебные шаги", "Значения из выборки"]
TABLES = {"Опись": HEAD,
          "Связь шагов": "| Шаг | ID | Основание |",
          "Служебные шаги": "| Шаг | Почему |",
          "Значения из выборки": "| Значение | Шаг-источник | Поле | Шаги |"}
REVIEW_TABLES = {"Пропущено скриптом": "| Вид | Метод | Адрес или SQL | Заголовки | Тело | Где |",
                 "Связь шагов": "| Шаг | ID | Основание |",
                 "Служебные шаги": "| Шаг | Почему |",
                 "Значения из выборки": "| Значение | Шаг-источник | Поле | Шаги |"}
TEXT_SOURCES = (".log", ".txt", ".out")


def out(*lines):
    sys.stdout.buffer.write(("\n".join(str(l) for l in lines) + "\n").encode("utf-8"))


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def esc(value):
    return (str(value) if value not in (None, "") else "-").replace("|", "\\|").replace("\n", " ")


def rows_of(text, title):
    sect = re.search(r"(?ms)^## " + re.escape(title) + r"\s*\n(.*?)(?=^## |\Z)", text)
    rows = []
    for line in (sect.group(1) if sect else "").split("\n"):
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if cells and not set(cells[0]) <= set("-: ") and cells[0] not in ("ID", "Шаг", "Значение", "Вид"):
            if cells != ["нет"] and not all(c in ("-", "нет", "") for c in cells):
                rows.append(cells)
    return rows


def meta_line(text, name):
    m = re.search(r"(?m)^- " + re.escape(name) + r":\s*(.*)$", text)
    return m.group(1).strip() if m else ""


# ---------- источники ----------

def allure_results(path, key):
    """Каталог или файл *-result.json -> [(каталог, объект результата)] этого ТК."""
    folder = path if path.is_dir() else path.parent
    files = [path] if path.is_file() else sorted(path.glob("*-result.json"))
    found = []
    for f in files:
        try:
            obj = json.loads(read(f))
        except ValueError:
            continue
        blob = json.dumps(obj.get("links", []), ensure_ascii=False) + json.dumps(obj.get("labels", []), ensure_ascii=False) + str(obj.get("name", ""))
        if path.is_file() or key in blob:
            found.append((folder, obj))
    if not found and len(files) == 1:
        try:
            found = [(folder, json.loads(read(files[0])))]
        except ValueError:
            pass
    return found


def allure_walk(folder, node, step_name, found):
    for att in node.get("attachments") or []:
        source = folder / str(att.get("source", ""))
        text = read(source)
        if not text:
            continue
        kind = str(att.get("type", ""))
        for e in (lp.allure_events(text) if "html" in kind or "<" in text[:200] else lp.events(text)):
            if e["kind"] == "http" and not e["url"] and found and found[-1]["kind"] == "http" and not found[-1]["status"]:
                found[-1]["status"] = e["status"]  # вложение «Response» дополняет «Request»
                found[-1]["response"] = e["response"] or e["body"]
                continue
            e["where"] = source.name + (" · шаг Allure «" + step_name + "»" if step_name else "")
            found.append(e)
    for sub in node.get("steps") or []:
        allure_walk(folder, sub, str(sub.get("name", "")), found)


def collect(sources, key):
    found, skipped = [], []
    for raw in sources:
        path = Path(raw)
        if path.is_dir() or path.name.endswith("-result.json"):
            results = allure_results(path, key)
            if not results:
                skipped.append(raw + " (нет *-result.json этого ТК)")
            for folder, obj in results:
                allure_walk(folder, obj, "", found)
        elif path.suffix.lower() in TEXT_SOURCES and path.is_file():
            for e in lp.events(read(path)):
                e["where"] = path.name + ":" + str(e["line"])
                found.append(e)
        else:
            skipped.append(raw + (" (нет файла)" if not path.exists() else " (ТК из TMS или код - запросов не содержит)"))
    return [e for e in found if e["kind"] in ("http", "sql", "topic")], skipped


def body_file(folder, name, body):
    if not body:
        return "-"
    body = lp.mask(body)
    suffix = ".json"
    try:
        body = json.dumps(json.loads(body), ensure_ascii=False, indent=2)
    except ValueError:
        suffix = ".txt"
    target = folder / "artifacts" / (name + suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body + "\n", encoding="utf-8")
    return "artifacts/" + target.name


def inventory_row(folder, n, e):
    aid = "A-" + str(n)
    if e["kind"] == "http":
        headers = ", ".join(h + "=" + (lp.mask_header(h, v) if len(v) <= 40 else v[:37] + "...") for h, v in e["headers"]) or "-"
        return [aid, "http", e["method"], e["url"], headers, body_file(folder, aid + "-request", e["body"]),
                e["status"] or "-", body_file(folder, aid + "-response", e["response"]), e.get("where", "-")]
    if e["kind"] == "sql":
        target = folder / "artifacts" / (aid + ".sql")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(lp.mask(e["sql"]) + "\n", encoding="utf-8")
        first = re.sub(r"\s+", " ", e["sql"])[:150]
        return [aid, "sql", "-", first, "-", "artifacts/" + target.name, "-", "-", e.get("where", "-")]
    return [aid, "topic", e["direction"], e["topic"], "-", "-", "-", "-", e.get("where", "-")]


# ---------- связь шагов ----------

PATH = re.compile(r"(?<![\w:/])(/[A-Za-z0-9_\-{}.]+(?:/[A-Za-z0-9_\-{}.]+)+)")


def link_steps(tc, inventory, service):
    """Шаг ТК -> строка описи: по пути запроса (по порядку), по таблице SQL. Служебные шаги не связываются."""
    links, used = [], set()
    skip = {r[0] for r in service}
    for s in tc["steps"]:
        if str(s["n"]) in skip:
            continue
        both = s["action"] + " " + s["data"]
        paths = [p.rstrip("/") for p in PATH.findall(both)]
        target = None
        for p in paths:
            target = next((r for r in inventory if r[1] == "http" and r[0] not in used and lp.path_of(r[3]) == p), None)
            if target:
                links.append((str(s["n"]), target[0], "путь " + p))
                break
        if not target and re.search(r"(?i)\bselect\b|\bsql\b|\bбд\b|таблиц|запис", both):
            for r in inventory:
                tables = re.findall(r"(?i)\b(?:from|join|into|update)\s+([\w.]+)", read_sql(r))
                hit = [t for t in tables if t.lower() in both.lower()]
                if r[1] == "sql" and r[0] not in used and hit:
                    target = r
                    links.append((str(s["n"]), r[0], "таблица " + hit[0]))
                    break
        if target:
            used.add(target[0])
    return links


SQL_CACHE = {}


def read_sql(row):
    if row[1] != "sql":
        return ""
    return SQL_CACHE.get(row[0], row[3])


def service_steps(tc):
    found = []
    for s in tc["steps"]:
        reason = tcc.service_reason(s["action"] + " " + s["expected"])
        if reason:
            found.append((str(s["n"]), "скрипт: " + reason))
    return found


def render(key, sources, skipped, status, inventory, links, service, values):
    out_lines = ["# Артефакты " + key, "",
                 "- Источники: " + (", ".join(sources) or "-"),
                 "- Не разобрано: " + ("; ".join(skipped) or "-"),
                 "- Разбор агентом: " + status, ""]
    data = {"Опись": inventory, "Связь шагов": links, "Служебные шаги": service, "Значения из выборки": values}
    for title in SECTIONS:
        head = TABLES[title]
        out_lines += ["## " + title, "", head, "|" + "|".join("-" * (len(c) + 2) for c in head.strip("|").split("|")) + "|"]
        rows = data[title]
        out_lines += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows] or ["| нет |"]
        out_lines.append("")
    return "\n".join(out_lines)


# ---------- команды ----------

def load(key):
    folder = tcc.pp.autotest_dir(key, create=False)
    tc_path = folder / "TC.md"
    if not tc_path.is_file():
        out("НЕТ TC.md: " + str(tc_path).replace("\\", "/") + " - сначала tc_convert.py")
        return None, None
    return folder, tcc.parse_tc(tc_path)


def cmd_scan(key, args):
    folder, tc = load(key)
    if folder is None:
        return 2
    target = folder / "ARTIFACTS.md"
    if meta_line(read(target), "Разбор агентом") == "готов" and "--force" not in args:
        out("ОПИСЬ УЖЕ РАЗОБРАНА: " + str(target).replace("\\", "/") + " - не перезаписываю (заново: --force)")
        return 0
    origin = tc["fields"].get("Файл источника", "-")
    sources = [origin] if origin not in ("", "-") else []
    sources += [a for a in args if not a.startswith("--") and a not in sources]
    events, skipped = collect(sources, key)
    inventory = [inventory_row(folder, n, e) for n, e in enumerate(events, 1)]
    for e, r in zip(events, inventory):
        if e["kind"] == "sql":
            SQL_CACHE[r[0]] = e["sql"]
    service = service_steps(tc)
    links = link_steps(tc, inventory, service)
    source_kind = tc["fields"].get("Источник", "tms")
    need = bool(inventory) or source_kind in ("log", "allure", "code")
    status = "нужен" if need else "не нужен"
    target.write_text(render(key, sources, skipped, status, inventory, links, service, []), encoding="utf-8")
    http = sum(1 for r in inventory if r[1] == "http")
    sql = sum(1 for r in inventory if r[1] == "sql")
    out("ОПИСЬ: запросов %d · SQL %d · топиков %d · шагов связано %d из %d · служебных шагов %d" % (
        http, sql, len(inventory) - http - sql, len(links), len(tc["steps"]), len(service)))
    for s in skipped:
        out("НЕ РАЗОБРАНО: " + s)
    out("ФАЙЛ: " + str(target).replace("\\", "/"))
    out("РАЗБОР АГЕНТОМ: " + status + (" - artifacts.py task " + key + " -> агент pvatf-artifacts -> artifacts.py merge " + key if need else ""))
    return 1 if need else 0


def cmd_task(key):
    folder, tc = load(key)
    if folder is None:
        return 2
    text = read(folder / "ARTIFACTS.md")
    if not text:
        out("НЕТ ОПИСИ: сначала artifacts.py scan " + key)
        return 2
    root = Path(".").resolve()
    linked = {r[0] for r in rows_of(text, "Связь шагов")}
    service = {r[0] for r in rows_of(text, "Служебные шаги")}
    open_steps = [s for s in tc["steps"] if str(s["n"]) not in linked and str(s["n"]) not in service]
    lines = ["ЗАДАНИЕ для агента pvatf-artifacts (передай дословно, всё ниже этой строки):", "",
             "- Проект: " + str(root),
             "- Тест-кейс: " + str(root / folder / "TC.md"),
             "- Опись (читать, не менять): " + str(root / folder / "ARTIFACTS.md"),
             "- Тела запросов и ответов: " + str(root / folder / "artifacts"),
             "- Исходные артефакты: " + (meta_line(text, "Источники") or "-"),
             "- Ответ записать в: " + str(root / folder / "ARTIFACTS-REVIEW.md"),
             "- Шаги ТК без связи с описью и не служебные (проверь каждый):"]
    lines += ["  - шаг %d: %s" % (s["n"], s["action"][:160]) for s in open_steps] or ["  - нет"]
    out(*lines)
    return 0


def parse_review(text, tc, inventory_ids):
    errors, data = [], {}
    numbers = {str(s["n"]) for s in tc["steps"]}
    for title, head in REVIEW_TABLES.items():
        if not re.search(r"(?m)^## " + re.escape(title) + r"\s*$", text):
            errors.append("нет раздела «## " + title + "»")
        data[title] = rows_of(text, title)
        width = len(head.strip("|").split("|"))
        for r in data[title]:
            if len(r) != width:
                errors.append(title + ": строка «" + " | ".join(r)[:80] + "» - колонок " + str(len(r)) + ", нужно " + str(width))
    new_ids = set()
    for n, r in enumerate(data["Пропущено скриптом"], 1):
        if len(r) == 6 and r[0] not in ("http", "sql", "topic"):
            errors.append("Пропущено скриптом: вид «" + r[0] + "» - нужно http, sql или topic")
        new_ids.add("N-" + str(n))
    for r in data["Связь шагов"]:
        if len(r) == 3 and r[0] not in numbers:
            errors.append("Связь шагов: шага " + r[0] + " нет в TC.md")
        if len(r) == 3 and r[1] not in inventory_ids and r[1] not in new_ids and r[1] != "нет в артефактах":
            errors.append("Связь шагов: шаг " + r[0] + " - ID «" + r[1] + "» нет в описи (A-n, N-n из «Пропущено скриптом» или «нет в артефактах»)")
    for r in data["Служебные шаги"]:
        if len(r) == 2 and r[0] not in numbers:
            errors.append("Служебные шаги: шага " + r[0] + " нет в TC.md")
    for r in data["Значения из выборки"]:
        if len(r) == 4 and r[1] not in numbers:
            errors.append("Значения из выборки: шаг-источник «" + r[1] + "» нет в TC.md")
        if len(r) == 4 and (not r[0] or r[0] == "-"):
            errors.append("Значения из выборки: пустое значение")
    return errors, data


def cmd_merge(key):
    folder, tc = load(key)
    if folder is None:
        return 2
    text = read(folder / "ARTIFACTS.md")
    review = read(folder / "ARTIFACTS-REVIEW.md")
    if not text:
        out("НЕТ ОПИСИ: сначала artifacts.py scan " + key)
        return 2
    if not review:
        out("НЕТ ОТВЕТА АГЕНТА: " + str(folder / "ARTIFACTS-REVIEW.md").replace("\\", "/") + " - сначала агент pvatf-artifacts")
        return 1
    inventory = rows_of(text, "Опись")
    errors, data = parse_review(review, tc, {r[0] for r in inventory})
    if errors:
        for e in errors:
            out("ОШИБКА: " + e)
        out("ИТОГ: ответ агента не по шаблону - задание агенту снова, к нему строки ОШИБКА")
        return 1
    renamed = {}
    for n, r in enumerate(data["Пропущено скриптом"], 1):
        aid = "A-" + str(len(inventory) + 1)
        renamed["N-" + str(n)] = aid
        inventory.append([aid, r[0], r[1], r[2], r[3], r[4], "-", "-", "агент: " + r[5]])
    links = rows_of(text, "Связь шагов")
    linked = {r[0] for r in links}
    for r in data["Связь шагов"]:
        if r[0] not in linked:
            missing = r[1] == "нет в артефактах"
            links.append([r[0], "-" if missing else renamed.get(r[1], r[1]), "агент: " + ("нет в артефактах: " if missing else "") + r[2]])
    service = rows_of(text, "Служебные шаги")
    known = {r[0] for r in service}
    service += [[r[0], "агент: " + r[1]] for r in data["Служебные шаги"] if r[0] not in known]
    values = data["Значения из выборки"]
    sources = [s.strip() for s in meta_line(text, "Источники").split(",") if s.strip() not in ("", "-")]
    skipped = [s for s in meta_line(text, "Не разобрано").split("; ") if s not in ("", "-")]
    (folder / "ARTIFACTS.md").write_text(render(key, sources, skipped, "готов", inventory, links, service, values), encoding="utf-8")
    out("ИТОГ: разбор внесён · добавлено запросов %d · связей %d · служебных шагов %d · значений из выборки %d" % (
        len(data["Пропущено скриптом"]), len(links), len(service), len(values)))
    out("ФАЙЛ: " + str(folder / "ARTIFACTS.md").replace("\\", "/"))
    return 0


def main(argv):
    if len(argv) < 2 or argv[0] not in ("scan", "task", "merge"):
        out("Использование: artifacts.py scan <ключ ТК> [<файл или каталог> ...] [--force] | task <ключ ТК> | merge <ключ ТК>")
        return 2
    if argv[0] == "scan":
        return cmd_scan(argv[1], argv[2:])
    return cmd_task(argv[1]) if argv[0] == "task" else cmd_merge(argv[1])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
