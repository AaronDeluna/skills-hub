# Separate markup check

Open this file when the human asks to check or add the test markup, not to migrate the
project: «проверь разметку», «разметь тесты», «поставь разметку». Do not start the migration
skills. Do not make and do not change the migration map. This is not a migration: here you ask the human questions
during the work (rule 8 of `references/core-rules.md` applies to a migration).

The markup rules are in `references/markup-rules.md`. Read the full file before the first command.
The report is `.gigacode/data/markup/MARKUP-REPORT.md`. Each run writes it again from zero.

**Where to search - only in the project** (section 0 of the markup rules). Do not go outside the project root
(`find /`, `find ~`, other projects). Do not go into the framework project and sources, the example project,
`~/.m2`, `~/.gradle`, .jar and the internet. Exception: the jar of allure-annotations itself, version
2.x, and only for an annotation that is not in the import table (section 0 of the rules). If you did not find a package, a version or
a value in the project -> do not search more: do what the rule for this case tells.

## 1. Preparation

1. Agents: run `java -Dfile.encoding=UTF-8 .gigacode/skills/orchestrator/scripts/NextAction.java`.
   If the output is `ДЕЙСТВИЕ: агенты установлены` -> say «Агенты установлены или обновлены. Перезапустите
   GigaCode (выйдите и запустите заново) и введите, чтобы продолжить с того же места:
   `/orchestrator <запрос человека дословно>`» and stop. Instead of `<запрос человека
   дословно>`, put the text that the human wrote after `/orchestrator`, without changes. All other
   actions are not related to this request: do not do them and do not show them. Do not copy the agents
   yourself and do not check `.gigacode/agents/`: the script does this.
2. **Dependency and version - first.** Make the dependency tree with the command
   «Зависимость и версия» from section 5 of the rules. Do not search for the dependency in the build files - use only
   the tree. Remember: `есть <версия>` or `нет`. If there is no dependency -> the version for the markup values is
   `2.0.2`, and the agent adds the dependency from zero. If the command failed -> say «Не удалось
   построить дерево зависимостей, поэтому не понять, есть ли allure-annotations и какой
   версии: <первые строки ошибки>. Исправьте сборку и повторите запрос» and stop. If the major version (the number before
   the first dot) is 0 or 1 -> remember `ниже 2.x`: before the changes, you must ask the question `upgrade`
   (section 3, item 1).
3. Find if a migration is in progress: if `.gigacode/data/migration/MIGRATION-MAP.md` exists and its unit table
   has a unit `markup` with a status that is not `done` -> the migration adds the markup. Do the check (section 2),
   but do not do the plan and the changes (sections 4-5). In the result, say «Разметку поставит шаг
   миграции M-<nnn>: `/orchestrator Продолжи миграцию`».
4. Test directories. First the standard paths:
   `find . -type d \( -path "*/src/test/java" -o -path "*/src/test/kotlin" \) | grep -v "/target/\|/build/\|\.gigacode"`.
   Then the build can set other paths: `grep -rnE "testSourceDirectory|srcDir|sourceSets|java\.srcDirs|kotlin\.srcDirs" --include=pom.xml --include='*.gradle' --include='*.kts' . | grep -v "/target/\|/build/"`.
   Add each existing directory from this output. If both commands found nothing, search the files with tests in the project:
   `grep -rlE "@(Test|ParameterizedTest)\b" --include='*.java' --include='*.kt' . | grep -v "/target/\|/build/\|\.gigacode"`.
   Their source root (the directory before the package path) is a test directory.
   Test classes are files with tests:
   `grep -rlE "@(Test|ParameterizedTest)\b" --include='*.java' --include='*.kt' <каталог>`.
   If there are no test classes -> say «В проекте не нашлось тестов для разметки» and stop.

## 2. Check

