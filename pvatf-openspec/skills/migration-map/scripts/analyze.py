#!/usr/bin/env python3
"""Разбор технологии для карточки юнита tech (Этап 5, card-subagents.md, 5.1). Запуск из корня проекта:

  python3 <каталог скилла>/scripts/analyze.py <tech> --old "<regex>" --core "<Класс|Класс>" \\
      [--frame "<regex>"] [--steps "<Класс|Класс>"] [--other "db=<regex>;kafka=<regex>"] <каталог>...

  --old    старая библиотека технологии: пакеты из строк G (io.restassured|org.apache.kafka)
  --core   классы старого ядра технологии: имена из строк L (BaseClient|AuthClient|PaymentDao)
  --frame  обращения к сервису фрейма в обход шагов (restService|dataBaseClient); нет - не передавай
  --steps  классы шагов из архитектурного плана: потребителями не считаются
  --other  импорты других технологий из паспорта: метка=regex через «;»

Пишет .gigacode/data/migration/inventory/analysis-<tech>.md по шаблону 5.1 и печатает одну строку
итога. Файлы читает сам, по строкам: модели не нужно открывать файлы проекта для разбора.
Потребитель - файл, который сам обращается к старой библиотеке, к классу старого ядра или к фрейму
напрямую. Уровни внутри этого набора: 0 - класс старого ядра; 1 - потребитель; 2 - потребитель,
который вызывает потребителя уровня 1; и так далее. Виды проверок и действия определяются по шаблонам строк.
Python 3.8+, только стандартная библиотека. Код выхода: 0 - записано, 1 - ничего не найдено, 2 - неверные аргументы.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pvatf_paths as pp  # noqa: E402 - копия shared/scripts
OUT_DIR = pp.migration_dir() / "inventory"
CODE_EXT = (".java", ".kt")
SKIP = {".git", ".gigacode", "openspec", "target", "build", "out", ".idea", ".gradle"}
ASSERT = re.compile(r"Assertions\.|\bassert(Equals|True|False|NotNull|Null|That|All|Throws)\(|SoftAssertions|\.should\(|"
                    r"\bassertThat\(")
PARSE = re.compile(r"\.as\([A-Z][A-Za-z0-9_]*\.class\)|readValue\(|fromJson\(|JsonNode|\.extract\(\)")
DTO = re.compile(r"\.as\(([A-Z][A-Za-z0-9_]*)\.class\)|readValue\([^;]*?,\s*([A-Z][A-Za-z0-9_]*)\.class\)|"
                 r"fromJson\([^;]*?,\s*([A-Z][A-Za-z0-9_]*)\.class\)")
TEST = re.compile(r"@(Test|ParameterizedTest|RepeatedTest|TestFactory|TestTemplate)\b")
HTTP = re.compile(r"\.(get|post|put|delete|patch)\s*\(\s*([^,)\s]+)", re.IGNORECASE)
SQL = re.compile(r"\b(SELECT\b[^\"]*?\bFROM|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+([A-Za-z_][A-Za-z0-9_.]*)", re.IGNORECASE)
TOPIC = re.compile(r"(?:send|subscribe|poll|topic|readRecords|records)\w*\s*\(\s*\"([A-Za-z0-9_.-]+)\"", re.IGNORECASE)
KINDS = [
    ("код ответа", re.compile(r"statusCode|getStatusCode|StatusCode|\.status\(\)|HttpStatus|haveStatus")),
    ("null", re.compile(r"isNull|isNotNull|assertNull|assertNotNull|nullValue|notNullValue")),
    ("размер массива", re.compile(r"hasSize|\.size\(\)|isEmpty|isNotEmpty|hasSizeGreaterThan|\.length\b")),
    ("boolean", re.compile(r"isTrue|isFalse|assertTrue|assertFalse")),
    ("дата", re.compile(r"LocalDate|LocalDateTime|Instant|OffsetDateTime|ZonedDateTime|\bDate\b")),
    ("поле-число", re.compile(r"BigDecimal|isGreaterThan|isLessThan|isEqualTo\(\s*-?[0-9]|assertEquals\(\s*-?[0-9]|isPositive|isZero")),
    ("поле-строка", re.compile(r"isEqualTo\(\s*\"|equalTo\(\s*\"|assertEquals\(\s*\"|contains\(\s*\"|startsWith\(\s*\"")),
    ("равенство с переменной", re.compile(r"isEqualTo\(|assertEquals\(|equalTo\(|\bis\(")),
]


def parse_args(argv):
    opts, dirs = {"old": "", "core": "", "frame": "", "steps": "", "other": ""}, []
    i = 1
    while i < len(argv):
        if argv[i].startswith("--") and argv[i][2:] in opts and i + 1 < len(argv):
            opts[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            dirs.append(argv[i])
            i += 1
    return argv[0] if argv else "", opts, dirs


def files_in(dirs):
    out = []
    for d in dirs:
        root = Path(d)
        if root.is_file() and root.suffix in CODE_EXT:
            out.append(root)
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix in CODE_EXT and path.is_file() and not (set(path.parts) & SKIP):
                out.append(path)
    return out


def names(value):
    return [n.strip() for n in value.split("|") if n.strip()]


def word_re(items):
    return re.compile(r"\b(" + "|".join(re.escape(n) for n in items) + r")\b") if items else None


def check_kind(line, tech):
    for kind, pattern in KINDS:
        if pattern.search(line):
            return kind
    if tech == "db" and re.search(r"row|Row|ResultSet|Map<|\.get\(\"", line):
        return "ячейка БД"
    if tech == "kafka" and re.search(r"record|Record|message|Message|event|Event", line):
        return "запись Kafka"
    return "другое"


def actions(text, core, tech):
    found = []
    for m in HTTP.finditer(text) if tech == "rest" else []:
        arg = m.group(2).strip()
        if arg.startswith("\"/") or re.match(r"[A-Z][A-Za-z0-9_]*\.[A-Z][A-Z0-9_]+$", arg):
            found.append(m.group(1).upper() + " " + arg.strip("\""))
    for m in SQL.finditer(text):
        found.append(m.group(1).split()[0].upper() + " " + m.group(2))
    for m in TOPIC.finditer(text):
        found.append("topic " + m.group(1))
    for cls in core:
        variables = set(re.findall(r"\b" + re.escape(cls) + r"\s+([a-z][A-Za-z0-9_]*)\s*[=;,)]", text))
        variables |= set(re.findall(r"\b([a-z][A-Za-z0-9_]*)\s*=\s*new\s+" + re.escape(cls) + r"\b", text))
        for m in re.finditer(r"\b" + re.escape(cls) + r"\.([a-z][A-Za-z0-9_]*)\(", text):
            found.append(cls + "." + m.group(1))
        for var in variables:
            for m in re.finditer(r"\b" + re.escape(var) + r"\.([a-z][A-Za-z0-9_]*)\(", text):
                found.append(cls + "." + m.group(1))
    return list(dict.fromkeys(found))


def main(argv):
    tech, opts, dirs = parse_args(argv)
    if not tech or not opts["old"] or not dirs:
        print(__doc__.split("\n\n")[1])
        return 2
    old = re.compile(opts["old"])
    core = names(opts["core"])
    steps = set(names(opts["steps"]))
    frame = re.compile(opts["frame"]) if opts["frame"] else None
    other = []
    for part in opts["other"].split(";"):
        if "=" in part:
            label, regex = part.split("=", 1)
            other.append((label.strip(), re.compile(regex.strip())))
    core_re = word_re(core)
    texts, failed = {}, []
    for path in files_in(dirs):
        try:
            texts[path] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            failed.append(path.as_posix() + ": " + e.__class__.__name__)
    stem = {p: p.stem for p in texts}
    core_files = {p for p in texts if stem[p] in core}
    level = {p: 0 for p in core_files}
    direct_old = {p for p, t in texts.items() if old.search(t)}
    direct_frame = {p for p, t in texts.items() if frame and frame.search(t)}
    # потребитель - файл, который САМ обращается к старой библиотеке, к старому ядру или к фрейму напрямую
    candidates = {p for p in texts if p not in core_files and stem[p] not in steps
                  and (p in direct_old or p in direct_frame or (core_re and core_re.search(texts[p])))}
    for p in candidates:
        level[p] = 1
    by_name = {stem[p]: p for p in candidates}
    cons_re = word_re(list(by_name))
    refs = {p: {by_name[m.group(1)] for m in cons_re.finditer(texts[p]) if m.group(1) != stem[p]} if cons_re else set()
            for p in candidates}
    memo = {}

    def depth(p, stack):
        """1 + уровень самого высокого потребителя, которого вызывает файл; взаимные вызовы не поднимают уровень."""
        if p in memo:
            return memo[p]
        stack = stack | {p}
        below = [depth(r, stack) for r in refs[p] if r not in stack]
        memo[p] = 1 + max(below) if below else 1
        return memo[p]

    for p in candidates:
        level[p] = depth(p, set())
    consumers = sorted((p for p in level if p not in core_files), key=lambda p: (level[p], p.as_posix()))
    if not consumers and not core_files:
        print("НИЧЕГО: по --old и --core не найдено ни одного файла - проверь регулярные выражения (строки G и L)")
        return 1
    kinds_all = {}
    rows = []
    for p in consumers:
        t = texts[p]
        lines = t.split("\n")
        assert_lines = [(i + 1, l) for i, l in enumerate(lines) if ASSERT.search(l) and not l.lstrip().startswith("import ")]
        kinds = {}
        for no, l in assert_lines:
            k = check_kind(l, tech)
            kinds[k] = kinds.get(k, 0) + 1
            kinds_all.setdefault(k, [0, p.as_posix() + ":" + str(no)])[0] += 1
        dto = sorted({g for m in DTO.finditer(t) for g in m.groups() if g})
        how = []
        if p in direct_old:
            how.append("старая библиотека")
        used_core = [c for c in core if re.search(r"\b" + re.escape(c) + r"\b", t)]
        if used_core:
            how.append("старое ядро " + ", ".join("`" + c + "`" for c in used_core[:4]))
        if p in direct_frame:
            how.append("фрейм напрямую")
        if not how:
            how.append("через уровень " + str(level[p] - 1))
        acts = actions(t, core, tech)
        others = [label for label, rx in other if rx.search(t) and label != tech]
        rows.append("| " + " | ".join([
            p.as_posix(), str(len(lines)), str(level[p]), "да" if TEST.search(t) else "нет", " / ".join(how),
            ", ".join(acts[:8]) + (" и ещё " + str(len(acts) - 8) if len(acts) > 8 else "") if acts else "-",
            str(len(assert_lines)), str(len(PARSE.findall(t))),
            ", ".join(k + " " + str(n) for k, n in sorted(kinds.items(), key=lambda x: -x[1])) or "-",
            ", ".join(dto) or "-", ", ".join(others) or "-"]) + " |")
    core_rows = []
    for p in sorted(core_files, key=lambda x: x.as_posix()):
        callers = sum(1 for q, t in texts.items() if q != p and re.search(r"\b" + re.escape(stem[p]) + r"\b", t))
        methods = re.findall(r"(?:public|protected)\s+(?:static\s+)?(?:final\s+)?[A-Za-z0-9_<>,\[\] ]+?\s+([a-z][A-Za-z0-9_]*)\s*\(", texts[p])
        core_rows.append("| " + " | ".join([stem[p], p.as_posix(), str(len(texts[p].split("\n"))), str(callers),
                                            "методы: " + (", ".join(list(dict.fromkeys(methods))[:8]) or "-")]) + " |")
    missing_core = [c for c in core if c not in {stem[p] for p in core_files}]
    dirs_s = " ".join(dirs)
    pattern = "|".join(filter(None, [opts["old"], "|".join(core)]))
    out = ["# Разбор технологии " + tech, "",
           "Собрано скриптом analyze.py. Поля «Действия» и «Виды проверок» - по шаблонам строк;",
           "уровни - по обращениям к классам старого ядра и потребителям нижнего уровня.", "",
           "## Команды поиска",
           "- старое: `grep -rlE \"" + pattern + "\" --include=*.java --include=*.kt " + dirs_s + "` -> "
           + str(len([p for p in consumers if p in direct_old or (core_re and core_re.search(texts[p]))]) + len(core_files)) + " файлов",
           "- фрейм напрямую: " + ("`grep -rlE \"" + opts["frame"] + "\" --include=*.java --include=*.kt " + dirs_s
                                   + "` -> " + str(len(direct_frame)) + " файлов" if frame else "-"), "",
           "## Потребители",
           "| Файл | Строк | Уровень | Тест | Как обращается | Действия | Ассертов | Разбор в объект | Виды проверок | DTO ответа | Другие технологии |",
           "|------|-------|---------|------|----------------|----------|----------|-----------------|---------------|------------|-------------------|"]
    out += rows or ["| - | - | - | - | - | - | - | - | - | - | - |"]
    out += ["", "## Классы старого ядра", "| Класс | Файл | Строк | Вызывают файлов | Что делает (1 строка) |",
            "|-------|------|-------|-----------------|-----------------------|"]
    out += core_rows or ["| - | - | - | - | - |"]
    out += ["", "## Виды проверок технологии (сводка)", "| Вид | Мест | Пример: файл:строка |", "|-----|------|---------------------|"]
    out += ["| " + k + " | " + str(v[0]) + " | " + v[1] + " |" for k, v in sorted(kinds_all.items(), key=lambda x: -x[1][0])] \
        or ["| - | 0 | - |"]
    out += ["", "## Не удалось"]
    out += ["- " + f for f in failed] + ["- класс старого ядра " + c + " - файла " + c + ".java/.kt не найдено" for c in missing_core]
    if not failed and not missing_core:
        out.append("- нет")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / ("analysis-" + tech + ".md")
    target.write_text("\n".join(out) + "\n", encoding="utf-8")
    tests = sum(1 for p in consumers if TEST.search(texts[p]))
    print("ОК: " + target.as_posix() + " · потребителей " + str(len(consumers)) + " (тестов " + str(tests)
          + ", уровней до " + str(max([level[p] for p in consumers] or [0])) + ") · старое ядро " + str(len(core_files))
          + " · ассертов " + str(sum(v[0] for v in kinds_all.values())) + " · не удалось: " + str(len(failed) + len(missing_core)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
