# Code rules for the migration (MR)

These rules tell HOW to write code. WHAT to write (which framework classes and methods) comes
only from the MCP documentation.

**Do not read this file in full.** Each substep (unit) needs 5-12 rules. Their numbers are
in the field «Правила подшага» of the card. Their text and the block «добавлено человеком» go into
`.gigacode/data/migration/tmp/rules-now.md`. The script `scripts/Unit.java rules` puts them there
(`references/work.md`, Step 5, item 1).

**Which rules for which substep:** see the table in `references/substep-rules.md` (one table for the whole kit).
If the field «Правила подшага» in the card is empty (old map), `Unit.java rules` takes the numbers
from that table itself.

**Do not read the mechanical rules as text.** The «Быстрая самопроверка grep-ом»
(the section below; `scripts/Unit.java check` runs it) finds them at Step 6 of each substep that
changes code: `MR-4`, `MR-5`, `MR-6`, `MR-14`, `MR-15`, `MR-17`, `MR-21`, `MR-22`, `MR-33`,
`MR-34`, `MR-35`, `MR-45`. If the script found a problem and you do not know how to fix it -> find this
rule in the file by its number (`grep -n "MR-<n> ·"`) and read only this rule.

**The rules apply to the full unit file, not only to your lines.** If you open a unit file and
see a violation of `MR-33`, `MR-34`, `MR-35`, `MR-36`, `MR-41`, `MR-42`, `MR-43` or `MR-4` in it, fix it. Do this also if
you did not write this line and the migration does not touch it. The excuses «не заметил» and «это было до меня» are not accepted.
Do not touch files OUTSIDE the unit: write a violation there into «Входящие» of the map.

Priority if rules conflict: the framework documentation > the code style of the project (checkstyle, map passport)
> the block «добавлено человеком» at the bottom > the `MR` rules below.

## Class structure

- **MR-1 · Order of class members.** From top to bottom: constants (`static final`) -> static
  fields -> instance fields -> constructors -> public methods -> `protected` and
  package-private methods -> **private methods at the very end of the class**. A private method between
  public methods is a violation. Nested classes go after all methods. If the class already had a different
  stable order and you add 1-2 methods, put the private methods at the end all the same.
- **MR-2 · Fields are private.** New fields are `private`, and `final` when possible. Do not make
  the visibility of existing members wider if it is not necessary.
- **MR-3 · One class - one job.** Do not add a new responsibility to the class that you migrate.
  Make a new class only if it is in the table «Файлы юнита» of the card.

## Imports and names

- **MR-4 · Classes through `import`.** Do not write the full class name with the package in the code
  (`ru.sber.qa.x.Foo foo`): add an import. Exception: a conflict of two equal names,
  for example `@ru.sber.qa.allure.system.System("<КЭ>")` in a file that has `java.lang.System`
  (markup rules, section 2, item 5).
- **MR-5 · Clean imports.** Remove the imports that are not used after the migration. Do not
  add an import with an asterisk if the project does not do this.
- **MR-6 · No old imports.** After the migration, the unit file must not contain
  imports that the card tells you to replace (the grep from «Критериев готовности» is empty).
- **MR-28 · In a `core` unit in mode `in-place`, public methods do not change.** Names, parameters, return
  types and exceptions of the public core methods stay as they were. Only the body changes. If not,
  the code that calls them breaks, and this code is not in your unit. Exception: a card with the note
  «сигнатура меняется, вызывающие файлы включены».
- **MR-7 · Do not rename.** Names of classes, methods, tests and packages stay the same
  if the steps of the card do not include the rename.
- **MR-8 · No own code in the framework package.** Do not declare classes in `package ru.sber.qa...`.
  You can import `ru.sber.qa`, but do not declare your own classes there.

## Meaning of tests

- **MR-9 · The test checks the same things as before.** The same steps, the same checks, the same test
  data, the same names/descriptions for the report. Change the way of writing, not the content.
- **MR-10 · Tests do not disappear.** Do not remove tests. Do not add `@Disabled`/`@Ignore`,
  `enabled = false`. Do not comment out the test body. The number of tests after >= before.
- **MR-11 · Checks do not become weaker.** Do not remove asserts. Do not replace an exact check with
  a weaker one. Do not wrap it in `try/catch` with an empty `catch` to make the test pass.

## Use of the framework

- **MR-12 · Only confirmed names.** Each PVATF name in the code is in the card table «Таблице
  подтверждений». If the name is not in the table, do not write it.
- **MR-13 · Do not write your own code where the framework already gives it.** Do not make your own utilities, wrappers,
  base classes or waits if the documentation has a ready mechanism. Do not «адаптируй» (adapt) an old custom
  wrapper: replace it with the framework mechanism, if the card tells you to do so.
- **MR-14 · No `Thread.sleep`.** Make waits with the framework mechanism from the documentation. If you did not find
  the mechanism, do not add `sleep`. Keep the place as it was and postpone it (`решить человеку` in
  «Входящие»).
- **MR-15 · No hardcode.** Addresses, logins, passwords, timeouts and stand names must not be in the code.
  Put them where the framework documentation tells (the section about configuration). Do not touch existing hardcode
  if the card has no step for it: write it into «Входящие».
- **MR-16 · Dependencies only from the documentation.** Do not add a library or a plugin
  that is not in the framework documentation or in the steps of the card. Keep versions where the project keeps them
  (BOM, `dependencyManagement`, version catalog), not in the module. Take the version numbers of the framework and
  perfeccionista from the line «Версии фрейма» of the map passport (the tool
  `get_pvat_release_notes`). Do not take them from memory or from the old code.

