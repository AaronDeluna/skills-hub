# Stage 6 - Show the migration map to the human and get the approval

This file is a part of the skill `migration-map`. The general rules are in `references/core-rules.md`. The rules of the migration map and the order of stages are in `SKILL.md`.

1. In the header, set `map_status: review`.
2. Show the human a summary:
   - the map passport (2-3 lines);
   - the table of technologies (the order, what we migrate, what stays `keep` and why);
   - the number of rows in the matrix `G`;
   - the number of problems `A`;
   - the number of units for each phase;
   - **all open questions** from section 6.

   Separately, show the architecture plan: the package tree and the new classes with their
   responsibility (sections 2 and 3 of `ARCHITECTURE.md`). Tell the human that he can correct
   it before the approval.
3. **First the questions, then the approval.** Usually, at this stage there are no questions
   (the gate before Stage 5). If section 6 still has a question without an answer (`ответ: -`),
   you CANNOT approve the migration map. Ask the human to answer each question. When you get
   an answer -> write it into section 6. Immediately correct the migration map and the unit
   cards by it (rows `G`, `L`, units). While at least one question has no answer,
   `map_status` stays `review`.
4. If there are no questions without an answer -> ask one question: «Карту утверждаем? да / нет (что
   поправить)».
   - «да» -> `map_status: approved`. Say: «Откройте новый чат и напишите: `/orchestrator Продолжи миграцию`».
   - corrections -> add them to the migration map and the unit cards, and show it again.

**Update of the migration map («Обновление карты»)** (the migration map is already `approved`,
but the project changed or «Входящие» has new items): do not make anything again from zero.

Examine section 5 «Входящие». Make each item a new unit or a question to the human. For a new
unit:
- put it at the end of the applicable phase;
- use the next free number `M-<nnn>`. It must be larger than any number in the table, in the
  row «В архиве» above it and in the directory `units/`.

Some items are about a technology whose unit `tech` is not `done` yet. They become substeps
at the end of its unit card (before the substep `review`, if it is not done yet).

Some items come from the review («крупно»: split a class, remove a layer). They become `arch`
units. After them, add one more `review` unit for the changed files.

Do not change the statuses of the units that are done. Show the changes and get «да» again.

If `scope` changed from `full` to `core`: rewrite the unit cards of the `core` substeps that
are not done yet for the mode `in-place` (Stage 5, the table of modes). Do not change the
substeps that are done.

