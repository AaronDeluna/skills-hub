# Stage 2 - Map passport and inventory of the project

This file is a part of the skill `migration-map`. The general rules are in `references/core-rules.md`. The rules of the migration map and the order of stages are in `SKILL.md`.

Read `references/inventory-guide.md` and work by it. What you must get:

0. **Technologies of the project** (a table in the map passport). First, read
   `references/frame-topics.md`. It is the list of sections of the framework documentation
   with technology labels (`rest`, `kafka`, `db`, `openshift` ...). Then use one of the two
   branches:
   - **Branch A - the human HIMSELF named the technologies** (in the request, or the
     orchestrator gave them): use his list as it is. Do NOT start the technologies subagent.
     In the column «Откуда», write `от пользователя`.
   - **Branch B - the technologies are not named:** start the subagent for the technologies of
     the project by `references/subagents.md` (section 3). Use the prompt word for word. Write
     its report as it is into `.gigacode/data/migration/inventory/technologies.md`. Take the
     list of technologies from the report. In the column «Откуда», write `сабагент`. Do not
     search the project for technologies yourself.

   For each technology, fill in a row of the table «Технологии проекта» in the map passport:
   - **Label** - from `frame-topics.md`. If the technology is not in the list -> make a label
     yourself in Latin letters (for example, `otel`, `db-oracle`). Use this label everywhere
     after this. For general items that are not about one technology, use `common`.
   - **Documentation section** - the name of the section from `frame-topics.md`, or `нет в списке`.
   - **Decision** - for now, `migrate`. Stage 3 sets the final decision: if the documentation
     does not describe the technology -> `keep` (rule 4 of the migration map).
   - **Order** - the number in which the technologies are migrated (rule 6 of the migration
     map). If the human gave the order - use it. Else, use this order and skip the items that
     are not in the project:
     1) `rest`; 2) `db`, `datasource`; 3) `kafka`; 4) `graphql`, `websocket`; 5) `grpc`;
     6) the other services of the framework (`sbermock`, `sessions`, `audit`, `opensearch`, `metrics`,
     `journals` and others); 7) `ui-selenide`, `ui-playwright`, `appium-android`,
     `appium-ios`; 8) `openshift`, `testcontainers` - last.
