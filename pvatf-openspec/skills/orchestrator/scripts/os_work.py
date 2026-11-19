#!/usr/bin/env python3
"""
Изменения OpenSpec для работ набора PVATF (пакет pvatf-openspec). Запуск из корня проекта:

  python3 <скилл>/scripts/os_work.py new <вид> [<объект>] [--task <код задачи>]  - создать изменение
  python3 <скилл>/scripts/os_work.py proposal <имя изменения>                     - proposal.md
  python3 <скилл>/scripts/os_work.py design <имя изменения>                       - design.md
  python3 <скилл>/scripts/os_work.py tasks <имя изменения>                        - tasks.md
  python3 <скилл>/scripts/os_work.py next [<имя изменения>]                      - что делать дальше

Виды (x-pvatf-kind) и объект:
  autotest <ключ ТК>       - автотест по ТК: схема pvatf-autotests, артефакты пишет os_artifacts.py
  tc-check <ключ ТК>       - проверка тест-кейса (TC-n)
  env-setup [-]            - проверка и настройка окружения проекта
  frame-update [<версия>]  - обновление версии фрейма (по умолчанию - самая новая из release notes)
  migration [-]            - миграция проекта на фрейм по карте MIGRATION-MAP.md
  autotest-review <файл>   - ревью и оптимизация автотеста
  markup [<каталог>]       - разметка тестов (аннотации Allure, TmsLink и т.п.)
  deps-review [-]          - ревью управления зависимостями

Данные для design берутся из рабочих файлов скиллов (.gigacode/data/...). Данных нет ->
строка НУЖНО называет скилл, который их подготовит. Модель артефакты руками не пишет.
Код выхода: 0 - выполнено, 1 - нужно действие (строки НУЖНО), 2 - неверный запуск / нет CLI.
Python 3.8+, только стандартная библиотека.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DATA = Path(".gigacode") / "data"
SKILLS = Path(__file__).resolve().parent.parent.parent
TIMEOUT = 600
KEY = re.compile(r"^[A-Z][A-Z0-9_]*-T?\d+$")
KINDS = {
    "autotest": ("pvatf-autotests", "ключ ТК", "Автотест по тест-кейсу"),
    "tc-check": ("pvatf-work", "ключ ТК", "Проверка тест-кейса по правилам TC-n"),
    "env-setup": ("pvatf-work", "-", "Проверка и настройка окружения проекта автотестов"),
    "frame-update": ("pvatf-work", "версия или -", "Обновление версии фрейма до самой новой из release notes"),
    "migration": ("pvatf-work", "-", "Миграция проекта автотестов на фрейм PVATF"),
    "autotest-review": ("pvatf-work", "файл теста", "Ревью и оптимизация автотеста"),
    "markup": ("pvatf-work", "каталог или -", "Разметка тестов по правилам markup-rules"),
    "deps-review": ("pvatf-work", "-", "Ревью управления зависимостями проекта"),
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


def status(name):
    res = openspec(["status", "--change", name, "--json"])
    if res and res[0] == 0:
        try:
            return json.loads(res[1][res[1].index("{"):])
        except ValueError:
            return None
    return None


def change_root(name):
    st = status(name)
    return Path(st["changeRoot"]) if st and "changeRoot" in st else Path("openspec") / "changes" / name


def meta(root):
    result = {}
    for line in read(root / ".openspec.yaml").splitlines():
        m = re.match(r"^([\w-]+):\s*(.*?)\s*$", line)
        if m:
            result[m.group(1)] = m.group(2).strip('"\'')
    return result


def run(skill, script, args):
    try:
        r = subprocess.run([sys.executable, str(SKILLS / skill / "scripts" / script)] + args,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 2, str(error)
    return r.returncode, r.stdout.decode("utf-8", "replace")


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
    if kind == "autotest":
        code, text = run("autotest-plan", "os_artifacts.py", ["new", obj] + (["--task", task] if task else []))
        out(text.rstrip())
        return code
    if kind == "tc-check" and not KEY.match(obj):
        out("НУЖНО: ключ ТК вида ABC-T123 для вида tc-check")
        return 2
    if kind == "autotest-review" and not Path(obj).is_file():
        out("НУЖНО: путь к тест-классу (.java) от корня проекта для вида autotest-review")
        return 2
    slug = re.sub(r"[^a-z0-9]+", "-", (Path(obj).stem if kind == "autotest-review" else obj).lower()).strip("-")
    name = "-".join(p for p in (task.lower(), kind, "" if slug in ("", "-") else slug) if p)
    root = Path("openspec") / "changes" / name
    if not root.is_dir():
        res = openspec(["new", "change", name, "--schema", KINDS[kind][0]])
        if res is None:
            out("НЕТ CLI: openspec не найден - установите по INSTALL.md пакета")
            return 2
        if res[0] != 0:
            out("ОШИБКА openspec new change:", res[1].strip())
            return 2
        root = change_root(name)
    m = meta(root)
    lines = read(root / ".openspec.yaml").rstrip("\n").splitlines()
    for k, v in (("skip_specs", "true"), ("x-pvatf-kind", kind), ("x-pvatf-object", obj)):
        if k not in m:
            lines.append(k + ": " + (v if k == "skip_specs" else '"' + v.replace('"', "") + '"'))
    write(root / ".openspec.yaml", "\n".join(lines) + "\n")
    out("ИЗМЕНЕНИЕ: " + name, "ВИД: " + kind, "ФАЙЛ: " + rel(root / ".openspec.yaml"))
    return 0


def target(args):
    if not args:
        out("НЕТ ИЗМЕНЕНИЯ: укажите имя изменения")
        return None
    root = change_root(args[0])
    m = meta(root)
    if not root.is_dir() or m.get("x-pvatf-kind") not in KINDS:
        out("НЕТ ИЗМЕНЕНИЯ: " + args[0] + " - создайте его: os_work.py new <вид> [<объект>]")
        return None
    return args[0], root, m["x-pvatf-kind"], m.get("x-pvatf-object", "-")


def cmd_proposal(args):
    t = target(args)
    if not t:
        return 2
    name, root, kind, obj = t
    if kind == "autotest":
        code, text = run("autotest-plan", "os_artifacts.py", ["proposal", name])
        out(text.rstrip())
        return code
    text = "\n".join(["# Proposal: " + name, "", "## Зачем", KINDS[kind][2] + ".", "",
                      "## Объект", obj if obj != "-" else "весь проект", "",
                      "## Что меняется", "- По design.md: план строится по данным скиллов набора.", "",
                      "## Вне scope", "- Работы других видов - отдельными изменениями.", ""])
    out("ИТОГ: proposal записан · вид " + kind, "ФАЙЛ: " + write(root / "proposal.md", text))
    return 0


# ---------- design: данные по видам ----------

def plan_tc_check(obj):
    if not read(DATA / "autotest" / obj / "TC.md"):
        return None, ["НУЖНО: тест-кейс " + obj + " не загружен - скилл autotest-plan, шаг 1 (MCP TMS -> tc_convert.py)"]
    code, text = run("autotest-plan", "tc_check.py", [obj])
    st = re.search(r"СТАТУС:\s*(\w+)", text)
    findings = [l[len("НАХОДКА:"):].strip() for l in text.splitlines() if l.startswith("НАХОДКА:")]
    state = ["Проверка: " + (st.group(1) if st else "?") + " · находок " + str(len(findings)),
             "Подробно: " + rel(DATA / "autotest" / obj / "TC-CHECK.md")] + ["- " + f for f in findings]
    return state, [("Итог проверки", "autotest-plan", "показать человеку итог проверки " + obj
                    + " по шаблону скилла (шаги 2-3), автотест не строить")]


def plan_env(_obj):
    code, text = run("env-check", "env_check.py", ["--no-compile"])
    data = {}
    try:
        data = json.loads(read(DATA / "autotest" / "ENV.json"))
    except ValueError:
        pass
    problems = data.get("problems", [])
    state = ["Статус: " + data.get("status", "?") + " · проблем " + str(len(problems))]
    state += ["- " + p.get("severity", "?") + " · " + p.get("code", "?") + " · " + p.get("message", "") for p in problems]
    work = [(p.get("code", "?"), "env-check", "режим setup: исправить проблему " + p.get("code", "?"))
            for p in problems if p.get("severity") in ("critical", "warning")]
    work.append(("Проверка", "env-check", "режим check: env_check.py с компиляцией, СТАТУС ok"))
    return state, work


def plan_frame(obj):
    code, text = run("env-update", "env_update.py", ["versions"])
    state = ["Версия фрейма сейчас:"] + ["- " + l for l in text.strip().splitlines()[:12]]
    state.append("Целевая версия: " + (obj if obj != "-" else "самая новая из release notes (MCP pvatf-docs)"))
    return state, [("Версия", "env-update", "поднять версию фрейма" + ("" if obj == "-" else " до " + obj)
                    + " (bump, по шагам скилла)"),
                   ("Компиляция", "env-update", "ошибки компиляции после обновления: env_update.py errors, правки по changelog"),
                   ("Проверка", "env-check", "режим check: env_check.py с компиляцией, СТАТУС ok")]


def plan_migration(_obj):
    m = read(DATA / "migration" / "MIGRATION-MAP.md")
    head = front(m)
    if not m or head.get("map_status") != "approved":
        return None, ["НУЖНО: карта миграции не утверждена (map_status: " + head.get("map_status", "нет карты")
                      + ") - скилл migration-map по этапам, затем одобрение карты человеком"]
    units = [u for u in table(m, "4. Юниты работ") if len(u) >= 8]
    state = ["Карта: " + rel(DATA / "migration" / "MIGRATION-MAP.md") + " · юнитов " + str(len(units))
             + " · не сделано " + str(sum(1 for u in units if u[7] != "done"))]
    passport = re.search(r"(?ms)^## 1\. Паспорт проекта\s*\n(.*?)(?=^## |\Z)", m)
    state += [l for l in (passport.group(1).strip().splitlines()[:15] if passport else [])]
    work = [(u[0] + " · " + u[2] + " · " + u[4], "migration-step", "юнит " + u[0] + " (один юнит на чат)")
            for u in units if u[7] != "done"]
    work.append(("Проверка миграции", "migration-review", "ревью миграции по скиллу"))
    return state, work


def plan_review(obj):
    name = Path(obj).stem
    plan = read(DATA / "autotest-review" / name / "REVIEW-PLAN.md")
    if not plan:
        run("autotest-review", "review.py", ["find", obj])
        plan = read(DATA / "autotest-review" / name / "REVIEW-PLAN.md")
    rows = [r for r in table(plan, "Правки") if len(r) >= 7]
    state = ["План ревью: " + rel(DATA / "autotest-review" / name / "REVIEW-PLAN.md") + " · правок " + str(len(rows))]
    state += ["- " + r[0] + " · " + r[1] + " · " + r[2] + " · " + r[3] for r in rows]
    work = [("Согласование", "autotest-review", "показать план правок человеку и записать выбор (review.py approve)")]
    work += [(r[0] + " · " + r[3][:60], "autotest-review", "правка " + r[0] + " (review.py next / mark)") for r in rows]
    work.append(("Проверка", "autotest-review", "review.py check: компиляция и REVIEW.md"))
    return state, work


def plan_markup(obj):
    scope = obj if obj != "-" else "все тест-классы проекта"
    return ["Объект разметки: " + scope, "Правила: references/markup-rules.md скилла migration-step"], \
        [("Разметка", "migration-step", "юнит типа markup для " + scope + " (агент pvatf-marker, references/markup.md)")]


def plan_deps(_obj):
    if not read(DATA / "dependency" / "DEPS.json"):
        run("dependency-review", "deps.py", ["scan"])
    findings = read(DATA / "dependency" / "FINDINGS.md")
    state = ["Скан: " + rel(DATA / "dependency" / "DEPS.json") + " · находки: " + rel(DATA / "dependency" / "FINDINGS.md")]
    state += [l for l in findings.splitlines() if l.startswith("|")][:20]
    return state, [("Проверка правил", "dependency-review", "цикл deps.py next / mark до конца списка"),
                   ("Отчёт", "dependency-review", "deps.py report -> DEPENDENCY-ANALYSIS.md")]


PLANS = {"tc-check": plan_tc_check, "env-setup": plan_env, "frame-update": plan_frame, "migration": plan_migration,
         "autotest-review": plan_review, "markup": plan_markup, "deps-review": plan_deps}


def cmd_design(args):
    t = target(args)
    if not t:
        return 2
    name, root, kind, obj = t
    if kind == "autotest":
        code, text = run("autotest-plan", "os_artifacts.py", ["design", name])
        out(text.rstrip())
        return code
    state, work = PLANS[kind](obj)
    if state is None:
        out(*work)
        return 1
    lines = ["# Design: " + name, "", "## Контекст", "- Вид: " + kind + " · объект: " + obj, "",
             "## Состояние"] + state + ["", "## План работ", "| № | Группа | Скилл | Что |", "|---|--------|-------|-----|"]
    lines += ["| " + str(i) + " | " + g.replace("|", "/") + " | " + s + " | " + w.replace("|", "/") + " |"
              for i, (g, s, w) in enumerate(work, 1)]
    lines += ["", "## Риски", "- Скилл остановился (вопрос, блокер) - apply ждёт человека, задача не отмечается.", ""]
    out("ИТОГ: design записан · вид " + kind + " · работ " + str(len(work)),
        "ФАЙЛ: " + write(root / "design.md", "\n".join(lines)))
    return 0


def cmd_tasks(args):
    t = target(args)
    if not t:
        return 2
    name, root, kind, obj = t
    if kind == "autotest":
        code, text = run("autotest-plan", "os_artifacts.py", ["tasks", name])
        out(text.rstrip())
        return code
    design = read(root / "design.md")
    if not design:
        out("НУЖНО: нет design.md - сначала артефакт design")
        return 1
    lines = ["apply-mode: single", "", "## Цель", KINDS[kind][2] + " · " + obj, ""]
    n = 0
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
    return 0


def cmd_next(args):
    """Что делать дальше по изменению: артефакт, apply или архив."""
    if not args:
        res = openspec(["list", "--json"])
        if res is None:
            out("НЕТ CLI: openspec не найден - установите по INSTALL.md пакета")
            return 2
        try:
            changes = json.loads(res[1][res[1].index("{"):]).get("changes", [])
        except ValueError:
            changes = []
        active = [c.get("name") for c in changes if c.get("status") != "complete"]
        if len(active) == 1:
            args = active
        else:
            out("ИЗМЕНЕНИЯ: " + (", ".join(active) or "нет"),
                "ДЕЙСТВИЕ: " + ("спроси человека, какое изменение продолжить" if active else "создай изменение: os_work.py new <вид> <объект>"))
            return 0
    st = status(args[0])
    if not st:
        out("НЕТ ИЗМЕНЕНИЯ: " + args[0])
        return 2
    for a in st.get("artifacts", []):
        if a.get("status") != "done":
            out("ИЗМЕНЕНИЕ: " + args[0], "ДЕЙСТВИЕ: артефакт " + a.get("id", "?"),
                "КОМАНДА: openspec instructions " + a.get("id", "?") + " --change \"" + args[0] + "\" --json - выполни поле instruction")
            return 0
    res = openspec(["instructions", "apply", "--change", args[0], "--json"])
    try:
        ap = json.loads(res[1][res[1].index("{"):]) if res else {}
    except ValueError:
        ap = {}
    prog = ap.get("progress", {})
    if prog.get("remaining", 1) > 0:
        out("ИЗМЕНЕНИЕ: " + args[0], "ДЕЙСТВИЕ: apply · задач осталось " + str(prog.get("remaining", "?")),
            "КОМАНДА: openspec instructions apply --change \"" + args[0] + "\" --json - выполни поле instruction")
        return 0
    out("ИЗМЕНЕНИЕ: " + args[0], "ДЕЙСТВИЕ: архив",
        "КОМАНДА: openspec archive " + args[0] + " --yes (или скилл openspec-de-archive-change, если стоит)")
    return 0


COMMANDS = {"new": cmd_new, "proposal": cmd_proposal, "design": cmd_design, "tasks": cmd_tasks, "next": cmd_next}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        out("Использование: os_work.py new <вид> [<объект>] | proposal | design | tasks | next <имя изменения>")
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