- **MR-29 · Checks use the framework matchers, `Assertions` go away.** How checks work in the
  framework, and which words to use to ask the documentation for the necessary matcher: see
  `references/matchers.md`. Read it before you change the checks. Take matcher names
  from the documentation answer (doc notes), not from memory. In a `usage` unit, change EACH check in the unit files to matchers and conditions
  of the framework:
  - `Assertions.*`, `assertEquals`/`assertTrue`/`assertThat`, AssertJ, Hamcrest;
  - `SoftAssertions`/`assertAll` (-> `.shouldSoft(...)`);
  - own `assertXxx`/`checkXxx`;
  - manual JSON parsing for a comparison.
  The new check must check the same thing as before (`MR-9`, `MR-11`).
  Move the message of the old assert into the parameter `errorMessage` of the matcher.
  The only exception: the documentation has no matcher that covers this check
  (8 query wordings, see `references/matchers.md`). Then the STANDARD assert (`Assertions` from
  JUnit/TestNG, AssertJ, Hamcrest) stays. Write into «Входящие» of the map: the file, the line,
  and what you could not change. Also write the line `исключение MR-29: <файл>:<строка>` in «Сделано» of the substep
  (with this line, `Unit.java check` does not count this assert as a finding). Custom assert classes never
  stay.
- **MR-48 · Write a check with a ready framework matcher - step by step, without own constructs.**
  This is the most frequent migration error, so the rule is long. The order is in
  `references/matchers.md`, section «Как писать проверку»: (1) write the check in words;
  (2) find the type of the expected value and use the table to select WHAT to check it with: a number, a date,
  a boolean, null, a size and a text use different conditions; (3) take the matcher name from the doc notes
  or from the documentation subagent; (4) use one call `.should(...)` / `.shouldSoft(...)` on the
  validatable object, and list the matchers directly in this call; (5) the expected value is data
  (a constant, a parameter, a DB cell); never get the actual value manually.
  PROHIBITED (`references/matchers.md`, section
  «Запрещённые приёмы», shows each technique with an example):
  1. own wrapper methods that return a framework matcher (`jsonTextMatcher(...)`,
     `jsonNumberMatcher(...)`);
  2. own classes that implement the matcher or condition interfaces of the framework;
  3. a list of matchers (`List<...Matcher>`), `matchers.add(...)` in a loop,
     `shouldSoft(matchers.toArray(...))`, methods that return a list of matchers;
  4. one condition for everything: a number, a date or a boolean through a text condition or through
     an expression string;
  5. reading the response again from the request history (`getRestHistory().getLast()`), parsing into
     `JsonNode` (`JacksonHelper`, `.path(...)`), the helpers `textOrNull` / `intOrNull`;
  6. `assertAll` / `assertEquals` / `assertTrue` and own `compareNumbers` /
     `assertDatesEqual` next to the response or the DB row;
  7. helpers that get a value from the response to compare it later;
  8. `assertAll` at all, also with lambdas `() -> response.should(...)` inside.
     For a group of checks, use `.shouldSoft(...)`. For a named step in the report, use
     `Allure.step("<описание>", () -> ...)` or a step method with `@Step`. The standard asserts that stay by `MR-29`
     also go without `assertAll`, one after the other.
  If there is no necessary matcher (doc notes, subagent, the folder `docs` of the framework sources) -> the standard
  JUnit assert stays (`MR-29`), add a line to «Входящие». The substep is not blocked. Do not ask
  a question. Do not go around it with own code (a wrapper, an own matcher). Array elements against
  DB rows without an array matcher: use a loop over the rows. In the loop body, use one call `.shouldSoft(...)` with
  the matchers for `[i]` directly in it, without a list. Self-check: the command `MR-48` at the end of this
  file.
- **MR-41 · Do not change the response into a DTO for a check.** In the framework, a request returns a
  validatable object, and you check it with `.should(...)`:
  ```java
  // нельзя: ответ -> свой объект -> ассерты по полям
  OrderDto order = response.as(OrderDto.class);
  Assertions.assertEquals("NEW", order.getStatus());
  Assertions.assertEquals(53, order.getCode());
  // нужно: метод, который делает запрос, возвращает валидируемый объект наверх,
  // а шаг или тест проверяет его
  createOrder(body)                       // возвращает ValidatableResponseWrapper
          .should(<matcher кода ответа>)
          .toValidatableJson()
          .should(<matcher поля status>, <matcher поля code>);
  ```
  What this means:
  - the low-level method (the method that sends the request to REST, DB, Kafka) returns a validatable
    framework object, not a DTO, `String`, `Map` or `Response` of the old library;
  - do not make new response DTOs; do not wrap the response into own result classes;
  - an old response DTO that was necessary only for asserts is not used after you change the checks to
    matchers. Remove it (in this unit if it has 0 references, otherwise
    in `cleanup`);
  - a value from the response that the scenario needs LATER (the id of the created entity for the
    next request): get it in the way that the documentation shows for the
    validatable object, not through a DTO.
  What to do with DTOs, models, Jackson and JAXB - only this, it is not a question:

  | In the project | Decision (always this, not a question) |
  |---------------|-----------------------------------|
  | A DTO or a response model: the response is parsed into an object (`.as(X.class)`, `readValue`, `fromJson`, `unmarshal`, `JacksonHelper.parse...`) to check its fields later | Remove it. The request response is already in the validatable framework object: call `.should(...)` on it with matchers by the field path. Deserialization for checks is not necessary |
  | The scenario needs one value from the response later (an id for the next request, a token) | Get it with one call on the validatable object, in the way from the doc notes. A DTO is not necessary for this |
  | A DTO or a model that builds the BODY of a request or a message (also JAXB XML models) | It stays as project data, together with its Jackson and JAXB annotations. Give the body to the framework request as the doc notes show |
  | The same model for the request body and for the response parsing | It stays as the request body model. Remove the response parsing into it; checks use `.should(...)` |
  | An own wrapper over Jackson or JAXB (`JacksonHelper`, `XmlUtils`, `JsonUtils`) | Remove the response parsing methods together with their calls. The methods that build request bodies or read test data files stay while something uses them. If the class becomes empty, remove it |
  | The documentation has no JSON/XML deserialization into an object, no way to get the response body as a string, and does not mention Jackson or JAXB | This is not a documentation gap: the framework does not need it, the response is checked with `.should(...)`. Do not ask a question |
  | No matcher was found for the necessary field | A standard assert (`MR-29`) on the value that you got from the validatable object (not through a DTO), and a line in «Входящие» |

  **Do not replace an assert mechanically: analyze the full chain.** You see an assert or a check of a
  value that was got manually (`dto.getStatus()`, `response.jsonPath().get(...)`,
  `row.getString(...)`, `record.value()`, own `checkXxx(dto)`). Do not change one line
  `assertEquals` to something similar. Go BACK from the assert and answer three questions:
  1. Where does the value come from? From a REST response, a DB row, a Kafka message -> this is a check of the
     call result, its place is `.should(...)` on the validatable object. The test calculated the value
     itself (a sum, the length of its own list, a flag) -> the framework has no check for
     this, `Assertions` stays (`MR-29`).
  2. What is between the call and the assert? Usually: the method sends a request -> changes
     the response into a DTO -> returns the DTO -> a getter gets the field -> a check method or an assert
     compares. All that is between «сделал запрос» and «проверил» is unnecessary.
  3. Does something other than the check need the value (an id for the next request)? If yes,
     get it in the way from the documentation on the validatable object: only this one
     value, without a DTO.
  Then rewrite the full chain, not only its end: the method that sends the request returns
  the validatable framework object; remove the extraction, the DTO mapping and the check method; write the check
  with `.should(...)` and a matcher for this field (the matcher comes from the doc notes). After this,
  run `grep -rn "<ИмяDto>" <src>`. If no references stay, remove the DTO class (for a file outside the
  unit, add an item to «Входящие»). Files outside the unit can call the method that returned the DTO, and you cannot
  change it without breaking them -> do not leave half of the work: write into «Входящие» which
  files keep the old chain.
  Prohibited: to keep the DTO and the getter and replace `assertEquals(a, dto.getX())` with a check of a
  string; to put the field into a variable and check the variable; to wrap the old check method
  into a new one.
  **A response DTO never stays.** For each request, the framework returns a validatable object
  (REST - `ValidatableResponseWrapper`, body - `ValidatableJson` or `ValidatableXml`, DB -
  `ValidatableTable`/`ValidatableRow`, Kafka - a record), and it always has `.should(...)`.
  So a way to check without a DTO always exists: this is not a question and not an exception. A typical
  old chain and what to do with it:
  ```java
  // БЫЛО: запрос -> разбор в DTO -> DTO передаётся дальше -> геттеры -> ассерты
  SdcRequest sdcRequest = mapper.readValue(response.body(), SdcRequest.class);
  verifyDebitingRequisites(sdcRequest, idocDebtor);          // внутри assertEquals(..., sdcRequest.getDebiting()...getInn())
  // СТАЛО: шаг запроса возвращает валидируемый объект, его и передаём дальше
  ValidatableJson sdcRequest = SdcSteps.getSdcRequest(...);  // без DTO
  verifyDebitingRequisites(sdcRequest, idocDebtor);          // внутри sdcRequest.shouldSoft(<matchers по путям debiting.requisites.*>)
  ```
  - the method that returned the response DTO now returns the validatable object;
  - the methods that took the response DTO as a parameter now take the validatable object
    (or one necessary value for the next request);
  - each «геттер DTO -> ассерт» becomes a matcher by the field path (`debiting.requisites.inn`);
  - change all calling files that break because of the type change in this same substep
    (if the change is mechanical, add them to the substep; if there are many, add a new substep `usage` immediately after it);
  - remove the response DTO class when no references to it stay.
  A DTO that BUILDS THE REQUEST BODY is data: it stays.
