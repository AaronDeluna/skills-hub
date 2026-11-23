#!/usr/bin/env python3
"""План генерации автотеста по тест-кейсу (скилл autotest-plan). Запуск из корня проекта:

  python3 <скилл>/scripts/tc_plan.py build <ключ ТК> [--force]  - черновик плана design.md (plan_status: draft)
  python3 <скилл>/scripts/tc_plan.py validate <ключ ТК>         - проверка плана; всё сошлось -> plan_status: planned
  python3 <скилл>/scripts/tc_plan.py style <ключ ТК> <steps|flow> - записать архитектуру тестов проекта (ответ человека)
  python3 <скилл>/scripts/tc_plan.py approve <ключ ТК>          - человек подтвердил разделы 11-16 -> approved: yes

build: шаги TC.md делятся на подшаги (два действия в одном шаге), каждому - тип, группа,
технология, уверенность, связь данных; шаги группируются в шаги генерации G-n; константы из
данных и ожидаемых результатов - в матрицу с источником хранения; классы проекта по
технологиям - в индекс для переиспользования. Читает ENV.json (паспорт проекта), если есть.
Существующий план со статусом не draft не перезаписывает без --force.
Опись артефактов ARTIFACTS.md (artifacts.py): служебные шаги - тип SERVICE (кода нет), связи шагов с
запросами - раздел 9, значения из выборки - раздел 10 (в тесте - переменная шага-источника, не литерал).
Архитектура тестов (steps - классы шагов, flow - FlowRunner): ответ человека (style, файл
openspec/pvatf/env/STYLE.md или ENV-INIT.md) или код проекта (ENV.json).
validate: нет UNKNOWN в шагах, каждый шаг в G, у каждой G есть справка, у констант есть источник,
имя класса и пакет - допустимые имена Java, tc_status не FAIL, архитектура steps или flow, разбор
артефактов закончен, у каждого запроса и SQL есть строка в разделе 9; разделы 11-14 (файлы, методы шагов,
проверки, настройки) заполнены без ЗАПОЛНИТЬ и сходятся друг с другом и с разделами 2-5 (references/design-rules.md);
сошлось -> validate пишет разделы 15 (привязка шагов ТК к коду) и 16 (планируемые изменения по файлам).
Генерация - только по плану, который человек подтвердил (approve -> approved: yes); validate сбрасывает approved.
Python 3.8+, только стандартная библиотека. Код выхода: 0 - выполнено, 1 - план не сошёлся или
ТК FAIL, 2 - неверные аргументы или нет TC.md.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tc_common as tcc  # noqa: E402
import frame_versions  # noqa: E402 - копия shared/scripts
import artifacts as art  # noqa: E402

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
FILL = "ЗАПОЛНИТЬ"  # клетка, которую дописывает модель по references/design-rules.md
FILE_ACTIONS = ("создать", "дополнить", "не трогать", "скрипт", "env-check")
CHECK_KINDS = ("равно", "не равно", "содержит", "ключ есть", "ключа нет", "не пусто", "пусто", "статус", "больше", "меньше",
               "по шаблону", "проверено в шаге")


# Окружение под ТК (раздел 8 плана): метка -> слова, которые ищутся в файлах сборки (подсказка, не имя артефакта:
# имя модуля берётся только из документации, его ставит env-check в режиме setup). Пустой список - модуль не ищется.
# слова ищутся в artifactId зависимостей фрейма (frame_versions.framework_artifacts); модуль REST фрейма - api
BUILD_WORDS = {"rest": ["rest", "api"], "grpc": ["grpc"], "graphql": ["graphql"], "websocket": ["websocket"],
               "db": ["database", "datasource", "jdbc"], "opensearch": ["opensearch", "elastic"], "kafka": ["kafka"],
               "ui": ["playwright", "selenide"], "mobile": ["appium", "mobile"], "audit": ["audit"], "journals": ["journal"],
               "abyss": ["abyss"], "metrics": ["metric"], "sup": ["sup-", "-sup"], "fixtures": ["fixture"], "timeouts": [],
               "testcontainers": ["testcontainers"], "sbermock": ["sbermock"], "openshift": ["openshift", "kubernetes"],
               "dataconverter": ["converter"], "toggler": ["toggler"], "launcher": ["launcher"], "sessions": ["session"],
               "value": [], "invocation": ["invocation"]}
# маркер, который прямо называет технологию (EXPLICIT); остальные маркеры - по смыслу шага (IMPLIED)
EXPLICIT = {"kafka", "кафк", "grpc", "graphql", "websocket", "opensearch", "elastic", "datasource", "sql", "select", "insert",
            "update", "delete from", "postgres", "oracle", "appium", "android", "ios", "selenide", "playwright", "fixture",
            "testcontainers", "sbermock", "openshift", "kubernetes", "toggler", "launcher", "thanos", "victoria",
            "pvm-abyss", "abyss", "valueservice", "invocation", "rest", "http", "post", "get", "put", "patch", "delete",
            "/api/", "аудит", "ефс", "ппрб", "суп", "dataconverter"}
LABEL_TECH = {label: tech for _, techs in tcc.GROUPS for tech, label, _ in techs}
ASYNC_GROUPS = {"kafka", "logs_metrics", "ui", "mobile"}


def env_needs(tc, rows, env):
    """-> строки раздела 8: (технология, метка, статус, шаги, слова, в сборке)."""
    needs = {}
    for r in rows:
        if r["label"] in ("-", ""):
            continue
        markers = {m.strip() for m in r["why"].split(",")}
        status = "EXPLICIT" if markers & EXPLICIT and not r["why"].startswith("унаследовано") else "IMPLIED"
        item = needs.setdefault(r["label"], {"tech": r["tech"], "status": status, "steps": []})
        item["steps"].append(r["id"])
        if status == "EXPLICIT":
            item["status"] = "EXPLICIT"
    for label in [l.strip() for l in tc["fields"].get("Технологии источника", "").split(",") if l.strip() not in ("", "-")]:
        item = needs.setdefault(label, {"tech": LABEL_TECH.get(label, label), "status": "EXPLICIT", "steps": []})
        item["status"] = "EXPLICIT"
        item["steps"].append("импорт")
    groups = {r["group"] for r in rows}
    if groups & ASYNC_GROUPS and "timeouts" not in needs:
        needs["timeouts"] = {"tech": "Сервис для работы с Таймаутами", "status": "RECOMMENDED", "steps": ["ожидание асинхронного результата"]}
    if (any(r["type"] == "SETUP" for r in rows) or tc["fields"].get("Предусловия", "-") not in ("", "-")) and "fixtures" not in needs:
        needs["fixtures"] = {"tech": "Сервис для работы с Fixtures", "status": "RECOMMENDED", "steps": ["предусловия"]}
    build = ""
    for name in env.get("project", {}).get("build_files", []):
        try:
            build += Path(name).read_text(encoding="utf-8", errors="replace") + "\n"
        except OSError:
            pass
    has_build = bool(build.strip())  # нет файлов сборки -> «-»; сборка без модулей фрейма -> «нет»
    build = frame_versions.framework_artifacts(build)
    out = []
    for label, item in needs.items():
        words = BUILD_WORDS.get(label, [])
        if not words or not has_build:
            present = "-"
        else:
            hit = [w for w in words if w in build]
            present = "да (" + hit[0] + ")" if hit else "нет"
        out.append((item["tech"], label, item["status"], ", ".join(item["steps"]), ", ".join(words) or "-", present))
    order = {"EXPLICIT": 0, "IMPLIED": 1, "RECOMMENDED": 2}
    return sorted(out, key=lambda o: (order[o[2]], o[1]))


def esc(value):
    return str(value).replace("|", "\\|").replace("\n", "<br>") or "-"


def load_env():
    try:
        return json.loads((tcc.pp.env_dir() / "ENV.json").read_text(encoding="utf-8"))
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
    после 4 шагов в одной G. Проверка своего запроса остаётся в G запроса. Служебный шаг (SERVICE) -
    в текущую G, новую не открывает."""
    groups, current = [], None
    for r in rows:
        if r["type"] == "SERVICE" and current is not None:
            current["rows"].append(r)
            r["g"] = current["id"]
            continue
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