1. Run the commands of section 5 of the rules on each test directory: «Проверка, что размечено»,
   «Ключи тест-кейсов без `@TmsLink`», «Одинаковые ключи тест-кейсов» and «Тест-методы без
   `@TmsLink`».
2. For each test class, find the base class: Java - the name after `extends`, Kotlin - the name
   after `:` in the class declaration (`class ApiTests : BaseTest()`):
   `grep -nE "class [A-Za-z0-9_]+.*( extends |\) *: *| : )[A-Za-z0-9_.]+" <файл>`. Its file is
   `grep -rlE "(class|interface) <Имя>\b" <каталог>`. Go up while the parent is in the project.
   If the parent is not from the project (it is from a library), this is the end of the chain: you do not know its annotations. Remember which class
   extends which class: the plan needs it (section 4).
3. For each test class and each annotation of the agent set (section 1 of the rules): if the class is in
   the command output -> it has the markup itself. If not -> check its base classes the same way. If the class and its
   parents do not have the markup -> the annotation is missing.
4. `@Regress`/`@CriticalRegress` and `@Story`/`@Issue` are necessary only if the model is in Allure
   TestOps. If the model is not known yet -> in the report, mark these lines with «только для Allure
   TestOps». If one or more of them are missing -> you cannot give the result «размечен» until you have the answer to
   `model`: in item 7, first ask the question `model` (section 4 of the rules), then give the result.
5. Keys in `@DisplayName`: check each found line by the conditions of section 2a of the rules.
   If all conditions are true -> `взять`; if one or more are false -> `не взят: <причина словами>` (section 2a
   of the rules). Find the same keys with the command «Одинаковые ключи тест-кейсов» (section 5 of the rules)
   and show each key in one line with all its test methods.
   A key without `T` before the digits (`PVATF-4567`) is not a test case: do not put it in the table.
   A line «значение не разобрать, проверьте вручную» -> `не взят: значение @DisplayName не разобрать скриптом`.
6. Write the report `.gigacode/data/markup/MARKUP-REPORT.md` exactly by the template:
   ```
   # Проверка разметки
   Дата: <ГГГГ-ММ-ДД>
   Каталоги тестов: <пути через запятую>
   Тест-классов: <N> · тест-методов: <N> · с @TmsLink: <N>
   Зависимость allure-annotations (дерево зависимостей): <есть <версия> / нет - подключим с нуля><; ниже 2.x - нужно поднять до 2.0.2>
   Базовые классы: <базовый класс - сколько тест-классов от него наследуется; нет - "нет">

   ## Набор агента
   | Аннотация | Размечено тест-классов | Без неё |
   |-----------|------------------------|---------|
   | контур - @TestStage | <n> из <N> | <классы через запятую / -> |
   | слой - @TestLayer | <n> из <N> | <...> |
   | КЭ - @System | <n> из <N> | <...> |
   | команда - @Team | <n> из <N> | <...> |
   | регресс - @Regress (только для Allure TestOps) | <n> из <N> | <...> |
   | задача - @Story / @Issue (только для Allure TestOps) | <n> из <N> | <...> |

   ## TMS-link
   Ключи тест-кейсов в @DisplayName - агент скопирует в @TmsLink, @DisplayName не меняется: <N>
   | Тест-метод | Ключ | Решение |
   |------------|------|---------|
   | <Класс.метод> | <ключ> | <взять / не взят: причина словами> |
   Ключи не взяты - решите вы: <N>
   <по строке на ключ, причина словами (раздел 2а правил), например:
   `SBOLCRM-T1234 - одинаковый в CreateOrderTest.create, CreateOrderUiTest.create: @TmsLink не поставлен ни одному, решите, какому тесту он принадлежит`; нет - "нет">
   Тест-методов без @TmsLink и без ключа - ставите вы: <N>
   Тест-классы без @TmsLink: <классы / ->

   ## Значения разметки
   <пусто до раздела 3>

   ## План разметки
   <пусто до раздела 4>

   ## Итог
   <размечен / не размечен: каких аннотаций не хватает, сколько ключей взять в @TmsLink>
   ```
   If there are more than 15 classes without an annotation or more than 15 keys -> write the first 15 and «и ещё <n>».
