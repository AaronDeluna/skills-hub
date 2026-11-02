# Sections of the PVATF framework documentation (reference for queries)

This is the table of contents of the framework documentation: the sections that it has.
This file has ONLY the section names. It does not tell how to use a technology, which classes,
dependencies and settings to use. Get this information only from the documentation, through the subagent.

Why you need this list:
1. **Queries to the documentation.** The section name is the most exact text for a query.
   Give it to the subagent in the line «Раздел документации».
2. **Technology labels.** Name the project technologies with the labels from this list.
   Do not make up your own labels if a suitable label exists.
3. **Does the framework have the technology.** If the technology is not in the list -> the
   framework possibly does not support it. This is NOT a final decision: the list can be old.
   Ask the documentation in all cases.
   If the documentation has nothing about the technology -> the decision is `keep`: the
   technology is not migrated and stays on the old implementation.

In the query, write the section name character for character, as it is here.

## Technology anchor - the first query to the documentation

Each technology in the framework has its own service. The service name is the **anchor**:
the very first query to the documentation about the technology contains only this name.
The answer shows which words the documentation uses (classes, methods, settings).
Ask the next questions with these words.

| Label | Anchor | Source of the name |
|-------|--------|--------------------|
| `rest` | `RestService` | from the documentation |
| `db` | `DatabaseService` | from the documentation |
| `kafka` | `KafkaService` | from the documentation |
| `sbermock` | `SberMockService` | assumption from the pattern |
| `grpc` | `GrpcService` | assumption from the pattern |
| `graphql` | `GraphQlService` | assumption from the pattern |
| `websocket` | `WebSocketService` | assumption from the pattern |
| `openshift` | `OpenShiftService` | assumption from the pattern |
| `ragas` | `RagasService` | from the documentation |
| other labels | `<Название технологии>Service` | make it yourself from the pattern |

The anchor is a word FOR THE QUERY, not for the code. An «Предположение» (assumption) can be different from the
real name. Then the anchor query returns little or wrong information. This is normal: the second
anchor query (the section name) shows the real service name.
Put into the code only the name from the documentation answer.

## Main concepts (label `common`)

| Documentation section | Topic |
|-----------------------|-------|
| Структура проекта | layers, packages, modules of the autotest project |
| Что такое Service? | framework services - the main building block |
| Работа с Environment | environment, run configuration |
| Как работает Flow и ConfigurationService | flow interfaces, configurations |
| Exceptions | framework exceptions |
| Logging | logging |
| Matchers and Conditions | checks and conditions |

## Framework services

| Label | Documentation section | What in the project belongs here |
|-------|-----------------------|----------------------------------|
| `fixtures` | Сервис для работы с Fixtures | data preparation and cleanup, before/after |
| `timeouts` | Сервис для работы с Таймаутами | waits, retries, Awaitility, sleep |
| `value` | ValueService | substitution and generation of values |
| `rest` | Работа с Rest API | RestAssured, HTTP clients |
| `kafka` | Работа с Kafka | kafka-clients, producer/consumer |
| `db` | Работа с Базами Данных | JDBC, sql2o, SQL queries |
| `sup` | Работа с СУП-Параметрами | СУП parameters |
| `sbermock` | Работа с SberMock | mocks, stubs |
| `grpc` | Работа с gRPC | io.grpc |
| `sessions` | Работа с Сессиями | authorization, sessions, tokens |
| `audit` | Работа с Единым Аудитом | check of audit events |
| `openshift` | Работа с OpenShift и Kubernetes | pods, deploy, kubernetes-client |
| `opensearch` | Работа с OpenSearch/ElasticSearch | search in logs and indexes |
| `metrics` | Работа с хранилищем метрик Thanos/Victoria Metrics | metrics, monitoring |
| `journals` | Работа с Журналами ЕФС и ППРБ | ЕФС journals, ППРБ journals |
| `ui-selenide` | Работа с UI Selenide | Selenide, Selenium |
| `ui-playwright` | Работа с UI Playwright | Playwright |
| `websocket` | Работа с WebSocket | WebSocket |
| `appium-android` | Работа с Appium Android | Android mobile tests |
| `appium-ios` | Работа с Appium iOS | iOS mobile tests |
| `graphql` | Работа с GraphQL | GraphQL |
| `allure` | Работа с Allure2 | reporting, steps, attachments |
| `invocation` | Работа с Invocation | call wrappers, retries |
| `testcontainers` | Работа с TestContainers | containers in tests |
| `dataconverter` | Работа с DataConverter | data conversion, JSON/XML |
| `datasource` | Работа с DataSource | sources of test data, Stash |
| `abyss` | Работа с PVM-ABYSS | PVM-ABYSS |
| `toggler` | Работа с Toggler | feature-toggle |
| `launcher` | Работа с Launcher | ФП Launcher |
| `sbercms` | Работа с SberCMS | SberCMS |
| `scheduler` | Работа с TaskScheduler | task scheduler |
| `techbreak` | Работа с TechBreak | technical breaks |
| `history` | Работа с Историей Операций | operation history |
| `smartcare` | Работа с SmartCare | SmartCare |
| `ragas` | Работа с Ragas - тестирование агентов | testing of AI agents |

## Test frameworks (label `runner`)

| Documentation section |
|-----------------------|
| Работа с TestNG |
| Работа с Cucumber7 |
| Работа с Spring |
| Работа с Ванильной Java |
| Работа с Junit4 |
| Работа с Junit5 |

Select the section by the test framework of the project from the map passport.

## Additional materials (label `common`)

| Documentation section |
|-----------------------|
| Разметка автотестов (Allure-Annotations) |
| Пакетная разметка автотестов (Allure-Markup-Tool) |
| Настройка выгрузки в Jira на Gradle |
| Работа с Драфтами (проект-пример) |
| Библиотека Mockito для разработки Unit-тестов |
| Expectations |
| JsonEditor |
| Часто задаваемые вопросы |
| Типичные ошибки при сборке |

## What is not in the list

Examples: OpenTelemetry, RabbitMQ and other queues except Kafka, file storages, mail.
For them, item 3 at the top applies: ask the documentation; if nothing is found - `keep`.