def field_name(row):
    """Поле, которое проверяет шаг: последний латинский идентификатор действия (result.accInfo.accState ->
    ACC_STATE, acc_state -> ACC_STATE). Нет -> STEP_<id>. Имя константы - по смыслу, не по значению."""
    names = re.findall(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", row["action"])
    names = [n for n in names if not re.fullmatch(r"(?i)get|post|put|patch|delete|http|https|json|jsonpath|sql|select|null|true|false|v\d+", n)]
    if not names:
        return "STEP_" + row["id"].replace(".", "_")
    last = names[-1].split(".")[-1]
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", last).upper().strip("_") or "STEP_" + row["id"].replace(".", "_")


def constants(rows, skip_values=()):
    """Константы плана. Одно значение у разных полей - разные константы (имя по полю). Значения из выборки
    (skip_values) константами не становятся: в тесте это переменная шага-источника."""
    found, names = [], set()

    def add(name, value, source, shape, row):
        if value in skip_values:
            return
        for c in found:
            if c["value"] == value and re.sub(r"_\d+$", "", c["name"]) == name:
                if row["id"] not in c["used"]:
                    c["used"].append(row["id"])
                return
        base, k = name, 2
        while name in names:
            name = base + "_" + str(k)
            k += 1
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
            add("EXPECTED_STATUS_CODE", m.group(2), "TEST_CLASS_STATIC_FINAL", "LOCAL_FIELD_REF", r)
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
                    add("EXPECTED_" + field_name(r), value, "TEST_CLASS_STATIC_FINAL", "LOCAL_FIELD_REF", r)
    return found


def camel(field):
    parts = [p for p in re.split(r"[^A-Za-z0-9]+|(?<=[a-z0-9])(?=[A-Z])", field) if p]
    return (parts[0].lower() + "".join(p[:1].upper() + p[1:].lower() for p in parts[1:])) if parts else "value"


def variables(rows, values=()):
    found = []
    for v in values:
        found.append((camel(v[2]), v[1], "результат шага " + v[1] + ": поле " + v[2] + " (в тесте вместо значения " + v[0] + ")"))
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
    """Имя тест-класса - из ключа ТК: DEPOEFS-T1906 -> Depoefs1906Test. Русские слова латиницей (транслит) в имена
    не попадают: это нарушает соглашения Java проекта. ТК нет (ключ NOTC-<n>) - имя из строки «Класс теста» TC.md."""
    given = tc.get("fields", {}).get("Класс теста", "-")
    if given != "-" and JAVA_NAME.fullmatch(given) and given.endswith("Test"):
        return given
    parts = re.findall(r"[A-Za-z]+|[0-9]+", tc["key"])
    code = next((p for p in parts if p.isalpha() and p.upper() != "T"), "Case")
    digits = "".join(p for p in parts if p.isdigit())
    name = code[:1].upper() + code[1:].lower() + digits + "Test"
    return name if JAVA_NAME.fullmatch(name) else "Case" + digits + "Test"


# ---------- запись ----------

def style_choice(env):
    """Архитектура тестов: ответ человека (STYLE.md, ENV-INIT.md) или код проекта (ENV.json). Иначе «-»."""
    for name in ("STYLE.md", "ENV-INIT.md"):
        try:
            text = (tcc.pp.env_dir() / name).read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.search(r"(?m)^- Стиль шагов: (steps|flow)\s*$", text)
        if m:
            return m.group(1)
    style = env.get("project", {}).get("step_style", "-")
    return style if style in ("steps", "flow") else "-"


def project_layout(env, package):
    """Корень пакетов, каталоги кода и ресурсов тестов (правило 13 autotest-rules.md)."""
    roots = env.get("project", {}).get("test_roots") or ["src/test/java"]
    java = roots[0].rstrip("/")
    root = package[:-len(".tests")] if package.endswith(".tests") else package
    resources = java[:-len("java")] + "resources" if java.endswith("java") else "src/test/resources"
    return {"java": java, "resources": resources, "root": root,
            "dir": lambda pkg: java + "/" + pkg.replace(".", "/") if pkg not in ("", "-") else java}


def find_files(pattern, text_re=None):
    found = []
    for path in sorted(Path(".").glob(pattern)):
        if any(part in ("target", "build", ".gigacode", "openspec", "node_modules") for part in path.parts):
            continue
        if text_re:
            try:
                if not re.search(text_re, path.read_text(encoding="utf-8", errors="replace")):
                    continue
            except OSError:
                continue
        found.append(str(path).replace("\\", "/"))
    return found


def config_class(path):
    """Класс конфигурации окружения или сервиса - не класс шагов: методы шагов в него не пишутся."""
    return "/config/" in path.replace("\\", "/") or Path(path).stem.endswith("Configuration")


def detail_sections(test_file, package, env, rows, groups, consts, index, arts):
    """Черновик разделов 11-14: файлы, методы шагов, проверки, настройки. Клетки, которые скрипт не решает, - ЗАПОЛНИТЬ."""
    lay = project_layout(env, package)
    steps_dir = lay["dir"](lay["root"] + ".steps" if lay["root"] not in ("", "-") else "-")
    files, methods, checks, settings = [], [], [], []
    files.append((test_file, "создать", "тест-метод; ожидаемые значения ТК (константы раздела 4 TEST_CLASS_STATIC_FINAL)", "все"))
    g_class = {}
    for g in groups:
        work = [r for r in g["rows"] if r["type"] != "SERVICE"]
        if not work:
            continue
        found = [c for c in index.get(g["group"], []) if not config_class(c[0])]
        if found:
            path, stem = found[0][0], found[0][1]
            files.append((path, "дополнить", "методы шагов " + g["id"] + " (раздел 12) - или " + FILL + ": путь нового класса", g["id"]))
        else:
            stem = FILL
            files.append((steps_dir + "/" + FILL + ".java", "создать", "методы шагов " + g["id"] + " (раздел 12)", g["id"]))
        g_class[g["id"]] = stem
        reqs = sorted({l[1] for l in arts.get("links", []) if l[0] in {str(r["n"]) for r in work} and l[1].startswith(("A-", "N-"))})
        methods.append((g["id"], stem, FILL, ", ".join(r["id"] for r in work), ", ".join(reqs) or "-", FILL))
    bodies = {c["value"]: c["step"] for c in consts if c["source"] == "TESTDATA_FILE_REF"}
    for l in arts.get("links", []):
        inv = {r[0]: r for r in arts.get("inventory", [])}.get(l[1])
        if inv and len(inv) > 5 and inv[5] not in ("-", "") and inv[2].upper() in ("POST", "PUT", "PATCH"):
            bodies.setdefault("testdata/" + l[0] + "-body.json", l[0])
    for value, step in bodies.items():
        files.append((lay["resources"] + "/" + value, "создать", "тело запроса шага " + step + " (из описи артефактов)", "-"))
    own = [f for f in find_files(lay["resources"] + "/*.properties")
           if not f.endswith(("perfeccionista.properties", "simplelogger.properties", "allure.properties"))]
    props_file = own[0] if own else lay["resources"] + "/test.properties"
    prop_consts = [c for c in consts if c["source"] == "PROPERTIES_FILE"]
    if prop_consts:
        files.append((props_file, "дополнить" if own else "создать", "ключи раздела 14", "-"))
    perf = find_files("**/src/test/resources/perfeccionista.properties")
    files.append(((perf or [lay["resources"] + "/perfeccionista.properties"])[0], "скрипт",
                  "ключи фрейма по эталону: env_props.py ensure (руками не пишется)", "-"))
    env_cfg = find_files("**/src/test/java/**/*.java", r"extends\s+DefaultEnvironmentConfiguration")
    files.append(((env_cfg or [lay["dir"](lay["root"] + ".config") + "/" + FILL + "EnvironmentConfiguration.java"])[0],
                  "env-check", "регистрация сервисов технологий раздела 8 (настраивает env-check, генерация не трогает)", "-"))
    for c in prop_consts:
        settings.append((FILL, props_file, c["value"], FILL))
    expected = {}
    for c in consts:
        if c["name"].startswith("EXPECTED_"):
            for sid in c["used"]:
                expected.setdefault(sid, []).append(c["name"])
    for r in rows:
        if r["type"] == "SERVICE" or not r["expected"].strip():
            continue
        names = expected.get(r["id"], [])
        for name in names or [FILL]:
            checks.append((r["id"], FILL, FILL, FILL, name))
    return files, methods, checks, settings


def render_detail(files, methods, checks, settings):
    out = ["", "## 11. Файлы", "",
           "| Файл | Действие | Что в нём | G |", "|------|----------|-----------|---|"]
    out += ["| %s | %s | %s | %s |" % f for f in files]
    out += ["", "## 12. Методы шагов", "",
            "| G | Класс | Метод | Шаги ТК | Запрос | Параметры |", "|---|-------|-------|---------|--------|-----------|"]
    out += ["| %s | %s | %s | %s | %s | %s |" % m for m in methods] or ["| - | - | - | - | - | - |"]
    out += ["", "## 13. Проверки", "",
            "| Шаг | Объект | Поле | Как | Ожидаемое |", "|-----|--------|------|-----|-----------|"]
    out += ["| %s | %s | %s | %s | %s |" % c for c in checks] or ["| - | - | - | - | - |"]
    out += ["", "## 14. Настройки", "",
            "| Ключ | Файл | Значение | Кто читает |", "|------|------|----------|------------|"]
    out += ["| %s | %s | %s | %s |" % tuple(esc(x) for x in st) for st in settings] or ["| - | - | - | - |"]
    return out


def render(tc, check, env, rows, groups, consts, vars_, index, needs, arts=None):
    project = env.get("project", {})
    package = project.get("test_package") or project.get("base_package") or "-"
    roots = project.get("test_roots") or ["src/test/java"]
    name = class_name(tc)
    test_file = roots[0].rstrip("/") + "/" + (package.replace(".", "/") + "/" if package != "-" else "") + name + ".java"
    bases = project.get("base_test_classes") or []
    base = bases[0].split("/")[-1].replace(".java", "").replace(".kt", "") if bases else "-"
    base_fqn = "-"
    for test_root in roots:
        prefix = test_root.rstrip("/") + "/"
        if bases and bases[0].startswith(prefix):
            base_fqn = bases[0][len(prefix):].rsplit(".", 1)[0].replace("/", ".")
    out = ["---", "tc: " + tc["key"], "plan_status: draft", "approved: no", "tc_status: " + check["status"], "class: " + name,
           "package: " + package, "test_file: " + test_file, "base_class: " + base, "base_fqn: " + base_fqn,
           "ui_lib: " + project.get("ui_lib", "-"), "step_style: " + style_choice(env), "---", "",
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
    out += ["", "## 7. Решения и блокеры", "", "- нет", "", "## 8. Окружение под ТК", "",
            "| Технология | Метка | Статус | Шаги | Слова в сборке | В сборке |",
            "|------------|-------|--------|------|----------------|----------|"]
    for n in needs:
        out.append("| %s | %s | %s | %s | %s | %s |" % n)
    if not needs:
        out.append("| - | - | - | - | - | - |")
    arts = arts or {"links": [], "inventory": [], "values": [], "folder": ""}
    inventory = {r[0]: r for r in arts["inventory"]}
    out += ["", "## 9. Запросы из артефактов", "",
            "| Шаг | ID | Метод | Адрес | Заголовки | Тело запроса | Код | Тело ответа |",
            "|-----|----|-------|-------|-----------|--------------|-----|-------------|"]
    for step_no, aid, why in arts["links"]:
        r = inventory.get(aid)
        if r:
            path = lambda v: (arts["folder"] + "/" + v) if v not in ("-", "") and not v.startswith("/") else v
            out.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (step_no, aid, r[2], esc(r[3]), esc(r[4]), path(r[5]), r[6], path(r[7])))
        else:
            out.append("| %s | - | - | %s | - | - | - | - |" % (step_no, esc(why)))
    if not arts["links"]:
        out.append("| - | - | - | - | - | - | - | - |")
    out += ["", "## 10. Значения из выборки", "",
            "| Значение | Шаг-источник | Поле | Шаги | Переменная |",
            "|----------|--------------|------|------|------------|"]
    for v in arts["values"]:
        out.append("| %s | %s | %s | %s | %s |" % (esc(v[0]), v[1], esc(v[2]), esc(v[3]), camel(v[2])))
    if not arts["values"]:
        out.append("| - | - | - | - | - |")
    out += render_detail(*detail_sections(test_file, package, env, rows, groups, consts, index, arts))
    out += ["", "## 17. Журнал", "", "| Когда | Что |", "|-------|-----|",
            "| build | черновик плана: шагов %d, G %d, констант %d |" % (len(rows), len(groups), len(consts))]
    return "\n".join(out) + "\n"


def load_artifacts(folder):
    """ARTIFACTS.md (artifacts.py) -> опись, связи, служебные шаги, значения из выборки, статус разбора."""
    path = folder / "ARTIFACTS.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    try:
        where = str(path.parent.resolve().relative_to(Path.cwd().resolve())).replace("\\", "/")
    except ValueError:
        where = str(path.parent).replace("\\", "/")
    return {"inventory": art.rows_of(text, "Опись"), "links": [r[:3] for r in art.rows_of(text, "Связь шагов") if len(r) >= 3],
            "service": [r[:2] for r in art.rows_of(text, "Служебные шаги") if len(r) >= 2],
            "values": [r[:4] for r in art.rows_of(text, "Значения из выборки") if len(r) >= 4],
            "status": art.meta_line(text, "Разбор агентом") or "-", "folder": where}


def read_check(folder):
    text = (folder / "TC-CHECK.md").read_text(encoding="utf-8") if (folder / "TC-CHECK.md").is_file() else ""
    status = re.search(r"- Статус: (\w+)", text)
    avg = re.search(r"- Средняя оценка: (\d+)", text)
    blocking = re.findall(r"^\| (TC-\d+) \| ([^|]+) \|[^|]+\| да \|", text, re.M)
    return {"status": status.group(1) if status else "-", "avg": avg.group(1) if avg else "-",
            "blocking": [b[0] + " " + b[1].strip() for b in blocking]}


def build(key, force):
    folder = tcc.pp.autotest_dir(key)
    if not (folder / "TC.md").is_file():
        print("НЕТ TC.md: " + str(folder / "TC.md") + " - сначала tc_convert.py")
        return 2
    plan = tcc.pp.plan_file(key)
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
    arts = load_artifacts(folder)
    service = {r[0]: r[1] for r in arts["service"]}
    for r in rows:
        reason = service.get(str(r["n"])) or tcc.service_reason(r["action"] + " " + r["expected"])
        if reason:
            r.update(type="SERVICE", conf="HIGH", bind="-", why="служебный: " + reason.replace("скрипт: ", "").replace("агент: ", ""))
    by_n = {}
    for r in rows:
        by_n.setdefault(str(r["n"]), []).append(r)
    for v in arts["values"]:
        for r in by_n.get(v[1], [])[:1]:
            r["bind"] = "produces"
        for n in re.findall(r"\d+", v[3]):
            for r in by_n.get(n, []):
                if r["bind"] in ("-", "produces") and n != v[1]:
                    r["bind"] = "uses " + v[1]
    groups = gen_steps(rows)
    consts = constants(rows, {v[0] for v in arts["values"]})
    vars_ = variables(rows, arts["values"])
    index = class_index(env, {g["group"] for g in groups})
    needs = env_needs(tc, rows, env)
    plan.write_text(render(tc, check, env, rows, groups, consts, vars_, index, needs, arts), encoding="utf-8")
    low = [r["id"] for r in rows if r["conf"] == "LOW" or r["group"] == "UNKNOWN_GROUP" or r["type"] == "UNKNOWN_TYPE"]
    print("ФАЙЛ: " + str(plan).replace("\\", "/"))
    print("ШАГОВ: %d · G: %d · КОНСТАНТ: %d · ПЕРЕМЕННЫХ: %d" % (len(rows), len(groups), len(consts), len(vars_)))
    print("ПРОВЕРИТЬ: " + (", ".join(low) if low else "нет - все шаги с уверенностью HIGH или MEDIUM"))
    missing = [n[1] + " (" + n[0] + ")" for n in needs if n[5] == "нет" and n[2] != "RECOMMENDED"]
    print("ОКРУЖЕНИЕ: " + ("нет в сборке: " + ", ".join(missing) if missing else "все технологии ТК найдены в сборке или не проверяются"))
    if style_choice(env) == "-":
        print("АРХИТЕКТУРА: не выбрана - спроси человека «steps или flow», ответ: tc_plan.py style " + key + " <steps|flow>")
    if arts["status"] == "нужен":
        print("АРТЕФАКТЫ: разбор агентом не закончен - artifacts.py task " + key + " -> pvatf-artifacts -> artifacts.py merge " + key)
    if env == {}:
        print("ЗАМЕТКА: нет ENV.json - пакет, базовый класс и библиотека UI не определены (env-check не запускался)")
    return 0


def table(text, title):
    sect = re.search(r"(?ms)^## " + re.escape(title) + r"\s*\n(.*?)(?=^## |\Z)", text)
    rows = []
    for line in (sect.group(1) if sect else "").split("\n"):
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if cells and not set(cells[0]) <= set("-:") and cells[0] not in ("Шаг", "G", "Имя", "Значение", "Файл", "Ключ"):
            rows.append(cells)
    return rows


def set_style(key, style):
    """Ответ человека об архитектуре тестов -> openspec/pvatf/env/STYLE.md и шапка плана."""
    if style not in ("steps", "flow"):
        print("Использование: tc_plan.py style <ключ ТК> <steps|flow>")
        return 2
    target = tcc.pp.env_dir() / "STYLE.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Архитектура тестов проекта\n\n- Стиль шагов: " + style + "\n- Откуда: ответ человека\n", encoding="utf-8")
    plan = tcc.pp.plan_file(key, create=False)
    if plan.is_file():
        text = plan.read_text(encoding="utf-8")
        plan.write_text(re.sub(r"(?m)^step_style:.*$", "step_style: " + style, text, count=1), encoding="utf-8")
    print("АРХИТЕКТУРА: " + style + " · ФАЙЛ: " + str(target).replace("\\", "/"))
    return 0