- **MR-44 · Step style `flow`: the test is a chain of FlowRunner steps, the logic is in the flow class.**
  Apply this rule only if the map passport has «Стиль шагов: flow». Take the exact names of classes and
  methods from the record `D-common-7` of the doc notes. The schema:
  ```java
  // тест: только названия шагов и вызовы методов флоу
  FlowRunner.flowRunnerFor(OrderFlow.class)
          .step("Создаём заказ", f -> f.createOrder(body))
          .step("Проверяем ответ", OrderFlow::validateResponse)
          .step("Проверяем запись в БД", OrderFlow::validateOrderRow)
          .run();

  // класс-флоу: клиенты фрейма, действия, проверки, состояние между шагами
  public class OrderFlow implements Flow, RestFlow, DataBaseFlow {
      private final RestClient restClient;
      private ValidatableResponseWrapper response;   // нужно следующим шагам
      ...
      public void createOrder(OrderRequest body) { response = restClient.post(...); }
      public void validateResponse() { response.should(<matchers>); }
  }
  ```
  - rewrite an old test with steps (`@Step`, `Allure.step`, comments «Шаг 1») into a
    chain: one old step - one `.step(...)`. Keep the step name and the order;
  - a step contains a call of ONE flow method (a method reference or a short lambda with parameters).
    A lambda longer than 3 lines, or a lambda with a condition or a loop, is logic: move it into a flow method;
  - in the style `flow`, an action method of the flow can return nothing and keep the validatable
    object in a field. The check with `.should(...)` is in a check method of the flow. This is not a
    violation of `MR-41` and `MR-42`. Response DTOs are still not made;
  - **build the flow from ready parts.** First look at what the ready framework technology interfaces
    give when you connect them with `implements` (the record `D-common-8`: ready steps for DB,
    REST, a request from an SQL template and so on). Call them. Do not write an own method or class that
    does the same (an own «выполнить select», an own SQL load from a file and substitution of
    parameters);
  - write the logic that several flows need only once, in its own pluggable part
    (an interface or a step class from the architecture plan). The flows connect this part. Do not copy
    methods from flow to flow;
  - a flow class runs one scenario and can work with several technologies: this is not a
    violation of `MR-38`. One flow for everything, or one flow for each test, is a violation;
  - the architecture plan tells which flow does what. Do not make a new flow «по ходу»
    if the plan has a suitable flow.
  If the passport style is `steps`, do not add FlowRunner: write usual step classes.
