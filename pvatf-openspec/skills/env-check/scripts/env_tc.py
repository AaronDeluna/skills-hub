#!/usr/bin/env python3
"""
Окружение под тест-кейс (скилл env-check, режим setup с ключом ТК). Запуск из корня проекта:

  python3 <каталог скилла>/scripts/env_tc.py <ключ ТК>               - проверка с компиляцией
  python3 <каталог скилла>/scripts/env_tc.py <ключ ТК> --no-compile  - без компиляции

Читает план автотеста - design.md изменения (раздел 8 «Окружение под ТК») и TC.md (колонки
«Действие» и «Тестовые данные») и сверяет с проектом:
- модуль фрейма под каждую технологию ТК есть в файлах сборки (слова из раздела 8 ищутся в artifactId
  зависимостей фрейма, groupId с маркером фрейма; файлов сборки нет -> проверка не делается, как в
  env_check.py и tc_plan.py);
- драйвер JDBC под каждый адрес jdbc:<вендор> из ТК есть в файлах сборки;
- allure-junit5 есть в файлах сборки (тест-класс несёт @TmsLink);
- логирование: slf4j-simple и slf4j-api в сборке, simplelogger.properties в ресурсах;
- ТК с REST: класс `extends DefaultRestServiceConfiguration` с фильтром AllureRestAssured есть в проекте;
- сервис фрейма под технологию ТК зарегистрирован в классе конфигурации окружения:
  ConfiguredServiceHolder.of(<Сервис>.class, ...) в getServiceConfigurations() (комментарии не в счёт),
  имя сервиса содержит слово технологии из SERVICE_WORDS. Метки без слова в SERVICE_WORDS (ui, mobile,
  graphql, openshift, sessions, sup, abyss) скрипт не проверяет: имени их сервиса в эталоне нет,
  регистрацию для них агент делает по ответу документации;
- каждое значение подключения из ТК (адрес REST-клиента, адрес, пользователь и пароль БД,
  логин и пароль пользователя) записано в файл настроек (src/test/resources) или в класс *Configuration;
- тесты компилируются (команда из env_check.py).
Имена ключей настроек и классов скрипт не знает и не проверяет - их даёт документация фрейма.

Печатает строки НУЖНО и итог, пишет .gigacode/data/autotest/<ключ>/ENV-TC.md.
Код выхода: 0 - окружение готово, 1 - не готово, 2 - неверный запуск или нет плана.
Код проекта не меняет. Python 3.8+, только стандартная библиотека.
"""
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_check  # noqa: E402 - тот же каталог
import frame_versions  # noqa: E402 - тот же каталог (копия shared/scripts)

OUT_DIR = Path(".gigacode") / "data" / "autotest"
TIMEOUT = 540
# вендор из jdbc:<вендор>: -> слово, которое ищется в файлах сборки (артефакт драйвера)
DRIVER_WORDS = {"postgresql": "postgresql", "oracle": "ojdbc", "sqlserver": "mssql-jdbc", "mysql": "mysql",
                "mariadb": "mariadb", "h2": "h2", "db2": "db2", "clickhouse": "clickhouse"}
URL = re.compile(r"https?://[^\s;,)\]|<>\"']+")
JDBC = re.compile(r"jdbc:[^\s;,)\]|<>\"']+")
CONFIG_SUFFIXES = (".properties", ".yml", ".yaml", ".conf", ".json")
# метка технологии (раздел 8 плана) -> слово в имени сервиса фрейма (RestService, DatabaseService, KafkaService ...),
# имена - из ApiEnvironmentConfiguration проекта-примера фрейма.
# Метки без слова скрипт не проверяет. DataSourceService - это Stash, не БД: слово БД - database.
SERVICE_WORDS = {"rest": "rest", "db": "database", "kafka": "kafka", "opensearch": "opensearch",
                 "websocket": "websocket", "grpc": "grpc", "sbermock": "sbermock", "toggler": "toggler", "metrics": "metric",
                 "launcher": "launcher", "fixtures": "fixture", "audit": "audit", "journals": "journal",
                 "dataconverter": "dataconverter", "testcontainers": "container", "value": "value",
                 "timeouts": "timeouts", "invocation": "invocation"}
HOLDER = re.compile(r"ConfiguredServiceHolder\s*\.\s*of\s*\(\s*(?:[\w.]+\.)?(\w+)\s*\.\s*class")


