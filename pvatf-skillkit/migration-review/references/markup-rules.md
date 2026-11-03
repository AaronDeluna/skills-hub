# Test markup (allure-annotations)

This is a shared file of the kit. The source is `shared/markup-rules.md`.
`scripts/SyncShared.java` puts the copies into the skills. If you change the file, change only the source.

The markup is the annotations of the library `allure-annotations` (`ru.sber.qa`). Allure
TestOps uses them to filter the tests and to make statistics. The markup is not related to the
framework documentation: this file contains all that you must know for the markup. Do not make
other markup annotations.

These skills use this file:
- `orchestrator`, the separate markup check (`references/markup.md`): it checks the project and,
  if the human agrees, adds the missing markup, without a migration;
- `migration-map`, Stage 2, step 1b: it finds if the project has markup and collects the values;
- `migration-step`, the unit `markup`: it adds the annotations (agent `pvatf-marker`);
- `migration-review`, item `P16`: it checks that the markup is present.

## 0. Where to search - only in the project

The markup is five to seven annotations from the table in section 1. All that you must know
about them is in this file. Do not search for information about them.

Run all markup commands from the project root, on the project files (path `.` or the test directory).
**Prohibited:**
- going outside the project root: `find /`, `find ~`, `cd ..`, absolute paths outside the project,
  other projects on the computer;
- the framework project, its sources, the example project, the MCP documentation: the markup does not need them;
- `~/.m2`, `~/.gradle`, the contents of a .jar (`unzip`, `jar tf`, `javap`), decompilation,
  the internet - except one exception below.
If you do not find a package, a version or a value in the project -> do not search more. This is a
normal case, and a rule exists for it: packages - the table in section 2, item 5; dependency and version - only the dependency
tree (section 5); value - a question to the human (section 4) or `-`.

**One exception - the jar of the library allure-annotations itself.** If the build has version 2.x
of this library (it was there, you added it from zero, or you upgraded it), you can look at its jar. Do this only to check an
annotation that is not in the import table (section 2, item 5; section 5, «Пакет и аннотации - из
jar библиотеки»). For the annotations from the table you do not need the jar. Use only this one
jar, and only the commands from there: the path from the build, `jar tf`, `javap`. Other jars, the rest of
`~/.m2` and `~/.gradle`, sources and unpacking stay prohibited. If the version is lower than 2.x -> do not look
at the jar.

## 1. Mandatory annotations

The base of the markup is five annotations: stage, layer, КЭ (system code), team, TMS link. If the test model
is in Allure TestOps, two more annotations are added: regress and task. Where the model is (Allure TestOps,
Zephyr or a different TMS) is the question `model` (section 4).

| Annotation | Meaning | Mandatory | Who adds it and where the value comes from |
|-----------|------------|-------------|------------------------------|
| `@TestStage` (or a ready one: `@IsolatedTest`, `@DevStandTest`, `@StStandTest`, `@IftStandTest`, `@PsiStandTest`, `@PromStandTest`) | the stage (environment) where the autotest runs | always | agent, question `stage` |
| `@TestLayer` (or a ready one: `@ApiTest`, `@DbTest`, `@MqTest`, `@UiTest`) | the layer on which the test runs (section 3) | always | agent, no question |
| `@System("<КЭ>")` | the КЭ of the system under test | always | agent, question `system` |
| `@Team("<команда>")` | the team that owns the autotest | always | agent, question `team` |
| `@TmsLink("<ключ>")` | the link from the autotest to the manual test in the TMS | always, above each test method | **the human**: the manual test key is only in the TMS. The agent adds it in one case only: the test-case key (`<КОД>-T<цифры>`) is already written in `@DisplayName` of this test method (section 2a). The agent does not change `@DisplayName`. The agent does not make up a key. The agent shows the other test methods without it in the report |
| `@Regress` or `@CriticalRegress` | the test is in the regress / in the critical regress; do not add both | only for a model in Allure TestOps | agent, question `regress` |
| `@Story("<задача>")` or `@Issue("<задача>")` | the link from the test to a task | only for a model in Allure TestOps | agent, question `story` |

**Agent set** - all rows of the table except `@TmsLink`. The agent set decides if the
project has markup (section 5). `@TmsLink` has a separate check: the agent copies the test-case keys from `@DisplayName`
itself (section 2a). The rest goes into the report as work for the human.

