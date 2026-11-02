# Documentation subagent (for migration-step)

You need it in Step 3 and when there are compilation errors in Step 6. This file is only about the subagents
«документация» and «примеры»: they get information and do not change code. The other subagents
of the executor and their permissions are in `SKILL.md` (main rule 12) and in their files: «проверяющий» -
`references/check.md`, «ревью» - `references/review-subagent.md`, «исполнитель подшага» -
`references/manager.md`. All of them are mandatory where the skill names them.

## How the documentation works (you must understand this)

The framework documentation is in a **vector database**. The tool `get_pv_at_doc` takes
a text query and returns documentation parts that are similar to this query. The database itself
has no table of contents. The list of documentation sections is in `references/frame-topics.md`.
Thus:
- the same question in different words returns DIFFERENT parts;
- one wording can give nothing, although the documentation has the answer;
- you must ask a question with a number of wordings and make the answer from all parts.

The subagent does this work. Your task is to give it specific questions and to write down the answer.

## Mandatory requirement

Each access to the framework documentation (the tool `get_pv_at_doc`) goes **ONLY
through a subagent**. Do NOT call this tool yourself, in your own context: this is a **violation
of the protocol**. The reason: each question needs a number of queries, and the answers are large. If
you read them yourself, the context ends before the work ends. The subagent makes the queries in its own context and
returns to you only a short answer by the template.

Agents often try to skip this rule («быстрее сам», «один вопрос»). Do not skip it.

The only exception: the tool that starts subagents (Task/Agent) is physically absent in
your environment, OR the subagent answered that the documentation tool is not available to it. Only
then call `get_pv_at_doc` yourself:
- follow the instruction from `.gigacode/agents/pvatf-docs.md` (a number of
  wordings for each question);
- immediately write the necessary data to the doc notes;
- write clearly in the log of the map/card «сабагенты недоступны, документация прочитана напрямую».

There are no other exceptions.

## Doc notes first, then the subagent («Сначала конспект, потом сабагент»)

All the data that the subagent already got is in the doc notes:
`.gigacode/data/migration/doc-notes/<технология>.md` (general data about the framework - `doc-notes/common.md`).
One record of the doc notes = one question and its answer, with an ID of the form `D-<tech>-<n>` (`D-rest-3`).

The order is always the same. **Never start the documentation subagent without step 1**. If you do,
it studies again what is already studied:
1. For EACH question, search the doc notes with the script. Use two sets of words:
   - the words of the question;
   - the words of the documentation (the name of a framework class or service, the section, the keywords
     from the second line of the doc notes).

   Latin words give more reliable results:
   ```
   java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/Notes.java find <tech> <слова>
   java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/Notes.java show <D-id>
   ```
   (`Notes.java list <tech>` - the table of contents of all the doc notes, one line for each record.)
   If you found a record with the status `найден` about the same thing -> use it, do NOT start the subagent.
2. If you found nothing, or the record is `найден частично` or `НЕТ В ДОКЕ` -> start the subagent with this
   question. In the task, in the line «Уже есть в конспекте», put the output of `Notes.java find`: what
   is already known and which wordings gave nothing. Then the subagent asks DIFFERENTLY and does not
   repeat what is already found.
3. IMMEDIATELY write the answer of the subagent to the doc notes as a new record (the record template is below), with
   all the query wordings. Then work by the record.
4. A record with the status `НЕТ В ДОКЕ` that has less than 8 wordings is not a final result: start
   the subagent again and give it the wordings that were already tried. If there are 8 or more wordings and the status is
   still `НЕТ В ДОКЕ` -> the documentation does not know this. Do not find an answer yourself and do not go into jar files.
   Go down the ladder of sources (section 2 of this file): example project, framework sources,
   then the place is postponed (the executor does not ask a question to the human).
   (Technologies about which the documentation has no data at all do not go into units: the map gives
   them the decision `keep`, and they stay on the old implementation.)

## How to write the questions

- **Specific and about one thing.** Not «как работает Kafka», but «как отправить сообщение в топик»,
  «как прочитать сообщение из топика и проверить его», «какая зависимость нужна для модуля
  Kafka», «как настроить подключение к брокеру (адрес, сертификаты)».
