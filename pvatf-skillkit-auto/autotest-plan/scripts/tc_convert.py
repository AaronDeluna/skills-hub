#!/usr/bin/env python3
"""Тест-кейс из TMS (md, xml, json) -> единый TC.md (скилл autotest-plan). Запуск из корня проекта:

  python3 <скилл>/scripts/tc_convert.py <файл ТК> [--key <ключ>]

Понимает: Markdown по шаблону ТК (поля **Название:**, **Ключ:**, таблица «Шаги выполнения»),
выгрузки Zephyr Scale / TestOps в XML и JSON (testCase, testScript/steps, step/description/
testData/expectedResult), результат Allure (*-result.json: name, steps[].name). HTML в полях
(<br>, <pre>, <p>) превращается в текст. Ключа в файле нет -> нужен --key.
Пишет .gigacode/data/autotest/<ключ>/TC.md и печатает: ТК, ШАГОВ, ФАЙЛ.
Python 3.8+, только стандартная библиотека. Код выхода: 0 - записано, 1 - шагов нет или формат
не распознан, 2 - неверные аргументы.
"""
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DATA = Path(".gigacode") / "data" / "autotest"
KEY = re.compile(r"\b[A-Z][A-Z0-9]*-T[0-9]+\b")
FIELDS = [("title", "Название"), ("key", "Ключ"), ("system", "КЭ"), ("priority", "Приоритет"),
          ("status", "Статус"), ("folder", "Папка"), ("kind", "Вид теста"), ("objective", "Цель"),
          ("precondition", "Предусловия"), ("test_data", "Требования к тестовым данным"), ("tags", "Тэги")]


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
            tc["steps"].append(step(action, first(inline, "testData", "data"),
                                    first(inline, "expectedResult", "expected", "result")))
            if item.get("steps") and not first(inline, "expectedResult", "expected"):
                walk(item["steps"])
    walk(find_steps(obj))
    return tc


def render(tc):
    out = ["# " + tc["key"] + " · " + (tc.get("title") or "-"), ""]
    for name, label in FIELDS:
        out.append("- " + label + ": " + (tc.get(name) or "-"))
    out += ["", "## Шаги", "", "| № | Действие | Тестовые данные | Ожидаемый результат |",
            "|---|----------|-----------------|---------------------|"]
    for number, s in enumerate(tc["steps"], 1):
        out.append("| %d | %s | %s | %s |" % (number, s["action"] or "-", s["data"] or "-", s["expected"] or "-"))
    return "\n".join(out) + "\n"


def main(args):
    if not args or args[0].startswith("-"):
        print("Использование: tc_convert.py <файл ТК: .md, .xml, .json> [--key <ключ>]")
        return 2
    path = Path(args[0])
    try:
        source = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        print("ФАЙЛ НЕ ЧИТАЕТСЯ: " + str(error))
        return 1
    try:
        if path.suffix.lower() == ".xml" or source.lstrip().startswith("<"):
            tc = from_xml(source)
        elif path.suffix.lower() == ".json" or source.lstrip()[:1] in "[{":
            tc = from_json(source)
        else:
            tc = from_markdown(source)
    except (ET.ParseError, ValueError) as error:
        print("ФОРМАТ НЕ РАСПОЗНАН: " + str(error))
        return 1
    if "--key" in args and args.index("--key") + 1 < len(args):
        tc["key"] = args[args.index("--key") + 1]
    if not tc.get("key"):
        found = KEY.search(source)
        tc["key"] = found.group() if found else ""
    if not tc.get("key"):
        print("КЛЮЧА НЕТ: в файле нет ключа тест-кейса вида CODE-T123 - запусти с --key <ключ>")
        return 1
    tc["key"] = re.sub(r"[^A-Za-z0-9_-]", "", tc["key"])
    steps = [s for s in tc["steps"] if s["action"] or s["expected"]]
    tc["steps"] = steps
    if not steps:
        print("ШАГОВ НЕТ: в файле не найдено ни одного шага (таблица «Шаги выполнения», steps, testScript)")
        return 1
    target = DATA / tc["key"] / "TC.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(tc), encoding="utf-8")
    print("ТК: " + tc["key"] + " · " + (tc.get("title") or "-"))
    print("ШАГОВ: " + str(len(steps)))
    print("ФАЙЛ: " + str(target).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
