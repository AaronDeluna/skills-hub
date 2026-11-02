# Stage 5 - Divide the work into units (section 4 of the map + unit cards)

This file is part of the skill `migration-map`. The common rules are in `references/core-rules.md`. The migration map rules and the order of stages are in `SKILL.md`.

**Ask all questions now, not during the work («Все вопросы - сейчас»).** After the human approves the
migration map, the executor does not ask questions. The human can start a batch of units and go away.
Thus, before you write the unit cards, examine each `migrate` technology. Close each open decision
now: decide it yourself (from the project and the documentation), or write a question in section 6:
1. In the block `T`, the fields «Данные подключения» and «Как проект пользуется технологией сейчас»
   are filled. In `CONNECTIONS.md`, the table «Перенос в фрейм» of the technology is filled: each
   key has a value or a record in «Чего фрейму не хватает». Each action from «Что вызывается и кем»
   is in the doc notes (the framework can do it);
2. the inventory of this technology has TYPES of checks (field equals, number, date, null,
   size, DB cell, array against table). For each TYPE, the doc notes have a matcher. Or the decision «стандартный ассерт» / «цикл с `.shouldSoft` по элементам» is written;
3. each method that parses the response into a DTO is in a substep `usage` with the step «метод возвращает валидируемый объект, DTO <имя> удалить, вызывающие <файлы> перевести на `.should(...)`»
   (`MR-41`);
4. the command of the representative test and the fast test are selected. If the tests cannot
   run locally, the map passport says so (the executor closes the substeps by compilation);
5. write the questions that remain after this in section 6 now, as one list.

**Gate before Stage 5: first the answers, then the units.** Do not make units while section 6
of the migration map has a question with `ответ: -`. If you make them, you must write the unit
cards again after the answers.
1. Read section 6 again. Do the «Фильтр вопросов» again for each question without an answer.
   If a question does not pass the filter -> decide it yourself as the filter tells, and remove it from section 6.
2. If no questions without an answer remain -> continue and make the units.
3. If questions remain -> **STOP. Do not make units.** Keep `map_stage` at `5`. Do not mark the stage.
   Show these questions to the human as a list, each question with answer options. Politely say:
   «Чтобы продолжить, нужны ваши ответы на вопросы ниже. После этого разобью работу на юниты».
   If the human answers in this chat -> write the answers in section 6. Correct the rows `G`, `L`, `T`
   and the technologies table from the answers. Go back to item 1. If the human does not
   answer, this chat ends.


A unit is a complete piece of work. Keep the number of units small. With small units, the
executor writes more records than it does work. Between units, the executor loses the context.

- **A `migrate` technology is ONE unit of type `tech`.** All REST work is one unit. All DB work is
  another unit. Inside the unit, the work is divided into **substeps** `S-<nn>`: analysis -> `env` ->
  `core` -> `usage` -> `cleanup` -> `review`. The executor does the substeps strictly in this order, all of them one after another in one chat.
  If the chat stops, the unit stays `in-progress`. The next chat continues from the first
  substep that is not done.
- The other units are small, one chat each: `env` of phase 1 (Java 17, dependencies), `arch`
  (phase 3), `cleanup` of phase 4.

A substep is a piece of work after which the project compiles.

**How to read this stage.** In phase 2, `env`, `core`, `usage`, `cleanup`, `review` are TYPES OF
SUBSTEPS inside the unit `tech`. Phase 2 has no separate units of these types. Below, where the text
about a technology says «файлы юнита», read «файлы подшага».

**Size (strict):**

| Unit type or substep type | Limit |
|-----------|-------|
| `env`, `core`, `arch` | max 6 changed files AND max 1000 source lines in total |
| `review` | max 15 files (subagents read them, not the executor); if there are more files - some `review` substeps one after another |
| `usage` | max 3 files AND max 600 lines in total - here the code is written again, not corrected, thus the substep is smaller |
| `cleanup` | its own limit - see below (do not read the files to remove) |

If you are not sure that a substep fits, divide it. A technology unit can have any number of
substeps: 30 small substeps are better than 8 large substeps. A file longer than 600 lines is a separate
substep. If it does not fit, divide it (by package, by subpackage, by alphabetical order of classes). But a
technology has exactly one unit: do not divide a technology into some units.