- **About the action, not about the old class.** The documentation does not know your old classes. Not
  «чем заменить KafkaHelper», but «как <то, что делает KafkaHelper>» - for example «как дождаться
  сообщения в топике по ключу».
- **Ask about the configuration in a separate question:** «как сконфигурировать ...», «какие параметры ...»,
  «в каком файле задаётся ...».
- **Give the anchor and the keywords.** Each technology in the framework has its own service (`RestService`,
  `DatabaseService`, `KafkaService` ...). The service name is the best first query: for it, the database
  returns parts that show which words the documentation uses. In the task, write
  «Якорь технологии» from `references/frame-topics.md`. If the doc notes of the technology already have the line
  «Ключевые слова» -> write it in the task. Then the subagent skips the anchor query.
- **Write the questions with the words of the documentation, not with your own words.** The doc notes can
  already have keywords (names of classes and methods). Then use them in the text of the question: not «как прочитать
  сообщение из очереди», but «как через `KafkaConsumerClient` прочитать запись из топика».
- **Give the documentation section.** Before you start the agent, open
  `references/frame-topics.md`, find the section of your technology and write its name in the task line
  «Раздел документации» character for character. If there is no section, write `нет в списке`.
- Give the technology name as the project uses it, AND a general word (for example: «Kafka,
  брокер сообщений»; «PostgreSQL, база данных»; «OpenShift, контейнерная платформа»).

Limit for one start of the subagent: max 5 questions. If there are more, do a number of starts, one after the other.

## Task for the agent `pvatf-docs` (replace <...>, do not add anything more)

How to search the documentation and how to answer is written in the agent itself
(`.gigacode/agents/pvatf-docs.md`). You give only the task. How to start an agent by
name - `references/core-rules.md`, rule 7.

```
Технология: <метка и обычное название, напр. kafka - Kafka, брокер сообщений>
Раздел документации: <название из frame-topics.md, напр. Работа с Kafka; или: нет в списке>
Вопросы:
1. <вопрос>
2. <вопрос>
Якорь технологии: <слово-якорь из frame-topics.md, напр. KafkaService; или: нет>
Ключевые слова из прошлых ответов документации: <слова из строки «Ключевые слова» конспекта; или: нет>
Формулировки, которые уже пробовали и они НИЧЕГО не дали (не повторяй их): <список или: нет>
Уже есть в конспекте (это не ищи заново, ищи только недостающее): <вывод Notes.java find по этим вопросам; или: нет>
```

The answer of the agent: blocks `### Вопрос <номер>: ...` with the fields `Статус`, `Что использовать`, `Как
подключить`, `Как настроить`, `Пример из документации`, `Условия и ограничения`, `Чего не
хватило`, `Формулировки запросов`, and at the end the block `### Ключевые слова документации`.

## Template of a doc notes record

The file is `.gigacode/data/migration/doc-notes/<технология>.md`. The first line of the file:
`# Конспект документации PVATF: <технология>`. The second line:
`Ключевые слова: <слова через запятую>`. This is the documentation dictionary for the technology (names
of classes, methods, settings, headings). Take it from the block «Ключевые слова документации» in the
answer of the subagent. After each start, add the new words to this same line. Only add records to the end. The number
`<n>` is the next number in order in this file.

```markdown
### D-<tech>-<n> · <вопрос>
- Статус: найден | найден частично | НЕТ В ДОКЕ
- Что использовать: <...>
- Как подключить: <...>
- Как настроить: <...>
- Пример:
- Условия и ограничения: <...>
- Чего не хватило: <...>
- Формулировки запросов: «<...>» - дала ответ; «<...>» - пусто
- Записано: <ГГГГ-ММ-ДД> · <этап карты или юнит M-nnn>
```

## What to do with the answer

- `найден` -> write the record to the doc notes and use it. The record ID is the documentation basis.
- `найден частично` -> write it. For the missing data, ask the subagent a separate, more
  narrow question.
- `НЕТ В ДОКЕ` -> write it (with the wordings!) and act by item 4 of the section «Сначала конспект»
  (the section "Doc notes first, then the subagent").
- `MCP НЕДОСТУПЕН` -> STOP, tell the human.
- If the answer is not by the template or has no list of wordings -> do not use it. Start the subagent again
  with the same task.

# 2. When the documentation is not sufficient (ladder of sources)

