# Subagents for building the migration map (for migration-map)

This is the full list of map subagents. Do not make up other subagents. If this file names a
subagent for a work, the subagent is MANDATORY: you do not do this work yourself
(`references/core-rules.md`, rule 7).

| Subagent | When | Mandatory | Prompt or agent |
|----------|-------|------------|--------|
| **Documentation** (answers to questions) | Stages 1, 3, 4 - each access to the framework documentation | always | agent `pvatf-docs`, task - this file, section 1 |
| **Project technologies** | Stage 2, item 0 - which technologies the project uses | if the human did not name the technologies | this file |
| **Module inventory** | Stage 2 - counts on the module sources | always | this file, section 2 |
| **Examples** (framework sources or the example project) | Stages 3, 4 - when the documentation did not give enough | if the paths are in the map passport (Stage 1, item 6 finds them) | agent `pvatf-examples`, task - this file, section 4 |
| **Technology analysis** | Stage 5 - consumers of the technology, before the unit card | always, for each technology `migrate` | `references/card-subagents.md` |
| **Card writer** | Stage 5 - writes the unit card of the unit `tech` (exactly one file) | always | `references/card-subagents.md` |
| **Card checker** | Stage 5 - after `Card.java` | always | `references/card-subagents.md` |

You do these tasks yourself: the map passport, the connection register, the matrix, the
architecture plan, the unit table, and the start of the subagents in the correct order. The
card writer writes the `tech` cards. You do not write them.

# 1. Documentation subagent

## How the documentation works (you must understand this)

The framework documentation is in a **vector database**. The tool `get_pv_at_doc` takes a text
query. It returns documentation pieces that are similar to this query. The database has no
table of contents. The list of documentation sections is in `references/frame-topics.md`.
Thus:
- the same question in different words returns DIFFERENT pieces;
- one wording can return nothing, although the answer is in the documentation;
- you must ask the question in a number of wordings and make the answer from all pieces.

The subagent does this work. Your task: give the subagent specific questions and write down
the answer.

## Mandatory requirement

Each access to the framework documentation (the tool `get_pv_at_doc`) goes **ONLY through
the subagent**. Do NOT call this tool yourself, in your own context. This is a **protocol
violation**. The reason: each question needs a number of queries, and the answers are large.
If you read them yourself, your context ends before the work ends. The subagent makes the
queries in its own context. It returns to you only a short answer by the template.

Agents often try to skip this rule («быстрее сам», «один вопрос»). Do not skip it.

There is only one exception. The exception applies when one of these conditions is true:
- the tool that starts subagents (Task/Agent) is physically not in your environment;
- OR the subagent answered that the documentation tool is not available to it.

Only then call `get_pv_at_doc` yourself. Follow the instructions in
`.gigacode/agents/pvatf-docs.md` (a number of wordings for each question). Immediately write
the necessary data into the doc notes. Write clearly in the log of the map or the unit card:
«сабагенты недоступны, документация прочитана напрямую». There are no other exceptions.

## First the doc notes, then the subagent («Сначала конспект, потом сабагент»)

All data that the subagent already got is in the doc notes:
`.gigacode/data/migration/doc-notes/<технология>.md` (general data about the framework -
`doc-notes/common.md`). One doc notes record = one question and its answer, with an ID of the
form `D-<tech>-<n>` (`D-rest-3`).

The order is always the same. **Never start the documentation subagent without step 1.** If
you do, the subagent studies again what is already studied:
1. For EACH question, search the doc notes with the script. Use two sets of words:
   - the words of the question;
   - the words of the documentation (the name of a framework class or service, a section,
     keywords from the second line of the doc notes).

   A search in Latin letters is more reliable:
   ```
   java -Dfile.encoding=UTF-8 .gigacode/skills/migration-map/scripts/Notes.java find <tech> <слова>
   java -Dfile.encoding=UTF-8 .gigacode/skills/migration-map/scripts/Notes.java show <D-id>
   ```
   (`Notes.java list <tech>` - the table of contents of all the doc notes, one line for each record.)
   If you found a record with the status `найден`, and it is about the same thing -> use it. Do NOT start the subagent.
