#!/usr/bin/env python3
"""Золотой набор скриптов (для разработчиков набора). Запуск из папки набора:

  python3 scripts/selftest.py

Создаёт временные проекты, запускает каждый скрипт набора и сверяет ключевые строки вывода
и коды выхода с ожидаемыми. Сеть, Maven и Gradle не нужны: сборку заменяет файл mvnw.
После смены текста скилла или скрипта прогоняй заново. Код выхода: 0 - всё сошлось, 1 - нет.
Python 3.8+, только стандартная библиотека.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
FAILED = []


def run(cwd, script, *args):
    result = subprocess.run([sys.executable, str(Path(cwd) / script)] + list(args), cwd=str(cwd),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    return result.returncode, result.stdout.decode("utf-8", "replace")


def expect(name, cwd, script, args, code, *needles, absent=()):
    rc, out = run(cwd, script, *args)
    bad = [n for n in needles if n not in out] + ["лишнее: " + n for n in absent if n in out]
    if rc != code or bad:
        FAILED.append(name)
        print("FAIL " + name + ": код " + str(rc) + " (ждали " + str(code) + "), не найдено: " + "; ".join(bad))
        print("     " + out.strip().replace("\n", "\n     ")[:1500])
    else:
        print("ok   " + name)
    return out


def write(root, path, text):
    target = Path(root) / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


POM = """<project><modelVersion>4.0.0</modelVersion><groupId>ru.demo</groupId><artifactId>at</artifactId><version>1</version>
<properties><pvat.version>3.4.1</pvat.version></properties><dependencies>
<dependency><groupId>ru.sber.qa</groupId><artifactId>environment-junit5</artifactId><version>${pvat.version}</version></dependency>
<dependency><groupId>ru.sber.qa</groupId><artifactId>allure2</artifactId><version>${pvat.version}</version></dependency>
</dependencies></project>
"""
TC = """**Название:** Запрос списка продуктов с атрибутом attChannel
**Ключ:** CMN-T120
**Цель:** Проверяется эндпоинт productList
### Шаги выполнения
| № | Описание шага | Тестовые данные | Ожидаемый результат |
|---|---|---|---|
| 1 | Отправить запрос POST | /rest/v1/productList | Код ответа 200 |
| 2 | Проверить значение поля по полному пути | JSONPath: $status.statusCode | 0 |
"""
MAP = """---
map_status: approved
scope: full
review_status: -
review_round: 0
---
## 4. Юниты работ
В архиве: M-001
| ID | Фаза | Тип | Тех | Что | Зависит | Файлов | Статус |
|----|------|-----|-----|-----|---------|--------|--------|
| M-002 | 2 | env | common | окружение | M-001 | 1 | done |
| M-003 | 2 | arch | common | архитектура | M-002 | 1 | todo |
## 6. Открытые вопросы к человеку
"""
REVIEW_TEST = """package ru.demo.tests;

import org.junit.jupiter.api.Test;

public class PayTest extends BaseTest {

