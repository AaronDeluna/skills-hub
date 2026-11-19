#!/usr/bin/env python3
"""Карта миграции: размер проекта, ворота этапов и служебные правки карты (скилл migration-map).
Запуск из корня проекта:

  python3 <каталог скилла>/scripts/map.py size            - размер проекта: готовая строка паспорта
  python3 <каталог скилла>/scripts/map.py check <1-5>     - ворота этапа: чего не хватает, чтобы его отметить
  python3 <каталог скилла>/scripts/map.py done <1-5>      - check, затем отметить этап `[x]`, map_stage, updated
  python3 <каталог скилла>/scripts/map.py tech-done <tech> - дописать метку в «Этап 3 сделан для технологий»
  python3 <каталог скилла>/scripts/map.py log <текст>     - дописать строку в журнал сессий (раздел 7)
  python3 <каталог скилла>/scripts/map.py names           - имена фрейма в строках G есть в конспекте

Этап карта отмечает только через done: модель этап сама не отмечает. Модель
не правит карту ради отметок и журнала - это делают команды выше.
Python 3.8+, только стандартная библиотека.
Код выхода: 0 - выполнено / ворота пройдены; 1 - есть что доделать (печатает список); 2 - неверные аргументы.
"""
import datetime
import re
import subprocess
import sys
from pathlib import Path

MIGRATION = Path(".gigacode") / "data" / "migration"
MAP = MIGRATION / "MIGRATION-MAP.md"
SKILL_DIR = Path(__file__).resolve().parent.parent
CODE_EXT = (".java", ".kt", ".groovy")
SKIP_DIRS = {".git", ".gigacode", ".qwen", ".claude", ".idea", "target", "build", "out", "node_modules", ".gradle", ".mvn"}
LIMIT_FILES, LIMIT_LINES, LIMIT_MODULES = 150, 10000, 5
STOP_AFTER = (2, 3, 4)
STAGE_NAMES = {1: "обзор фрейма", 2: "паспорт и инвентаризация", 3: "документация и матрица",
               4: "архитектура", 5: "юниты и карточки"}


def read(path):
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else ""
    except (OSError, UnicodeDecodeError):
        return ""


def cells(line):
    t = line.strip()
    if not t.startswith("|"):
        return []
    raw = t[1:].split("|")
    while raw and raw[-1] == "":
        raw.pop()
    return [c.strip() for c in raw]


def section(text, number):
    """Текст раздела «## <number>. ...» до следующего «## »."""
    m = re.search(r"(?m)^## " + str(number) + r"\.[^\n]*\n", text)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"(?m)^## ", rest)
    return rest[:nxt.start()] if nxt else rest


def subsection(text, title):
    m = re.search(r"(?m)^### " + re.escape(title) + r"[^\n]*\n", text)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"(?m)^##+ ", rest)
    return rest[:nxt.start()] if nxt else rest


def passport(text, key):
    m = re.search(r"(?m)^- " + re.escape(key) + r"[^:\n]*:\s*(.*)$", section(text, 1))
    return m.group(1).strip() if m else None


def placeholder(value):
    return value is None or value == "" or "<" in value


# ---------- размер ----------

def size():
    files = lines = 0
    modules = set()
    root = Path(".")
    for path in root.rglob("*"):
        parts = set(path.parts)
        if parts & SKIP_DIRS:
            continue
        if path.is_file() and path.name in ("pom.xml", "build.gradle", "build.gradle.kts"):
            if (path.parent / "src").is_dir():
                modules.add(path.parent.as_posix())
        if path.is_file() and path.suffix in CODE_EXT and "src" in path.parts:
            files += 1
            try:
                with path.open(encoding="utf-8", errors="replace") as f:
                    lines += sum(1 for _ in f)
            except OSError:
                pass
    count = max(1, len(modules))
    big = files > LIMIT_FILES or lines > LIMIT_LINES or count > LIMIT_MODULES
    return big, files, lines, count


def size_line():
    big, files, lines, count = size()
    return big, "Размер: " + ("большой" if big else "обычный") + " (" + str(files) + " файлов, " + str(lines) \
        + " строк, " + str(count) + " модулей)"


def cmd_size():
    big, line = size_line()
    print(line)
    print("Строку выше впиши в паспорт (раздел 1 карты) как есть, своими словами не пересчитывай.")
    if big:
        print("Проект большой (больше " + str(LIMIT_FILES) + " файлов, или " + str(LIMIT_LINES) + " строк, или "
              + str(LIMIT_MODULES) + " модулей): после Этапов 2, 3 и 4 чат заканчивается - это скажет `map.py done`.")
    else:
        print("Проект обычный: этапы можно делать подряд в одном чате.")
    return 0