7. Show the human the agent set table, the TMS-link part and the result.
   - If the regress or the task is missing and the model is not known:
     - the human asked only for a check -> first ask the question `model` (item 4). If the answer
       is not `testops` -> these lines are not part of the result;
     - the human asked to add the markup, or answered «да» to the question below -> do not ask `model` here.
       Go to section 3: the question `upgrade` comes first, `model` comes with the other values.
   - If the project has markup and there are no keys to take -> stop: give the final answer (section 6).
   - If the project does not have markup or there are keys `взять`, and the human asked only for a check -> ask
     «Поставить недостающие аннотации и @TmsLink по ключам из @DisplayName? да/нет».
     «нет» -> the final answer. «да» -> section 3.
   - If the project does not have markup or there are keys `взять`, and the human asked to add the markup -> section 3.

## 3. Values

First do two checks from section 2b of the rules. Do them before the questions, so that the human does not answer for no result:
1. Git: if `git status --porcelain -- . ':(exclude).gigacode'` is not empty -> say «В проекте
   есть незакоммиченные изменения: <файлы из вывода>. Закоммитьте их, и я продолжу
   разметку», write this in the result of the report and stop.
2. If the version is `ниже 2.x` (section 1, item 2) -> ask the question `upgrade` from section 4 of the rules, with exactly
   its text. `нет` -> say «Разметить тесты по правилам не получится: в проекте
   allure-annotations <версия>, а нужна 2.x», write this in the result of the report and stop. `да` ->
   the version for the values is `поднять <версия> -> 2.0.2`.

You need values only for the missing annotations. For each key of section 4 of the rules,
except `upgrade`:
1. Search for the value in the project: annotations, settings, README, Jenkinsfile
   (`grep -rniE "CI0[0-9]{7}|@Team|team|testops|zephyr|allure" --include='*.md' --include='*.properties' --include='*.yml' --include='Jenkinsfile*' . | grep -v "/target/\|/build/\|\.gigacode" | head`).
   If you found it -> use it with the mark `из проекта: <файл>`.
2. If you did not find it -> ask the human. Before the first question, say: «Для разметки нужны значения,
   которых нет в проекте. Задам несколько вопросов по одному». Ask the questions by the rules of
   section 4 of the rules: one at a time, in the order of the table, in a usual message, with exactly the text from
   the column «Вопрос», without your own explanations and options. If the model is not in Allure TestOps, the answer to `model` removes the questions
   `regress` and `story`.
3. The version comes from section 1, item 2 and the question `upgrade`: `версия: есть в сборке <версия>`,
   `версия: поднять <версия> -> 2.0.2` or `версия: 2.0.2`.
4. Write one line in the part «Значения разметки» of the report:
   `model: <testops / tms: название> · system: <КЭ / -> · stage: <контур / -> · team: <команда / -> · regress: <regress / critical / -> · story: <задача / -> · версия: <...>`.
   Answer `-` means: do not add this annotation.

## 4. Markup plan

Before the changes, make the plan and write it in the part «План разметки» of the report. The agent works by this plan,
and after that you check the result by the same plan.

