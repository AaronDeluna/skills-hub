"""Разбор входных артефактов автотеста (скилл de-pvatf-autotest-plan): лог прогона, вложения Allure.
Сам не запускается - его импортируют tc_convert.py и artifacts.py из той же папки scripts/.

events(text) - события лога по порядку: шаг (@Step, Allure-шаг), HTTP-обмен (метод, адрес,
заголовки, тело, код и тело ответа), SQL (в том числе многострочный), топик Kafka, ошибка проверки.
Понимает:
- лог RestAssured (RequestLoggingFilter / ResponseLoggingFilter): «Request method:», «Request URI:»,
  «Headers:», «Body:», строка статуса «HTTP/1.1 200», заголовки и тело ответа - на разных строках;
- однострочные записи вида «POST https://host/v1/x», «--> POST /v1/x», «Sending request POST /v1/x»;
- вложения Allure (HTML или текст): «POST: https://...», разделы «Headers», «Body», «Status code».
mask(text) - секреты (sid, token, password, Authorization, cookie, ...) заменяются на ***.
Python 3.8+, только стандартная библиотека.
"""
import html
import re

METHODS = r"GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS"
SECRET_NAMES = re.compile(r"(?i)^(sid|session[-_]?id|jsessionid|token|access[-_]?token|refresh[-_]?token|id[-_]?token|"
                          r"authorization|proxy-authorization|cookie|set-cookie|password|passwd|pwd|secret|client[-_]?secret|"
                          r"api[-_]?key|x-api-key|x-auth-token)$")
SECRET = re.compile(r"(?i)(?<![\w.])(sid|session[-_]?id|jsessionid|token|access[-_]?token|refresh[-_]?token|authorization|"
                    r"cookie|password|passwd|pwd|secret|client[-_]?secret|api[-_]?key|x-api-key|x-auth-token)"
                    r"(\"?\s*[=:]\s*\"?|\s+(?=(?:bearer|basic)\s))((?:bearer|basic)\s+)?([A-Za-z0-9+/=._~\-]{6,})")
TS = re.compile(r"^(?:\[?\d{4}-\d{2}-\d{2}[ T])?\S*\d{2}:\d{2}:\d{2}\S*\s+(?:\[[^\]]*\]\s*)*(?:(?:TRACE|DEBUG|INFO|WARN|WARNING|ERROR)\s+)?(?:[\w.$]+\s+-\s+)?")
STEP = re.compile(r"(?:@Step|Allure\.step|\bStep|\bШаг)\s*[(:\-]\s*[\"«]?([^\"»)]{3,200})", re.I)
HTTP_LINE = re.compile(r"\b(" + METHODS + r")\b\s*:?\s+[\"']?((?:https?://)?[\w.:\-]*/[\w/{}.\-?=&%~:@]*)", re.I)
HTTP_HINT = re.compile(r"request|запрос|sending|calling|-->|>>|curl", re.I)
SQL_START = re.compile(r"(?i)(?:^|[\s:\"'(])(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|WITH)\b")
SQL_FULL = re.compile(r"(?is)\b(SELECT\b.+?\bFROM\b\s*\S+|INSERT\s+INTO\s+\S+|UPDATE\s+\S+\s+SET\b|DELETE\s+FROM\s+\S+|WITH\b.+?\bSELECT\b)")
TOPIC = re.compile(r"(?:topic|топик)\s*[=:(]?\s*[\"']?([\w.\-]{3,})", re.I)
STATUS_LINE = re.compile(r"^\s*HTTP/\d(?:\.\d)?\s+([1-5]\d\d)\b")
STATUS_FIELD = re.compile(r"(?i)^\s*(?:status\s*code|response\s*code|код ответа|status)\s*:?\s*([1-5]\d\d)\b")
EXPECT = re.compile(r"expected:?\s*<?\[?([^>\]]{1,80})\]?>?\s*but was:?\s*<?\[?([^>\]]{1,80})", re.I)
FIELD = re.compile(r"(?i)^\s*(request\s*method|request\s*ur[il]|proxy|request\s*params|query\s*params|form\s*params|"
                   r"path\s*params|headers|cookies|multiparts|body)\s*:\s*(.*)$")