def plan_hash(text):
    """Отпечаток содержания плана: без статусов (plan_status, approved, статусы G) и журнала."""
    import hashlib
    body = re.sub(r"(?ms)^## \d+\. Журнал.*\Z", "", strip_derived(text))
    body = re.sub(r"(?m)^(plan_status|approved|run_status):.*$", "", body)
    body = re.sub(r"(?m)\| (todo|ok|stub|blocked) \|\s*$", "| |", body)
    return hashlib.sha1(body.encode("utf-8")).hexdigest()[:12]


def detail_problems(text, head, steps):
    """Разделы 11-14 заполнены и сходятся друг с другом и с разделами 2-5, 9-10 (references/design-rules.md)."""
    problems = []
    for title in ("11. Файлы", "12. Методы шагов", "13. Проверки", "14. Настройки"):
        if not re.search(r"(?m)^## " + re.escape(title) + r"\s*$", text):
            problems.append("нет раздела «" + title + "» - перестрой план: tc_plan.py build " + head.get("tc", "<ключ>") + " --force")
            return problems
        for r in table(text, title):
            if FILL in " ".join(r):
                problems.append("раздел " + title + ": строка «" + " | ".join(r)[:120] + "» - заполни " + FILL
                                + " по references/design-rules.md")
    package = head.get("package", "-")
    root = package[:-len(".tests")] if package.endswith(".tests") else package
    files = [r for r in table(text, "11. Файлы") if len(r) >= 4 and r[0] != "-"]
    stems = {}
    for f in files:
        if "/-/" in f[0] or f[0].startswith("-/"):
            problems.append("файл " + f[0] + ": в пути «-» - пакет не был известен при build: исправь package в шапке и"
                            " перестрой план: tc_plan.py build " + head.get("tc", "<ключ>") + " --force")
        if f[1] not in FILE_ACTIONS:
            problems.append("файл " + f[0] + ": действие «" + f[1] + "» - одно из: " + ", ".join(FILE_ACTIONS))
        if f[0].endswith(".java") and f[1] == "создать" and f[0] != head.get("test_file"):
            pkg = "/" + root.replace(".", "/") + "/"
            config = f[0].endswith("Configuration.java")
            want = pkg + ("config/" if config else "steps/")
            if root not in ("", "-") and want not in f[0] and (pkg + "data/") not in f[0]:
                problems.append("файл " + f[0] + ": новый " + ("класс конфигурации - в пакете " + root + ".config" if config else
                                "класс шагов - в пакете " + root + ".steps (данные - " + root + ".data)") + ", не в пакете тестов")
        if f[0].endswith(".java"):
            stems[Path(f[0]).stem] = f
        if f[0].endswith("perfeccionista.properties") and f[1] != "скрипт":
            problems.append("файл " + f[0] + ": perfeccionista.properties пишет только скрипт env_props.py - действие «скрипт»")
    if head.get("test_file") and head["test_file"] not in [f[0] for f in files]:
        problems.append("раздел 11: нет строки тест-класса " + head["test_file"])
    gens = {r[0]: r for r in table(text, "3. Порядок генерации")}
    types = {r[0]: r[3] for r in steps if len(r) > 3}
    methods = [m for m in table(text, "12. Методы шагов") if len(m) >= 6 and m[0] != "-"]
    for g, row in gens.items():
        need = {sid.strip() for sid in row[1].split(",") if types.get(sid.strip()) not in ("SERVICE", None)}
        got = {sid.strip() for m in methods if m[0] == g for sid in m[3].split(",")}
        if need - got:
            problems.append(g + ": шаги " + ", ".join(sorted(need - got)) + " не названы ни в одном методе раздела 12")
    for m in methods:
        if m[1] not in stems and FILL not in m[1]:
            problems.append("метод " + m[2] + ": класс «" + m[1] + "» не назван файлом .java в разделе 11")
        if FILL not in m[2] and not re.fullmatch(r"[a-z][A-Za-z0-9]*", m[2]):
            problems.append("метод «" + m[2] + "»: имя Java с маленькой буквы, латиницей, без скобок и транслита")
    consts = {c[0] for c in table(text, "4. Константы") if c and c[0] != "-"}
    variables = {v[0] for v in table(text, "5. Переменные") if v and v[0] != "-"}
    variables |= {v[4] for v in table(text, "10. Значения из выборки") if len(v) >= 5 and v[0] != "-"}
    seen = {}
    checks = [c for c in table(text, "13. Проверки") if len(c) >= 5 and c[0] != "-"]
    for c in checks:
        sid, obj, field, how, expected = c[:5]
        if FILL in " ".join(c):
            continue
        if not how.startswith(CHECK_KINDS):
            problems.append("проверка шага " + sid + ": «Как» = «" + how + "» - одно из: " + ", ".join(CHECK_KINDS))
        if how.startswith("проверено в шаге"):
            continue
        key = (obj.lower(), field.lower())
        if key in seen:
            problems.append("проверка шага " + sid + ": поле «" + field + "» у «" + obj + "» уже проверяется в шаге " + seen[key]
                            + " - вторую строку замени на «проверено в шаге " + seen[key] + "»")
        seen.setdefault(key, sid)
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", expected) and expected not in consts:
            problems.append("проверка шага " + sid + ": константы " + expected + " нет в разделе 4")
        elif re.fullmatch(r"[a-z][A-Za-z0-9]*", expected) and expected not in variables:
            problems.append("проверка шага " + sid + ": переменной " + expected + " нет в разделах 5 и 10")
        elif expected == "-" and not how.startswith(("ключ есть", "ключа нет", "не пусто", "пусто")):
            problems.append("проверка шага " + sid + ": у «" + how + "» нужно ожидаемое: константа раздела 4, переменная или \"значение\"")
    checked = {c[0] for c in checks}
    for r in steps:
        if len(r) > 3 and r[3] != "SERVICE" and r[2] not in ("", "-") and r[0] not in checked:
            problems.append("шаг " + r[0] + ": ожидаемый результат «" + r[2][:60] + "» без строки в разделе 13")
    file_names = {f[0] for f in files}
    for st in [x for x in table(text, "14. Настройки") if len(x) >= 4 and x[0] != "-"]:
        if FILL in " ".join(st):
            continue
        if st[0].startswith(("perfeccionista.", "session.")) or st[1].endswith("perfeccionista.properties"):
            problems.append("настройка " + st[0] + ": свои ключи - в своём файле настроек, не perfeccionista.* и не в perfeccionista.properties")
        if st[1] not in file_names:
            problems.append("настройка " + st[0] + ": файла " + st[1] + " нет в разделе 11")
    return problems