2. If you found nothing, or the record is `найден частично` or `НЕТ В ДОКЕ` -> start the
   subagent with this question. In the task, in the line «Уже есть в конспекте», put the output
   of `Notes.java find`. It tells what is already known and which wordings gave nothing. Then
   the subagent asks in a DIFFERENT way and does not repeat the found data.
3. IMMEDIATELY write the subagent answer into the doc notes as a new record (the record
   template is below). Include all query wordings. Then work from the record.
4. A record with the status `НЕТ В ДОКЕ` and fewer than 8 wordings is not a final result: start
   the subagent again and give it the wordings that it already tried. If there are 8 or more
   wordings and the status is still `НЕТ В ДОКЕ` -> the documentation does not know this. Do not
   find an answer yourself. Do not look into a jar. Then there are two cases:
   - the documentation says nothing about the technology AT ALL (no module, no section) -> the
     technology gets the decision `keep`: it is not migrated and stays on the old
     implementation. A question to the human is not necessary;
   - the technology is in the framework, but there is no answer to one specific question.
     Examples: what replaces a specific pattern, how to configure it, the process is not fully
     described. -> Go down the source ladder (section 4 of this file): the example project, the
     framework sources, then a question to the human with options. In the matrix, keep
     `НЕТ В ДОКЕ` for now.

## How to write the questions

- **Specific and about one thing.** Not «как работает Kafka», but «как отправить сообщение в топик»,
  «как прочитать сообщение из топика и проверить его», «какая зависимость нужна для модуля
  Kafka», «как настроить подключение к брокеру (адрес, сертификаты)».
- **About the action, not about the old class.** The documentation does not know your old
  classes. Not «чем заменить KafkaHelper», but «как <то, что делает KafkaHelper>» - for example
  «как дождаться
  сообщения в топике по ключу».
- **Ask about the configuration in a separate question:** «как сконфигурировать ...», «какие параметры ...»,
  «в каком файле задаётся ...».
- **Give the anchor and the keywords.** Each technology in the framework has its own service
  (`RestService`, `DatabaseService`, `KafkaService` ...). The service name is the best first
  query. For this name, the database returns pieces that show the words of the documentation.
  In the task, write the «Якорь технологии» from `references/frame-topics.md`. If the doc notes
  of the technology already have the line «Ключевые слова» -> write it into the task. Then the
  subagent skips the anchor query.
- **Write the questions in the words of the documentation, not in your own words.** If the doc
  notes already have keywords (class names and method names), use them in the question text:
  not «как прочитать
  сообщение из очереди», but «как через `KafkaConsumerClient` прочитать запись из топика».
- **Name the documentation section.** Before you start the agent, open
  `references/frame-topics.md`. Find the section of your technology. Write its name into the
  task line «Раздел документации» character for character. If there is no section, write `нет в списке`.
- Name the technology with its name in the project AND with a general word (for example: «Kafka,
  брокер сообщений»; «PostgreSQL, база данных»; «OpenShift, контейнерная платформа»).

The limit for one subagent run: max 5 questions. If you have more, do a number of runs one after the other.

## Task for the agent `pvatf-docs` (replace <...>, add nothing else)

The agent itself contains the instructions how to search the documentation and how to answer
(`.gigacode/agents/pvatf-docs.md`). You give only the task. How to start an agent by name -
`references/core-rules.md`, rule 7.

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

The agent answer - blocks `### Вопрос <номер>: ...` with the fields `Статус`, `Что использовать`, `Как
подключить`, `Как настроить`, `Пример из документации`, `Условия и ограничения`, `Чего не
хватило`, `Формулировки запросов`, and at the end the block `### Ключевые слова документации`.

## Doc notes record template

The file `.gigacode/data/migration/doc-notes/<технология>.md`. The first line of the file:
`# Конспект документации PVATF: <технология>`. The second line:
`Ключевые слова: <слова через запятую>`. This line is the documentation vocabulary for the
technology (names of classes, methods, settings, headings). Take it from the block «Ключевые слова документации» in the subagent answer. After each run, add the new words to this same
line. Only add records at the end of the file. The number
`<n>` is the next number in sequence in this file.

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

- `найден` -> write the record into the doc notes and use it. The record ID is the doc basis.
- `найден частично` -> write the record. For the missing part, ask the subagent a separate,
  narrower question.