1. Distribute the annotations by the rules of section 2 of the rules:
   - common for all tests (`@System`, `@Team`, `@TestStage`, common `@Regress` and `@Story`)
     -> above the base class from section 2, item 2. If the test classes extend different base
     classes -> one line for each base class. If a test class has no base class -> above the test class.
     Exception (section 2, item 4 of the rules): if some subclasses already have the annotation and the base class
     does not -> not above the base class, but one line for each subclass without it;
   - `@TestLayer` -> above the test class or above the base class of the layer (section 3 of the rules);
   - keys `взять` -> `@TmsLink` above the test method; `@DisplayName` does not change. A test class with
     such keys is in the plan in its own line, also if it gets all the other annotations
     through a base class (for example, UI tests with `@UiTest` on the base class);
   - no dependency -> the build files (section 2, item 6 of the rules);
   - `версия: поднять` -> the build file where the version number is written (in the dependency or in a
     property; command «Где записан номер версии», section 5 of the rules): `поднять
     allure-annotations <версия> -> 2.0.2`. If the project does not write the number -> the build file of the module
     with tests: `добавить allure-annotations 2.0.2 явно`.
   If an annotation is already present (on the class itself or on a parent) -> it is not in the plan.
2. Write the plan as a table, one line for each file:
   ```
   | # | Файл | Что сделать | Правило | Сделано |
   |---|------|-------------|---------|---------|
   | 1 | <путь> | <аннотации со значениями / какой ключ тест-кейса взять в @TmsLink из какого метода / зависимость с версией> | <раздел правил: 2.1 / 2.2 / 2а / 2.6> | [ ] |
   | <N> | все каталоги тестов | перепроверка: ключи тест-кейсов без @TmsLink, набор агента, импорты, @DisplayName не изменён | 6 | [ ] |
   ```
   The last line of the plan is always the final re-check (section 6 of the rules), also if the plan has
   one line only.
3. Compare the plan with the rules before you send it to the agent:
   - the common annotations are above the base class, and no line adds them again above
     its subclasses. Exception: the case of section 2, item 4 of the rules (above);
   - the plan does not have annotations that are already in the class or in its parent;
   - each key from the plan has the status `взять` in the report and has `T` before the digits;
   - `@TmsLink` is only in the lines with a key `взять`; the plan has no changes of `@DisplayName`;
   - value `-` -> this annotation is not in the plan;
   - `версия: поднять` -> the plan has a line with the version upgrade, and no other build changes;
   - the plan has annotations also if the project has no imports of the library:
     a project without markup is exactly what must get the markup. The agent takes the imports from
     the table in section 2, item 5 of the rules. Do not remove annotations from the plan because of the package.
   If you found an error -> fix the plan and compare again.

## 5. Changes

1. Git: run `git status --porcelain -- . ':(exclude).gigacode'` again. If it is not empty -> say «В
   проекте есть незакоммиченные изменения: <файлы из вывода>. Закоммитьте их, и я продолжу
   разметку» and stop.
2. Base: `git rev-parse HEAD` - remember the hash. You use it to check the changes, also if the
   agent already made the commit.
3. Compile command: if `pom.xml` exists -> `./mvnw -q test-compile` (no `mvnw` -> `mvn -q
   test-compile`); if `build.gradle` or `build.gradle.kts` exists -> `./gradlew testClasses`
   (no `gradlew` -> `gradle testClasses`).
4. Start the agent `pvatf-marker` by name (rule 7 of `references/core-rules.md`) with this task:
   ```
   Проект: <абсолютный путь>
   Юнит: без карты · markup · отдельная проверка разметки
   Файлы: <путь - изменить, по строке на файл из плана>
   Значения разметки: <строка из раздела «Значения разметки» отчёта>
   Что сделать: <строки плана по порядку: номер - файл - что сделать>
   Компиляция: <команда>
   Коммит: markup: разметка тестов allure-annotations
   ```
   If the agent returned «не сделан» because of the checks before the changes (section 2b of the rules) -> do not add
   the markup yourself and do not start the agent again. Tell the human the message from section 2b of the rules:
   - `есть незакоммиченные изменения` -> «В проекте есть незакоммиченные изменения:
     <файлы>. Закоммитьте их, и я продолжу разметку»;
   - `allure-annotations <версия>, нужна 2.x` -> «Разметить тесты по правилам не получится:
     в проекте allure-annotations <версия>, а нужна 2.x»;
   - `проект не компилируется до разметки` -> «Проект не компилируется, поэтому разметку
     поставить нельзя: <строки ошибки из отчёта>. Исправьте сборку и повторите запрос»;
   - `не построилось дерево зависимостей` -> «Не удалось построить дерево зависимостей,
     поэтому не понять, есть ли allure-annotations и какой версии: <строки ошибки из
     отчёта>. Исправьте сборку и повторите запрос».
   Write the reason in the result of the report and stop.
   If the subagent call returned an error (the agent did not start) -> show it in the chat and do the plan lines
   yourself, by sections 2-3 of the rules. Start with the checks of section 2b (item 1 and item 3), then
   make the commit the same way.
