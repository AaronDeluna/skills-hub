#!/usr/bin/env python3
"""Общие проверки Java-кода и компиляция проекта для скиллов autotest-gen и autotest-review.

Модуль, а не команда: его импортируют at_tools.py и review.py из той же папки scripts/.
Источник - shared/scripts/java_checks.py набора, копии раскладывает scripts/sync_shared.py.
Python 3.8+, только стандартная библиотека.
"""
import json
import re
import subprocess
from pathlib import Path

ENV_JSON = Path(".gigacode") / "data" / "autotest" / "ENV.json"

# (правило, регулярное выражение, что не так) - одна строка кода, комментарии не проверяются
CHECKS = [
    ("MR-33", r"(^|[^A-Za-z0-9_])var +[A-Za-z_][A-Za-z0-9_]* *(=|:)", "var вместо явного типа"),
    ("MR-29", r"Assertions\.|\bassert(Equals|True|False|NotNull|Null|That|All|Throws)\(|SoftAssertions|org\.junit\.Assert\b|org\.testng\.Assert\b", "JUnit/AssertJ-проверка вместо matcher фрейма"),
    ("MR-41", r"\.as\([A-Z][A-Za-z0-9_]*\.class\)|readValue\(|fromJson\(|\.getObject\(", "ответ превращают в объект (DTO)"),
    ("MR-4", r"^(?!.*@ru\.sber\.qa\.allure\.system\.System\b)[^/*\"]*[^A-Za-z0-9_.\"](org|com|ru|io|java)\.[a-z0-9_]+\.[a-z0-9_.]+\.[A-Z]", "полное имя класса в коде вместо import"),
    ("MR-43", r"\b(log|logger|LOG|LOGGER)\.(info|debug|trace|warn|error)\(|System\.(out|err)\.print|\.prettyPrint\(|\.prettyPeek\(", "ручное логирование"),
    ("MR-48", r"implements [A-Za-z.]*(Matcher|Condition)\b|List<[A-Za-z.]*Matcher>|matchers\.add\(|JacksonHelper|JsonNode|textOrNull|intOrNull|assertAll\(", "своя конструкция вокруг matcher или разбор ответа руками"),
    ("MR-49", r"^\s+(public |private |protected )?(static )?(final )?(class|interface|enum|record) [A-Z]", "вложенный класс"),
    ("MR-47", r"ConfigFactory\.create|new Properties\(\)|getResourceAsStream\(|ResourceBundle\.getBundle|System\.(getProperty|getenv)\(", "своё чтение настроек"),
    ("MR-15", r"\"https?://|\"(jdbc|kafka|ldap)s?:|(password|passwd|token|secret)\s*=\s*\"[^\"]+\"", "адрес или секрет прямо в коде - только ключ настроек"),
    ("MR-45", r"(^|[ .(])[a-z][A-Za-z0-9]*_[A-Za-z0-9_]*( *\(| *=| *;|,|\))", "имя с нижним подчёркиванием"),
    ("MR-14", r"Thread\.sleep|TimeUnit\.[A-Z]+\.sleep", "sleep вместо ожидания фрейма"),
    ("MR-21", r"\b(TODO|FIXME)\b|TODO-CONST", "TODO в коде - место не доделано"),
    ("STUB", r"//\s*STUB\b", "заглушка: шаг не сгенерирован"),
]
# только для тест-класса (класса с @Test)
TEST_ONLY = [("MR-42", r"^\s*(private|protected|static) [^=]*\([^)]*\)\s*(throws [A-Za-z, ]+)?\{", "вспомогательный метод в тест-классе (место - класс шагов)")]
# правила, которые ищутся и в комментариях
IN_COMMENTS = ("MR-21", "STUB")


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def comment_lines(lines):
    """Номера строк (с 1), которые целиком комментарий, import или package."""
    result, in_block = set(), False
    for number, line in enumerate(lines, 1):
        trimmed = line.strip()
        if trimmed.startswith("/*"):
            in_block = True
        if in_block or trimmed.startswith("//") or trimmed.startswith("*") or trimmed.startswith("import ") or trimmed.startswith("package "):
            result.add(number)
        if "*/" in trimmed:
            in_block = False
    return result


def scan_items(lines, checks):
    """Находки по строкам: список (правило, номер строки, что не так, строка)."""
    found, comments = [], comment_lines(lines)
    for number, line in enumerate(lines, 1):
        for rule, pattern, message in checks:
            if number in comments and rule not in IN_COMMENTS:
                continue
            if re.search(pattern, line, re.ASCII):
                if rule == "MR-49" and re.search(r"static (final )?class [A-Za-z]*Builder\b", line):
                    continue
                found.append((rule, number, message, line.strip()[:140]))
    return found


def scan(path, lines, checks):
    """Находки строками «<правило> <файл>:<строка> - <что не так>: <код>»."""
    return ["%s %s:%d - %s: %s" % (rule, path, number, message, code) for rule, number, message, code in scan_items(lines, checks)]


def compile_project(timeout, env_json=ENV_JSON):
    """Компиляция командой из ENV.json. Возвращает (статус ok | failed | skipped, строки)."""
    try:
        env = json.loads(read(env_json) or "{}")
    except ValueError:
        env = {}
    argv = env.get("project", {}).get("compile_argv") or env.get("project", {}).get("compile_command", "-").split()
    command = " ".join(argv)
    if not argv or argv == ["-"]:
        return "skipped", ["нет команды компиляции в ENV.json - запусти env-check"]
    try:
        result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "failed", ["таймаут " + str(timeout) + " с: " + command]
    except OSError as error:
        return "failed", [str(error)]
    if result.returncode == 0:
        return "ok", [command]
    output = result.stdout.decode("utf-8", "replace").splitlines()
    errors = [l.strip() for l in output if re.search(r"\bERROR\b|error:|cannot find symbol|FAILED", l)]
    return "failed", (errors or output[-20:])[:20]
