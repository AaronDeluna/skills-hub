---
name: orchestrator
description: 'The single entry point for the migration of a test-automation project to the PVATF framework. It finds the state of the migration (is there a map, which unit is next) and calls the necessary skill: the build of the migration map (migration-map), the execution of one work unit (migration-step) or the check of the migration result (migration-review). Use it at the START OF EACH chat about the migration: when the human asks «мигрируй проект на PVATF», «начни миграцию», «продолжи миграцию», «что дальше по миграции», «покажи статус миграции», «сделай следующий шаг миграции», «проверь миграцию», «как прошла миграция», «проверь разметку», «разметь тесты», or any other work to move the project to PVATF and to mark up its tests.'
---

**Language.** These instructions are in English. Write everything for the human in Russian:
messages, questions, reports, the map, unit cards, notes and commit messages. Copy every
template exactly as it is shown, with its Russian headings and field names.

# Migration orchestrator for PVATF

The migration is divided into units. All the state is in the files `.gigacode/data/migration/`.
You do not migrate code and you do not make the map. Your work:
- find what the human wants;
- get the next action from the script;
- start ONE skill;
- give a short report.

First, read `references/core-rules.md`: the common rules of the migration.

**The scripts of this skill are in `.gigacode/skills/orchestrator/scripts/`.** The commands below are ready:
copy them and run them as they are, from the root of the migrated project (where `.gigacode/` is).
You must have Java 11+. If the script is not at this path (the skills are installed in a different
place) -> find it one time: `find . ~/.gigacode -path "*orchestrator/scripts/*.java" 2>/dev/null | head -3`.
Then use the directory that you found. If the script stops with an error -> show the error in the chat.
Then do the same work manually with commands, as this skill describes. Do not skip the script silently.

## Step 1 - What the human wants

Use the first row from the top that applies:

| Request | What you do |
|---------|-------------|
| show the status, «что сделано» | `references/status.md`. Do not start skills |
| compress the map, «карта разрослась» | `references/compress.md`. Do not start skills |
| move tests from a different (old) project to this project | Say: «Перенос из старого проекта в новый пока не поддерживается. Эти скиллы мигрируют проект на месте: целиком или только ядро». Do nothing more |
| check or add the markup of the tests («проверь разметку», «разметь тесты», «поставь разметку») | `references/markup.md`. Do not start the migration skills. Step 2 is not necessary |
| check the migration («как прошла миграция») | Start `migration-review`. The map is not necessary. Give the named old libraries word for word |
| only the core / full migration («тесты не трогай», «теперь переводи тесты») | `references/scope.md`, then Step 2 |
| the project changed much, the map is old | Start `migration-map`: update mode (Stage 6) |
| who does the substeps: «подшаги делай сабагентами», «режим менеджера» / «подшаги делай сам», «без сабагентов» | If there is no map -> give the request to `migration-map`. If there is a map -> in section 1 of the map, replace the line with `- Режим исполнения: менеджер · основание: попросил человек` (or `сам`). Tell the human that the mode is changed. Then Step 2, if the human asked for more |
| answers to the questions of the map | `references/questions.md`, item 2 |
| all other requests («мигрируй», «продолжи», «сделай M-012», «с M-001 по M-003») | Step 2 |

Write out from the request and give forward word for word:
- the named technologies and the paths to the example project or to the framework sources
  (`migration-map` gets them);
- the named unit, range or list (the script in Step 2 gets them).

## Step 2 - Ask the script what to do

```
java -Dfile.encoding=UTF-8 .gigacode/skills/orchestrator/scripts/NextAction.java [M-012 | M-001..M-003 | M-001,M-004]
```

Give the argument only if the human named a unit, a range or a list. The script reads the map and
writes `ДЕЙСТВИЕ:` and `ПОЧЕМУ:`. Also, the script installs the kit agents (`pvatf-*`) into
`.gigacode/agents/` of the project, if they are not there or if they are old.
**This step is mandatory in each chat:** without the script output, do not start skills.
Show the two output lines to the human word for word. Do exactly what the script said.
Do not select the unit yourself:

| ДЕЙСТВИЕ | What you do |
|----------|-------------|
| `агенты установлены` | The script wrote the kit agents to `.gigacode/agents/`. Show the two output lines and say: «Агенты миграции установлены или обновлены. Перезапустите GigaCode (выйдите и запустите заново) и введите, чтобы продолжить с того же места: `/orchestrator <запрос человека дословно>`». In place of `<запрос человека дословно>`, put the text that the human wrote after `/orchestrator` in this message, without changes. Do not start skills. Do not copy the agents yourself and do not check `.gigacode/agents/`: the script already compared them with the installed agents and wrote only the new or changed agents |
| `migration-map` | Start `migration-map`. Give it the technologies, the paths and the answers to the questions, if there are answers |
| `одобрение карты` | Show the summary of the map and ask «Карту утверждаем? да/нет». If «Да» -> write `map_status: approved` in the header of the map. If the human gives changes -> `migration-map`, Stage 6 |
| `вопросы` | `references/questions.md`. Do not start units |
| `карта повреждена` | Show the human the reason from `ПОЧЕМУ` word for word. Do not start skills: with a damaged unit table, you cannot know what is done |
| `migration-step M-<nnn>` | Start `migration-step` for this unit |
| `migration-step пачка: ...` | Start `migration-step` ONE time. Give it «пачка: <ID через запятую>» |
| `нельзя`, `нечего делать` | Tell the human the reason from `ПОЧЕМУ`. Do not start skills |
| `заблокировано` | Show the blockers: the section «Блокер» of the `blocked` cards and the lines `решить человеку` (`grep -n "решить человеку" .gigacode/data/migration/MIGRATION-MAP.md`) |
| `ядро готово` | Say: the core is migrated, the tests are not changed; to continue, the human must ask for the full migration |
| `migration-review` | Start `migration-review` |
| `проверка не сходится` | Show the summary of the last round from `MIGRATION-REVIEW.md`. Ask the human to look at the findings that repeat. Start a new round only if the human asks for it directly |
| `финал` | `references/final.md` |

If there is a line `ЗАМЕТКА:` -> add its meaning to the final answer. If the script stops with an error or the map cannot be read ->
tell the human exactly what the script wrote. Do not analyze the unit table yourself.

## Step 3 - Start one skill and wait until it ends

Call the selected skill with the skill call mechanism. From this moment, work by the SKILL.md
of that skill: its rules are more important than this file. When the skill ends, do not start
a second skill in this chat.

## Final answer to the human

Make it short:
- what was the input and which skill you started;
- what the skill did (the map stage / the unit and its status);
- the progress: `done` X of N units;
- what the human must do (questions, lines `решить человеку`, push - you do not do it without permission);
- what is next: **«Откройте новый чат и напишите: `/orchestrator Продолжи миграцию`»**.
