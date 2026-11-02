# Markup unit (`markup`)

This file is part of the skill `migration-step`. Open it when the unit type in the unit card is `markup`.

The unit adds allure-annotations to the tests that are already migrated. The rules and the values are in
`references/markup-rules.md` and in the line «Разметка» of the map passport. You do not need the framework documentation
here: do not start the documentation subagent, «Таблица подтверждений» is `-`. There are no questions:
the values were collected at Stage 2 of the map. If there is no value (`-`), do not add the annotation.

**Where to search - only in the project** (section 0 of the markup rules). Do not go outside the project root
(`find /`, `find ~`, other projects). Do not go into the framework project and sources, the example project,
`~/.m2`, `~/.gradle`, .jar and the internet. Exception: the jar of allure-annotations itself, version
2.x, and only for an annotation that is not in the import table (section 0 of the rules). If you did not find a package, a version or
a value in the project -> do not search more: do what the rule for this case tells.

1. Read `references/markup-rules.md` and the line «Разметка» of the passport:
   `grep -n "^- Разметка" .gigacode/data/migration/MIGRATION-MAP.md`.
   If the line still has angle brackets (the value is not collected) -> this is an open question of the map:
   stop (СТОП), as in Step 1 (`references/start.md`).
2. `Unit.java rules M-<nnn>` - rule `MR-51`.
3. Base: `git rev-parse HEAD` - remember the hash before the changes.
4. Who adds the annotations:
   - mode `менеджер` - the agent `pvatf-marker` (call by name, `references/core-rules.md`,
     rule 7) with this task:
     ```
     Проект: <абсолютный путь>
     Юнит: M-<nnn> · markup · <название>
     Файлы: <таблица «Файлы юнита»: путь - изменить>
     Значения разметки: <строка «Разметка» паспорта целиком>
     Что сделать: <«Что сделать» карточки дословно>
     Компиляция: <команда из паспорта>
     Коммит: <сообщение по конвенции проекта, с ID юнита M-<nnn>>
     ```
     The agent makes the commit of its files itself. Before the changes, the agent does three checks (section 2b
     of the rules): no uncommitted changes, library version 2.x or its upgrade in the
     values, the project compiles. If it returned «не сделан» because of one of them -> do not add the markup yourself
     and do not start the agent again. This is a stop (`references/stuck.md`, «Если упёрся»,
     way 3). In «Где остановился», write the reason from the agent report and what the human must do:
     commit the changes / upgrade the version to 2.x / fix the build or the dependency tree.
     After this, do the same as with the substep executor
     (`references/manager.md`, items 4-8): report check, `Unit.java check`, checker,
     retries. In a retry, also use `pvatf-marker`. The unit files for the checker come from
     `git diff --name-only <база>` (without `.gigacode/`). Add the line
     `База: <база>` to the task of the checker;
   - mode `сам` - first the three checks of section 2b of `references/markup-rules.md` (if one is not
     passed -> stop, as above), then do the items «Что сделать» yourself, by sections 2-3,
     then the checks from `references/check.md` (do not run the tests).
5. Markup check - the commands from section 5 of `references/markup-rules.md`, on the test classes of the
   unit: «Файлы юнита» and the subclasses of the base classes from them. If a test class does not have an annotation of
   the agent set that has a value in the line «Разметка» (not `-`; section 1 of the rules; not
   its own and not through a base class) -> retry the executor with this list. The test classes of other
   markup units are not part of this check. Write the command output in «Журнал выполнения» of the unit card.
   Each test-case key that «Что сделать» tells to take from `@DisplayName` must now be in
   `@TmsLink` of this test method, and `@DisplayName` must not change.
   Then do the final re-check from section 6 of `references/markup-rules.md` yourself (do not trust the agent
   report without a check): the output of the command «Ключи тест-кейсов без `@TmsLink`» must be empty, or each of its
   lines must be in the report with a false condition of section 2a. Run the command on all
   test directories of the project, not only on «Файлам юнита». If you found a line without a reason ->
   retry the agent with this list.
   The agent report is the block `=== ОТЧЁТ PVATF-MARKER ===` ... `=== КОНЕЦ ОТЧЁТА ===`. If there is no block
   or a line is missing in it -> retry the agent: «Верни отчёт по шаблону». Compare the same keys
   yourself: run the command «Одинаковые ключи тест-кейсов» (section 5 of the rules) on all test directories.
   Write each key from its output in «Входящие» of the map, also if the agent did not name it:
   `решить человеку: <ключ> - одинаковый в <Класс.метод>, <Класс.метод>, новый @TmsLink
   не поставлен`. Write the lines «Ключи не взяты по другим причинам» there too, with the reason in words.
   The files `добавлен по перепроверке` (only `@TmsLink` and its import) are not a violation of the unit
   limits: add them to «Файлы юнита» with this mark.
6. The checker (`pvatf-checker`, `references/check.md`, item 9) also checks one more thing: the changes are
   only in the annotations, their imports and the dependency; `@DisplayName` did not change; the test logic
   did not change.
7. Then use `references/close.md`, as for all units. The agent already made the commit of the unit files:
   in Step 7, commit the remaining files (the unit card, the map, your fixes). Write the hash in the unit card from
   `git log --format=%h <база>..HEAD`.
