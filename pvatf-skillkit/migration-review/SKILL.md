---
name: migration-review
description: 'Checks the result of the migration of a test-automation project to the framework PVATF (it works also without the migration service files - the migration map is optional): old code and old dependencies that stay, code rules (var, imports, asserts instead of matchers, response DTO, layers over the framework, long methods, classes with more than one responsibility), legacy that is not removed. It does not fix anything. It finds problems, writes a report and adds fix units (fix) to the migration map; migration-step then does these units. Use it when the migration is complete, or when the human asks «проверь миграцию», «как прошла миграция», «проверь, что агент не накосячил», «сделай ревью миграции». Usually orchestrator calls it after all units are done.'
---

**Language.** These instructions are in English. Write everything for the human in Russian:
messages, questions, reports, the map, unit cards, notes and commit messages. Copy every
template exactly as it is shown, with its Russian headings and field names.

# Migration check to PVATF (migration-review)

The migration went in small parts, in different chats. You look at the result AS A WHOLE.
You answer one question: is the project cleanly moved to the framework, or did old code stay
somewhere and are rules broken? **You do not fix anything and you do not change the project
code.** You find problems, write a report and add fix units for them. `migration-step` does
the fixes later, in other chats. After the fixes, the check runs again. This repeats until
the result is clean.

## Work in steps

1. Add Steps 1-7 to todo.
2. Do the steps in order. Write the result of each step to the report file IMMEDIATELY: the
   chat can stop at any time.
3. If you lose track, see «Если потерял нить».

## Check rules

The general migration rules are in `references/core-rules.md`. Read them at the start. Below
are only the rules for the check.

1. **Read only.** Do not change the project code, the build files or the configs. Write only
   to `.gigacode/data/migration/`: the report, the cards of new units, the unit table, the map
   header and (in mode «без карты») the architecture plan.
2. **Check by the checklist, not by taste.** A finding is a violation of one specific item
   (`V1`..`V26` from `references/review-subagent.md` or `P1`..`P16` from Step 3), with a file
   and a line number. If there is no item or no line, it is not a finding.
3. **Subagents read the files, not you.** Do not open full source files in your context. You
   count with commands and collect the tables from the review subagents. A review subagent
   only reads and answers with a table.
4. **Do not check technologies `keep` for migration.** Their old code, dependencies and
   configs stay legally. The code rules (`V1`, `V2`, `V10`..`V16`) apply to them only if the
   migration changed the file.
5. **Do not study the framework API** and do not call MCP. The target state is in the
   migration map (blocks `T`, tables `G` and `L`). If there is no map, the checklist is
   sufficient: see mode «без карты». No map is not a reason to refuse the check.

## Step 1 - Open the map and check the input

Read from `.gigacode/data/migration/MIGRATION-MAP.md`:
- the header;
- «1. Паспорт проекта» (commands, technology table, branches);
- «2. Что мигрируем» (tables `G`, `L`, blocks `T`);
- «4. Юниты работ». The units from the line «В архиве» above the table count as `done`. Old
  content that compression removed from the map is in `archive/MAP-ARCHIVE.md`. Read it only with `grep`.

Gates:
- no map (no folder `.gigacode/data/migration/` or no `MIGRATION-MAP.md` in it) -> this is
  NOT a stop: work in mode **«без карты»** (see the section below), then go back to Step 2.
- the map exists, but `map_status` is not `approved` -> **СТОП**: the map is not complete yet,
  it is too early for the check.
- there are units `todo` / `in-progress` / `blocked` (but not the units that wait because of `scope: core`):
  - the human asked for the check now -> do the check, but only for technologies where all
    units `cleanup` have status `done`. In the report write «проверка частичная» and list
    the technologies that you did not check;
  - else -> **СТОП**: first the units must be completed.
- `scope: core` -> check only the core: skip items `P1`, `P2`, `P3` of Step 3 (tests
  and legacy are not migrated yet). In the report write «проверка для scope core».

