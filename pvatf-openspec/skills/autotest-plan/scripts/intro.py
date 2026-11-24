#!/usr/bin/env python3
"""Знакомство с технологией до плана (скилл autotest-plan): обзор документации и образцы из проекта-примера.

Модель не обучалась на фрейме и не знает его слов. Поэтому до разделов 11-14 плана по каждой технологии
ТК делается ровно одно знакомство на проект:
  1) обзорный вопрос в документацию (агент pvatf-docs) - запись конспекта «Обзор технологии ...»; из неё
     следующие вопросы строятся словами фрейма, а не словами модели;
  2) сбор документации под план (агент pvatf-docs): скрипт выписывает из плана (разделы 2, 9, 10), что
     нужно сделать на фрейме, простыми словами («отправить HTTP-запрос POST и получить ответ»); агент
     переводит каждую потребность в запросы словами фрейма из обзора и пишет запись конспекта. Генератор
     потом только читает конспект;
  3) образцы из проекта-примера platform-v-at-maven-draft (агент pvatf-examples): тест-класс, класс шагов,
     проверка результата - как на фрейме раскладывают код.
Режим - по каждой технологии отдельно, по колонке «Классы проекта» раздела 3 плана:
  - классов нет (пишем с нуля, миграция, технология в проекте новая) - обзор, сбор и образцы драфта;
  - классы есть (на фрейме уже пишут в своей архитектуре) - обзор и сбор документации, образцы драфта
    не нужны: раскладка кода - как в классах проекта.
Результат общий для проекта: конспект openspec/pvatf/doc-notes/<метка>.md и openspec/pvatf/examples/<метка>.md.

Запуск из корня проекта:
  python3 <скилл>/scripts/intro.py draft [--again | --path <каталог>]  - найти проект-пример на диске
  python3 <скилл>/scripts/intro.py todo <ключ>              - что осталось по технологиям плана (код 1 - есть НУЖНО)
  python3 <скилл>/scripts/intro.py docs-task <метка>        - задание агенту pvatf-docs (обзорный вопрос)
  python3 <скилл>/scripts/intro.py needs <ключ>             - потребности плана по технологиям и что из них уже в конспекте
  python3 <скилл>/scripts/intro.py collect-task <ключ> <метка> - задание агенту pvatf-docs: до 5 потребностей плана
  python3 <скилл>/scripts/intro.py examples-task <метка>    - задание агенту pvatf-examples (3 вопроса)
  python3 <скилл>/scripts/intro.py examples-check <метка>   - проверка файла образцов, который записала модель

Каждое задание выдаётся не больше 2 раз на метку: потом метка считается пройденной (обзор или образец
не получен), чтобы не было цикла. Python 3.8+, только стандартная библиотека.
Код выхода: 0 - готово; 1 - есть что сделать или файл не прошёл проверку; 2 - неверные аргументы.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pvatf_paths as pp  # noqa: E402 - копия shared/scripts
import notes  # noqa: E402 - копия shared/scripts

SKILL = Path(__file__).resolve().parent.parent
SCRIPT = "python3 .gigacode/skills/autotest-plan/scripts/intro.py"
DRAFT = "platform-v-at-maven-draft"
OVERVIEW = "Обзор технологии"
TRIES = 2
SEARCH_SECONDS = 30
SKIP = {".git", ".svn", "node_modules", "target", "build", "out", ".gradle", ".m2", ".idea", ".vscode", "Library",
        "AppData", ".Trash", ".cache", "venv", ".venv", "__pycache__", "Applications", "System", "Windows",
        "Program Files", "Program Files (x86)", "ProgramData", "$Recycle.Bin", "proc", "sys", "dev", "snap"}
QUESTIONS = [
    "Пример тест-класса, где используется {what}: аннотации класса и метода теста, поля, как вызываются шаги",
    "Пример класса шагов (или класса-флоу) для {what}: как объявлен класс, как в методе отправляют запрос или"
    " сообщение и возвращают ответ",
    "Как в примере проверяют результат {what}: matcher-ы в .should(...), проверка статуса, поля ответа, ожидание",
]


def examples_dir():
    return pp.root() / "examples"


def ledger_path():
    return examples_dir() / "INTRO.json"


def load_ledger():
    try:
        data = json.loads(ledger_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("draft", "")
    data.setdefault("docs", {})
    data.setdefault("examples", {})
    data.setdefault("needs", {})
    return data


def save_ledger(data):
    ledger_path().parent.mkdir(parents=True, exist_ok=True)
    ledger_path().write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def topics():
    """Метка -> (раздел документации, якорь) из таблицы правила 3 references/autotest-rules.md."""
    try:
        text = (SKILL / "references" / "autotest-rules.md").read_text(encoding="utf-8")
    except OSError:
        return {}
    found = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or not cells[0].startswith("`"):
            continue
        labels = [x.strip(" `") for x in cells[0].split("/")]
        sections = [x.strip() for x in cells[1].split(" / ")]
        anchors = [x.strip() for x in cells[2].split(" / ")]
        for i, label in enumerate(labels):
            section = sections[i] if len(sections) == len(labels) else sections[0]
            anchor = anchors[i] if len(anchors) == len(labels) else anchors[0]
            found[label] = (section, anchor)
    return found


def what(label, info):
    section, anchor = info
    return anchor if anchor not in ("нет", "-", "") else "раздел «" + section + "»"


def is_draft(path):
    return path.is_dir() and path.name.lower().startswith(DRAFT) and (
        (path / "pom.xml").is_file() or any((c / "pom.xml").is_file() for c in path.iterdir() if c.is_dir()))


def search_roots():
    """Где искать, по порядку: рядом с проектом, домашний каталог, на Windows - корни дисков."""
    here = Path.cwd().resolve()
    roots = [(here.parent, 2), (here.parent.parent, 3), (Path.home(), 4)]
    if os.name == "nt":
        roots += [(Path(d + ":\\"), 3) for d in "CDEFGH" if Path(d + ":\\").is_dir()]
    seen, result = set(), []
    for root, depth in roots:
        if str(root) not in seen:
            seen.add(str(root))
            result.append((root, depth))
    return result


def find_draft():
    """Каталог platform-v-at-maven-draft* с pom.xml: обход в ширину, не дольше SEARCH_SECONDS. Нет - None."""
    start = time.time()
    for root, depth in search_roots():
        level = [root]
        for _ in range(depth + 1):
            following = []
            for folder in level:
                if time.time() - start > SEARCH_SECONDS:
                    return None
                try:
                    entries = list(os.scandir(str(folder)))
                except OSError:
                    continue
                for entry in entries:
                    try:
                        if not entry.is_dir(follow_symlinks=False) or entry.name in SKIP or entry.name.startswith("."):
                            continue
                    except OSError:
                        continue
                    path = Path(entry.path)
                    if entry.name.lower().startswith(DRAFT):
                        try:
                            if is_draft(path):
                                return path
                        except OSError:
                            pass
                    following.append(path)
            level = following
    return None


def draft_path(again=False):
    """Путь к проекту-примеру: запомненный или найденный поиском; '-' - не найден."""
    data = load_ledger()
    known = data.get("draft", "")
    if known and known != "-" and Path(known).is_dir() and not again:
        return known
    if known == "-" and not again:
        return "-"
    found = find_draft()
    data["draft"] = str(found) if found else "-"
    save_ledger(data)
    return data["draft"]


def say_draft(path):
    if path != "-":
        print("ДРАФТ: " + path)
    else:
        print("ДРАФТА НЕТ: проект-пример " + DRAFT + " на диске не найден (искал рядом с проектом и в домашнем каталоге)."
              " Скажи человеку одной строкой: «Для лучшего результата скачайте себе проект-пример " + DRAFT
              + " (в любой каталог домашней папки) и скажите «драфт установлен» - тогда " + SCRIPT + " draft --again;"
              " без него план строится только по документации». Ответа не жди - работа идёт дальше.")


def cmd_draft(args):
    if args[:1] == ["--path"] and len(args) >= 2:
        path = Path(args[1]).expanduser()
        if not is_draft(path):
            print("НЕ ДРАФТ: " + str(path) + " - нужен каталог " + DRAFT + "* с pom.xml")
            return 1
        data = load_ledger()
        data["draft"] = str(path.resolve())
        save_ledger(data)
        say_draft(data["draft"])
        return 0
    path = draft_path(again=args[:1] == ["--again"])
    say_draft(path)
    return 0


def project_classes(key):
    """Метка -> классы проекта из колонки «Классы проекта» раздела 3 плана (через запятую, без «-»)."""
    plan = pp.plan_file(key, create=False)
    found, inside = {}, False
    for line in (plan.read_text(encoding="utf-8") if plan.is_file() else "").splitlines():
        if line.startswith("## "):
            inside = line.startswith("## 3. Порядок генерации")
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if inside and line.startswith("| G-") and len(cells) >= 7:
            for label in re.split(r"[,\s]+", cells[4]):
                for cls in cells[6].split(","):
                    # настройка окружения (EnvironmentConfiguration, конфигурации сервисов) есть в любом проекте на
                    # фрейме - это не архитектура тестов; засчитываются только классы шагов и флоу
                    if re.search(r"(Configuration|Config|ConfigurationManager)$", cls.strip()):
                        continue
                    if cls.strip() not in ("", "-") and cls.strip() not in found.setdefault(label, []):
                        found[label].append(cls.strip())
    return found


def plan_labels(key):
    """Метки технологий раздела 3 плана (колонка «Метка»), по порядку, без повторов."""
    plan = pp.plan_file(key, create=False)
    if not plan.is_file():
        return None
    labels, inside = [], False
    for line in plan.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.startswith("## 3. Порядок генерации")
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if inside and line.startswith("| G-") and len(cells) >= 5:
            for label in re.split(r"[,\s]+", cells[4]):
                if label and label != "-" and label not in labels:
                    labels.append(label)
    return labels


def has_overview(label):
    return any(OVERVIEW.lower() in r.question.lower() for r in notes.parse(notes.DATA / "doc-notes" / (label + ".md")))


def examples_file(label):
    return examples_dir() / (label + ".md")


def check_examples(label):
    """Ошибки файла образцов: 3 блока «### Вопрос n:» со статусом из шаблона агента pvatf-examples."""
    path = examples_file(label)
    if not path.is_file():
        return ["файла " + path.as_posix() + " нет"]
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^### Вопрос ", text)[1:]
    errors = []
    if len(blocks) != len(QUESTIONS):
        errors.append("блоков «### Вопрос n:» %d, нужно %d - ответ агента целиком, без сокращений" % (len(blocks), len(QUESTIONS)))
    for block in blocks:
        number = block.split(":", 1)[0].strip()
        m = re.search(r"(?m)^- Статус:\s*(.+?)\s*$", block)
        if not m or m.group(1) not in ("найден", "найден частично", "НЕТ В ПРИМЕРЕ"):
            errors.append("Вопрос " + number + ": нет строки «- Статус: найден | найден частично | НЕТ В ПРИМЕРЕ»")
    return errors


