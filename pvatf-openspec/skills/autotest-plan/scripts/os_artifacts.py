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
AT = "python3 .gigacode/skills/autotest-gen/scripts/at_tools.py"


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
    m = re.search(r"\*\*" + re.escape(name) + r":\*\*\s*(.+)", text)
    return m.group(1).strip() if m else "-"


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


def cmd_proposal(args):
    name, root, key = target(args)
    if not root:
        return 2
    tc = read(root / "outputs" / "TC.md")
    if not tc:
        out("НУЖНО: тест-кейс " + key + " не загружен - шаг 1 скилла autotest-plan (MCP TMS по ключу -> tc_convert.py), потом снова")
        return 1
    title = field(tc, "Название")
    text = "\n".join([
        "# Proposal: " + name, "",
        "## Зачем", "Автоматизировать тест-кейс " + key + " «" + title + "».", "",
        "## Тест-кейсы", "| Ключ TMS | Название | Источник |", "|----------|----------|----------|",
        "| " + key + " | " + title + " | " + field(tc, "Источник") + " |", "",
        "## Что меняется",
        "- Новый автотест по тест-кейсу " + key + "; классы шагов, данные и тест-класс - по design.md.", "",
        "## Вне scope",
        "- Правка тест-кейса в TMS.",
        "- Запуск теста на стенде - только с согласия человека, после apply.", ""])
    out("ИТОГ: proposal записан · ТК " + key, "ФАЙЛ: " + write(root / "proposal.md", text))
    return 0


def cmd_tc(args):
    name, root, key = target(args)
    if not root:
        return 2
    tc = read(root / "outputs" / "TC.md")
    if not tc:
        out("НУЖНО: тест-кейс " + key + " не загружен - сначала артефакт proposal")
        return 1
    code, output = run_script("autotest-plan", "tc_check.py", [key])
    status = re.search(r"СТАТУС:\s*(\w+)", output)
    status = status.group(1) if status else ("FAIL" if code == 1 else "?")
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
    if not design.is_file():
        code, text = run_script("autotest-plan", "tc_plan.py", ["build", key])
        lines = [l for l in text.splitlines() if l.split(":", 1)[0] in ("ФАЙЛ", "ШАГОВ", "ПРОВЕРИТЬ", "ОКРУЖЕНИЕ", "ЗАМЕТКА", "НЕТ TC.md", "НЕТ TC-CHECK.md")]
        out(*lines)
        if code != 0:
            return 1
        if any(l.startswith("ПРОВЕРИТЬ:") and "нет -" not in l for l in lines):
            out("НУЖНО: шаг 5 скилла autotest-plan - исправь в design.md только строки из ПРОВЕРИТЬ, потом снова")
            return 1
    code, text = run_script("autotest-plan", "tc_plan.py", ["validate", key])
    if code != 0:
        out(*[l for l in text.splitlines() if l.startswith(("ПРОБЛЕМА", "ИТОГ"))])
        out("НУЖНО: шаги 6-7 скилла autotest-plan - исправь в design.md строки ПРОБЛЕМА, потом снова (не больше 3 кругов)")
        return 1
    code, env_out = run_script("env-check", "env_tc.py", [key, "--no-compile"])
    if code != 0:
        out(*[l for l in env_out.splitlines() if l.startswith("НУЖНО:")])
        out("НУЖНО: окружение под ТК не готово - скилл env-check, режим setup " + key + ", потом снова")
        return 1
    head = front(read(design))
    out("ИТОГ: design готов · plan_status " + head.get("plan_status", "-") + " · G " + str(len(gen_rows(read(design))))
        + " · окружение готово", "ФАЙЛ: " + rel(design))
    return 0


def cmd_tasks(args):
    name, root, key = target(args)
    if not root:
        return 2
    plan = read(root / "design.md")
    if front(plan).get("plan_status") not in ("planned", "generating", "checked"):
        out("НУЖНО: design.md не готов (plan_status: " + front(plan).get("plan_status", "нет") + ") - сначала артефакт design")
        return 1
    gens = gen_rows(plan)
    test_line = next((no for no, l in enumerate(plan.splitlines(), 1) if l.startswith("test_file:")), 1)
    lines = ["apply-mode: subagents", "", "## Цель", "Автотест " + key + " по design.md.", ""]
    n = 0
    for no, g in gens:
        n += 1
        lines += ["## " + str(n) + ". " + g[0] + " · " + (g[3] if len(g) > 3 else "-"),
                  "- [ ] " + str(n) + ".1 " + g[0] + ": задание `" + AT + " next " + key + "` -> агент pvatf-generator,"
                  " ответ ok -> `" + AT + " mark " + key + " " + g[0] + " ok` (design.md:" + str(no) + ")", ""]
    n += 1
    lines += ["## " + str(n) + ". Сборка и проверка",
              "- [ ] " + str(n) + ".1 `" + AT + " assemble " + key + "` (design.md:" + str(test_line) + ")",
              "- [ ] " + str(n) + ".2 `" + AT + " check " + key + "` -> ИТОГ: находок 0 (design.md:" + str(test_line) + ")", ""]
    out("ИТОГ: tasks записан · групп " + str(n), "ФАЙЛ: " + write(root / "tasks.md", "\n".join(lines)))
    return sync(root)


def sync(root):
    """Чекбоксы tasks.md по статусам: G ok/stub в разделе 3 плана, сборка (CHECK.md), check (plan_status: checked)."""
    tasks = root / "tasks.md"
    text = read(tasks)
    if not text:
        return 0
    plan = read(root / "design.md")
    done = {g[0] for _, g in gen_rows(plan) if len(g) > 7 and g[7] in ("ok", "stub")}
    checked = front(plan).get("plan_status", "") == "checked"
    assembled = checked or "| at_tools | assemble ->" in plan
    lines, marked = [], 0
    for line in text.splitlines():
        m = re.match(r"^- \[ \] \S+ (G-\d+):", line)
        hit = (m and m.group(1) in done) or ("at_tools.py assemble" in line and assembled) \
            or ("at_tools.py check" in line and checked)
        if hit and line.startswith("- [ ]"):
            line = "- [x]" + line[5:]
            marked += 1
        lines.append(line)
    tasks.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out("СИНХРОНИЗАЦИЯ: tasks.md · отмечено сейчас " + str(marked))
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