NONE = ("", "<none>", "none", "null", "<empty>")


def mask(text):
    """Секреты в тексте -> ***: sid=abc123 -> sid=***, "token": "x" -> "token": "***", Bearer x -> Bearer ***."""
    return SECRET.sub(lambda m: m.group(1) + m.group(2) + (m.group(3) or "") + "***", text or "")


def mask_header(name, value):
    return "***" if SECRET_NAMES.match(name.strip()) else value


def clean(line):
    """Строка лога без отметки времени, уровня и имени логгера."""
    return TS.sub("", line.rstrip("\r"))


def from_html(text):
    """HTML вложения Allure -> строки текста."""
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", text)
    text = re.sub(r"(?i)<br\s*/?>|</(div|p|pre|h\d|li|tr|td|th)>|<(h\d)[^>]*>", "\n", text)
    return html.unescape(re.sub(r"<[^>]+>", "", text))


def new_http(method, url, line):
    return {"kind": "http", "method": method.upper(), "url": url, "headers": [], "body": "", "status": "",
            "response": "", "line": line}


def events(text):
    """-> список событий по порядку строк. Вид: step, http, sql, topic, expect."""
    raw = text.replace("\r\n", "\n").split("\n")
    lines = [clean(l) for l in raw]
    stamped = [TS.match(l) is not None and TS.match(l).group() != "" for l in raw]
    found, ex, state, i = [], None, "", 0

    def record_starts(k):
        """Строка k начинает новую запись лога (есть отметка времени) или новый шаг / SQL."""
        return stamped[k] or bool(STEP.search(lines[k])) or bool(re.match(r"(?i)\s*(SELECT|INSERT|UPDATE|DELETE)\b", lines[k]))

    while i < len(lines):
        line = lines[i]
        number = i + 1
        field = FIELD.match(line)
        status = STATUS_LINE.match(line) or (STATUS_FIELD.match(line) if ex and state in ("headers", "body", "url") else None)
        if field and field.group(1).lower().startswith("request") and "method" in field.group(1).lower():
            method = re.match(r"\s*(" + METHODS + r")\b", field.group(2), re.I)
            ex = new_http(method.group(1) if method else field.group(2).strip(), "", number)
            found.append(ex)
            state = "url"
        elif field and ex is not None and re.match(r"(?i)request\s*ur[il]", field.group(1)):
            ex["url"] = field.group(2).strip()
        elif field and ex is not None and field.group(1).lower() == "headers":
            state = "resp-headers" if ex["status"] else "headers"
            first = field.group(2).strip()
            if first.lower() not in NONE:
                add_header(ex, first)
        elif field and ex is not None and field.group(1).lower() == "body":
            state = "resp-body" if ex["status"] else "body"
            first = field.group(2).strip()
            if first.lower() not in NONE:
                ex["response" if ex["status"] else "body"] += first + "\n"
        elif field and ex is not None:
            state = "skip"
        elif status and ex is not None and not ex["status"]:
            ex["status"] = status.group(1)
            state = "resp-headers"
        elif state in ("headers", "resp-headers") and ex is not None and re.match(r"^\s*[\w\-]+\s*[=:]\s*\S", line) and not record_starts(i):
            if state == "headers":
                add_header(ex, line.strip())
        elif state in ("body", "resp-body") and ex is not None and not record_starts(i) and not STATUS_LINE.match(line) \
                and not re.match(r"(?i)\s*request\s*method\s*:", line):
            ex["response" if state == "resp-body" else "body"] += line + "\n"
        elif state == "resp-headers" and ex is not None and not line.strip():
            state = "resp-body"
        else:
            state = ""
            step = STEP.search(line)
            sql = SQL_START.search(line)
            single = HTTP_LINE.search(line)
            if step:
                found.append({"kind": "step", "action": step.group(1).strip(), "line": number})
            elif single and HTTP_HINT.search(line):
                ex = new_http(single.group(1), single.group(2), number)
                found.append(ex)
                state = "url"
            elif sql:
                chunk, k = [line[sql.start(1):]], i + 1
                while ";" not in chunk[-1] and k < len(lines) and len(chunk) < 80 and lines[k].strip() and not stamped[k]:
                    chunk.append(lines[k])
                    k += 1
                statement = SQL_FULL.search("\n".join(chunk))
                if statement:
                    found.append({"kind": "sql", "sql": "\n".join(chunk).split(";")[0].strip(), "line": number})
                    i = k - 1
            else:
                topic = TOPIC.search(line)
                if topic and re.search(r"send|produc|publish|отправ|consum|receiv|poll|получ|прочит", line, re.I):
                    found.append({"kind": "topic", "topic": topic.group(1),
                                  "direction": "send" if re.search(r"send|produc|publish|отправ", line, re.I) else "read",
                                  "line": number})
                expect = EXPECT.search(line)
                if expect:
                    found.append({"kind": "expect", "value": expect.group(1).strip(), "line": number})
                if status and found and found[-1]["kind"] == "http" and not found[-1]["status"]:
                    found[-1]["status"] = status.group(1)
        i += 1
    for e in found:
        if e["kind"] == "http":
            e["body"] = e["body"].strip()
            e["response"] = e["response"].strip()
            if e["body"].lower() in NONE:
                e["body"] = ""
    return [e for e in found if e["kind"] != "http" or e["url"]]