Find the round number: `review_round` in the map header + 1 (if there is no field, this is
round 1). Make the report file `.gigacode/data/migration/MIGRATION-REVIEW.md` from the
template in `references/report-template.md`. If the file exists, do not delete the old round.
Add a new section «Круг <n>» at the end.

## Mode «без карты» (no migration service files)

You can run the check on any project that is already moved to PVATF. This is true also if
somebody deleted the migration service folder, or if it never existed. The check does not
need the map: you collect all necessary data from the project.

1. Make the folder: `mkdir -p .gigacode/data/migration/units`.
2. **Make the passport yourself.** Write it at the start of the report, in the section
   «Паспорт для проверки»:
   - build and compile command: `pom.xml` exists -> `./mvnw -q -DskipTests test-compile`
     (no wrapper - `mvn ...`); `build.gradle(.kts)` exists -> `./gradlew compileTestJava -x test`
     (no wrapper - `gradle ...`);
   - source directories: `find . -type d -path "*src*" -name java -not -path "*/target/*" -not -path "*/build/*"`;
   - current branch: `git branch --show-current`; main branch:
     `git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null` (empty - `master` or
     `main`, the one that is in `git branch -a`).
3. **What counts as old.** You do not have the lists `G` and `L`. Get the list like this:
   - the human named old libraries or packages in the request -> use that list;
   - the human did not name them -> use the typical list of libraries that the framework replaces:
     `io.restassured`, `org.assertj`, `org.hamcrest`, `org.skyscreamer.jsonassert`,
     `net.javacrumbs.jsonunit`, `org.awaitility`, `org.sql2o`, `org.springframework.jdbc`,
     `com.github.tomakehurst.wiremock`. In the report, mark findings from the typical list as
     `предположительно старое`: the project can keep some of them on purpose.
4. **Which checks change:**
   - `P1` - use the list from item 3;
   - `P2`, `P3` - skip them. In the report write `не проверялось: нет карты, список legacy неизвестен`.
     Instead, run: `grep -rn "<artifactId библиотеки из п.3>" --include=pom.xml
     --include=*.gradle --include=*.kts --include=*.toml .`. If the dependency stays in the build,
     but the sources have no imports of its packages -> finding `P2`;
   - `P5` - there is nothing to compare with: check only disabled tests;
   - `P7` - find the Java version with this command:
     `grep -rnE "maven\.compiler\.(source|target|release)|<java\.version>|sourceCompatibility|targetCompatibility|languageVersion|jvmTarget" --include=pom.xml --include=*.gradle --include=*.kts --include=gradle.properties .`;
   - you do not know the technologies `keep`: think that everything was migrated. In the final
     summary write: «Если что-то оставлено на старой реализации намеренно - скажите, уберу эти
     находки».
5. **File list (Step 2):** the current branch is not the main branch -> `git diff --name-only`
   between the main branch and the current branch, as in Step 2. You are on the main branch or
   the diff is empty -> all sources: `find <каталоги исходников> \( -name "*.java" -o -name "*.kt" \)`.
   The round number is 1 (or the next number, if `MIGRATION-REVIEW.md` exists).
6. **If you need fix units (Step 6)**, first make a minimal map
   `.gigacode/data/migration/MIGRATION-MAP.md`, so that `migration-step` can do them.
   The template is in `references/fix-unit-template.md`, section «Минимальная карта». In the
   cards `fix`, write `-` in the field «Целевая картина».

All the other parts (Steps 3-7, checklist, report) are as usual.

## Step 2 - Collect the list of files to check

```
git diff --name-only <основная ветка из паспорта>...<ветка миграции из паспорта> -- '*.java' '*.kt' | while read f; do [ -f "$f" ] && echo "$f"; done
```

These are the files that the migration created or changed and that exist now. Write their
number in the report. If the command fails (no branch) -> take the files from the tables «Файлы юнита»
of the cards `core`, `usage`, `arch`, `review`, `fix` (action `создать` / `изменить`).

