#!/usr/bin/env python3
"""
Каркас нового проекта автотестов (скилл env-check, режим init). Запуск из пустого корня проекта:

  python3 <каталог скилла>/scripts/env_init.py defaults
      - значения по умолчанию: groupId, artifactId, пакет (из имени каталога)
  python3 <каталог скилла>/scripts/env_init.py create --group <groupId> --artifact <artifactId> --package <пакет>
      - pom.xml (координаты, Java 17, UTF-8), src/test/java/<пакет>, src/test/resources,
        .gigacode/data/autotest/ENV-INIT.md - список созданного

Зависимости фрейма, плагины, класс конфигурации окружения, perfeccionista.properties и базовый
тест-класс скрипт НЕ пишет: их имена берутся только из документации (дальше - режим setup).
Код выхода: 0 - создано, 1 - проект уже есть (файл сборки найден) или значения неверные, 2 - неверный запуск.
Python 3.8+, только стандартная библиотека.
"""
import re
import sys
from datetime import datetime
from pathlib import Path

OUT = Path(".gigacode") / "data" / "autotest" / "ENV-INIT.md"
BUILD = ["pom.xml", "build.gradle", "build.gradle.kts"]
GROUP = re.compile(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+")
ARTIFACT = re.compile(r"[a-z][a-z0-9\-]*")
PACKAGE = re.compile(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*")

POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>{group}</groupId>
    <artifactId>{artifact}</artifactId>
    <version>1.0.0-SNAPSHOT</version>

    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <java.version>17</java.version>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencies>
    </dependencies>

    <build>
        <plugins>
        </plugins>
    </build>
</project>
"""


def defaults():
    name = re.sub(r"[^a-z0-9]+", "-", Path(".").resolve().name.lower()).strip("-") or "autotests"
    if not name[0].isalpha():
        name = "at-" + name
    group = "ru.autotests"
    package = group + "." + re.sub(r"[^a-z0-9]", "", name) + ".tests"
    return group, name, package


def option(args, name):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else ""


def main(args):
    if not args or args[0] not in ("defaults", "create"):
        print("Использование: env_init.py defaults | create --group <groupId> --artifact <artifactId> --package <пакет>")
        return 2
    existing = [b for b in BUILD if Path(b).is_file()]
    if existing:
        print("ПРОЕКТ УЖЕ ЕСТЬ: " + ", ".join(existing) + " - каркас не создаю, нужен режим setup")
        return 1
    group, artifact, package = defaults()
    if args[0] == "defaults":
        print("ПО УМОЛЧАНИЮ: groupId " + group + " · artifactId " + artifact + " · пакет " + package)
        return 0
    group = option(args, "--group") or group
    artifact = option(args, "--artifact") or artifact
    package = option(args, "--package") or package
    bad = [n + " «" + v + "»" for n, v, rx in (("groupId", group, GROUP), ("artifactId", artifact, ARTIFACT),
                                                ("пакет", package, PACKAGE)) if not rx.fullmatch(v)]
    if bad:
        print("НЕВЕРНО: " + ", ".join(bad) + " - groupId вида ru.sber.demo, artifactId вида demo-tests, пакет вида ru.sber.demo.tests")
        return 1
    created = []
    Path("pom.xml").write_text(POM.format(group=group, artifact=artifact), encoding="utf-8")
    created.append("pom.xml")
    for folder in ("src/test/java/" + package.replace(".", "/"), "src/test/resources"):
        if not Path(folder).is_dir():
            Path(folder).mkdir(parents=True)
            created.append(folder + "/")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("# Каркас проекта\n\n- Дата: " + datetime.now().strftime("%Y-%m-%d %H:%M")
                   + "\n- groupId: " + group + "\n- artifactId: " + artifact + "\n- Пакет тестов: " + package
                   + "\n\n## Создано\n\n" + "\n".join("- " + c for c in created) + "\n", encoding="utf-8")
    for item in created:
        print("СОЗДАНО: " + item)
    print("ПАКЕТ: " + package)
    print("ДАЛЬШЕ: режим setup - зависимости фрейма, конфигурация, базовый тест-класс по документации")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
