#!/usr/bin/env python3
"""
Изменения OpenSpec для работ набора PVATF (пакет pvatf-openspec). Запуск из корня проекта
(в нём есть openspec/config.yaml):

  python3 <скилл>/scripts/os_work.py new <вид> [<объект>] [--task <код задачи>]  - создать изменение
  python3 <скилл>/scripts/os_work.py proposal <имя изменения>                     - proposal.md
  python3 <скилл>/scripts/os_work.py design <имя изменения>                       - design.md
  python3 <скилл>/scripts/os_work.py tasks <имя изменения>                        - tasks.md
  python3 <скилл>/scripts/os_work.py sync <имя изменения>                         - чекбоксы tasks.md по статусам
  python3 <скилл>/scripts/os_work.py next [<имя изменения>]                      - что делать дальше
  python3 <скилл>/scripts/os_work.py steps-ok <имя изменения>                     - человек подтвердил шаги из лога или кода

Виды (x-pvatf-kind) и объект:
  autotest <ключ ТК>       - автотест по ТК: схема pvatf-autotests, артефакты пишет os_artifacts.py
  tc-check <ключ ТК>       - только проверка ТК: то же изменение autotest, остановка после артефакта tc
  env-setup [-]            - проверка и настройка окружения проекта
  frame-update [<версия>]  - обновление версии фрейма (по умолчанию - самая новая из release notes)
  migration [-]            - миграция на фрейм: design.md изменения - это карта миграции
  de-pvatf-autotest-review <файл>   - ревью и оптимизация автотеста
  markup [<каталог>]       - разметка тестов (аннотации Allure, TmsLink и т.п.)
  deps-review [-]          - ревью управления зависимостями

Раскладка: openspec/changes/<имя>/ - proposal.md, design.md, tasks.md, outputs/ (рабочие
файлы скиллов). Общее для проекта - openspec/pvatf/ (конспект документации, ENV.json).
Модель артефакты руками не пишет. Код выхода: 0 - выполнено, 1 - нужно действие (строки
НУЖНО), 2 - неверный запуск или нет изменения. Python 3.8+, только стандартная библиотека.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pvatf_paths as pp  # noqa: E402 - копия shared/scripts

SKILLS = Path(__file__).resolve().parent.parent.parent
TIMEOUT = 600
KEY = re.compile(r"^[A-Z][A-Z0-9_]*-T?\d+$")
OA = "de-pvatf-autotest-plan", "os_artifacts.py"
KINDS = {
    "autotest": "Автотест по тест-кейсу",
    "tc-check": "Проверка тест-кейса по правилам TC-n",
    "env-setup": "Проверка и настройка окружения проекта автотестов",
    "frame-update": "Обновление версии фрейма до самой новой из release notes",
    "migration": "Миграция проекта автотестов на фрейм PVATF",
    "de-pvatf-autotest-review": "Ревью и оптимизация автотеста",
    "markup": "Разметка тестов по правилам markup-rules",
    "deps-review": "Ревью управления зависимостями проекта",
}


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


def openspec(args):
    exe = shutil.which("openspec")
    if not exe:
        return None
    try:
        r = subprocess.run([exe] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def as_json(res):
    if not res or res[0] != 0 or "{" not in res[1]:
        return None
    try:
        return json.loads(res[1][res[1].index("{"):])
    except ValueError:
        return None


def run(skill, script, args):
    try:
        r = subprocess.run([sys.executable, str(SKILLS / skill / "scripts" / script)] + args,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 2, str(error)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def relay(skill_script, args):
    code, text = run(skill_script[0], skill_script[1], args)
    if text.strip():
        out(text.rstrip())
    return code


def table(text, title):
    sect = re.search(r"(?ms)^## " + re.escape(title) + r"[^\n]*\n(.*?)(?=^## |\Z)", text)
    rows = []
    for line in (sect.group(1) if sect else "").splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not set("".join(cells)) <= set("-: "):
                rows.append(cells)
    return rows[1:] if rows else []


def front(text):
    head = re.search(r"(?s)^---\n(.*?)\n---", text)
    return dict((k.strip(), v.strip()) for k, v in
                (l.split(":", 1) for l in (head.group(1) if head else "").splitlines() if ":" in l))


# ---------- new / proposal ----------

def cmd_new(args):
    task = ""
    if "--task" in args:
        i = args.index("--task")
        task = args[i + 1] if i + 1 < len(args) else ""
        args = args[:i] + args[i + 2:]
    kind = args[0] if args else ""
    obj = args[1] if len(args) > 1 else "-"
    if kind not in KINDS:
        out("Использование: os_work.py new <вид> [<объект>] [--task <код>]; виды: " + ", ".join(KINDS))
        return 2
    if not pp.on():
        out("НЕТ OPENSPEC: в корне нет openspec/config.yaml - установите по INSTALL.md пакета")
        return 2
    if kind == "autotest" and obj == "--no-tc":
        obj = pp.next_no_tc_key()  # ТК ещё не заведён: служебный ключ, @TmsLink в тест не ставится
        root = pp.ensure_change("autotest", obj, task)
        out("ИЗМЕНЕНИЕ: " + root.name, "ВИД: autotest", "ТК НЕТ: служебный ключ " + obj,
            "ДАЛЬШЕ: спроси имя тест-класса, потом tc_convert.py <файл> --key " + obj + " --class <Имя>Test",
            "ФАЙЛ: " + rel(root / ".openspec.yaml"))
        return 0
    if kind in ("autotest", "tc-check") and Path(obj).is_file():
        code, text = run("de-pvatf-autotest-plan", "tc_convert.py", [obj])  # ключ - из файла ТК, человека не спрашиваем
        key = re.search(r"(?m)^ТК:\s*(\S+)", text)
        if code != 0 or not key:
            out(text.rstrip())
            return code or 1
        obj = key.group(1)
    if kind in ("autotest", "tc-check"):
        if not KEY.match(obj):
            out("НУЖНО: ключ ТК вида ABC-T123 - спроси человека одной строкой: «Ключ ТК? Дайте ключ вида CODE-T123 или"
                " ответьте «ТК нет»»; ответ «ТК нет» -> os_work.py new autotest --no-tc")
            return 2
        root = pp.find_change("autotest", obj) or pp.ensure_change("autotest", obj, task)
        if kind == "tc-check" and "x-pvatf-stop" not in pp.meta(root) and not (root / "design.md").is_file():
            (root / ".openspec.yaml").write_text(read(root / ".openspec.yaml") + 'x-pvatf-stop: "tc"\n', encoding="utf-8")
        if kind == "autotest" and "x-pvatf-stop" in pp.meta(root):  # после «проверь ТК» человек просит автотест
            (root / ".openspec.yaml").write_text(re.sub(r"(?m)^x-pvatf-stop:.*\n?", "", read(root / ".openspec.yaml")),
                                                 encoding="utf-8")
        out("ИЗМЕНЕНИЕ: " + root.name, "ВИД: " + kind, "ФАЙЛ: " + rel(root / ".openspec.yaml"))
        return 0
    if kind == "de-pvatf-autotest-review" and not Path(obj).is_file():
        out("НУЖНО: путь к тест-классу (.java) от корня проекта")
        return 2
    obj = obj.replace("\\", "/")
    root = pp.find_change(kind, None if obj == "-" else obj) or pp.ensure_change(kind, obj, task)
    out("ИЗМЕНЕНИЕ: " + root.name, "ВИД: " + kind, "ФАЙЛ: " + rel(root / ".openspec.yaml"))
    return 0


def target(args):
    if not args:
        out("НЕТ ИЗМЕНЕНИЯ: укажите имя изменения")
        return None
    root = pp.OPENSPEC / "changes" / args[0]
    m = pp.meta(root)
    if not root.is_dir() or m.get("x-pvatf-kind") not in KINDS:
        out("НЕТ ИЗМЕНЕНИЯ: " + args[0] + " - создайте его: os_work.py new <вид> [<объект>]")
        return None
    return args[0], root, m["x-pvatf-kind"], m.get("x-pvatf-object", m.get("x-pvatf-tc", "-"))


def cmd_proposal(args):
    t = target(args)
    if not t:
        return 2
    name, root, kind, obj = t
    if kind == "autotest":
        return relay(OA, ["proposal", name])
    text = "\n".join(["# Proposal: " + name, "", "## Зачем", KINDS[kind] + ".", "",
                      "## Объект", obj if obj != "-" else "весь проект", "",
                      "## Что меняется", "- По design.md: состояние и план работ по данным скиллов набора.", "",
                      "## Вне scope", "- Работы других видов - отдельными изменениями.", ""])
    out("ИТОГ: proposal записан · вид " + kind, "ФАЙЛ: " + write(root / "proposal.md", text))
    return 0


# ---------- design по видам: (состояние, план работ) или (None, строки НУЖНО) ----------

def plan_env(_root, _obj):
    run("de-pvatf-env-check", "env_check.py", ["--no-compile"])
    try:
        data = json.loads(read(pp.env_dir() / "ENV.json"))
    except ValueError:
        data = {}
    problems = data.get("problems", [])
    state = ["- Паспорт: " + rel(pp.env_dir() / "ENV.json") + " · статус " + data.get("status", "?") + " · проблем " + str(len(problems))]
    state += ["- " + p.get("severity", "?") + " · " + p.get("code", "?") + " · " + p.get("message", "") for p in problems]
    work = [(p.get("code", "?"), "de-pvatf-env-check", "режим setup: исправить проблему " + p.get("code", "?"))
            for p in problems if p.get("severity") in ("critical", "warning")]
    work.append(("Проверка", "de-pvatf-env-check", "режим check: env_check.py с компиляцией, СТАТУС ok"))
    return state, work


def plan_frame(_root, obj):
    code, text = run("de-pvatf-env-update", "env_update.py", ["versions"])
    state = ["- Версия фрейма сейчас:"] + ["  " + l for l in text.strip().splitlines()[:12]]
    state.append("- Целевая версия: " + (obj if obj != "-" else "самая новая из release notes (MCP, агент pvatf-docs)"))
    return state, [("Версия", "de-pvatf-env-update", "поднять версию фрейма" + ("" if obj == "-" else " до " + obj) + " по шагам скилла"),
                   ("Компиляция", "de-pvatf-env-update", "ошибки компиляции после обновления: env_update.py errors, правки по changelog"),
                   ("Проверка", "de-pvatf-env-check", "режим check: env_check.py с компиляцией, СТАТУС ok")]


def plan_review(_root, obj):
    plan_file = pp.review_dir(obj) / "REVIEW-PLAN.md"
    if not read(plan_file):
        run("de-pvatf-autotest-review", "review.py", ["find", obj])
    rows = [r for r in table(read(plan_file), "Правки") if len(r) >= 7]
    state = ["- План ревью: " + rel(plan_file) + " · правок " + str(len(rows))]
    state += ["- " + r[0] + " · " + r[1] + " · " + r[2] + " · " + r[3] for r in rows]
    work = [("Согласование", "de-pvatf-autotest-review", "показать план правок человеку и записать выбор (review.py approve)")]
    work += [(r[0] + " · " + r[3][:60], "de-pvatf-autotest-review", "правка " + r[0] + " (review.py next / mark)") for r in rows]
    work.append(("Проверка", "de-pvatf-autotest-review", "review.py check: компиляция и REVIEW.md"))
    return state, work


def plan_markup(root, obj):
    scope = obj if obj != "-" else "все тест-классы проекта"
    return ["- Объект разметки: " + scope, "- Рабочие файлы: " + rel(root / "outputs"),
            "- Правила: references/markup-rules.md скилла de-pvatf-migration-step"], \
        [("Разметка", "de-pvatf-migration-step", "юнит типа markup для " + scope + " (агент pvatf-marker, references/markup.md)")]


def plan_deps(_root, _obj):
    folder = pp.kind_dir("deps-review", "dependency")
    if not read(folder / "DEPS.json"):
        run("de-pvatf-dependency-review", "deps.py", ["scan"])
    state = ["- Скан: " + rel(folder / "DEPS.json") + " · находки: " + rel(folder / "FINDINGS.md")]
    state += [l for l in read(folder / "FINDINGS.md").splitlines() if l.startswith("|")][:20]
    return state, [("Проверка правил", "de-pvatf-dependency-review", "цикл deps.py next / mark до конца списка"),
                   ("Отчёт", "de-pvatf-dependency-review", "deps.py report -> DEPENDENCY-ANALYSIS.md")]


PLANS = {"env-setup": plan_env, "frame-update": plan_frame, "de-pvatf-autotest-review": plan_review,
         "markup": plan_markup, "deps-review": plan_deps}


def cmd_design(args):
    t = target(args)
    if not t:
        return 2
    name, root, kind, obj = t
    if kind == "autotest":
        return relay(OA, ["design", name])
    if kind == "migration":
        head = front(read(root / "design.md"))
        if head.get("map_status") != "approved":
            out("НУЖНО: карта миграции (design.md этого изменения) не утверждена (map_status: "
                + head.get("map_status", "нет карты") + ") - скилл de-pvatf-migration-map по этапам, затем одобрение карты человеком")
            return 1
        out("ИТОГ: design (карта миграции) утверждён · " + rel(root / "design.md"))
        return 0
    state, work = PLANS[kind](root, obj)
    lines = ["# Design: " + name, "", "## Контекст", "- Вид: " + kind + " · объект: " + obj, "",
             "## Состояние"] + state + ["", "## План работ", "| № | Группа | Скилл | Что |", "|---|--------|-------|-----|"]
    lines += ["| " + str(i) + " | " + g.replace("|", "/") + " | " + s + " | " + w.replace("|", "/") + " |"
              for i, (g, s, w) in enumerate(work, 1)]
    lines += ["", "## Риски", "- Скилл остановился (вопрос, блокер) - apply ждёт человека, задача не отмечается.", ""]
    out("ИТОГ: design записан · вид " + kind + " · работ " + str(len(work)), "ФАЙЛ: " + write(root / "design.md", "\n".join(lines)))
    return 0


def cmd_tasks(args):
    t = target(args)
    if not t:
        return 2
    name, root, kind, obj = t
    if kind == "autotest":
        return relay(OA, ["tasks", name])
    design = read(root / "design.md")
    if not design:
        out("НУЖНО: нет design.md - сначала артефакт design")
        return 1
    lines = ["apply-mode: single", "", "## Цель", KINDS[kind] + " · " + obj, ""]
    n = 0
    if kind == "migration":
        if front(design).get("map_status") != "approved":
            out("НУЖНО: карта миграции не утверждена - сначала артефакт design")
            return 1
        in_units = False
        for no, line in enumerate(design.splitlines(), 1):
            if line.startswith("## "):
                in_units = line.startswith("## 4.")
                continue
            m = re.match(r"^\| (M-\d+) \| [^|]* \| ([^|]*) \| ([^|]*) \| ([^|]*) \|", line) if in_units else None
            if m:
                n += 1
                lines += ["## " + str(n) + ". " + m.group(1) + " · " + m.group(2).strip() + " · " + m.group(4).strip(),
                          "- [ ] " + str(n) + ".1 " + m.group(1) + ": скилл de-pvatf-migration-step, юнит " + m.group(1)
                          + " (один юнит на чат) (design.md:" + str(no) + ")", ""]
        n += 1
        lines += ["## " + str(n) + ". Проверка миграции", "- [ ] " + str(n) + ".1 Скилл de-pvatf-migration-review: ревью миграции", ""]
    else:
        for no, line in enumerate(design.splitlines(), 1):
            m = re.match(r"^\| (\d+) \| (.*?) \| ([\w-]+) \| (.*) \|$", line)
            if m:
                n += 1
                lines += ["## " + str(n) + ". " + m.group(2),
                          "- [ ] " + str(n) + ".1 Скилл " + m.group(3) + ": " + m.group(4) + " (design.md:" + str(no) + ")", ""]
    if not n:
        out("НУЖНО: в design.md нет строк плана работ")
        return 1
    out("ИТОГ: tasks записан · групп " + str(n), "ФАЙЛ: " + write(root / "tasks.md", "\n".join(lines)))
    return sync(root, kind)


def sync(root, kind):
    """Чекбоксы tasks.md по статусам скиллов (миграция - статус юнита done в карте)."""
    if kind == "autotest":
        return relay(OA, ["sync", root.name])
    tasks = root / "tasks.md"
    text = read(tasks)
    if not text or kind != "migration":
        return 0
    done = {u[0] for u in table(read(root / "design.md"), "4. Юниты работ") if len(u) >= 8 and u[7] == "done"}
    lines, marked = [], 0
    for line in text.splitlines():
        m = re.match(r"^- \[ \] \S+ (M-\d+):", line)
        if m and m.group(1) in done:
            line = "- [x]" + line[5:]
            marked += 1
        lines.append(line)
    tasks.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out("СИНХРОНИЗАЦИЯ: tasks.md · отмечено сейчас " + str(marked))
    return 0


def cmd_sync(args):
    t = target(args)
    return sync(t[1], t[2]) if t else 2


def artifact_status(root):
    """[(id, done)] по схеме изменения: из openspec status, без CLI - по файлам."""
    st = as_json(openspec(["status", "--change", root.name, "--json"]))
    if st and st.get("artifacts"):
        return [(a.get("id"), a.get("status") == "done") for a in st["artifacts"]]
    files = [("proposal", "proposal.md"), ("tc", "tc"), ("design", "design.md"), ("tasks", "tasks.md")]
    schema = pp.meta(root).get("schema")
    return [(i, (root / f).exists() and (not (root / f).is_dir() or any((root / f).iterdir())))
            for i, f in files if i != "tc" or schema == "pvatf-autotests"]


def approved_ok(text):
    sys.path.insert(0, str(SKILLS / "de-pvatf-autotest-plan" / "scripts"))
    import tc_plan
    return tc_plan.approved_ok(text)


def plan_hash(text):
    sys.path.insert(0, str(SKILLS / "de-pvatf-autotest-plan" / "scripts"))
    import tc_plan
    return tc_plan.plan_hash(text)


def file_hash(path):
    import hashlib
    return hashlib.sha1(read(path).replace("\r\n", "\n").encode("utf-8")).hexdigest()[:12]


def steps_unconfirmed(root):
    """Шаги TC.md восстановлены скриптом из лога или кода (Источник: log / code), а человек их не подтвердил для этой
    версии TC.md (x-pvatf-steps-ok в .openspec.yaml - отпечаток TC.md на момент «да»)."""
    tc_md = root / "outputs" / "TC.md"
    source = re.search(r"(?m)^- Источник:\s*(\w+)", read(tc_md))
    return bool(source) and source.group(1) in ("log", "code") and pp.meta(root).get("x-pvatf-steps-ok") != file_hash(tc_md)


def cmd_steps_ok(args):
    t = target(args)
    if not t:
        return 2
    root = t[1]
    tc_md = root / "outputs" / "TC.md"
    if not tc_md.is_file():
        out("НЕТ TC.md: " + rel(tc_md))
        return 2
    meta = re.sub(r"(?m)^x-pvatf-steps-ok:.*\n?", "", read(root / ".openspec.yaml"))
    (root / ".openspec.yaml").write_text(meta.rstrip("\n") + '\nx-pvatf-steps-ok: "' + file_hash(tc_md) + '"\n', encoding="utf-8")
    out("ИТОГ: шаги TC.md подтверждены человеком", "ДАЛЬШЕ: os_work.py next " + t[0])
    return 0


def check_rows(root):
    """Находки последнего check (outputs/CHECK.md), если он новее тест-класса; старый итог - None."""
    check_md = root / "outputs" / "CHECK.md"
    test = Path(front(read(root / "design.md")).get("test_file", "-"))
    if not check_md.is_file() or (test.is_file() and test.stat().st_mtime > check_md.stat().st_mtime):
        return None
    return [l.strip()[2:-2].strip() for l in read(check_md).splitlines()
            if l.startswith("| ") and l.strip() not in ("| Находка |", "| нет |")]


def cmd_next(args):
    if not pp.on():
        out("НЕТ OPENSPEC: в корне нет openspec/config.yaml - установите по INSTALL.md пакета")
        return 2
    if not args:
        active = [f.name for f, m in pp.changes()]
        if len(active) != 1:
            out("ИЗМЕНЕНИЯ: " + (", ".join(active) or "нет"),
                "ДЕЙСТВИЕ: " + ("спроси человека, какое изменение продолжить" if active
                                else "создай изменение: os_work.py new <вид> <объект>"))
            return 0
        args = active
    t = target(args)
    if not t:
        return 2
    name, root, kind, obj = t
    sync(root, kind)
    tc_md = root / "outputs" / "TC.md"
    if kind == "autotest" and steps_unconfirmed(root):
        out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: подтверждение шагов",
            "КОМАНДА: шаги TC.md восстановлены скриптом из лога или кода - покажи человеку таблицу шагов из " + rel(tc_md)
            + " и спроси «Шаги восстановлены верно? Да / номер шага и как исправить»; правки -> исправь в TC.md только"
            " названные строки и спроси снова; «да» -> python3 .gigacode/skills/de-pvatf-orchestrator/scripts/os_work.py steps-ok "
            + name + ", потом os_work.py next " + name)
        return 0
    newer = lambda f: tc_md.is_file() and f.is_file() and tc_md.stat().st_mtime > f.stat().st_mtime
    for aid, done in artifact_status(root):
        head = front(read(root / "design.md")) if aid == "design" and done else {}
        if kind == "autotest" and done and aid == "proposal" and newer(root / "proposal.md"):
            done = False  # ТК заменили (исправленный после FAIL) - proposal заново
        if kind == "autotest" and done and aid == "tc" and newer(root / "tc" / (obj + ".md")):
            done = False  # новый TC.md - проверка ТК заново
        if aid == "design" and done and kind == "migration" and head.get("map_status") != "approved":
            done = False  # карта ещё строится - design не готов
        if aid == "design" and done and kind == "autotest" and head.get("plan_status", "draft") == "draft":
            done = False  # черновик плана - design не готов
        if aid == "design" and done and kind == "autotest" and not approved_ok(read(root / "design.md")):
            done = False  # человек не подтвердил план или план изменён после «да» - код не пишется
        if aid == "tasks" and done and kind == "autotest" and not re.search(
                r"(?m)^plan: " + plan_hash(read(root / "design.md")) + r"\s*$", read(root / "tasks.md")):
            done = False  # tasks.md построен по другой версии плана - заново
        if aid == "tc" and done and re.search(r"\*\*Проверка ТК:\*\*\s*FAIL\b", read(root / "tc" / (obj + ".md"))):
            out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: итог проверки ТК",
                "КОМАНДА: покажи человеку tc/" + obj + ".md - тест-кейс FAIL, автотест не пишется; автор исправляет ТК в TMS."
                " Человек дал исправленный ТК -> python3 .gigacode/skills/de-pvatf-autotest-plan/scripts/tc_convert.py <файл> --key " + obj
                + " (ключ без файла - ТК из TMS по ключу), потом os_work.py next " + name)
            return 0
        if not done:
            out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: артефакт " + aid,
                "КОМАНДА: openspec instructions " + aid + " --change \"" + name + "\" --json - выполни поле instruction")
            return 0
        if aid == "tc" and pp.meta(root).get("x-pvatf-stop") == "tc":
            out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: итог проверки ТК",
                "КОМАНДА: покажи человеку tc/" + obj + ".md; автотест по этому ТК - os_work.py new autotest " + obj
                + " (снимает стоп), потом os_work.py next " + name)
            return 0
    tasks_text = read(root / "tasks.md")
    left = len(re.findall(r"(?m)^- \[ \]", tasks_text))
    # задачи запуска и итога идут последними, у них свои ДЕЙСТВИЯ ниже
    other = len([l for l in tasks_text.splitlines() if l.startswith("- [ ]") and "at_tools.py run" not in l
                 and "at_tools.py summary" not in l])
    summary_left = any(l.startswith("- [ ]") and "at_tools.py summary" in l for l in tasks_text.splitlines())
    design = read(root / "design.md")
    run = front(design).get("run_status", "")
    if kind == "autotest":
        test_file = Path(front(design).get("test_file", "-"))
        test_code = read(test_file)
        gens = [g for g in table(design, "3. Порядок генерации") if len(g) >= 8]
        built = test_file.is_file() and front(design).get("plan_status") in ("assembled", "checked")
        # заглушка - пока строка STUB этой G в тест-классе; человек дописал код и убрал её -> accept
        stubs = [g[0] for g in gens if g[7] == "stub" and re.search(r"//\s*STUB\s+" + re.escape(g[0]) + r"\b", test_code)]
        written = [g[0] for g in gens if g[7] == "stub" and g[0] not in stubs] if built else []
        gap = [g[0] for g in gens if g[7] == "blocked"
               and re.search(r"(?mi)^- Причина:\s*план\s*[-:]", read(root / "outputs" / "fragments" / (g[0] + ".md")))]
        rows = check_rows(root) if built else None
        person = [r for r in rows or [] if r.startswith("ЧЕЛОВЕК ")]
        if gap:
            out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: правка плана · " + ", ".join(gap),
                "КОМАНДА: агент ответил, что в плане не хватает файла, метода или проверки (fragments/" + gap[0] + ".md, строка"
                " «Причина: план - ...»). Документация это не решит, stub не ставь: покажи человеку причину и спроси «В плане"
                " не хватает: <причина>. Добавить в design.md? да / как иначе»; ответ -> правка строки раздела 11-14"
                " design.md, os_work.py design " + name + " (validate и новое «да»), потом os_work.py next " + name)
            return 0
        if written:
            out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: приём кода человека · " + ", ".join(written),
                "КОМАНДА: человек дописал заглушки и убрал строки // STUB - python3 .gigacode/skills/de-pvatf-autotest-gen/scripts/"
                "at_tools.py accept " + obj + " (код G -> фрагменты, статус manual), потом at_tools.py check " + obj
                + ", потом os_work.py next " + name)
            return 0
        if person and not [r for r in rows if not r.startswith(("STUB ", "ЧЕЛОВЕК "))]:
            out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: итог · находки в коде человека",
                "КОМАНДА: check нашёл ошибки в коде, который дописал человек (строки ЧЕЛОВЕК в outputs/CHECK.md) - сам их не"
                " исправляешь. Покажи человеку эти строки и спроси «Находки в вашем коде: исправите сами или архивировать"
                " как есть?»; «исправил» -> python3 .gigacode/skills/de-pvatf-autotest-gen/scripts/at_tools.py check " + obj
                + " (assemble не запускай), потом os_work.py next " + name + "; «архивировать» -> openspec archive "
                + name + " --yes")
            return 0
        if other:
            out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: apply · задач осталось " + str(left),
                "КОМАНДА: openspec instructions apply --change \"" + name + "\" --json - выполни поле instruction")
            return 0
        if stubs:
            out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: итог · заглушки " + ", ".join(stubs),
                "КОМАНДА: тест не запускается - в нём заглушки (строки STUB). Покажи человеку итог скилла de-pvatf-autotest-gen и спроси"
                " «Заглушки " + ", ".join(stubs) + ": допишете код сами (в тест-классе и классах шагов, строки // STUB убрать)"
                " или архивировать как есть?»; «дописал» -> os_work.py next " + name + " (даст приём кода: at_tools.py"
                " accept; assemble не запускай)"
                + "; «архивировать» -> openspec archive " + name + " --yes")
            return 0
        if run == "env":
            out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: env-setup " + obj,
                "КОМАНДА: окружение под ТК не готово, тест не запускался - скилл de-pvatf-env-check, режим setup " + obj
                + ", потом python3 .gigacode/skills/de-pvatf-autotest-gen/scripts/at_tools.py run " + obj)
            return 0
    if kind == "autotest" and run and run != "passed":
        out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: тест не прошёл · " + run + " · отчёт openspec/changes/" + name + "/outputs/RUN.md",
            "КОМАНДА: скилл de-pvatf-autotest-gen, шаг 8: падения КОД - исправление по шагу 8 (тест-класс - через фрагмент, класс шагов -"
            " агент), check, снова at_tools.py run " + obj
            + " (не больше 2 кругов); СТЕНД, ПРОВЕРКА, окружение - покажи человеку RUN.md и спроси «Тест не прошёл: <причина>."
            " Исправить и запустить снова или архивировать как есть?»; «архивировать» -> openspec archive " + name + " --yes")
        return 0
    if kind == "autotest" and run == "passed" and summary_left and not other:
        out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: итог",
            "КОМАНДА: тест прошёл - python3 .gigacode/skills/de-pvatf-autotest-gen/scripts/at_tools.py summary " + obj
            + ", строки под ИТОГ - в ответ дословно (заполни только поля в <...>), потом os_work.py next " + name)
        return 0
    if left and not (kind == "autotest" and not other):  # автотест: остались только задачи запуска и итога - ниже «запуск теста»
        out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: apply · задач осталось " + str(left),
            "КОМАНДА: openspec instructions apply --change \"" + name + "\" --json - выполни поле instruction")
        return 0
    head = front(read(root / "design.md"))
    if kind == "autotest" and (not head.get("run_status") or left):
        out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: apply · запуск теста",
            "КОМАНДА: скилл de-pvatf-autotest-gen, шаги 7-9: python3 .gigacode/skills/de-pvatf-autotest-gen/scripts/at_tools.py run " + obj
            + " - тест не запускался, архив только после запуска")
        return 0
    out("ИЗМЕНЕНИЕ: " + name, "ДЕЙСТВИЕ: архив",
        "КОМАНДА: openspec archive " + name + " --yes")
    return 0


COMMANDS = {"new": cmd_new, "proposal": cmd_proposal, "design": cmd_design, "tasks": cmd_tasks,
            "sync": cmd_sync, "next": cmd_next, "steps-ok": cmd_steps_ok}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        out("Использование: os_work.py new <вид> [<объект>] | proposal | design | tasks | sync | next | steps-ok <имя изменения>")
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