Round 2 and later: check only the files from the units `fix` and `arch` of the previous
round, plus all project checks of Step 3.

## Step 3 - Project checks with commands (P1-P16)

The source directories and the build files are in the passport. From the output, take the
numbers and the first 30 lines. Do not copy the full raw output into the report. Exclude the
directories `target/`, `build/`.

| № | What to check | How | Finding if |
|---|---------------|-----|------------|
| P1 | Old imports | For each line `G` with the decision «заменить»: `grep -rln "import <старый пакет>" --include=*.java --include=*.kt <src> \| grep -v "/target/\\|/build/"` | the list is not empty (except technologies `keep`) |
| P2 | Legacy is not removed | For each line `L`: class/file - `find . -name "<Имя>.java" -not -path "*/target/*"`; dependency/plugin - `grep -rn "<artifactId>" --include=pom.xml --include=*.gradle --include=*.kts --include=*.toml --include=gradle.properties .` | something is found |
| P3 | References to removed code | For each class from `L` and from «Чего НЕ будет» of blocks `T`: `grep -rln "\\b<Имя>\\b" --include=*.java --include=*.kt <src>` | the list is not empty |
| P4 | Compilation | the compile command from the passport | the project does not compile |
| P5 | Tests did not disappear | `grep -rE "^\\s*@Test\\b" --include=*.java --include=*.kt <src> \| wc -l` and compare with the sum of «Тестов» from `inventory/*.md`; `grep -rnE "@Disabled\|@Ignore\|enabled *= *false" --include=*.java --include=*.kt <src>` | there are fewer tests; disabled tests appeared |
| P6 | Framework configuration in `config` | `grep -rlE "class [A-Za-z0-9_]*(EnvironmentConfiguration\|ServiceConfiguration)" --include=*.java <src>` | the file is not in the directory `config` |
| P7 | Java version | the command from the passport (grep of the version in the build) | a version below 17 stays somewhere |
| P8 | Leftovers in the working tree | `git status --short` | there are uncommitted changes |
| P9 | Classes outside the architecture plan | `git diff --name-only --diff-filter=A <основная ветка>...<ветка миграции>` - for each new source file, find the class name in `ARCHITECTURE.md` (`grep -c "<ИмяКласса>"`). If there is no plan file, skip the check and write `плана нет` in the report | the new class is in neither section 3 nor section 5 of the plan; section 5 has more than 5 classes (the plan is not thought out - show the list to the human) |
| P10 | Old logging | three commands below the table | a configuration or a dependency of another logger (logback, log4j) stays; there is no file `simplelogger.properties` in the test resources; the build has no `slf4j-simple` or `slf4j-api` |
| P11 | Own configuration classes | two commands below the table | an own class stays that keeps or reads the connection settings of a migrated technology (not a framework configuration class); an old settings file stays, and its values were moved |
| P12 | The thread does not connect: a class is made, but not connected | two commands below the table | no code calls the new class; a call to a framework service repeats in files that are not step classes, but a step class for this action exists |
| P13 | Own constructs around checks | commands `MR-48` below the table, for all test sources | an own wrapper over a matcher, an own matcher or condition class, a list of matchers in a loop, parsing of the response into `JsonNode`, a number or a date checked as text, `assertAll` |
| P14 | Extra layers | commands `MR-49` below the table, for all test sources | a delegate method (facade), a nested class in a step class, a class «всё общее» (`...Common`, `...Helper`, `...Utils`) |
| P15 | Connection data is not moved | two commands below the table | in the framework settings files, a key has no value or has a placeholder (`TODO`, `changeme`, `<...>`), but the project has the value (in `CONNECTIONS.md` or in old files of the main branch) |
| P16 | Tests are not marked | commands from section 5 of `references/markup-rules.md`, for the test directory | the passport has `Разметка: нужна`, but a test class has no annotation from the agent set - not its own, and not through a base class (agent set - section 1 of the rules, values - the line «Разметка» of the passport). Test methods without `@TmsLink` and without a key in the name are not a finding: write one line `решить человеку` with their count. Keys - `java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/MarkupKeys.java missing <каталоги тестов>` and `... dup <каталоги тестов>` (section 5 of the rules): do not count the last line `итого:` of each command. A line `missing` with one key that is not in the output of `dup` is a finding (the agent had to add `@TmsLink`); a line `missing` with two keys or «значение не разобрать» - `решить человеку`. Each line of `dup` is one more line `решить человеку`, also if the key is not in the output of `missing`: `<ключ> - одинаковый в <Класс.метод>, <Класс.метод>`. An annotation with the value `-` in the passport is not required. `Разметка: не нужна`, `Разметка: не делается`, `scope: core` or mode «без карты» - skip this item |

