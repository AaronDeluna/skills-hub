# Record of the result and summary: Steps 7-8

This is a part of the skill `migration-step`. The main rules and the reading order are in
`SKILL.md`. «Если упёрся» and «Таблица решений по умолчанию» are in `references/stuck.md`.

## Step 7 - Write the result and make the commit

**Unit `tech`:** close a substep and make its commit by the section «Юнит технологии»
(`references/tech-flow.md`, item 4). Write into the migration map at the end of the chat by
its item 6. Close the unit by its item 7. For such a unit, do the items below one time -
when all checkpoints of the unit agree.

1. **Write what changed.** At the end of the section «8. Что уже изменилось» of the
   migration map, add one line for each replacement of this unit. The line has: unit,
   technology, what it was, what it is now, how to call it now (a short pattern or the path
   to a pattern file). Write it so that a person who did not see this chat understands the
   new way. Without this record, the unit does not close.
2. All readiness criteria are `[x]` -> `status: done` in the unit card, and `done` in the
   table of section 4 of the migration map. If not all -> keep `in-progress` and fill
   «Где остановился» exactly: which step of the unit card is the last done step, what
   stays, which error.
3. Make a commit of ONLY the files of the unit (not `git add .`). Do not ask for permission -
   you are in the migration branch. Check it: `git branch --show-current` must be equal to
   the branch from the map passport. If it is not equal -> do not make the commit, СТОП,
   tell the human.
   ```
   git add <файлы юнита>
   git commit -m "<сообщение по конвенции проекта, с ID юнита M-nnn>"
   ```
   Write the commit hash into the unit card. Also make a commit of a unit that is not
   finished, if the project compiles. If it does not compile -> do not make the commit. Keep
   the changes in the working tree and describe them in «Где остановился».
4. Add one line at the end of the section «7. Журнал сессий» of the migration map. Update
   `updated` in the header.

## Step 8 - СТОП and summary

Do not take the next unit (in a batch - do not take units that are not in the given list).
Show to the human (for a batch - for each unit):
- unit `M-<nnn>`, name, final status (`done` / `in-progress` / `blocked`);
- the changed files;
- checks: compilation, **representative test** (which test, command, result - honestly),
  remains of old code, `MR`;
- which legacy is removed (classes, dependencies, configs);
- what you added to «Входящие». Separately, show all lines `решить человеку` (the human
  looks at them when the human comes back);
- progress: `done` X of N;
- what next: **«Откройте новый чат и напишите: `/orchestrator Продолжи миграцию`»**.
