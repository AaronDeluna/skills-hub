# Technology unit (`tech`): order of substeps

This is a part of the skill `migration-step`. The main rules and the reading order are in
`SKILL.md`. «Если упёрся» and «Таблица решений по умолчанию» are in `references/stuck.md`.

## Technology unit («Юнит технологии») (type `tech`) - work by substeps

A unit `tech` is the full migration of one technology. Its unit card has:
- the section «Разбор технологии» (who uses the technology and how);
- the table «Подшаги» (`S-01`, `S-02`, ...) with statuses;
- one section for each substep (files, what to do, final result, checkpoint);
- the table «Чекпоинты юнита» at the end.
Do all substeps one after another in one chat, until all checkpoints agree. The context
compresses itself when it is full. After this, read SKILL.md and the unit card again and
continue from the first substep that is not done.

**Order of work in the chat:**

1. **Step 2 - one time at the start** (and again after context compression). Read these
   parts of the unit card: all before the section of the first substep, the table
   «Подшаги», «Чекпоинты юнита», «Таблицу подтверждений». Do not read the sections of
   substeps with the status `done` - keep the context small.
2. **Take the FIRST substep from the top whose status is not `done`.** Do not skip and do
   not select. Give it `in-progress` in the table «Подшаги». Read its section.
3. **Do the substep: Steps 3-5 (`references/work.md`) and Step 6 (`references/check.md`)** -
   or, in manager mode (map passport), by the cycle from `references/manager.md`.
   Here «файлы юнита» are the files of this substep, and «тип юнита» is the kind of the
   substep. BEFORE the changes of EACH substep, cut out and read its rules
   (`references/work.md`, Step 5, item 1). Yes, each time: in a long chat, you forget the
   rules first, and each kind of substep has its own rules. Substep `core`, `usage` or
   `fix` -> also read `references/matchers.md`, sections «Как писать проверку» and
   «Запрещённые приёмы». Kind `разбор` - see below. Kind `review` -
   by `references/review-subagent.md`.
4. **Close the substep:**
   - Step 6 is fully done, including the checker (item 9);
   - run the command from the field «Чекпоинт» of the substep and compare the output with
     the expected output. If they do not agree -> the substep is not closed:
     «Итоговый результат» is not reached, go back to Step 5;
   - in the field «Сделано» of the substep - 1-3 lines: what is done; the checkpoint
     output; compilation and representative test (result); `MR`; the line of the checker
     (`проверка: ...`, Step 6 item 9). Do not keep a separate section «Проверки» for a
     substep;
   - the status of the substep in the table - `done`;
   - make a commit of the files of the substep and of the unit card:
     `git commit -m "<по конвенции проекта> M-<nnn> S-<nn>"`. Write the hash into the column «Коммит».
   Do not write anything into the migration map after a substep. Do it one time, at the end
   of the chat.
5. **Decide if you continue** (check after EACH closed substep, use the first matching
   line):

   | What you see | What you do |
   |--------------|-------------|
   | the substep is not closed or `blocked` | Stop the chat |
   | all substeps are `done` | «Конец юнита» (below) |
   | `scope: core`, and the next substep is not `разбор`, `env` or `core` | Stop the chat: the other substeps wait for the full migration |
   | else | Go back to item 2 - the next substep, in this same chat. Do not go to a new chat. «контекст кончается» is not a reason: it compresses itself |

   «Подшаг не закрыт» means only that you physically cannot work: the project does not
   compile after 3 attempts, or the test is red because of the migration after 3 attempts.
   These are not reasons: something is not clear, the documentation is not sufficient, there
   is no matcher. Postpone such a place («Если упёрся») and close the substep.

6. **Stop the chat (the unit is not finished - only for a reason from the table above).**
   The unit stays `in-progress` in the unit card and in the table of the migration map. Add:
   - a line to the table «Чаты» of the unit card (date, which substeps are done, which
     substep is next);
   - to section «8. Что уже изменилось» of the migration map - one line for each
     replacement of this chat;
   - one line to the log of the migration map.
   Make a commit of the migration map and the unit card. Then do Step 8: in the summary,
   show the done substeps, the next substep and how many substeps stay.
7. **End of the unit («Конец юнита»).** Run ALL lines of the table «Чекпоинты юнита». For
   each line, write into the column «Итог» the command output and `сошлось` / `не сошлось`.
   - All agree -> `status: done` in the unit card and in the migration map, section 8 of
     the migration map, log, commit (Step 7).
   - One or more do not agree -> the unit is NOT `done`. For each checkpoint that does not
     agree, add a substep (the rules are below) and do it. Do it in this chat if the stop
     condition did not occur yet. Else do it in the next chat. After the added substeps, run
     all checkpoints again.

**Substep `разбор` (always `S-01`).** The code does not change. You do not need the
documentation. Run both search commands from the section «Разбор технологии» and compare the
output with the table of consumers:
- the file is in the output, but not in the table (and it is not a step class from the plan
  and not a postponed file) -> add a line to the table and a substep `usage` for it;
- the file is in the table, but not in the output (removed, already moved) -> mark the line
  `уже нет`. Remove the file from the list of its substep. If no files stay in the substep ->
  the status of the substep is `done` with the mark `не нужен`;
- for 2-3 consumers of each access method, look which actions they do (grep in the file, do
  not read it in full). If the action is not in the column «Какие действия делает», or the
  substeps `core` have no method for it -> add the action to the table and a method to
  «Что сделать» of the substep `core`.
Write into «Сделано»: how many consumers the unit card had, how many it has now, what you
added.

**Adding substeps («Дописывание подшагов»).** You can add substeps to the unit card only in
three cases: in the substep `разбор`; for findings of the substep `review`; for a checkpoint
of the unit that does not agree. Rules:
- the kind is `usage` (move a file to the step class), `fix` (fix a finding) or `cleanup`
  (remove the old code that stays);
- add a line to the table «Подшаги» and a section of the substep in the same format as the
  other substeps:
  - files (not more than 3);
  - numbered actions with names of classes and methods;
  - «Итоговый результат» - a fact that you can check;
  - «Чекпоинт» - one command and the expected output.
  Do not write the words «доработать», «привести в порядок», «при необходимости»;
- the number is the next free `S-<nn>`. The place in the table: substeps from `разбора` -
  before the first `cleanup`; other substeps - at the end;
- only files and findings of THIS technology. A different technology or a change of the
  project layers -> not a substep, but an item in «Входящие» of the migration map.