# ---------- проверка имён (строки G) ----------

CODE_WORD = re.compile(r"(?<![A-Za-z0-9_.])([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)")
NOT_NAMES = {"PVATF", "PVAT", "НЕТ", "REST", "API", "JSON", "SQL", "HTTP", "Kafka", "Allure", "JUnit", "Maven",
             "Gradle", "Java", "Spring", "BOM", "DTO", "TestOps", "Zephyr"}


NEGATIVE = re.compile(r"не найден|не нашл|не описан|нет в док|в документации нет|НЕТ В ДОКЕ", re.IGNORECASE)


def notes_text():
    """Конспект без строк о неудачных запросах: имя из «Чего не хватило» и «пусто» - не основание."""
    out = []
    folder = MIGRATION / "doc-notes"
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        for line in read(path).split("\n"):
            s = line.strip()
            if s.startswith("- Формулировки") or s.startswith("- Чего не хватило") or s.startswith("- «") \
                    or "- пусто" in s or "Ключевые слова:" in s or NEGATIVE.search(s):
                continue
            out.append(line)
    return "\n".join(out)


def frame_names(cell):
    names = []
    for m in CODE_WORD.finditer(cell):
        word = m.group(1)
        for part in word.split("."):
            if len(part) < 4 or part in NOT_NAMES or part.isupper() and len(part) < 6:
                continue
            camel = re.search(r"[a-z][A-Z]", part) or re.match(r"[A-Z][a-z]+[A-Z]", part)
            if camel or cell[m.end():m.end() + 1] == "(":
                names.append(part)
    return list(dict.fromkeys(names))


def check_names(text):
    problems = []
    notes = notes_text() + "\n" + read(MIGRATION / "ARCHITECTURE.md")  # новые классы проекта из плана - не имена фрейма
    for line in section(text, 2).split("\n"):
        row = cells(line)
        if len(row) < 6 or not re.fullmatch(r"G-[0-9]+", row[0]):
            continue
        target = row[4]
        if "уже PVATF" in target or target.startswith("НЕТ В ДОКЕ"):
            continue
        for name in frame_names(target):
            if name not in notes:
                problems.append(row[0] + ": `" + name + "` нет ни в конспекте (doc-notes/), ни в ARCHITECTURE.md - возьми имя из записи "
                                + (row[5] or "D-...") + " или напиши в ячейке `НЕТ В ДОКЕ`")
    return problems


def cmd_names():
    problems = check_names(read(MAP))
    for p in problems:
        print("- " + p)
    print("ИТОГ: находок " + str(len(problems)))
    return 1 if problems else 0


# ---------- ворота этапов ----------

def migrate_techs(text):
    techs = []
    for line in subsection(section(text, 1), "Технологии проекта").split("\n"):
        row = cells(line)
        if len(row) >= 5 and re.fullmatch(r"[0-9]+", row[0]) and row[4].startswith("migrate"):
            techs.append(row[1].strip("`"))
    return techs


def open_questions(text):
    """Вопросы раздела 6 без ответа: (Q-id, текст)."""
    result = []
    for block in re.split(r"(?m)^- (?=Q-[0-9]+)", section(text, 6))[1:]:
        qid = block.split(" ", 1)[0]
        if re.search(r"(?m)^\s*- ответ:\s*-\s*$", block):
            result.append((qid, block.split("\n", 1)[0]))
    return result