Commands for `P10`:
```
find . \( -name "logback*.xml" -o -name "log4j*.xml" -o -name "log4j*.properties" \) -not -path "*/target/*" -not -path "*/build/*"
grep -rnE "logback|log4j|slf4j-(log4j12|reload4j)" --include=pom.xml --include=*.gradle --include=*.gradle.kts .
find . -name simplelogger.properties -not -path "*/target/*" -not -path "*/build/*"
grep -rnE "slf4j-(simple|api)" --include=pom.xml --include=*.gradle --include=*.gradle.kts --include=*.toml .
```

Commands for `P13` and `P14` are the commands `MR-48` and `MR-49` from the section «Быстрая самопроверка
grep-ом» (`code-rules.md` of the skill `migration-step`). Replace `<файлы юнита>` with
`-r --include=*.java <каталоги исходников тестов>`:
```
grep -rnE "implements [A-Za-z.]*(Matcher|Condition)\b|List<[A-Za-z.]*Matcher>|matchers\.add\(|\.toArray\(new [A-Za-z.]*Matcher|static [A-Za-z.<>]*(Matcher|Condition) [a-z][A-Za-z0-9]*\(" --include=*.java <каталоги исходников тестов>
grep -rnE "getRestHistory\(\)\.getLast\(\)|JacksonHelper|JsonNode|textOrNull|intOrNull|compareNumbers|assertDatesEqual|bigDecimalsEqual|equalToText\(String\.valueOf|assertAll\(" --include=*.java <каталоги исходников тестов>
grep -rnE "^\s+(public |private |protected )?(static )?(final )?class [A-Z]" --include=*.java <каталоги исходников тестов>
grep -rnE "^\s+return [A-Z][A-Za-z0-9]*\.[a-z][A-Za-z0-9]*\([a-zA-Z, ]*\);" --include=*.java <каталоги исходников тестов>
find <каталоги исходников тестов> \( -name "*Common.java" -o -name "*Helper.java" -o -name "*Utils.java" \) -not -path "*/target/*"
```
Write the number of lines per file in the report. In «Как исправить» write a reference to `MR-48` / `MR-49`.
Open each line with `return Класс.метод(...)` and check it. The parameters are the same as in the
method itself, and the method has nothing else -> it is a delegate, finding `P14`. Else it is not a
finding.

Commands for `P12`. Run the first command for each new source file that is not a test (the list from `P9`;
without the map - for each class in the step directory):
```
grep -rl "\b<ИмяКласса>\b" --include=*.java --include=*.kt <каталоги исходников> | grep -v "<ИмяКласса>.java" | wc -l
grep -rlE "<прямое обращение к сервису фрейма, из конспекта технологии>" --include=*.java --include=*.kt <каталоги исходников>
```
If the first command gives 0 -> finding `P12`: «класс <Имя> никто не вызывает». For the second command:
remove the step classes from the list (from section 3 of the plan; without a plan - the files of the step
directory of this technology). If files stay, and the project has a step class with this action -> finding
`P12` for each such file: «обращается к сервису фрейма сам, в обход <КлассШагов>». If there are no doc
notes, skip the second command and write this in the report.