Ready annotations and values:

| Ready annotation | Same as |
|-------------------|-------------|
| `@ApiTest` | `@TestLayer("api")` |
| `@DbTest` | `@TestLayer("db")` |
| `@MqTest` | `@TestLayer("mq")` |
| `@UiTest` | `@TestLayer("ui")` |
| `@IsolatedTest` | `@TestStage("code")` |
| `@DevStandTest` | `@TestStage("dev")` |
| `@StStandTest` | `@TestStage("st")` |
| `@IftStandTest` | `@TestStage("ift")` |
| `@PsiStandTest` | `@TestStage("psi")` |
| `@PromStandTest` | `@TestStage("prom")` |

## 2. How to add - as a cascade

An annotation above a class applies to all its tests. An annotation above an abstract base class applies to all
tests of its subclasses. Do not add the full set above each method.

1. One value for all the project (`@System`, `@Team`, `@TestStage`, a common `@Regress`,
   a common `@Story`) -> add it above the base test class. This is the class that the test classes
   extend (from `ARCHITECTURE.md`; without a map - the class after `extends` in the
   test classes). Add it there also if the class is not abstract. Do not add these annotations
   above the subclasses. If the test classes extend different base classes -> add them above each of
   these base classes. If a test class has no base class -> add them above the test class itself.
2. `@TestLayer` - above the test class, or above the base class of the layer if the tests of one layer
   extend it. If a test class works with the system through more than one layer, select the layer by
   what the test checks (where the request goes, whose response the test checks).
3. `@TmsLink` - only above a test method, one for each test. The agent adds it only by
   section 2a - the key from `@DisplayName`.
4. If an annotation is already present (above a method, a class or a base class) -> do not change it and do not
   add it again lower in the hierarchy. If it is not above the base class, but it is already above some of its
   subclasses -> do not add it above the base class. Add it above the subclasses that do not have it
   (not their own and not through a parent). Do not move and do not remove annotations that you did not add.
5. Imports - explicit, without `*`, one for each annotation: **each annotation has its own package**.
   Use the imports exactly from this table. Do not search for them:

   | Annotation | Import |
   |-----------|--------|
   | `@TestLayer` | `ru.sber.qa.allure.layer.TestLayer` |
   | `@ApiTest`, `@DbTest`, `@MqTest`, `@UiTest` | `ru.sber.qa.allure.layer.layers.<Имя>` |
   | `@TestStage` | `ru.sber.qa.allure.stage.TestStage` |
   | `@DevStandTest`, `@StStandTest`, `@IftStandTest`, `@PsiStandTest`, `@PromStandTest` | `ru.sber.qa.allure.stage.stages.<Имя>` |
   | `@System` | `ru.sber.qa.allure.system.System` |
   | `@Team` | `ru.sber.qa.allure.team.Team` |
   | `@Regress`, `@CriticalRegress` | `ru.sber.qa.allure.regress.<Имя>` |
   | `@TmsLink`, `@Story`, `@Issue` | `io.qameta.allure.<Имя>` - these are annotations of Allure itself, not of allure-annotations |

   The only annotation that is not in the table is `@IsolatedTest`. Its import is the same as for the other stage annotations
   (`ru.sber.qa.allure.stage.stages.IsolatedTest`). But first check that the class is in the jar
   (section 5, «Пакет и аннотации - из jar библиотеки»). If it is not in the jar -> do not add it. Write in the report:
   `<аннотация> - не поставлена: нет в allure-annotations <версия>`. Do not use a similar
   annotation instead.

   **`@System` and `java.lang.System`.** The import `ru.sber.qa.allure.system.System` hides the
   standard `System` in the file: `System.getProperty(...)`, `System.out`, `System::currentTimeMillis`
   will not compile. Before you add `@System`, check the file for any
   use of `System` other than the annotation and the imports:
   `grep -nE "\bSystem\b" <файл> | grep -vE "@System\(|^[0-9]+:[[:space:]]*import "`. Empty output -> use a usual import. Lines found -> in this file
   only, write the full name without an import:
   `@ru.sber.qa.allure.system.System("<КЭ>")`.

   If you get the error «cannot find symbol» on the import of an annotation, do not fix it by a search. Remove this annotation and
   write it in the report.
