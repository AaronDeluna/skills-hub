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
import re
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

DEPS_ROOT = """<project><modelVersion>4.0.0</modelVersion><groupId>ru.demo</groupId><artifactId>root</artifactId><version>1.0</version>
<packaging>pom</packaging><modules><module>core</module><module>tests</module></modules>
<properties><pvat.version>3.4.1</pvat.version></properties>
<repositories><repository><id>x</id><url>http://x</url></repository></repositories>
</project>
"""
DEPS_CORE = """<project><parent><groupId>ru.demo</groupId><artifactId>root</artifactId><version>1.0</version></parent>
<artifactId>core</artifactId><dependencies>
<dependency><groupId>ru.demo</groupId><artifactId>tests</artifactId><version>1.0</version></dependency>
<dependency><groupId>com.fasterxml.jackson.core</groupId><artifactId>jackson-databind</artifactId><version>2.15.2</version></dependency>
<dependency><groupId>com.fasterxml.jackson.core</groupId><artifactId>jackson-core</artifactId><version>2.14.0</version></dependency>
<dependency><groupId>com.fasterxml.jackson.core</groupId><artifactId>jackson-annotations</artifactId><version>2.15.2</version></dependency>
<dependency><groupId>com.google.code.gson</groupId><artifactId>gson</artifactId><version>[2.8,)</version></dependency>
<dependency><groupId>ru.sber.qa</groupId><artifactId>environment-junit5</artifactId><version>3.4.1</version></dependency>
<dependency><groupId>ru.sber.qa</groupId><artifactId>allure2</artifactId><version>3.3.0</version></dependency>
</dependencies></project>
"""
DEPS_TESTS = """<project><parent><groupId>ru.demo</groupId><artifactId>root</artifactId><version>1.0</version></parent>
<artifactId>tests</artifactId><dependencies>
<dependency><groupId>ru.demo</groupId><artifactId>core</artifactId><version>1.0</version></dependency>
<dependency><groupId>com.fasterxml.jackson.core</groupId><artifactId>jackson-databind</artifactId><version>2.13.0</version></dependency>
<dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId><version>5.10.0</version><scope>test</scope></dependency>
<dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId><version>5.10.0</version><scope>test</scope></dependency>
<dependency><groupId>lib</groupId><artifactId>local</artifactId><version>1</version><scope>system</scope><systemPath>/x.jar</systemPath></dependency>
</dependencies></project>
"""
DEPS_MVNW = """#!/bin/sh
case "$*" in
*tree*) echo "[INFO] --- maven-dependency-plugin:3.6.0:tree (default-cli) @ core ---"
        echo "[INFO] |  \\- (com.fasterxml.jackson.core:jackson-core:jar:2.15.2:compile - omitted for conflict with 2.14.0)"
        echo "[INFO] |  \\- (io.netty:netty-buffer:jar:4.1.94:compile - omitted for conflict with 4.1.95)" ;;
*analyze*) echo "[INFO] BUILD SUCCESS" ;;
esac
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
        ec = ".gigacode/skills/env-check/scripts/env_check.py"
        expect("env_check: версия отстаёт", p, ec, ["--no-compile", "--release-notes", "rn.md"], 0,
               "САМАЯ НОВАЯ: 3.5.0", "info · FRAME_OUTDATED · Версия фрейма 3.4.1")
        run(p, ec)
        ini = project(tmp, "init")
        ei = ".gigacode/skills/env-check/scripts/env_init.py"
        run(ini, na, "env", "init")  # первый запуск ставит агентов набора
        expect("next_action: env init", ini, na, ["env", "init"], 0, "ДЕЙСТВИЕ: env-init")
        expect("env_init defaults", ini, ei, ["defaults"], 0, "ПО УМОЛЧАНИЮ: groupId ru.autotests · artifactId init")
        expect("env_init неверный пакет", ini, ei, ["create", "--package", "Ru.Bad"], 1, "НЕВЕРНО: пакет")
        expect("env_init create", ini, ei, ["create", "--group", "ru.sber.demo", "--artifact", "demo-tests", "--package", "ru.sber.demo.tests"], 0,
               "СОЗДАНО: pom.xml", "СОЗДАНО: src/test/java/ru/sber/demo/tests/")
        expect("env_init повторно", ini, ei, ["create"], 1, "ПРОЕКТ УЖЕ ЕСТЬ")
        expect("next_action: env init при pom", ini, na, ["env", "init"], 0, "ДЕЙСТВИЕ: env-setup")
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
        write(p, "run.log", "10:00:01 INFO Running ru.demo.OrderTest\n10:00:02 DEBUG Request: POST https://h/api/v1/orders\n"
                            "10:00:03 DEBUG Response: status code 201\n10:00:04 INFO Sending message to topic=order-events\n")
        expect("tc_convert лог", p, ap + "tc_convert.py", ["run.log", "--key", "LOG-T1"], 0, "ШАГОВ: 2", "ИСТОЧНИК: log")
        write(p, "old/PayTest.java", "import io.restassured.RestAssured;\nclass PayTest {\n@BeforeEach void up() { step(\"Подготовить пользователя\"); }\n"
                                     "@Test @TmsLink(\"PAY-T12\") void pay() { given().post(\"/api/pay\").then().statusCode(200); }\n"
                                     "@Test void other() { step(\"Другое\"); }\n}\n")
        expect("tc_convert код: несколько тестов", p, ap + "tc_convert.py", ["old/PayTest.java"], 1, "ТЕСТОВ НЕСКОЛЬКО: pay, other")
        expect("tc_convert код", p, ap + "tc_convert.py", ["old/PayTest.java", "--method", "pay"], 0, "ТК: PAY-T12", "ИСТОЧНИК: code")
        write(p, "allure-results/a-result.json", json.dumps({"uuid": "1", "name": "Проверка баланса счёта клиента", "links": [{"name": "BAL-T3"}],
                                                            "labels": [{"name": "layer", "value": "api"}],
                                                            "steps": [{"name": "GET /api/balance", "parameters": [{"name": "user", "value": "u1"}]}]}, ensure_ascii=False))
        expect("tc_convert allure-results", p, ap + "tc_convert.py", ["allure-results"], 0, "ТК: BAL-T3", "ИСТОЧНИК: allure")
        expect("tc_check тэги TC-14", p, ap + "tc_check.py", ["PAY-T12"], 0, "TC-14 · тэги · нет тэгов: @TestLayer, @System")
        write(p, "tags.md", "**Название:** Создание заказа через REST API\n**Ключ:** TAG-T1\n**Цель:** цель\n### Шаги выполнения\n"
                            "| № | Описание шага | Ожидаемый результат |\n|---|---|---|\n| 1 | Отправить POST /api/orders | код 200 |\n"
                            "### Тэги\n@TestLayer(\"rest\") @System(\"CI1\") @TestStage(\"ift\") @TestStage(\"st\")\n")
        run(p, ap + "tc_convert.py", "tags.md")
        expect("tc_check тэги TC-15", p, ap + "tc_check.py", ["TAG-T1"], 0, "СТАТУС: WARNING", "@TestStage с разными значениями", "это технология, а не слой")
        write(p, "kafka.md", "**Название:** Отправка события заказа в шину\n**Ключ:** KAF-T1\n**Цель:** цель\n### Шаги выполнения\n"
                             "| № | Описание шага | Ожидаемый результат |\n|---|---|---|\n| 1 | Отправить сообщение в топик Kafka order-events | сообщение отправлено, status = NEW |\n")
        run(p, ap + "tc_convert.py", "kafka.md")
        run(p, ap + "tc_check.py", "KAF-T1")
        expect("tc_plan: окружение под ТК", p, ap + "tc_plan.py", ["build", "KAF-T1"], 0, "ОКРУЖЕНИЕ: нет в сборке: kafka")
        expect("env_check: TC_MODULES_MISSING", p, ".gigacode/skills/env-check/scripts/env_check.py", ["--no-compile"], 0,
               "TC_MODULES_MISSING", "KAF-T1: Работа с Kafka")
        for extra in ("LOG-T1", "PAY-T12", "BAL-T3", "TAG-T1", "KAF-T1"):
            for name in ("TC.md", "TC-CHECK.md", "PLAN.md"):
                target = p / ".gigacode/data/autotest" / extra / name
                if target.is_file():
                    target.unlink()
        run(p, ".gigacode/skills/env-check/scripts/env_check.py")
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
        write(p, "cl.md", "**Название:** Создание и удаление заказа через API\n**Ключ:** CLN-T1\n**Цель:** цель\n### Шаги выполнения\n"
                          "| № | Описание шага | Ожидаемый результат |\n|---|---|---|\n| 1 | Подготовить клиента фикстурой | клиент создан |\n"
                          "| 2 | Отправить POST /api/orders | код ответа 201 |\n| 3 | Удалить созданный заказ | - |\n")
        run(p, ap + "tc_convert.py", "cl.md")
        run(p, ap + "tc_check.py", "CLN-T1")
        run(p, ap + "tc_plan.py", "build", "CLN-T1")
        run(p, ap + "tc_plan.py", "validate", "CLN-T1")
        empty = "- Статус: ok\n- Причина: -\n- Нужно из документации: -\n- Файлы шагов: -\n\n## imports\n```java\n```\n\n## fields\n```java\n```\n\n## body\n```java\n"
        write(p, ".gigacode/data/autotest/CLN-T1/fragments/G-1.md", "# G-1 · x\n" + empty + "// Шаг 1: Подготовить клиента\nString clientId = ClientSteps.create();\n```\n")
        write(p, ".gigacode/data/autotest/CLN-T1/fragments/G-2.md", "# G-2 · x\n" + empty + "// Шаг 2: Отправить POST\nString orderId = OrderSteps.create(clientId);\n"
                                                                 "// Шаг 3: Удалить заказ\nif (orderId != null) { OrderSteps.delete(orderId); }\n```\n")
        run(p, at, "mark", "CLN-T1", "G-1", "ok")
        run(p, at, "mark", "CLN-T1", "G-2", "ok")
        out = expect("at_tools assemble: @BeforeEach и @AfterEach", p, at, ["assemble", "CLN-T1"], 0, "МЕТОДЫ: @BeforeEach есть · @Test · @AfterEach есть")
        built = next((p / "src/test/java").rglob("*CherezApiTest.java"), None) or next((f for f in (p / "src/test/java").rglob("*.java") if "CLN-T1" in f.read_text(encoding="utf-8")), None)
        body = built.read_text(encoding="utf-8") if built else ""
        if "private String clientId;" in body and "private String orderId;" in body and "@AfterEach" in body and "        clientId = ClientSteps.create();" in body:
            print("ok   at_tools assemble: поля вместо локальных переменных")
        else:
            FAILED.append("at_tools assemble: поля")
            print("FAIL at_tools assemble: поля\n" + body[:1500])
        if built:
            built.unlink()
        expect("next_action: финал", p, na, ["autotest", "CMN-T120"], 0, "ДЕЙСТВИЕ: финал CMN-T120")
        # --- запуск сгенерированного теста ---
        expect("next_action: запуск после проверки", p, na, ["autotest", "run", "CMN-T120"], 0, "ДЕЙСТВИЕ: autotest-gen CMN-T120 запуск")
        expect("next_action: запуск без плана", p, na, ["autotest", "run", "NONE-T1"], 0, "ДЕЙСТВИЕ: нельзя")
        expect("at_tools run --dry-run: Maven", p, at, ["run", "CMN-T120", "--dry-run"], 0, "КОМАНДА: ./mvnw -B test -Dtest=", "surefire-reports/TEST-")
        head = dict(re.findall(r"(?m)^(\w+): *(.*)$", (p / ".gigacode/data/autotest/CMN-T120/PLAN.md").read_text(encoding="utf-8").split("\n---", 1)[0]))
        fqn = head.get("package", "") + "." + head.get("class", "")
        write(p, "target/surefire-reports/TEST-" + fqn + ".xml",
              '<testsuite tests="3" failures="1" errors="1" skipped="0"><testcase name="ok"/>'
              '<testcase name="pay"><failure type="org.opentest4j.AssertionFailedError" message="expected: 200 but was: 400"/></testcase>'
              '<testcase name="db"><error type="java.net.ConnectException" message="Connection refused"/></testcase></testsuite>')
        expect("at_tools run --report-only: падения по видам", p, at, ["run", "CMN-T120", "--report-only"], 1,
               "РЕЗУЛЬТАТ: failed · тестов 3 · упало 2", "ПАДЕНИЕ pay ПРОВЕРКА", "ПАДЕНИЕ db СТЕНД")
        if "run_status: failed" not in (p / ".gigacode/data/autotest/CMN-T120/PLAN.md").read_text(encoding="utf-8"):
            FAILED.append("at_tools run: run_status в шапке")
            print("FAIL at_tools run: run_status в шапке")
        # --- очередь ТК ---
        aq = ".gigacode/skills/orchestrator/scripts/autotest_queue.py"
        write(p, "tcs/new.md", TC.replace("CMN-T120", "NEW-T1"))
        write(p, "tcs/keys.txt", "NEW-T7\nNEW-T8\n")
        expect("next_action: каталог ТК -> очередь", p, na, ["autotest", "tcs"], 0, "ДЕЙСТВИЕ: очередь tcs")
        expect("autotest_queue add", p, aq, ["add", "tcs", "tc.md"], 0, "ДОБАВЛЕНО: 4 · УЖЕ БЫЛО: 0 · ВСЕГО: 4")
        expect("autotest_queue add: без дублей", p, aq, ["add", "tcs"], 1, "ДОБАВЛЕНО: 0")
        expect("autotest_queue status: ключ по файлу источника", p, aq, ["status"], 0, "готово 1 из 4")
        expect("next_action: очередь - первый пункт", p, na, ["autotest", "queue"], 0, "ДЕЙСТВИЕ: autotest-plan NEW-T7", "ЗАМЕТКА: очередь")
        expect("autotest_queue block", p, aq, ["block", "1", "ТК не найден в Zephyr"], 0, "ЗАБЛОКИРОВАН: 1")
        expect("next_action: очередь - после блока", p, na, ["autotest", "queue"], 0, "ДЕЙСТВИЕ: autotest-plan NEW-T8")
        expect("autotest_queue skip", p, aq, ["skip", "NEW-T8", "нет", "доступа"], 0, "ПРОПУЩЕН: 2")
        expect("next_action: очередь - файл ТК", p, na, ["autotest", "queue"], 0, "ДЕЙСТВИЕ: autotest-plan tcs/new.md")
        expect("autotest_queue skip по номеру", p, aq, ["skip", "3"], 0, "ПРОПУЩЕН: 3")
        expect("next_action: очередь пройдена", p, na, ["autotest", "queue"], 0, "ДЕЙСТВИЕ: очередь пройдена", "заблокированы: 1 NEW-T7")
        expect("autotest_queue clear", p, aq, ["clear"], 0, "ОЧЕРЕДЬ УДАЛЕНА: пунктов было 4")
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
        # --- ревью зависимостей ---
        d = project(tmp, "deps")
        dr = ".gigacode/skills/dependency-review/scripts/deps.py"
        expect("next_action: без файла сборки", d, na, ["deps"], 0, "ДЕЙСТВИЕ: агенты установлены")
        expect("next_action: ревью зависимостей без сборки", d, na, ["deps"], 0, "ДЕЙСТВИЕ: нельзя")
        expect("deps scan: нет сборки", d, dr, ["scan"], 1, "НЕТ СБОРКИ")
        write(d, "pom.xml", DEPS_ROOT)
        write(d, "core/pom.xml", DEPS_CORE)
        write(d, "tests/pom.xml", DEPS_TESTS)
        write(d, "mvnw", DEPS_MVNW)
        os.chmod(str(d / "mvnw"), 0o755)
        expect("next_action: ревью зависимостей", d, na, ["deps"], 0, "ДЕЙСТВИЕ: dependency-review", "новое ревью")
        expect("deps scan", d, dr, ["scan"], 0, "СБОРКА: Maven", "мультимодуль", "ТИП: автотесты", "ФРЕЙМ: 3.3.0, 3.4.1")
        rows = (d / ".gigacode/data/dependency/FINDINGS.md").read_text(encoding="utf-8")
        for rid, word in (("D-01", "[2.8,)"), ("D-03", "scope system"), ("D-04", "jackson-databind"), ("D-06", "jackson-core:2.14.0"),
                          ("D-07", "ещё раз"), ("D-08", "repositories"), ("D-09", "core -> tests -> core"), ("D-P1", "3.3.0"),
                          ("D-P2", "pvatf-docs"), ("D-23", "gson, jackson-databind")):
            if not any(("| " + rid + " |") in l and word in l for l in rows.splitlines()):
                FAILED.append("deps scan: нет " + rid)
                print("FAIL deps scan: нет строки " + rid + " с «" + word + "»")
        expect("next_action: ревью не закончено", d, na, ["deps"], 0, "deps_status: scanned")
        expect("deps tree", d, dr, ["tree"], 0, "опасных конфликтов 1", "ДАЛЬШЕ: deps.py next")
        expect("deps report: не всё проверено", d, dr, ["report", "--summary", "x"], 1, "НЕ ПРОВЕРЕНО")
        nxt = expect("deps next", d, dr, ["next"], 0, "СТРОКА: N-", "КАК ПРОВЕРИТЬ: references/rules.md, раздел D-")
        for _ in range(12):
            out = run(d, dr, "next")[1]
            if "ВСЁ ПРОВЕРЕНО" in out:
                break
            row = out.split("СТРОКА: ")[1].split(" ")[0]
            run(d, dr, "mark", row, "PASS", "--note", "selftest")
        expect("deps mark: неверный уровень", d, dr, ["add", "D-20", "--where", "core/pom.xml:9", "--note", "x", "--level", "HIGH"], 2, "НЕВЕРНО")
        expect("deps add", d, dr, ["add", "D-20", "--where", "core/pom.xml:9", "--note", "junit в compile", "--level", "INFO"], 0, "ДОБАВЛЕНО")
        expect("deps report", d, dr, ["report", "--summary", "Версии разъехались."], 0, "ОТЧЁТ:", "НАХОДКИ: критично 5",
               "ФРЕЙМ: D-P1, D-P2")
        report = (d / ".gigacode/data/dependency/DEPENDENCY-ANALYSIS.md").read_text(encoding="utf-8")
        for part in ("## Пересечения и конфликты зависимостей", "## 🔴 Критично", "## Требует внимания человека", "<details>",
                     "транзитивно, из дерева"):
            if part not in report:
                FAILED.append("deps report: нет «" + part + "»")
                print("FAIL deps report: нет «" + part + "»")
        expect("next_action: после отчёта - новое ревью", d, na, ["deps"], 0, "новое ревью", "прошлое:")
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