def main(args):
    compile_on = "--no-compile" not in args
    keys = [a for a in args if not a.startswith("--")]
    if len(keys) != 1 or len(args) - len(keys) > (0 if compile_on else 1):
        print("Использование: env_tc.py <ключ ТК> [--no-compile]")
        return 2
    key = keys[0]
    plan_file = env_check.pp.plan_file(key, create=False)
    if not plan_file.is_file():
        print("НЕТ ПЛАНА: " + str(plan_file).replace("\\", "/") + " - сначала autotest-plan")
        return 2
    root = Path(".").resolve()
    raw_build = "\n".join(env_check.read(f) for f in env_check.find_build_files(root))
    build_text = raw_build.lower()
    frame_artifacts = frame_versions.framework_artifacts(raw_build)
    need = []
    techs = tc_technologies(env_check.read(plan_file))
    for tech, _, words in techs:
        if words and raw_build.strip() and not any(w in frame_artifacts for w in words):
            need.append(("модуль", tech, "слова в artifactId фрейма: " + ", ".join(words)))
    data = tc_data(env_check.read(env_check.pp.autotest_dir(key, create=False) / "TC.md"))
    for vendor in sorted({d["vendor"] for d in data["db"]}):
        word = DRIVER_WORDS.get(vendor, vendor)
        if word not in build_text:
            need.append(("драйвер", "jdbc:" + vendor, "слово в сборке: " + word))
    log_missing = [d for d in env_check.LOGGING_DEPS if d not in build_text]
    log_missing += env_check.logging_files_missing(root)
    if log_missing:
        need.append(("логирование", ", ".join(log_missing), "simplelogger.properties и slf4j-simple + slf4j-api"))
    if "allure-junit5" not in build_text:
        need.append(("allure", "allure-junit5", "тест-класс несёт @TmsLink"))
    java_files = [f for f in env_check.walk(root) if f.suffix in (".java", ".kt")]
    if any(label == "rest" for _, label, _ in techs) and not any(
            re.search(r"extends\s+DefaultRestServiceConfiguration\b", t) and "AllureRestAssured" in t
            for t in (env_check.read(f) for f in java_files)):
        need.append(("allure-rest", "Allure2RestServiceConfiguration",
                     "класс настройки REST с AllureRestAssured - рецепт setup.md, раздел 3"))
    services = registered_services(root)
    for tech, label, _ in techs:
        word = SERVICE_WORDS.get(label)
        if word and not any(word in s for s in services):
            need.append(("сервис", tech, "нет ConfiguredServiceHolder.of(<сервис со словом %s>.class, ...) "
                                         "в классе конфигурации окружения" % word))
    stored = stored_text(root)
    for name, value in values(data):
        if value not in stored:
            need.append(("значение", name, value))
    compile_status = "skipped"
    if compile_on:
        compile_status = run_compile(root)
        if compile_status != "ok":
            need.append(("компиляция", compile_status, "тесты не компилируются"))
    ready = not need
    out_file = env_check.pp.autotest_dir(key, create=False) / "ENV-TC.md"
    written = write_report(out_file, key, ready, need, compile_status)
    lines = ["ТК: " + key]
    lines += ["НУЖНО: %s · %s · %s" % item for item in need]
    lines.append("КОМПИЛЯЦИЯ: " + compile_status)
    if not written:
        lines.append("НЕ ЗАПИСАН: " + str(out_file).replace("\\", "/") + " - без него генерация не начнётся")
        ready = False
    lines.append("ОКРУЖЕНИЕ ТК: " + ("готово" if ready else "не готово (НУЖНО %d)" % len(need)))
    lines.append("ФАЙЛ: " + str(out_file).replace("\\", "/"))
    sys.stdout.buffer.write(("\n".join(lines) + "\n").encode("utf-8"))
    return 0 if ready else 1


