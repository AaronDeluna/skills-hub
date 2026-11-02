# Stage 3 - Matrix «как сейчас -> как в PVATF» (section 2 of the migration map)

This file is a part of the skill `migration-map`. The general rules are in `references/core-rules.md`. The rules of the migration map and the order of stages are in `SKILL.md`.

This is the core of the migration map. Do the steps below for each usage pattern that the
inventory found. A usage pattern is the old framework, custom wrappers, or the way to write
tests, steps, pages, API calls, configs or reports:

1. Go through the list of technologies from the map passport, ONE technology at a time. For
   each technology, do two runs of the documentation subagent (`references/subagents.md`,
   section 1), one after the other.
   - In the prompt of Run A, write the «Якорь технологии» from `references/frame-topics.md`.
     The subagent starts with a query by the service name (`RestService`, `DatabaseService`,
     `KafkaService` ...) and returns a dictionary of documentation keywords.
   - Write the dictionary as the second line of the doc notes («Ключевые слова: ...»).
   - Write the questions of Run B with THESE words (the class and method names from the
     dictionary). Give the dictionary in the prompt.

   The runs:
   - **Run A - how the module works.** Use EXACTLY these questions (put in the technology):
     1. Какой модуль фрейма отвечает за <технология> и что он умеет?
     2. Какие зависимости и плагины нужно подключить для <технология>?
     3. Как настроить и сконфигурировать <технология>: файлы конфигурации, параметры,
        подключение к стенду?
     4. Как выполнить основные действия с <технология> (<действия, которые делает проект:
        напр. отправить запрос и разобрать ответ>): классы, методы, пример?
     5. Как выглядит тест или шаг с <технология> на фрейме - пример?
   - **Run B - what replaces the things that are in the project.** Ask one question for each
     usage pattern of this technology from the inventory. The question is about the ACTION,
     not about the name of the old class: «как <что делает старый код>». If there are more
     than 5 questions, do more than one run.
   IMMEDIATELY write each answer as a record `D-<tech>-<n>` into
   `.gigacode/data/migration/doc-notes/<технология>.md`. If the status is `найден частично` or `НЕТ В
   ДОКЕ`, work by the rules «Сначала конспект, потом сабагент» (ask again in a different way).
   - **The first questions of Run B are always about checks.** Read `references/matchers.md`
     and ask questions by it:
     (1) «Какой объект возвращает <операция технологии> и как у
     него вызвать проверку через .should()?»;
     (2) one question for each TYPE of check that the project really has for this technology
     (response code, JSON field, number of rows, cell value, message in a topic...). Use the
     name of the matchers class from the keyword table.

     You need the answers to replace the old asserts and the response DTOs (rule 5 of the
     migration map).
   - **The documentation does not describe the technology at all** (question 1 of Run A has
     the final answer `НЕТ В ДОКЕ` - 8 wordings, see `references/subagents.md`) -> this is
     `keep` (rule 4 of the migration map):
     - in the table «Технологии проекта», set the decision `keep` and the cause;
     - add the technology to the row «Остаётся как
     есть» of section 2;
     - do not do Run B. Do not write `G` and `L` rows for it;
     - do NOT make a question to the human.

     Go to the next technology.
   - **The documentation does not describe a PART of the technology** (it describes `db`, but
     not Oracle) -> write this part as a separate row in the table «Технологии проекта» (the
     label `db-oracle`, the decision `keep`). The other parts are migrated.
2. Write a row `G-<n>` into section 2 of the migration map:
   technology -> current state -> where and how many -> replacement in PVATF -> documentation
   basis -> sample file. Details:
   - technology: the label from the map passport. Use the same label for all items of one
     technology;
   - where and how many: the modules, the number of files;
   - replacement in PVATF: the **exact** names from the documentation;
   - documentation basis: `D-<tech>-<n>`;
   - sample file: an example file in the project.