def section(text, title):
    """Строки таблицы раздела плана «## <title>» без заголовка и разделителя: [[ячейки]]."""
    rows, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.startswith("## " + title)
            continue
        if inside and line.startswith("|") and not re.match(r"^\|[-\s|]+\|$", line):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
            rows.append(cells)
    return rows[1:] if rows else []


WAIT = re.compile(r"ожида|дожд|в течение|появит|станет|асинхрон", re.I)
FIELD = re.compile(r"пол[еяю]|значени|json|содерж|тел[оае]|атрибут|параметр", re.I)


def plan_needs(text):
    """Метка -> потребности плана простыми словами, по порядку, без повторов. Только то, что есть в шагах ТК
    и описи артефактов: шагов и проверок сверх ТК не добавляет."""
    steps = [r for r in section(text, "2. Шаги") if len(r) >= 11 and r[0] != "-"]
    label_of = {r[0]: r[6] for r in steps}
    reqs = [r for r in section(text, "9. Запросы из артефактов") if len(r) >= 8 and r[1] != "-"]
    values = [v for v in section(text, "10. Значения из выборки") if len(v) >= 5 and v[0] != "-"]
    result = {}

    def add(label, need):
        bucket = result.setdefault(label, [])
        if need not in bucket:
            bucket.append(need)

    for r in steps:
        label, kind, words = r[6], r[3], r[1] + " " + r[2]
        if label in ("", "-") or kind == "SERVICE":
            continue
        if kind == "AUTH_SESSION":
            add(label, "авторизоваться и передать сессию или токен в следующие запросы")
        if label == "rest":
            own = [q for q in reqs if q[0].split(".")[0] == r[0].split(".")[0]]
            for q in own:
                add(label, "отправить HTTP-запрос " + q[2].upper() + " и получить ответ")
                if q[4] not in ("", "-"):
                    add(label, "передать заголовки HTTP-запроса")
                if q[5] not in ("", "-") and q[2].upper() in ("POST", "PUT", "PATCH"):
                    add(label, "отправить тело запроса JSON из файла")
            if kind in ("OPERATION", "NAVIGATION") and not own:
                add(label, "отправить HTTP-запрос и получить ответ")
            if kind == "ASSERT" or any(q[6] not in ("", "-") for q in own):
                add(label, "проверить код ответа (статус)")
            if kind == "ASSERT" and FIELD.search(words):
                add(label, "проверить значение поля JSON в ответе")
        elif label == "kafka":
            add(label, "прочитать сообщение из топика Kafka и проверить его поля" if kind == "ASSERT"
                else "отправить сообщение в топик Kafka")
        elif label == "db":
            add(label, "выполнить SQL-запрос и получить строки результата")
            if kind == "ASSERT":
                add(label, "проверить значение колонки в результате SQL-запроса")
        elif label == "ui":
            add(label, {"NAVIGATION": "открыть страницу приложения", "ASSERT": "проверить элемент или текст на странице"}.get(
                kind, "нажать на элемент страницы и ввести текст"))
        else:
            add(label, ("проверить: " + r[2] if kind == "ASSERT" else r[1])[:120] + " (шаг " + r[0] + ")")
        if WAIT.search(words):
            add(label, "дождаться результата ожиданием фрейма, без sleep")
    for v in values:
        label = label_of.get(v[1], label_of.get(v[1].split(".")[0], ""))
        if label not in ("", "-"):
            add(label, "взять значение поля из ответа и передать в следующий шаг")
    for label in ("rest", "kafka", "db"):
        if label in result:
            add(label, {"rest": "задать адрес сервиса через настройки, а не в коде",
                        "kafka": "задать адрес брокера и имя топика через настройки",
                        "db": "задать подключение к базе через настройки"}[label])
    return result


