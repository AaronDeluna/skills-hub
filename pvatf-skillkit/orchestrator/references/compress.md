# Map compression

Part of the skill `orchestrator`. Open this file only when SKILL.md sends you here.

The map becomes larger with each unit and uses much context. When the human asks, move the data
that is no longer in use from the map to the archive: the folder `.gigacode/data/migration/archive/`.
Do not erase anything: move all of it to the file `archive/MAP-ARCHIVE.md` (add it at the end, with the date).
Do not change the project code and the unit cards.

Do not compress if there is a unit `in-progress`: first, that unit must be complete.

What goes to the archive (word for word, as it was in the map):

| Map section | What goes to the archive | What stays in the map |
|--------------|--------------------|----------------------|
| 4. Юниты работ | the unit lines with the status `done` | the lines `todo`, `in-progress`, `blocked`; in the line «В архиве» above the table - the ranges of the removed units (`M-001..M-040, M-043`) |
| 5. Входящие | the items that are already changed into units or into questions | the items that nobody analyzed |
| 6. Открытые вопросы | the questions that have an answer | the questions without an answer |
| 7. Журнал сессий | all records, except the last 5 | the last 5 records |
| report `MIGRATION-REVIEW.md` | all check rounds, except the last round | the last round |

What NEVER goes to the archive (the next units and the check use these items):
- the header;
- sections 0-3 (passport, matrix `G`, target picture `T`, `L`, architecture);
- section 8 «Что уже изменилось»;
- the file `ARCHITECTURE.md`;
- the doc notes `doc-notes/`;
- the cards `units/`.

Order:
(1) `mkdir -p .gigacode/data/migration/archive`;
(2) add the data that you move to the end of `archive/MAP-ARCHIVE.md`, under the heading
`## Сжатие <ГГГГ-ММ-ДД>`, with subheadings by sections;
(3) only after this, remove the moved data from the map;
(4) add one line to the log of the map: «карта сжата, в архив ушло: юнитов <n>, вопросов <n>, записей журнала <n>»;
(5) tell the human how many lines the map had before and how many lines it has now (`wc -l`).

**A unit from the line «В архиве» is `done`.** This applies to the check «Зависит от» and to the
progress count in the status. The number of a new unit must be larger than all numbers in the table
and in the line «В архиве».

If you need old data (how a question was answered, what was in the log, details of a done unit)
-> open `archive/MAP-ARCHIVE.md` or the unit card `units/M-<nnn>.md` and find the data
with `grep`. Do not read the full archive.

Do not start the compression yourself. But if the map has more than 600 lines (`wc -l`), add one sentence to the final
answer: «Карта выросла до <n> строк. Чтобы она занимала меньше контекста,
напишите: сожми карту».
