#!/usr/bin/env python3
"""
Проверка окружения проекта автотестов на PVATF (скилл env-check). Запуск из корня проекта:

  python3 <каталог скилла>/scripts/env_check.py               - полная проверка с компиляцией
  python3 <каталог скилла>/scripts/env_check.py --no-compile  - без компиляции (быстро)
  python3 <каталог скилла>/scripts/env_check.py --timeout 900 - свой предел времени компиляции, секунды
  python3 <каталог скилла>/scripts/env_check.py --json        - напечатать полный JSON вместо сводки

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
RECOMMENDED_DEPS = ["slf4j-api", "slf4j-simple", "allure-junit5", "aspectjweaver"]
RECOMMENDED_PLUGINS = ["maven-surefire-plugin", "allure-maven", "maven-resources-plugin"]
REQUIRED_PROPERTY_KEY = "perfeccionista.attachment.dir"
DEFAULT_TIMEOUT = 600


def main():
    args = sys.argv[1:]
    compile_on = True
    as_json = False
    timeout = DEFAULT_TIMEOUT
    i = 0
    while i < len(args):
        if args[i] == "--no-compile":
            compile_on = False
        elif args[i] == "--json":
            as_json = True
        elif args[i] == "--timeout" and i + 1 < len(args) and args[i + 1].isdigit():
            timeout = int(args[i + 1])
            i += 1
        else:
            print("Использование: env_check.py [--no-compile] [--timeout <секунды>] [--json]")
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
    check_configuration(report, root, java_files)
    check_plugins(report, build_text, tool)
    describe_tests(report, root, java_files, test_roots, build_text)
    report["frame_versions"] = frame_versions(root, build_files)

    command = compile_command(root, tool)
    report["project"]["compile_command"] = " ".join(command) if command else "-"
    report["project"]["compile_argv"] = command
    if tool != "-":
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


def summary(report):
    project = report["project"]
    lines = ["СТАТУС: " + report["status"],
             "ФАЙЛ: " + str(OUT_FILE).replace("\\", "/"),
             "ПРОЕКТ: сборка %s · модулей %d · тест-классов %s · базовый пакет %s · UI %s · стиль шагов %s" % (
                 project.get("build_tool", "-"), len(project.get("modules", [])), project.get("test_classes", "-"),
                 project.get("base_package", "-"), project.get("ui_lib", "-"), project.get("step_style", "-")),
             "КОМПИЛЯЦИЯ: " + project.get("compile_command", "-") + " -> " + report["compile"]["status"]]
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
    report["project"]["base_test_classes"] = base_classes[:10]
    lowered = build_text.lower()
    libs = [name for name in ("playwright", "selenide") if name in lowered]
    report["project"]["ui_lib"] = libs[0] if len(libs) == 1 else ("playwright+selenide" if libs else "-")
    report["project"]["step_style"] = "flow" if flow and flow >= steps else ("steps" if steps else "plain")


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
                "Запусти с --timeout <больше секунд> или проверь доступ к репозиторию зависимостей")
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
        return [wrapper if (root / wrapper).exists() else "mvn", "-q", "-DskipTests", "test-compile"]
    if tool == "Gradle":
        wrapper = "gradlew.bat" if windows else "./gradlew"
        return [wrapper if (root / wrapper).exists() else "gradle", "-q", "testClasses"]
    return []


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
