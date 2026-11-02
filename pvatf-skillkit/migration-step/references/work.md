# Work on the substep (unit): Steps 3-5

This is a part of the skill `migration-step`. The main rules and the reading order are in
`SKILL.md`. «Если упёрся» and «Таблица решений по умолчанию» are in `references/stuck.md`.

**Manager mode (default): from this file, take only Step 3 (documentation - before you start
the executor, `references/manager.md`, item 2).** In this mode, the executor agent
`pvatf-executor` does Steps 4 and 5 (read the project files, change the code), not you.

## Step 3 - Get the documentation (first the doc notes, then the subagent)

**Unit of type `review` and substep `review` of a technology unit:** do not do Steps 3, 4
and 5 for it. Instead, read `references/review-subagent.md` and work by the section
«Порядок работы в юните `review`». To get the text of an `MR` rule for a finding, find it
by its number: `grep -n "MR-<n> ·" .gigacode/skills/migration-step/references/code-rules.md`.
Read only this rule. Then do Step 6 (`references/check.md`, items 1, 2, 6, 8, 10) and
Step 7 (`references/close.md`).

1. Read `references/doc-subagent.md` in full. It has the rules, the task for the agent and
   the record template.
2. The doc notes records of the substep are already in
   `.gigacode/data/migration/tmp/docs-now.md`. `Unit.java rules` writes them (Step 5,
   item 1). If you did not run it yet, run it now. Read the file in full. Do not read the
   full doc notes file.
3. Go through the steps «Что сделать» of the unit card. For each step, ask yourself: «каждое имя из
   PVATF, которое мне тут нужно написать (класс, аннотация, метод, зависимость, параметр
   конфигурации), есть в прочитанных записях?»
   - Yes -> write it into «Таблицу подтверждений» of the unit card: the exact name and the
     record ID.
   - No -> first run `Notes.java find <tech> <слова>` (with two sets of words, see
     `references/doc-subagent.md`, «Сначала конспект»). The doc notes often already have
     the answer from the time when the migration map was made, or from previous substeps.
     If you found it -> write it into «Таблицу подтверждений» with its ID. If you did not
     find it -> this is a question for the subagent. Write a list of such questions, with the output of `Notes.java find` for
     each question.
4. If there are questions -> start the agent `pvatf-docs` (the task by the template, not
   more than 5 questions for one run). Do NOT call `get_pv_at_doc` yourself. Ask about an
   action («как <сделать то-то> в <технология>»), not about the name of an old class.
5. IMMEDIATELY add the answers as new records into the doc notes of the technology. Write
   their IDs into «Док-основание» and into «Таблицу подтверждений» of the unit card.
6. Answer `найден частично` or `НЕТ В ДОКЕ` -> ask again by the rules from
   `references/doc-subagent.md` (other wording). A final `НЕТ В ДОКЕ` for a question
   without which you cannot do the step -> «Если упёрся».
7. The subagent answered `MCP НЕДОСТУПЕН` -> **СТОП**. Without the documentation, you
   cannot do the unit. Keep the status `in-progress`. Write the cause into «Где остановился».

## Step 4 - Read the files of the unit (only them)

1. Read the files from the table «Файлы юнита». Do not open other project files. Exception:
   1-2 files that the unit card directly names as a pattern.
2. Count «число тестов до» and write it into the unit card:
   ```
   grep -cE "^\s*@Test\b" <файлы юнита>
   ```
3. **Representative test - run BEFORE the changes.** Do this only if the unit card has a
   test (`env` and `core`-`new` do not have it - skip this item). Run it with a time
   limit of 10 minutes: `timeout 600 <команда из карточки>`. If there is no command
   `timeout`, run the command as it is, and stop it yourself if it runs more than 10
   minutes. If it did not finish in time -> do not run it again: this is not a fast test,
   see «Если упёрся».
   Run the command from the section «Показательный тест» of the unit card. Write the result
   into «Проверки» (`зелёный` / `красный: <ошибка в 1 строку>` / `не запускается: <причина>`). This is the reference point. If it is red or does not
   start before your changes, do not fix it. Only write it down: after the migration, you
   compare with this result.
   If the unit card has `-` with a cause instead of a test, skip this item.
4. Make a map for yourself: which place in the files -> which step of the unit card ->
   which line of «Таблицы подтверждений». If a place has no line in the table, go back to
   Step 3. If the documentation does not have it, go to «Если упёрся».

## Step 5 - Migrate

1. **The rules of this substep (unit) - only them.** The script takes the numbers from the
   field «Правила подшага» of the unit card (in a usual unit - «Правила юнита»; if the field
   is empty - by the kind of substep). It writes their text into a file:
   ```
   java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/Unit.java rules M-<nnn> S-<nn>
   ```
   Read `.gigacode/data/migration/tmp/rules-now.md` in full. If the script wrote «НЕ
   НАЙДЕНЫ», a number in the unit card is wrong. Fix the unit card and run again. Do not
   read all of `references/code-rules.md`. The checker also needs the file `rules-now.md`
   (Step 6, item 9). Do not remove it and do not make a commit of it. In a usual unit
   (not `tech`), do not write the substep number.
