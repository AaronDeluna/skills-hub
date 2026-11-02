# Manager mode: the executor subagent does the substep

This is a part of the skill `migration-step`. **This is the default mode.** It applies if the
map passport has the line `- Режим исполнения: менеджер`, or if it has no such line (an
older migration map). Only with `- Режим исполнения: сам`, do not read this file. Then you
do the substeps yourself (`references/work.md`, `references/check.md`).

Why: in a long unit `tech`, your context collects the code of all substeps. At the tenth
substep, you forget the rules of the first substeps. In manager mode, you do not write code
and you do not read the project files. A new subagent with a clean context does each
substep. It gets only its task package and returns a short report. You keep the unit card,
do the checks and make the commits.

This mode works if GigaCode subagents can change project files and run commands (build,
tests, `java`). Check this in practice, on the first substep - see «Первый
исполнитель в карте».

## First executor in the migration map («Первый исполнитель в карте»)

If the map passport has no mark `проверено` near the mode -> after the report of the FIRST
executor, check yourself:
```
git status --short
```
- The output has the files of the substep, and the report has the compilation output ->
  the subagents can do all that is necessary. Add `· проверено M-<nnn> S-<nn>` to the line
  of the map passport. Continue to work in this mode.
- Any of these conditions -> change the mode:
  - the output has no files of the substep;
  - the executor answered that it cannot change files or run commands;
  - the subagent call returned an error (show it in the chat).
  To change the mode, write this line in the map passport: `- Режим исполнения: сам · основание: сабагент не смог менять файлы (M-<nnn>
  S-<nn>, <что случилось одной строкой>)`. Do this substep and all next substeps yourself
  (`references/work.md`, `references/check.md`). Do not ask the human. In the final answer
  to the human, write one line: «Исполнитель не смог менять файлы. Частая причина - GigaCode
  запущен в режиме plan: из него сабагенту нельзя дать права на правки. Чтобы вернуть
  режим менеджера, перезапустите GigaCode в обычном режиме и напишите `/orchestrator
  Подшаги делай сабагентами`».

## Rules of the manager

1. **One substep - one executor, strictly one after another.** Start the next executor only
   when the previous substep is closed and has a commit. Never run executors in parallel:
   they change the same files and build the same project.
2. **You do not write or change code - at all.** Do not change any file outside
   `.gigacode/`: no line, no import, no fix of a finding, no compilation error. If you
   found something to fix, it is a retry of the executor (item 8), even if the fix is one
   line. Do not read the project files in full. You read the unit card, the migration map,
   the reports of the subagents and the output of the scripts. All «исправь» and
   «почини» in `references/work.md` and `references/check.md` are for the mode «сам» and for
   the executor, not for you.
3. **Only you write the unit card and the migration map.** The executor changes only the
   files of its substep. It does not touch `rules-now.md`.
4. **Only you make the commit**, after the checker and the checkpoint.
5. **Documentation - before the executor.** The executor cannot start the documentation
   subagent (a subagent does not start subagents). Thus, get from the documentation all
   that the executor needs before you start it. Give it in «Таблице подтверждений».

## Substep cycle

Do this for each substep in order (as in `references/tech-flow.md`, item 2). Do the substeps
`разбор` and `review` yourself, as before.

1. **Task package.** Run `Unit.java recite M-<nnn> S-<nn>` and
   `Unit.java rules M-<nnn> S-<nn>`. Give the substep the status `in-progress`.
2. **Documentation.** Do Step 3 of `references/work.md`. The doc notes records of the
   substep are in `tmp/docs-now.md`. For each framework name that is not there, first search
   with `Notes.java find`. Only if it is not there too, use the documentation subagent.
   Write the result into «Таблицу подтверждений» of the unit card. If the documentation
   does not have the necessary name -> write a line `решить человеку` in «Входящие», and
   write «это место не трогать» in the task package for the executor.
3. **Executor.** Keep the base: `git rev-parse HEAD`. Start the agent `pvatf-executor` with
   the task below. Wait for the report.
4. **Your check of the report.**
   - `git rev-parse HEAD` is not equal to the base (the executor made a commit, but it must
     not) -> `git reset --soft <база>`. The changes stay in the working tree. Then continue
     as usual.
   - The report does not agree with the template -> start the executor again (one time).
   - `Статус: не сделан` -> «Если упёрся» (`references/stuck.md`) for the cause from the
     report.
5. **Script.** Run `Unit.java check M-<nnn> S-<nn>`. `находок 0` -> continue. There are
   findings -> start the executor again with these findings (item 8).
6. **Checker.** Run the agent `pvatf-checker` with the task from `references/check.md`,
   item 9. Findings `просто` -> start the executor again (item 8). Findings `крупно` -> add
   a substep by `references/tech-flow.md`, «Дописывание подшагов».
7. **Checkpoint of the substep** - run the command from the field «Чекпоинт» yourself. If the
   result is not as expected -> start the executor again with the checkpoint output (item 8).
8. **Retry of the executor.** Give the same task, and add at the end «Подшаг уже начат. Исправь ТОЛЬКО
   это, остальное не трогай:» and the list of findings. Do not do more than two retries for
   a substep. If findings stay after the second retry -> write the lines
   `решить человеку: <файл>:<строка> - <что>` in «Входящие». If the project compiles, close
   the substep. If it does not compile -> the substep is `blocked`, stop the chat.
9. **Closing.** In «Сделано» of the substep, write:
   - the report of the executor (the lines «Сделано», «Проверки»);
   - the line `проверка: ...`;
   - the checkpoint output.
   Set the status `done`. Make the commit of the files of the substep and of the unit card
   (`references/tech-flow.md`, item 4). Then go to the next substep.

## Task for the agent `pvatf-executor` (replace `<...>`, do not add anything more)

The agent itself (`.gigacode/agents/pvatf-executor.md`) already tells how the executor
works, what it can do and how it reports. Give only the task package of the substep. Do not
copy the code rules into the task: the agent reads `tmp/rules-now.md` itself. For how to
start an agent by name, see `references/core-rules.md`, rule 7.

```
Проект: <абсолютный путь к корню>
Подшаг: M-<nnn> S-<nn> · <вид> · <название>
Файлы (менять можно ТОЛЬКО их):
- <путь> - <изменить / создать / удалить>
Что сделать (по порядку):
<пункты «Что сделать» подшага дословно>
Критерии по файлам:
<таблица «Критерии по файлам» дословно; нет - "-">
Итоговый результат: <дословно>
Таблица подтверждений (имена фрейма, которые можно писать):
<строки таблицы подтверждений: имя - запись конспекта - как использовать (1 строка)>
Не трогать (нет в документации): <места; нет - "-">
Образец в проекте (как уже сделано в прошлых подшагах): <1-2 пути из «Что уже изменилось»; нет - "-">
Компиляция: <команда из паспорта>
Показательный тест: <команда с timeout 600; для env и core-new - "-">
```

The answer of the agent must start with the line `- Статус:`. It must contain the lines
`Сделано`, `Файлы`, `Проверки`, `Не сделано и почему`. If it does not have them -> the
answer does not agree with the template (item 4 of the cycle).