6. Check the dependency `ru.sber.qa:allure-annotations` and its version before all changes, as the first
   step, with the dependency tree (section 5, «Зависимость и версия»). If the module with tests does not
   have it -> add it to the build of this module from zero, scope `test` (Gradle - `testImplementation`).
   The version comes from the markup values (there it is `2.0.2`, if the human did not give a different one). If it is already present (also
   when it comes through a different library) -> do not change it: not the version and not the scope. One
   exception: the markup values contain `версия: поднять <старая> -> 2.0.2` or, when the version was not known
   at the map, `поднять до 2.0.2, если ниже` and the tree now shows major 0 or 1 (section 2b, item 2) ->
   change the version number to `2.0.2` where the project writes it (in the dependency or in a
   property; command «Где записан номер версии», section 5). If the project does not write the number
   (a BOM or a parent pom sets the version, or it comes through a different library) -> add the
   dependency explicitly to the build of the module with tests, with version `2.0.2`. Do not change other things
   in the build. Do not search for the version in a .jar, in `~/.m2` or on the internet.

## 2a. Test-case key in `@DisplayName`

Search for the keys in **all** test classes of the project, not only in the classes where you add the other
annotations. A test class that has markup through a base class can still need
`@TmsLink` above its methods. To get the list of these methods, use the command «Ключи тест-кейсов без
`@TmsLink`» (section 5).

Sometimes the name of a test contains the key of the manual test case:
`@DisplayName("[SBOLCRM-T1234] Создание заказа")`. The agent **copies** this key into `@TmsLink`
of this test method. **Do not change `@DisplayName`**: do not remove the key or the text from it.

**Test-case key** - `<КОД ПРОЕКТА>-T<цифры>`: the project code (the first character is a capital Latin
letter, then capital Latin letters and digits), a hyphen, the letter `T` and then digits. Correct keys: `SBOLCRM-T1234`, `PVATF-T12`, `AB2-T7`. The letter `T` before the digits is
the sign of a test case. Without it (`PVATF-4567`, `SBOLCRM-123`) the key is a task, a bug or a story,
not a test case. Do not use such a key, also if it is the only key in the name.

Use the key only if all these conditions are true:
1. the name of the test method has exactly one test-case key (`-T<цифры>`). The name is `@DisplayName`
   and `name` of `@ParameterizedTest` together: the same key in both is one key, different keys are two keys.
   The position of the key in the name is not important;
2. the test method does not have `@TmsLink` yet;
3. no other test method has the same test-case key - not in `@DisplayName`, not in
   `name` of its `@ParameterizedTest`, not in its `@TmsLink` (a parameterized test is one
   method, its runs do not count; a `@DisplayName` above a class does not count).
Check condition 3 before you add `@TmsLink`: first run the command «Одинаковые ключи
тест-кейсов» (section 5), then make the changes. Do not remove an added `@TmsLink` (section 6).
If one or more conditions are false -> do not add anything: the test method goes into the report as work for the
human. **In the report, write the reason in words, not the condition number.** This shows that it is not
an agent failure:
- same key (condition 3) - one line for each key, with all its test methods:
  `<ключ> - одинаковый в <Класс.метод>, <Класс.метод>: новый @TmsLink не поставлен,
  уже стоит у <Класс.метод / никого>, решите, какому тесту он принадлежит` (to find them, use the command «Одинаковые ключи тест-кейсов»,
  section 5);
- two keys in one name (condition 1): `<Класс.метод> - в @DisplayName два ключа
  тест-кейса: <ключ>, <ключ>`;
- `@TmsLink` is already present with a different key (condition 2): `<Класс.метод> - уже @TmsLink("<ключ>"),
  в названии <ключ>`.

**A parameterized test (`@ParameterizedTest`) is a test method of the same type.** It runs
many times with different data, but it is one method and one test case: add `@TmsLink` above it
the same as above `@Test`. This is not a same key (condition 3): condition 3 is about one key in two
different methods. Take the key from `@DisplayName` or from the name template
`@ParameterizedTest(name = "[SBOLCRM-T1234] {0}")` (condition 1):
```java
@TmsLink("SBOLCRM-T1234")
@ParameterizedTest(name = "[SBOLCRM-T1234] {0}")
@ValueSource(strings = {"a", "b"})
void create(String value) { ... }
```
If `@DisplayName` and `name` of the same method have the same key, it is one key, not two. If they have
different keys, it is two keys: condition 1 is false.

