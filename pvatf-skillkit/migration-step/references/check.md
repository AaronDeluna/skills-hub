# Check of the substep (unit): Step 6

This is a part of the skill `migration-step`. The main rules and the reading order are in
`SKILL.md`. «Если упёрся» and «Таблица решений по умолчанию» are in `references/stuck.md`.

**Manager mode (default): from this file, take only the task for the agent
`pvatf-checker` (item 9, `references/manager.md`, item 6).** The executor does the
compilation and the self-check. In this mode, all «исправь» and «почини» in this file mean a
retry of the executor (`references/manager.md`, item 8), not your change of the code.

## Step 6 - Check (all checks are mandatory, write the result into the unit card)

Take the compilation and test commands from the map passport.

1. **Compilation.** Run it. If it fails:
   - the error is in your code -> fix it and run again;
   - `cannot find symbol` / a wrong type for something from PVATF -> start the documentation
     subagent again with an exact question about this name (common rule 1: not the jar). If
     this does not help -> «Если упёрся»;
   - a file OUTSIDE the unit breaks because it depended on the changed file ->
     «Если упёрся», the item about an extra file.
2. **Representative test.** Unit `env` or `core`-`new` (the unit card has no test, `-`) ->
   do not run tests. Write `тесты не запускались: проверка компиляцией` and go to item 3.
   Else run EXACTLY the command from the section «Показательный тест» of the unit card,
   with the same limit of 10 minutes (`timeout 600 ...`). Write into «Проверки» the command,
   the result (how many passed/failed) and how many seconds it ran.
   - **green** -> continue;
   - **red** -> read the error. If the cause is in your migration -> fix the code (not the
     test and not its checks, see `MR-9`..`MR-11`) and run again. Do not do more than 3
     attempts. If it does not work -> «Если упёрся»;
   - **red with the same error as BEFORE the changes** (Step 4) -> the migration did not
     break it, but it is not proved. Go to «Если упёрся», the line about a test that was
     red before the migration;
   - **does not start because of the environment** (no stand, no network, no access) ->
     «Если упёрся».
   Do not do these things:
   - run the full class, module or all tests instead of one method;
   - replace the representative test with a different test «попроще» (except the cases
     from «Если упёрся»);
   - run with skipped tests (`-DskipTests`, `-x test`);
   - write «зелёный» without a real run.
   If the unit card has `-` with a cause instead of a test -> write
   `показательного теста нет: <причина>`. The unit closes by the other checks.
3. **Remains of old code.** Run the grep pattern from «Критериев готовности» on the files
   of the unit. The output must be empty. If it is not empty -> finish the work. Then, for
   each item of «Legacy под удаление в этом юните», make sure of two things: the
   file/dependency does not exist, and grep by its name is empty. Write into «Проверки»: what you removed, and that 0 references stay.
   In a `cleanup` unit, run grep on the FULL project (sources, resources and build files),
   not only on the files of the unit. After the cleanup, nothing of the old implementation
   of the technology must stay. If something stays and it is not from a `keep` technology
   -> remove it if it has no references. Else write an item in «Входящие».
4. **Number of tests after** (the same command as in Step 4). It must not be less than the
   number «до».
5. **Compare with the target picture (for `core` and `usage`).** For each changed and new
   file, answer these questions. Write each answer into «Проверки» as one line:
   - Are there calls or imports of classes from the list «Чего НЕ будет» of the block `T`?
     It must be: no.
   - Did you make a class that is not in «Что будет» and not in the file table of the unit
     card? It must be: no.
   - Do the steps go to the framework through the base layer of the technology (`MR-49`),
     with the mechanisms from «Что вызывается и кем»? Do the checks use the matchers that
     are named there? It must be: yes.
   - Does the test class (a file with `@Test`) have helper methods - private methods that
     send requests, read files, make SQL, map into objects (`MR-42`)? It must be: no. This
     logic must be in the step classes. (One short call to the framework in the body of the
     test itself is permitted.)
   Any other answer -> fix the code. (`core` in mode `in-place` checks only the second
   item.)
6. **Code rules.** Run the self-check:
   ```
   java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/Unit.java check M-<nnn> S-<nn>
   ```
   It checks the mechanical rules on the files of the substep: `var`, setters,
   `getForCurrentThread()`, asserts, DTO, own matchers, nested classes, delegates, reading
   of settings, names, logging, `sleep`, `TODO`, test class. It also shows the changed files
   that are not in the unit card (item 8). Fix each line of the output, also in lines that
   you did not write. Run it again until you get `находок 0`.
   The only permitted exception is an assert by `MR-29` when the documentation has no
   matcher. For it, write the line `исключение MR-29: <файл>:<строка>` in «Сделано» of the
   substep and a line in «Входящие». Then the script skips it.
   If you do not know how to fix a line -> open the rule in `rules-now.md` (or run
   `Unit.java rules` with this number in the unit card).
   Then go through the rules from `.gigacode/data/migration/tmp/rules-now.md` for each
   changed file. If a rule is broken -> fix it. Write: `MR: все пройдены` or a list of
   exceptions with the cause.