DERIVED = ("15. Привязка шагов ТК к коду", "16. Планируемые изменения")
PARAM = re.compile(r"^\s*([a-z]\w*)\s+([A-Za-z][\w<>\[\], .?]*?)\s+-\s+(.+?)\s*$")


def strip_derived(text):
    """Без разделов 15-16: их пишет validate из разделов 2-14, руками они не правятся."""
    for title in DERIVED:
        text = re.sub(r"(?ms)^## " + re.escape(title) + r"\s*\n.*?(?=^## |\Z)", "", text)
    return text


def params(cell):
    """«host String - настройки test.url; code BigDecimal - тест» -> [(имя, тип, откуда)]."""
    found = []
    for part in cell.split(";"):
        m = PARAM.match(part)
        if m:
            found.append(m.groups())
    return found


def signature(m):
    """Строка раздела 12 -> «Класс.метод(Тип имя, ...)»."""
    return m[1] + "." + m[2] + "(" + ", ".join(t + " " + n for n, t, _ in params(m[5])) + ")"


def java_package(path):
    m = re.search(r"/java/(.+)/[^/]+\.java$", path)
    return m.group(1).replace("/", ".") if m else "-"


def ids(cell):
    return [x.strip() for x in cell.split(",") if x.strip() and x.strip() != "-"]