**Layers.** Each file with old code belongs to one of two layers. Find the layer as follows:

| File attribute | Layer |
|---------------|------|
| It imports a package of the old technology (from the matrix `G`) and it has NO `@Test` - clients, base classes, helpers, utilities, wrappers, own asserts, configuration | old core |
| It has `@Test`; OR it does not import the old technology itself, but it calls classes of the old core (steps, scenarios, tests) | top level |

**What happens to each layer (the mode `core_mode` in the card of the substep `core`).** Select the
mode from `scope` in the map header. There is one mode for the whole map:

| `scope` | `core_mode` | Old core | Top level |
|---------|-------------|-------------|-----------------|
| `full` (usual migration) | `new` | **NOT translated and NOT corrected.** It stays as it is until the tests stop using it. It is removed in `cleanup`. | The `usage` substeps write the steps and tests again by the target picture `T-<tech>`: directly on the framework mechanisms, and the checks on matchers. They do not refer to the old core any more. |
| `core` (only the core, do not touch the tests) | `in-place` | The internals of the core classes are replaced with calls to the framework. The public methods (names, parameters, return types) are kept. | Not touched. It continues to call the core. |

What the substep `core` does in the mode `new`: it makes **a new foundation of the technology by the
target picture**. This is what must exist BEFORE the first test is written again:
- configuration classes and settings of the framework service;
- **step classes of the technology** (the step layer from `T-<tech>`: action methods that call the
  framework and return a validatable object);
- it moves the project data (endpoints, DTOs of request bodies, queries) to their place by `T-<tech>`.
It makes new files and does NOT touch the old core. If, by the
documentation, the technology needs nothing except the configuration from the substep `env`, and
the step classes already exist -
the technology has no `core` substeps; write this. If the step class is large -> make some `core` substeps, one
group of actions per substep. Each next substep adds methods to the same class.

Do not write these steps in the mode `new` (check each card): a step such as «перевести `RestHelper` на PVATF», «заменить в `BaseApiTest` RestAssured на клиент фрейма», «создать класс-обёртку над сервисом фрейма с прежними методами». Old intermediate classes appear only in `cleanup`.

**Phases and order (from top to bottom; the executor does them in this order). Do not change the order.**

Make units only for technologies with the decision `migrate`. The `keep` technologies are not in
phases 1-2 and 4 (map rule 4).

| Phase | Unit type | What it contains |
|------|-----------|------------------|
| 1    | `env`     | **Java 17 - the very first unit (`M-001`), if the passport has a version lower than 17.** Technology `common`. It changes the Java version to 17 in ALL build locations from the passport (compiler properties, `maven-compiler-plugin`, `sourceCompatibility`/`targetCompatibility`, toolchain, `jvmTarget`). It repairs what does not compile after this change. This unit does nothing else: no framework dependencies, no code for the framework. If the version is already 17+, there is no such unit. Do not change the CI files (Jenkinsfile, `.gitlab-ci.yml`) that set the JDK: write a question to the human. |
| 1    | `env`     | **Dependencies.** Connect PVATF and its modules for EACH `migrate` technology. Add dependencies and plugins strictly by the documentation. Take the versions of the framework and perfeccionista from the passport row «Версии фрейма» (`get_pvat_release_notes`). In the unit card, write the versions explicitly. ONE unit for all technologies together (if there are more than 6 build locations - some units, by modules). Do not touch the old dependencies here. |
| 2    | `tech`    | **Technologies one by one, each one TO THE END - one unit `tech` per technology.** Go by the column «Порядок» from the passport: first `common` (the base environment of the framework), then `rest`, then `db`, and so on. Inside the unit, the substeps are in this order: (1) `разбор` - who calls the technology and how; (2) `env` - its configuration and environment; (3) `core` - its new foundation: the step classes; (4) `usage` - the consumers change to the step classes, and the checks change to matchers: first the steps and intermediate classes, then the tests; (5) `cleanup` - remove its legacy from the table `L`; (6) `review` - subagents review the code of THIS technology, and the executor corrects the findings. The unit of the next technology depends on the unit of the previous technology. |
| 3    | `arch`    | **Architecture.** Problems `A-<n>` with the term `после` - small units, one problem (or a part of it) per unit. This phase also contains the architecture corrections of the code of `keep` technologies. |
| 4    | `cleanup` | **Final cleanup.** Common legacy that is not related to one technology (common old dependencies, empty packages). |
| 5    | `markup`  | **Test markup** with allure-annotations - the last unit, when the code is already on the framework. Only if the passport has `Разметка: нужна`. One unit; if more than 15 test classes need annotations - some units, by packages. For details, see «Юнит разметки» below. |

