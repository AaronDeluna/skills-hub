#!/usr/bin/env python3
"""
Артефакты изменения OpenSpec для автотеста по тест-кейсу (пакет pvatf-openspec, вид autotest).
Запуск из корня проекта:

  python3 <скилл>/scripts/os_artifacts.py new <ключ ТК> [--task <код задачи>]  - создать изменение
  python3 <скилл>/scripts/os_artifacts.py proposal <имя изменения>            - proposal.md
  python3 <скилл>/scripts/os_artifacts.py tc <имя изменения>                  - tc/<ключ>.md
  python3 <скилл>/scripts/os_artifacts.py design <имя изменения>              - design.md
  python3 <скилл>/scripts/os_artifacts.py tasks <имя изменения>               - tasks.md

Содержимое берётся из рабочих файлов набора .gigacode/data/autotest/<ключ>/ (TC.md,
TC-CHECK.md, PLAN.md, ENV-TC.md); модель артефакты руками не пишет. Ключ ТК изменения -
строка `x-pvatf-tc:` в .openspec.yaml, вид - `x-pvatf-kind: autotest`.
Каталог изменения - из `openspec status --change <имя> --json` (changeRoot); CLI нет -
openspec/changes/<имя>.

Печатает строки ИТОГ, ФАЙЛ, НУЖНО, НАХОДКА. Код выхода: 0 - артефакт записан, 1 - нужно
действие (строки НУЖНО / НАХОДКА), 2 - неверный запуск, нет изменения или нет CLI для new.
Python 3.8+, только стандартная библиотека.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DATA = Path(".gigacode") / "data" / "autotest"
SKILLS = Path(__file__).resolve().parent.parent.parent
TIMEOUT = 600
KEY = re.compile(r"^[A-Z][A-Z0-9_]*-T?\d+$")


def out(*lines):
    sys.stdout.buffer.write(("\n".join(lines) + "\n").encode("utf-8"))


def openspec(args):
    """Запуск CLI openspec; (код, вывод) или None, если CLI нет."""
    exe = shutil.which("openspec")
    if not exe:
        return None
    try:
        r = subprocess.run([exe] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def change_root(name):
    res = openspec(["status", "--change", name, "--json"])
    if res and res[0] == 0:
        try:
            return Path(json.loads(res[1])["changeRoot"])
        except (ValueError, KeyError):
            pass
    return Path("openspec") / "changes" / name


def meta(root):
    result = {}
    f = root / ".openspec.yaml"
    if f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([\w-]+):\s*(.*?)\s*$", line)
            if m:
                result[m.group(1)] = m.group(2).strip('"\'')
    return result


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def table(text, title):
    """Строки таблицы раздела «## <title>» как списки ячеек (без шапки и разделителя)."""
    sect = re.search(r"(?ms)^## " + re.escape(title) + r"\s*\n(.*?)(?=^## |\Z)", text)
    rows = []
    for line in (sect.group(1) if sect else "").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    return rows[1:] if rows else []


def front(text):
    head = re.search(r"(?s)^---\n(.*?)\n---", text)
    result = {}
    for line in (head.group(1) if head else "").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            result[k.strip()] = v.strip()
    return result


def field(text, name):
    m = re.search(r"\*\*" + re.escape(name) + r":\*\*\s*(.+)", text)
    return m.group(1).strip() if m else "-"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return rel(path)


