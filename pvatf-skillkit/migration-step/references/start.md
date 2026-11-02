# Start of the work: Steps 1-2 and the batch of units

This is a part of the skill `migration-step`. The main rules and the reading order are in
`SKILL.md`. «Если упёрся» and «Таблица решений по умолчанию» are in `references/stuck.md`.

## Step 1 - Open the migration map and take one unit

1. From `.gigacode/data/migration/MIGRATION-MAP.md`, read ONLY these parts:
   - the header;
   - «1. Паспорт проекта» (commands, rules, table of technologies);
   - «4. Юниты работ»;
   - «6. Открытые вопросы к человеку».
2. Gate:
   - `map_status` is not `approved` -> **СТОП**: the migration map is not approved, you
     need `migration-map`.
   - There is no map file -> **СТОП**: first do `migration-map`.
   - Section 6 has a question without an answer (`ответ: -`) -> **СТОП**: show these
     questions. Tell the human that the migration does not continue until the human answers
     them. Do not change anything.
3. Select the unit:
   - You got a batch («пачка: M-001, M-002, ...») -> see «Пачка юнитов» below.
   - The human or the orchestrator named a unit -> take it.
   - There is a unit `in-progress` -> take it.
   - Else take the first `todo` from the top whose all «Зависит от» units have the status
     `done`. A unit that is not in the table, but is in the line «В архиве» above it, has
     the status `done`.
   If the header of the migration map has `scope: core`, take only units of type `env`. In
   units `tech`, take only the substeps `разбор`, `env` and `core`. Do not touch other
   units and substeps, even if the human asks «продолжи». If no unit agrees with these
   conditions -> **СТОП**, tell why (all is done / all waits on `blocked`).

## Step 2 - Read the unit card and check the input

1. Read `.gigacode/data/migration/units/M-<nnn>.md` in full. For a unit `tech`, do not read
   it in full: read it as section «Юнит технологии», item 1, tells.
   Then, in section 2 of the migration map, read the target picture block `T-<tech>` of this
   technology (the field «Целевая картина» of the unit card). It shows how the code must
   look at the end.
   Then read the architecture plan `.gigacode/data/migration/ARCHITECTURE.md`. Read
   sections 1, 2 and 4 in full. From sections 3 and 5, read only the lines of your technology
   (`grep -n "| <tech> |" .gigacode/data/migration/ARCHITECTURE.md`). If the file does not
   exist (the migration map was made without a plan), work by the block `T`. Write this
   into the log of the migration map.
   Then, in section «8. Что уже изменилось» of the migration map, read the lines with the
   technology of this unit (the field `tech` of the unit card). These lines show what was
   already moved before you: what was replaced with what, and how to call it now. Do it the
   same way. Do not invent a second way.
   For a unit `tech` (before the substep `env`) and for a unit `env`: in
   `.gigacode/data/migration/CONNECTIONS.md`, read the section of your technology and the
   sections «Стенды», «Переменные окружения и системные свойства», «Сертификаты и хранилища ключей». If the
   file does not exist (the migration map was made before the registry), collect the section
   of your technology yourself. Do it by step 1a of Stage 2 of the skill `migration-map` (the
   search commands are there). Write the file by its template.
2. Check git:
   ```
   git status --short
   git branch --show-current
   ```
   - The migration branch in the map passport is `-` (this is the first unit): go to the
     main branch from the map passport. Make the migration branch (`git checkout -b <имя>`)
     and write its name into the map passport. Use the branch name convention of the
     project from the map passport. If there is no convention, use `pvatf-migration`. Do
     not ask for permission to make the branch.
   - The map passport has a migration branch: you must be on it. If you are not on it and
     the tree is clean -> `git checkout <ветка миграции>`.
   - There are changes without a commit, and the unit is NOT `in-progress` -> **СТОП**.
     Tell the human. Do not revert anything and do not make a commit of changes of other
     people.
3. The unit was `in-progress` -> read «Где остановился» in the unit card and continue from
   there. Do not do again the work that is already done. For a unit `tech`: look at the
   table «Подшаги». Continue from the first substep whose status is not `done`. For a
   substep `in-progress`, read its «Сделано» and `git status --short`, and finish it.
4. **Write immediately:** `status: in-progress` in the unit card, and the same in the table
   of section 4 of the migration map.

## Batch of units («Пачка юнитов») (only if you got more than one ID)

A batch is a set of units that you do one after another in one chat. The rules of each unit
do NOT change: each unit has its own unit card, its own checks, its own record in the
migration map and its own commit.

0. Units `tech` can be in a batch. Do each of them completely, with all substeps. Then do
   the next unit of the batch. The context compresses itself during the work. This is
   normal, see rule 3 of the executor in SKILL.md.
1. Write the list of batch IDs into todo, in the order of the table of section 4. If there
   are more than 5 IDs, take the first 5. Name the other IDs in the summary as not done.
2. For the FIRST unit of the batch, do Steps 2-7 completely.
3. After Step 7, look at the status of this unit:
   - `done` -> take the next ID from the batch and do Steps 2-7 completely for it. Read the
     unit card again. You do not need to read `references/` again.
   - `in-progress` or `blocked` (you physically cannot work: the project does not compile,
     or the test is red because of the migration after 3 attempts) -> **СТОП пачки**. Do NOT
     start the next units, even if they do not depend on this unit. Go to Step 8.
   Postponed places (`решить человеку`) do NOT stop the batch: a unit with them closes as
   `done`.
4. Before each next unit, check:
   - all its «Зависит от» units are `done`;
   - the git tree is clean (`git status --short` is empty);
   - section 6 of the migration map has no new questions without an answer.
   If not -> СТОП пачки, Step 8.
5. Do not do these things:
   - put units of the batch into one commit;
   - skip the checks of Step 6 «потому что юнит маленький»;
   - make changes of the next unit before the current unit is closed.
6. Do Step 8 ONE time at the end: a summary with a separate line for each unit of the batch.
