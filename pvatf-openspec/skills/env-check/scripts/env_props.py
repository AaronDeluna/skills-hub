#!/usr/bin/env python3
"""perfeccionista.properties по эталону проекта-примера фрейма (скилл env-check). Запуск из корня проекта:

  python3 <скилл>/scripts/env_props.py ensure   - дописать недостающие ключи фрейма, ничего не удаляя
  python3 <скилл>/scripts/env_props.py check    - только показать, чего не хватает и что лишнее

Эталон - блок ниже (проект-пример фрейма): пакеты сканирования сервисов и источников данных, каталог
вложений, логирование модуля сессий. ensure: файла нет -> создаёт в src/test/resources модуля с тестами;
ключа нет -> дописывает блок эталона; в списке пакетов scanPackages нет пакета эталона -> дописывает
пакет в конец списка, свои пакеты проекта оставляет. Ключи не из эталона не удаляет: печатает
ПРОВЕРИТЬ (ключ не фрейма - перенести в свой файл настроек по правилу 14 autotest-rules.md).
Модель этот файл руками не пишет.
Python 3.8+, только стандартная библиотека. Код выхода: 0 - файл по эталону, 1 - есть строки
ПРОВЕРИТЬ или (check) не хватает ключей, 2 - неверный запуск.
"""
import re
import sys
from pathlib import Path

# ключ -> (комментарий, значения); список значений - пакеты через «,\» на новых строках
STANDARD = [
    ("perfeccionista.services.scanPackages", "Packages for Service scanning",
     ["io.perfeccionista.framework.value", "io.perfeccionista.framework.datasource",
      "io.perfeccionista.framework.fixture", "io.perfeccionista.framework.invocation"]),
    ("perfeccionista.datasources.scanPackages", "Packages for datasource scanning",
     ["io.perfeccionista.framework", "ru.sber.qa.services.datasource"]),
    ("perfeccionista.attachment.dir", "Path for test attachments", ["target/attachment"]),
    ("session.showConsoleLog", "Parameter for disable logging to console in session module", ["true"]),
    ("session.consoleLogLevel", None, ["INFO"]),
]
SKIP = {"target", "build", ".git", ".gigacode", "node_modules", "openspec", ".idea"}


def out(*lines):
    sys.stdout.buffer.write(("\n".join(lines) + "\n").encode("utf-8"))


def find():
    found = [p for p in Path(".").rglob("perfeccionista.properties") if not set(p.parts) & SKIP and "test" in p.parts]
    if found:
        return sorted(found, key=lambda p: len(p.parts))[0], True
    roots = sorted((p for p in Path(".").rglob("src/test/java") if not set(p.parts) & SKIP), key=lambda p: len(p.parts))
    base = roots[0].parent if roots else Path("src/test")
    return base / "resources" / "perfeccionista.properties", False


def parse(text):
    """-> {ключ: [значения]} с учётом продолжения строки «\\»."""
    logical = re.sub(r"\\[ \t]*\r?\n[ \t]*", "", text)
    keys = {}
    for line in logical.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "!")) or not re.search(r"[=:]", line):
            continue
        key, value = re.split(r"\s*[=:]\s*", line, maxsplit=1)
        keys[key] = [v.strip() for v in value.split(",") if v.strip()]
    return keys


def block(key, comment, values):
    lines = (["", "# " + comment] if comment else [])
    if len(values) == 1:
        return lines + [key + "=" + values[0]]
    lines.append(key + "=" + values[0] + ",\\")
    lines += ["  " + v + (",\\" if i < len(values) - 2 else "") for i, v in enumerate(values[1:])]
    return lines


def add_packages(text, key, missing):
    """Дописать пакеты в конец списка ключа (последняя строка значения получает «,\\»)."""
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if re.match(r"\s*" + re.escape(key) + r"\s*[=:]", l))
    end = start
    while lines[end].rstrip().endswith("\\") and end + 1 < len(lines):
        end += 1
    lines[end] = lines[end].rstrip() + ",\\"
    extra = ["  " + p + (",\\" if i < len(missing) - 1 else "") for i, p in enumerate(missing)]
    return "\n".join(lines[:end + 1] + extra + lines[end + 1:]) + "\n"


def main(argv):
    if not argv or argv[0] not in ("ensure", "check"):
        out("Использование: env_props.py ensure | check")
        return 2
    path, exists = find()
    text = path.read_text(encoding="utf-8") if exists else ""
    have = parse(text)
    added, changed = [], []
    for key, comment, values in STANDARD:
        if key not in have:
            added.append(key)
            if argv[0] == "ensure":
                text = text.rstrip("\n") + ("\n" if text.strip() else "") + "\n".join(block(key, comment, values)).lstrip("\n") + "\n" \
                    if not text.strip() else text.rstrip("\n") + "\n" + "\n".join(block(key, comment, values)) + "\n"
        elif key.endswith("scanPackages"):
            missing = [v for v in values if v not in have[key]]
            if missing:
                changed.append(key + " + " + ", ".join(missing))
                if argv[0] == "ensure":
                    text = add_packages(text, key, missing)
    standard = {k for k, _, _ in STANDARD}
    review = []
    for key in have:
        if key in standard:
            continue
        if key.startswith(("perfeccionista.", "session.")):
            review.append(key + " - нет в эталоне проекта-примера: оставь, только если ключ есть в конспекте документации")
        else:
            review.append(key + " - не ключ фрейма: перенеси в свой файл настроек (правило 14 autotest-rules.md), sid не храни нигде")
    if argv[0] == "ensure" and (added or changed or not exists):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    out("ФАЙЛ: " + path.as_posix() + ("" if exists else (" - создан" if argv[0] == "ensure" else " - нет")))
    out(("ДОПИСАНО: " if argv[0] == "ensure" else "НЕ ХВАТАЕТ: ") + (", ".join(added + changed) or "нет"))
    for r in review:
        out("ПРОВЕРИТЬ: " + r)
    out("ИТОГ: " + ("по эталону" if not review and (argv[0] == "ensure" or not (added or changed)) else "есть что поправить"))
    return 0 if not review and (argv[0] == "ensure" or not (added or changed)) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
