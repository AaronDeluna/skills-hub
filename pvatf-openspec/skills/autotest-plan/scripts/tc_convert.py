#!/usr/bin/env python3
"""Тест-кейс или другой артефакт -> единый TC.md (скилл autotest-plan). Запуск из корня проекта:

  python3 <скилл>/scripts/tc_convert.py <файл или каталог> [--key <ключ>] [--method <тест-метод>] [--name <имя теста>]
  python3 <скилл>/scripts/tc_convert.py <файл или каталог> --no-tc --class <Имя>Test  - ТК ещё не заведён

Понимает:
- Markdown по шаблону ТК (поля **Название:**, **Ключ:**, таблица «Шаги выполнения», раздел «Тэги»);
- выгрузки Zephyr Scale / TestOps в XML и JSON (testCase, testScript/steps, step/description/
  testData/expectedResult), ответ Jira MCP zephyr_get_testcase;
- Allure: файл *-result.json или каталог allure-results/ (один тест; несколько - нужен --name или --key);
- лог прогона (.log, .txt): шаги из @Step / Allure-шагов, HTTP-запросов (и лог RestAssured, где метод, адрес,
  заголовки и тело - на разных строках), SQL (и многострочного), топиков Kafka, ошибок проверок;
- код автотеста на любом фреймворке (.java, .kt): шаги из Allure.step, методов @Step, вызовов
  REST / SQL / Kafka, проверок; @BeforeEach / @BeforeAll - предусловия, @AfterEach / @AfterAll -
  шаги очистки; импорты - строка «Технологии источника». Несколько тестов в файле - нужен --method.
HTML в полях (<br>, <pre>, <p>) превращается в текст. Ключа нет -> нужен --key или, если ТК ещё не
заведён, --no-tc --class <Имя>Test: служебный ключ NOTC-<n> (следующий свободный номер), имя тест-класса -
из --class (строка «Класс теста» в TC.md), @TmsLink в тест не ставится.
Пишет TC.md в рабочий каталог автотеста (OpenSpec: openspec/changes/<имя>/outputs/) и печатает: ТК, ШАГОВ,
ИСТОЧНИК, ФАЙЛ. Секреты (sid, token, password, Authorization, cookie) в TC.md - ***.
Python 3.8+, только стандартная библиотека. Код выхода: 0 - записано, 1 - шагов нет или формат
не распознан, 2 - неверные аргументы.
"""
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pvatf_paths as pp  # noqa: E402 - копия shared/scripts
import log_parse as lp  # noqa: E402
DATA = Path(".gigacode") / "data" / "autotest"
KEY = re.compile(r"\b[A-Z][A-Z0-9]*-T[0-9]+\b")
FIELDS = [("title", "Название"), ("key", "Ключ"), ("system", "КЭ"), ("priority", "Приоритет"),
          ("status", "Статус"), ("folder", "Папка"), ("kind", "Вид теста"), ("objective", "Цель"),
          ("precondition", "Предусловия"), ("test_data", "Требования к тестовым данным"), ("tags", "Тэги"),
          ("source", "Источник"), ("source_tech", "Технологии источника"), ("origin", "Файл источника"),
          ("test_class", "Класс теста")]
NO_TC = "NOTC"  # префикс служебного ключа работы без ТК: NOTC-1, NOTC-2
JAVA_CLASS = re.compile(r"[A-Z][A-Za-z0-9]*Test")
TAG = re.compile(r"@[A-Za-z][\w]*(?:\([^)]*\))?")
# импорт -> технология (строка «Технологии источника»; читает tc_plan.py, раздел «Окружение под ТК»)
IMPORT_TECH = [("io.restassured", "rest"), ("okhttp", "rest"), ("org.apache.http", "rest"), ("java.net.http", "rest"),
               ("org.springframework.web.client", "rest"), ("io.grpc", "grpc"), ("graphql", "graphql"),
               ("websocket", "websocket"), ("java.sql", "db"), ("jdbc", "db"), ("javax.persistence", "db"),
               ("org.opensearch", "opensearch"), ("elasticsearch", "opensearch"), ("kafka", "kafka"),
               ("com.codeborne.selenide", "ui"), ("com.microsoft.playwright", "ui"), ("org.openqa.selenium", "ui"),
               ("io.appium", "mobile"), ("org.testcontainers", "testcontainers"), ("wiremock", "sbermock"),
               ("mockserver", "sbermock"), ("io.fabric8.kubernetes", "openshift"), ("io.fabric8.openshift", "openshift")]


