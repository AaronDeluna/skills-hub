# Template of the architecture plan

Path: `.gigacode/data/migration/ARCHITECTURE.md`. This is the plan of the project AFTER the
migration: which packages, which classes, and what each class does. `migration-map` makes it
at Stage 4. `migration-step` reads it before each unit. Fill in only
`<...>`. Do not change the headings and the column names.

```markdown
# Архитектурный план · <имя проекта>

## 1. Слои и кто кого вызывает

Основание: <D-common-n>

| Слой | Пакет | Что в нём лежит | Кого может вызывать |
|------|-------|-----------------|---------------------|
| тесты | <пакет> | тест-классы: только сценарий | шаги |
| шаги | <пакет> | действия предметной области с `@Step`: собирают данные запроса, вызывают базовый слой, возвращают валидируемый объект | базовый слой технологии, данные |
| базовый слой технологии | <пакет> | один класс на технологию (`RestSteps`, `DbSteps`, `KafkaSteps`): общие операции - get/post/put/delete, выполнить SQL, отправить и прочитать сообщение; только здесь обращение к клиенту фрейма | сервисы фрейма |
| данные | <пакет> | эндпоинты, тела запросов, запросы SQL, тестовые данные | - |
| конфигурация | <...>.config | классы конфигурации фрейма | - |

## 2. Дерево пакетов после миграции

<корень исходников>
  <пакет>/            - <что лежит, 3-6 слов>
    <подпакет>/       - <...>

## 3. Классы

Одна строка - один класс. Тест-классы и классы данных поимённо не перечисляй: одна строка
на пакет («тест-классы пакета <...>: <n> файлов»).

| Класс | Пакет | Слой | Технология | За что отвечает (одно предложение) | Кто вызывает | Откуда | Юнит |
|-------|-------|------|------------|------------------------------------|--------------|--------|------|
| <Имя> | <пакет> | шаги | rest | <отправляет запросы к API заказов> | <тесты пакета ...> | новый / остаётся / вместо <СтарыйКласс> | <M-nnn, заполняется на Этапе 5> |

## 4. Чего в проекте не будет

Старые классы, которые исчезают, - в таблице «Legacy под удаление» карты (строки `L`).
Здесь - только общие запреты этого проекта: <например: нет базовых классов с клиентами и
методами запросов, нет классов Utils и Helper, нет своих классов проверок>

## 5. Добавлено по ходу миграции

Заполняет `migration-step`, когда в плане не нашлось класса с нужной ответственностью.

| Класс | Пакет | Слой | Технология | За что отвечает | Почему не подошёл ни один класс из раздела 3 | Юнит |
|-------|-------|------|------------|-----------------|----------------------------------------------|------|
```

## Rules to fill in section 3

Apply these rules to EACH row before you write the class into the plan.

1. **One responsibility.** The column «За что отвечает» is one sentence with one action verb.
   If the sentence has «и», «а также», «разное», «общие», «вспомогательные» ->
   these are two classes or an unnecessary class: divide it or remove it.
2. **No repetitions.** The plan does not have two classes with the same responsibility or with
   overlapping responsibilities. One action (a request to one API, a query to one table, a send
   to one topic) is in ONE class. If you found an overlap -> join the classes into one class.
3. **The class has a caller.** The column «Кто вызывает» is not empty. If there is no caller ->
   you do not need the class. Do not plan it «на будущее» (for the future). For a new step class, this
   column contains the classes that do this action themselves now (the technology consumers).
   At Stage 5, each of them gets a `usage` unit that moves it to this class.
4. **The name tells what the class does.** Do not use: `Utils`, `Helper`, `Common`, `Manager`,
   `Base...`, `Abstract...` for shared code, `...Wrapper` around a framework service.
   Exception: the base test class (see rule 8).
5. **One class - one technology.** A step class works with one technology and one subject
   area (orders API; client tables). A scenario that needs two technologies is built in the
   test from the steps of two classes, not in a class «всё сразу» (everything at once).
   Exception: a flow class (style `flow`, see below). It runs one scenario and can
   work with a number of technologies of this scenario.