How to add:
- above the test method - `@TmsLink("<ключ>")`. The key is exactly as in the name, without brackets and
  separators: `@DisplayName("[SBOLCRM-T1234] Создание заказа")` -> `@TmsLink("SBOLCRM-T1234")`.
  `@DisplayName` stays as it was;
- do not change a `@DisplayName` above a class and do not take keys from it: it is not a test method.

## 2b. Before the changes - three checks

Add the markup only by the rules of this file. These rules are for allure-annotations
2.x. Here and below, «2.x» is major version 2 or higher (`2.0.2`, `2.5.0`, `3.0.0`); «ниже
2.x» is major version 0 or 1. Thus, before the first change, do these checks in this order:

1. **Uncommitted changes.** From the project root:
   `git status --porcelain -- . ':(exclude).gigacode'`. If the output is not empty -> do not make changes,
   stop. Tell the human: «В проекте есть незакоммиченные изменения: <файлы из вывода>.
   Закоммитьте их, и я продолжу разметку». Reason: the markup is a separate commit. Changes of other people
   must not go into it, and a rollback of the markup will remove them.
2. **Library version.** Get the version from the dependency tree (section 5, «Зависимость и
   версия»), not from a search in files. The first number of the version (before the first dot) is the major
   version: `1.8.3` -> 1, `2.0.2` -> 2.
   - no dependency -> it will be added with version `2.0.2`, the check is passed;
   - major version 2 or higher -> the check is passed;
   - the tree failed (section 5: the command failed) -> the dependency is not known: do not make
     changes, stop. Tell the human: «Не удалось построить дерево зависимостей, поэтому
     не понять, есть ли allure-annotations и какой версии: <первые строки ошибки>.
     Исправьте сборку и повторите запрос»;
   - major version 0 or 1 -> markup by the rules is not possible. Offer the human an upgrade of the
     version to 2.0.2 (question `upgrade`, section 4). `да` -> the markup values get
     `версия: поднять <старая> -> 2.0.2`, and the version is upgraded together with the markup (section 2,
     item 6). `нет` -> do not make changes, stop. Tell the human: «Разметить тесты по правилам не
     получится: в проекте allure-annotations <версия>, а нужна 2.x».
   Who asks: in a migration - `migration-map` at Stage 2 (step 1b); in the separate markup
   check - `orchestrator` before the values. The markup agent does not ask, it compares: if the
   build has major version 0 or 1 and the markup values do not have `поднять` -> stop with the
   status «не сделан: allure-annotations <версия>, нужна 2.x».
3. **Compilation.** Run the project compile command before the changes. If it fails -> do not make changes,
   stop. Tell the human: «Проект не компилируется, поэтому разметку поставить нельзя:
   <первые строки ошибки>. Исправьте сборку и повторите запрос». Reason: if not, after the
   markup you cannot know whose error it is - yours or an error that was there before.

If all three checks are passed -> you can add the markup. After this, a compilation error after the changes
is caused by the markup: fix it yourself.

Checks 1 and 3 are done by the one who adds the markup: the agent `pvatf-marker`, or you, if you
add the markup without the agent. The agent does not write to the human: it returns the status «не сделан: <причина>».
The one who started the agent writes the message from this section to the human.

## 3. Layer

The layer is not the technology. It is the level on which the test works with the system. Look at what the
test uses to access the system and whose response it checks. The technology label in the map only gives a hint about
the layer:

| What the test uses to work with the system | Annotation | Hint: technology of the map |
|------------------------------------|-----------|-----------------------------|
| system API: HTTP requests, gRPC, GraphQL, WebSocket, API stubs | `@ApiTest` | `rest`, `grpc`, `graphql`, `websocket`, `sbermock` |
| user interface: browser, mobile application | `@UiTest` | `ui-selenide`, `ui-playwright`, `appium-android`, `appium-ios` |
| database directly | `@DbTest` | `db`, `datasource` |
| message queues | `@MqTest` | `kafka` and other queues |
| other | `@TestLayer("<слой>")` | - |

## 4. Questions to the human

The question `upgrade` is about the library version (section 2b, item 2). Ask the other questions only for
annotations that the project does not have. If the project has the value (the annotation
is already present, or the КЭ / team is written in the settings, README, Jenkinsfile) -> take it from there,
do not ask the question. Use the order of the table. When to ask: in a migration - at Stage 2 of the map
(step 1b); in the separate markup check - before the changes (`orchestrator`,
`references/markup.md`).