def derived_sections(text, head):
    """Разделы 15-16 из подтверждаемых таблиц 2-14: что, где и как будет в коде. Ничего нового - только сводка."""
    steps = [r for r in table(text, "2. Шаги") if len(r) >= 11]
    gens = [g for g in table(text, "3. Порядок генерации") if len(g) >= 8]
    consts = [c for c in table(text, "4. Константы") if len(c) >= 6 and c[0] != "-"]
    reqs = [r for r in table(text, "9. Запросы из артефактов") if len(r) >= 8 and r[1] != "-"]
    files = [f for f in table(text, "11. Файлы") if len(f) >= 4 and f[0] != "-"]
    methods = [m for m in table(text, "12. Методы шагов") if len(m) >= 6 and m[0] != "-"]
    checks = [c for c in table(text, "13. Проверки") if len(c) >= 5 and c[0] != "-"]
    settings = [x for x in table(text, "14. Настройки") if len(x) >= 4 and x[0] != "-"]
    by_step = {}
    for m in methods:
        for sid in ids(m[3]):
            by_step.setdefault(sid, m)
    req_text = lambda sid: "; ".join(r[1] + " " + r[2] + " " + r[3] for r in reqs if r[0] == sid or r[0] == sid.split(".")[0]) or "-"
    check_text = lambda c: c[1] + " · `" + c[2] + "` " + c[3] + ("" if c[4] == "-" else " " + c[4])
    out = ["", "## " + DERIVED[0], "",
           "Пишет `tc_plan.py validate` из разделов 2-14, руками не правится. Каждый шаг ТК - место в коде и его проверки.", "",
           "| Шаг ТК | Действие | G | Где в коде | Запрос | Проверки |", "|--------|----------|---|------------|--------|----------|"]
    for r in steps:
        m = by_step.get(r[0])
        where = "тест-класс: служебный шаг, кода шага нет" if r[3] == "SERVICE" else ("`" + signature(m) + "`" if m else "-")
        cks = "; ".join(check_text(c) for c in checks if c[0] == r[0]) or "-"
        out.append("| %s | %s | %s | %s | %s | %s |" % (r[0], r[1], r[10], where, req_text(r[0]), cks))
    out += ["", "## " + DERIVED[1], "",
            "Пишет `tc_plan.py validate` из разделов 4, 9, 11-14. Файлы и public-методы только отсюда:"
            " лишнее `at_tools.py check` находит как ВНЕ ПЛАНА и МЕТОД ВНЕ ПЛАНА."]
    analogs = {}
    for line in re.findall(r"(?m)^- (\w+) · `([^`]+)` ·", text):
        if not config_class(line[1]):
            analogs.setdefault(line[0], line[1])
    g_group = {g[0]: g for g in gens}
    test_file = head.get("test_file", "-")
    order = sorted(methods, key=lambda m: [float(x) if re.fullmatch(r"[\d.]+", x) and x.count(".") <= 1 else 0 for x in ids(m[3])][:1])
    for f in files:
        path, action, what, g = f[:4]
        if action not in ("создать", "дополнить"):
            continue
        tag = "[ADDED]" if action == "создать" else "[MODIFIED]"
        name = Path(path).stem if path.endswith(".java") else path.rsplit("/", 1)[-1]
        out += ["", "### " + tag + " `" + name + "`",
                "- Файл: `" + path + "`" + (" (новый)" if action == "создать" else " (есть в проекте, добавляются только методы ниже;"
                                                                                  " существующие методы не меняются)")]
        if path.endswith(".java"):
            out.append("- Пакет: `" + java_package(path) + "`")
        if path == test_file:
            out.append("- Базовый класс: `" + head.get("base_fqn", "-") + "`")
            out.append("- Аннотации: " + ("ТК нет (ключ " + head.get("tc", "-") + ") - без @TmsLink"
                                          if head.get("tc", "").startswith("NOTC-") else "`@TmsLink(\"" + head.get("tc", "-") + "\")`"))
            own = [c for c in consts if c[2] == "TEST_CLASS_STATIC_FINAL"]
            out.append("- Константы класса: " + (", ".join("`" + c[0] + "` = `" + c[1] + "`" for c in own) or "нет"))
            other = [c for c in consts if c[2] != "TEST_CLASS_STATIC_FINAL"]
            if other:
                out.append("- Значения не в тест-классе: " + ", ".join("`" + c[0] + "` - " + c[2] for c in other))
            out.append("- Тест-метод: шаги ТК по порядку")
            done = set()
            for r in steps:
                m = by_step.get(r[0])
                if r[3] == "SERVICE":
                    out.append("  - шаг " + r[0] + ": служебный, кода нет")
                elif m and id(m) not in done:
                    done.add(id(m))
                    args = ", ".join(n + " (" + w + ")" for n, _, w in params(m[5])) or "без параметров"
                    out.append("  - шаги " + m[3] + ": `// Шаг n: <действие>` и вызов `" + m[1] + "." + m[2] + "(...)` - " + args)
            continue
        own_methods = [m for m in order if m[1] == name]
        if path.endswith(".java"):
            for m in own_methods:
                cks = [c for c in checks if c[0] in ids(m[3]) and not c[3].startswith("проверено в шаге")]
                out.append("- Метод (public): `" + signature(m).split(".", 1)[1] + "` - шаги " + m[3]
                           + ("; запрос " + m[4] if m[4] not in ("-", "") else ""))
                for n, t, w in params(m[5]):
                    out.append("  - параметр `" + n + "` (" + t + ") - " + w)
                for c in cks:
                    out.append("  - проверка шага " + c[0] + ": " + check_text(c))
            if not own_methods:
                out.append("- Методы: нет строк в разделе 12")
            if action == "создать":
                group = next((g_group[x][2] for x in ids(g) if x in g_group), "")
                ref = next((g_group[x][5] for x in ids(g) if x in g_group), "-")
                out.append("- Аналог: " + ("`" + analogs[group] + "`" if group in analogs else "в проекте нет - по справке " + ref))
        else:
            keys = [x for x in settings if x[1] == path]
            for x in keys:
                out.append("- Ключ: `" + x[0] + "` = `" + x[2] + "` - читает " + x[3])
            out.append("- Что: " + what)
        out.append("- G: " + g)
    rest = [f for f in files if f[1] not in ("создать", "дополнить")]
    if rest:
        out += ["", "### Без правок генерации"]
        out += ["- `" + f[0] + "` - " + f[1] + ": " + f[2] for f in rest]
    out += ["", "### Порядок и зависимости"]
    for n, g in enumerate(gens, 1):
        names = sorted({m[1] for m in methods if m[0] == g[0]})
        out.append(str(n) + ". " + g[0] + " (" + g[3] + ", шаги " + g[1] + "): " + (", ".join("`" + x + "`" for x in names) or "-"))
    out.append(str(len(gens) + 1) + ". Сборка тест-класса `" + Path(test_file).name + "` из фрагментов G, `at_tools.py check` - находок 0.")
    out.append(str(len(gens) + 2) + ". Запуск теста `at_tools.py run` - последняя задача, человека не спрашивать.")
    return out