- **MR-43 · Do not log requests and responses manually: the framework does it.** The framework itself writes
  each call and its response to the log: the REST request and response, the DB query and result,
  the send and read of Kafka messages, and so on. So in the migration, do NOT move the old manual
  logging of these things. Remove it:
  - logger calls and `System.out.println` that print the URL, the method, the headers, the body of the
    request or response, the status code, the SQL text and its result, a Kafka message;
  - logging filters and settings of old libraries (`.log().all()`,
    `RequestLoggingFilter`, `ResponseLoggingFilter`, `.prettyPrint()`, `.peek()`), own
    filters and interceptors that were written for logging;
  - lines like «Отправляем запрос...», «Получен ответ...», «Выполняем SQL...» around
    a framework call.
  Remove the logger field (`Logger log`, `@Slf4j`) that nothing uses after this, and its
  imports. Do not add such logging in new code.
  **Logging is configured in one place: the file `simplelogger.properties`** in the test
  resources (`src/test/resources/`). The framework writes the log through the simple SLF4J logger
  (`SimpleLogger`), and the project needs nothing more. For more or less detail,
  change the level in this file, not the code. The usual content of the file:
  ```
  org.slf4j.simpleLogger.defaultLogLevel=INFO
  org.slf4j.simpleLogger.showShortLogName=true
  org.slf4j.simpleLogger.showDateTime=true
  org.slf4j.simpleLogger.dateTimeFormat=HH:mm:ss:SSS
  org.slf4j.simpleLogger.logFile=System.out

  #org.slf4j.simpleLogger.log.ru.sber.at=INFO
  ```
  The file is mandatory in each migrated project. If it is not there, make it with this content (in the
  unit where the card says so). The last line is a commented example of a level
  for one package. If the file in the doc notes `doc-notes/common.md` or in the example project
  is different, use that version. Set the level for one package with the line `org.slf4j.simpleLogger.log.<пакет>=<уровень>`.
  The simple SLF4J logger reads the file, so the build must have two dependencies with one
  version: `org.slf4j:slf4j-simple` and `org.slf4j:slf4j-api`, the version is `${log.version}`
  (the property `<log.version>2.0.16</log.version>` in `<properties>`, if the card does not tell
  a different version). If they are not there, add them in the same unit as the file.
  All other logging of the project is old. Remove it (in the units where the card says
  so):
  - the configurations `logback.xml`, `logback-test.xml`, `log4j.xml`, `log4j2.xml`,
    `log4j.properties`, `log4j2.properties`, `logging.properties`;
  - the dependencies of loggers and of their bindings to SLF4J (`logback-classic`, `logback-core`, `log4j-core`, `log4j-api`,
    `log4j-slf4j-impl`, `log4j-slf4j2-impl`, `slf4j-log4j12`, `slf4j-reload4j`, `jul-to-slf4j`
    and similar);
  - own appenders, filters and formatters of logs.
  Do not add to the project a configuration of a different logger or a dependency on it.
  If a message about the scenario progress stays, the logger is only `org.slf4j.Logger` (or
  `@Slf4j`), not `org.apache.logging.log4j`, not `java.util.logging`, not `ch.qos.logback`.
  What you can keep: a message about things that the framework cannot know: the scenario progress and
  domain values («создан заказ <id>», «ждём смены статуса»). If you are not sure
  whether a line duplicates the framework log, remove it.
- **MR-42 · The test class is clean: the logic does not lie in the test «снаружи» (outside).** A class with `@Test` contains
  test methods, annotations, test data constants and, when the tests need them, setup and
  cleanup methods (`@BeforeEach`/`@AfterEach`). The test body reads as a scenario: prepare the data
  -> do the action -> check with `.should(...)`.
  **Prohibited: helper methods in the test class.** No private (and no other non-test)
  methods that:
  - send requests, go to the DB or Kafka (`postExecutionReport(...)`, `selectXxx(...)`,
    `queryTable(...)`);
  - read files and build requests (`loadSqlFile`, `Files.readString`,
    `replaceSqlPlaceholders`), select a schema or an alias by conditions (`if ... return "..."`);
  - map a response or a table row into an object (`toXxxRow(...)`, `cellValue(...)`, groups of
    `dto.setXxx(...)`), serialize (`JacksonHelper`, `ObjectMapper`).
  Encapsulation exists for this logic: it lives in the step classes of the
  technology or of the domain (the layer and the package come from the target picture `T-common`,
  `T-<tech>`). A step class takes a framework service and gives action methods: «сделать запрос в
  API», «отправить в Kafka», «выбрать из БД». A step method returns a validatable framework object
  (`MR-41`), and the test checks it.
  **Allowed: a call to the framework directly IN THE BODY of the test method** when it is a one-time short
  action of this test only (one service call and a check with `.should(...)`), and
  no suitable step exists. This is not a violation. But a second test can need the same action,
  or the call can get preparation (a file read, an SQL build, mapping, branching). Then it is a
  step: move it into a step class, not into a private method of the test.
  Where to move it:
  1. the step class already has the necessary step method -> the test calls it;
  2. the step class exists, but the method does not -> add the method there (the file is in the card, or «добавлен по
     ходу» if the change is mechanical);
  3. there is no step class and the card does not have it -> do NOT put the logic into private methods of the
     test class «временно». Make a step class by the architecture plan (the rule «один
     незапланированный класс за подшаг» - Step 5 SKILL.md). Or, in a `tech` unit, add a substep
     `core` that makes it, and do it immediately. Do not ask a question.
  The same service logic (an SQL load from a file, the substitution of parameters) is in ONE
  place. Do not copy it into each test class.
- **MR-30 · To the framework directly, without intermediate layers.** The code calls the framework mechanisms as
  the documentation shows: through the base layer of the technology (`MR-49`), not through an intermediate class. Do not wrap a framework client or service into
  an own `RestHelper`, `ApiClient`, `DbUtils`, `KafkaHelper`, a base class or a static
  utility «чтобы было как раньше». Know the difference:
  - **an intermediate layer (prohibited):** a general method that repeats the framework -
    `RestHelper.post(url, body)`, `DbUtils.select(sql)`, `KafkaHelper.send(topic, msg)`;
  - **a step (necessary):** a method with the name of a domain action -
    `postExecutionReport(body, headers)`, `selectExecutionReportConfig()`. It
    calls the framework directly and returns a validatable object. Steps are in step
    classes, not in private methods of the test class (`MR-42`).
  **The base layer of the technology is not an intermediate layer** (`MR-49`): it is one class for each technology from the
  architecture plan with common operations (`get`/`post`/`put`/`delete`, run SQL).
  Each operation returns a validatable framework object. An intermediate layer is a second class above it,
  a class with old signatures of the old library, or a class that hides the framework.
  Old intermediate classes go away in `cleanup`. (The only
  exception is a `core` unit in mode `in-place`: there the old core class lives for some time with
  its old public methods, see `MR-23`.)
