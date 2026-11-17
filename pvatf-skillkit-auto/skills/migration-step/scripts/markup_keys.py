#!/usr/bin/env python3
"""Ключи тест-кейсов (<КОД>-T<цифры>) в тест-методах - для разметки (markup-rules.md, разделы 2а и 6).

python3 markup_keys.py missing <каталог тестов>...  - ключ есть, @TmsLink нет
python3 markup_keys.py dup <каталог тестов>...      - один ключ у разных тест-методов
python3 markup_keys.py count <каталог тестов>...    - сколько тест-методов и сколько с @TmsLink
python3 markup_keys.py classes [--need stage,layer,system,team,regress,story] <каталог тестов>...
    - каждый тест-класс и его разметка: своя или от базового класса из проекта; НЕТ - нужной аннотации нет нигде

Учитываются только тест-методы: с @Test, @ParameterizedTest, @RepeatedTest, @TestFactory или @TestTemplate.
Ключи метода - из значений всех его аннотаций: @DisplayName, name у @ParameterizedTest, @Zephyr("...") и любых других
(один и тот же ключ в нескольких аннотациях - один ключ). Не считаются: @TmsLink (это цель), источники данных
(@...Source), @Disabled..., ссылки Allure на задачи (@Link, @Issue, @Story). Ключ в комментарии не считается.
Для dup считаются все ключи метода: из @DisplayName, из name и из @TmsLink. @DisplayName над классом не считается.
Файл разбирается по символам: комментарии и строки не путаются с кодом, аннотации могут быть многострочными,
с пробелами и переводами строки перед "(", полным именем и на одной строке с объявлением.
Последняя строка вывода - всегда "итого: N". Строки до неё - находки; "итого: 0" - находок нет.
Python 3.8+, только стандартная библиотека. Код выхода: 0 - выполнено, 2 - неверные аргументы.
"""
import os
import re
import sys
from pathlib import Path

KEY = re.compile(r"[A-Z][A-Z0-9]*-T[0-9]+")
NAME_ARG = re.compile(r"\bname\s*=", re.ASCII)
NAMED = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*=")
SKIP = re.compile(r".*Sources?|Disabled.*|Link|Links|Issue|Issues|Story|Stories|SuppressWarnings")
VALUE_ARG = re.compile(r"^\(\s*value\s*=")
TESTS = {"Test", "ParameterizedTest", "RepeatedTest", "TestFactory", "TestTemplate"}
STAGE = re.compile(r"TestStage|IsolatedTest|DevStandTest|StStandTest|IftStandTest|PsiStandTest|PromStandTest")
LAYER = re.compile(r"TestLayer|ApiTest|DbTest|MqTest|UiTest|UnitTest|CdcConsumerTest|CdcProviderTest|PerformanceTest")
EXTENDS = re.compile(r"\bextends\s+([A-Za-z_][A-Za-z0-9_.]*)", re.ASCII)
KOTLIN_SUPER = re.compile(r":\s*([A-Za-z_][A-Za-z0-9_.]*)")
# ключ набора -> название в выводе; порядок - как в выводе
SET = {"stage": "контур", "layer": "слой", "system": "КЭ", "team": "команда", "regress": "регресс", "story": "задача"}
CLASS_WORDS = {"class", "interface", "object", "enum"}
HEADER_STOP = {"class", "interface", "object", "fun", "val", "var", "enum"}

DECLS = []  # (file, line, name, parent, marks) - классы верхнего уровня


def ident_part(c):
    return c.isalnum() or c in "_$"


def ident_start(c):
    return c.isalpha() or c in "_$"


def skip_space(s, i):
    while i < len(s) and s[i].isspace():
        i += 1
    return i