def put_derived(text):
    """Записать разделы 15-16 перед журналом (повторный запуск их пересоздаёт)."""
    text = strip_derived(text)
    head = dict(re.findall(r"(?m)^(\w+):\s*(.*)$", text.split("\n---", 1)[0]))
    block = "\n".join(derived_sections(text, head)).lstrip("\n") + "\n\n"
    m = re.search(r"(?m)^## \d+\. Журнал", text)
    if not m:
        return text.rstrip("\n") + "\n\n" + block
    return text[:m.start()] + block + "## 17. Журнал" + text[m.end():]


def approve(key):
    """Человек подтвердил план (разделы 11-16) -> approved: yes <отпечаток>. План изменится - подтверждение снимается."""
    plan = tcc.pp.plan_file(key, create=False)
    text = plan.read_text(encoding="utf-8") if plan.is_file() else ""
    head = dict(re.findall(r"(?m)^(\w+):\s*(.*)$", text.split("\n---", 1)[0]))
    if head.get("plan_status") not in ("planned", "generating", "assembled", "checked"):
        print("НЕЛЬЗЯ: plan_status " + head.get("plan_status", "-") + " - сначала tc_plan.py validate " + key + " (план должен сойтись)")
        return 1
    mark = "approved: yes " + plan_hash(text)
    text = re.sub(r"(?m)^approved:.*$", mark, text, count=1) if re.search(r"(?m)^approved:", text) \
        else re.sub(r"(?m)^(plan_status:[^\n]*)$", r"\1\n" + mark, text, count=1)
    plan.write_text(text.rstrip("\n") + "\n| approve | план подтверждён человеком |\n", encoding="utf-8")
    print("ПОДТВЕРЖДЕНО: " + mark)
    return 0