def norm(text):
    return re.sub(r"[\s.«»\"`]+", " ", text.lower()).strip()


def answered(label):
    """Вопросы записей конспекта метки (нормализованные)."""
    return {norm(r.question) for r in notes.parse(notes.DATA / "doc-notes" / (label + ".md"))}


def pending_needs(key, label, data=None):
    """Потребности плана метки, на которые в конспекте нет записи и которые выдавались агенту меньше TRIES раз."""
    plan = pp.plan_file(key, create=False)
    text = plan.read_text(encoding="utf-8") if plan.is_file() else ""
    data = data or load_ledger()
    tries = data["needs"].get(label, {})
    done = answered(label)
    return [n for n in plan_needs(text).get(label, []) if norm(n) not in done and tries.get(n, 0) < TRIES]


def cmd_needs(key):
    plan = pp.plan_file(key, create=False)
    if not plan.is_file():
        print("НЕТ ПЛАНА: design.md изменения нет - сначала tc_plan.py build " + key)
        return 2
    found = plan_needs(plan.read_text(encoding="utf-8"))
    for label, items in found.items():
        done = answered(label)
        for need in items:
            print("ПОТРЕБНОСТЬ: " + label + " · " + need + " · " + ("в конспекте" if norm(need) in done else "нет"))
    print("ИТОГ: потребностей " + str(sum(len(v) for v in found.values())))
    return 0