1. **Map passport** (section 1 of the migration map). Write:
   - the build system and the runner (wrapper or system);
   - the modules;
   - the language(s);
   - the test framework (from the imports of `@Test`, not from the dependencies);
   - the main branch;
   - the commands to compile and to run the tests;
   - can the tests run locally at all (or is a test stand necessary);
   - the code style / checkstyle;
   - the convention for branches and commits.

   **Execution mode** (a row of the map passport): `менеджер` is the default. In manager mode,
   a separate executor subagent with a clean context does each substep. The main chat keeps
   the unit card, checks and commits. Use `сам` only if the human asked for it («подшаги
   делай сам», «без сабагентов»). If GigaCode subagents cannot change files, the executor
   changes the mode itself at the first substep. Do not check this here.

   **Java version - mandatory.** The framework needs Java 17 or higher. Find which version
   the build sets and WHERE (all places). Write it into the map passport:
   ```
   grep -rnE "maven\.compiler\.(source|target|release)|<java\.version>|<source>|<target>|<release>|sourceCompatibility|targetCompatibility|languageVersion|jvmTarget|JavaVersion\." --include=pom.xml --include=*.gradle --include=*.kts --include=gradle.properties .
   java -version 2>&1 | head -1
   ```
   - if the version in the build is 17 or higher -> write `Java <n> - менять не надо`;
   - if the version is lower than 17 (8, 11 ...) -> write `Java <n> -> нужно 17` and the list
     of places. At Stage 5, this becomes the FIRST unit of the migration map (see phase 1).
     This is mandatory. It is not a question to the human;
   - if the locally installed JDK (`java -version`) is lower than 17 -> write a question to the
     human into section 6: «нужен JDK 17, сейчас установлен <n>». Without it, the project
     does not build.

   **Step style - `flow` or `steps` (the row «Стиль шагов» of the map passport).** The
   framework has FlowRunner. With it, a test is a chain of named steps. The actions and checks
   are in a flow class. For IFT tests and for tests that already use steps, this is the
   recommended way. Decide as follows. Do not ask the human:
   - if the human said how to write («через FlowRunner», «без флоу») -> do as he said;
   - else, count:
     ```
     grep -rliE "ифт|[^a-z]ift[^a-z]" --include=*.properties --include=*.yml --include=*.yaml --include=pom.xml --include=*.gradle --include=*.md --include=Jenkinsfile . | grep -v "/target/\|/build/\|\.gigacode" | head
     grep -rlE "@Step|Allure\.step\(|[^A-Za-z]step\(\"|// *(Шаг|Step|шаг) *[0-9]" --include=*.java --include=*.kt <каталог тестов> | wc -l
     grep -rl "@Test" --include=*.java --include=*.kt <каталог тестов> | wc -l
     ```
     - if the first command found something (an IFT stand, profile, tag or description) -> `flow`;
     - if the number of files with steps (the second command) is not less than one third of
       the number of test classes (the third command) -> `flow`;
     - else -> `steps` (usual step classes);
   - `scope: core` -> write `steps`: in this mode, the tests and the steps do not change.

   If the style is `flow` -> start the documentation subagent (technology `common`) with this
   question:
   «FlowRunner: как создать класс-флоу (интерфейс Flow), как описать шаги теста через step
   и запустить, как передавать данные между шагами (поле класса-флоу, Stash), пример теста и
   класса-флоу». The answer is the record `D-common-7`. The second question: «Какие готовые интерфейсы
   технологий можно подключить к классу-флоу (RestFlow, DataBaseFlow и другие), какие
   готовые шаги и методы они дают (DatabaseSteps, выполнение запроса из шаблона SQL -
   SqlTemplates), как сделать свой подключаемый интерфейс флоу». The answer is the record
   `D-common-8`. If the documentation did not answer -> use the ladder of sources (in the
   sample project, look at the package with the classes `*Flow`).

   **Spring - the row «Spring» of the map passport.** Check if the project has Spring:
   ```
   grep -rlE "org\.springframework" --include=pom.xml --include=*.gradle --include=*.kts . | grep -v "/target/\|/build/" | head
   grep -rlE "@SpringBootTest|@ContextConfiguration|@Autowired|@Component|@Configuration|SpringExtension" --include=*.java --include=*.kt <каталог тестов> | wc -l
   ```
   If both commands are empty -> `Spring: нет`. If something is found -> this is ALWAYS a
   question to the human in section 6. Do not apply the question filter to it: the decision
   changes all of the migration map. The text:
   «В проекте используется Spring (<где: зависимости, n классов с аннотациями>). Как
   поступаем?», the options:
   1) убрать Spring полностью: тесты на JUnit 5 и фрейме, без контекста Spring
      (рекомендуем - проще и меньше кода);
   2) оставить Spring: фрейм подключается к проекту на Spring через свой стартер.
   While there is no answer, write `Spring: есть, ждём ответа` in the map passport. After the
   answer:
   - **«оставить»** -> `Spring: оставить`. Start the documentation subagent (technology
     `common`) with this question: «Как подключить фрейм к проекту на Spring: стартер, зависимости,
     конфигурация, как тесты и шаги получают сервисы фрейма в Spring-контексте». The answer
     is the record `D-common-9`. Write the new code by this record. Keep the Spring
     annotations that the documentation requires;
   - **«убрать»** -> `Spring: убрать`. Spring is a separate technology with the label
     `spring`, the decision `migrate`, and the LAST Order among the technologies. Its unit
     removes from the tests:
     - the Spring context (`@SpringBootTest`, `@Autowired`, `@Component`, the classes
       `@Configuration`, `SpringExtension`);
     - the Spring dependencies;
     - the Spring configs.

     The tests stay on JUnit 5 with the framework annotations. In the units of the other
     technologies, write the new code already WITHOUT Spring (without `@Component` and
     `@Autowired`). The old beans stay until the unit `spring`.