- **MR-49 · Layers are exactly the layers of the architecture plan. No delegates, facades and nested
  classes.** The code goes into layers, and each layer does its own job:

  | Layer | What it contains | What it calls |
  |------|-----------|---------------|
  | tests | the scenario: data, step calls, checks `.should(...)` | steps |
  | domain steps (`OrderSteps`, `ReportSteps`) | actions with domain names and `@Step`: build the body and the headers, call the base layer, return a validatable object | the base layer of the technology, data |
  | the base layer of the technology (`RestSteps`, `DbSteps`, `KafkaSteps` - one class for each technology) | common operations of the technology: `get` / `post` / `put` / `delete` with parameters (path, body, headers, request settings), run SQL from a file, send and read a message. The call to the framework client is built here; steps and tests do not repeat this build | the framework |
  | data | endpoints, request bodies, SQL files, constants | - |

  A one-time call to the framework in the test body (`MR-42`) also goes through the base layer if the base layer
  has the necessary operation. Step style `flow` (`MR-44`): the step layer is the flow classes. The ready framework
  technology interfaces (`RestFlow`, `DataBaseFlow` -
  by `D-common-8`) and own pluggable parts do the role of the base layer. The prohibitions below apply in the same way.

  Prohibited:
  1. **A facade with delegation.** A method that only calls the same method of a different
     class with the same parameters:
     ```java
     // НЕЛЬЗЯ
     public static ValidatableJson postJournalDetailed(String body, Map<String, String> headers) {
         return ReportServiceIdocJrnSteps.postJournalDetailed(body, headers);
     }
     ```
     If you split a large class, change the callers to the new class. Do not keep the old class as a
     «тонким фасадом» (thin facade). Calling files outside the card -> they go into the substep (or an item in
     «Входящие»). Never write a facade.
  2. **Nested classes.** `static class`, an inner class, a holder class
     (`JournalExpectations`), an anonymous class in a step class - prohibited. If you need a data
     structure, it is a class of the data layer from the plan.
  3. **Twin methods.** Two or more methods that have the same body and differ
     only in the path, the table, the SQL file or the header - prohibited. The common part (the request build,
     the settings, the client call, the response code check) is ONE method of the base layer with
     parameters. The domain step calls it with one or two lines.
  4. **A class «всё общее» (all common).** `...Common`, `...Helper`, `...Utils` that contains constants,
     service access, wrappers over matchers and helpers - prohibited. Put each thing into its own layer.
  5. **A split «на всякий случай» (just in case).** New step classes - only the classes in the plan
     (`ARCHITECTURE.md`). Split a large class by the plan, not into 10 classes by your own
     decision.
  6. **Layer chains.** Test -> step -> base layer -> framework. A step does not call a step of a different
     class for the same request; the base layer does not call steps.
- **MR-50 · The data layer - simple classes and files, without own mechanics.** Data is
  WHAT we send and WHAT we expect: endpoints, request bodies, SQL files, test values.
  They are in the layer «данные» of the architecture plan. How they look:

  | What | How it is kept | Prohibited |
  |-----|--------------|--------|
  | endpoints (paths) | constants `static final String` in the step class of their domain, or one endpoint class for each service if the project already has it | an endpoint enum with methods, a path builder, a «реестр» class with logic |
  | the request body | a DTO/body model (with a builder, `MR-34`) or a JSON/XML file in the resources - as the project had it | a body factory, a class `...Factory`/`...Generator` with branches, body inheritance for «общих полей» |
  | SQL | an `.sql` file in the resources or a constant - as it was; the execution is in the base layer of the technology | an own SQL loader and template engine if the framework has one (`D-common-8`) |
  | test values | constants in the test class or a test data class of the domain | «держатели» classes in steps (`MR-49`, item 2), a `Map` «поле -> значение» for checks (`MR-48`) |

  A data class has only fields, constants and a builder. It has no methods with logic (requests, checks,
  settings read, branches by stands). Do not make own data classes that are not in the
  plan. Move what the project had as it is (`MR-32`).
- **MR-31 · Do not touch `keep` technologies.** Do not migrate and do not remove the code, dependencies and configs of a technology with the decision
  `keep` in the map passport. Exception: an `arch` unit, strictly by the
  steps of the card.
- **MR-51 · Markup - only annotations, as a cascade.** A `markup` unit adds the annotations of
  allure-annotations strictly by `references/markup-rules.md` and the values from the line «Разметка» of the
  passport. Put an annotation on the base class if the value is common; on the test class if the value is its own. If the annotation
  is already there, do not add it again lower in the hierarchy. Do not change the test logic, steps and checks.
  Do not change `@DisplayName`: only copy the test-case key from it into `@TmsLink` (section 2a
  of the markup rules). Do not invent other markup annotations. Take the annotation names from
  `references/markup-rules.md`, not from the doc notes: this is an exception from `MR-12`.

## How to write code (strict, no exceptions by taste)

- **MR-33 · `var` is prohibited. Only explicit types.** Nowhere: not in local variables, not in
  `for`, not in `try`, not in lambdas. Write the full type:
  ```java
  // нельзя
  var entity = new EridProductExecEntity();
  for (var entry : headers.entrySet()) { ... }
  // нужно
  EridProductExecEntity entity = ...;
  for (Map.Entry<String, String> entry : headers.entrySet()) { ... }
  ```
  If you do not know the type, look at the method signature on the right or in the documentation. Do not use `var`.
  If the unit file already has `var`, replace it with an explicit type.
- **MR-34 · Make an object with several fields with a builder, not with a group of setters.** Prohibited:
  `new Foo()` and then 4 or more calls `foo.setXxx(...)`.
  ```java
  // нельзя
  EridProductExecEntity entity = new EridProductExecEntity();
  entity.setId(...);
  entity.setProductId(...);
  entity.setDebtorId(...);
  // ... ещё 25 строк
  return entity;
  // нужно
  return EridProductExecEntity.builder()
          .id(...)
          .productId(...)
          .debtorId(...)
          .build();
  ```
  Where to get the builder:
  - the class already has a builder -> use it;
  - the class is your own (it is in the project) and has no
    builder -> add one. If the project has Lombok (grep `lombok` in the build files), add the annotation
    `@Builder` to the class. If there is no Lombok, add a static nested class `Builder` with methods for the
    fields and `build()`. Add the class file to the card with the note `добавлен по ходу`;
  - the class is from a library and has no builder -> keep the setters, this is not a violation.