The documentation from MCP is the first and the main source. But it can be incomplete: a process is not described
to the end, or it is not clear how to call or configure something. Then do NOT invent and do NOT stop the work.
Go down the ladder from the top:

| Level | What you do | Is the human necessary |
|---------|-------------|---------------|
| 1 | The documentation subagent, as usual (up to 8 wordings for each question - the rules above) | no |
| 2 | If the line «Исходники фрейма» in the passport is filled -> FIRST, use the documentation inside the sources: `find <исходники> -path "*docs*" -name "*.md"`, then `grep -rln "<ключевые слова>" <исходники>/docs`, and read the found parts yourself (this is the same documentation, but in files). If you found nothing, start the examples subagent on this path: the tests and examples of the technology module, then the classes `.java` | no |
| 3 | If the line «Проект-пример» in the map passport is filled -> start the examples subagent on this path (the task is below) | no |
| 3a | If the human gave in the chat a path to a documentation file or folder -> read it yourself (`grep`, then the necessary parts). Write the found data as a doc notes record with the source `файл <путь>`. Write the path to the folder `docs` of the sources in the passport, near «Исходники фрейма» | no |
| 4 | If there is still no answer -> the executor (`migration-step`) does NOT ask. It postpones the place (`references/stuck.md`, «Если упёрся», method 2) and continues the work. The question text below is only for the map stage (`migration-map`), when questions are still asked | no |

Skip levels 2 and 3 if the related line of the passport is empty (`-`).

**The paths come from the map passport.** `migration-map` finds the framework sources and the example project in
Stage 1. Do not search for them on the disk yourself. PROHIBITED: `~/.m2`, `.gradle`, unpacking and decompiling of `.jar`.
If the passport line «Исходники фрейма» is empty, and the map was made before this rule ->
do item 6 of Stage 1 of the skill `migration-map` one time (search for git clones and `git pull`).
Then write the path in the passport.

## Text of the question to the human (level 4, copy it, replace <...>)

Write politely, use the formal «вы», do not blame.

```
В документации фрейма не удалось найти: <что именно непонятно, 1-2 строки> (технология <метка>).
Где это нужно в проекте: <путь к файлу>:<строка>.
Что уже сделано: <сколько формулировок запроса; какие ключевые слова; смотрел ли проект-пример>.
Как поступим? Выберите вариант:
1) отвечу сам - напишу, как это делается;
2) дам полный путь к драфт-проекту Platform V (проект-пример) - там можно посмотреть, как это сделано.
```

Write this question in section 6 of the map (these two options go in the field «Варианты ответа»). What
to do with the answer:
- `1` and an explanation -> write the explanation of the human as a doc notes record with the status `найден` and
  the source `человек`. Work by this record;
- `2` and a path -> write the path in the map passport (line «Проект-пример»): the next chats also
  use it. Start the examples subagent. If the example has no answer -> ask the question
  again, with only option 1;
- the human wrote «не мигрировать это» / «оставить как есть» -> mark this place in the map
  as «остаётся как есть». Do not include it in units;
- the human gave a path to the framework sources -> write it in the passport line «Исходники фрейма» and
  start the examples subagent on it.

## Task for the agent `pvatf-examples` (replace <...>, do not add anything more)

How to search and how to answer is written in the agent itself
(`.gigacode/agents/pvatf-examples.md`). How to start an agent by name -
`references/core-rules.md`, rule 7.

```
Путь: <полный путь из паспорта карты>
Что это: <проект-пример (драфт) | исходники фрейма>
Технология: <метка и обычное название>
Вопросы:
1. <вопрос>
2. <вопрос>
```

The answer of the agent: blocks `### Вопрос <номер>: ...` with the fields `Статус` (найден | найден частично |
НЕТ В ПРИМЕРЕ), `Что использовать`, `Как подключить`, `Как настроить`, `Пример`, `Откуда`,
`Чего не хватило`, `Какие слова искал`.

Write the answer of the examples subagent to the doc notes as the same kind of record `D-<tech>-<n>` as the answers
of the documentation, with an additional line `- Источник: проект-пример <путь к файлу>:<строки>`
(or `исходники фрейма ...`). Such a record is a full documentation basis. If the documentation and
the example do not agree, the documentation is correct. Write the difference in the same record.