| Key | Вопрос | When to ask | Ответ |
|------|--------|----------------|-------|
| `upgrade` | В проекте allure-annotations версии ниже 2.x, а разметка по правилам требует 2.x. Поднять версию до 2.0.2: да или нет? | the major version in the build is 0 or 1 (section 2b, item 2); ask it first | `да` / `нет`. `нет` -> do not ask the other questions, do not add the markup |
| `model` | Где хранится тестовая модель: Allure TestOps, Zephyr или другая TMS? | always, if the markup is necessary | Allure TestOps -> `testops`; other -> `tms: <название>` |
| `system` | Какой КЭ у тестируемой системы? Например, CI02546875. | no `@System` | КЭ |
| `stage` | На каком контуре работают автотесты: code, dev, st, ift, psi или prom? | no `@TestStage` and no ready stage annotations | one value |
| `team` | Как называется команда? Полное название, как в справочнике команд. | no `@Team` | team name |
| `regress` | Тесты входят в регресс: regress - в регрессе, critical - в критичном регрессе, `-` - не входят? | `model: testops`, no `@Regress`/`@CriticalRegress` | `regress` / `critical` / `-` |
| `story` | Какая задача у тестов? Например, PVATF-4567, или `-`, если задачи нет. | `model: testops`, no `@Story`/`@Issue` | task / `-` |

How to ask: in a usual message, with exactly the text from the column «Вопрос», one question at a time.
Do not rephrase. Do not add explanations or your own answer options. Do not add to the question
«напишите», «введите», «укажите», and do not offer your own names: the human answers.
If the answer does not agree with the column «Ответ» -> ask the same question again one time.

In a migration, write the answer into the map passport, line «Разметка» (map template). Answer `-` means
do not add this annotation; write it so. There are no questions about `@TmsLink`: the human adds the manual test keys
himself.

## 5. When the markup is not necessary

The markup (the unit `markup` or the changes in the separate check) is not necessary if:
- each test class already has the agent set (section 1, itself or through a base class), and
  there are no test-case keys in `@DisplayName` that you can copy into `@TmsLink` (section 2a);
- `scope: core` - in this mode the tests do not change (migration only);
- allure-annotations in the build is lower than 2.x, and the human did not agree to upgrade the version (section 2b,
  item 2): markup by the rules is not possible.

«Проверка, что размечено» - the check that the markup is present (on the test directory):
```
grep -rlE "@(TestLayer|ApiTest|DbTest|MqTest|UiTest|UnitTest|CdcConsumerTest|CdcProviderTest|PerformanceTest)\b" --include='*.java' --include='*.kt' <каталог тестов>
grep -rlE "@(TestStage|IsolatedTest|DevStandTest|StStandTest|IftStandTest|PsiStandTest|PromStandTest)\b" --include='*.java' --include='*.kt' <каталог тестов>
grep -rlE "@(ru\.sber\.qa\.allure\.system\.)?System\b" --include='*.java' --include='*.kt' <каталог тестов>
grep -rlE "@Team\b" --include='*.java' --include='*.kt' <каталог тестов>
grep -rlE "@(Regress|CriticalRegress)\b" --include='*.java' --include='*.kt' <каталог тестов>
grep -rlE "@(Story|Issue)\b" --include='*.java' --include='*.kt' <каталог тестов>
```
If a file is in the output -> the annotation is above its class (look and make sure that it is above `class` and
not above only one method). If a file is not in the output, open it before you add an annotation: grep finds a line,
not an annotation (for example, the argument can be on the next line). If the annotation is above the class -> it is present. Regress and task are two different rows of the set: check each
separately.

«Зависимость и версия» - get the dependency and the version from the build dependency tree, not by a search in files. The tree
shows the version that the tests really get, also if a property, a
parent pom, a BOM or a different library sets it. From the project root:
- Maven (no `mvnw` -> `mvn`):
  ```
  ./mvnw dependency:tree -Dincludes=ru.sber.qa:allure-annotations
  ```
  The tree is printed for each module (line `--- ... @ <модуль> ---`). If the line
  `ru.sber.qa:allure-annotations:jar:<версия>:<scope>` is in the module block -> the module has it, the version is
  the fourth field. If there is no line -> the module does not have it;