- **MR-35 · Get the framework service in ONE place of the class, not in each method.** Do not
  repeat the chain `Environment.getForCurrentThread().getService(...)` in each method:
  ```java
  // нельзя: одна и та же цепочка в каждом методе
  private void sendToKafka(...) {
      KafkaProducerClient producer = Environment.getForCurrentThread()
              .getService(KafkaService.class).producerClient(KAFKA_ALIAS);
      ...
  }
  private ConsumerRecord<String, String> receiveFromKafka(...) {
      KafkaConsumerClient<String, String> consumer = Environment.getForCurrentThread()
              .getService(KafkaService.class).consumerClient(KAFKA_ALIAS, ...);
      ...
  }
  // нужно: получение сервиса - один приватный метод, остальные вызывают его
  private KafkaService kafkaService() {
      return Environment.getForCurrentThread().getService(KafkaService.class);
  }
  ```
  Use one private method for each service (`kafkaService()`, `restService()`, `databaseService()`),
  at the end of the class (`MR-1`). If the documentation for the test class shows a different way to
  get the service once (a field, a method parameter), use that way. Do not put
  the result of `getForCurrentThread()` into a `static` field: the environment is bound to the thread.
  When a repetition is allowed: clients with DIFFERENT connection aliases (`producerClient(ALIAS_A)` and
  `producerClient(ALIAS_B)`) are different clients, and you can get them in different places. But
  get the service itself through the same one method. Such a private method is not a wrapper
  and does not break `MR-30`. Do not make a separate helper class for this.
- **MR-46 · Framework annotations - once, in the base test class.** The annotations that connect the
  framework are the same for all tests of one environment configuration. Do not repeat them in each
  test class. Put them on the base test class, and the tests extend it:
  ```java
  @ExtendWith(PerfeccionistaExtension.class)
  @SetEnvironmentConfiguration(ApiEnvironmentConfiguration.class)
  public class BaseTest {
  }

  public class OrderTests extends BaseTest {   // аннотаций фрейма на самом тесте нет
      @Test
      void whenOrderCreatedExpectStatusNew() { ... }
  }
  ```
  (the exact annotations come from the doc notes `doc-notes/common.md`).
  - **Such a base class is normal and necessary.** The prohibition of «базовые классы» (`MR-25`,
    `MR-30`) is about a different thing: a base class with clients and methods that tests
    extend to get access to them;
  - the base test class can contain: annotations of the framework and of the test framework (extensions,
    environment configuration, common tags), constants common for all tests, and common
    `@BeforeAll`/`@BeforeEach`/`@AfterEach` if ALL subclasses need them;
  - the base test class must not contain: framework clients and services in fields, request methods,
    check methods, file reads, helpers «для удобства». Their place is in step classes;
  - one base test class for one environment configuration (API tests - one, UI tests - a
    different one). See the architecture plan for the base test class that the project has. Do not make a second one for
    the same configuration;
  - if the project already has a base test class (`TestBase`, `BaseTest`), use it: keep the
    name, remove the old things from it (clients, helpers), keep the framework annotations;
  - if you write or rewrite a test class -> it extends the base class; remove the framework annotations from
    the test class itself. If the base class is not in the project, not in the card and not in the plan -> add an
    item to «Входящие», and for now put the annotations on the test class.
- **MR-47 · The framework reads the connection settings: the old configuration read does not move.**
  The framework has its own settings files (`*.properties` in the test resources: the common framework file and the
  technology files - for DB, Kafka, stubs and so on). The framework finds them, reads them and
  configures the services from them: the address, the login, the DB alias, the Kafka brokers and topics, the timeouts.
  So in the migration:
  - MOVE the values from the old configs (addresses, aliases, topics, credentials, timeouts)
    to the framework settings files. Take the names of the files and keys only from the doc notes
    of the technology (question 3 «как настроить»). Do not invent them;
  - do NOT move the old settings read CODE: remove it. This is own `ConfigReader`,
    `PropertyReader`, `PropertiesLoader`, Owner interfaces (`ConfigFactory.create`),
    `new Properties().load(...)`, `ResourceBundle`, `System.getProperty` / `System.getenv`
    for an address or a login, `@Value`, settings holder classes (`KafkaConfig`, `DbConfig`,
    `Endpoints` with hosts);
  - do not build the connection manually: no own `Properties` for a Kafka client
    (`bootstrap.servers`, serializers, SSL), no own JDBC string, no own `DataSource`,
    no own base URL in the code. Get the client from the framework service by alias. The framework
    does the rest by its own settings;
  - remove the old settings files after you move their values (lines `L`);
  - do not make a «переходник» (adapter) that reads the old config and gives the values to the framework.
  **The own configuration classes of the project are not necessary after the migration.** This is a class that keeps
  or gives connection settings (`DbConfig`, `DatabaseProperties`, `KafkaConfig`,
  `ApiConfig`, `Endpoints` with hosts, `TestConfig` with url/login/password). It did what
  the framework now does with its own settings files. What to do with it:
  - the technology is migrated -> nothing must read its part of the class. Remove the calls
    to the class from the unit files (get the framework service by alias, the address from the framework settings);
  - the class served one technology -> remove it in the `cleanup` of this technology;
  - the class is common for several technologies -> remove it part by part: in each unit of a technology,
    remove the fields and methods of this technology. When nothing stays in the class, remove it.
    Do not wait for the end of the migration to start to clean it. Do not keep it «на всякий случай»;
  - the class has connection settings and also own parameters of the project (test
    data) -> the connections go away; move the parameters in the way that the
    documentation shows. Then remove the class;
  - do not confuse it with the configuration classes of the FRAMEWORK (`*EnvironmentConfiguration`,
    `*ServiceConfiguration` from the documentation, the package `config`, `MR-36`): they are necessary and
    stay. The difference: a framework class tells which services are connected and follows the
    documentation; an own class keeps values (address, login, alias) or reads them from a file.
  Before you remove a class, run `grep -rn "<ИмяКласса>" <src>`: it must have no references. If references stay
  in files outside the unit, do not remove the class: write into «Входящие».
  What stays: own parameters of the project that are not about connections
  (test data, identifiers). Keep them and get them in the way that the
  documentation shows (ask the subagent: «как получить свой параметр проекта из
  настроек, ConfigurationService»), not with an own reader.