def cmd_todo(key):
    labels = plan_labels(key)
    if labels is None:
        print("НЕТ ПЛАНА: design.md изменения нет - сначала tc_plan.py build " + key)
        return 2
    info = topics()
    data = load_ledger()
    own = project_classes(key)
    draft = draft_path() if any(label not in own for label in labels) else "-"
    need, done = [], []
    for label in labels:
        if label in own:
            print("ПРОЕКТ: " + label + " - в проекте уже свои классы на фрейме (" + ", ".join(own[label][:5]) + "): образцы"
                  " драфта не нужны, раскладка кода (классы шагов, методы, проверки) - как в этих классах; документация - да")
        if label not in info:
            done.append(label + " (нет в таблице правила 3 - знакомства нет)")
            continue
        docs_left = not has_overview(label) and data["docs"].get(label, 0) < TRIES
        examples_left = (label not in own and draft != "-" and check_examples(label)
                         and data["examples"].get(label, 0) < TRIES)
        if docs_left:
            need.append("НУЖНО: знакомство " + label + " · обзор документации: " + SCRIPT + " docs-task " + label
                        + " -> задание агенту pvatf-docs дословно -> notes.py merge " + label + " doc-notes")
        collect = [] if docs_left else pending_needs(key, label, data)
        if collect:
            need.append("НУЖНО: знакомство " + label + " · сбор документации под план (потребностей " + str(len(collect))
                        + "): " + SCRIPT + " collect-task " + key + " " + label + " -> задание агенту pvatf-docs дословно"
                        " -> notes.py merge " + label + " doc-notes")
        if examples_left:
            need.append("НУЖНО: знакомство " + label + " · образцы проекта-примера: " + SCRIPT + " examples-task " + label
                        + " -> задание агенту pvatf-examples дословно -> ответ агента дословно в файл "
                        + examples_file(label).as_posix() + " -> " + SCRIPT + " examples-check " + label)
        if not docs_left and not examples_left and not collect:
            done.append(label)
    if draft == "-" and any(label not in own for label in labels) and not data.get("told"):
        say_draft(draft)  # совет скачать проект-пример - один раз, дальше работа идёт без него
        data = load_ledger()
        data["told"] = True
        save_ledger(data)
    for line in need:
        print(line)
    print("ЗНАКОМСТВО: " + ("готово" if not need else "не закончено") + " · технологии: " + (", ".join(done) or "-")
          + (" · осталось: " + str(len(need)) if need else ""))
    if need:
        print("ДАЛЬШЕ: сделай строки НУЖНО по порядку, потом снова " + SCRIPT + " todo " + key)
    return 1 if need else 0