1a. **Connection registry - the file `CONNECTIONS.md` (mandatory).** The project works: its
   tests run. Thus the project already contains all the connection data:
   - addresses, ports, logins, passwords, tokens, clientId and clientSecret;
   - certificates and their passwords;
   - topics, groups, DB schemas;
   - OpenShift namespaces and clusters;
   - addresses of the Sbermock stubs.

   Collect them now into `.gigacode/data/migration/CONNECTIONS.md` (the template is in
   `references/map-template.md`, the section «Шаблон CONNECTIONS.md»). After this, you and the
   executor do not ask the human for data that is in the project. Do the items in order. Do
   not skip an item:
   1) Settings files:
      ```
      find . -type f \( -name "*.properties" -o -name "*.yml" -o -name "*.yaml" -o -name "*.conf" -o -name "*.cfg" -o -name "*.ini" -o -name "*.env" -o -name ".env*" -o -iname "*config*.json" -o -iname "*config*.xml" -o -iname "*settings*.json" \) -not -path "*/target/*" -not -path "*/build/*" -not -path "*/.git/*" -not -path "*/.gigacode/*" -not -path "*/.idea/*" -not -name "gradle-wrapper.properties"
      find . -type f \( -name "Jenkinsfile*" -o -name ".gitlab-ci.yml" -o -name "docker-compose*.yml" -o -name "*.groovy" \) -not -path "*/target/*" -not -path "*/build/*" -not -path "*/.git/*"
      ```
   2) Certificates and key stores:
      ```
      find . -type f \( -name "*.jks" -o -name "*.p12" -o -name "*.pfx" -o -name "*.pem" -o -name "*.crt" -o -name "*.cer" -o -name "*.key" -o -name "*.keystore" -o -name "*.truststore" \) -not -path "*/target/*" -not -path "*/build/*" -not -path "*/.git/*"
      ```
      For each file, find who uses it and where its password is:
      `grep -rn "<имя файла>" --include=*.java --include=*.kt --include=*.properties --include=*.yml --include=*.yaml --include=pom.xml --include=*.gradle* . | grep -v "/target/\|/build/"`.
   3) The values that come from the outside - environment variables, system properties, build
      profiles:
      ```
      grep -rhoE "System\.(getenv|getProperty)\(\"[^\"]+\"|@Value\(\"[^\"]+\"|\$\{[A-Za-z0-9_.-]+\}" --include=*.java --include=*.kt --include=*.properties --include=*.yml --include=*.yaml --include=pom.xml --include=*.gradle --include=*.kts . | sort -u | head -80
      grep -nE "<profile>|<id>|<systemPropertyVariables>|<environmentVariables>|<argLine>|systemProperty|environment\(|jvmArgs" pom.xml */pom.xml build.gradle* */build.gradle* 2>/dev/null | head -60
      ```
      For each name, find where it gets its value:
      `grep -rn "<ИМЯ>" --include=Jenkinsfile* --include=*.yml --include=*.yaml --include=pom.xml --include=*.gradle* --include=*.md --include=*.properties . | grep -v "/target/\|/build/\|\.gigacode"`.
   4) Addresses and credentials that are written directly in the code:
      ```
      grep -rnE "\"(https?|wss?|jdbc:[a-z0-9]+)://[^\"]+\"|\"[a-z0-9.-]+\.[a-z]{2,}:[0-9]{2,5}\"|(password|passwd|pass|token|secret|clientId|client_id|login|username|user)[A-Za-z]* *= *\"[^\"]+\"" --include=*.java --include=*.kt <каталоги исходников> | head -60
      ```
   5) **Read IN FULL each file from item 1.** If a file is longer than 300 lines, do not read
      it in full. Run
      `grep -nE "host|url|uri|port|server|broker|bootstrap|topic|group|jdbc|schema|user|login|pass|token|secret|client|cert|ssl|tls|keystore|truststore|sasl|jaas|namespace|cluster|openshift|mock|stub|alias" <файл>`.
      If the file is test data (request bodies, expected responses) -> in «Откуда
      собрано», mark `данные, не подключение` and do not examine it further.
   6) Assign each key to a technology. Use the key name, the file name and the class that
      reads it: `grep -rn "<ключ>" --include=*.java --include=*.kt <каталоги исходников> | head -5`.
      Hint by words:

      | Технология | Слова в ключах, файлах и классах |
      |------------|----------------------------------|
      | `kafka` | kafka, bootstrap, broker, topic, group.id, consumer, producer, security.protocol, sasl, jaas, ssl |
      | `db` | jdbc, datasource, db, database, schema, driver; user и password рядом с jdbc |
      | `rest` | base.url, baseUri, api, host, endpoint, clientId, clientSecret, token, oauth, auth; ssl рядом с http |
      | `sbermock` | sbermock, mock, stub |
      | `openshift` | openshift, ocp, k8s, kubernetes, namespace, cluster, project; token рядом с api |

      If a key fits more than one technology - write it into each. If it fits none - use the
      section `common`.
   7) Write all of it into `CONNECTIONS.md` by the template. Write each value exactly as it is
      in the project: a reference `${VAR}` as a reference, a password as it is written. If the
      value comes from the outside (CI, a run parameter) -> in the column «Значение», write
      `снаружи: <имя переменной>` and where it is set. If there are more than one stand - write
      a row for each stand.
   Gate: `CONNECTIONS.md` has a section for EACH technology from the table «Технологии
   проекта». For a technology that needs no connection, write one row `подключение не нужно -
   <почему>`. If the section of a technology is empty, but the project has this technology,
   your search was bad. The project uses the technology, thus it connects somewhere. Do items
   4-6 again with the words from the technology name and from the names of its classes
   (`KafkaConfig`, `DbClient` ...). Read these classes.