    @Test
    void pay() {
        String phone = "79991234567";
        steps.pay(phone);
        steps.status("PAY-001");
        Thread.sleep(1000);
        steps.a();
        steps.b();
        steps.c();
        steps.d();
        steps.e();
        steps.a();
        steps.b();
        steps.c();
        steps.d();
        steps.e();
    }
}
"""
CARD = """---
id: M-003
type: arch
tech: common
status: todo
---
# M-003 · Архитектура
## Файлы юнита
| Файл | Строк | Действие |
|------|-------|----------|
| src/test/java/a/A.java | 1 | изменить |
## Что сделать
1. Перенести метод, адаптировать вызовы.
## Правила юнита
MR-3
"""


def project(tmp, name):
    root = Path(tmp) / name
    for skill in sorted(d for d in KIT.iterdir() if (d / "SKILL.md").is_file()):
        shutil.copytree(str(skill), str(root / ".gigacode" / "skills" / skill.name))
    return root


def main():
    with tempfile.TemporaryDirectory() as tmp:
        # --- окружение и генерация ---
        p = project(tmp, "at")
        write(p, "pom.xml", POM)
        write(p, "src/test/java/ru/demo/config/DemoEnvironmentConfiguration.java", "package ru.demo.config; public class DemoEnvironmentConfiguration {}\n")
        write(p, "src/test/java/ru/demo/tests/BaseTest.java", "package ru.demo.tests; public abstract class BaseTest {}\n")
        write(p, "src/test/java/ru/demo/tests/OldTest.java", "package ru.demo.tests;\nclass OldTest extends BaseTest { @Test void a() {} }\n")
        write(p, "src/test/resources/perfeccionista.properties", "perfeccionista.attachment.dir=target\n")
        write(p, "mvnw", "#!/bin/sh\nexit 0\n")
        os.chmod(str(p / "mvnw"), 0o755)
        write(p, "tc.md", TC)
        na = ".gigacode/skills/orchestrator/scripts/next_action.py"
        expect("next_action: агенты ставятся", p, na, ["env"], 0, "ДЕЙСТВИЕ: агенты установлены", "pvatf-generator.md")
        expect("next_action: генерация ждёт окружения", p, na, ["autotest", "tc.md"], 0, "ДЕЙСТВИЕ: env-check")
        expect("env_check: ok/warning и ENV.json", p, ".gigacode/skills/env-check/scripts/env_check.py", [], 0,
               "E6 · компиляция тестов · ok", "ВЕРСИЯ: pvat.version = 3.4.1")
        expect("next_action: новый ТК", p, na, ["autotest", "tc.md"], 0, "ДЕЙСТВИЕ: autotest-plan")
        expect("next_action: обновление", p, na, ["env", "update"], 0, "ДЕЙСТВИЕ: env-update")
        eu = ".gigacode/skills/env-update/scripts/env_update.py"
        expect("env_update versions", p, eu, ["versions"], 0, "ТЕКУЩАЯ: 3.4.1")
        write(p, "rn.md", "## 3.5.0\n## 3.6.0-SNAPSHOT\n## 3.4.1\n")
        expect("env_update latest", p, eu, ["latest", "rn.md"], 0, "САМАЯ НОВАЯ: 3.5.0")
        expect("env_update bump", p, eu, ["bump", "3.5.0"], 0, "ИЗМЕНЕНО: pom.xml:2 · pvat.version · 3.4.1 -> 3.5.0")
        expect("env_update bump повторно", p, eu, ["bump", "3.5.0"], 1, "УЖЕ:")
        expect("env_update rollback", p, eu, ["rollback"], 0, "ВОЗВРАЩЁН: pom.xml")
        expect("env_update bump для reset", p, eu, ["bump", "3.5.0"], 0, "ИЗМЕНЕНО: pom.xml:2")
        expect("env_update reset", p, eu, ["reset"], 0, "СБРОШЕНО")
        expect("env_update rollback после reset", p, eu, ["rollback"], 1, "КОПИЙ НЕТ")
        write(p, "pom.xml", (Path(p) / "pom.xml").read_text(encoding="utf-8").replace("3.5.0", "3.4.1"))
        ap = ".gigacode/skills/autotest-plan/scripts/"
        expect("tc_convert md", p, ap + "tc_convert.py", ["tc.md"], 0, "ТК: CMN-T120", "ШАГОВ: 2")
        write(p, "tc.xml", "<testCase key=\"XML-T1\"><name>Создание заказа через REST API</name><objective>цель</objective>"
                           "<testScript><steps><step index=\"0\"><description>Отправить POST /api/orders</description>"
                           "<expectedResult>Код ответа 201</expectedResult></step></steps></testScript></testCase>")
        expect("tc_convert xml", p, ap + "tc_convert.py", ["tc.xml"], 0, "ТК: XML-T1", "ШАГОВ: 1")
        write(p, "tc.json", json.dumps({"key": "JS-T2", "name": "Проверка записи заказа в базе", "testScript": {"steps": [
            {"description": "Выполнить SELECT status FROM orders", "expectedResult": "status = ACTIVE"}]}}, ensure_ascii=False))
        expect("tc_convert json", p, ap + "tc_convert.py", ["tc.json"], 0, "ТК: JS-T2")
        expect("tc_check PASS/WARNING", p, ap + "tc_check.py", ["CMN-T120"], 0, "BLOCKING: false")
        write(p, "bad.md", "**Название:** Заказ\n**Ключ:** BAD-T1\n| № | Описание шага | Ожидаемый результат |\n|---|---|---|\n"
                           "| 1 | Отправить GET запрос | Ответ успешный |\n| 2 | Перейти в профиль из шага 5 | random |\n")
        run(p, ap + "tc_convert.py", "bad.md")
        expect("tc_check FAIL", p, ap + "tc_check.py", ["BAD-T1"], 1, "СТАТУС: FAIL", "TC-10", "TC-12")
        expect("next_action: FAIL не генерируется", p, na, ["autotest", "BAD-T1"], 0, "ДЕЙСТВИЕ: autotest-plan BAD-T1")
        expect("tc_plan build", p, ap + "tc_plan.py", ["build", "CMN-T120"], 0, "G: 1")
        expect("tc_plan validate", p, ap + "tc_plan.py", ["validate", "CMN-T120"], 0, "plan_status: planned")
        expect("tc_plan build не перезаписывает", p, ap + "tc_plan.py", ["build", "CMN-T120"], 1, "ПЛАН УЖЕ ЕСТЬ")
        expect("next_action: план готов", p, na, ["autotest", "CMN-T120"], 0, "ДЕЙСТВИЕ: autotest-gen CMN-T120")
        at = ".gigacode/skills/autotest-gen/scripts/at_tools.py"
        expect("at_tools rules", p, at, ["rules", "CMN-T120"], 0, "ПРАВИЛА: 32")
        expect("at_tools next", p, at, ["next", "CMN-T120"], 0, "ЗАДАНИЕ для агента pvatf-generator", "Шаг 2 · ASSERT")
        expect("at_tools mark без фрагмента", p, at, ["mark", "CMN-T120", "G-1", "ok"], 1, "нет фрагмента")
        write(p, ".gigacode/data/autotest/CMN-T120/fragments/G-1.md",
              "# G-1 · Работа с Rest API\n- Статус: ok\n- Файлы шагов: -\n\n## imports\n```java\nimport ru.demo.steps.ProductSteps;\n```\n\n"
              "## fields\n```java\nprivate static final String PATH_PRODUCT_LIST = \"/rest/v1/productList\";\n```\n\n"
              "## body\n```java\n// Шаг 1: Отправить запрос POST\nvar r = ProductSteps.list(PATH_PRODUCT_LIST);\n```\n")
        expect("at_tools mark ok", p, at, ["mark", "CMN-T120", "G-1", "ok"], 0, "ОТМЕЧЕНО: G-1 ok")
        expect("at_tools assemble", p, at, ["assemble", "CMN-T120"], 0, "СОБРАНО: src/test/java/ru/demo/tests/")
        expect("at_tools check находит", p, at, ["check", "CMN-T120"], 1, "MR-33", "ПОКРЫТИЕ шаг 2")
        frag = p / ".gigacode/data/autotest/CMN-T120/fragments/G-1.md"
        frag.write_text(frag.read_text(encoding="utf-8").replace("var r", "ValidatableResponse r")
                        .replace("```\n", "// Шаг 2: Проверить значение поля\nr.should(haveStatusCode(200));\n```\n", 3)
                        .replace("// Шаг 2: Проверить значение поля\nr.should(haveStatusCode(200));\n```\n\n## fields", "```\n\n## fields")
                        .replace("// Шаг 2: Проверить значение поля\nr.should(haveStatusCode(200));\n```\n\n## body", "```\n\n## body"), encoding="utf-8")
        run(p, at, "assemble", "CMN-T120")
        expect("at_tools check чисто", p, at, ["check", "CMN-T120"], 0, "ИТОГ: находок 0", "plan_status: checked")
        expect("next_action: финал", p, na, ["autotest", "CMN-T120"], 0, "ДЕЙСТВИЕ: финал CMN-T120")
        mk = ".gigacode/skills/migration-step/scripts/markup_keys.py"
        expect("markup_keys: новый тест с @TmsLink", p, mk, ["missing", "src/test/java"], 0, "итого: 0")
        # --- миграция ---
        m = project(tmp, "mig")
        write(m, ".gigacode/data/migration/MIGRATION-MAP.md", MAP)
        write(m, ".gigacode/data/migration/units/M-003.md", CARD)
        write(m, "src/test/java/a/A.java", "class A {}\n")
        run(m, na)
        expect("next_action: первый todo", m, na, [], 0, "ДЕЙСТВИЕ: migration-step M-003")
        expect("next_action: done пропускается", m, na, ["M-002"], 0, "ДЕЙСТВИЕ: нечего делать", "M-002 уже done")
        expect("card: пустые слова по-русски", m, ".gigacode/skills/migration-map/scripts/card.py", ["M-003"], 1, "«адаптировать»")
        expect("unit recite", m, ".gigacode/skills/migration-step/scripts/unit.py", ["recite", "M-003"], 0, "Юнит M-003 (arch, common)")
        write(m, ".gigacode/data/doc-notes/rest.md", "## D-rest-1 · Как отправить POST\n- Статус: найден\n- Что использовать: RestService\n")
        expect("notes find в общем конспекте", m, ".gigacode/skills/migration-step/scripts/notes.py", ["find", "rest", "post"], 0, "D-rest-1")
        expect("notes next", m, ".gigacode/skills/env-check/scripts/notes.py", ["next", "rest"], 0, "D-rest-2")
        # --- проверка существующего автотеста ---
        r = project(tmp, "rv")
        write(r, "src/test/java/ru/demo/tests/PayTest.java", REVIEW_TEST)
        for other in ("RefundTest", "CancelTest"):
            write(r, "src/test/java/ru/demo/tests/" + other + ".java",
                  "package ru.demo.tests;\nclass " + other + " { @Test void t() { steps.status(\"PAY-001\"); } }\n")
        write(r, ".gigacode/data/autotest/ENV.json", json.dumps({"status": "ok", "project": {"compile_argv": ["./mvnw", "-q"]}}))
        write(r, "mvnw", "#!/bin/sh\nexit 1\n")
        os.chmod(str(r / "mvnw"), 0o755)
        run(r, na)
        test = "src/test/java/ru/demo/tests/PayTest.java"
        rv = ".gigacode/skills/autotest-review/scripts/review.py"
        expect("next_action: новая проверка автотеста", r, na, ["review", test], 0, "ДЕЙСТВИЕ: autotest-review " + test)
        expect("review find", r, rv, ["find", test], 0, "MR-14", "MARKUP", "CONST", "PHONE", "SHARED-CONST", "DUP",
               "RefundTest.java", absent=("SLEEP",))
        expect("next_action: проверка не закончена", r, na, ["review"], 0, "review_status: found")
        expect("review start без approve", r, rv, ["start", test], 1, "сначала approve")
        expect("review approve", r, rv, ["approve", test, "all", "--target-only"], 0, "ОДОБРЕНО:", "только тест-класс")
        expect("review start: проект не компилируется", r, rv, ["start", test], 1, "ПРОЕКТ НЕ КОМПИЛИРУЕТСЯ ДО ПРАВОК")
        write(r, "mvnw", "#!/bin/sh\nexit 0\n")
        expect("review start", r, rv, ["start", test], 0, "КОМПИЛЯЦИЯ ДО ПРАВОК: ok", "СКРИПТ СДЕЛАЛ: R-")
        body = (r / test).read_text(encoding="utf-8")
        if "private static final String PHONE = \"79991234567\";" not in body or "String phone = PHONE;" not in body:
            FAILED.append("review start: константа PHONE не вынесена")
            print("FAIL review start: константа PHONE не вынесена")
        expect("review next", r, rv, ["next", test], 0, "ПРАВКА для агента pvatf-generator", "fixes.md", "раздел «MR», строка MR-14")
        plan = (r / ".gigacode/data/autotest-review/PayTest/REVIEW-PLAN.md").read_text(encoding="utf-8")
        for rid in [l.split("|")[1].strip() for l in plan.splitlines() if l.rstrip().endswith("| approved |")]:
            run(r, rv, "mark", test, rid, "done")
        write(r, "src/test/java/ru/demo/steps/PaySteps.java", "package ru.demo.steps;\npublic class PaySteps { var x = 1; }\n")
        expect("review check: новое нарушение", r, rv, ["check", test], 1, "MR-33", "круг 1 из 3")
        expect("review next: FIX", r, rv, ["next", test], 0, "FIX", "исправь ошибки последнего check")
        write(r, "src/test/java/ru/demo/steps/PaySteps.java", "package ru.demo.steps;\npublic class PaySteps { int x = 1; }\n")
        expect("review check чисто", r, rv, ["check", test], 0, "review_status checked")
        expect("review rollback", r, rv, ["rollback", test], 0, "восстановлен " + test, "удалён src/test/java/ru/demo/steps/PaySteps.java")
        if (r / test).read_text(encoding="utf-8") != REVIEW_TEST:
            FAILED.append("review rollback: файл не совпал с исходным")
            print("FAIL review rollback: файл не совпал с исходным")
    for kit_root in (KIT,):
        rc, out = subprocess.run([sys.executable, str(kit_root / "scripts" / "sync_shared.py"), "--check"], cwd=str(kit_root),
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT).returncode, ""
        print(("ok   " if rc == 0 else "FAIL ") + "sync_shared --check")
        if rc:
            FAILED.append("sync_shared")
    print("ИТОГ: " + ("всё сошлось" if not FAILED else "не сошлось " + str(len(FAILED)) + ": " + ", ".join(FAILED)))
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