What each substep type does inside the technology unit (mode `new`, usual migration):
- `core`: makes the new foundation of the technology by `T-<tech>` (see above). It does not touch
  the old core.
- `usage`: writes the steps and tests again by `T-<tech>`. The steps call the framework through the base layer
  of the technology (`MR-49`), not through the old core. The tests call the steps and stay clean: a test class has only the scenario,
  with no helper (private) methods with requests, SQL, file reading and mapping
  (`MR-42`). A test can
  need an action that the step classes do not have yet. Then add the file of the step class to this substep
  (action `изменить`) with the step «добавить метод <имя> в <КлассШагов>». **Go from bottom to top, level by level:** level 1 - classes that
  call the old core themselves (usually steps); level 2 - classes that call level 1;
  and so on up to the tests. In the substeps table, the substeps of level N+1 are after ALL substeps of level N. While the executor writes the lower level again, it keeps its public methods, thus
  the upper levels compile. Find the level with the command: `grep -rl "<ИмяКласса нижнего
  уровня>" --include=*.java --include=*.kt <src>`. Write the level in the substep name
  («rest, уровень 1: шаги заказа»). `usage` also does this: it replaces the old asserts and custom checks with the framework matchers
  (map rule 5). The meaning of the test does not change: the same actions, the same data, the same checks.
  An intermediate step class that only passed calls to the old core, and became an empty
  intermediate layer after the rewrite, is not kept: it goes to `L`.
- `cleanup`: removes all legacy of the technology - the old core, wrappers, own asserts, old
  dependencies and configs. After it, nothing of the old implementation stays.
- `review`: is made ALWAYS, as the last substep in the technology unit. Subagents check the code of the technology by
  the rules `MR` (for example: `var`, full names instead of imports, remaining asserts, intermediate layers, logic
  in test classes, long methods, duplicates). The executor corrects the findings. Why now and not
  at the end: the next technology is written by the pattern of the previous one. Find an error before
  it repeats. Its files are all files that the substeps `core` and
  `usage` of this unit made or changed and did not remove. The framework configuration classes (`common`) go into the
  `review` of the first technology after `common`. The check of the whole project at the end is not
  a unit of the map: the skill `migration-review` does it when all units are `done`.

**Technology thread («создал - подключи»: you made it - connect it).** A technology unit is one chain.
Each substep continues the previous substep. First find who calls the technology and how.
Then make step classes for these calls. Then change EACH caller to these classes.
Then remove the old code. Then check.

**A consumer of the technology** is a file that calls the technology ITSELF, in one of three ways:
- with the old library;
- with a class of the old core;
- **with a framework service directly, past the step layer** (the project is already partly on the
  framework: the call of the framework service and the request construction are directly in the test,
  or they repeat in different step classes).
The old imports do not find the third way. Find it separately, by the names of the framework
service calls from the doc notes of the technology:
```
grep -rlE "<старые пакеты технологии>|<классы старого ядра>" --include=*.java --include=*.kt <src>
grep -rlE "<обращение к сервису фрейма из D-<tech>-n>" --include=*.java --include=*.kt <src>
```
From the second list, remove the step classes from the plan. The other files are consumers: the same
logic repeats in them, and its place is the step class. Write both commands and the list of consumers with their
actions in the section «Разбор технологии» of the card.

Thread rules (check them for each `migrate` technology before you write the card):
1. **Do not make a class in advance.** The substep `core` makes a step class only if the class
   has consumers. The class methods are the actions that the consumers now do themselves.
   If there are no consumers -> there is no class in the plan and no class in the card.
2. **Connect each new class in the same card.** After the substep `core`
   that makes the class, put the `usage` substeps. They change the consumers to this class. Each has the step:
   «заменить в <файл> обращения <какие> на вызовы `<КлассШагов>.<метод>`; свой код запроса из файла убрать».
3. **Each consumer is in exactly one substep `usage`** (a file for some technologies - in
   the unit of the last of them). If there are 40 consumers -> there are many `usage` substeps; this is normal.
   Do not skip consumers.