7. **Thread.** Check with commands:
   - You MADE a class or a method (`core`): count its callers -
     `grep -rl "\b<ИмяКласса>\b" --include=*.java --include=*.kt <src> | grep -v "<ИмяКласса>.java"`.
     If there are no callers yet, this is normal only if the unit card has later substeps
     `usage` that move code to it (`grep -n "<ИмяКласса>"
     .gigacode/data/migration/units/M-<nnn>.md`). If there are no such substeps -> find the
     files that do the same thing themselves (commands from «Разбор технологии»). Add
     substeps `usage` for these files. For a usual unit (not `tech`) -> write an item in
     «Входящие» of the migration map:
     `класс <Имя> создан в M-<nnn>, но не подключён; то же делают сами: <файлы>`.
   - You MOVE files to a step class (`usage`): in each file, the step class must really be
     called (`grep -c "<ИмяКласса>" <файл>` is more than 0). No calls that it replaces must
     stay (the command from «Чекпоинта» is empty). If some stay -> go back to Step 5.
   Write the result as one line: `нить: <класс> вызывают <n> файлов`.
8. **Limits of the unit.** Run `git status --short`. The list of changed files must have
   only the files from the unit card. If there are extra files -> put them back as they were
   (`git checkout -- <файл>`) or go to «Если упёрся».
   The service folder `.gigacode/data/migration/tmp/` does not count. Do not make a commit
   of it.
9. **Check with fresh eyes - the subagent «проверяющий».** You wrote this code and you do
   not see your errors. A subagent with a clean context sees them. Do this check after EACH
   substep (unit) before the commit. Exceptions: the kind `разбор` (the code did not change)
   and `review` (it has its own review).
   1) The file list - the files of the substep from `git status --short` (without
      `.gigacode/`).
   2) Start the agent `pvatf-checker` with the task below. If there are more than 8 files,
      divide them into groups of not more than 8, one agent for each group. Do not run more
      than 3 agents at the same time.
      The subagent is mandatory. Do not check yourself. Only if the subagent call returned
      an error (not «долго» and not «проще самому»):
      - show the error in the chat;
      - write into the log of the migration map `сабагент не запустился: <ошибка>`;
      - go through the instruction from `.gigacode/agents/pvatf-checker.md` yourself, one
        file at a time;
      - write `проверка: сам - <ошибка>`.
   3) For each finding, open the line yourself and make sure that the finding is real:
      - false -> do not touch it. In «Сделано», write `ложная: <почему>`;
      - real, `просто` -> fix it now;
      - real, `крупно` -> for a unit `tech`: add a substep `fix` or `usage` («Дописывание
        подшагов», `references/tech-flow.md`). For a different type of unit: a line in
        «Входящие» of the migration map.
   4) If you fixed something -> run the compilation, and start the subagent ONE more time
      only on the fixed files. If it finds the same thing again -> do not loop: write the
      line `решить человеку: <файл>:<строка> - <правило>` in «Входящие» and continue. Never do more than two runs for a substep.
   5) Write into «Сделано» of the substep (in a usual unit - into «Проверки»):
      `проверка: находок <n>, исправлено <n>, ложных <n>, в подшаги или Входящие <n>`. Without this line, the
      substep does not close.

   **Task for the agent `pvatf-checker`** (replace `<...>`, do not add anything more). The
   agent itself (`.gigacode/agents/pvatf-checker.md`) tells how to check and in which form
   to answer. It reads the rules itself from `tmp/rules-now.md`.
   For how to start an agent by name, see `references/core-rules.md`, rule 7.
   ```
   Проект: <абсолютный путь к корню проекта>
   Что шаг должен был сделать: <«Итоговый результат» подшага дословно>
   Чего в коде быть не должно: <старые классы и пакеты из «Чего НЕ будет» блока T и grep-шаблон из карточки; нет - "-">
   Файлы шага:
   - <путь> - <изменён / создан / удалён>
   База: <только юнит markup: хэш из references/markup.md, п.3; в остальных юнитах этой строки нет>
   ```
   If the answer does not have the headings `## Находки`, `## Файлы без находок`,
   `## Не удалось прочитать`, it does not agree with the template. Start the agent again
   with the same task.
10. Mark with `[x]` the done items of «Критерии готовности» in the unit card.