- **MR-36 · Framework configuration classes are in the package `config`.**
  Put `ApiEnvironmentConfiguration` and all other framework configuration classes
  (`*EnvironmentConfiguration`, `*ServiceConfiguration`, `*Configuration` for the framework
  services) into the package `config`. If the project already has a package `config` (in `src/main/java`
  or in `src/test/java`) -> put them there: `find . -type d -name config -path "*src*" | grep -v
  "/target/\|/build/"`. If not -> make `<базовый пакет проекта>.config` where the documentation
  tells you to keep the configuration; if the documentation does not tell this, make it in `src/main/java`. Prohibited: to put
  the configuration into the root of `src/main/java` without a package, next to tests, into the package `utils`/`helpers`,
  or to spread it over several packages. If you find a framework configuration class not in `config`, and it
  is in the unit files -> move it.

## Readability (standard Java conventions: simple, clear, one job)

- **MR-37 · A method does one job and fits on the screen.** It is not longer than 40 lines. The nesting
  (`if`/`for`/`try` in each other) is not deeper than 3 levels. If it is longer or deeper, move parts into
  private methods of this class with clear names. Do not mix in one method the
  send, the wait, the parsing and the check if they read as separate steps.
- **MR-38 · A class does one job.** Do not put work with different
  technologies (REST, DB, Kafka together) into one class. Do not make classes `Utils`/`Helper`/`Common` with
  unrelated methods. Do not make a class larger than 500 lines. Do not write new code like this. Do not split an
  existing class like this yourself in a migration unit: this is the work of an `arch` unit. Write it
  into «Входящие».
- **MR-39 · No duplicates and no dead code.** If the same block of 5 or more lines is in two
  places, move it into a private method. Remove private methods, fields, parameters and variables
  that nothing uses.
- **MR-40 · Names tell what it is.** No `tmp`, `data1`, `obj`, no names of one letter
  (except a loop counter). Give a method a name for what it does.
- **MR-45 · Names follow the Java conventions, without an underscore.** This is Java, not
  JavaScript and not Python:
  | What | How to write | Correct | Incorrect |
  |-----|------------|-----------|-------------|
  | a method (also a test method) | starts with a small letter, each next word starts with a capital letter | `createOrder`, `whenOrderCreatedExpectStatusNew` | `create_order`, `Create_Order`, `when_order_created_expect_status_new`, `test_create_order` |
  | a variable, a parameter, a field | the same, starts with a small letter | `orderId`, `responseWrapper` | `order_id`, `response_wrapper`, `OrderId` |
  | a class, an interface, an enum | each word starts with a capital letter | `OrderFlow`, `OrderRequest` | `order_flow`, `Order_Flow`, `orderFlow` |
  | a constant (`static final`) | all letters are capital, words are separated by `_` | `DEFAULT_TIMEOUT` | `defaultTimeout`, `Default_Timeout` |
  | a package | small letters, no `_` | `ru.sber.qa.orders` | `ru.sber.qa.order_steps` |
  An underscore is allowed ONLY in constants. The rule applies to all that you
  make or rewrite in the unit, also to the names of test methods. It applies also if the old
  project code was different. Do not rename a test method that you did not change.
  If you renamed a method, fix all its calls (`grep -rn "<старое имя>(" <src>`).

## Quick self-check with grep («Быстрая самопроверка grep-ом»; run it at Step 6 on the unit files)