4. **The unit ends with checkpoints** that prove that the thread is complete: there is no old code,
   only the step classes call the framework, and something calls each new class.

Mode `in-place` (`scope: core`): there are no new step classes; rules 1-3 do not apply.

**Files for some technologies are deferred («Файлы на несколько технологий»).** A top-level file uses a
technology in one of these cases: it imports its old package, it calls a class of its old core, or it calls
another deferred file. Some files use TWO or more `migrate` technologies (the test
calls both REST and DB). Do NOT divide such a file into parts, and do not correct it two times:
- the whole file goes into the unit of the LAST of its technologies by the column «Порядок» (REST + DB ->
  unit `db`). In the earlier units, no substep contains it;
- in that unit, the executor writes it again in one pass for all its technologies: the new foundation of the earlier
  technologies already exists at this time. In such a substep `usage`, in «Что сделать», name the
  `T` blocks of all technologies of the file. In the substep name, write «(rest + db)»;
- do not count the `keep` technologies here;
- **remove the old items that deferred files need together with these files.** A deferred file can use
  a class of the old core, a dependency or a config of an earlier technology. Do not remove such an item in the `cleanup` of the earlier technology.
  In the column «Технология» of the `L` row of such an item, write
  the label of the technology where the executor migrates the LAST file that uses the item. The item is removed in the `cleanup`
  of that unit. All other old items are removed in their own unit. The check command:
  `grep -rl "<ИмяСтарогоКласса или старый пакет>" --include=*.java --include=*.kt <src>` -
  if the output has a deferred file -> the `L` row moves;
- as a result, after the last technology unit, no old code stays anywhere: to defer does not mean
  to keep.
While an earlier unit is in progress, the deferred files compile on the old code, as before.

In the mode `in-place` (`scope: core`): the `core` substeps replace the internals of the old core
and keep the public methods. The `usage` and `cleanup` substeps are in the map, but they wait for the change to `full`.
When the human changes to `full`, the `usage` substeps still write the tests again by
`T-<tech>` directly on the framework. Then `cleanup` removes the shells of the old core.

Order rules:
- The rows of the units table are EXACTLY in the order of execution: all of phase 1, then technology by
  technology (one unit `tech` per technology; inside it the substeps `разбор` -> `env` -> `core`
  -> `usage` -> `cleanup` -> `review`), then phase 3, then phase 4, then phase 5.
- The unit «Java 17» (if it exists) is the first in the table. All other units of phase 1 depend on
  it: the framework does not connect to a project on old Java.
- The column «Зависит от»: the unit `tech` of the technology `common` depends on the dependencies unit of
  phase 1. The unit `tech` of each next technology depends on the unit `tech` of the previous technology. The table «Подшаги» of the card
  sets the order of substeps inside the unit. Substeps have no dependencies.
- Substep `review`: the files are all files that the substeps `core` and `usage` of this
  unit made or changed and did not remove. The target picture is the block `T-<tech>`. The representative test is the fast test
  of this technology. The review checks only this technology, not the whole project.
- Architecture is AFTER the migration, not before. First change everything to PVATF, then correct
  the project structure.
- **Only for the mode `in-place`: if you cannot keep a public method of the core** (its parameters or return type
  contain a type of the old technology): put this core class in one substep TOGETHER with the files
  that call it (substep type `core`; in the card write: «сигнатура меняется,
  вызывающие файлы включены»). If the callers do not fit in the substep limit, do not decide yourself:
  write a question to the human in section 6.

**Remove legacy immediately, not «когда-нибудь потом».** When a technology is migrated, its `cleanup`
is the next substep in the same unit. Why so strict: each next chat starts with empty memory
and a limited context. Old code that stays in the project gets into search and reading.
It uses the context and shows the executor the old way instead of the framework. After the `cleanup`
of a technology, NOTHING of its old implementation must stay in the project: no classes, no
dependencies, no versions in the build, no configs.

**The cleanup of a technology is some small `cleanup` substeps, not one large substep.** Divide it
as follows:

| substep `cleanup` | What it removes | Limit |
|----------------|-------------|-------|
| «код» (code) | classes and packages from the table `L`: old core, wrappers, helpers, own asserts | max 15 files to remove per substep; if more - some substeps (by package) |
| «сборка» (build) | dependencies, plugins, versions, exclusions from ALL build locations (`L` rows of the type «зависимость»/«плагин») | one substep; it comes AFTER the «код» substeps |
| configs and resources | old properties, yml, templates, test resources | one substep; if there are less than 5 `L` rows of this type - join it with the substep «сборка» |

The order inside the cleanup: code -> build -> configs. Do not remove a dependency before you
remove the last class that imports it. EACH substep `cleanup` has these done
criteria: the project compiles, the representative test is green, grep for the old packages and
names from its `L` rows in the whole project is empty.

**Migration scope (`scope` in the map header).** ALWAYS make units and cards for the whole migration,
for all phases, for any scope. The scope only tells which of them to do now:

| `scope` | When | What is done |
|---------|-------|-----------------|
| `full`  | by default; «мигрируй проект» | all phases |
| `core`  | the human asks to change only the core and not to touch the tests | the units `env` of phase 1, and in the units `tech` only the substeps `разбор`, `env` and `core`. The substeps `usage`, `cleanup`, `review` and the units `arch` stay `todo` and wait. |

**Markup unit («Юнит разметки», `markup`, phase 5).** Make it only if the passport has `Разметка: нужна`.
It depends on the last unit of phase 4 (if there is no phase 4 - on the last unit before it). Write the card
by `references/unit-card-template.md`, `tech: common`, `phase: 5`:
- «Файлы юнита»: the base test class from `ARCHITECTURE.md`; the test classes that need their own
  layer annotation (`references/markup-rules.md`, sections 2-3); the test classes without a base
  class that do not have one or more annotations of the set (put the common annotations on these classes
  themselves: section 2, item 1 of the rules); plus the build files if the dependency
  `allure-annotations` is not present, the passport has `версия: поднять` (the file where the version number is written;
  if the project does not write it - the build file of the test module) or `версия: не определена` (the build
  files of the test modules: the agent makes the tree before the changes and decides itself). The action is
  `изменить`. Take the test classes from the plan, not from
  the old code: at phase 5 the old classes do not exist. Do not list in advance the test classes that need only
  `@TmsLink` by the key from `@DisplayName`: the final re-check of the agent finds and marks them
  in all test directories (section 6 of the markup rules);
- «Что сделать»: one item per file: which annotations and with which values from the passport row
  «Разметка». The common annotations (`@System`, `@Team`, `@TestStage`, common `@Regress` and
  `@Story`) go only on the base class, not on its subclasses. The final re-check puts `@TmsLink` by the keys from
  `@DisplayName` (the last item). If `версия: поднять`, the first item is `поднять
  allure-annotations <версия> -> 2.0.2` in the build file. If the value is `-`, do not put this
  annotation; write this in the card;
- «Показательный тест» - `-`: compilation and grep check the markup;
- «Что сделать» - the last item is always `перепроверка: раздел 6 правил разметки -
  ключи тест-кейсов без @TmsLink, набор агента, импорты, @DisplayName не изменён`;
- «Критерии готовности»: the final re-check (section 6 of the rules) is clean; the project compiles; the check commands from section 5 of the rules
  find the markup in each test class (directly or through the base class).

**Units make only what is in the architecture plan.** Each file with the action
`создать` in a card is a class from section 3 of `ARCHITECTURE.md`. After you write a card -> write the number
of the unit and substep (`M-003 S-03`) in the plan. Use the column «Юнит» of the class row. If you need a class that is not in the plan ->
first add it to the plan by the 10 rules of the template. Then add it to the card.

For each unit:
1. A row in the table of section 4 of the map: `M-<nnn>`, phase, type, technology, name, depends
   on, number of files, status `todo`.
2. **Subagents make the card of a `tech` unit, from files, not from memory.** Read
   `references/card-subagents.md` and follow it for each technology: technology analysis
   (5.1) -> card writer (5.2) -> `scripts/Card.java` (5.3) -> card checker
   (5.4) -> correction (5.5). Do not write the `tech` card yourself: you prepare the input data for the
   subagents and accept the result.
   The other units (`env` of phase 1, `arch`, `cleanup` of phase 4) are small. Write them yourself STRICTLY
   by `references/unit-card-template.md` and check them with the same script
   (`java -Dfile.encoding=UTF-8 .gigacode/skills/migration-map/scripts/Card.java M-<nnn>`). The card contains: the exact list of files;
   the steps «что сделать» with references to `G-<n>`/`A-<n>`/`L-<n>`; the doc basis `D-<tech>-<n>`;
   the done criteria; the numbers of the code rules («Правила подшага» / «Правила юнита» - by the table
   in `references/tech-unit-template.md`, rule 16).