def rel(path):
    try:
        return str(Path(path).resolve().relative_to(Path.cwd().resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def run_script(skill, script, args):
    try:
        r = subprocess.run([sys.executable, str(SKILLS / skill / "scripts" / script)] + args,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 2, str(error)
    return r.returncode, r.stdout.decode("utf-8", "replace")


# ---------- команды ----------

def cmd_new(args):
    key = args[0] if args else ""
    task = args[args.index("--task") + 1] if "--task" in args and args.index("--task") + 1 < len(args) else ""
    if not KEY.match(key):
        out("Использование: os_artifacts.py new <ключ ТК вида ABC-T123> [--task <код задачи>]")
        return 2
    name = re.sub(r"[^a-z0-9-]+", "-", ((task + "-") if task else "") + "autotest-" + key.lower()).strip("-")
    root = Path("openspec") / "changes" / name
    if not root.is_dir():
        res = openspec(["new", "change", name])
        if res is None:
            out("НЕТ CLI: openspec не найден - установите по INSTALL.md пакета (npm install -g @fission-ai/openspec)")
            return 2
        if res[0] != 0:
            out("ОШИБКА openspec new change:", res[1].strip())
            return 2
        root = change_root(name)
    m = meta(root)
    lines = read(root / ".openspec.yaml").rstrip("\n").splitlines()
    for k, v in (("skip_specs", "true"), ("x-pvatf-kind", "autotest"), ("x-pvatf-tc", key)):
        if k not in m:
            lines.append(k + ": " + (v if k == "skip_specs" else '"' + v.replace('"', "") + '"'))
    write(root / ".openspec.yaml", "\n".join(lines) + "\n")
    out("ИЗМЕНЕНИЕ: " + name, "ТК: " + key, "ФАЙЛ: " + rel(root / ".openspec.yaml"))
    return 0


def target(args):
    if not args:
        return None, None, None
    root = change_root(args[0])
    m = meta(root)
    key = m.get("x-pvatf-tc", "")
    if not root.is_dir() or not KEY.match(key):
        out("НЕТ ИЗМЕНЕНИЯ: " + args[0] + " - создайте его: os_artifacts.py new <ключ ТК>")
        return None, None, None
    return args[0], root, key


def cmd_proposal(args):
    name, root, key = target(args)
    if not root:
        return 2
    tc = read(DATA / key / "TC.md")
    if not tc:
        out("НУЖНО: тест-кейс " + key + " не загружен - шаг 1 скилла autotest-plan (MCP TMS -> tc_convert.py), потом снова")
        return 1
    title = field(tc, "Название")
    source = field(tc, "Источник")
    text = "\n".join([
        "# Proposal: " + name, "",
        "## Зачем", "Автоматизировать тест-кейс " + key + " «" + title + "».", "",
        "## Тест-кейсы", "| Ключ TMS | Название | Источник |", "|----------|----------|----------|",
        "| " + key + " | " + title + " | " + source + " |", "",
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
    tc = read(DATA / key / "TC.md")
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
            + str(DATA / key / "TC-CHECK.md").replace("\\", "/"), "",
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
    name, root, key = target(args)
    if not root:
        return 2
    plan = read(DATA / key / "PLAN.md")
    head = front(plan)
    if head.get("plan_status") not in ("planned", "generating", "checked"):
        out("НУЖНО: план не сошёлся (plan_status: " + head.get("plan_status", "нет PLAN.md")
            + ") - шаги 4-7 скилла autotest-plan для " + key + ", потом снова")
        return 1
    code, env_out = run_script("env-check", "env_tc.py", [key, "--no-compile"])
    need = [l for l in env_out.splitlines() if l.startswith("НУЖНО:")]
    if code != 0:
        for l in need:
            out(l)
        out("НУЖНО: окружение под ТК не готово - скилл env-check, режим setup " + key + ", потом снова")
        return 1
    steps = table(plan, "2. Шаги")
    gens = table(plan, "3. Порядок генерации")
    consts = table(plan, "4. Константы")
    classes = re.search(r"(?ms)^## 6\. Классы проекта по технологиям\s*\n(.*?)(?=^## |\Z)", plan)
    env_rows = table(read(DATA / key / "ENV-TC.md"), "Окружение под ТК " + key) or []
    lines = ["# Design: " + name, "",
             "## Контекст изменения",
             "- Тест-кейс: " + key + " · план: " + str(DATA / key / "PLAN.md").replace("\\", "/"),
             "- Технологии: " + (", ".join(sorted({g[3] for g in gens if len(g) > 3})) or "-"),
             "- Стиль шагов: " + head.get("step_style", "-") + " · UI: " + head.get("ui_lib", "-"), "",
             "## Вне scope", "- Правка тест-кейса в TMS, запуск на стенде.", "",
             "## Привязка шагов ТК к коду", "| Шаг ТК | Действие | Тип | G |", "|--------|----------|-----|---|"]
    for s in steps:
        if len(s) > 10:
            lines.append("| " + " | ".join([s[0], s[1], s[3], s[10]]) + " |")
    lines += ["", "## Окружение", "Проверка: `env_tc.py " + key + "` - готово."]
    lines += ["- " + " · ".join(r) for r in env_rows if r and r[0] != "-"] or ["- всё на месте"]
    lines += ["", "## Планируемые изменения", "", "### Классы шагов"]
    for g in gens:
        if len(g) < 7:
            continue
        lines += ["#### " + g[0] + " · " + g[3],
                  "- Шаги ТК: " + g[1],
                  "- Класс шагов: " + (g[6] if g[6] not in ("", "-") else "новый класс шагов технологии в пакете steps (правило 13 autotest-rules.md)"),
                  "- Справка: " + g[5], ""]
    lines += ["### Данные", "| Имя | Значение | Где хранится | Шаг |", "|-----|----------|--------------|-----|"]
    lines += ["| " + " | ".join([c[0], c[1].replace("|", "/"), c[2], c[4]]) + " |" for c in consts if len(c) > 4] or ["| нет | - | - | - |"]
    lines += ["", "### Тест-класс",
              "#### [ADDED] `" + head.get("class", "-") + "`",
              "- Файл: `" + head.get("test_file", "-") + "`",
              "- Пакет: `" + head.get("package", "-") + "`",
              "- Базовый класс: `" + head.get("base_fqn", head.get("base_class", "-")) + "`",
              "- Шаги ТК: все, по порядку G", "",
              "### Классы проекта по технологиям", (classes.group(1).strip() if classes else "- нет"), "",
              "## Порядок и зависимости", "- G по порядку: " + (", ".join(g[0] for g in gens) or "-")
              + "; сборка тест-класса после всех G.", "",
              "## Риски", "- Шаг с заглушкой (STUB) - в итоге человеку, тест не зелёный до правки.", ""]
    out("ИТОГ: design записан · G " + str(len(gens)) + " · шагов " + str(len(steps)),
        "ФАЙЛ: " + write(root / "design.md", "\n".join(lines)))
    return 0


def cmd_tasks(args):
    name, root, key = target(args)
    if not root:
        return 2
    design = read(root / "design.md")
    if not design:
        out("НУЖНО: нет design.md - сначала артефакт design")
        return 1
    where = {}
    for no, line in enumerate(design.splitlines(), 1):
        m = re.match(r"^#### (G-\d+) · (.+)$", line)
        if m:
            where[m.group(1)] = (no, m.group(2))
    test_line = next((no for no, l in enumerate(design.splitlines(), 1) if l.startswith("### Тест-класс")), 0)
    at = "python3 .gigacode/skills/autotest-gen/scripts/at_tools.py"
    lines = ["apply-mode: subagents", "", "## Цель", "Автотест " + key + " по design.md.", ""]
    n = 0
    for gid, (no, tech) in sorted(where.items(), key=lambda x: int(x[0][2:])):
        n += 1
        lines += ["## " + str(n) + ". " + gid + " · " + tech,
                  "- [ ] " + str(n) + ".1 Задание `" + at + " next " + key + "` -> агент pvatf-generator (design.md:" + str(no) + ")",
                  "- [ ] " + str(n) + ".2 `" + at + " mark " + key + " " + gid + " ok` (design.md:" + str(no) + ")", ""]
    n += 1
    lines += ["## " + str(n) + ". Сборка и проверка",
              "- [ ] " + str(n) + ".1 `" + at + " assemble " + key + "` (design.md:" + str(test_line) + ")",
              "- [ ] " + str(n) + ".2 `" + at + " check " + key + "` -> ИТОГ: находок 0", ""]
    out("ИТОГ: tasks записан · групп " + str(n), "ФАЙЛ: " + write(root / "tasks.md", "\n".join(lines)))
    return 0


COMMANDS = {"new": cmd_new, "proposal": cmd_proposal, "tc": cmd_tc, "design": cmd_design, "tasks": cmd_tasks}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        out("Использование: os_artifacts.py new <ключ ТК> [--task <код>] | proposal | tc | design | tasks <имя изменения>")
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