```
grep -nE "(^|[^A-Za-z0-9_])var +[A-Za-z_][A-Za-z0-9_]* *(=|:)" <файлы юнита>          # MR-33: должно быть пусто
grep -cE "\.set[A-Z][A-Za-z0-9]*\(" <файл>                                          # MR-34: 4 и больше подряд на один объект - переделай на билдер
grep -c "getForCurrentThread()" <файл>                                               # MR-35: больше, чем разных сервисов в файле, - вынеси в один метод
grep -nE "Assertions\.|assert(Equals|True|False|NotNull|Null|That|All)\(|SoftAssertions" <файлы юнита>   # MR-29: в usage-юните каждая строка либо заменена, либо записана во «Входящие»
grep -nE "\.as\([A-Z][A-Za-z0-9_]*\.class\)|readValue\(|fromJson\(|\.getObject\(|\.extract\(\)" <файлы юнита>   # MR-41: ответ превращают в объект - замени на проверку через .should(), если это ради проверки
grep -nE "^[^/*]*[^A-Za-z0-9_.\"](org|com|ru|io|java)\.[a-z0-9_]+\.[a-z0-9_.]+\.[A-Z]" <файлы юнита> | grep -v "^[0-9]*:\(import\|package\)" | grep -v "@ru.sber.qa.allure.system.System"   # MR-4: полное имя класса в коде
grep -nE "\b(log|logger|LOG|LOGGER)\.(info|debug|trace|warn|error)\(|System\.(out|err)\.print|\.log\(\)\.(all|body|headers|ifValidationFails)|(Request|Response)LoggingFilter|\.prettyPrint\(|\.prettyPeek\(|\.peek\(" <файлы юнита>   # MR-43: строка логирует запрос, ответ, SQL или сообщение - удали; остаётся только сообщение о ходе сценария
```
The check `MR-48` (own constructs around checks) - fix each output line:
```
grep -nE "implements [A-Za-z.]*(Matcher|Condition)\b|List<[A-Za-z.]*Matcher>|matchers\.add\(|\.toArray\(new [A-Za-z.]*Matcher|static [A-Za-z.<>]*(Matcher|Condition) [a-z][A-Za-z0-9]*\(" <файлы юнита>   # свои matchers, обёртки над matcher, списки matchers
grep -nE "getRestHistory\(\)\.getLast\(\)|JacksonHelper|JsonNode|\.path\(\"|textOrNull|intOrNull|longOrNull|boolOrNull|compareNumbers|assertDatesEqual|bigDecimalsEqual" <файлы юнита>   # ответ разбирают руками или сравнивают своими хелперами
grep -nE "equalToText\(String\.valueOf|equalToText\([^)]*\.toString\(\)" <файлы юнита>   # число или дата проверяются как текст - возьми условие по типу
grep -nE "assertAll\(" <файлы юнита>   # assertAll не используется: группа проверок - .shouldSoft(...), именованный шаг - Allure.step("...", () -> ...)
```
The check `MR-49` (extra layers):
```
grep -nE "^\s+(public |private |protected )?(static )?(final )?class [A-Z]" <файлы юнита>   # вложенный класс: должно быть пусто
grep -nE "^\s+return [A-Z][A-Za-z0-9]*\.[a-z][A-Za-z0-9]*\([a-zA-Z, ]*\);" <файлы юнита>   # метод-делегат: тело - вызов метода другого класса с теми же параметрами; уберите метод, вызывающих переведите на настоящий
```
The check `MR-47` (settings read with own code):
```
grep -nE "ConfigFactory\.create|new Properties\(\)|getResourceAsStream\(|ResourceBundle\.getBundle|System\.(getProperty|getenv)\(|@Value\(|PropertiesLoader|ConfigReader|PropertyReader" <файлы юнита>   # своё чтение настроек или сборка подключения руками: значения - в файлы настроек фрейма, код чтения удалить
```
The name check `MR-45` - run it as a separate command, and look only at the lines that you wrote:
```
grep -nE "(^|[ .(])[a-z][A-Za-z0-9]*_[A-Za-z0-9_]*( *\(| *=| *;|,|\))" <файлы юнита>   # метод, переменная или параметр с нижним подчёркиванием: переименуй в стиле createOrder / orderId
```
For each unit file that has `@Test` (a test class), also run `MR-46`:
```
grep -nE "@ExtendWith\(PerfeccionistaExtension|@SetEnvironmentConfiguration" <тест-класс>   # аннотации фрейма на самом тест-классе: должно быть пусто, если есть базовый тест-класс - наследуйся от него
```
and `MR-42`:
```
grep -nE "^\s*(private|protected|static) .*\(.*\)\s*(throws [A-Za-z, ]+)?\{" <тест-класс>                 # вспомогательные методы в тест-классе: должно быть пусто (кроме @BeforeEach/@AfterEach и подобных); не пусто - вынеси в класс шагов
grep -cE "getForCurrentThread\(\)|restClient\(\)|dataBaseClient\(|executeSelect\(|consumerClient\(|producerClient\(" <тест-класс>   # обращения к фрейму в тест-классе: в теле теста разовое обращение допустимо; если одно и то же действие встречается в 2 и более тестах - вынеси в шаг
```
Write the results into «Проверки» of the card next to `правила кода MR`.

## Clean changes

- **MR-17 · Remove old code, do not comment it out.** Do not keep commented
  old code «на всякий случай»: git has it. Remove old comments and Javadoc that
  describe the old implementation (old classes, the old way of the call) together with it.
- **MR-18 · Do not reformat untouched code.** Do not change indents, line breaks and order in lines
  that are not related to the migration. The diff must contain only the migration and the fixes of
  violations `MR-33`..`MR-36`, `MR-4` in the unit files.
- **MR-19 · The code style of the project.** Indents, line length, braces - as in this file and
  in checkstyle. For `var`, see the separate strict rule `MR-33`. Do not add `final` to
  parameters/variables if the project does not do this, and the reverse.
- **MR-20 · Javadoc and comments - as in the project.** If a method had Javadoc, keep it and
  fix it if the meaning/parameters changed. The language of comments - as in the file. Do not write
  comments like «мигрировано на PVATF», «было так - стало так».
- **MR-21 · No silent `TODO`.** Do not leave `TODO`/`FIXME` in the code. Write what is not finished
  into the card («Где остановился») or into «Входящие» of the map.
- **MR-22 · Do not suppress errors.** Do not add `@SuppressWarnings`, empty `catch`, `throws
  Exception` «чтобы скомпилировалось».

## Legacy removal

- **MR-23 · Two implementations do not exist together.** After you move a place to PVATF, remove the old implementation
  of this place fully. Do not keep the old class next to the new one, do not mark it
  `@Deprecated`, do not keep it «на переходный период». The map sets the only exception: the old
  technology core lives until the `usage` units rewrite its callers (in mode
  `new` - untouched, in mode `in-place` - with the old public methods and the framework
  inside). Then `cleanup` removes it. Do not make such an exception yourself.
- **MR-24 · No bridges.** Do not write new adapters, converters and wrappers that connect
  old code with PVATF or make PVATF «похожим на старое». Change the calling code to the
  framework mechanism directly, as in the documentation.
- **MR-25 · The old architecture does not move.** Do not repeat on PVATF the old layers,
  base classes, factories and utilities «как было, только на новом фрейме». The structure is the structure
  in the target picture `T-<tech>`, in the framework documentation and in the steps of the card. Signs that you
  move the old things (each sign is a violation):
  - a new class has the name of the old one or the same methods;
  - a framework client or service is hidden in a field of your own class, and the tests go through this class;
  - the new code still has a static helper «отправить запрос и проверить код»;
  - a test extends its own base class to get access to the client;
  - a check uses an own method `assertXxx`/`checkXxx` instead of a framework matcher.
- **MR-32 · Take data from the old code, not mechanics.** Move: what we call
  (address, method, topic, query), what we send (body, parameters, headers), what we expect
  (code, fields, values). Do not move: how the call was made, how the response was parsed, how values were compared.
  The framework does this.
- **MR-26 · Remove only what has no references.** Before you remove a class, a package,
  a dependency or a config, grep the project. If references stay outside the unit files, do not remove it and
  do not change other files: write into «Входящие».
- **MR-27 · Remove fully.** If you removed a class, also remove its imports, its configs and resources.
  Also remove its mentions in the build (dependency, plugin, version property) and the empty package.

---

## Правила: добавлено человеком

<!-- Этот блок пишет команда руками. Сюда добавляются правила, специфичные для вашего фрейма
     и проектов (формат: MR-H<n> · название. Правило. Исключения.). Эти правила приоритетнее
     правил MR выше. Пусто = дополнительных правил пока нет. -->

(пусто)