3. **The representative test** is a mandatory field of the card (in a `tech` unit - a field of each
   substep, plus one test of the technology in the checkpoint `C7`). It is ONE fast test that
   proves that the unit is migrated successfully. Run tests only where the logic changed:

   | Unit type | How to check it |
   |-----------|-----------------|
   | `env` (Java 17, dependencies, configuration, environment) | ONLY compilation. Do not run tests: in the test field, write `-` and the reason `env - проверяется компиляцией` |
   | `core` in the mode `new` | only compilation (`-`, the reason is below) |
   | `core` in the mode `in-place`, `usage`, `cleanup`, `arch`, `review` | compilation + one fast representative test |

   **The test must be fast.** Some tests take 40 minutes - do not use them as representative tests.
   Select as follows:
   - if there are reports of previous runs (`find . -path "*surefire-reports*" -name "*.xml" -o -path
     "*test-results*" -name "*.xml" | head`) -> take the time from the attribute `time` and select from
     the tests faster than 60 seconds; write the time in the card;
   - if there are no reports -> select by the code. The test and what it calls must have no waits and
     polls (`sleep`, `await`, `Awaitility`, `waitFor`, `poll`, `timeout` in minutes). They must have no
     UI and no browser, no container start, few steps (max 5 actions), one request -
     one check. In the card, write `время неизвестно, выбран по коду`;
   - do not take tests with tags and names `slow`, `long`, `e2e`, `load`, `performance`,
     `regress`, `smoke-full`;
   - from the suitable fast tests, take the test that goes through the most migrated places.
   If there is no fast test for the migrated places -> write `-` and the reason `быстрого теста нет`.
   Do NOT make the card of this unit: add a question to the human in section 6 (which test to
   run). After you make the other units, stop by the same gate rule.
   The card is completed after the answer.

   Which test is correct by its meaning:
   - substep `core` in the mode `in-place`: an EXISTING test that calls the core classes from
     this unit and goes through the most of their methods. The test does not change:
     it proves that the core on PVATF works as before;
   - substep `core` in the mode `new`: nothing calls the new foundation yet - write `-` and
     the reason `новое основание, тестов на нём пока нет`. The unit closes by compilation, and
     the first substep `usage` of the technology proves it;
   - substep `usage`: a test from the unit files (or a test that calls the migrated classes)
     that goes through the most migrated places; if they are equal - the shortest test;
   - substep `cleanup`: a test of this technology that is already on PVATF. It must stay
     green after the legacy is removed;
   - `arch` unit: a test that uses the restructured classes;
   - substep `env`: no test, `-` (see the table above).
   Write the full path to the class, the method name and the expected time. Write the exact command that runs ONLY this ONE
   method (not the class and not the whole module).

Check the coverage and write the result of the check in section 0 of the map. First run the script. It
checks all mechanical items in all cards at once (fields, limits, empty words, consumers,
`L`, doc notes records, «создал - подключи»):
```
java -Dfile.encoding=UTF-8 .gigacode/skills/migration-map/scripts/Card.java all
```
`находок 0` -> go through the list below. Check only the items that the script does not see (phase order,
dependencies, coverage of `G` and `A`, deferred files, representative tests):
- section 6 has no questions without an answer, except the questions about the representative test;
- for each technology, the 5 items of «Все вопросы - сейчас» are done: the executor must not
  stop at an open decision that the map stage can close;
- each row `G-<n>` (except `уже PVATF` and `НЕТ В ДОКЕ`) is covered by at least one unit;
- each `A-<n>` with a basis is covered by a unit;
- each `L-<n>` is covered by a substep `cleanup`, and each `migrate` technology has the full cleanup:
  code, build, configs (if there are no `L` rows of a type - write this);
- for each old library of the technology, there are `L` rows for ALL build locations where it
  is mentioned (module, parent, versions, version catalog);
