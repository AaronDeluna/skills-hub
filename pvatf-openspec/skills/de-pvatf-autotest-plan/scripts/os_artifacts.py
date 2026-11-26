#!/usr/bin/env python3
"""
Артефакты изменения OpenSpec для автотеста по тест-кейсу (пакет pvatf-openspec, вид autotest).
Запуск из корня проекта (в нём есть openspec/config.yaml):

  python3 <скилл>/scripts/os_artifacts.py new <ключ ТК> [--task <код задачи>]  - создать изменение
  python3 <скилл>/scripts/os_artifacts.py proposal <имя изменения>            - proposal.md
  python3 <скилл>/scripts/os_artifacts.py tc <имя изменения>                  - tc/<ключ>.md
  python3 <скилл>/scripts/os_artifacts.py design <имя изменения>              - design.md = план автотеста
  python3 <скилл>/scripts/os_artifacts.py tasks <имя изменения>               - tasks.md
  python3 <скилл>/scripts/os_artifacts.py sync <имя изменения>                - чекбоксы tasks.md по статусам G

Раскладка изменения openspec/changes/<имя>/:
  proposal.md, tc/<ключ>.md, design.md (план: шаги, G, константы, окружение - пишет
  tc_plan.py), tasks.md; outputs/ - рабочие файлы: TC.md, TC-CHECK.md, ENV-TC.md,
  fragments/, CHECK.md, RUN.md.
Ключ ТК - строка x-pvatf-tc в .openspec.yaml. Модель артефакты руками не пишет.

Печатает строки ИТОГ, ФАЙЛ, НУЖНО, НАХОДКА, ПРОВЕРИТЬ. Код выхода: 0 - артефакт готов,
1 - нужно действие (строки НУЖНО / НАХОДКА / ПРОВЕРИТЬ), 2 - неверный запуск или нет изменения.
Python 3.8+, только стандартная библиотека.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pvatf_paths as pp  # noqa: E402 - копия shared/scripts

SKILLS = Path(__file__).resolve().parent.parent.parent
TIMEOUT = 600
KEY = re.compile(r"^[A-Z][A-Z0-9_]*-T?\d+$")
AT = "python3 .gigacode/skills/de-pvatf-autotest-gen/scripts/at_tools.py"


def out(*lines):
    sys.stdout.buffer.write(("\n".join(str(l) for l in lines) + "\n").encode("utf-8"))


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def rel(path):
    try:
        return str(Path(path).resolve().relative_to(Path.cwd().resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return rel(path)


def run_script(skill, script, args):
    try:
        r = subprocess.run([sys.executable, str(SKILLS / skill / "scripts" / script)] + args,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 2, str(error)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def field(text, name):
    """Поле ТК: строка «- Название: x» (TC.md от tc_convert) или «**Название:** x»."""
    m = re.search(r"(?m)^- " + re.escape(name) + r":\s*(.+)$", text) or re.search(r"\*\*" + re.escape(name) + r":\*\*\s*(.+)", text)
    value = m.group(1).strip() if m else "-"
    if value in ("", "-") and name == "Название":
        head = re.match(r"#\s*\S+\s*·\s*(.+)", text)
        value = head.group(1).strip() if head else "-"
    return value or "-"


def front(text):
    head = re.search(r"(?s)^---\n(.*?)\n---", text)
    return dict((k.strip(), v.strip()) for k, v in
                (l.split(":", 1) for l in (head.group(1) if head else "").splitlines() if ":" in l))


def gen_rows(plan):
    """Строки раздела 3 плана (G) с номером строки в файле: [(номер строки, ячейки)]."""
    rows, inside = [], False
    for no, line in enumerate(plan.splitlines(), 1):
        if line.startswith("## "):
            inside = line.startswith("## 3.")
            continue
        if inside and re.match(r"^\|\s*G-\d+\s*\|", line):
            rows.append((no, [c.strip() for c in line.strip().strip("|").split("|")]))
    return rows


# ---------- команды ----------

def cmd_new(args):
    key = args[0] if args else ""
    task = args[args.index("--task") + 1] if "--task" in args and args.index("--task") + 1 < len(args) else ""
    if not KEY.match(key):
        out("Использование: os_artifacts.py new <ключ ТК вида ABC-T123> [--task <код задачи>]")
        return 2
    if not pp.on():
        out("НЕТ OPENSPEC: в корне нет openspec/config.yaml - установите по INSTALL.md пакета")
        return 2
    root = pp.find_change("autotest", key) or pp.ensure_change("autotest", key, task)
    out("ИЗМЕНЕНИЕ: " + root.name, "ТК: " + key, "ФАЙЛ: " + rel(root / ".openspec.yaml"))
    return 0


def target(args):
    if not args:
        out("НЕТ ИЗМЕНЕНИЯ: укажите имя изменения")
        return None, None, None
    root = pp.OPENSPEC / "changes" / args[0]
    key = pp.meta(root).get("x-pvatf-tc", "")
    if not root.is_dir() or not KEY.match(key):
        out("НЕТ ИЗМЕНЕНИЯ: " + args[0] + " - создайте его: os_artifacts.py new <ключ ТК>")
        return None, None, None
    return args[0], root, key


def tc_steps(tc):
    """Таблица шагов TC.md: [(№, действие, данные, ожидаемый результат)]."""
    rows = []
    for line in tc.splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if len(cells) >= 4 and re.fullmatch(r"\d+", cells[0]):
            rows.append(cells[:4])
    return rows


def cmd_proposal(args):
    name, root, key = target(args)
    if not root:
        return 2
    tc = read(root / "outputs" / "TC.md")
    if not tc and key.startswith("NOTC-"):
        out("НУЖНО: ТК нет - нужен файл (лог, Allure, код теста) и имя тест-класса: спроси одной строкой «Имя тест-класса?"
            " Латиницей, окончание Test», потом tc_convert.py <файл> --key " + key + " --class <Имя>Test; потом снова")
        return 1
    if not tc:
        out("НУЖНО: тест-кейс " + key + " не загружен - шаг 1 скилла de-pvatf-autotest-plan: человек дал файл (ТК, лог, Allure, код теста)"
            " -> tc_convert.py <этот файл> --key " + key + "; дал только ключ -> ТК из TMS по ключу (MCP) -> tc_convert.py; потом снова")
        return 1
    import tc_plan
    import tc_common as tcc
    parsed = tcc.parse_tc(root / "outputs" / "TC.md")
    project = tc_plan.load_env().get("project", {})
    cls = tc_plan.class_name(parsed)
    package = project.get("test_package") or project.get("base_package") or ""
    title, no_tc = field(tc, "Название"), key.startswith("NOTC-")
    steps = tc_steps(tc)
    run_script("de-pvatf-autotest-plan", "tc_check.py", [key])  # всегда заново: ТК могли заменить исправленным
    check = read(root / "outputs" / "TC-CHECK.md")
    status = re.search(r"(?m)^- Статус:\s*(\S+)", check)
    findings = [" · ".join(c.strip() for c in l.strip().strip("|").split("|")[:3]) for l in check.splitlines()
                if re.match(r"^\|\s*TC-\d+", l) and l.strip().strip("|").split("|")[-1].strip() != "да"]  # блокирующие - не допущения
    text = ["# Proposal: " + name, "",
            "## Зачем",
            ("Автоматизировать проверку «" + title + "» - ТК в TMS ещё нет, служебный ключ " + key + "." if no_tc
             else "Автоматизировать тест-кейс " + key + " «" + title + "».")
            + (" Цель ТК: " + field(tc, "Цель") + "." if field(tc, "Цель") not in ("-", "") else ""), "",
            "## Тест-кейс",
            "| Ключ | Название | Источник | Проверка ТК |", "|------|----------|----------|-------------|",
            "| " + key + " | " + title + " | " + field(tc, "Источник") + " (" + field(tc, "Файл источника") + ") | "
            + (status.group(1) if status else "-") + " |", "",
            "## Сценарий",
            "Шаги ТК дословно. Автотест повторяет их по порядку - ни шагов, ни проверок сверх этого списка.", "",
            "| № | Действие | Тестовые данные | Ожидаемый результат |", "|---|----------|-----------------|---------------------|"]
    text += ["| " + " | ".join(r) + " |" for r in steps] or ["| - | шагов нет | - | - |"]
    text += ["", "## Предусловия и данные",
             "- Предусловия: " + field(tc, "Предусловия"),
             "- Требования к тестовым данным: " + field(tc, "Требования к тестовым данным"), "",
             "## Что меняется",
             "- Новый тест-класс `" + cls + "`" + (" в пакете `" + package + "`" if package else "") + " - один тест-метод, шаги 1-"
             + str(len(steps)) + ".",
             "- Классы шагов, данные и настройки - только из design.md, разделы 11-16: каждый файл, метод, проверка и ключ"
             " настройки там названы, человек подтверждает их до кода.", "",
             "## Критерии приёмки",
             "1. Каждый шаг ТК 1-" + str(len(steps)) + " - шаг теста с комментарием `// Шаг <n>: <действие>`; служебные шаги"
             " (design.md, раздел 2, тип SERVICE) - без кода.",
             "2. Каждый ожидаемый результат - проверка в коде по design.md, раздел 13; ожидаемые значения - константы тест-класса.",
             "3. " + ("Без `@TmsLink`: ТК нет, ключ служебный." if no_tc else "`@TmsLink(\"" + key + "\")` на тест-методе."),
             "4. Компиляция тестов `" + (" ".join(project.get("compile_argv") or []) or project.get("compile_command") or "командой из ENV.json") + "` - без ошибок.",
             "5. `" + AT + " check " + key + "` - ИТОГ: находок 0.",
             "6. `" + AT + " run " + key + "` - РЕЗУЛЬТАТ: passed; тест запускается последней задачей, без вопроса человеку."
             " Не прошёл - отчёт RUN.md человеку, изменение без passed архивирует только человек.", "",
             "## Вне scope",
             "- Правка тест-кейса в TMS.",
             "- Шаги, проверки, очистка данных и подготовка, которых нет в ТК.",
             "- Другие тесты и общие классы проекта, кроме строк «дополнить» в design.md, раздел 11.",
             "- `perfeccionista.properties` и регистрация сервисов: их пишут скрипт и de-pvatf-env-check, не генерация.", "",
             "## Допущения",
             "Находки проверки ТК, которые не блокируют автотест (подробно: outputs/TC-CHECK.md):"]
    text += ["- " + f for f in findings] or ["- нет"]
    out("ИТОГ: proposal записан · ТК " + key + " · шагов " + str(len(steps)), "ФАЙЛ: " + write(root / "proposal.md", "\n".join(text) + "\n"))
    return 0


def cmd_tc(args):
    name, root, key = target(args)
    if not root:
        return 2
    tc = read(root / "outputs" / "TC.md")
    if not tc:
        out("НУЖНО: тест-кейс " + key + " не загружен - сначала артефакт proposal")
        return 1
    code, output = run_script("de-pvatf-autotest-plan", "tc_check.py", [key])
    status = re.search(r"СТАТУС:\s*(\w+)", output)
    if code not in (0, 1) or not status or status.group(1) not in ("PASS", "WARNING", "FAIL"):
        out("ОШИБКА ПРОВЕРКИ ТК: tc_check.py вернул " + str(code) + " без статуса PASS / WARNING / FAIL - артефакт tc не записан",
            *output.strip().splitlines()[-10:])
        return 2
    status = status.group(1)
    findings = [l[len("НАХОДКА:"):].strip() for l in output.splitlines() if l.startswith("НАХОДКА:")]
    steps = re.search(r"(?ms)^(\|\s*№.*?)(?=^\s*$|\Z)", tc)
    body = ["# ТК " + key + ": " + field(tc, "Название"), "",
            "**Проверка ТК:** " + status + " · находок " + str(len(findings)) + " · подробно: "
            + rel(root / "outputs" / "TC-CHECK.md"), "",
            "## Шаги", (steps.group(1).strip() if steps else "нет таблицы шагов в TC.md"), "",
            "## Находки проверки (TC-n)", "| Находка |", "|---------|"]
    body += ["| " + f.replace("|", "/") + " |" for f in findings] or ["| нет |"]
    path = write(root / "tc" / (key + ".md"), "\n".join(body) + "\n")
    if status == "FAIL":
        for f in findings:
            out("НАХОДКА: " + f)
        out("ИТОГ: тест-кейс FAIL - автотест не пишется, ТК правит автор в TMS", "ФАЙЛ: " + path)
        return 1
    out("ИТОГ: тест-кейс " + status + " · находок " + str(len(findings)), "ФАЙЛ: " + path)
    return 0


def cmd_design(args):
    """design.md = план автотеста: tc_plan build (если нет), validate, окружение под ТК."""
    name, root, key = target(args)
    if not root:
        return 2
    design = root / "design.md"
    arts = root / "outputs" / "ARTIFACTS.md"
    if not arts.is_file():
        run_script("de-pvatf-autotest-plan", "artifacts.py", ["scan", key])
    import tc_plan
    env = tc_plan.load_env()
    if env.get("status", "failed") == "failed":
        codes = [x.get("code", "-") for x in env.get("problems", []) if x.get("severity") == "critical"]
        out("НУЖНО: окружение проекта не готово (" + ("нет ENV.json" if not env else "ENV.json failed: " + ", ".join(codes[:3]))
            + ") - скилл de-pvatf-env-check, режим setup, потом снова")
        return 1
    if "- Разбор агентом: нужен" in read(arts):
        out("НУЖНО: разбор артефактов - шаг 1б скилла de-pvatf-autotest-plan: artifacts.py task " + key + " -> агент pvatf-artifacts"
            " -> artifacts.py merge " + key + ", потом снова")
        return 1
    changed = design.is_file() and tc_plan.tc_changed(read(design))
    if changed:
        out("ТК ИЗМЕНЁН: TC.md новее плана - план строится заново по новому ТК (прошлые правки плана и подтверждение не в счёт)")
    if not design.is_file() or changed:
        code, text = run_script("de-pvatf-autotest-plan", "tc_plan.py", ["build", key] + (["--force"] if changed else []))
        lines = [l for l in text.splitlines() if l.split(":", 1)[0] in ("ФАЙЛ", "ШАГОВ", "ПРОВЕРИТЬ", "ОКРУЖЕНИЕ", "ЗАМЕТКА", "НЕТ TC.md", "НЕТ TC-CHECK.md", "АРХИТЕКТУРА", "СБРОС")]
        out(*lines)
        if code != 0:
            return 1
        if any(l.startswith("ПРОВЕРИТЬ:") and "нет -" not in l for l in lines):
            out("НУЖНО: шаг 5 скилла de-pvatf-autotest-plan - исправь в design.md только строки из ПРОВЕРИТЬ, потом снова")
            return 1
    # знакомство с технологиями ТК до разделов 11-14: обзор документации и образцы проекта-примера
    code, text = run_script("de-pvatf-autotest-plan", "intro.py", ["todo", key])
    out(*[l for l in text.splitlines() if l.startswith(("ДРАФТА НЕТ", "ПРОЕКТ", "НУЖНО", "ЗНАКОМСТВО", "ДАЛЬШЕ"))])
    if code == 1:
        out("НУЖНО: шаг 4б скилла de-pvatf-autotest-plan - сделай строки НУЖНО знакомства по порядку, потом снова")
        return 1
    code, text = run_script("de-pvatf-autotest-plan", "tc_plan.py", ["validate", key])
    edited = [l for l in text.splitlines() if l.startswith(("ПРАВКА ПЛАНА ПОСЛЕ ГЕНЕРАЦИИ", "ПОДТВЕРЖДЕНИЕ: нужно - план изменён"))]
    if code != 0:
        out(*[l for l in text.splitlines() if l.startswith(("ПРОБЛЕМА", "ИТОГ", "СБРОС"))])
        if "архитектура тестов не выбрана" in text:
            out("НУЖНО: шаг 1в скилла de-pvatf-autotest-plan - спроси человека «steps или flow», ответ: " + tc_plan.SELF + " style " + key + " <steps|flow>")
        out("НУЖНО: шаги 6-7 скилла de-pvatf-autotest-plan - исправь в design.md строки ПРОБЛЕМА, потом снова (не больше 3 кругов)")
        return 1
    code, env_out = run_script("de-pvatf-env-check", "env_tc.py", [key, "--no-compile"])
    if code != 0:
        out(*[l for l in env_out.splitlines() if l.startswith("НУЖНО:")])
        out("НУЖНО: окружение под ТК не готово - скилл de-pvatf-env-check, режим setup " + key + ", потом снова")
        return 1
    head = front(read(design))
    if not tc_plan.approved_ok(read(design)) and len(edited) == 2:
        out(*edited)
        out("НУЖНО: подтверждение плана - шаг 8 скилла de-pvatf-autotest-plan, вопрос из строки ПОДТВЕРЖДЕНИЕ дословно; «да» -> " + tc_plan.SELF + " approve "
            + key + "; правки -> исправь строки, потом снова. Код не пишется до подтверждения")
        return 1
    if not tc_plan.approved_ok(read(design)):
        out("НУЖНО: подтверждение плана - шаг 8 скилла de-pvatf-autotest-plan: покажи человеку разделы 11-16 design.md (файлы, методы"
            " шагов, проверки, настройки, реализация по G - раздел 14а, привязка шагов к коду, планируемые изменения) и спроси «План верен? да / номер строки и как исправить»; «да» -> " + tc_plan.SELF + " approve "
            + key + "; правки -> исправь строки, потом снова. Код не пишется до подтверждения")
        return 1
    out("ИТОГ: design готов · plan_status " + head.get("plan_status", "-") + " · G " + str(len(gen_rows(read(design))))
        + " · окружение готово", "ФАЙЛ: " + rel(design))
    return 0


def section_lines(plan, title):
    """Строки таблицы раздела плана с номером строки в файле: [(номер строки, ячейки)]."""
    rows, inside = [], False
    for no, line in enumerate(plan.splitlines(), 1):
        if line.startswith("## "):
            inside = line.startswith("## " + title)
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if inside and cells and not set(cells[0]) <= set("-:") and cells[0] not in ("Шаг", "G", "Файл", "Ключ", "-"):
            rows.append((no, cells))
    return rows


def ids(cell):
    return [x.strip() for x in cell.split(",") if x.strip() and x.strip() != "-"]


def plan_items(plan):
    """Задачи групп G из разделов 11-14 плана: {G: [(текст задачи, номер строки design.md)]}."""
    step_g = {r[0]: r[10] for _, r in section_lines(plan, "2.") if len(r) >= 11}
    files = [(no, f) for no, f in section_lines(plan, "11.") if len(f) >= 4]
    methods = [(no, m) for no, m in section_lines(plan, "12.") if len(m) >= 6]
    checks = [(no, c) for no, c in section_lines(plan, "13.") if len(c) >= 5]
    settings = [(no, x) for no, x in section_lines(plan, "14.") if len(x) >= 4]
    test_file = front(plan).get("test_file", "-")
    items = {}
    for no, f in files:
        if f[1] not in ("создать", "дополнить") or f[0] == test_file:
            continue
        gs = ids(f[3])
        if not gs:  # тело запроса шага n -> G этого шага
            step = re.search(r"шага ([\d.]+)", f[2])
            gs = [step_g.get(step.group(1), "")] if step else []
        for g in gs or [""]:
            items.setdefault(g, []).append(("%s `%s` - %s" % ("Создать" if f[1] == "создать" else "Дополнить", f[0], f[2]), no))
    for no, m in methods:
        sig = m[2] + "(" + ", ".join(p.strip().split()[1] + " " + p.strip().split()[0] for p in m[5].split(";")
                                     if len(p.strip().split()) >= 2 and p.strip() != "нет") + ")"
        items.setdefault(m[0], []).append(("Метод `%s.%s` - шаги %s%s" % (m[1], sig, m[3], "; запрос " + m[4] if m[4] not in ("-", "") else ""), no))
    for no, c in checks:
        if c[3].startswith("проверено в шаге"):
            continue
        items.setdefault(step_g.get(c[0], ""), []).append(("Проверка шага %s: %s · поле `%s` · %s · %s" % tuple(c[:5]), no))
    for no, x in settings:
        g = next((m[0] for _, m in methods if "настройки " + x[0] in m[5]), "")
        items.setdefault(g, []).append(("Настройка `%s` = `%s` в `%s`" % (x[0], x[2], x[1]), no))
    return items


def cmd_tasks(args):
    name, root, key = target(args)
    if not root:
        return 2
    plan = read(root / "design.md")
    if front(plan).get("plan_status") not in ("planned", "generating", "assembled", "checked"):
        out("НУЖНО: design.md не готов (plan_status: " + front(plan).get("plan_status", "нет") + ") - сначала артефакт design")
        return 1
    import tc_plan
    if not tc_plan.approved_ok(plan):
        out("НУЖНО: план не подтверждён человеком или изменён после подтверждения - сначала артефакт design, шаг подтверждения")
        return 1
    gens = gen_rows(plan)
    lines_of = plan.splitlines()
    test_line = next((no for no, l in enumerate(lines_of, 1) if l.startswith("test_file:")), 1)
    test_row = next((no for no, f in section_lines(plan, "11.") if f[0] == front(plan).get("test_file")), test_line)
    items = plan_items(plan)
    project = tc_plan.load_env().get("project", {})
    compile_cmd = " ".join(project.get("compile_argv") or []) or project.get("compile_command") or "команда компиляции из ENV.json"
    lines = ["apply-mode: subagents", "plan: " + tc_plan.plan_hash(plan), "",
             "## Цель", "Автотест " + key + " по design.md: тест-класс `" + front(plan).get("test_file", "-") + "`, шаги генерации "
             + ", ".join(g[0] for _, g in gens) + ". Делать только задачи ниже; файл, метод или проверка не из списка - не писать.", ""]
    flow = front(plan).get("step_style") == "flow"
    n = 0
    for no, g in gens:
        n += 1
        lines += ["## " + str(n) + ". " + g[0] + " · " + (g[3] if len(g) > 3 else "-") + " · шаги " + g[1],
                  "- [ ] " + str(n) + ".1 " + g[0] + ": задание `" + AT + " next " + key + "` -> агенту pvatf-generator строка"
                  " ПРОМПТ дословно, ответ ok -> `" + AT + " mark " + key + " " + g[0] + " ok` (design.md:" + str(no) + ")"]
        k = 1
        for text, line in items.get(g[0], []):
            k += 1
            lines.append("- [ ] " + str(n) + "." + str(k) + " " + text + " (design.md:" + str(line) + ")")
        k += 1
        lines.append("- [ ] " + str(n) + "." + str(k) + " " + g[0] + " · проверка задания: `outputs/tasks/" + g[0] + ".md` руками"
                     " не правлен; строка находки или ПАДЕНИЕ - только `" + AT + " next " + key + " --add \"<строка>\"` (design.md:" + str(no) + ")")
        k += 1
        lines.append("- [ ] " + str(n) + "." + str(k) + " " + g[0] + " · проверка фрагмента: константы своей G в ## fields, комментариев"
                     " нет" + (" (только `// STUB`), в body только `.step(\"Шаг N: ...\", f -> f.<метод>(...))` по каждому шагу G"
                               if flow else " (только `// Шаг N:` и `// STUB`)") + " (design.md:" + str(no) + ")")
        lines += ["- [ ] " + str(n) + "." + str(k + 1) + " `" + AT + " compile " + key + " " + g[0] + "` (`" + compile_cmd + "`)"
                  " -> КОМПИЛЯЦИЯ: ok (design.md:" + str(no) + ")", ""]
    n += 1
    lines += ["## " + str(n) + ". Сборка и проверка",
              "- [ ] " + str(n) + ".1 `" + AT + " assemble " + key + "` -> тест-класс `" + front(plan).get("test_file", "-")
              + "` (design.md:" + str(test_row) + ")"]
    k = 1
    for text, line in items.get("", []):  # строки плана без G (настройки без метода и т.п.)
        k += 1
        lines.append("- [ ] " + str(n) + "." + str(k) + " " + text + " (design.md:" + str(line) + ")")
    if flow:
        k += 1
        lines.append("- [ ] " + str(n) + "." + str(k) + " проверка flow: тест-класс - цепочка `FlowRunner.flowRunnerFor(<Флоу>.class)"
                     " ... .run()` от assemble, `new <Флоу>()` нет, тест-класс руками не правлен (design.md:" + str(test_row) + ")")
    k += 1
    lines.append("- [ ] " + str(n) + "." + str(k) + " проверка комментариев: в тест-классе и созданных классах шагов комментариев нет"
                 + (" (только `// STUB`)" if flow else " (только `// Шаг N:` и `// STUB`)") + " (design.md:" + str(test_row) + ")")
    lines += ["- [ ] " + str(n) + "." + str(k + 1) + " `" + AT + " check " + key + "` -> ИТОГ: находок 0, кроме строк STUB (design.md:" + str(test_line) + ")", ""]
    n += 1  # последняя задача всегда - запуск теста; без него изменение не архивируется
    lines += ["## " + str(n) + ". Запуск теста",
              "- [ ] " + str(n) + ".1 `" + AT + " run " + key + "` -> РЕЗУЛЬТАТ: passed - тест прошёл на стенде; запуск без вопроса человеку"
              " (design.md:" + str(test_line) + ")",
              "- [ ] " + str(n) + ".2 итог: `" + AT + " summary " + key + "` -> строки под ИТОГ дословно, свой текст итога не пишешь"
              " (design.md:" + str(test_line) + ")", ""]
    total = sum(1 for l in lines if l.startswith("- [ ]"))
    out("ИТОГ: tasks записан · групп " + str(n) + " · задач " + str(total), "ФАЙЛ: " + write(root / "tasks.md", "\n".join(lines)))
    return sync(root)


def fragment_code(root, done):
    """Блоки fields и body фрагментов готовых G: проверки тест-метода видны в них ещё до assemble."""
    lines = []
    for g in sorted(done):
        text = read(root / "outputs" / "fragments" / (g + ".md"))
        for m in re.finditer(r"(?ms)^## (?:fields|body)\s*\n```(?:java|kotlin)?\n(.*?)```", text):
            lines += m.group(1).splitlines()
    return lines


def code_fields(paths, extra=()):
    """Поля, которые проверяет код файлов и строк extra (те же правила, что у at_tools.py check). Нет at_tools - None."""
    try:
        sys.path.insert(0, str(SKILLS / "de-pvatf-autotest-gen" / "scripts"))
        import at_tools
    except Exception:  # noqa: BLE001 - скилл de-pvatf-autotest-gen не установлен
        return None
    found = set()
    for lines in [read(f).splitlines() for f in paths if Path(f).is_file()] + [list(extra)]:
        consts = at_tools.file_constants(lines)
        for _, line in at_tools.code_lines(lines):
            found.update(x.lower() for x in at_tools.checked_fields(line, consts))
    return found


def code_lines_of(paths, extra=()):
    """Строки кода файлов и строк extra без комментариев (правила at_tools.py). Нет at_tools - None."""
    try:
        sys.path.insert(0, str(SKILLS / "de-pvatf-autotest-gen" / "scripts"))
        import at_tools
    except Exception:  # noqa: BLE001 - скилл de-pvatf-autotest-gen не установлен
        return None
    return [l for f in paths if Path(f).is_file() for _, l in at_tools.code_lines(read(f).splitlines())] \
        + [l for _, l in at_tools.code_lines(list(extra))]


def item_done(line, plan, fields, code=None):
    """Задача из раздела 11-14 сделана по коду: файл есть, метод объявлен, поле проверяется, ключ в файле."""
    m = re.search(r"(?:Создать|Дополнить) `([^`]+)`", line)
    if m:
        return Path(m.group(1)).is_file()
    m = re.search(r"Метод `(\w+)\.(\w+)\(", line)
    if m:
        path = next((f[0] for _, f in section_lines(plan, "11.") if f[0].endswith("/" + m.group(1) + ".java")), "")
        return bool(path) and Path(path).is_file() and re.search(r"\b" + m.group(2) + r"\s*\(", read(path)) is not None
    m = re.search(r"Проверка шага \S+: .*? · поле `([^`]+)` · ([^·]+) · (.*?) \(design\.md:", line)
    if m and m.group(2).strip() == "статус":  # код ответа: в коде должно быть ожидаемое (константа или значение)
        if code is None:
            return True
        import at_tools
        return at_tools.status_checked(m.group(3), code)
    if m:
        return fields is None or m.group(1).strip("`").lstrip("$.").lower() in fields
    m = re.search(r"Настройка `([^`]+)` = .* в `([^`]+)`", line)
    if m:
        return Path(m.group(2)).is_file() and re.search(r"(?m)^\s*" + re.escape(m.group(1)) + r"\s*[=:]", read(m.group(2))) is not None
    return None


def sync(root):
    """Чекбоксы tasks.md по статусам и коду: G ok/stub в разделе 3 плана; задачи файлов, методов, проверок и настроек -
    G готова и это видно в коде; компиляция G - outputs/compile/G-n.md с «Компиляция: ok» или «заглушки»; сборка (plan_status assembled), check (checked), запуск (run_status: passed при checked)."""
    tasks = root / "tasks.md"
    text = read(tasks)
    if not text:
        return 0
    plan = read(root / "design.md")
    done = {g[0] for _, g in gen_rows(plan) if len(g) > 7 and g[7] in ("ok", "stub", "manual")}
    # заглушка (stub) и код, который дописал человек (manual): задачи G - за человеком, check сверит код
    stub = {g[0] for _, g in gen_rows(plan) if len(g) > 7 and g[7] in ("stub", "manual")}
    status = front(plan).get("plan_status", "")
    checked = status == "checked"
    assembled = status in ("assembled", "checked")
    ran = checked and front(plan).get("run_status") == "passed"  # отметка - только тест прошёл, не «запускали»
    code = [f[0] for _, f in section_lines(plan, "11.") if f[0].endswith(".java")]
    frags = fragment_code(root, done)
    fields = code_fields(code, frags)
    lines_of_code = code_lines_of(code, frags)
    tools = None
    try:
        sys.path.insert(0, str(SKILLS / "de-pvatf-autotest-gen" / "scripts"))
        import at_tools as tools
    except Exception:  # noqa: BLE001 - скилл de-pvatf-autotest-gen не установлен: проверки задач ниже не отмечаются по коду
        tools = None
    key = front(plan).get("tc", "-")
    test_file = front(plan).get("test_file", "-")
    flow = front(plan).get("step_style") == "flow"
    test_code = read(test_file) if test_file != "-" else ""
    lines, marked, cleared, group = [], 0, 0, ""
    for line in text.splitlines():
        head = re.match(r"^## \d+\. (G-\d+)\b", line)
        if line.startswith("## "):
            group = head.group(1) if head else ""
        m = re.match(r"^- \[[ x]\] \S+ (G-\d+):", line)
        if m:
            hit = m.group(1) in done
        elif "· проверка задания:" in line:
            hit = group in stub or (group in done and (tools is None or not tools.task_changed(key, group)))
        elif "· проверка фрагмента:" in line:
            hit = group in stub or (group in done and (tools is None or not tools.fragment_problems(key, plan, group)))
        elif " проверка flow:" in line:
            hit = assembled and "FlowRunner.flowRunnerFor(" in test_code and (tools is None or (
                Path(test_file).is_file() and tools.code_hash(test_file) == front(plan).get("assembled", "-")))
        elif " проверка комментариев:" in line:
            hit = assembled and (tools is None or not tools.comment_findings(plan, test_file, flow))
        elif "at_tools.py summary" in line:
            hit = ran and (root / "outputs" / "SUMMARY.md").is_file()
        elif "at_tools.py compile" in line:
            result = read(root / "outputs" / "compile" / (group + ".md"))
            hit = bool(group) and (group in stub or group in done and re.search(r"(?m)^- Компиляция: (ok|заглушки)\b", result) is not None)
        elif "at_tools.py assemble" in line:
            hit = assembled
        elif "at_tools.py check" in line:
            hit = checked
        elif "at_tools.py run" in line:
            hit = ran
        else:
            hit = item_done(line, plan, fields, lines_of_code)
            if hit is not None:
                hit = group in stub or (hit and (group in done if group else assembled))
        if hit is not None and line.startswith(("- [ ]", "- [x]")):
            if hit and line.startswith("- [ ]"):
                marked += 1
            if not hit and line.startswith("- [x]"):
                cleared += 1  # G вернули в todo или план снова генерируется - отметка снимается
            line = ("- [x]" if hit else "- [ ]") + line[5:]
        lines.append(line)
    tasks.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out("СИНХРОНИЗАЦИЯ: tasks.md · отмечено сейчас " + str(marked) + (" · снято " + str(cleared) if cleared else ""))
    return 0


def cmd_sync(args):
    name, root, key = target(args)
    return sync(root) if root else 2


COMMANDS = {"new": cmd_new, "proposal": cmd_proposal, "tc": cmd_tc, "design": cmd_design, "tasks": cmd_tasks, "sync": cmd_sync}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        out("Использование: os_artifacts.py new <ключ ТК> [--task <код>] | proposal | tc | design | tasks | sync <имя изменения>")
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
