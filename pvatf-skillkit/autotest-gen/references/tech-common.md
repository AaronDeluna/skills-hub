# Общие правила справок технологий

Часть скилла `autotest-gen`. Справку `tech-<группа>.md` читает агент `pvatf-generator`; этот
файл - для основного чата: что общее у всех справок и как они устроены.

1. **Справка - подсказка, а не основание.** Имена классов и методов в справках взяты из
   примеров набора. В код они попадают, только если есть в конспекте (`D-<tech>-<n>`) или в
   коде проекта. Нет - агент возвращает `blocked` с вопросами документации.
2. **Статусы фрагмента** - только `ok`, `stub`, `blocked` (других нет: не `DECLARED_ONLY`,
   не `PARTIAL`, не `SUCCESS`).
3. **Проверки** - matchers фрейма в `.should(...)` у объекта, который вернул фрейм.
   `assertEquals`, `assertThat`, `assertTrue`, `assertNotNull` и AssertJ - запрещены во всех
   технологиях (правило MR-29). Нет matcher в конспекте - `blocked`, вопрос «каким matcher
   проверить <что>».
4. **Константы** - по колонке «Источник» плана, одинаково во всех технологиях: значение
   `TEST_CLASS_STATIC_FINAL` - поле `private static final`; `PROPERTIES_FILE` - ключ
   настроек, значение в коде не пишется; `TESTDATA_FILE_REF` - файл в `src/test/resources/`.
5. **Сервис фрейма** получается один раз в классе шагов (поле или один приватный метод), не
   в каждом методе (MR-35).
6. **Нет DTO ответа.** Значение для следующего шага - одна переменная с явным типом,
   способом из конспекта (MR-41, MR-48).
7. **Каждый шаг тест-кейса** - комментарий `// Шаг <номер>: <действие>` в теле фрагмента;
   без него `at_tools.py check` считает шаг не сгенерированным.

| Группа плана | Справка | Метки конспекта |
|--------------|---------|-----------------|
| `integration` | `tech-integration.md` | `rest`, `grpc`, `graphql`, `websocket` |
| `db` | `tech-db.md` | `db`, `opensearch` |
| `kafka` | `tech-kafka.md` | `kafka` |
| `ui` | `tech-ui.md` | `ui` |
| `mobile` | `tech-mobile.md` | `mobile` |
| `logs_metrics` | `tech-logs-metrics.md` | `audit`, `journal`, `abyss`, `metrics`, `sup` |
| `tools` | `tech-tools.md` | `fixtures`, `timeouts`, `testcontainers`, `sbermock`, `openshift`, `dataconverter`, `toggler`, `launcher` |
| `other` | `tech-other.md` | `value`, `session`, `invocation` |