- these items have a fast representative test (or `-` with a reason and a question to the human): each substep `usage`, `cleanup`,
  each substep `core` of the mode `in-place` and each `arch` unit. The substeps `env` have
  no test;
- each source file with old imports is in a substep: a top-level file - in
  `usage`; an old-core file - in `cleanup` (mode `new`) or in `core` (mode `in-place`);
- each `migrate` technology has a block `T-<tech>`, and the field «Целевая картина»
  of the card of its `tech` unit names it;
- mode `new`: no substep `core`/`usage` has a step that changes or
  reproduces a class from the list «Чего НЕ будет» of the block `T`;
- a unit of phase 1 connects the dependencies of each `migrate` technology;
- if the passport has a Java version lower than 17 -> the first unit of the table is «Java 17». The other units of phase 1
  depend on it;
- the `tech` units are in the units table in the order of technologies from the passport;
- no `keep` technology has a `tech` unit;
- each substep `usage` whose files have checks has the step «заменить проверки на matchers фрейма» with a reference to the doc notes record about matchers;
- for each `migrate` technology, the block `T` has «Слой шагов» filled. For each step
  class that is not in the project yet, there is a substep `core` that makes it;
- no card has a step that adds to a test class a helper method with
  request, SQL or mapping logic;
- the unit of each `migrate` technology ends with a substep `review`. Each file from its
  `core`/`usage` substeps (except removed files) is in the substep `review` of the same unit;
- each file for some technologies is in exactly one unit - of the last of its
  technologies; no `L` row is removed before the last file that uses it is migrated;
- exactly one substep makes each new class from section 3 of `ARCHITECTURE.md` (the column
  «Юнит» is filled). No card makes a file that is not in the plan;
- in the card of each `migrate` technology, the table «Данные подключения» repeats its table
  «Перенос в фрейм» from `CONNECTIONS.md`. «Итоговый результат» of the substep `env` lists
  the framework files and the keys with the values from that table. There are no empty values, no `TODO`, no `<...>`;
- each substep of the `tech` cards (except `разбор` and `review`) has «Правила подшага» filled;
  each card of the other types has «Правила юнита» filled. The numbers are strictly by `references/substep-rules.md`
  (the type row plus the additions) - `Card.java` checks this;
- the substep `env` of `common` in phase 2 has a step about `simplelogger.properties` and the dependencies
  `slf4j-simple` + `slf4j-api` with the version `${log.version}`. For each old
  logger configuration and dependency, there is an `L` row covered by a `cleanup` unit of phase 4;
- step style `flow`: the doc notes have the records `D-common-7` and `D-common-8`; each test with steps in
  a substep `usage` has the step «записать тест цепочкой FlowRunner»; an earlier substep `core`
  makes the flow class for it;
- the unit of the technology `common` makes the base test class with the framework annotations (or removes the old items from it).
  Each substep `usage` with test classes has the step «унаследовать тест-класс от базового, аннотации фрейма с тест-класса убрать»;
- each `migrate` technology has exactly ONE unit of type `tech`, and its card has substeps
  of all types in this order: `разбор`, `env`, `core`, `usage`, `cleanup`, `review` (if a type is absent,
  the card tells why);
- **the thread of each technology is complete.** Read the substep names of the unit one after another, from top to bottom.
  They must make a connected story «разобрали, кто обращается -> настроили -> создали шаги -> перевели на них всех, кто обращался -> удалили старое -> проверили».
  Two commands collected the consumer list (old imports and direct calls to the framework service).
  Each consumer is in exactly one substep `usage`. Each class from the `core` substeps has
  `usage` substeps that change the callers to it;
- each substep has «Что сделать» (actions with names), «Итоговый результат» and
  «Чекпоинт» with a command filled; the substeps do not contain the words «мигрировать», «адаптировать», «при необходимости», «и так далее»;
- each `tech` card has the table «Чекпоинты юнита» filled, with an exact
  command in each row;
- no unit and no substep is larger than the limit of its type;
- the `usage` substeps of each technology go from bottom to top by levels, the tests are last;
- no unit depends on a unit that is below it.

Do not change the `НЕТ В ДОКЕ` rows (no replacement for a separate pattern inside a `migrate` technology) into units.
They wait for the answer of the human in section 6.

Mark Stage 5 `[x]`, `map_stage: 6`.