def gate(stage, text):
    p = []
    notes = MIGRATION / "doc-notes"
    if stage == 1:
        if not re.search(r"(?m)^#{2,3} D-common-[0-9]+", read(notes / "common.md")):
            p.append("в doc-notes/common.md нет записей D-common-<n> (Этап 1, п.2-3: агент pvatf-docs и notes.py merge)")
        if placeholder(passport(text, "Исходники фрейма")):
            p.append("в паспорте не заполнена строка «Исходники фрейма» (Этап 1, п.6; нет исходников - `-`)")
    elif stage == 2:
        big, line = size_line()
        written = passport(text, "Размер")
        if written is None or not written.startswith(line[len("Размер: "):].split(" ")[0]):
            p.append("строка паспорта «Размер» не совпадает со скриптом. Впиши как есть: " + line)
        modules = [re.split(r"\s+\(", cells(l)[0].strip("`"))[0] for l in subsection(section(text, 1), "Модули проекта").split("\n")
                   if len(cells(l)) >= 3 and not cells(l)[0].startswith(("Модуль", "-", "<"))]
        if not modules:
            p.append("в разделе 1 нет таблицы «Модули проекта» со строками")
        for m in modules:
            if not (MIGRATION / "inventory" / (m + ".md")).is_file():
                p.append("нет inventory/" + m + ".md - инвентаризацию модуля делает сабагент (Этап 2, п.2)")
        if not migrate_techs(text) and "keep" not in subsection(section(text, 1), "Технологии проекта"):
            p.append("в «Технологии проекта» нет ни одной строки с решением migrate / keep")
        if not (MIGRATION / "CONNECTIONS.md").is_file():
            p.append("нет CONNECTIONS.md (Этап 2)")
        markup = passport(text, "Разметка")
        if markup is None:
            p.append("в паспорте нет строки «Разметка» (Этап 2, шаг 1б)")
        elif markup.startswith("нужна"):
            for key in ("model", "system", "stage", "team"):
                m = re.search(r"\b" + key + r":\s*([^·]*)", markup)
                if not m or placeholder(m.group(1).strip()) or m.group(1).strip() == "":
                    p.append("«Разметка: нужна», но нет значения " + key + " - задай вопросы разметки (Этап 2, шаг 1б)")
            if "model: testops" in markup:
                for key in ("regress", "story"):
                    if not re.search(r"\b" + key + r":", markup):
                        p.append("model: testops, но в строке «Разметка» нет " + key + " (Этап 2, шаг 1б)")
        for qid, head in open_questions(text):
            if "разметка" in head:
                p.append(qid + " (разметка) без ответа - Этап 2 не отмечается до ответа")
    elif stage == 3:
        done_line = re.search(r"(?m)^Этап 3 сделан для технологий:\s*(.*)$", text)
        done = {t.strip(" `") for t in (done_line.group(1) if done_line else "").split(",")}
        sec2 = section(text, 2)
        for tech in migrate_techs(text):
            if tech not in done:
                p.append(tech + ": нет в строке «Этап 3 сделан для технологий» (map.py tech-done " + tech + ")")
            if tech != "common" and not re.search(r"(?m)^#{2,3} D-" + re.escape(tech) + r"-[0-9]+",
                                                  read(notes / (tech + ".md"))):
                p.append(tech + ": нет конспекта doc-notes/" + tech + ".md с записями")
            if "T-" + tech not in sec2:
                p.append(tech + ": в разделе 2 нет блока T-" + tech)
        if migrate_techs(text) and not re.search(r"(?m)^\| G-[0-9]+ ", sec2):
            p.append("в разделе 2 нет ни одной строки G")
        for line in sec2.split("\n"):
            row = cells(line)
            if len(row) >= 7 and re.fullmatch(r"G-[0-9]+", row[0]):
                for path in re.findall(r"[A-Za-z0-9_./-]+\.(?:java|kt|groovy|properties|xml|yml|yaml)", row[6]):
                    if not Path(path).is_file():
                        p.append(row[0] + ": файла " + path + " нет в проекте - укажи настоящий путь (find . -name ...)")
        p.extend(check_names(text))
    elif stage == 4:
        if not read(MIGRATION / "ARCHITECTURE.md"):
            p.append("нет ARCHITECTURE.md (Этап 4)")
        sec3 = section(text, 3)
        if not re.search(r"(?m)^\| A-[0-9]+ ", sec3) and not re.search(r"(?m)^-\s*$", sec3):
            p.append("в разделе 3 нет строк A-<n> (проблем нет - напиши `-`)")
    elif stage == 5:
        units = [cells(l)[0] for l in section(text, 4).split("\n")
                 if len(cells(l)) >= 8 and re.fullmatch(r"M-[0-9]+", cells(l)[0])]
        if not units:
            p.append("в разделе 4 нет юнитов")
        for uid in units:
            if not (MIGRATION / "units" / (uid + ".md")).is_file():
                p.append(uid + ": в разделе 4 юнит есть, карточки units/" + uid + ".md нет")
        if units:
            run = subprocess.run([sys.executable, str(SKILL_DIR / "scripts" / "card.py"), "all"],
                                 capture_output=True, text=True, encoding="utf-8")
            if run.returncode != 0:
                tail = [l for l in run.stdout.strip().split("\n") if l.startswith("ИТОГ")]
                p.append("card.py all: " + (tail[0] if tail else "ошибка") + " - исправь карточки (card-subagents.md, 5.5)")
        cover = re.search(r"(?m)^Проверка покрытия[^:]*:\s*(.*)$", text)
        if not cover or placeholder(cover.group(1)):
            p.append("в разделе 0 не заполнена «Проверка покрытия» (Этап 5)")
        for qid, head in open_questions(text):
            if "показательн" not in head:
                p.append(qid + " без ответа - юниты не создаются, пока есть вопросы (Этап 5, «Ворота»)")
    return p