def dictionary(label):
    path = notes.DATA / "doc-notes" / (label + ".md")
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if notes.DICT_HEAD not in text:
        return "нет"
    words = [l.strip()[2:] for l in text.split(notes.DICT_HEAD, 1)[1].splitlines() if l.strip().startswith("- ")]
    return "; ".join(words[:30]) or "нет"


def cmd_docs_task(label):
    info = topics().get(label)
    if not info:
        print("НЕТ МЕТКИ: " + label + " - нет в таблице правила 3 references/autotest-rules.md")
        return 2
    data = load_ledger()
    data["docs"][label] = data["docs"].get(label, 0) + 1
    save_ledger(data)
    section, anchor = info
    known = notes.parse(notes.DATA / "doc-notes" / (label + ".md"))
    print("ЗАДАНИЕ для агента pvatf-docs (передай дословно, всё ниже этой строки):")
    print("- Технология: " + label + " · " + section)
    print("- Раздел документации: " + section)
    print("- Вопросы:")
    print("  1. " + OVERVIEW + " " + label + ": как работать с " + what(label, info) + " - какой модуль подключить, основные"
          " классы и методы, как отправить запрос или сообщение и получить ответ, как проверить результат matcher-ом в"
          " .should(...), короткий пример теста целиком")
    print("- Якорь технологии: " + anchor)
    print("- Ключевые слова из прошлых ответов документации: " + dictionary(label))
    print("- Формулировки, которые уже пробовали и они НИЧЕГО не дали: нет")
    print("- Уже есть в конспекте: " + ("; ".join(r.id + " " + r.question for r in known[:10]) or "нет"))
    print("- Артефакт: нет")
    folder = notes.DIRS["doc-notes"]
    print("- Записать в: " + (Path.cwd() / folder / "inbox" / (label + ".md")).as_posix())
    print("- Номер первой записи: " + notes.next_id(label))
    return 0


def overview_line(label):
    """Запись обзора метки для задания: ID, «Что использовать» и пример (до 600 знаков); нет - «нет»."""
    for r in notes.parse(notes.DATA / "doc-notes" / (label + ".md")):
        if OVERVIEW.lower() in r.question.lower():
            text = " ".join(l.strip() for l in r.text.splitlines()[1:] if l.strip() and not l.startswith("- Формулировки")
                            and not l.strip().startswith("- «"))
            return r.id + " · " + text[:600]
    return "нет"


