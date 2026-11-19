#!/usr/bin/env python3
"""
Проверка окружения проекта автотестов на PVATF (скилл env-check). Запуск из корня проекта:

  python3 <каталог скилла>/scripts/env_check.py               - полная проверка с компиляцией
  python3 <каталог скилла>/scripts/env_check.py --no-compile  - без компиляции (быстро)
  python3 <каталог скилла>/scripts/env_check.py --timeout 540 - свой предел времени компиляции, секунды
  python3 <каталог скилла>/scripts/env_check.py --json        - напечатать полный JSON вместо сводки
  python3 <каталог скилла>/scripts/env_check.py --release-notes <файл> - ещё сравнить версию фрейма с самой новой
      из ответа MCP get_pvat_release_notes (проблема FRAME_OUTDATED, severity info: статус не меняет)
  python3 <каталог скилла>/scripts/env_check.py --offline [--example <путь>] - MCP недоступен: самая новая версия
      фрейма из скачанных исходников фрейма (теги git) или проекта-примера (frame_versions.py offline)
  python3 <каталог скилла>/scripts/env_check.py --notes-fresh <файл> - нужен ли новый запрос release notes:
      файл записан сегодня и в нём есть номера версий -> «СВЕЖИЕ», код 0; иначе «НУЖЕН ЗАПРОС», код 1

Печатает короткую сводку (СТАТУС, проверки E1-E6, проблемы) и пишет полный JSON в
.gigacode/data/autotest/ENV.json.
Код выхода: 0 - status ok или warning, 1 - status failed, 2 - неверный запуск.
Код проекта не меняет. Нужен Python 3.8+, сторонних библиотек нет.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frame_versions as frame_versions_module  # noqa: E402

OUT_DIR = Path(".gigacode") / "data" / "autotest"
OUT_FILE = OUT_DIR / "ENV.json"
SKIP_DIRS = {".git", ".gigacode", ".idea", ".gradle", "target", "build", "out", "node_modules"}

# Что ищем в файлах сборки. Список - из пакета генерации автотестов; имя ищется как подстрока.
MANDATORY_DEPS = ["environment-junit5", "allure2"]
RECOMMENDED_DEPS = ["allure-junit5", "aspectjweaver"]
# логирование на фрейме: простой логгер SLF4J - две зависимости и файл настроек (code-rules.md, MR-43)
LOGGING_DEPS = ["slf4j-simple", "slf4j-api"]
LOGGING_FILE = "simplelogger.properties"
RECOMMENDED_PLUGINS = ["maven-surefire-plugin", "allure-maven", "maven-resources-plugin"]
REQUIRED_PROPERTY_KEY = "perfeccionista.attachment.dir"
DEFAULT_TIMEOUT = 540


def main():
    args = sys.argv[1:]
    if args and args[0] == "--notes-fresh":
        return notes_fresh(args[1:])
    compile_on = True
    as_json = False
    timeout = DEFAULT_TIMEOUT
    notes = None
    offline = False
    examples = []
    i = 0
    while i < len(args):
        if args[i] == "--no-compile":
            compile_on = False
        elif args[i] == "--json":
            as_json = True
        elif args[i] == "--offline":
            offline = True
        elif args[i] == "--example" and i + 1 < len(args):
            examples.append(args[i + 1])
            i += 1
        elif args[i] == "--release-notes" and i + 1 < len(args):
            notes = args[i + 1]
            i += 1
        elif args[i] == "--timeout" and i + 1 < len(args) and args[i + 1].isdigit():
            timeout = int(args[i + 1])
            i += 1
        else:
            print("Использование: env_check.py [--no-compile] [--timeout <секунды>] [--json] [--release-notes <файл> | --offline [--example <путь>]]")
            return 2
        i += 1

    root = Path(".").resolve()
    report = {
        "status": "ok",
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "project": {"root": str(root)},
        "frame_versions": [],
        "checks": [],
        "problems": [],
        "compile": {"executed": False, "command": None, "exit_code": None, "status": "skipped", "errors": []},
    }
    build_files = find_build_files(root)
    tool = build_tool(root)
    report["project"]["build_tool"] = tool
    report["project"]["build_files"] = [rel(root, f) for f in build_files]

    if tool == "-":
        problem(report, "critical", "BUILD_FILE_MISSING", "В корне проекта нет pom.xml, build.gradle или build.gradle.kts",
                "Запускай скрипт из корня проекта автотестов")
        check(report, "E1", "файл сборки", "failed", "не найден")
    else:
        check(report, "E1", "файл сборки", "ok", tool + ": " + ", ".join(report["project"]["build_files"][:5]))

    build_text = "\n".join(read(f) for f in build_files)
    java_files = find_files(root, ".java") + find_files(root, ".kt")
    test_roots = find_test_roots(root)
    report["project"]["test_roots"] = [rel(root, d) for d in test_roots]
    report["project"]["modules"] = modules(root, tool)

    check_structure(report, test_roots)
    check_dependencies(report, build_text, tool)
    check_tc_modules(report, build_text)
    check_configuration(report, root, java_files)
    check_plugins(report, build_text, tool)
    check_logging(report, root, build_text, tool)
    describe_tests(report, root, java_files, test_roots, build_text)
    report["frame_versions"] = frame_versions(root, build_files)
    if notes is not None:
        check_outdated(report, notes)
    elif offline:
        check_offline(report, examples)

    command = compile_command(root, tool)
    report["project"]["compile_command"] = " ".join(command) if command else "-"
    report["project"]["compile_argv"] = command
    if tool == "-":
        check(report, "E6", "компиляция тестов", "warning", "не запускалась: нет файла сборки")
    else:
        if compile_on:
            run_compile(report, command, timeout)
        else:
            check(report, "E6", "компиляция тестов", "warning", "не запускалась (--no-compile)")
            problem(report, "warning", "COMPILE_SKIPPED", "Компиляция не запускалась", "Запусти скрипт без --no-compile")

    severities = {p["severity"] for p in report["problems"]}
    report["status"] = "failed" if "critical" in severities else ("warning" if "warning" in severities else "ok")
    text = json.dumps(report, ensure_ascii=False, indent=2)
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        OUT_FILE.write_text(text + "\n", encoding="utf-8")
    except OSError as error:
        report["problems"].append({"severity": "warning", "code": "REPORT_NOT_WRITTEN",
                                   "message": "Не записан " + str(OUT_FILE), "details": str(error)})
        text = json.dumps(report, ensure_ascii=False, indent=2)
    out(text if as_json else summary(report))
    return 1 if report["status"] == "failed" else 0


def notes_fresh(args):
    """Сохранённые заголовки release notes годятся без нового запроса MCP: записаны сегодня, есть номера версий."""
    if len(args) != 1:
        print("Использование: env_check.py --notes-fresh <файл>")
        return 2
    path = Path(args[0])
    if not path.is_file():
        print("RELEASE NOTES: НУЖЕН ЗАПРОС - файла " + args[0] + " нет")
        return 1
    day = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    latest, _ = frame_versions_module.newest(read(path))
    if day != datetime.now().strftime("%Y-%m-%d") or not latest:
        print("RELEASE NOTES: НУЖЕН ЗАПРОС - файл от " + day + ("" if latest else ", номеров версий нет"))
        return 1
    print("RELEASE NOTES: СВЕЖИЕ - файл от " + day + ", самая новая " + latest + "; MCP не вызывай")
    return 0


def summary(report):
    project = report["project"]
    lines = ["СТАТУС: " + report["status"],
             "ФАЙЛ: " + str(OUT_FILE).replace("\\", "/"),
             "ПРОЕКТ: сборка %s · модулей %d · тест-классов %s · базовый пакет %s · UI %s · стиль шагов %s" % (
                 project.get("build_tool", "-"), len(project.get("modules", [])), project.get("test_classes", "-"),
                 project.get("base_package", "-"), project.get("ui_lib", "-"), project.get("step_style", "-")),
             "КОМПИЛЯЦИЯ: " + project.get("compile_command", "-") + " -> " + report["compile"]["status"]]
    if "latest_version" in report:
        lines.append("САМАЯ НОВАЯ: " + report["latest_version"]
                     + (" (" + report["latest_source"] + ")" if report.get("latest_source") else ""))
    for version in report["frame_versions"]:
        lines.append("ВЕРСИЯ: %s = %s (%s:%d)" % (version["name"], version["value"], version["file"], version["line"]))
    for item in report["checks"]:
        lines.append("%s · %s · %s · %s" % (item["id"], item["name"], item["status"], item["details"]))
    for item in report["problems"]:
        lines.append("ПРОБЛЕМА: %s · %s · %s · %s" % (item["severity"], item["code"], item["message"], item["details"]))
    for line in report["compile"]["errors"][:15]:
        lines.append("ОШИБКА КОМПИЛЯЦИИ: " + line)
    return "\n".join(lines)


# ---------- проверки ----------

def check_structure(report, test_roots):
    if test_roots:
        check(report, "E2", "каталог тестов", "ok", ", ".join(report["project"]["test_roots"][:5]))
    else:
        check(report, "E2", "каталог тестов", "failed", "нет ни одного src/test/java или src/test/kotlin")
        problem(report, "critical", "TEST_ROOT_MISSING", "В проекте нет каталога src/test/java",
                "Создай src/test/java в модуле автотестов")


def check_dependencies(report, build_text, tool):
    if tool == "-":
        check(report, "E3", "зависимости фрейма", "failed", "нет файла сборки")
        return
    found = {}
    missing_mandatory = []
    missing_recommended = []
    for dep in MANDATORY_DEPS + RECOMMENDED_DEPS:
        if dep in build_text:
            found[dep] = dependency_version(build_text, dep) or "версия задана не рядом (BOM, parent или свойство)"
        elif dep in MANDATORY_DEPS:
            missing_mandatory.append(dep)
        else:
            missing_recommended.append(dep)
    report["project"]["dependencies"] = found
    if missing_mandatory:
        problem(report, "critical", "MANDATORY_DEPENDENCIES_MISSING", "Нет обязательных зависимостей фрейма",
                ", ".join(missing_mandatory))
        check(report, "E3", "зависимости фрейма", "failed", "нет обязательных: " + ", ".join(missing_mandatory))
    elif missing_recommended:
        problem(report, "warning", "RECOMMENDED_DEPENDENCIES_MISSING", "Нет рекомендуемых зависимостей",
                ", ".join(missing_recommended))
        check(report, "E3", "зависимости фрейма", "warning", "нет рекомендуемых: " + ", ".join(missing_recommended))
    else:
        check(report, "E3", "зависимости фрейма", "ok", "обязательные и рекомендуемые найдены")


def check_tc_modules(report, build_text):
    """Раздел 8 «Окружение под ТК» незаконченных планов: технология, слов которой нет в artifactId зависимостей фрейма."""
    low = frame_versions_module.framework_artifacts(build_text)
    missing = []
    for plan in sorted(OUT_DIR.glob("*/PLAN.md")) if OUT_DIR.is_dir() else []:
        text = read(plan)
        if re.search(r"(?m)^plan_status:\s*checked", text):
            continue
        sect = re.search(r"(?ms)^## 8\. Окружение под ТК\s*\n(.*?)(?=^## |\Z)", text)
        for line in (sect.group(1) if sect else "").split("\n"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 6 or cells[1] in ("Метка", "-") or set(cells[0]) <= set("-:") or cells[2] == "RECOMMENDED":
                continue
            words = [w.strip() for w in cells[4].split(",") if w.strip() not in ("", "-")]
            if words and low and not any(w in low for w in words):
                missing.append(plan.parent.name + ": " + cells[0])
    report["project"]["tc_modules_missing"] = missing
    if missing:
        problem(report, "warning", "TC_MODULES_MISSING", "В сборке нет модулей фрейма под технологии тест-кейсов",
                "; ".join(missing[:10]))


def check_offline(report, examples):
    """MCP недоступен: версия из исходников фрейма или проекта-примера. Не нашлась -> FRAME_VERSION_NOT_FOUND."""
    rows = frame_versions_module.offline(examples)
    best = next((r for r in rows if r[2] and r[0] != "perfeccionista"), None)
    if not best:
        report["latest_version"] = "-"
        problem(report, "warning", "FRAME_VERSION_NOT_FOUND", "Версия фрейма не найдена: MCP недоступен, исходников фрейма "
                "и проекта-примера с версией нет", "нужна версия фрейма от человека")
        return
    report["latest_version"] = best[2]
    report["latest_source"] = "без MCP: " + best[0] + " " + best[1] + " (" + best[3] + ")"
    key = frame_versions_module.version_key
    current = [v["value"] for v in report["frame_versions"] if frame_versions_module.VERSION.match(str(v["value"]))]
    unknown = sorted({v for v in current if key(v) > key(best[2])})
    if unknown:
        problem(report, "warning", "FRAME_VERSION_UNKNOWN", "Версии фрейма " + ", ".join(unknown)
                + " нет в источниках, она новее самой новой " + best[2], "поставь самую новую: " + best[2])


def check_outdated(report, notes):
    """Версия фрейма в сборке против самой новой из release notes. Отстаёт -> FRAME_OUTDATED (info)."""
    latest, known = frame_versions_module.newest(read(Path(notes)), allow_snapshot=True)
    stable, _ = frame_versions_module.newest(read(Path(notes)))
    latest = stable or latest
    report["latest_version"] = latest or "-"
    if not latest:
        problem(report, "info", "RELEASE_NOTES_EMPTY", "В release notes нет номеров версий", notes)
        return
    current = [v["value"] for v in report["frame_versions"] if frame_versions_module.VERSION.match(str(v["value"]))]
    key = frame_versions_module.version_key
    unknown = sorted({v for v in current if v not in known and key(v) > key(latest)})
    if unknown:
        problem(report, "warning", "FRAME_VERSION_UNKNOWN", "Версии фрейма " + ", ".join(unknown)
                + " нет в release notes, она новее самой новой " + latest, "поставь самую новую из release notes: " + latest)
    old = sorted({v for v in current if frame_versions_module.version_key(v) < frame_versions_module.version_key(latest)})
    if old:
        problem(report, "info", "FRAME_OUTDATED", "Версия фрейма " + ", ".join(old) + ", самая новая " + latest,
                "обновление - /orchestrator обнови окружение (env-update)")


def check_configuration(report, root, java_files):
    env_configs = [f for f in java_files if f.name.endswith("EnvironmentConfiguration.java")
                   or f.name.endswith("EnvironmentConfiguration.kt")]
    stash_configs = [f for f in java_files if f.stem == "AllureDataSourceServiceConfiguration"]
    properties = [f for f in find_named(root, "perfeccionista.properties")]
    report["project"]["environment_configurations"] = [rel(root, f) for f in env_configs]
    report["project"]["properties_files"] = [rel(root, f) for f in properties]
    failed = False
    warned = False
    if not env_configs:
        failed = True
        problem(report, "critical", "ENVIRONMENT_CONFIGURATION_MISSING",
                "Нет класса конфигурации окружения (*EnvironmentConfiguration)",
                "Искал по всему проекту файл, имя которого кончается на EnvironmentConfiguration")
    if not stash_configs:
        warned = True
        problem(report, "warning", "STASH_CONFIGURATION_MISSING",
                "Нет класса AllureDataSourceServiceConfiguration",
                "Нужен, если тест передаёт данные между шагами через Stash")
    if not properties:
        failed = True
        problem(report, "critical", "PERFECCIONISTA_PROPERTIES_MISSING", "Нет файла perfeccionista.properties",
                "Искал в каталогах resources всех модулей")
    elif not any(REQUIRED_PROPERTY_KEY in read(f) for f in properties):
        failed = True
        problem(report, "critical", "PERFECCIONISTA_REQUIRED_KEY_MISSING",
                "В perfeccionista.properties нет ключа " + REQUIRED_PROPERTY_KEY, rel(root, properties[0]))
    status = "failed" if failed else ("warning" if warned else "ok")
    details = "конфигурация окружения: %d, perfeccionista.properties: %d" % (len(env_configs), len(properties))
    check(report, "E4", "конфигурация фрейма", status, details)


def check_plugins(report, build_text, tool):
    if tool != "Maven":
        check(report, "E5", "плагины Maven", "skipped", "проект не Maven")
        return
    missing = [p for p in RECOMMENDED_PLUGINS if p not in build_text]
    if missing:
        problem(report, "warning", "MAVEN_PLUGINS_MISSING", "Нет рекомендуемых плагинов Maven", ", ".join(missing))
        check(report, "E5", "плагины Maven", "warning", "нет: " + ", ".join(missing))
    else:
        check(report, "E5", "плагины Maven", "ok", "найдены")


def check_logging(report, root, build_text, tool):
    """Логирование: slf4j-simple и slf4j-api в сборке и simplelogger.properties в ресурсах тестов."""
    if tool == "-":
        return
    missing = [d for d in LOGGING_DEPS if d not in build_text]
    missing += logging_files_missing(root)
    report["project"]["logging_missing"] = missing
    if missing:
        problem(report, "warning", "LOGGING_MISSING", "Логирование фрейма не настроено", ", ".join(missing))


def logging_files_missing(root):
    """simplelogger.properties нужен в ресурсах тестов каждого модуля с src/test/java."""
    roots = find_test_roots(root)
    if not roots:
        return [] if find_named(root, LOGGING_FILE) else [LOGGING_FILE]
    return [rel(root, d.parent / "resources" / LOGGING_FILE) for d in roots
            if not (d.parent / "resources" / LOGGING_FILE).is_file()]


def describe_tests(report, root, java_files, test_roots, build_text):
    """Паспорт тестов: сколько классов, базовый пакет, базовые классы, библиотека UI, стиль шагов."""
    test_files = [f for f in java_files if any(is_inside(f, d) for d in test_roots)]
    packages = Counter()
    test_classes = 0
    flow = 0
    steps = 0
    base_classes = []
    for f in test_files:
        text = read(f)
        if re.search(r"@(Test|ParameterizedTest)\b", text):
            test_classes += 1
            match = re.search(r"^\s*package\s+([\w.]+)", text, flags=re.M)
            if match:
                packages[match.group(1)] += 1
        if "FlowRunner" in text or "flowRunnerFor" in text:
            flow += 1
        if re.search(r"@Step\b", text):
            steps += 1
        if re.match(r"(Base|Abstract)\w*Test\w*$", f.stem) or re.match(r"\w*(TestBase|BaseTest)$", f.stem):
            base_classes.append(rel(root, f))
    report["project"]["test_classes"] = test_classes
    report["project"]["base_package"] = common_package(list(packages.keys()))
    init = read(OUT_DIR / "ENV-INIT.md")
    root_match = re.search(r"(?m)^- Корень пакетов: ([\w.]+)", init)
    style_match = re.search(r"(?m)^- Стиль шагов: (steps|flow)", init)
    # новый проект (каркас init): тест-классы - в <корень>.tests, иначе - пакет существующих тестов
    report["project"]["root_package"] = root_match.group(1) if root_match else "-"
    report["project"]["test_package"] = (root_match.group(1) + ".tests") if root_match else report["project"]["base_package"]
    report["project"]["base_test_classes"] = base_classes[:10]
    lowered = build_text.lower()
    libs = [name for name in ("playwright", "selenide") if name in lowered]
    report["project"]["ui_lib"] = libs[0] if len(libs) == 1 else ("playwright+selenide" if libs else "-")
    report["project"]["step_style"] = "flow" if flow and flow >= steps else ("steps" if steps else
                                     (style_match.group(1) if style_match else "plain"))


def run_compile(report, command, timeout):
    info = report["compile"]
    info["command"] = " ".join(command)
    if shutil.which(command[0]) is None and not Path(command[0]).exists():
        info["status"] = "failed"
        problem(report, "critical", "BUILD_TOOL_NOT_FOUND", "Не найдена команда " + command[0],
                "Установи её или добавь в PATH")
        check(report, "E6", "компиляция тестов", "failed", "нет команды " + command[0])
        return
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired:
        info.update({"executed": True, "status": "failed"})
        problem(report, "critical", "COMPILE_TIMEOUT", "Компиляция не уложилась в %d секунд" % timeout,
                "Повтори ту же команду (не больше 2 раз): сборка продолжит со скачанного; снова таймаут - проверь доступ к репозиторию зависимостей")
        check(report, "E6", "компиляция тестов", "failed", "таймаут %d c" % timeout)
        return
    except OSError as error:
        info["status"] = "failed"
        problem(report, "critical", "COMPILE_NOT_STARTED", "Компиляция не запустилась", str(error))
        check(report, "E6", "компиляция тестов", "failed", str(error))
        return
    output = result.stdout.decode("utf-8", errors="replace")
    info.update({"executed": True, "exit_code": result.returncode})
    if result.returncode == 0:
        info["status"] = "ok"
        check(report, "E6", "компиляция тестов", "ok", info["command"])
        return
    info["status"] = "failed"
    errors = [line.strip() for line in output.splitlines()
              if re.search(r"\bERROR\b|error:|FAILED|Could not|cannot find symbol", line)]
    info["errors"] = (errors or output.splitlines()[-30:])[:40]
    problem(report, "critical", "COMPILE_FAILED", "Проект не компилируется: " + info["command"],
            "первые ошибки - в поле compile.errors")
    check(report, "E6", "компиляция тестов", "failed", "код выхода %d" % result.returncode)


# ---------- сборка ----------

def build_tool(root):
    if (root / "pom.xml").exists():
        return "Maven"
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        return "Gradle"
    return "-"


def compile_command(root, tool):
    windows = os.name == "nt"
    if tool == "Maven":
        wrapper = "mvnw.cmd" if windows else "./mvnw"
        return [wrapper_path(root, wrapper) if (root / wrapper).exists() else tool_path("mvn"), "-q", "-DskipTests", "test-compile"]
    if tool == "Gradle":
        wrapper = "gradlew.bat" if windows else "./gradlew"
        return [wrapper_path(root, wrapper) if (root / wrapper).exists() else tool_path("gradle"), "-q", "testClasses"]
    return []


def wrapper_path(root, wrapper):
    """Обёртка в корне: на Windows - полный путь к mvnw.cmd / gradlew.bat, иначе ./mvnw как есть."""
    return str(root / wrapper) if os.name == "nt" else wrapper


def tool_path(name):
    """Полный путь к команде сборки: на Windows mvn - это mvn.cmd, и без полного пути Python его не запустит
    (WinError 2). Не нашлась - имя как есть, проверка E6 скажет BUILD_TOOL_NOT_FOUND."""
    return shutil.which(name) or name


def modules(root, tool):
    if tool == "Maven":
        return re.findall(r"<module>\s*([^<\s]+)\s*</module>", read(root / "pom.xml"))
    if tool == "Gradle":
        text = read(root / "settings.gradle") + read(root / "settings.gradle.kts")
        return [m.strip(":").replace(":", "/") for m in re.findall(r"['\"](:?[\w\-:./]+)['\"]", " ".join(
            re.findall(r"include\s*\(?([^\n)]*)", text)))]
    return []


def find_build_files(root):
    names = {"pom.xml", "build.gradle", "build.gradle.kts", "gradle.properties", "libs.versions.toml"}
    return [f for f in walk(root) if f.name in names]


def frame_versions(root, build_files):
    """Где в файлах сборки объявлена версия фрейма (общий модуль frame_versions.py)."""
    return frame_versions_module.declarations(root)


def dependency_version(text, artifact):
    match = re.search(r"<artifactId>\s*" + re.escape(artifact) + r"\s*</artifactId>\s*<version>\s*([^<\s]+)\s*</version>", text)
    if match:
        return match.group(1)
    match = re.search(re.escape(artifact) + r":([\w.\-$\{\}]+)['\"]", text)
    return match.group(1) if match else None


# ---------- файлы ----------

def walk(root):
    result = []
    for current, dirs, files in os.walk(str(root)):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            result.append(Path(current) / name)
    return result


def find_files(root, suffix):
    return [f for f in walk(root) if f.name.endswith(suffix)]


def find_named(root, name):
    return [f for f in walk(root) if f.name == name]


def find_test_roots(root):
    roots = []
    for current, dirs, _files in os.walk(str(root)):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        path = Path(current)
        if path.name in ("java", "kotlin") and path.parent.name == "test" and path.parent.parent.name == "src":
            roots.append(path)
    return sorted(roots)


def is_inside(path, folder):
    try:
        path.relative_to(folder)
        return True
    except ValueError:
        return False


def common_package(packages):
    if not packages:
        return "-"
    parts = [p.split(".") for p in packages]
    prefix = []
    for group in zip(*parts):
        if len(set(group)) == 1:
            prefix.append(group[0])
        else:
            break
    return ".".join(prefix) if prefix else "-"


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def rel(root, path):
    try:
        return str(Path(path).resolve().relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def check(report, check_id, name, status, details):
    report["checks"].append({"id": check_id, "name": name, "status": status, "details": details})


def problem(report, severity, code, message, details):
    report["problems"].append({"severity": severity, "code": code, "message": message, "details": details})


def out(text):
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))


if __name__ == "__main__":
    sys.exit(main())