Commands for `P15`. The first command finds empty values and placeholders in the settings files of the test resources:
```
grep -rnE "^[^#!]+=\s*$|TODO|changeme|CHANGE_?ME|<[a-zA-Z _-]+>" --include=*.properties <каталоги ресурсов тестов>
grep -rnE "TODO|changeme|CHANGE_?ME|<[a-zA-Z _-]+>|:\s*\"\"\s*$" --include=*.yml --include=*.yaml <каталоги ресурсов тестов>
```
For each found line, find the value: in `CONNECTIONS.md` (`grep -n "<слово ключа>"
.gigacode/data/migration/CONNECTIONS.md`); without the registry - in the old files of the main branch:
`git grep -niE "<слово ключа>" <основная ветка> -- '*.properties' '*.yml' '*.yaml' '*.java' | head -20`.
If the value is found -> finding `P15`, «Как исправить»: «записать в `<файл>` ключ `<ключ>` =
`<значение>` (откуда: `<файл: ключ>`)». If the value is not found anywhere -> it is not a finding, write a line in the report.
Commands for `P11` (remove from the output the framework configuration classes - `*EnvironmentConfiguration`,
`*ServiceConfiguration` - and the classes of technologies `keep`):
```
find <каталоги исходников> \( -name "*Config.java" -o -name "*Config*.java" -o -name "*Propert*.java" -o -name "*Settings.java" -o -name "Endpoints*.java" \) -not -path "*/target/*" -not -path "*/build/*"
grep -rlE "ConfigFactory\.create|new Properties\(\)|ResourceBundle\.getBundle|System\.(getProperty|getenv)\(" --include=*.java --include=*.kt <каталоги исходников>
```
Open the first 40 lines of each found file (`head -40`) and decide. If the file keeps or reads
connection settings -> finding `P11`. Else it is not a finding.

`simplelogger.properties` is the logging setting of a project on the framework. It must be in the
test resources of each module with tests. If the third command of `P10` found nothing, or the file
has no line `org.slf4j.simpleLogger.defaultLogLevel` -> finding `P10`, «Как исправить»:
«создать `<каталог ресурсов тестов>/simplelogger.properties`» with this content:
```
org.slf4j.simpleLogger.defaultLogLevel=INFO
org.slf4j.simpleLogger.showShortLogName=true
org.slf4j.simpleLogger.showDateTime=true
org.slf4j.simpleLogger.dateTimeFormat=HH:mm:ss:SSS
org.slf4j.simpleLogger.logFile=System.out

#org.slf4j.simpleLogger.log.ru.sber.at=INFO
```
If the fourth command did not find `slf4j-simple` or `slf4j-api` -> finding `P10`, «Как
исправить»: «добавить в сборку зависимости `org.slf4j:slf4j-simple` и `org.slf4j:slf4j-api`
с одной версией `${log.version}` (свойство `log.version`, 2.0.16)».
Do this check also in mode «без карты».

Fast counters for the code rules (only for the files from Step 2). You need them later to compare
with the findings of the subagents:

```
grep -cE "(^|[^A-Za-z0-9_])var +[A-Za-z_][A-Za-z0-9_]* *(=|:)" <файл>
grep -cE "Assertions\.|assert(Equals|True|False|NotNull|Null|That|All)\(|SoftAssertions" <файл>
grep -cE "\.as\([A-Z][A-Za-z0-9_]*\.class\)|readValue\(|fromJson\(" <файл>
grep -c "getForCurrentThread()" <файл>
grep -cE "Thread\.sleep|TODO|FIXME" <файл>
grep -cE "\b(log|logger|LOG|LOGGER)\.(info|debug|trace|warn|error)\(|System\.(out|err)\.print|\.log\(\)\.(all|body|headers|ifValidationFails)|(Request|Response)LoggingFilter|\.prettyPrint\(|\.prettyPeek\(|\.peek\(" <файл>   # ручное логирование (V21)
grep -cE "ConfigFactory\.create|new Properties\(\)|getResourceAsStream\(|ResourceBundle\.getBundle|System\.(getProperty|getenv)\(|@Value\(|PropertiesLoader|ConfigReader|PropertyReader" <файл>   # своё чтение настроек (V24)
# только для файлов с @Test: вспомогательные методы в тест-классе (должно быть 0)
grep -cE "^\s*(private|protected|static) .*\(.*\)\s*(throws [A-Za-z, ]+)?\{" <тест-класс>
# обращения к фрейму в тест-классе: само по себе не находка (в теле теста разово - можно); находка, если счётчик вспомогательных методов не ноль или одно действие повторяется в нескольких тестах
grep -cE "getForCurrentThread\(\)|restClient\(\)|dataBaseClient\(|executeSelect\(|consumerClient\(|producerClient\(" <тест-класс>
```

In the report, write the table «файл - счётчики» only for the files where at least one counter is not zero.

## Step 4 - Code review with subagents

Read `references/review-subagent.md`.

1. Divide the files from Step 2 into groups of max 8 files (by packages, so that related classes
   are together).
2. Start the review subagents in waves: max 3 at the same time. Copy the prompt word for word.
3. Write the findings table of each subagent to the report IMMEDIATELY. Mark the group as
   checked in the section «Проверенные группы».
4. **Stop by size.** In one chat, check max 6 groups (48 files). If there are more files -> stop
   after the sixth group, set `состояние: проверка не закончена` in the report, and say:
   «Откройте новый чат и напишите: `/orchestrator Продолжи проверку миграции`». In the new chat, continue from the
   first group that is not checked. Do not do Step 3 again.
5. The review subagents are mandatory. Only if the subagent call returned an error (not «долго» and not «проще самому») -> show the error in the chat and write `сабагент не запустился: <ошибка>` in the report.
   Then do the checklist `V1`..`V26` yourself, one file at a time, max 10 files per chat.

Comparison. The matching rules are `V1`, `V4`, `V19`, `V6`, `V9`/`V18`, `V21`, `V20`. A Step 3
counter for a file is not zero, but the subagent found nothing in this file for the matching rule
-> add the finding yourself, from the grep line.

## Step 5 - Verdict

Count the findings and write a summary in the report: for each item `P` and `V`, the number of findings.

- no findings (no `P` and no `V`) -> verdict `clean`;
- there are findings -> verdict `findings`.

Do not make the result look better: «мелочь» and «и так сойдёт» are also findings if an item of
the checklist is broken.

## Step 6 - Add fix units

Do this step only for the verdict `findings`. Read `references/fix-unit-template.md`.