def add_header(ex, text):
    m = re.match(r"^\s*([\w\-]+)\s*[=:]\s*(.*)$", text)
    if m:
        ex["headers"].append((m.group(1), m.group(2).strip()))


def allure_events(text):
    """Вложение Allure (HTML или текст) -> события: запрос «POST: url» с разделами, ответ «Status code»."""
    lines = [l.strip() for l in from_html(text).split("\n")]
    found, ex, section = [], None, ""
    for line in lines:
        if not line:
            continue
        req = re.match(r"^(" + METHODS + r")\s*:?\s+(\S+)", line, re.I)
        code = re.match(r"(?i)^(?:status\s*code|response\s*code|код ответа)\s*:?\s*([1-5]\d\d)?", line)
        if req:
            ex = new_http(req.group(1), req.group(2), 0)
            found.append(ex)
            section = ""
        elif code:
            ex = ex or new_http("-", "", 0)
            if ex not in found:
                found.append(ex)
            if code.group(1):
                ex["status"] = code.group(1)
            section = "code"
        elif re.match(r"(?i)^(headers|заголовки)$", line):
            section = "headers"
        elif re.match(r"(?i)^(body|тело)$", line):
            section = "body"
        elif re.match(r"(?i)^(cookies|query params|form params|path params|multiparts)$", line):
            section = "skip"
        elif section == "code" and re.fullmatch(r"[1-5]\d\d", line) and ex is not None:
            ex["status"] = line
        elif section == "headers" and ex is not None:
            add_header(ex, line)
        elif section == "body" and ex is not None:
            ex["response" if ex["status"] else "body"] += line + "\n"
    for e in found:
        e["body"], e["response"] = e["body"].strip(), e["response"].strip()
    return found


def path_of(url):
    """https://host:8080/v1/x?y=1 -> /v1/x; /v1/x -> /v1/x."""
    m = re.match(r"^(?:[a-z]+://[^/]+)?(/[^?#\s]*)", url or "", re.I)
    return m.group(1).rstrip("/") if m else ""


def host_of(url):
    m = re.match(r"^([a-z]+://[^/]+)", url or "", re.I)
    return m.group(1) if m else ""


def looks_like_requests(text, limit=10):
    """Строки, похожие на запросы или SQL, которые разбор не взял: для подсказки человеку."""
    hits = []
    for number, line in enumerate(text.split("\n"), 1):
        if re.search(r"/v\d+/|https?://|\b(" + METHODS + r")\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b", line, re.I):
            hits.append("строка %d: %s" % (number, mask(clean(line).strip())[:160]))
            if len(hits) >= limit:
                break
    return hits