3. Sometimes the documentation does not tell the replacement. Sometimes it does not describe
   the process to the end (it is not clear how to call or how to configure). Then FIRST use
   the table «Документация молчит» (below, after the DTO table). If a row fits - use its decision, there is no
   question. If no row fits -> go by the ladder of sources from `references/subagents.md`,
   section 4: the framework sources, then the sample project (the paths are in the map
   passport), then a question to the human with options in section 6 of the migration map.
   While there is no answer, write `НЕТ В ДОКЕ` in the replacement column.
   Do not choose a replacement yourself.
4. Mark the items that are already made on PVATF by the documentation as `уже PVATF`. Do not
   migrate them.
5. **Legacy to remove.** For each technology, write rows `L-<n>` into the table «Legacy под
   удаление» (section 2 of the migration map). These rows are all the old items that must
   disappear from the project COMPLETELY after the move of this technology to PVATF:
   - custom classes, wrappers (also the wrappers around RestAssured, JDBC, the Kafka client);
   - base classes, utilities, helpers;
   - custom assert classes and assertions, custom JSON comparators and parsers;
   - custom filters, interceptors and utilities for the logging of requests and responses (the
     framework logs the calls itself, `MR-43`);
   - all the old logging of the project (see below);
   - custom code that reads the settings, and the old connection settings files themselves
     (see below);
   - old packages, old dependencies and plugins in the build, old configs and resources.

   Technologies with the decision `keep` have no `L` rows.

   **The framework reads the connection settings.** The framework has its own settings files.
   It reads them and configures the services itself (`MR-47`). Thus, for each technology:

   (а) In `CONNECTIONS.md`, in the section of the technology, fill in the table «Перенос в
   фрейм». Write which files and keys the framework needs (from the answer to question 3 of
   Run A). For each key, write which value comes from the table «Сейчас в проекте».

   Move the values into the framework properties as data - to the place and in the way that
   the doc notes tell. Do not repeat how the project put them in before (profiles, `-D`,
   filtering, file selection in the code). That was necessary only to find the values. If
   there are more than one stand -> in the framework, these are different keys in its
   properties (a key with the stand, by the doc notes). Write the values of each stand with
   their own keys. Select the stand as the documentation describes.

   If a framework key has no value in the table:
   1) search again as in step 1а (items 4-6) with the words of this key, and look at the history:
      `git log --all -p -S "<слово>" -- '*.properties' '*.yml' '*.yaml' | head -60`;
   2) if you found it - add it to both tables;
   3) if you did not find it, and the key is optional or has a default value (by the doc
      notes) - write into «Чего фрейму не хватает»: `<ключ> - необязательный / по умолчанию <...>, D-...`;
   4) if you did not find it, the key is mandatory, and the project does the thing that needs
      this key - then the value comes from the outside. Find how (step 1а, item 3) and write
      `снаружи: <имя>`;
   5) if the project does not do this thing - the key is not necessary (question filter,
      check 3).
   Ask the human a question only if items 1-5 did not give a mandatory value, and the project
   clearly uses it. The question must also pass the «Фильтр вопросов».

   (б) In `L`, make rows for the old code that reads the settings and makes the connections,
   and for the old settings files. Find them:
   ```
   grep -rlE "ConfigFactory\.create|new Properties\(\)|ResourceBundle\.getBundle|System\.(getProperty|getenv)\(|@Value\(" --include=*.java --include=*.kt <src>
   find <src> -name "*Config*.java" -o -name "*Propert*.java" -o -name "*Settings*.java" | head -40
   ```
   The move of the values into the framework settings files is in the substep `env` of the
   technology (phase 2). The removal of the old reading code and the old files is in its `cleanup`.

   **Custom configuration classes** (`DbConfig`, `KafkaConfig`, `ApiConfig`, a class with
   hosts) are not necessary after the migration - the framework does their work. Each such
   class is an `L` row:
   - if it serves one technology -> remove it in the `cleanup` of this technology;
   - if it is common for more than one technology -> in the `cleanup` of each technology, add
     the step «убрать из <Класс> поля и методы
     <технология>». Put the `L` row for the class itself into the unit of the last of these
     technologies.

   The framework configuration classes (`*EnvironmentConfiguration`, `*ServiceConfiguration`)
   do not go into `L`.

   **Logging - always in `L`, technology `common`.** In the framework, the logging is one
   file `simplelogger.properties` in the test resources (the simple logger of SLF4J). Nothing
   more is necessary. Find all the old logging items and make `L` rows for them:
   ```
   find . \( -name "logback*.xml" -o -name "log4j*.xml" -o -name "log4j*.properties" -o -name "logging.properties" \) -not -path "*/target/*" -not -path "*/build/*"
   grep -rnE "logback|log4j|slf4j-(log4j12|reload4j|jdk14)|jul-to-slf4j|jcl-over-slf4j" --include=pom.xml --include=*.gradle --include=*.gradle.kts --include=*.toml .
   grep -rlE "import (org\.apache\.logging\.log4j|org\.apache\.log4j|java\.util\.logging|ch\.qos\.logback)" --include=*.java --include=*.kt <src>
   ```
   - Logger configurations and dependencies - `L` rows of the type «конфиг» and «зависимость».
   - Custom appenders, filters, formatters - rows of the type «класс».
   - The files from the third command (the code uses a different logger, not SLF4J) - write
     them into the `usage` substeps of their technologies with the step «убрать ручное
     логирование запросов и ответов; оставшиеся сообщения перевести на `org.slf4j.Logger`».

   **The file `simplelogger.properties` is mandatory.** Check if it exists:
   `find . -name simplelogger.properties -not -path "*/target/*" -not -path "*/build/*"`.
   If it does not exist -> the substep `env` of the technology `common` in phase 2 makes it.
   Write into the unit card the step «создать `<каталог ресурсов тестов>/simplelogger.properties`»
   and the file content WORD FOR WORD, six lines:
   ```
   org.slf4j.simpleLogger.defaultLogLevel=INFO
   org.slf4j.simpleLogger.showShortLogName=true
   org.slf4j.simpleLogger.showDateTime=true
   org.slf4j.simpleLogger.dateTimeFormat=HH:mm:ss:SSS
   org.slf4j.simpleLogger.logFile=System.out

   #org.slf4j.simpleLogger.log.ru.sber.at=INFO
   ```
   (If the file in the doc notes `D-common-6` or in the sample project is different - use that
   file.)

   **The logger dependencies in the build are mandatory** - without them, nothing reads the
   file. In the same step of the unit card, write: in `pom.xml` (in `<dependencies>`, and if
   there is a common `<dependencyManagement>` - also there), add WORD FOR WORD
   ```xml
   <!-- Logger -->
   <dependency>
       <groupId>org.slf4j</groupId>
       <artifactId>slf4j-simple</artifactId>
       <version>${log.version}</version>
   </dependency>
   <dependency>
       <groupId>org.slf4j</groupId>
       <artifactId>slf4j-api</artifactId>
       <version>${log.version}</version>
   </dependency>
   ```
   and the property `<log.version>2.0.16</log.version>` in `<properties>` (if the sample project
   or the doc notes have a different version - use that version). For Gradle - the same two
   dependencies `org.slf4j:slf4j-simple` and `org.slf4j:slf4j-api` with one version variable.
   If they already exist - do not duplicate them. Only check that both have the same version.

   If the project has more than one module with tests -> the file is necessary in the test
   resources of each module. If the file already exists -> write into the unit card the step
   «проверить, что в нём задан `defaultLogLevel`». Do not overwrite the content. The old
   logger configurations and dependencies are removed in phase 4 (final cleanup), when the
   code does not use them.

   **Check the build in ALL places where it keeps dependencies.** Make a separate `L` row for
   each place that you find:
   - Maven: `<dependency>` and `<plugin>` in `pom.xml` of each module; `<dependencyManagement>`
     and `<pluginManagement>` in the parent `pom.xml`; version properties in `<properties>`
     (`<restassured.version>` and others); `<exclusions>` written for the old library;
     profiles `<profile>` that add it;
   - Gradle: the blocks `dependencies` and `plugins` in `build.gradle(.kts)` of each module;
     `gradle/libs.versions.toml` (the lines in `[versions]`, `[libraries]`, `[bundles]`,
     `[plugins]`); `gradle.properties` (versions); `buildSrc/` and convention plugins;
     `ext { ... }` with versions; `settings.gradle(.kts)`;
   - configs and resources of the old technology in `src/*/resources` (properties, yml, templates).
   The command to find all places: `grep -rn "<artifactId или имя библиотеки>" --include=pom.xml
   --include=*.gradle --include=*.kts --include=*.toml --include=gradle.properties .`
   Principle: we have the framework and its implementation. Nothing that was added on top of
   the old technology is necessary. Do not keep anything «на всякий случай» or «для совместимости».