1b. **Test markup - the row «Разметка» of the map passport.** After the migration, the tests
   get the markup with allure-annotations (the unit `markup`, Stage 5). Collect the values
   for it now, at the start of the migration map: after the approval of the migration map,
   there are no questions. Read `references/markup-rules.md`. Search only in the project
   (section 0 of the rules: no `~/.m2`, no .jar, no framework project, no other directories of
   the computer). Then do these steps in order:
   1) `scope: core` -> write `Разметка: не нужна - scope core` in the map passport. Do not go
      further;
   2) first, the dependency and the version: use the dependency tree, the command «Зависимость и
      версия» from section 5 of the rules. Do not search for the dependency in the build
      files - use only the dependency tree.
      - If it exists -> `версия: есть в сборке <версия>`.
      - If it does not exist -> `версия: 2.0.2`. The markup unit adds it from zero.

      If the command failed -> say «Не удалось построить дерево зависимостей, поэтому не понять, есть ли
      allure-annotations и какой версии: <первые строки ошибки>» and ask the question `upgrade` now, before the
      other markup questions. `да` -> `версия: не определена - дерево зависимостей не построилось; поднять до 2.0.2, если ниже`.
      `нет` -> `версия: не определена - дерево зависимостей не построилось; не поднимать`.
      The markup agent makes the dependency tree again before the changes and uses this answer.

      Do not go to .jar, `~/.m2` or the internet for the version.
      If the major version (the number before the first dot) is 0 or 1 -> the markup by the
      rules is possible only after the upgrade to 2.x. In item 5, the question `upgrade` comes
      first (section 2б of the rules, item 2);
   3) run the other check commands from section 5 of the rules, with the keys in
      `@DisplayName`. Then check two conditions:
      - each test class already has the markup with the agent set from section 1 of the rules
        (itself or through a base class);
      - there are no test-case keys for `@TmsLink` (section 2а of the rules).

      If both are true ->
      `Разметка: не нужна - проект размечен`. Do not go further;
   4) for each key from section 4 of the rules (`model`, `system`, `stage`, `team`, `regress`,
      `story`), find its value in the project: annotations, settings, README, Jenkinsfile
      (`grep -rniE "CI0[0-9]{7}|@Team|team|testops|zephyr|allure" --include='*.md' --include='*.properties' --include='*.yml' --include='Jenkinsfile*' . | grep -v "/target/\|/build/\|\.gigacode" | head`).
      If you found it -> write it into the map passport with the note `из проекта: <файл>`;
   5) the keys without a value are questions to the human. Do not apply the question filter to
      them: only the human has these values. Ask them **now, one at a time**:
      - in the order of the table in section 4 of the rules;
      - as a usual message;
      - with exactly the text from the column «Вопрос»;
      - without your own explanations and options (section 4 of the rules, «Как задавать»).

      Before the first question, say:
      «Для разметки тестов нужны значения, которых нет в проекте. Задам несколько вопросов
      по одному». Before the answer, write each question into section 6 of the migration map:
      ```
      - Q-<n> · <вопрос из раздела 4 правил> · относится к: разметка:<ключ>
        - Где это в проекте: <каталог тестов> - <аннотации нет ни в одном тест-классе / какие классы без неё>
        - Варианты ответа: <из колонки «Ответ»>
        - ответ: -
      ```
      If the human answered -> write `ответ: <значение>`, write the value into the row of the
      map passport, and ask the next question.
      - If the answer to `upgrade` is `да` -> `версия: поднять <версия> -> 2.0.2`.
      - If the answer to this question is `нет` -> in the map passport, write
        `Разметка: не делается - allure-annotations <версия>, поднять до 2.x отказались`.
        Tell the human: «Разметить тесты по правилам не получится: в проекте allure-annotations
        <версия>, а нужна 2.x. Миграция продолжится без разметки». Do not ask the other
        markup questions.

      The answer to `model` removes the questions that are necessary only for a different
      answer (`regress` and `story` - only for `testops`). If the human did not answer, the
      question stays with `ответ: -`. The gate before Stage 5 closes it.
2. **Inventory by modules - through subagents (mandatory).** Start the inventory subagents
   by `references/subagents.md` (section 2). Their number = `min(3, число модулей)`. Use the
   prompt word for word. Write each returned template into
   `.gigacode/data/migration/inventory/<модуль>.md`. Gate: there is a file for EACH module.
3. In section 1 of the migration map, write the summary table of modules (module - files -
   lines - what it is written with).

**Stop because of size.** If the project has more than 150 source files of test code OR more
than 5 modules, stop after Stage 2. Mark the stage and tell the human «Этап 2 готов. Откройте
новый чат и напишите: `/orchestrator Продолжи миграцию`». Do not continue in this chat.

Mark Stage 2 `[x]`, `map_stage: 3`.