2. Do the steps «Что сделать» from the unit card in order. After each step of the unit
   card, write one line in «Что сделано».
   **Where to put the code (architecture plan).** Before you make a file or add a method:
   - the file with the action `создать` from the unit card is in section 3 of the plan ->
     make it. Write into it only what agrees with its «За что отвечает»;
   - you need a method (a new action, a common part of logic) -> in sections 3 and 5 of the
     plan, find a class with a matching responsibility and add the method there. If the
     same method already exists, call it. Do not write a second one;
   - the plan has no matching class -> you can make ONE new class for a unit (in a
     technology unit - for a substep). Conditions:
     - one responsibility, in one sentence;
     - a name that tells what it does (not `Utils`/`Helper`/`Common`);
     - it has callers.
     Immediately add a line to section 5 of the plan «Добавлено по ходу миграции» and to
     «Что сделано» of the unit card. If you need a second such class -> the plan is not
     complete. Make the second class too, and add it to section 5 of the plan. Add a line in
     «Входящие»: `решить человеку: план неполный, добавлены классы <...>`;
   - the code does not agree with the responsibility of the class where you want to add it
     -> do not add it «заодно». Do as the previous items tell.
3. **Checks - on the framework matchers.** Read `references/matchers.md`. It tells how the
   checks in the framework work, and which words to use when you ask the documentation
   about the necessary matcher.
   Write out all DIFFERENT kinds of checks from the files of the unit. For each kind that is
   not yet in the doc notes, ask the documentation subagent (Step 3).
   In a `usage` unit, replace each old check with a matcher/condition of the framework. Old
   checks are: `Assertions`, `assertEquals`, `assertThat`, an own assert class, an own wrapper around the response,
   manual parse of JSON for comparison. The check must check the same thing as before
   (`MR-9`, `MR-11`). Only the method changes.
   **Do not change an assert mechanically.** Sometimes the checked value was taken manually
   from the response, from a DB row or from a message (a DTO getter, `jsonPath().get`, an
   own check method). Then go back through the chain and write it again completely:
   - the method returns a validatable object;
   - the check uses `.should(...)`;
   - remove the extra DTOs and check methods (`MR-41`, «разбери всю цепочку»).
   If the doc notes do not have the necessary matcher -> ask the documentation subagent
   (Step 3). If the documentation does not have it -> see «Если упёрся».
4. Write only what the table confirms. Replace the old code. Do not keep it as comments.
   Remove the old comments that described the old implementation together with it.
5. **Remove the legacy of the unit.** Go through the section «Legacy под удаление в этом юните» of the unit card.
   Before you remove each class/package, make sure that no references to it stay:
   ```
   grep -rln "<ИмяКласса>" --include=*.java --include=*.kt --include=*.xml --include=*.properties --include=*.yml --include=*.yaml . | grep -v "/target/\|/build/"
   ```
   - empty (or only the file that you remove) -> remove it (`git rm <файл>`);
   - there are references in the files of this unit -> first finish the migration of these
     places;
   - there are references in files OUTSIDE the unit -> do NOT remove it and do not change
     files of other units. Write into «Входящие» of the migration map which files still
     refer to it. In `cleanup` - see «Если упёрся», the line about legacy.
   Remove a dependency/plugin from the build in the same way. First make sure with grep that
   the project has no imports of its packages. Remove it FROM ALL places of the build at the
   same time, not only from the module:
   ```
   grep -rn "<artifactId или имя библиотеки>" --include=pom.xml --include=*.gradle --include=*.kts --include=*.toml --include=gradle.properties .
   ```
   Maven: `<dependency>`/`<plugin>` in modules, `<dependencyManagement>`/`<pluginManagement>`
   in the parent, the version property in `<properties>`, `<exclusions>` for it. Gradle:
   blocks `dependencies`/`plugins`, lines in `gradle/libs.versions.toml` (`[versions]`,
   `[libraries]`, `[bundles]`, `[plugins]`), `gradle.properties`, `buildSrc/`.
   If a place is in the grep output but not in the unit card, it is the same case as
   «лишний файл» in «Если упёрся». The change is mechanical: add the file to the unit card with the
   mark `добавлен по ходу`.
6. If after your changes an old class that is NOT in the unit card is not necessary any more
   (grep shows zero references), remove it too. Add it to the unit card with the mark
   `удалён - больше не используется`. This is the only permitted extension of the file list.
7. Do not reformat lines that you do not change. Do not rename or move classes if the steps
   of the unit card do not tell you to do it.