6. **Not one class for everything.** If the technology has more than 15 actions, or the class
   becomes longer than 500 lines -> divide the class by subject area. Do it now, in the plan, not later.
7. **Do not make too many classes.** Plan a new class only if the framework does not cover its
   responsibility and no other class of the plan covers it. If the framework covers it, you do not
   need the class at all.
8. **The plan always has the base test class.** This class has only the annotations that
   connect the framework (framework extension, environment configuration). The test classes
   extend it, so that each test does not repeat the annotations. There is one base test class
   for each environment configuration.
   - If the project already has a base test class -> it stays in the plan with its name.
     «Откуда» is `остаётся`. «За что отвечает» is «подключает фрейм и конфигурацию
     <имя> для тестов». Everything else from it goes into the steps or is removed.
   - If not -> a new `BaseTest` in the root test package.
   The base test class has no clients, no request methods and no checks.
9. **The plan agrees with the target picture.** Section 3 has each class from «Слой шагов» and
   «Что будет» of the `T` blocks of the map. Also, section 3 has no technology class that is not in the `T`
   block of this technology.
10. **No unnecessary layers.** Each technology has exactly one class of the base layer.
   The plan has no facade classes that only pass calls to another class, no nested classes,
   and no classes «всё общее» (everything shared): `...Common`, `...Helper`. Sometimes the project already
   has tens of methods with the same body (the same request with different paths). In this case,
   the plan has one method of the base layer and thin subject-area steps for them (`MR-49`).

## If the step style is flow («Если стиль шагов - flow»; map passport line «Стиль шагов»)

The tests use the FlowRunner of the framework (take the exact names only from the record `D-common-7`).
How it works:

- **Test** - a chain of named steps: start the flow -> step «<название>» -> step
  «<название>» -> run. Each step calls ONE method of the flow class. The test has no own
  logic. Take the step names from the old test (the text of `@Step`, the comment «Шаг 1»).
  Do not change the order of the steps.
- **Flow class** - the step layer. It gets the framework clients (one time, in the constructor).
  It contains:
  - action methods (send a request, select from the DB, send to Kafka);
  - check methods (a check with `.should(...)` of the result from the previous step).
  Between steps, it keeps the data that the next steps need (the validatable response):
  in a field or in the way that the documentation shows.

- **The flow is built from parts.** The flow class implements the flow interface of the
  framework and connects the necessary parts with `implements`:
  - ready interfaces of the framework technologies (for REST, for the DB and other; the list
    and the methods are in the record `D-common-8`). They already give ready steps: run a DB
    query, a query from an SQL template, and other steps. Do not repeat with your own code
    what the framework gives;
  - own connectable parts of the project: an interface or a step class with the logic of one
    subject area («действия с API заказов»). Write the logic in them one time. Each flow that
    needs this logic connects the part.
  In section 3 of the plan, write a separate row for each own connectable part. For the flow class,
  list in the column «За что отвечает» the parts that it connects.

In section 1 of the plan, write the layer «шаги» as «флоу». In section 3, for each flow class,
write the scenario in the column «За что отвечает»: «ведёт сценарий создания заказа: запрос в API,
проверка записи в БД, проверка сообщения в Kafka».

How to find which flows you need:

1. Write down the test scenarios: which steps the test classes have and in which order
   (2-3 examples for each test package; do not read all tests).
2. **One flow - one group of scenarios of one subject area** (orders, clients,
   payments). The tests of one test class usually go into one flow.
3. Do NOT make: one flow for all of the project; a separate flow for each test; two flows with
   the same methods; your own class that repeats the ready steps of the framework. If two flows
   need the same action -> move it into one connectable part (your own interface or step
   class), and both flows connect it.
4. If a flow has more than 15 methods or is longer than 500 lines -> divide it by scenarios.
5. Make a flow that works with a number of technologies in the unit of the LAST of these
   technologies. The tests for a number of technologies use the same rule.
6. You do not have to move tests without steps (one request - one check) into a flow:
   a usual step class is allowed for them. Write this in the plan.