- Gradle (no `gradlew` -> `gradle`), for each module with tests (one module - without
  `:<модуль>`):
  ```
  ./gradlew -q :<модуль>:dependencies --configuration testRuntimeClasspath | grep "ru.sber.qa:allure-annotations"
  ```
  Line `ru.sber.qa:allure-annotations:<версия>` -> present. If the line has `->`
  (`...:1.8.3 -> 2.0.2` or `ru.sber.qa:allure-annotations -> 2.0.2`) -> the version is the text
  after `->`. The marks `(*)`, `(c)` at the end of the line are not part of the version. Empty -> the module does not have it:
  grep found nothing - this is not a command error.
Remember for each module with tests: `есть <версия>` or `нет`. If different modules have different
versions -> for section 2b, item 2 use the lowest one.
If the command failed (Maven - `BUILD FAILURE`, Gradle - `FAILURE:` or `What went wrong`: no network,
dependencies were not downloaded, build error) -> the dependency is not
known: show the first lines of the error; what to do - section 2b, item 2. Do not search for the dependency in files, in a .jar,
in `~/.m2` or on the internet - use only the tree.

«Пакет и аннотации - из jar библиотеки» - the package and the annotations from the library jar (section 0, exception; only when version 2.x is already
in the build and only for an annotation that is not in the import table of section 2, item 5). First get the path to the jar. The build gives it. Do not search in folders:
- Maven:
  ```
  ./mvnw -q dependency:build-classpath -Dmdep.outputFile=/dev/stdout | tr ':' '\n' | grep "allure-annotations-.*\.jar" | sort -u
  ```
- Gradle - exactly this folder, with the version from the tree:
  ```
  find ~/.gradle/caches/modules-2/files-2.1/ru.sber.qa/allure-annotations/<версия> -name "allure-annotations-<версия>.jar"
  ```
Then get the list of annotations and their packages:
```
jar tf <путь к jar> | grep '\.class$' | grep -v '\$'
```
Each line is one annotation with its package: `ru/sber/qa/allure/layer/layers/UiTest.class`
-> class `UiTest`, import `ru.sber.qa.allure.layer.layers.UiTest` (slashes become dots, without
`.class`). Write the package for each annotation from section 1 separately: the packages are different. If it is not clear how to write an annotation, find what it accepts (does it have `value`):
`javap -cp <путь к jar> <пакет>.<Аннотация>`. Do not look at other things in the jar: do not unpack,
do not decompile, do not open other jars.

«Где записан номер версии» - where the version number is written (necessary only for the version upgrade, section 2, item 6):
```
grep -rn "allure-annotations" --include=pom.xml --include='*.gradle' --include='*.kts' --include='*.toml' . | grep -v "/target/\|/build/"
```
If a property sets the version (`${allure.annotations.version}`, `libs.versions.toml`) -> the place is
this property: `grep -rn "<имя свойства>" --include=pom.xml --include='*.gradle' --include='*.kts' --include='*.properties' --include='*.toml' .`.

Find and count the test-case keys and the test methods with the script, not with grep. The script reads
multi-line annotations, spaces and line breaks before `(`, full annotation names, annotations on one line with
the method, `@ParameterizedTest` and Kotlin. It takes only test methods (`@Test`, `@ParameterizedTest`,
`@RepeatedTest`, `@TestFactory`, `@TestTemplate`). It takes the keys only from the value of the annotation: string
literals, text blocks and their concatenation with `+`. If the value is something different (a constant, a method call)
-> the script cannot read it and prints the line `... - значение не разобрать, проверьте вручную`.
It does not take comments, strings and text blocks outside the annotations, and a `@DisplayName` above a class. The last output line is always `итого: <n>`: it is not a test method. Each other line is a finding.
`итого: 0` -> no findings. If there are more test directories than one -> write all of them, separated by spaces.

«Ключи тест-кейсов без `@TmsLink`» - test-case keys without `@TmsLink` (candidates for section 2a):
```
java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/MarkupKeys.java missing <каталог тестов>...
```
Line: `<файл>:<строка>: <метод> - <ключи> - нет @TmsLink`. If a line has two or more keys -
condition 1 of section 2a is false. Line `<файл>:<строка>: <метод> - значение не разобрать, проверьте вручную` ->
do not add `@TmsLink`: it is work for the human, reason «значение @DisplayName не разобрать скриптом». The last line is `итого: <n>`.