def text(value):
    """HTML и разметку поля - в одну строку текста; переводы строк - «<br>» (ячейка таблицы)."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = "; ".join(text(v) for v in value)
    value = str(value)
    value = re.sub(r"(?i)<br\s*/?>|</p>|</pre>|</li>|</div>", "\n", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value).replace("\r", "")
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in value.split("\n")]
    return "<br>".join(l for l in lines if l).replace("|", "\\|")


def step(action, data="", expected=""):
    return {"action": text(action), "data": text(data), "expected": text(expected)}


# ---------- Markdown ----------

def from_markdown(source):
    tc = {"steps": []}
    for name, label in FIELDS:
        m = re.search(r"(?m)^\s*(?:\*\*)?" + re.escape(label) + r"(?:\*\*)?\s*:\s*(?:\*\*)?\s*(.+?)\s*$", source)
        if m:
            tc[name] = text(m.group(1).strip("* "))
    tags_sect = re.search(r"(?ms)^#{2,4}\s*Т[эе]ги[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", source)
    if tags_sect and not tc.get("tags"):
        tc["tags"] = text("; ".join(TAG.findall(tags_sect.group(1))))
    for name, label in (("objective", "Цель"), ("precondition", "Предусловия")):
        sect = re.search(r"(?ms)^#{2,4}\s*" + label + r"[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", source)
        if sect and not tc.get(name):
            tc[name] = text(sect.group(1).strip())
    head = None
    for line in source.split("\n"):
        if not line.strip().startswith("|"):
            head = None if head and not line.strip() else head
            continue
        cells = [c.strip().strip("*").strip() for c in line.strip().strip("|").split("|")]
        low = [c.lower() for c in cells]
        if any("шаг" in c or "описание" in c or "действие" in c for c in low) and any("ожидаем" in c for c in low):
            head = low
            continue
        if head is None or set(line.replace("|", "").strip()) <= set("-: "):
            continue
        row = dict(zip(head, cells))

        def pick(*words):
            for k, v in row.items():
                if any(w in k for w in words):
                    return v
            return ""
        number = pick("№", "n")
        action = pick("описание", "действие", "шаг")
        if action and (number == "" or re.match(r"^\d+(\.\d+)?$", number)):
            tc["steps"].append(step(action, pick("данн"), pick("ожидаем")))
    if not tc["steps"]:
        sect = re.search(r"(?ms)^#{2,4}\s*Шаги[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", source)
        for m in re.finditer(r"(?m)^\s*\d+[.)]\s+(.+)$", sect.group(1) if sect else ""):
            tc["steps"].append(step(m.group(1)))
    return tc


# ---------- XML ----------

def local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def child_text(node, *names):
    for sub in node.iter():
        if local(sub.tag) in names and (sub.text or "").strip():
            return "".join(sub.itertext())
    return ""


def from_xml(source):
    root = ET.fromstring(source)
    case = next((n for n in root.iter() if local(n.tag) in ("testcase", "test-case", "case")), root)
    tc = {"steps": [],
          "key": case.get("key") or child_text(case, "key"),
          "title": child_text(case, "name", "title"),
          "objective": child_text(case, "objective", "description"),
          "precondition": child_text(case, "precondition", "preconditions"),
          "priority": child_text(case, "priority"),
          "status": child_text(case, "status"),
          "folder": child_text(case, "folder"),
          "tags": "; ".join("".join(l.itertext()) for l in case.iter() if local(l.tag) == "label")}
    for name, value in list(tc.items()):
        if name != "steps":
            tc[name] = text(value)
    steps = [n for n in case.iter() if local(n.tag) == "step"]
    steps.sort(key=lambda n: int(n.get("index", "0")) if (n.get("index") or "0").isdigit() else 0)
    for n in steps:
        tc["steps"].append(step(child_text(n, "description", "action", "name"),
                                child_text(n, "testdata", "data"), child_text(n, "expectedresult", "expected", "result")))
    return tc


# ---------- JSON ----------

def first(obj, *names):
    for name in names:
        if isinstance(obj, dict) and obj.get(name) not in (None, "", []):
            return obj[name]
    return ""


def find_steps(obj):
    if isinstance(obj, dict):
        for name in ("steps", "testScript", "scenario"):
            value = obj.get(name)
            if isinstance(value, dict):
                value = find_steps(value)
            if isinstance(value, list) and value:
                return value
    return []


def from_json(source):
    obj = json.loads(source)
    if isinstance(obj, list):
        obj = obj[0] if obj else {}
    if "testCase" in obj and isinstance(obj["testCase"], dict):
        obj = dict(obj["testCase"], **{k: v for k, v in obj.items() if k != "testCase"})
    labels = obj.get("labels") or []
    tags = [l.get("value", "") if isinstance(l, dict) else str(l) for l in labels] if isinstance(labels, list) else [str(labels)]
    tc = {"key": text(first(obj, "key", "testCaseKey", "tmsLink")), "title": text(first(obj, "name", "title")),
          "objective": text(first(obj, "objective", "description", "descriptionHtml")),
          "precondition": text(first(obj, "precondition", "preconditions")),
          "priority": text(first(obj, "priority", "severity")), "status": text(first(obj, "status")),
          "folder": text(first(obj, "folder", "fullName")), "tags": text("; ".join(t for t in tags if t)), "steps": []}
    for link in obj.get("links") or []:
        if isinstance(link, dict) and not tc["key"] and KEY.search(str(link.get("name", ""))):
            tc["key"] = KEY.search(str(link["name"])).group()

    def walk(items, prefix=""):
        for item in items:
            if isinstance(item, str):
                tc["steps"].append(step(item))
                continue
            inline = item.get("inline") if isinstance(item.get("inline"), dict) else item
            action = first(inline, "description", "action", "name", "step")
            params = item.get("parameters") if isinstance(item.get("parameters"), list) else []
            data = first(inline, "testData", "data") or "; ".join(
                "%s=%s" % (p.get("name", ""), p.get("value", "")) for p in params if isinstance(p, dict))
            tc["steps"].append(step(action, data, first(inline, "expectedResult", "expected", "result")))
            if item.get("steps") and not first(inline, "expectedResult", "expected"):
                walk(item["steps"])
    walk(find_steps(obj))
    if "uuid" in obj or "historyId" in obj or "start" in obj:
        tc["source"] = "allure"
        layer = [l.get("value") for l in labels if isinstance(l, dict) and l.get("name") == "layer"]
        if layer:
            tc["tags"] = text("; ".join([t for t in tags if t] + ['@TestLayer("%s")' % layer[0]]))
        if not tc["steps"] and tc["title"]:
            tc["steps"].append(step(tc["title"]))
    return tc


def from_allure_dir(folder, key, name):
    """Каталог allure-results/ -> один тест: по --key (ссылки, метки) или --name (часть имени)."""
    found = []
    for path in sorted(folder.glob("*-result.json")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        blob = json.dumps(obj.get("links", []), ensure_ascii=False) + json.dumps(obj.get("labels", []), ensure_ascii=False)
        if key and key not in blob and key not in str(obj.get("name", "")):
            continue
        if name and name.lower() not in str(obj.get("name", "")).lower() and name.lower() not in str(obj.get("fullName", "")).lower():
            continue
        found.append((path, obj))
    if not found:
        raise ValueError("в каталоге нет подходящих *-result.json" + (" для " + (key or name) if key or name else ""))
    names = sorted({str(o.get("fullName") or o.get("name")) for _, o in found})
    if len(names) > 1:
        raise LookupError("ТЕСТОВ НЕСКОЛЬКО: " + "; ".join(names[:20]) + " - запусти с --name <часть имени> или --key <ключ>")
    path, obj = max(found, key=lambda f: f[1].get("stop", 0) or 0)  # последний прогон
    return from_json(json.dumps(obj, ensure_ascii=False))


# ---------- лог прогона ----------

def from_log(source):
    """Лог CI/консоли -> шаги (разбор - log_parse.events). Действие: строка шага Allure/@Step, HTTP-запрос
    (в том числе лог RestAssured, где метод, адрес, заголовки и тело - на разных строках), SQL
    (в том числе многострочный), топик Kafka. Ожидаемый результат: код ответа, AssertionError expected/but was.
    Тестовые данные запроса: хост, имена заголовков, тело (секреты - ***). Полная опись - artifacts.py."""
    tc = {"steps": [], "source": "log"}
    title = re.search(r"(?:Running|Test(?:ing)?|Тест)\s*[:=]?\s+([\w.$#]+(?:\(\))?)", source)
    tc["title"] = title.group(1) if title else ""
    for e in lp.events(source):
        if e["kind"] == "step":
            tc["steps"].append(step(e["action"]))
        elif e["kind"] == "http":
            data = []
            if lp.host_of(e["url"]):
                data.append("хост: " + lp.host_of(e["url"]))
            if e["headers"]:
                data.append("заголовки: " + ", ".join(n for n, _ in e["headers"]))
            if e["body"]:
                data.append("тело: " + re.sub(r"\s+", " ", lp.mask(e["body"]))[:1500])
            tc["steps"].append(step("Отправить " + e["method"] + " " + (lp.path_of(e["url"]) or e["url"]), "\n".join(data),
                                    "код ответа " + e["status"] if e["status"] else ""))
        elif e["kind"] == "sql":
            tc["steps"].append(step("Выполнить SQL", e["sql"].replace("\n", " ")[:1500]))
        elif e["kind"] == "topic":
            verb = "Отправить сообщение в топик " if e["direction"] == "send" else "Прочитать сообщение из топика "
            tc["steps"].append(step(verb + e["topic"]))
        elif e["kind"] == "expect" and tc["steps"] and not tc["steps"][-1]["expected"]:
            tc["steps"][-1]["expected"] = text("значение = " + e["value"])
    return tc


# ---------- код автотеста (любой фреймворк) ----------

def body_at(source, start):
    """Тело метода: от первой «{» после start до парной «}»."""
    open_at = source.find("{", start)
    if open_at < 0:
        return ""
    depth = 0
    for index in range(open_at, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[open_at + 1:index]
    return source[open_at + 1:]


METHOD = re.compile(r"((?:\s*@\w+(?:\.\w+)*(?:\((?:[^()]|\([^()]*\))*\))?)+)\s*(?:public\s+|protected\s+|private\s+|static\s+|final\s+)*"
                    r"(?:fun\s+|void\s+|[\w<>\[\],\s]+?\s+)(\w+)\s*\(", re.S)


def code_steps(body, step_names):
    """Шаги из тела метода по порядку появления."""
    events = []
    for m in re.finditer(r"(?:Allure\.)?step\s*\(\s*\"([^\"]{3,200})\"", body):
        events.append((m.start(), "action", m.group(1)))
    for name, label in step_names.items():
        for m in re.finditer(r"(?<![\w.])(?:\w+\.)?" + re.escape(name) + r"\s*\(", body):
            events.append((m.start(), "action", label))
    for m in re.finditer(r"\.(get|post|put|patch|delete)\s*\(\s*\"([^\"]+)\"", body, re.I):
        events.append((m.start(), "action", "Отправить " + m.group(1).upper() + " " + m.group(2)))
    for m in re.finditer(r"\"((?:SELECT|INSERT|UPDATE|DELETE)\b[^\"]{5,200})\"", body, re.I):
        events.append((m.start(), "action", "Выполнить SQL: " + m.group(1)))
    for m in re.finditer(r"\b(?:send|produce|publish)\w*\s*\(\s*\"([\w.\-]{3,})\"", body):
        events.append((m.start(), "action", "Отправить сообщение в топик " + m.group(1)))
    for m in re.finditer(r"\.(?:statusCode|status|code)\s*\(\s*([1-5]\d\d)\s*\)", body):
        events.append((m.start(), "expected", "код ответа " + m.group(1)))
    for m in re.finditer(r"\b(assert\w*\s*\((?:[^();]|\([^()]*\))*\)(?:\.\w+\((?:[^();]|\([^()]*\))*\))*|\.should\w*\s*\((?:[^();]|\([^()]*\))*\))", body):
        events.append((m.start(), "expected", re.sub(r"\s+", " ", m.group(1))[:160]))
    steps = []
    for _, kind, value in sorted(events):
        if kind == "action":
            if not steps or steps[-1]["action"] != text(value):
                steps.append(step(value))
        elif steps:
            steps[-1]["expected"] = text((steps[-1]["expected"].replace("<br>", "; ") + "; " if steps[-1]["expected"] else "") + value)
        else:
            steps.append(step("Проверить результат", "", value))
    return steps


def from_code(source, method):
    tc = {"steps": [], "source": "code"}
    techs = sorted({tech for prefix, tech in IMPORT_TECH for imp in re.findall(r"(?m)^\s*import\s+([\w.]+)", source) if prefix in imp})
    tc["source_tech"] = ", ".join(techs)
    step_names, tests, before, after = {}, [], [], []
    for m in METHOD.finditer(source):
        notes, name = m.group(1), m.group(2)
        label = re.search(r"@Step\s*\(\s*(?:value\s*=\s*)?\"([^\"]+)\"", notes)
        if label:
            step_names[name] = label.group(1)
        if re.search(r"@(Test|ParameterizedTest|RepeatedTest|TestFactory)\b", notes):
            tests.append((name, notes, m.end()))
        elif re.search(r"@(BeforeEach|BeforeAll|BeforeMethod|BeforeClass|Before)\b", notes):
            before.append(m.end())
        elif re.search(r"@(AfterEach|AfterAll|AfterMethod|AfterClass|After)\b", notes):
            after.append(m.end())
    if method:
        tests = [t for t in tests if t[0] == method]
    if not tests:
        raise ValueError("в файле нет тест-метода" + (" " + method if method else " с @Test"))
    if len(tests) > 1:
        raise LookupError("ТЕСТОВ НЕСКОЛЬКО: " + ", ".join(t[0] for t in tests) + " - запусти с --method <имя метода>")
    name, notes, end = tests[0]
    shown = re.search(r"@DisplayName\s*\(\s*\"([^\"]+)\"", notes)
    tms = re.search(r"@TmsLink\s*\(\s*\"([^\"]+)\"", notes)
    tc["title"] = KEY.sub("", shown.group(1)).strip(" :-·") if shown else name
    tc["key"] = tms.group(1) if tms else (KEY.search(shown.group(1)).group() if shown and KEY.search(shown.group(1)) else "")
    tc["tags"] = text("; ".join(t for t in TAG.findall(notes) if not re.match(r"@(Test|DisplayName|TmsLink|Step|ParameterizedTest)\b", t)))
    pre = [s["action"] for e in before for s in code_steps(body_at(source, e), step_names)]
    tc["precondition"] = text("; ".join(pre))
    tc["steps"] = code_steps(body_at(source, end), step_names)
    for e in after:
        for s in code_steps(body_at(source, e), step_names):
            tc["steps"].append(step("Очистить после теста: " + s["action"].replace("<br>", " "), "", s["expected"]))
    return tc


def render(tc):
    out = ["# " + tc["key"] + " · " + (tc.get("title") or "-"), ""]
    for name, label in FIELDS:
        out.append("- " + label + ": " + (tc.get(name) or "-"))
    out += ["", "## Шаги", "", "| № | Действие | Тестовые данные | Ожидаемый результат |",
            "|---|----------|-----------------|---------------------|"]
    for number, s in enumerate(tc["steps"], 1):
        out.append("| %d | %s | %s | %s |" % (number, lp.mask(s["action"]) or "-", lp.mask(s["data"]) or "-", lp.mask(s["expected"]) or "-"))
    return "\n".join(out) + "\n"


def option(args, name):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else ""


def main(args):
    if not args or args[0].startswith("-"):
        print("Использование: tc_convert.py <файл ТК (.md .xml .json), лог (.log .txt), тест (.java .kt) или каталог allure-results> "
              "[--key <ключ>] [--method <тест-метод>] [--name <имя теста>] [--no-tc --class <Имя>Test]")
        return 2
    path = Path(args[0])
    key_arg, method, name = option(args, "--key"), option(args, "--method"), option(args, "--name")
    no_tc, test_class = "--no-tc" in args or bool(re.fullmatch(NO_TC + r"-[0-9]+", key_arg)), option(args, "--class")
    if no_tc and ((key_arg and not re.fullmatch(NO_TC + r"-[0-9]+", key_arg)) or not JAVA_CLASS.fullmatch(test_class)):
        if not JAVA_CLASS.fullmatch(test_class):
            print("НУЖЕН --class <Имя>Test: ТК нет, имя тест-класса даёт человек - латиницей с большой буквы, окончание Test,"
                  " без транслита (PaymentLockTest); спроси одной строкой «Имя тест-класса?» и запусти снова с --class")
        else:
            print("Использование: ТК нет - --key NOTC-<n> (из изменения) или --no-tc, и --class <Имя>Test")
        return 2
    suffix = path.suffix.lower()
    try:
        source = "" if path.is_dir() else path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        print("ФАЙЛ НЕ ЧИТАЕТСЯ: " + str(error))
        return 1
    try:
        if path.is_dir():
            tc = from_allure_dir(path, key_arg, name)
        elif suffix in (".java", ".kt"):
            tc = from_code(source, method)
        elif suffix in (".log", ".txt", ".out"):
            tc = from_log(source)
        elif suffix == ".xml" or source.lstrip().startswith("<"):
            tc = from_xml(source)
        elif suffix == ".json" or source.lstrip()[:1] in "[{":
            tc = from_json(source)
        else:
            tc = from_markdown(source)
    except LookupError as error:
        print(str(error))
        return 1
    except (ET.ParseError, ValueError) as error:
        print("ФОРМАТ НЕ РАСПОЗНАН: " + str(error))
        return 1
    tc.setdefault("source", "tms")
    tc["origin"] = path.as_posix().rstrip("/")  # по нему очередь генерации находит ключ ТК
    if key_arg:
        tc["key"] = key_arg
    if no_tc:
        tc["key"], tc["test_class"] = key_arg or pp.next_no_tc_key(), test_class
    if not tc.get("key"):
        found = KEY.search(source)
        tc["key"] = found.group() if found else ""
    if not tc.get("key"):
        print("КЛЮЧА НЕТ: в файле нет ключа тест-кейса вида CODE-T123 - спроси человека: ключ ТК (запусти с --key <ключ>)"
              " или «ТК нет» (спроси имя тест-класса и запусти с --no-tc --class <Имя>Test)")
        return 1
    tc["key"] = re.sub(r"[^A-Za-z0-9_-]", "", tc["key"])
    steps = [s for s in tc["steps"] if s["action"] or s["expected"]]
    tc["steps"] = steps
    if not steps:
        print("ШАГОВ НЕТ: в файле не найдено ни одного шага (таблица «Шаги выполнения», steps, testScript)")
        if tc.get("source") == "log":
            print("ИСКАЛ: @Step / Allure-шаги; «Request method:» + «Request URI:» (RestAssured); «POST https://...» со словом"
                  " request / запрос / --> в той же строке; SQL SELECT ... FROM; топики Kafka")
            for hint in lp.looks_like_requests(source):
                print("ПОХОЖЕ НА ЗАПРОС: " + hint)
        return 1
    target = pp.autotest_dir(tc["key"]) / "TC.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    text = render(tc)
    if no_tc:
        text = text.replace("- Ключ: " + tc["key"] + "\n", "- Ключ: " + tc["key"] + " - ТК нет: служебный ключ, ТК ещё не заведён\n")
    target.write_text(text, encoding="utf-8")
    print("ТК: " + tc["key"] + " · " + (tc.get("title") or "-") + (" - ТК нет, служебный ключ" if no_tc else ""))
    print("ШАГОВ: " + str(len(steps)))
    print("ИСТОЧНИК: " + tc["source"] + (" - шаги восстановлены скриптом, сверь их с артефактом" if tc["source"] in ("log", "code") else ""))
    print("ФАЙЛ: " + str(target).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