def validate(key):
    plan = tcc.pp.plan_file(key, create=False)
    if not plan.is_file():
        print("НЕТ ПЛАНА " + str(plan).replace("\\", "/") + ": сначала tc_plan.py build " + key)
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
    if head.get("step_style") not in ("steps", "flow"):
        problems.append("архитектура тестов не выбрана (step_style «" + head.get("step_style", "-") + "») - спроси человека"
                        " «Как писать тесты: steps - классы шагов, или flow - FlowRunner и классы-флоу?», ответ:"
                        " tc_plan.py style " + key + " <steps|flow>")
    arts = load_artifacts(tcc.pp.autotest_dir(key, create=False))
    if arts["status"] == "нужен":
        problems.append("разбор артефактов не закончен - artifacts.py task " + key + " -> агент pvatf-artifacts -> artifacts.py merge " + key)
    steps = table(text, "2. Шаги")
    gens = {r[0]: r for r in table(text, "3. Порядок генерации")}
    linked = {r[0] for r in table(text, "9. Запросы из артефактов")}
    if arts["inventory"]:
        for r in steps:
            if len(r) >= 11 and r[3] == "OPERATION" and r[4] in ("integration", "db", "kafka") and r[0].split(".")[0] not in linked:
                problems.append("шаг " + r[0] + ": запрос без связи с описью артефактов (раздел 9) - разбор агентом pvatf-artifacts"
                                " должен назвать A-n или «нет в артефактах»")
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
        if re.fullmatch(r"EXPECTED_[0-9_]+", c[0]):
            problems.append("константа " + c[0] + ": имя по значению - назови по полю, которое проверяет шаг (EXPECTED_ACC_STATE)")
        if c[0] != "-" and (len(c) < 6 or c[2] not in ("GLOBAL_CONSTANTS_CLASS", "TEST_CLASS_STATIC_FINAL", "CONFIG_OWNER",
                                                     "PROPERTIES_FILE", "TESTDATA_FILE_REF", "ENUM", "REUSE_FRAGMENT")):
            problems.append("константа " + c[0] + ": источник «" + (c[2] if len(c) > 2 else "-") + "» - выбери по references/classify.md, раздел «Константы»")
    problems += detail_problems(text, head, steps)
    if problems:
        for p in problems:
            print("ПРОБЛЕМА: " + p)
        print("ИТОГ: план не сошёлся, проблем " + str(len(problems)))
        return 1
    approved = head.get("approved", "no").split()
    still = len(approved) == 2 and approved[0] == "yes" and approved[1] == plan_hash(text)
    mark = "approved: " + ("yes " + approved[1] if still else "no")
    text = re.sub(r"(?m)^approved:.*$", mark, text, count=1) if re.search(r"(?m)^approved:", text) \
        else re.sub(r"(?m)^(plan_status:[^\n]*)$", r"\1\n" + mark, text, count=1)
    text = re.sub(r"(?m)^plan_status:\s*\S+", "plan_status: planned", text, count=1)
    text = put_derived(text)
    text = text.rstrip("\n") + "\n| validate | план сошёлся: шагов %d, G %d |\n" % (len(steps), len(gens))
    plan.write_text(text, encoding="utf-8")
    print("ИТОГ: план сошёлся, plan_status: planned · шагов %d · G %d" % (len(steps), len(gens)))
    if not still:
        print("ПОДТВЕРЖДЕНИЕ: нужно - покажи человеку разделы 11-16 design.md (файлы, методы шагов, проверки, настройки, привязка шагов, планируемые изменения) и"
              " спроси «План верен? да / номер строки и как исправить»; «да» -> tc_plan.py approve " + key)
    return 0


def main(args):
    if len(args) < 2 or args[0] not in ("build", "validate", "style", "approve"):
        print("Использование: tc_plan.py build <ключ ТК> [--force] | validate <ключ ТК> | style <ключ ТК> <steps|flow>"
              " | approve <ключ ТК>")
        return 2
    if args[0] == "approve":
        return approve(args[1])
    if args[0] == "style":
        return set_style(args[1], args[2] if len(args) > 2 else "")
    return build(args[1], "--force" in args) if args[0] == "build" else validate(args[1])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