- `НЕТ В ДОКЕ` -> write the record (with the wordings!) and do item 4 of the section «Сначала конспект» (the section "First the doc notes, then the subagent" above).
- `MCP НЕДОСТУПЕН` -> stop, tell the human.
- If the answer is not by the template, or has no list of wordings -> do not use it. Start the
  subagent again with the same task.

# 2. Module inventory subagent

## Mandatory requirement

The counts on the module sources (Stage 2, item 2) go **only through subagents**. The grep
output for a large module is very large. It must not come to you. You need only the short
result. There is only one exception: the subagent tool is physically not available. Then
count yourself by `references/inventory-guide.md`, one module at a time, and write this in the
map log.

## How many subagents

```
число сабагентов = min(3, число модулей)
```

Divide the modules among the subagents as equally as possible, without overlaps. Together the
subagents must cover ALL modules. If the project has one module, use one subagent.

## Prompt (copy word for word, replace <...>)

```
Ты делаешь инвентаризацию исходников для СПИСКА модулей одного проекта. Только считаешь и
ищешь командами. Не меняй файлы. Не читай target/, build/, .gradle/, .idea/, *.jar, *.class.
Не открывай файлы целиком, кроме случаев, когда это прямо сказано. Верни ТОЛЬКО заполненные
шаблоны (по одному на модуль), без рассуждений и без сырого вывода команд.

Проект: <абсолютный путь к корню проекта>
Модули (обработай КАЖДЫЙ): <модуль: путь к его каталогу src>, <модуль: путь>

Для КАЖДОГО модуля (SRC - его каталог src) выполни команды:

1. find SRC \( -name "*.java" -o -name "*.kt" \) | wc -l
2. find SRC \( -name "*.java" -o -name "*.kt" \) -exec cat {} + | wc -l
3. grep -rE "^\s*@Test\b" --include=*.java --include=*.kt SRC | wc -l
4. grep -rhoE "^import (static )?[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+" --include=*.java --include=*.kt SRC | sed -E "s/^import (static )?//" | sort | uniq -c | sort -rn | head -40
5. grep -rhoE "(extends|implements) [A-Z][A-Za-z0-9_<>, ]+" --include=*.java SRC | sort | uniq -c | sort -rn | head -30
6. grep -rhoE "^\s*@[A-Z][A-Za-z0-9_]+" --include=*.java --include=*.kt SRC | sed -E "s/^\s+//" | sort | uniq -c | sort -rn | head -30
7. find SRC \( -name "*.java" -o -name "*.kt" \) -exec wc -l {} + | sort -rn | head -15
8. find SRC -path "*resources*" -type f | head -40
9. grep -rlE "^import (static )?(ru\.sber\.qa|io\.perfeccionista)\." --include=*.java --include=*.kt SRC | wc -l
10. find SRC -name "*Utils.java" -o -name "*Helper.java" -o -name "*Wrapper.java" -o -name "Base*.java" -o -name "Abstract*.java" | head -40

Верни на каждый модуль РОВНО такой шаблон (заголовки сохрани):

# Инвентаризация: <модуль>

- Файлов: <n> · Строк: <n> · Тестов (@Test): <n>
- Уже на PVATF файлов: <n>

## Топ импортов (пакет - сколько раз)
- <пакет> - <n>      (JDK-пакеты java.*, javax.* не перечисляй)

## Базовые классы / интерфейсы (имя - сколько наследников)
- <имя> - <n>

## Аннотации (имя - сколько)
- <имя> - <n>

## Большие файлы (путь - строк)
- <путь> - <n>

## Конфиги и ресурсы
- <путь>

## Самописные обёртки и базовые классы (кандидаты в legacy)
- <путь>

## Команды, которые не выполнились
- <номер команды: ошибка>   (если все выполнились - напиши: нет)
```

## What to do with the results

1. Write each template as it is into `.gigacode/data/migration/inventory/<модуль>.md`.
2. **Gate:** there must be a template for EACH module from the map passport. If a template is
   missing - start a subagent again for the missing modules.
3. You select and read the sample files for the matrix (Stage 3) yourself - max 3 for each pattern.

# 3. Project technologies subagent

## When to start it

Stage 2, item 0, **only if the human did not name the technologies**. If the human named them,
the subagent is not necessary: use the list of the human. There is one subagent. Start it one
time for the full project.

