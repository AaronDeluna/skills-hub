"""Общий разбор TC.md и словари маркеров для скриптов скилла autotest-plan. Сам не запускается.
Python 3.8+, только стандартная библиотека."""
import re
from pathlib import Path

DATA = Path(".gigacode") / "data" / "autotest"

# Глаголы действий (основа слова) -> тип шага. Порядок проверки типов - PRIORITY.
TYPE_VERBS = {
    "ASSERT": ["провер", "убедит", "сравн", "валидац", "валидир", "должен", "должна", "должно", "отображает", "совпада", "равн", "содерж", "присутств", "соответств"],
    "TEARDOWN_CLEANUP": ["удалить созданн", "очист", "закрыть соединен", "закрыть сесси", "откат", "вернуть исходн"],
    "NAVIGATION": ["перейти", "открыть страниц", "открыть раздел", "открыть экран", "открыть вкладк", "прокрут", "вернуться на"],
    "AUTH_SESSION": ["авториз", "войти", "логин", "получить токен", "открыть сесси", "аутентиф", "sign in"],
    "OPERATION": ["отправ", "выполн", "создать", "создай", "изменить", "обнов", "удалить", "нажать", "нажми", "ввести", "введи", "выбрать", "загруз", "скачать", "опубликов", "вызвать", "сохранить", "заполн", "кликн"],
    "SETUP": ["подготов", "настро", "инициализ", "создать тестов", "сгенерир"],
}
PRIORITY = ["ASSERT", "TEARDOWN_CLEANUP", "NAVIGATION", "AUTH_SESSION", "OPERATION", "SETUP"]

# Группа -> [(технология, метка конспекта, [маркеры])]; маркер ищется в тексте шага без учёта регистра.
GROUPS = [
    ("kafka", [("Работа с Kafka", "kafka", ["kafka", "кафк", "топик", "продюсер", "консьюмер", "producer", "consumer", "сообщение в шину"])]),
    ("db", [("Работа с OpenSearch/ElasticSearch", "opensearch", ["opensearch", "elastic"]),
            ("Работа с DataSource", "db", ["datasource"]),
            ("Работа с Базами Данных", "db", ["select ", "insert ", "update ", "delete from", "sql", "в бд", "в базе", "базы данных", "таблиц", "postgres", "oracle"])]),
    ("logs_metrics", [("Работа с Единым Аудитом", "audit", ["аудит"]),
                      ("Работа с Журналами ЕФС и ППРБ", "journals", ["журнал", "ефс", "ппрб"]),
                      ("Работа с PVM-ABYSS", "abyss", ["pvm-abyss", "abyss"]),
                      ("Работа с хранилищем метрик Thanos/Victoria Metrics", "metrics", ["thanos", "victoria", "метрик"]),
                      ("Работа с СУП-Параметрами", "sup", ["суп"])]),
    ("mobile", [("Работа с Appium iOS", "mobile", ["ios", "iphone"]),
                ("Работа с Appium Android", "mobile", ["appium", "android", "мобильн", "мп ", "мр сбол"])]),
    ("tools", [("Сервис для работы с Fixtures", "fixtures", ["fixture", "фикстур"]),
               ("Сервис для работы с Таймаутами", "timeouts", ["таймаут", "timeout"]),
               ("Работа с TestContainers", "testcontainers", ["testcontainers", "контейнер"]),
               ("Работа с SberMock", "sbermock", ["sbermock", "заглушк", "мок "]),
               ("Работа с OpenShift и Kubernetes", "openshift", ["openshift", "kubernetes", "под ", "pod"]),
               ("Работа с DataConverter", "dataconverter", ["dataconverter", "конверт"]),
               ("Работа с Toggler", "toggler", ["toggler", "тоглер", "фич-флаг", "feature toggle"]),
               ("Работа с Launcher", "launcher", ["launcher", "лаунчер"])]),
    ("integration", [("Работа с gRPC", "grpc", ["grpc"]),
                     ("Работа с GraphQL", "graphql", ["graphql"]),
                     ("Работа с WebSocket", "websocket", ["websocket", "веб-сокет", "ws://", "wss://"]),
                     ("Работа с Rest API", "rest", ["rest", "http", "post", "get ", "put ", "patch", "delete ", "эндпоинт", "endpoint", "/api/", "запрос", "ответ", "json", "statuscode", "код ответа", "jsonpath"])]),
    ("ui", [("Работа с UI", "ui", ["selenide", "playwright", "браузер", "страниц", "кнопк", "клик", "нажать", "поле ", "форм", "экран", "вкладк", "ссылк", "чекбокс", "отображается"])]),
    ("other", [("Работа с Сессиями", "sessions", ["сесси", "авториз"]),
               ("ValueService", "value", ["valueservice", "сгенерир", "случайн"]),
               ("Работа с Invocation", "invocation", ["invocation"])]),
]
GROUP_NAMES = [g for g, _ in GROUPS]


def lower(value):
    return " " + value.lower().replace("<br>", " ") + " "


def parse_tc(path):
    """TC.md (формат tc_convert.py) -> dict: key, title, fields{}, steps[{n, action, data, expected}]."""
    source = Path(path).read_text(encoding="utf-8")
    head = re.match(r"#\s*(\S+)\s*·\s*(.*)", source)
    tc = {"key": head.group(1) if head else "-", "title": head.group(2).strip() if head else "-", "fields": {}, "steps": []}
    for m in re.finditer(r"(?m)^- ([^:\n]+):\s*(.*)$", source):
        tc["fields"][m.group(1).strip()] = m.group(2).strip()
    for line in source.split("\n"):
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if len(cells) >= 4 and re.fullmatch(r"\d+", cells[0]):
            clean = [("" if c == "-" else c.replace("\\|", "|")) for c in cells]
            tc["steps"].append({"n": int(cells[0]), "action": clean[1], "data": clean[2], "expected": clean[3]})
    return tc


def step_type(text):
    low = lower(text)
    for kind in PRIORITY:
        if any(v in low for v in TYPE_VERBS[kind]):
            return kind
    return "UNKNOWN_TYPE"


def classify(text):
    """-> (группа, технология, метка, уверенность, маркеры)."""
    low = lower(text)
    hits = []
    for group, techs in GROUPS:
        for tech, label, markers in techs:
            found = [m.strip() for m in markers if m in low]
            if found:
                hits.append((group, tech, label, found))
    if not hits:
        return "UNKNOWN_GROUP", "UNKNOWN_TECHNOLOGY", "-", "LOW", []
    groups = {h[0] for h in hits}
    group, tech, label, found = hits[0]
    confidence = "HIGH" if len(groups) == 1 and len(found) >= 1 else "MEDIUM"
    if len(groups) > 1:
        confidence = "LOW"
    return group, tech, label, confidence, found


def actions_in(text):
    """Сколько разных действий в тексте шага (для атомарности)."""
    low = lower(text)
    verbs = set()
    for kind in ("OPERATION", "NAVIGATION", "AUTH_SESSION", "ASSERT"):
        for verb in TYPE_VERBS[kind]:
            if re.search(r"(^|[\s,;(])" + re.escape(verb), low):
                verbs.add(kind + ":" + verb)
    return verbs