def matching(code, start):
    """Индекс после ")", парной к "(" в позиции start. Строки и комментарии уже заменены пробелами."""
    depth = 0
    for i in range(start, len(code)):
        if code[i] == "(":
            depth += 1
        elif code[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(code)


def mask(t, strings):
    """Та же длина и те же переводы строк; комментарии - пробелы, а при strings=True - и строки, текстовые блоки, символы."""
    b = list(t)
    n = len(t)

    def blank(start, stop):
        for k in range(start, stop):
            if t[k] != "\n":
                b[k] = " "

    i = 0
    while i < n:
        if t.startswith("//", i):
            while i < n and t[i] != "\n":
                b[i] = " "
                i += 1
        elif t.startswith("/*", i):
            end = t.find("*/", i + 2)
            end = n if end < 0 else end + 2
            blank(i, end)
            i = end
        elif t.startswith('"""', i):
            end = t.find('"""', i + 3)
            end = n if end < 0 else end + 3
            if strings:
                blank(i, end)
            i = end
        elif t[i] in "\"'":
            q = t[i]
            j = i + 1
            while j < n and t[j] != q and t[j] != "\n":
                j += 2 if t[j] == "\\" else 1
            end = min(n, j + 1)
            if strings:
                blank(i, end)
            i = end
        else:
            i += 1
    return "".join(b)


def text_block(raw):
    """Текстовый блок Java: без первой строки после открывающих кавычек и без общего отступа."""
    nl = raw.find("\n")
    body = raw[nl + 1:] if nl >= 0 and not raw[:nl].strip() else raw
    lines = body.split("\n")
    indent = sys.maxsize
    for idx, line in enumerate(lines):
        if line.strip() or idx == len(lines) - 1:
            k = 0
            while k < len(line) and line[k].isspace():
                k += 1
            indent = min(indent, k)
    return "\n".join(line[indent:] if len(line) >= indent else line.strip() for line in lines)


def evaluate(expr):
    """Значение константного выражения из строковых литералов и "+"; None - выражение не разобрать."""
    out = []
    i, n, any_part = 0, len(expr), False
    while i < n:
        c = expr[i]
        if c.isspace() or c == "+":
            i += 1
        elif expr.startswith('"""', i):
            end = expr.find('"""', i + 3)
            if end < 0:
                return None
            out.append(text_block(expr[i + 3:end]))
            i = end + 3
            any_part = True
        elif c == '"':
            j = i + 1
            while j < n and expr[j] != '"':
                if expr[j] == "\\" and j + 1 < n:
                    j += 1
                    e = expr[j]
                    out.append("\n" if e == "n" else "\t" if e == "t" else e)
                else:
                    out.append(expr[j])
                j += 1
            if j >= n:
                return None
            i = j + 1
            any_part = True
        else:
            return None
    return "".join(out) if any_part else None


class Method:
    def __init__(self, place, name, keys, all_keys, has_link, test, unknown, sources):
        self.place, self.name, self.keys, self.all = place, name, keys, all_keys
        self.has_link, self.test, self.unknown, self.sources = has_link, test, unknown, sources


class Pending:
    def __init__(self):
        self.marks = {}
        self.has_link = False
        self.test = False
        self.unknown = False
        self.keys = []
        self.sources = []
        self.link_keys = []

    @staticmethod
    def _add(target, value):
        if value not in target:
            target.append(value)

    def add(self, name, args, code):
        """args - текст аргументов без комментариев, code - тот же текст, где строки заменены пробелами."""
        shown = "@" + name + ("" if not args else re.sub(r"\s+", " ", args))
        if STAGE.fullmatch(name):
            self.marks.setdefault("stage", shown)
        elif LAYER.fullmatch(name):
            self.marks.setdefault("layer", shown)
        elif name == "System" and args:
            self.marks.setdefault("system", shown)
        elif name == "Team":
            self.marks.setdefault("team", shown)
        elif name in ("Regress", "CriticalRegress"):
            self.marks.setdefault("regress", shown)
        elif name in ("Story", "Issue"):
            self.marks.setdefault("story", shown)
        if name == "TmsLink":
            self.has_link = True
            if len(args) > 1:
                v = VALUE_ARG.search(code)
                text = evaluate(args[v.end() if v else 1:len(args) - 1])
                if text is None:
                    self.unknown = True
                else:
                    for key in KEY.findall(text):
                        self._add(self.link_keys, key)
        elif name == "TmsLinks":
            self.has_link = True
            for key in KEY.findall(args):
                self._add(self.link_keys, key)
        elif name == "DisplayName":
            self.value("@DisplayName", args, code)
        elif name == "ParameterizedTest":
            m = NAME_ARG.search(code)
            if m:
                end, depth = m.end(), 0
                while end < len(code) - 1:
                    c = code[end]
                    if c in "({[":
                        depth += 1
                    elif c in ")}]":
                        depth -= 1
                    elif c == "," and depth == 0:
                        break
                    end += 1
                self.add_value("name у @ParameterizedTest", args[m.end():end])
        elif not SKIP.fullmatch(name) and len(args) > 1:
            self.other("@" + name, args[1:len(args) - 1], code[1:len(code) - 1])
        if name in TESTS:
            self.test = True

    def declare(self, place, method, result):
        all_keys = list(self.keys)
        for key in self.link_keys:
            self._add(all_keys, key)
        if all_keys or self.test or self.unknown:
            result.append(Method(place, method, self.keys, all_keys, self.has_link, self.test, self.unknown, self.sources))

    def value(self, source, args, code):
        """Значение единственного аргумента (или value = ...) аннотации."""
        if len(args) < 2:
            return
        v = VALUE_ARG.search(code)
        self.add_value(source, args[v.end() if v else 1:len(args) - 1])

    def other(self, source, args, code):
        """Любая другая аннотация: каждый аргумент (и элемент массива) со строкой разбирается отдельно."""
        start, depth = 0, 0
        for i in range(len(code) + 1):
            c = code[i] if i < len(code) else ","
            if c in "({[":
                depth += 1
            elif c in ")}]":
                depth -= 1
            elif c == "," and depth == 0:
                part, part_code = args[start:i], code[start:i]
                named = NAMED.search(part_code)
                if named:
                    part, part_code = part[named.end():], part_code[named.end():]
                trimmed = part_code.strip()
                at, paren = part_code.find("@"), part_code.find("(")
                if trimmed.startswith("@") and paren > at:
                    inner = part_code[at + 1:paren].strip()
                    inner = inner[inner.rfind(".") + 1:]
                    close = part_code.rfind(")")
                    if not SKIP.fullmatch(inner) and not inner.startswith("TmsLink") and close > paren:
                        self.other("@" + inner, part[paren + 1:close], part_code[paren + 1:close])
                elif trimmed.startswith("{") or trimmed.startswith("[") or trimmed.startswith("arrayOf("):
                    opener = "(" if trimmed[0] == "a" else trimmed[0]
                    open_at = part_code.find(opener)
                    close = max(part_code.rfind("}"), part_code.rfind("]"), part_code.rfind(")"))
                    if open_at >= 0 and close > open_at:
                        self.other(source, part[open_at + 1:close], part_code[open_at + 1:close])
                elif '"' in part:
                    text = evaluate(part)
                    if text is not None:
                        self.add_keys(source, text)
                    elif KEY.search(part):
                        self.unknown = True
                start = i + 1

    def add_value(self, source, expr):
        """Ключи из значения выражения. Выражение не из строк и "+" (константа, вызов) - unknown: проверить вручную."""
        text = evaluate(expr)
        if text is None:
            self.unknown = True
            return
        self.add_keys(source, text)

    def add_keys(self, source, text):
        for key in KEY.findall(text):
            self._add(self.keys, key)
            self._add(self.sources, source)


def declare_class(path, text, code, after_word, pending):
    """Класс верхнего уровня: имя после ключевого слова, базовый класс из заголовка до "{"."""
    n = len(code)
    k = skip_space(code, after_word)
    s = k
    while k < n and ident_part(code[k]):
        k += 1
    if k == s:
        return
    name = code[s:k]
    header = []
    depth = 0
    q = k
    while q < n:
        c = code[q]
        if c in "(<":
            depth += 1
            q += 1
            continue
        if c in ")>":
            depth -= 1
            q += 1
            continue
        if depth > 0:
            q += 1
            continue
        if c in "{;}@=":
            break
        if ident_start(c) and not ident_part(code[q - 1]):
            e = q
            while e < n and ident_part(code[e]):
                e += 1
            if code[q:e] in HEADER_STOP:
                break
        header.append(c)
        q += 1
    h = "".join(header)
    m = EXTENDS.search(h)
    parent = m.group(1) if m else None
    if parent is None and str(path).endswith(".kt"):
        m = KOTLIN_SUPER.search(h)
        parent = m.group(1) if m else None
    if parent is not None:
        parent = parent[parent.rfind(".") + 1:]
    DECLS.append((str(path), text.count("\n", 0, s) + 1, name, parent, pending.marks))


def parse(path):
    """Разбор файла: аннотации копятся до объявления метода; класс, поле, блок или ";" их сбрасывают."""
    text = Path(path).read_text(encoding="utf-8")
    code = mask(text, True)
    no_comments = mask(text, False)
    result = []
    p = Pending()
    i, n, depth = 0, len(code), 0
    while i < n:
        c = code[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        if c == "@":
            j = start = i + 1
            while j < n and (ident_part(code[j]) or code[j] in ".:"):
                j += 1
            name = code[start:j]
            if ":" in name:
                name = name[name.rfind(":") + 1:]
            name = name[name.rfind(".") + 1:]
            k = skip_space(code, j)
            args_text = args_code = ""
            if k < n and code[k] == "(":
                end = matching(code, k)
                args_text, args_code = no_comments[k:end], code[k:end]
                j = end
            p.add(name, args_text, args_code)
            i = j
            continue
        if ident_start(c) and (i == 0 or not ident_part(code[i - 1])):
            j = i
            while j < n and ident_part(code[j]):
                j += 1
            word = code[i:j]
            if word in CLASS_WORDS:
                if depth == 0 and (i == 0 or code[i - 1] != "@"):
                    declare_class(path, text, code, j, p)
                p = Pending()
            elif word in ("void", "fun"):
                k = skip_space(code, j)
                s = k
                if k < n and code[k] == "`":
                    close = code.find("`", k + 1)
                    k = n if close < 0 else close + 1
                else:
                    while k < n and ident_part(code[k]):
                        k += 1
                if k > s:
                    p.declare(str(path) + ":" + str(text.count("\n", 0, s) + 1), code[s:k].replace("`", ""), result)
                    p = Pending()
                    j = k
            i = j
            continue
        if c in ";{}=":
            p = Pending()
        i += 1
    return result


def classes(methods, need):
    """Режим classes: строка на тест-класс, НЕТ - нужной аннотации нет ни над ним, ни над его предками из проекта."""
    by_name, main_of = {}, {}
    for d in DECLS:
        by_name.setdefault(d[2], d)
        main_of.setdefault(d[0], d)
    test_files = sorted({m.place[:m.place.rfind(":")] for m in methods if m.test})
    bad = 0
    for f in test_files:
        d = main_of.get(f)
        if d is None:
            continue
        chain, bases, cur, outside, seen = [d], [], d, None, {d[2]}
        while cur[3] is not None:
            up = by_name.get(cur[3])
            if up is None:
                outside = cur[3]
                break
            if up[2] in seen:
                break
            seen.add(up[2])
            chain.append(up)
            bases.append(up[2])
            cur = up
        line = d[0] + ":" + str(d[1]) + ": " + d[2] + " · база: "
        if not bases and outside is None:
            line += "нет"
        else:
            line += " <- ".join(bases + ([outside + " (не из проекта)"] if outside else []))
        missing = []
        for key, title in SET.items():
            value = None
            for c in chain:
                v = c[4].get(key)
                if v is not None:
                    value = v if c is d else v + " (в " + c[2] + ")"
                    break
            if value is None:
                if key in need:
                    value = "НЕТ"
                    missing.append(title)
                else:
                    value = "нет"
            line += " · " + title + ": " + value
        print(line)
        if missing:
            bad += 1
    print("тест-классов: " + str(len(test_files)) + ", с НЕТ: " + str(bad))
    return bad


def source_files(root):
    root = Path(root)
    found = []
    if root.is_file():
        found.append(root)
    for base, _dirs, names in os.walk(str(root)):
        for name in names:
            found.append(Path(base) / name)
    result = [p for p in found if (str(p).endswith(".java") or str(p).endswith(".kt"))
              and "/target/" not in str(p) and "/build/" not in str(p)]
    return sorted(result, key=str)


def main(args):
    usage = "использование: markup_keys.py missing|dup|count|classes [--need stage,layer,system,team,regress,story] <каталог тестов>..."
    if len(args) < 2 or args[0] not in ("missing", "dup", "count", "classes"):
        print(usage)
        return 2
    first = 1
    need = ["stage", "layer", "system", "team"]
    if args[0] == "classes" and args[1] == "--need":
        if len(args) < 4:
            print("использование: markup_keys.py classes --need stage,layer,system,team,regress,story <каталог тестов>...")
            return 2
        need = []
        for k in args[2].split(","):
            k = k.strip()
            if k and k not in SET:
                print("неизвестный ключ в --need: " + k + " (можно: " + ",".join(SET) + ")")
                return 2
            if k and k not in need:
                need.append(k)
        first = 3
    methods = []
    for root in args[first:]:
        for path in source_files(root):
            methods.extend(parse(path))
    found = 0
    if args[0] == "missing":
        for m in methods:
            if m.test and m.unknown:
                print(m.place + ": " + m.name + " - значение не разобрать, проверьте вручную")
                found += 1
            elif m.test and m.keys and not m.has_link:
                print(m.place + ": " + m.name + " - " + " ".join(m.keys) + " - нет @TmsLink (из " + ", ".join(m.sources) + ")")
                found += 1
    elif args[0] == "dup":
        by_key = {}
        for m in methods:
            if m.test:
                for key in m.all:
                    by_key.setdefault(key, []).append(m.place + ":" + m.name)
        for key in sorted(by_key):
            if len(by_key[key]) > 1:
                print(key + " - " + " ".join(by_key[key]))
                found += 1
        for m in methods:
            if m.test and m.unknown:
                print(m.place + ":" + m.name + " - значение не разобрать, проверьте вручную")
                found += 1
    elif args[0] == "classes":
        found = classes(methods, need)
    else:
        tests = sum(1 for m in methods if m.test)
        linked = sum(1 for m in methods if m.test and m.has_link)
        print("тест-методов: " + str(tests))
        print("с @TmsLink: " + str(linked))
        print("итого без @TmsLink: " + str(tests - linked))
        return 0
    print("итого: " + str(found))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