6. **Target state of the technology.** For each technology with `migrate`, write a block
   `T-<tech>` into section 2 of the migration map (the template is in
   `references/map-template.md`). The block shows how the code of this technology must look
   AFTER the migration. The only source is the doc notes `doc-notes/<технология>.md`:
   - the test example from Run A, question 5;
   - the configuration - question 3;
   - the checks - the record about matchers.

   If this is not sufficient, ask the subagent again: «как выглядит полный тест <технология> на фрейме от
   настройки до проверки». The block has these lists:
   - **«Что будет»:** which classes and files stay or appear in the project, and why (by the
     documentation: the framework configuration, the service configuration, the test).
     - In the block `T-common`, this list must have a **base test class**. It is a class only
       with the annotations that connect the framework (the framework extension and the
       environment configuration - the names from `D-common-4`). The test classes extend it.
       The framework annotations are not repeated in each test.
     - If the project already has a base test class -> it stays with its name. The clients,
       helpers and methods from it go into `L` or into the steps;
   - **«Что вызывается и кем»:**
     (а) the TEST calls the steps and checks the result through `.should(...)` - list the
     matchers with the IDs of the doc notes records;
     (б) the STEPS call the framework - list the exact names of the framework mechanisms for
     the actions with the IDs of the records.

     Actions that more than one test needs, or that need a preparation, are always in the
     steps. A single short call to the framework in the body of one test is allowed. Helper
     methods in the test class are not allowed;
   - **«Слой шагов»:** where the logic of the actions is (sending requests, DB queries, Kafka
     reading). Write the package and the step classes by subject areas. Write how the
     documentation tells to write them (the section «Как работает Flow и ConfigurationService».
     If the doc notes do not have it, ask the subagent). For each step class, write which
     actions it will have. If the project has no step classes -> they are made: add them to
     «Что будет».
     **If the step style in the map passport is `flow`:** the step layer is the flow classes
     (the record `D-common-7`). For each flow class, write:
     - which scenario or subject area it serves;
     - which ready interfaces of the framework technologies it uses (the record `D-common-8`)
       and what it takes from them ready;
     - which own action methods and check methods it has;
     - what it keeps between the steps.

     The test in «Что вызывается
     и кем» is a chain of FlowRunner steps. Each step calls one method of the flow;
   - **«Как проект пользуется технологией сейчас»:** 1-3 lines - what it calls, where and how
     (for example: «вызывает заглушённые REST-эндпоинты Сбермок по адресу из
     `rest.properties`, ключ `sbermock.host`; заглушки включает API управления»). After the
     migration, the project uses the technology IN THE SAME WAY. Only the mechanism changes to
     the framework mechanism. Do not plan what the framework cannot do: each action from «Что
     вызывается и кем» must be in the doc notes;
   - **«Данные подключения»:** a reference to the section of the technology in `CONNECTIONS.md`
     and one line: how many files and keys of the framework, and do all of them have values
     («`CONNECTIONS.md`, `## kafka`: 2
     файла фрейма, 9 ключей, значения есть у всех»). The executor takes the values from there
     and never asks the human;
   - **«Данные проекта, которые переезжают как данные»:** endpoint addresses and paths, request
     bodies and the DTOs that make these bodies, SQL queries, topic names, test data. The tests
     need them, and they stay. But they are where the documentation tells, not in the old
     classes. **RESPONSE DTOs are not in this list:** in the framework, you check the response
     through `.should(...)` on the validatable object. Do not convert it into a custom object;
   - **«Чего НЕ будет»:** list by name the old layer classes of this technology from the
     inventory (custom clients, base classes, wrappers, helpers, asserts). Also list the
     response DTOs that are necessary only to compare fields with asserts. They do not move -
     they are removed (also add them as `L` rows). How to find response DTOs:
     `grep -rnE "\.as\([A-Z][A-Za-z0-9_]*\.class\)|readValue\(|fromJson\(" --include=*.java <src>` -
     the classes from these calls. For DTOs, models, Jackson and JAXB, use only the table
     below. Do not ask the human about them.

   **Decision table «DTO, Jackson, JAXB».**

   | In the project | Decision (always this, not a question) |
   |---------------|-----------------------------------|
   | A response DTO or model: the response is parsed into an object (`.as(X.class)`, `readValue`, `fromJson`, `unmarshal`, `JacksonHelper.parse...`) to check its fields later | Remove it. The response of the request is already in the validatable object of the framework. Call `.should(...)` on it with matchers by the path to the field. Deserialization for checks is not necessary |
   | One value from the response is necessary later in the scenario (an id for the next request, a token) | Get it with one call on the validatable object, by the way from the doc notes. A DTO is not necessary for this |
   | A DTO or model that makes the BODY of a request or message (also JAXB XML models) | It stays as project data, with the Jackson and JAXB annotations. Give the body to the framework request as the doc notes show |
   | The same model for the request body and for the response parsing | It stays as the request body model. Remove the response parsing into it. The checks use `.should(...)` |
   | A custom wrapper over Jackson or JAXB (`JacksonHelper`, `XmlUtils`, `JsonUtils`) | Remove the response parsing methods together with their calls. The methods that make request bodies or read test data files stay while something uses them. If the class becomes empty - remove it |
   | The documentation has no JSON/XML deserialization into an object, no way to get the response body as a string, and does not mention Jackson or JAXB | This is not a gap in the documentation: the framework does not need it. You check the response through `.should(...)`. Do not ask a question |
   | There is no matcher for the necessary field | A standard assert (`MR-29`) on the value that you got from the validatable object (not through a DTO), and a row in «Входящие» |

   **Decision table «Документация молчит».** If the documentation does not describe something,
   this is almost never a question. The framework does not have to describe each library of
   the project. First, find a row here. If a row fits - write the decision into the migration
   map (rows `G`, `L`, block `T`) and go on. Do not write anything into section 6.

   | In the project, and the documentation does not describe it | Decision (always this, not a question) |
   |----------------------------------------------|-----------------------------------|
   | A general-purpose library, not a wrapper over a framework technology: Lombok, Apache Commons, Guava, Awaitility, test data generators and others | It stays as it is, with its dependencies, plugins and build settings (`annotationProcessorPaths` and others). New code can use it. Do not rewrite it in «чистую Java» |
   | A mapper generator (MapStruct and others) that serves only response DTOs | It goes away together with these DTOs (the DTO table): `L` rows for the mappers, the dependencies and the plugins |
   | A driver or client of a specific DBMS, broker or protocol that the documentation does not describe (Oracle `ojdbc`, but the documentation has only PostgreSQL) | This part is `keep` (rule 4 of the migration map): the driver, its dependency and the code stay as they are |
   | Custom annotations and report labels: Allure annotations of the project or of an external jar (`@Team`, `@Regress`, `@AllureId`, `@Link`, `@LabelAnnotation`) | They stay as they are. Do not change the markup of the tests. If the labels disappear from the report after the framework is added - the review finds it. Do not ask a question before |
   | Reading of test data files (JSON, XML, CSV) from resources, and the documentation has no standard way or the section is «в разработке» | The custom file reading stays. Make the helper smaller: only file reading (no response parsing). Add a row in «Входящие»: «вернуться, когда в доке появится штатный способ» |
   | DB result rows are collected into a DTO (`RowMapper`, `BeanListHandler`, a custom `ResultSet` mapper) to check fields | The same as a response DTO: remove the mapping. The checks are DB matchers by the column name from the doc notes. One value for later in the scenario - one call from the doc notes |
   | A technology, module or infrastructure that the tests really do not use (0 callers, 0 tests: a Selenium wrapper without UI tests) | Dead code: `L` rows. Remove it with its dependencies and configs. Do not add a framework module for it. Do not choose between modules |
   | Logging level and logger settings | Always `simplelogger.properties` (the logging step above). Log4j, Logback, their configs and logger wrappers - `L` rows |
   | More than one stand (IFT, DEV...) | In the framework, stands are different keys in its properties (value sets under a prefix with the stand name, by the doc notes). The values of each stand come from `CONNECTIONS.md` with their own keys. The old stand selection (profiles, `-D`, file selection in the code, `@BeforeAll`, static fields) - `L` rows |
   | The key names of a standard library (`ssl.keystore.location`, `ssl.truststore.password`, `security.protocol`, `sasl.*`, `bootstrap.servers`) are not in the framework documentation | These are standard client names (Kafka, JDBC): write them as they are, with the prefix from the doc notes. The values come from `CONNECTIONS.md` |
   | The framework needs something that the project does not have and that you cannot get from the project (a service account token instead of a login and password) | This is not a question of the migration map. Make the key with the value `снаружи: <ИМЯ_ПЕРЕМЕННОЙ>` (the name comes from the key). In «Входящие», write `решить человеку: получить <что>`. If the documentation tells who has it - write it. The migration does not stop |
   | The example in the documentation does not cover the case completely | Do as the example shows. For the missing parts (values, names, data), do as the project does now |

   If no row fits -> use the ladder of sources (item 3 above), then the «Фильтр вопросов».

   Ask the documentation about checks as `references/matchers.md` describes (it tells how the
   checks work in the framework and which words to use in the question). The matcher names
   for the block `T` come from the documentation answer, with the ID of the doc notes record.

   In the block `T-common`, you must write this: the framework configuration classes
   (`ApiEnvironmentConfiguration` and the others) are in the package `config`. Use the package
   that the project already has (`src/main/java` or `src/test/java`). If it does not exist, use
   the new package `<базовый пакет>.config`. Write the exact path.

   **Gate of the target state.** The lists «Что будет», «Что вызывается и кем» and «Слой
   шагов» must have the EXACT names from the doc notes (class, method, matcher) with the ID of
   the record. Lines such as «использовать сервис фрейма», «проверять через matchers» without
   names are not a target state. If there are no names because the sources were not
   sufficient -> use the ladder of sources (`references/subagents.md`, section 4), up to a
   question to the human. Do not split a technology with an incomplete target state into units.

   Rule to tell the difference: an old class has DATA (what we call, what we send, what we
   expect) and MECHANICS (how to call, how to parse, how to compare). Keep the data. The
   framework replaces all of the mechanics.

**Mark the technologies and do not do everything in one chat.** A technology is finished
when the doc notes are written and the rows `G`, `L` and the block `T` for it are added. Then
add its label to the row «Этап 3 сделан для технологий» in section 0 of the migration map. If you did
4 technologies in this chat, and the map passport has more -> stop and say: «Откройте новый
чат и напишите: `/orchestrator Продолжи миграцию`». In the new chat, continue from the first
technology that is not in this row.

Check completeness:
- each technology from the map passport is in the row «Этап 3 сделан для
  технологий», and each has the decision `migrate` or `keep`;
- each package from the top imports in `inventory/*.md` that is not JDK and not PVATF must be
  in a row `G-<n>` or in the list «остаётся как есть» (with the cause).

Mark Stage 3 `[x]`, `map_stage: 4`.