def tc_technologies(plan):
    """Раздел 8 плана: [(технология, метка, [слова в сборке])], кроме строк RECOMMENDED."""
    sect = re.search(r"(?ms)^## 8\. Окружение под ТК\s*\n(.*?)(?=^## |\Z)", plan)
    result = []
    for line in (sect.group(1) if sect else "").split("\n"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[1] in ("Метка", "-") or set(cells[0]) <= set("-:") or cells[2] == "RECOMMENDED":
            continue
        words = [w.strip().lower() for w in cells[4].split(",") if w.strip() not in ("", "-")]
        result.append((cells[0], cells[1], words))
    return result


def tc_data(tc):
    """Значения подключения из колонок «Действие» и «Тестовые данные» таблицы шагов TC.md."""
    data = {"rest": [], "db": [], "user": []}
    for line in tc.split("\n"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        text = cells[1] + " ; " + cells[2]
        for match in JDBC.finditer(text):
            url = match.group(0).rstrip(".")
            vendor = url.split(":")[1].lower() if url.count(":") >= 2 else "-"
            name = re.search(r"(?:БД|база|базе|database|db)\s+([\w\-]+)", text, flags=re.I)
            data["db"].append({"name": name.group(1) if name else url.rstrip("/").split("/")[-1].split("?")[0],
                               "url": url, "vendor": vendor,
                               "user": word_after(text, ("пользователь", "user", "username")),
                               "password": word_after(text, ("пароль", "password"))})
        for match in URL.finditer(text):
            url = match.group(0).rstrip(".")
            before = text[:match.start()]
            name = re.search(r"([A-Za-z][\w\-]*)\s*[:=]\s*$", before)
            data["rest"].append({"name": name.group(1) if name else "-", "url": url})
        if not JDBC.search(text):
            login = word_after(text, ("логин", "login"))
            if login:
                data["user"].append({"login": login, "password": word_after(text, ("пароль", "password"))})
    return data


def word_after(text, words):
    for word in words:
        match = re.search(r"\b" + word + r"\s*[:=]?\s+([^\s,;|]+)", text, flags=re.I)
        if match:
            return match.group(1).strip(".")
    return None


def values(data):
    """[(что, значение)] - всё, что должно лежать в настройках проекта."""
    result = []
    for item in data["rest"]:
        result.append(("адрес REST-клиента " + item["name"], item["url"]))
    for item in data["db"]:
        result.append(("адрес БД " + item["name"], item["url"]))
        if item["user"]:
            result.append(("пользователь БД " + item["name"], item["user"]))
        if item["password"]:
            result.append(("пароль БД " + item["name"], item["password"]))
    for item in data["user"]:
        result.append(("логин пользователя", item["login"]))
        if item["password"]:
            result.append(("пароль пользователя " + item["login"], item["password"]))
    seen = set()
    return [v for v in result if not (v[1] in seen or seen.add(v[1]))]


def registered_services(root):
    """Имена сервисов (строчными) из ConfiguredServiceHolder.of(<Сервис>.class ...) в методах
    getServiceConfigurations() классов .java/.kt проекта; комментарии вырезаются."""
    names = set()
    for f in env_check.walk(root):
        if f.suffix not in (".java", ".kt"):
            continue
        text = re.sub(r"/\*.*?\*/|//[^\n]*", "", env_check.read(f), flags=re.S)
        # объявление метода: «getServiceConfigurations() {», вызов super.getServiceConfigurations() не в счёт
        for match in re.finditer(r"getServiceConfigurations\s*\(\s*\)\s*\{", text):
            body = method_body(text, match.end() - 1)
            names.update(n.lower() for n in HOLDER.findall(body))
    return names


def method_body(text, start):
    """Тело метода от первой «{» после start до парной «}»."""
    open_at = text.find("{", start)
    if open_at < 0:
        return ""
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_at:i + 1]
    return text[open_at:]


def stored_text(root):
    """Текст файлов настроек (каталоги resources) и классов *Configuration проекта."""
    parts = []
    for f in env_check.walk(root):
        inside = "resources" in f.parts and f.name.endswith(CONFIG_SUFFIXES)
        if inside or re.search(r"Configuration\.(java|kt)$", f.name):
            parts.append(env_check.read(f))
    return "\n".join(parts)


def run_compile(root):
    command = env_check.compile_command(root, env_check.build_tool(root))
    if not command:
        return "failed: нет файла сборки"
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return "failed: таймаут %d c" % TIMEOUT
    except OSError as error:
        return "failed: " + str(error)
    return "ok" if result.returncode == 0 else "failed: " + " ".join(command)


def write_report(path, key, ready, need, compile_status):
    rows = ["| %s | %s | %s |" % item for item in need] or ["| - | - | всё на месте |"]
    text = "\n".join([
        "---", "tc: " + key, "env_tc: " + ("ready" if ready else "missing"),
        "checked_at: " + datetime.now().strftime("%Y-%m-%d %H:%M"), "---", "",
        "# Окружение под ТК " + key, "", "Компиляция: " + compile_status, "",
        "| Что нужно | Чего | Подробно |", "|-----------|------|----------|"] + rows) + "\n"
    try:
        path.write_text(text, encoding="utf-8")
        return True
    except OSError:
        return False


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
