#!/usr/bin/env python3
"""
Окружение под тест-кейс (скилл env-check, режим setup с ключом ТК). Запуск из корня проекта:

  python3 <каталог скилла>/scripts/env_tc.py <ключ ТК>               - проверка с компиляцией
  python3 <каталог скилла>/scripts/env_tc.py <ключ ТК> --no-compile  - без компиляции

Читает .gigacode/data/autotest/<ключ>/PLAN.md (раздел 8 «Окружение под ТК») и TC.md (колонки
«Действие» и «Тестовые данные») и сверяет с проектом:
- модуль фрейма под каждую технологию ТК есть в файлах сборки (слова из раздела 8);
- драйвер JDBC под каждый адрес jdbc:<вендор> из ТК есть в файлах сборки;
- allure-junit5 есть в файлах сборки (тест-класс несёт @TmsLink);
- логирование: slf4j-simple и slf4j-api в сборке, simplelogger.properties в ресурсах;
- в services() класса конфигурации окружения регистраций не меньше, чем технологий ТК;
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

OUT_DIR = Path(".gigacode") / "data" / "autotest"
TIMEOUT = 540
# вендор из jdbc:<вендор>: -> слово, которое ищется в файлах сборки (артефакт драйвера)
DRIVER_WORDS = {"postgresql": "postgresql", "oracle": "ojdbc", "sqlserver": "mssql-jdbc", "mysql": "mysql",
                "mariadb": "mariadb", "h2": "h2", "db2": "db2", "clickhouse": "clickhouse"}
URL = re.compile(r"https?://[^\s;,)\]|<>\"']+")
JDBC = re.compile(r"jdbc:[^\s;,)\]|<>\"']+")
CONFIG_SUFFIXES = (".properties", ".yml", ".yaml", ".conf", ".json")


def main(args):
    compile_on = "--no-compile" not in args
    keys = [a for a in args if not a.startswith("--")]
    if len(keys) != 1 or len(args) - len(keys) > (0 if compile_on else 1):
        print("Использование: env_tc.py <ключ ТК> [--no-compile]")
        return 2
    key = keys[0]
    plan_file = OUT_DIR / key / "PLAN.md"
    if not plan_file.is_file():
        print("НЕТ ПЛАНА: " + str(plan_file).replace("\\", "/") + " - сначала autotest-plan")
        return 2
    root = Path(".").resolve()
    build_text = "\n".join(env_check.read(f) for f in env_check.find_build_files(root)).lower()
    need = []
    techs = tc_technologies(env_check.read(plan_file))
    for tech, words in techs:
        if words and not any(w in build_text for w in words):
            need.append(("модуль", tech, "слова в сборке: " + ", ".join(words)))
    data = tc_data(env_check.read(OUT_DIR / key / "TC.md"))
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
    registered = count_registered(root)
    if registered < len(techs):
        need.append(("сервисы", ", ".join(t for t, _ in techs),
                     "в services() зарегистрировано %d, технологий ТК %d" % (registered, len(techs))))
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
    out_file = OUT_DIR / key / "ENV-TC.md"
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
    """Раздел 8 плана: [(технология, [слова в сборке])], кроме строк RECOMMENDED."""
    sect = re.search(r"(?ms)^## 8\. Окружение под ТК\s*\n(.*?)(?=^## |\Z)", plan)
    result = []
    for line in (sect.group(1) if sect else "").split("\n"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[1] in ("Метка", "-") or set(cells[0]) <= set("-:") or cells[2] == "RECOMMENDED":
            continue
        words = [w.strip().lower() for w in cells[4].split(",") if w.strip() not in ("", "-")]
        result.append((cells[0], words))
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


def count_registered(root):
    """Сколько регистраций (.register() в services() классов *EnvironmentConfiguration проекта."""
    total = 0
    for f in env_check.walk(root):
        if f.name.endswith(("EnvironmentConfiguration.java", "EnvironmentConfiguration.kt")):
            body = re.search(r"services\s*\(\s*\)[^{]*\{(.*?)\n\s{0,4}\}", env_check.read(f), flags=re.S)
            if body:
                total += len(re.findall(r"\.register\s*\(", body.group(1)))
    return total


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
