# Open questions to the human

Part of the skill `orchestrator`. Open this file only when SKILL.md sends you here.

1. This rule applies also when the human wrote «продолжи миграцию»: do NOT continue the migration.
   Show the questionnaire. Write politely, use the formal «вы», do not blame. Start with: «Прежде
   чем продолжить миграцию, нужны ваши ответы - в карте остались открытые вопросы:». Then
   write ALL questions from section 6 of the map that have `ответ: -`. Use this template:
   ```
   Q-<n>. <текст вопроса>
   Где это в проекте: <файл>:<строка>
   Варианты ответа:
     1) отвечу сам - напишу, как это делается;
     2) дам полный путь к драфт-проекту Platform V (проект-пример).
   ```
   Take the options from the field «Варианты ответа» of the question in the map. If there is no such field, use these two options.
   End with: «Ответьте, пожалуйста, на каждый вопрос: номер вопроса и вариант».
2. The human answered (in this chat, or in a new chat with the answers):
   - write the answer in section 6 of the map in place of `-`, word for word;
   - if the unit of the question was `blocked` -> change it to `todo` (in the table of
     section 4 and in the card). In the card, add the answer of the human to the section «Блокер»;
   - if the answer has a full path to the example project or to the framework sources -> write it in
     the map passport (line «Проект-пример» or «Исходники фрейма»). Do not go to this path
     yourself: the subagent of the skill that you start examines it;
   - the answer «запусти поиск по документации ещё раз» is also an answer. Write it, and start
     the skill that the question came from: `migration-map` if the map is not complete yet or if the
     question is about `G`/`T`; `migration-step` for the unit if the question is about a unit;
   - if the answer changes the map -> start `migration-map` in update mode (Stage 6) and give it
     the answer. Examples: a different replacement, do not migrate a technology, a new unit is necessary.
3. If the human did not answer all questions -> write the answers that you have, and stop: do not start units.
4. If no questions without an answer are left -> in this chat, run `NextAction.java` again (SKILL.md, Step 2).

Do not answer the questions yourself. Do not decide that a question is «неважным» (not important).
If the path to the draft project is already in the map passport, do not suggest option 2
(the example was already examined). Keep option 1.