## Prompt (copy word for word, replace <...>)

```
Ты определяешь, с какими технологиями работает проект автотестов. Только считаешь и ищешь
командами. Не меняй файлы. Не читай target/, build/, .gradle/, .idea/, *.jar, *.class. Файлы
исходников целиком не открывай. Верни ТОЛЬКО заполненный шаблон отчёта, без рассуждений и
без сырого вывода команд.

Проект: <абсолютный путь к корню проекта>

Выполни команды из корня проекта:

1. find . \( -name pom.xml -o -name "build.gradle" -o -name "build.gradle.kts" -o -name "libs.versions.toml" \) -not -path "*/target/*" -not -path "*/build/*"
2. Для каждого найденного файла сборки:
   grep -hoE "<artifactId>[^<]+</artifactId>|['\"][a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+(:[^'\"]*)?['\"]" <файл> | sort -u
3. grep -rhoE "^import (static )?[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+" --include=*.java --include=*.kt . | sed -E "s/^import (static )?//" | sort | uniq -c | sort -rn | head -80
4. find . -path "*resources*" -type f \( -name "*.properties" -o -name "*.yml" -o -name "*.yaml" -o -name "*.conf" -o -name "*.json" \) -not -path "*/target/*" -not -path "*/build/*" | head -60
5. grep -rhoiE "(jdbc:[a-z0-9]+|kafka|bootstrap\.servers|grpc|graphql|wss?://|openshift|kubernetes|elastic|opensearch|selenide|playwright|appium|rabbit|mq|redis|mongo|s3|ftp|smtp|otel|opentelemetry)" --include=*.properties --include=*.yml --include=*.yaml --include=*.conf . | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn | head -40

По результатам определи технологии. Подсказка, по каким признакам (зависимость или пакет
импорта -> технология):
- io.restassured, okhttp3, org.apache.http, retrofit2, feign, java.net.http -> rest
- java.sql, javax.sql, org.sql2o, org.jooq, org.hibernate, org.springframework.jdbc, jdbc:... -> db (впиши КАКАЯ база: postgresql / oracle / mssql / ... - по драйверу и строке jdbc)
- org.apache.kafka, org.springframework.kafka -> kafka
- io.grpc, com.google.protobuf -> grpc
- graphql -> graphql
- websocket, org.java_websocket -> websocket
- com.codeborne.selenide, org.openqa.selenium -> ui-selenide
- com.microsoft.playwright -> ui-playwright
- io.appium -> appium-android / appium-ios
- io.fabric8, io.kubernetes, openshift -> openshift
- org.opensearch, org.elasticsearch, co.elastic -> opensearch
- org.testcontainers -> testcontainers
- io.qameta.allure -> allure
- org.awaitility -> timeouts
- com.github.tomakehurst.wiremock, org.mockserver -> моки (sbermock)
- io.opentelemetry -> otel
- com.rabbitmq, javax.jms, com.ibm.mq -> очередь, не Kafka (впиши какая)
- org.junit.jupiter -> runner JUnit 5; org.junit (без jupiter) -> runner JUnit 4; org.testng -> runner TestNG; io.cucumber -> runner Cucumber
- org.assertj, org.hamcrest, net.javacrumbs.jsonunit, org.skyscreamer.jsonassert -> проверки (asserts)
Нашёл технологию, которой нет в подсказке, - тоже впиши, своими словами.
Признаков технологии нет - не вписывай её.

Верни РОВНО такой шаблон (заголовки сохрани):

# Технологии проекта

| Метка | Технология (что именно) | Признак: зависимости | Признак: импорты (пакет - сколько раз) | Признак: конфиги | Модули |
|-------|-------------------------|----------------------|-----------------------------------------|------------------|--------|
| <rest> | <REST API, RestAssured> | <io.rest-assured:rest-assured> | <io.restassured - 143> | <-> | <модули, где встречается> |

## Тест-фреймворк
- <JUnit 5 / TestNG / ...> - <признак>

## Библиотеки проверок
- <AssertJ / Hamcrest / JsonUnit / свои классы> - <пакет - сколько раз>

## Пакеты из топа импортов, которые не удалось отнести к технологии
- <пакет - сколько раз>     (JDK-пакеты java.*, javax.* не перечисляй; нет - напиши: нет)

## Команды, которые не выполнились
- <номер команды: ошибка>   (если все выполнились - напиши: нет)
```

