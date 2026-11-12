#!/usr/bin/env python3
"""План генерации автотеста по тест-кейсу (скилл autotest-plan). Запуск из корня проекта:

  python3 <скилл>/scripts/tc_plan.py build <ключ ТК> [--force]  - черновик PLAN.md (plan_status: draft)
  python3 <скилл>/scripts/tc_plan.py validate <ключ ТК>         - проверка плана; всё сошлось -> plan_status: planned

build: шаги TC.md делятся на подшаги (два действия в одном шаге), каждому - тип, группа,
технология, уверенность, связь данных; шаги группируются в шаги генерации G-n; константы из
данных и ожидаемых результатов - в матрицу с источником хранения; классы проекта по
технологиям - в индекс для переиспользования. Читает ENV.json (паспорт проекта), если есть.
Существующий план со статусом не draft не перезаписывает без --force.
validate: нет UNKNOWN в шагах, каждый шаг в G, у каждой G есть справка, у констант есть источник,
имя класса и пакет - допустимые имена Java, tc_status не FAIL.
Python 3.8+, только стандартная библиотека. Код выхода: 0 - выполнено, 1 - план не сошёлся или
ТК FAIL, 2 - неверные аргументы или нет TC.md.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tc_common as tcc  # noqa: E402

SKILLS = Path(__file__).resolve().parent.parent.parent
GROUP_REF = {"integration": "tech-integration.md", "db": "tech-db.md", "kafka": "tech-kafka.md", "ui": "tech-ui.md",
             "mobile": "tech-mobile.md", "logs_metrics": "tech-logs-metrics.md", "tools": "tech-tools.md", "other": "tech-other.md"}
CLASS_HINTS = [("integration", r"RestService|WebSocketService|GrpcService|GraphQl|restClient\("),
               ("db", r"DatabaseService|OpenSearchService|dataBaseClient\("),
               ("kafka", r"KafkaService|producerClient\(|consumerClient\("),
               ("ui", r"@Page\b|PlaywrightPage|SelenidePage|extends \w*Page\b|@PageElement"),
               ("mobile", r"AndroidPage|IosPage|AndroidElement|IosElement"),
               ("logs_metrics", r"AuditFlow|JournalFlow|MetricsFlow|PvmAbyss|AuditService|JournalService"),
               ("tools", r"FixtureService|ContainerService|SberMockService|TogglerService|LauncherService|DataConverterService|OpenShift"),
               ("other", r"ValueService|SessionOpen|runInvocation")]
TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "f",
                     "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"]))
JAVA_NAME = re.compile(r"[A-Z][A-Za-z0-9]*")
JAVA_PACKAGE = re.compile(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*")


def esc(value):
    return str(value).replace("|", "\\|").replace("\n", "<br>") or "-"


def load_env():
    try:
        return json.loads((tcc.DATA / "ENV.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ---------- шаги ----------

def split_step(s):
    """Шаг с несколькими действиями -> подшаги n.1, n.2 (по «;», «, затем», « и » перед глаголом)."""
    parts = [p.strip(" ,.") for p in re.split(r";|,\s*затем\s+|,\s*после этого\s+|\s+и\s+(?=[а-яё]+(?:ть|ти|сь)\b)", s["action"]) if p.strip(" ,.")]
    acting = [p for p in parts if tcc.actions_in(p)]
    if len(parts) < 2 or len(acting) < 2:
        return [dict(s, id=str(s["n"]))]
    rows = []
    for index, part in enumerate(parts, 1):
        last = index == len(parts)
        rows.append({"n": s["n"], "id": "%d.%d" % (s["n"], index), "action": part,
                     "data": s["data"] if index == 1 or last else "", "expected": s["expected"] if last else ""})
    return rows


def classify_rows(rows, ui_lib):
    for r in rows:
        r["type"] = tcc.step_type(r["action"])
        if r["type"] == "UNKNOWN_TYPE":
            r["type"] = tcc.step_type(r["action"] + " " + r["expected"])
        group, tech, label, conf, found = tcc.classify(r["action"] + " " + r["data"])
        if group == "UNKNOWN_GROUP":
            group, tech, label, conf, found = tcc.classify(r["expected"])
            conf = "MEDIUM" if conf == "HIGH" else conf
        r.update(group=group, tech=tech, label=label, conf=conf, why=", ".join(found[:3]) or "-")
    for index, r in enumerate(rows):
        if r["group"] != "UNKNOWN_GROUP":
            continue
        near = [rows[i] for i in (index - 1, index + 1) if 0 <= i < len(rows) and rows[i]["group"] != "UNKNOWN_GROUP"]
        if near:
            r.update(group=near[0]["group"], tech=near[0]["tech"], label=near[0]["label"], conf="LOW",
                     why="унаследовано от шага " + near[0]["id"])
    for r in rows:
        if r["group"] == "ui":
            r["tech"] = "Работа с UI Selenide" if "selenide" in ui_lib else "Работа с UI Playwright"
    last_op = {}
    for r in rows:
        refs = re.findall(r"(?:из|на|в)\s+шаг[аеу]?\s*(?:№\s*)?(\d+)", tcc.lower(r["action"] + " " + r["data"]))
        low = tcc.lower(r["action"] + " " + r["expected"])
        if refs:
            r["bind"] = "uses " + refs[0]
        elif r["type"] == "ASSERT" and r["group"] in last_op and re.search(r"ответ|результат|код|пол[еяю]|jsonpath|запис|сообщени|значени", low):
            r["bind"] = "uses " + last_op[r["group"]]
        elif r["type"] in ("OPERATION", "AUTH_SESSION") and r["group"] in ("integration", "db", "kafka", "other"):
            r["bind"] = "produces"
        else:
            r["bind"] = "-"
        if r["type"] in ("OPERATION", "AUTH_SESSION"):
            last_op[r["group"]] = r["id"]
    return rows


def gen_steps(rows):
    """Шаги генерации: новая G при смене группы или технологии, при переходе на новый экран UI,
    после 4 шагов в одной G. Проверка своего запроса остаётся в G запроса."""
    groups, current = [], None
    for r in rows:
        fresh = (current is None or r["group"] != current["group"] or r["tech"] != current["tech"]
                 or (r["group"] in ("ui", "mobile") and r["type"] == "NAVIGATION")
                 or (len(current["rows"]) >= 4 and not r["bind"].startswith("uses")))
        if fresh:
            current = {"id": "G-%d" % (len(groups) + 1), "group": r["group"], "tech": r["tech"], "label": r["label"], "rows": []}
            groups.append(current)
        current["rows"].append(r)
        r["g"] = current["id"]
    return groups


# ---------- константы ----------

def constants(rows):
    found, names = [], set()

    def add(name, value, source, shape, row):
        base, k = name, 2
        while name in names:
            name = base + "_" + str(k)
            k += 1
        for c in found:
            if c["value"] == value:
                if row["id"] not in c["used"]:
                    c["used"].append(row["id"])
                return
        names.add(name)
        found.append({"name": name, "value": value, "source": source, "shape": shape, "step": row["id"], "used": [row["id"]]})

    for r in rows:
        data, expected = r["data"].replace("<br>", "\n"), r["expected"].replace("<br>", "\n")
        both = r["action"] + "\n" + data + "\n" + expected
        for m in re.finditer(r"https?://[^\s<>\"']+", both):
            add(r["label"].upper().replace("-", "_") + "_URL", m.group(), "PROPERTIES_FILE", "PROPERTIES_REF", r)
        for m in re.finditer(r"(?<![\w:/])(/[A-Za-z0-9_\-{}.]+(?:/[A-Za-z0-9_\-{}.]+)+)", both):
            if "http" in both[max(0, m.start() - 60):m.start()]:
                continue
            tail = re.sub(r"[^A-Za-z0-9]+", "_", m.group(1).rstrip("/").split("/")[-1]).strip("_")
            add("PATH_" + re.sub(r"(?<=[a-z])(?=[A-Z])", "_", tail).upper(), m.group(1), "TEST_CLASS_STATIC_FINAL", "LOCAL_FIELD_REF", r)
        for m in re.finditer(r"(?i)\b(код\w*(?:\s+ответа)?|статус\w*|status\s*code)\D{0,12}\b([1-5]\d\d)\b", both):
            add("EXPECTED_STATUS_" + m.group(2), m.group(2), "TEST_CLASS_STATIC_FINAL", "LOCAL_FIELD_REF", r)
        for m in re.finditer(r"(?is)\b(SELECT|INSERT|UPDATE|DELETE)\b.+?(?:;|$)", data + "\n" + r["action"]):
            add("QUERY_" + m.group(1).upper(), m.group().strip().rstrip(";"), "TEST_CLASS_STATIC_FINAL", "LOCAL_FIELD_REF", r)
        for m in re.finditer(r"(?i)(?:топик\w*|topic)\s*[:=]?\s*[«\"`']?([A-Za-z0-9_.\-]{3,})", both):
            add("TOPIC_" + re.sub(r"[^A-Za-z0-9]+", "_", m.group(1)).upper(), m.group(1), "PROPERTIES_FILE", "PROPERTIES_REF", r)
        for m in re.finditer(r"(?i)pattern\s*:\s*(\^\S+\$)", both):
            add("PATTERN", m.group(1), "TEST_CLASS_STATIC_FINAL", "LOCAL_FIELD_REF", r)
        for m in re.finditer(r"(?i)jsonpath\s*:\s*(\$[\w.\[\]]+)", both):
            add("JSON_PATH_" + re.sub(r"[^A-Za-z0-9]+", "_", m.group(1).strip("$.")).upper(), m.group(1), "TEST_CLASS_STATIC_FINAL", "LOCAL_FIELD_REF", r)
        body = re.search(r"\{[\s\S]*\}", data)
        if body and ('"' in body.group() or ":" in body.group()) and r["group"] in ("integration", "kafka"):
            add("BODY_" + r["id"].replace(".", "_"), "testdata/" + r["id"].replace(".", "-") + "-body.json", "TESTDATA_FILE_REF", "FILE_NAME_REF", r)
        if r["group"] not in ("ui", "mobile"):
            for m in re.finditer(r"[\"«]([^\"»]{1,60})[\"»]", expected):
                value = m.group(1).strip()
                if value and not value.startswith("__"):
                    add("EXPECTED_" + (re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()[:30] or "VALUE"), value,
                        "TEST_CLASS_STATIC_FINAL", "LOCAL_FIELD_REF", r)
    return found


def variables(rows):
    found = []
    for r in rows:
        for m in re.finditer(r"__([A-Za-z][A-Za-z0-9_]*)__", r["data"] + " " + r["action"]):
            name = m.group(1)[0].lower() + m.group(1)[1:]
            if name not in [v[0] for v in found]:
                found.append((name, r["id"], "генерируется перед шагом"))
        if r["bind"] == "produces":
            found.append(("response" + r["id"].replace(".", "_"), r["id"], "результат шага"))
    return found


# ---------- проект ----------

def class_index(env, groups_needed):
    roots = env.get("project", {}).get("test_roots") or [str(p) for p in Path(".").glob("**/src/test/java") if "target" not in p.parts]
    index = {}
    for root in roots:
        for path in sorted(Path(root).rglob("*")):
            if path.suffix not in (".java", ".kt") or any(part in ("target", "build") for part in path.parts):
                continue
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if re.search(r"@(Test|ParameterizedTest)\b", source):
                continue
            for group, pattern in CLASS_HINTS:
                if group in groups_needed and re.search(pattern, source):
                    methods = re.findall(r"(?m)^\s*public\s+(?:static\s+)?[\w<>\[\], ?]+\s+([a-z]\w*)\s*\(", source)
                    index.setdefault(group, []).append((str(path).replace("\\", "/"), path.stem, methods[:12]))
    return index


def class_name(tc):
    title = re.sub(r"\[[^\]]*\]", " ", tc["title"])
    words = re.findall(r"[A-Za-z][A-Za-z0-9]*", title)
    if len(words) < 2:
        words = ["".join(TRANSLIT.get(ch, ch) for ch in w.lower()) for w in re.findall(r"[А-Яа-яЁё]{3,}", title)[:4]] or words
    camel = "".join(w[:1].upper() + w[1:] for w in words if w.lower() not in ("api", "rest", "test"))[:60]
    digits = re.sub(r"\D", "", tc["key"].split("-")[-1])
    name = (camel or "Case") + digits + "Test"
    return name if JAVA_NAME.fullmatch(name) else "Case" + digits + "Test"


# ---------- запись ----------

def render(tc, check, env, rows, groups, consts, vars_, index):
    project = env.get("project", {})
    package = project.get("base_package") or "-"
    roots = project.get("test_roots") or ["src/test/java"]
    name = class_name(tc)
    test_file = roots[0].rstrip("/") + "/" + (package.replace(".", "/") + "/" if package != "-" else "") + name + ".java"
    bases = project.get("base_test_classes") or []
    base = bases[0].split("/")[-1].replace(".java", "").replace(".kt", "") if bases else "-"
    out = ["---", "tc: " + tc["key"], "plan_status: draft", "tc_status: " + check["status"], "class: " + name,
           "package: " + package, "test_file: " + test_file, "base_class: " + base,
           "ui_lib: " + project.get("ui_lib", "-"), "step_style: " + project.get("step_style", "-"), "---", "",
           "# План автотеста " + tc["key"] + " · " + tc["title"], "",
           "## 1. Проверка тест-кейса", "",
           "- Статус: " + check["status"] + " · средняя оценка " + check["avg"] + " · подробно: TC-CHECK.md",
           "- Блокирующие находки: " + (", ".join(check["blocking"]) or "нет"), "",
           "## 2. Шаги", "",
           "| Шаг | Действие | Ожидаемый результат | Тип | Группа | Технология | Метка | Уверенность | Основание | Связь данных | G |",
           "|-----|----------|---------------------|-----|--------|------------|-------|-------------|-----------|--------------|---|"]
    for r in rows:
        out.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["id"], esc(r["action"]), esc(r["expected"]), r["type"], r["group"], r["tech"], r["label"], r["conf"],
            esc(r["why"]), r["bind"], r["g"]))
    out += ["", "## 3. Порядок генерации", "",
            "| G | Шаги | Группа | Технология | Метка | Справка | Классы проекта | Статус |",
            "|---|------|--------|------------|-------|---------|----------------|--------|"]
    for g in groups:
        classes = ", ".join(c[1] for c in index.get(g["group"], [])[:5]) or "-"
        out.append("| %s | %s | %s | %s | %s | %s | %s | todo |" % (
            g["id"], ", ".join(r["id"] for r in g["rows"]), g["group"], g["tech"], g["label"],
            GROUP_REF.get(g["group"], "-"), classes))
    out += ["", "## 4. Константы", "",
            "| Имя | Значение | Источник | Форма | Шаг | Где используется |",
            "|-----|----------|----------|-------|-----|------------------|"]
    for c in consts:
        out.append("| %s | %s | %s | %s | %s | %s |" % (c["name"], esc(c["value"])[:200], c["source"], c["shape"], c["step"], ", ".join(c["used"])))
    if not consts:
        out.append("| - | - | - | - | - | - |")
    out += ["", "## 5. Переменные", "", "| Имя | Шаг | Откуда |", "|-----|-----|--------|"]
    for v in vars_:
        out.append("| %s | %s | %s |" % v)
    if not vars_:
        out.append("| - | - | - |")
    out += ["", "## 6. Классы проекта по технологиям", ""]
    for group, classes in index.items():
        for path, stem, methods in classes[:8]:
            out.append("- " + group + " · `" + path + "` · методы: " + (", ".join(methods) or "-"))
    if not index:
        out.append("- нет: в проекте не найдено классов шагов для технологий этого ТК")
    out += ["", "## 7. Решения и блокеры", "", "- нет", "", "## 8. Журнал", "", "| Когда | Что |", "|-------|-----|",
            "| build | черновик плана: шагов %d, G %d, констант %d |" % (len(rows), len(groups), len(consts))]
    return "\n".join(out) + "\n"


def read_check(folder):
    text = (folder / "TC-CHECK.md").read_text(encoding="utf-8") if (folder / "TC-CHECK.md").is_file() else ""
    status = re.search(r"- Статус: (\w+)", text)
    avg = re.search(r"- Средняя оценка: (\d+)", text)
    blocking = re.findall(r"^\| (TC-\d+) \| ([^|]+) \|[^|]+\| да \|", text, re.M)
    return {"status": status.group(1) if status else "-", "avg": avg.group(1) if avg else "-",
            "blocking": [b[0] + " " + b[1].strip() for b in blocking]}


def build(key, force):
    folder = tcc.DATA / key
    if not (folder / "TC.md").is_file():
        print("НЕТ TC.md: " + str(folder / "TC.md") + " - сначала tc_convert.py")
        return 2
    plan = folder / "PLAN.md"
    if plan.is_file() and not force:
        status = re.search(r"(?m)^plan_status:\s*(\S+)", plan.read_text(encoding="utf-8"))
        if status and status.group(1) != "draft":
            print("ПЛАН УЖЕ ЕСТЬ: plan_status " + status.group(1) + " - не перезаписываю (перестроить: --force)")
            return 1
    check = read_check(folder)
    if check["status"] == "-":
        print("НЕТ TC-CHECK.md: сначала tc_check.py " + key)
        return 2
    tc = tcc.parse_tc(folder / "TC.md")
    env = load_env()
    rows = []
    for s in tc["steps"]:
        rows.extend(split_step(s))
    rows = classify_rows(rows, env.get("project", {}).get("ui_lib", "-"))
    groups = gen_steps(rows)
    consts = constants(rows)
    vars_ = variables(rows)
    index = class_index(env, {g["group"] for g in groups})
    plan.write_text(render(tc, check, env, rows, groups, consts, vars_, index), encoding="utf-8")
    low = [r["id"] for r in rows if r["conf"] == "LOW" or r["group"] == "UNKNOWN_GROUP" or r["type"] == "UNKNOWN_TYPE"]
    print("ФАЙЛ: " + str(plan).replace("\\", "/"))
    print("ШАГОВ: %d · G: %d · КОНСТАНТ: %d · ПЕРЕМЕННЫХ: %d" % (len(rows), len(groups), len(consts), len(vars_)))
    print("ПРОВЕРИТЬ: " + (", ".join(low) if low else "нет - все шаги с уверенностью HIGH или MEDIUM"))
    if env == {}:
        print("ЗАМЕТКА: нет ENV.json - пакет, базовый класс и библиотека UI не определены (env-check не запускался)")
    return 0


def table(text, title):
    sect = re.search(r"(?ms)^## " + re.escape(title) + r"\s*\n(.*?)(?=^## |\Z)", text)
    rows = []
    for line in (sect.group(1) if sect else "").split("\n"):
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if cells and not set(cells[0]) <= set("-:") and cells[0] not in ("Шаг", "G", "Имя"):
            rows.append(cells)
    return rows


def validate(key):
    plan = tcc.DATA / key / "PLAN.md"
    if not plan.is_file():
        print("НЕТ PLAN.md: сначала tc_plan.py build " + key)
        return 2
    text = plan.read_text(encoding="utf-8")
    head = dict(re.findall(r"(?m)^(\w+):\s*(.*)$", text.split("\n---", 1)[0]))
    problems = []
    if head.get("tc_status") == "FAIL":
        problems.append("tc_status FAIL - тест-кейс не прошёл проверку, нужен исправленный ТК")
    if not JAVA_NAME.fullmatch(head.get("class", "")) or not head.get("class", "").endswith("Test"):
        problems.append("class «" + head.get("class", "") + "» - нужно имя Java с большой буквы и окончанием Test")
    if not JAVA_PACKAGE.fullmatch(head.get("package", "")):
        problems.append("package «" + head.get("package", "") + "» - нужен пакет Java, например ru.sber.demo.tests")
    if not head.get("test_file", "").endswith("/" + head.get("class", "") + ".java"):
        problems.append("test_file не оканчивается на /<class>.java")
    pkg_path = head.get("package", "").replace(".", "/")
    if JAVA_PACKAGE.fullmatch(head.get("package", "")) and ("/" + pkg_path + "/") not in head.get("test_file", ""):
        problems.append("test_file не лежит в каталоге пакета " + pkg_path)
    steps = table(text, "2. Шаги")
    gens = {r[0]: r for r in table(text, "3. Порядок генерации")}
    if not steps:
        problems.append("раздел 2 пуст")
    for r in steps:
        if len(r) < 11:
            problems.append("шаг " + r[0] + ": в строке не 11 колонок")
            continue
        if r[3] == "UNKNOWN_TYPE" or r[4] == "UNKNOWN_GROUP" or r[5] == "UNKNOWN_TECHNOLOGY":
            problems.append("шаг " + r[0] + ": тип или группа UNKNOWN - выбери по references/classify.md")
        if r[4] not in GROUP_REF:
            problems.append("шаг " + r[0] + ": группа «" + r[4] + "» не из списка " + ", ".join(GROUP_REF))
        if r[10] not in gens:
            problems.append("шаг " + r[0] + ": G «" + r[10] + "» нет в разделе 3")
    covered = {s.strip() for g in gens.values() for s in g[1].split(",")}
    for r in steps:
        if r[0] not in covered:
            problems.append("шаг " + r[0] + " не входит ни в одну G раздела 3")
    for g, r in gens.items():
        if len(r) < 8:
            problems.append(g + ": в строке не 8 колонок")
            continue
        ref = SKILLS / "autotest-gen" / "references" / r[5]
        if r[2] not in GROUP_REF or r[5] != GROUP_REF.get(r[2]):
            problems.append(g + ": справка «" + r[5] + "» не соответствует группе " + r[2])
        elif not ref.is_file():
            problems.append(g + ": нет файла справки " + str(ref) + " (скилл autotest-gen не установлен?)")
    for c in table(text, "4. Константы"):
        if c[0] != "-" and (len(c) < 6 or c[2] not in ("GLOBAL_CONSTANTS_CLASS", "TEST_CLASS_STATIC_FINAL", "CONFIG_OWNER",
                                                     "PROPERTIES_FILE", "TESTDATA_FILE_REF", "ENUM", "REUSE_FRAGMENT")):
            problems.append("константа " + c[0] + ": источник «" + (c[2] if len(c) > 2 else "-") + "» - выбери по references/classify.md, раздел «Константы»")
    if problems:
        for p in problems:
            print("ПРОБЛЕМА: " + p)
        print("ИТОГ: план не сошёлся, проблем " + str(len(problems)))
        return 1
    text = re.sub(r"(?m)^plan_status:\s*\S+", "plan_status: planned", text, count=1)
    text = text.rstrip("\n") + "\n| validate | план сошёлся: шагов %d, G %d |\n" % (len(steps), len(gens))
    plan.write_text(text, encoding="utf-8")
    print("ИТОГ: план сошёлся, plan_status: planned · шагов %d · G %d" % (len(steps), len(gens)))
    return 0


def main(args):
    if len(args) < 2 or args[0] not in ("build", "validate"):
        print("Использование: tc_plan.py build <ключ ТК> [--force] | validate <ключ ТК>")
        return 2
    return build(args[1], "--force" in args) if args[0] == "build" else validate(args[1])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