«Одинаковые ключи тест-кейсов» - the same test-case keys in different test methods (condition 3 of section 2a; the script counts the keys
from `@DisplayName`, from `name` of `@ParameterizedTest` and from `@TmsLink`):
```
java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/MarkupKeys.java dup <каталог тестов>...
```
Line: `<ключ> - <файл>:<строка>:<метод> <файл>:<строка>:<метод> ...`. Line
`<файл>:<строка>:<метод> - значение не разобрать, проверьте вручную` -> the key of this method is not known: write it in
the report for the human. `итого: 0` means there are no same keys.

«Тест-методы без `@TmsLink`» - test methods without `@TmsLink` (work for the human, not a reason for agent changes):
```
java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/MarkupKeys.java count <каталог тестов>...
grep -rlE "@(Test|ParameterizedTest)\b" --include='*.java' --include='*.kt' <каталог тестов> | xargs grep -LE "@TmsLink\b"
```
The script prints three lines: `тест-методов: <n>`, `с @TmsLink: <n>`, `итого без @TmsLink: <n>`. Use these numbers in reports.
The grep shows the test classes that have no `@TmsLink`. It is an estimate only: open a file before you use it.

## 6. Final re-check at the end - mandatory

This is the last step of all markup: after all changes, before the commit. Without it the work is not done.
A frequent error: the annotations above the class are added, but `@TmsLink` above the test methods with a key in
`@DisplayName` is missing. The final re-check finds exactly this error.

1. **Test-case keys without `@TmsLink`.** First run the command «Одинаковые ключи тест-кейсов»
   (section 5) on all test directories: do not add the keys from its output to any method (condition 3
   of section 2a). Then, from the project root, run the command «Ключи тест-кейсов без `@TmsLink`»
   (section 5) on all test directories:
   ```
   java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/MarkupKeys.java missing <каталог тестов>...
   ```
   Each output line is a test method that has a test-case key but no `@TmsLink`. For each line: if the conditions of section 2a are true -> add `@TmsLink` with
   this key; if they are false -> write it in the report with the reason in words (section 2a: a same key -
   with all its test methods). You must fix each output line or
   explain it in the report. Do not skip a line silently. `итого: 0` -> all keys are taken.
   **Never remove and never move `@TmsLink`** - not one that you did not add, and not one that you added in this
   markup. If an output line is about a method that already has `@TmsLink` with this key, it is
   a check error, not a reason for a change: do not change anything. Write in the report:
   `<Класс.метод> - перепроверка показала «нет @TmsLink», но он стоит`.
   **If the file is not in the plan (or not in «Файлах юнита»), add the annotation all the same.** This occurs with test classes
   that get annotations through a base class (for example, UI tests with `@UiTest` on the
   base UI class): they are not in the plan, but they contain keys. In such a file you can change
   only these: `@TmsLink` above a test method and the import `io.qameta.allure.TmsLink`. In the report:
   `<файл> - добавлен по перепроверке`.
   Write each key from the output of the command «Одинаковые ключи тест-кейсов» in the report, with all its
   test methods. This line of the report is mandatory, also if the output is empty.
2. **Agent set.** Run the commands «Проверка, что размечено» from section 5 on the test classes of this
   markup: the files from the plan (task package) and the subclasses of the base classes from it. Each such
   test class must have markup (itself or through a base class) with each annotation of the agent set
   that has a value (not `-`). A different unit adds markup to the other test classes of the project
   (there are more markup units than one): do not change them and do not write them as findings. The test-case keys (item 1)
   are the opposite: check them on all test directories.
3. **Imports.** Each added annotation has an import from the table of section 2, item 5 (or
   the full name of `@System` by the same item); there are no imports with `*`.
4. **The existing code lines did not change:** the markup only adds lines (annotations
   and imports). Thus the test sources must not have a removed or changed
   line. This makes sure that `@DisplayName` and the test logic did not change:
   `git diff HEAD -- '*.java' '*.kt' | grep -E "^-[^-]"` must be empty (before the markup commit, all its
   changes are not committed yet; after the commit, use the base instead of `HEAD`).
5. If you fixed something -> run the compilation and items 1-4 again, until only the lines
   explained in the report stay (same key, two keys, a different `@TmsLink` already present). Do not
   «дочищай» them (do not try to clean them up): these methods do not get `@TmsLink`.