## What to do with the report

1. Write the report as it is into `.gigacode/data/migration/inventory/technologies.md`.
2. Each line of the report table -> a line of the table «Технологии проекта» in the map
   passport. Compare the label with `references/frame-topics.md`. Put the lines in the order
   from the rule of Stage 2.
3. Do not discard the «Пакеты, которые не удалось отнести». At Stage 3, each such package must
   go into a line `G` or into «остаётся как есть».
4. If the report is not by the template -> start the subagent again with the same task. Only if
   the subagent call returned an error (not «долго» and not «проще самому») -> show the error in
   the chat, write `сабагент не запустился: <ошибка>` into the map log, and run the prompt
   commands yourself.

# 4. When the documentation did not give enough (the source ladder)

The MCP documentation is the first and main source. But it can be incomplete: the process is
not fully described, or it is not clear how to call or configure something. Then do NOT make
up an answer and do NOT stop the work. Go down the ladder from top to bottom:

| Step | What you do | The human is necessary |
|---------|-------------|---------------|
| 1 | The documentation subagent, as usual (max 8 wordings for each question - see the rules above) | no |
| 2 | **Framework sources** (line of the map passport). FIRST their documentation: `grep -rln "<ключевые слова>" <папка docs из паспорта>`, and read the found pieces yourself. If you found nothing -> the examples subagent on the sources path (task below): tests and examples of the technology module, then the classes themselves | no |
| 3 | **Example project** (line of the map passport) -> the examples subagent on this path | no |
| 4 | If there is still no answer -> a polite question to the human with two options (text below). Until the answer, do not do this part. This is the last case: a question without steps 2 and 3 done (if their paths are in the map passport) is not valid | yes |

Skip steps 2 and 3 only if the line of the map passport is empty (`-`).

**Where to get the sources.** `migration-map` itself finds the paths at Stage 1 (item 6): git
clones with source code on the disk, updated with `git pull`. The sources are a folder with the
`.java` files of the framework. Do not use `~/.m2`, `.gradle`, and do not unpack or decompile
`.jar` files: these are prohibited. Jar files are not sources.

## Text of the question to the human (step 4, copy it, replace <...>)

Write politely, on «вы», without reproach.

```
В документации фрейма не удалось найти: <что именно непонятно, 1-2 строки> (технология <метка>).
Где это нужно в проекте: <путь к файлу>:<строка>.
Что уже сделано: <сколько формулировок запроса к документации; что искал в исходниках фрейма и в проекте-примере - пути и слова>.
Как поступим? Выберите вариант:
1) отвечу сам - напишу, как это делается;
2) дам полный путь к драфт-проекту Platform V (проект-пример) - там можно посмотреть, как это сделано.
```

Write this question into section 6 of the migration map (write these two options into the
field «Варианты ответа»). What to do with the answer:
- `1` and an explanation -> write the explanation of the human as a doc notes record with the
  status `найден` and the source `человек`. Work from this record;
- `2` and a path -> write the path into the map passport (line «Проект-пример»). It is also
  useful in the next chats. Start the examples subagent. If the example has no answer -> ask the
  question again, now only with option 1;
- the human wrote «не мигрировать это» / «оставить как есть» -> mark this part in the
  migration map as «остаётся как есть». Do not include it in the units;
- the human gave the path to the framework sources -> write it into the line of the map passport
  «Исходники фрейма» and start the examples subagent on it.

## Task for the agent `pvatf-examples` (replace <...>, add nothing else)

The agent itself contains the instructions how to search and how to answer
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

The agent answer - blocks `### Вопрос <номер>: ...` with the fields `Статус` (найден | найден частично |
НЕТ В ПРИМЕРЕ), `Что использовать`, `Как подключить`, `Как настроить`, `Пример`, `Откуда`,
`Чего не хватило`, `Какие слова искал`.

Write the answer of the examples subagent into the doc notes as the same kind of record
`D-<tech>-<n>` as the documentation answers. Add one more line: `- Источник: проект-пример <путь к файлу>:<строки>`
(or `исходники фрейма ...`). Such a record is a full doc basis. If the documentation and the
example are different - the documentation is correct. Write the difference into the same record.