def cmd_check(stage, quiet=False):
    text = read(MAP)
    if not text:
        print("ОШИБКА: нет " + MAP.as_posix() + " - запускай из корня проекта")
        return 1
    problems = gate(stage, text)
    if problems:
        print("Этап " + str(stage) + " (" + STAGE_NAMES[stage] + ") не готов, отмечать нельзя. Доделай:")
        for x in problems:
            print("- " + x)
        return 1
    if not quiet:
        print("ОК: ворота Этапа " + str(stage) + " пройдены")
    return 0


def cmd_done(stage):
    if cmd_check(stage, quiet=True) != 0:
        return 1
    text = read(MAP)
    mark = re.compile(r"(?m)^- \[ \] Этап " + str(stage) + r" ")
    if not mark.search(text) and not re.search(r"(?m)^- \[x\] Этап " + str(stage) + r" ", text):
        print("ОШИБКА: в разделе 0 нет строки «- [ ] Этап " + str(stage) + " ...»")
        return 1
    text = mark.sub("- [x] Этап " + str(stage) + " ", text, count=1)
    text = re.sub(r"(?m)^map_stage:.*$", "map_stage: " + str(stage + 1), text, count=1)
    text = re.sub(r"(?m)^updated:.*$", "updated: " + datetime.date.today().isoformat(), text, count=1)
    MAP.write_text(text, encoding="utf-8")
    print("ОК: Этап " + str(stage) + " отмечен [x], map_stage: " + str(stage + 1))
    big = (passport(text, "Размер") or "").startswith("большой")
    if big and stage in STOP_AFTER:
        print("СТОП: проект большой. Скажи пользователю: «Этап " + str(stage) + " готов. Откройте новый чат и "
              "напишите: `/orchestrator Продолжи миграцию`». Этап " + str(stage + 1) + " в этом чате не начинай.")
    else:
        print("Дальше: Этап " + str(stage + 1) + ".")
    return 0


def cmd_tech_done(tech):
    text = read(MAP)
    m = re.search(r"(?m)^(Этап 3 сделан для технологий:\s*)(.*)$", text)
    if not m:
        print("ОШИБКА: в разделе 0 нет строки «Этап 3 сделан для технологий:»")
        return 1
    done = [t.strip(" `") for t in m.group(2).split(",") if t.strip(" `-")]
    if tech not in done:
        done.append(tech)
    text = text[:m.start(2)] + ", ".join(done) + text[m.end(2):]
    MAP.write_text(text, encoding="utf-8")
    print("ОК: Этап 3 сделан для технологий: " + ", ".join(done))
    return 0


def cmd_log(message):
    text = read(MAP)
    m = re.search(r"(?m)^## 7\.[^\n]*\n", text)
    if not m:
        print("ОШИБКА: в карте нет раздела «## 7. Журнал сессий»")
        return 1
    nxt = re.search(r"(?m)^## ", text[m.end():])
    end = m.end() + nxt.start() if nxt else len(text)
    body = text[m.end():end].rstrip("\n")
    line = "- " + datetime.date.today().isoformat() + " · migration-map · " + " ".join(message.split())
    text = text[:m.end()] + body + "\n" + line + "\n\n" + text[end:]
    MAP.write_text(text, encoding="utf-8")
    print("ОК: в журнал записано: " + line)
    return 0


def main(args):
    usage = ("Использование: map.py size | check <1-5> | done <1-5> | tech-done <tech> | log <текст> | names")
    if not args:
        print(usage)
        return 2
    cmd = args[0]
    if cmd == "size":
        return cmd_size()
    if cmd == "names":
        return cmd_names()
    if cmd in ("check", "done"):
        if len(args) != 2 or args[1] not in ("1", "2", "3", "4", "5"):
            print(usage)
            return 2
        return cmd_check(int(args[1])) if cmd == "check" else cmd_done(int(args[1]))
    if cmd == "tech-done" and len(args) == 2:
        return cmd_tech_done(args[1])
    if cmd == "log" and len(args) >= 2:
        return cmd_log(" ".join(args[1:]))
    print(usage)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