5. Check the result yourself, for each line of the plan:
   - `git diff --name-only <база> -- . ':(exclude).gigacode'` and `git status --porcelain --
     . ':(exclude).gigacode'` (your report in `.gigacode/` is not a violation): only the plan files
     and the files `добавлен по перепроверке` from the agent report changed (in these files - only `@TmsLink` and its
     import);
   - `git diff <база>`: only annotations, their imports and the dependency are added;
     `@DisplayName` did not change; the test logic did not change;
   - compilation - the command from item 3;
   - section 2, items 1-3 again: each test class has the agent set (annotations with the
     value `-` are not necessary), each
     taken key has `@TmsLink`, `@DisplayName` did not change;
   - the comparison from section 4, item 3 - now against the code, not against the plan;
   - the agent report is the block `=== ОТЧЁТ PVATF-MARKER ===` ... `=== КОНЕЦ ОТЧЁТА ===`, with all
     lines present. If there is no block or a line is missing -> retry the agent: «Верни отчёт по шаблону»;
   - do the final re-check from section 6 of the rules yourself, not by the agent report. If the command «Ключи
     тест-кейсов без `@TmsLink`» shows a line that has no reason in the agent report -> this is
     a plan line that is not done: retry the agent with it;
   - do the same keys check yourself: run the command «Одинаковые ключи тест-кейсов» (section 5 of the rules) on
     all test directories. Write each key from its output in the report (part «TMS-link», «Ключи не
     взяты») and in the final answer, with all test methods, also if the agent did not name it.
   If a plan line is done -> write `[x]` in the column «Сделано». If something is wrong -> do one retry of
   `pvatf-marker` with the list of the plan lines that are not done. If the second time also fails -> revert to the base only
   the markup files and do not change the other files.
   WARNING: do not use `git reset --hard`: it also removes the
   uncommitted changes in `.gigacode/`. Use this command:
   `git reset -q <база> && git checkout -- <файлы плана и «добавлен по перепроверке»>`.
   Write the reason in the result of the report, then give the final answer.
6. The agent makes the commit. If, after the check, `git status --porcelain` on the plan files is not empty
   (the agent did not make the commit or you made the changes yourself) -> `git add <файлы плана и файлы «добавлен по
   перепроверке»> && git commit -m
   "markup: разметка тестов allure-annotations"`. Do not commit the report in `.gigacode/`. Push
   only if the human asks for it directly.
7. Update the report by section 2, item 6 (the values and the plan stay the same, the plan gets the marks «Сделано»).

## 6. Final answer

Write it short:
- if the project has markup: the agent set table «было -> стало»;
- what was added and where (base class, test classes), how many test-case keys were copied into `@TmsLink` from
  `@DisplayName`, the commits (`git log --oneline <база>..HEAD`);
- values: which values came from the project, which values the human gave;
- work for the human: test methods without `@TmsLink` and without a key in the name; keys `не взят` -
  each in a separate line with the reason in words, same keys - with all test methods, for example
  «SBOLCRM-T1234 - одинаковый в двух тестах: A.create, B.create - @TmsLink не поставлен,
  решите, какому тесту он принадлежит»;
- report: `.gigacode/data/markup/MARKUP-REPORT.md`.