1. Group the findings into units. The complex logic is already migrated, so the fix units are of
   medium size - larger than the migration units:
   - findings `просто` and findings `P1`, `P2`, `P3`, `P6`, `P7`, `P10`, `P11`, `P15`, `P16` -> units of type `fix`: max 10 files
     and max 30 findings per unit. Group them by technology, and in each technology by package;
   - each finding `крупно` (divide a class, remove a layer, move code between classes) -> a
     separate unit of type `arch`. Use the limit for `arch` (max 6 files);
   - `P9` (a class outside the architecture plan) -> if the class does the same as a class from the plan,
     add a unit `arch` «перенести код в <класс из плана> и удалить лишний». If the class is necessary and
     repeats nothing, it is not a unit: add the class to section 5 of `ARCHITECTURE.md`;
   - `P13` (own constructs around checks) -> units of type `fix`, max 3 files per unit:
     «переписать проверки в <файлы> готовыми matchers фрейма по `references/matchers.md`,
     «Как писать проверку»; удалить обёртки, свои классы matcher, списки matchers, разбор
     в `JsonNode`». Remove the wrappers and the own classes in the unit where the last call
     disappears;
   - `P14` (extra layers) -> units of type `arch`: «убрать делегаты <класс>: вызывающих
     перевести на настоящий метод, делегат удалить»; «вынести вложенный класс»;
     «разнести класс <...Common> по слоям плана». The calling files go into the same unit;
   - `P12` (the thread does not connect) -> units of type `fix`, max 3 files per unit: «заменить в <файл>
     свои обращения к сервису фрейма на вызовы `<КлассШагов>.<метод>`, свой код запроса
     убрать». If no code calls the class and no code can move to it -> a unit `fix` «удалить
     класс <Имя>»;
   - **rewrite instead of patching.** The code of one technology (or one package) can have 3
     or more findings `V8`, `V25`, `V26`, `P13`, `P14` together. Then this code is built with «своей
     архитектурой» (wrappers over wrappers, nested classes, delegates, twin methods, own
     constructs around checks). Do not fix such code line by line: remove it and write it again
     by the layers `MR-49`. Do not add separate units for these findings. Add units of type `arch`
     for the technology, with the mark «переделка» in the name:
     1. «создать»: the base layer of the technology and the step classes from `ARCHITECTURE.md`; the methods
        by name - the actions that the callers do now;
     2. «перевести»: move each file that calls the classes to remove to the classes from item 1
        (max 6 files per unit; several units - in batches);
     3. «удалить»: each class to remove, by name (delegates, facades, `...Common`, classes with
        nested classes, own matchers) - as the last unit;
     4. checkpoints: `grep -rn "<имена удалённых классов>" <src>` is empty; the checks `MR-48` and
        `MR-49` from the self-check are empty; the number of tests did not decrease.
     In mode «без карты» there is no plan -> before these units, make
     `.gigacode/data/migration/ARCHITECTURE.md` from `references/architecture-template.md`
     only for this technology (sections 1 and 3). Else the executor has nothing to build from;
   - `P4` (does not compile) -> the first unit `fix`, only one; the other units depend on it;
   - `P5` (tests disappeared or are disabled) and `P8` -> not a unit, but a question to the human in section 6 of the map.
2. Numbers: use the next free `M-<nnn>` after the last unit of the map.
3. For each unit, write a card `.gigacode/data/migration/units/M-<nnn>.md` from the template. Add a line
   at the end of the table in section 4 of the map (phase `6`, status `todo`). Put the units `arch` after all
   units `fix` of this round.
4. As the last unit of the round, add one unit of type `review` for the files of all `arch` units of this
   round. If there are no `arch` units, do not add it.

## Step 7 - Write the result and stop

1. In the map header, write: `review_round: <номер круга>`, `review_status: clean | findings`,
   `updated`. Add a line to «7. Журнал сессий».
2. Show to the human:
   - the verdict and the round number;
   - the summary: the number of findings for each item, and the 5 most frequent items;
   - the number of fix units that you added (`fix` / `arch`) and their numbers;
   - the questions to the human, if there are any;
   - the path to the report.
3. Next steps:
   - `findings` -> «Откройте новый чат и напишите: `/orchestrator Продолжи миграцию`» (the orchestrator will
     do the fix units, then it will start the check again). Small `fix` units can run in a batch:
     «сделай с M-<a> по M-<b>»;
   - `clean` -> «Миграция проверена, замечаний нет». Do not delete the service folder
     `.gigacode/data/migration/` yourself - the human decides this (the orchestrator will ask);
   - round 3 and the verdict is still `findings` -> say it directly: three rounds did not give a
     clean result. List the items that repeat from round to round. Recommend that the human looks at them.

## If you lose track («Если потерял нить»)

(1) Read this SKILL.md again. (2) Open `MIGRATION-REVIEW.md`: the sections of the last round
show which steps are done and which file groups are checked. (3) Continue from the first
section that is not filled. The report is the source of truth, not the chat.