def cmd_collect_task(key, label):
    info = topics().get(label)
    if not info:
        print("НЕТ МЕТКИ: " + label + " - нет в таблице правила 3 references/autotest-rules.md")
        return 2
    data = load_ledger()
    batch = pending_needs(key, label, data)[:5]
    if not batch:
        print("СБОР: " + label + " - все потребности плана уже в конспекте, задание не нужно")
        return 0
    tries = data["needs"].setdefault(label, {})
    for n in batch:
        tries[n] = tries.get(n, 0) + 1
    save_ledger(data)
    section_name, anchor = info
    known = notes.parse(notes.DATA / "doc-notes" / (label + ".md"))
    print("ЗАДАНИЕ для агента pvatf-docs (передай дословно, всё ниже этой строки):")
    print("- Технология: " + label + " · " + section_name)
    print("- Раздел документации: " + section_name)
    print("- Режим: сбор под план - каждый вопрос ниже - потребность простыми словами; заголовок записи - текст вопроса дословно")
    print("- Вопросы:")
    for i, n in enumerate(batch, 1):
        print("  " + str(i) + ". " + n)
    print("- Обзор технологии: " + overview_line(label))
    print("- Якорь технологии: " + anchor)
    print("- Ключевые слова из прошлых ответов документации: " + dictionary(label))
    print("- Формулировки, которые уже пробовали и они НИЧЕГО не дали: нет")
    print("- Уже есть в конспекте: " + ("; ".join(r.id + " " + r.question for r in known[:15]) or "нет"))
    print("- Артефакт: нет")
    folder = notes.DIRS["doc-notes"]
    print("- Записать в: " + (Path.cwd() / folder / "inbox" / (label + ".md")).as_posix())
    print("- Номер первой записи: " + notes.next_id(label))
    return 0


def cmd_examples_task(label):
    info = topics().get(label)
    if not info:
        print("НЕТ МЕТКИ: " + label + " - нет в таблице правила 3 references/autotest-rules.md")
        return 2
    draft = draft_path()
    if draft == "-":
        say_draft(draft)
        return 1
    data = load_ledger()
    data["examples"][label] = data["examples"].get(label, 0) + 1
    save_ledger(data)
    print("ЗАДАНИЕ для агента pvatf-examples (передай дословно, всё ниже этой строки):")
    print("- Путь: " + draft)
    print("- Что это: проект-пример (драфт)")
    print("- Технология: " + label + " · " + info[0])
    print("- Вопросы:")
    for i, q in enumerate(QUESTIONS, 1):
        print("  " + str(i) + ". " + q.format(what=what(label, info)))
    print("ПОСЛЕ ОТВЕТА: ответ агента целиком, без правок, запиши инструментом записи файлов в "
          + examples_file(label).as_posix() + ", потом " + SCRIPT + " examples-check " + label)
    return 0


def cmd_examples_check(label):
    errors = check_examples(label)
    if errors:
        print("ОШИБКА: образцы " + label + " не прошли проверку:")
        for e in errors:
            print("- " + e)
        left = TRIES - load_ledger()["examples"].get(label, 0)
        print("ДАЛЬШЕ: " + ("снова " + SCRIPT + " examples-task " + label + " и агент pvatf-examples" if left > 0
                            else "попыток больше нет - образцов " + label + " не будет, " + SCRIPT + " todo <ключ>"))
        return 1
    print("ОК: образцы " + label + " - " + examples_file(label).as_posix())
    return 0


def main(args):
    if args[:1] == ["draft"]:
        return cmd_draft(args[1:])
    if len(args) == 3 and args[0] == "collect-task":
        return cmd_collect_task(args[1], args[2])
    if len(args) == 2 and args[0] == "needs":
        return cmd_needs(args[1])
    if len(args) == 2 and args[0] in ("todo", "docs-task", "examples-task", "examples-check"):
        return {"todo": cmd_todo, "docs-task": cmd_docs_task, "examples-task": cmd_examples_task,
                "examples-check": cmd_examples_check}[args[0]](args[1])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
