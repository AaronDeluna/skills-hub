# If you are stuck: table of default decisions

This is a part of the skill `migration-step`. The main rules and the reading order are in
`SKILL.md`. «Если упёрся» and «Таблица решений по умолчанию» are in `references/stuck.md`.

**Manager mode (default):** some decisions from this table need a change of the project
code («поправь», «замени», «удали»). The executor does such a decision - as a retry with this
decision (`references/manager.md`, item 8). You yourself change only the unit card and the
migration map.

## If you are stuck («Если упёрся»)

You work without the human: you do not ask questions (rule 2 of the executor in SKILL.md).
You have three methods to continue. Use them in this order:

1. **Decide by the table of default decisions** (below) - it already has decisions for most
   choices.
2. **Postpone the place** - if the table has no decision and the sources have no answer:
   - keep this place in the code as it was (old code that compiles), or do the nearest
     thing that the documentation confirms;
   - add a line to the section «5. Входящие» of the migration map: `решить человеку: <файл>:<строка> - <что
     не сделано> - <что искал: формулировки, источники> - <какое решение предлагаешь>`;
   - in «Сделано» of the substep (or «Что сделано» of the unit): `отложено: <файл>:<строка> - <что>`;
   - close the substep and continue. A postponed place does not make the substep and the
     unit not closed.
3. **Stop** - only if you physically cannot work:
   - the project does not compile after 3 attempts;
   - the representative test is red because of the migration after 3 attempts;
   - the MCP with the documentation is fully not available;
   - git has changes of other people without a commit.
   Then the unit is `in-progress` (or `blocked`). Write an exact description in
   «Где остановился» / «Блокер». Do Step 7 (items 3-4) and Step 8.

**Table of default decisions («Таблица решений по умолчанию»).** If you found your situation
-> do as the table tells, and write one line: «решено по умолчанию: <что> - <почему>».

| Situation | Decision |
|-----------|----------|
| Which addresses, hosts, logins, passwords, tokens, clientId/clientSecret, certificates, topics, groups, namespace, aliases to use for the connection (Kafka, DB, OpenShift, Сбермок, REST) | The same that the project used before. Search in this order until you find them: 1) `CONNECTIONS.md`, the section of the technology; 2) «Данные подключения» in the unit card; 3) old configs and code: `grep -rniE "<слово1>\|<слово2>" --include=*.properties --include=*.yml --include=*.yaml --include=*.conf --include=*.java --include=*.kt --include=pom.xml --include=Jenkinsfile* . \| grep -v "/target/\|/build/\|\.gigacode"`; 4) the old file is already removed - the history of the main branch: `git show <основная ветка>:<путь к файлу>` or `git log --all -p -S "<слово>" \| head -60`. If you found it, add it to `CONNECTIONS.md`. If the value comes from the outside (`${VAR}`, `System.getenv`, a variable in Jenkinsfile), write the same variable into the framework settings, in the way that the documentation gives. If it is nowhere: an optional key - do not write it; a mandatory key - the same environment variable as before, and the line `решить человеку: <ключ> - значения нет в проекте` in «Входящие». Do not ask the human |
| Which certificates to connect and where their password is | The same files that the project connects now: `CONNECTIONS.md`, section «Сертификаты и хранилища ключей». Connect them as the doc notes of the technology tell. The path and the password stay the same |
| How to use the technology now (for example, Сбермок stubs: how to call the stubbed endpoints) | The same way as the project used it before: the same calls, addresses, parameters. Only the mechanism changes to the framework mechanism. A usual REST call of a stub - with the standard REST client of the framework through the base layer `RestSteps`. Control of stubs - with the framework service of this technology, if the project used it |
| The unit card asks for something that the framework cannot do | The documentation is correct: get the same result in the way that the framework can do it. Change the substep in the unit card yourself (what to do, final result, checkpoint) and write why. Do not keep the technology on the old code. Do not set `keep` |
| Before, the response was parsed into a DTO, the DTO went further through the code, then a getter and an assert | Always write the chain again (`MR-41`): the request method returns a validatable framework object, the checks use `.should(...)`, the code passes further the validatable object or one necessary value, remove the response DTO. Add the calling files that break to this substep (or as the next substep `usage`) |
| DTOs, models, Jackson, JAXB, own wrappers around them (`JacksonHelper`); the documentation does not describe deserialization or getting the body as a string | The table in `MR-41` (`references/code-rules.md`): response DTO - remove, checks - `.should(...)`; models of request bodies - keep; wrapper methods for parsing the response - remove; for building bodies - keep while code uses them. If the documentation has no deserialization, this is not a gap: the framework does not need it |
| The documentation says nothing about a library, a driver, annotations, file reading, logging, stands, names of standard keys | The decision from the migration map (the table «Документация молчит» in section 2 / block `T`). If the migration map does not have it: general-purpose libraries (Lombok etc.), the DBMS driver, own Allure annotations, own reading of data files - keep as they are; code without callers - remove; logging - `simplelogger.properties`; standard SSL and client keys - names as in the library; the project has no value - `снаружи: <ПЕРЕМЕННАЯ>` and a line in «Входящие». Do not ask the human |
| No matcher for the check was found (doc notes, subagent, folder `docs` of the framework sources) | A standard JUnit assert (`MR-29`), without `assertAll`; a line in «Входящие». Do not write an own matcher, wrapper or condition class |
| Elements of a JSON array against rows of a DB table, and there is no matcher for the full array | A loop over the rows. In the body - one call `.shouldSoft(...)` with matchers for the element `[i]` directly inside (`MR-48`) |
| The value of a DB cell is compared with the expected value | A matcher of a row or of a table (`DatabaseMatchers`, «значение ячейки равно»). If not found - see the line about the matcher above |
| The documentation is not sufficient, the ladder of sources (`references/doc-subagent.md`, section 2) gave nothing | Postpone the place (method 2) |
| The documentation does not agree with the unit card | The documentation is correct. Do it by the documentation. Write the difference in «Сделано». If the set of files or steps changes - change the substep in the unit card yourself |
| To make the project compile, you must change files that are not in the substep | A mechanical change (import, type name, call) - make it, and add the files to the substep with the mark `добавлен по ходу`. Not mechanical - add a new substep `usage` for these files immediately after the current substep, and do it |
| The substep is larger than the limit | Divide it yourself: do a part, and put the remaining part into a new substep immediately after the current one, in this same chat |
| The representative test was red already BEFORE the migration, and after it, it is red with the same error | Do not fix a cause that is not yours. Take a different test from the files of the substep that is green. If there is no such test - close by compilation, line `решить человеку: тест <...> красный и до миграции` |
| The representative test runs more than 10 minutes | Stop it. Take a different fast test (without waits, UI, containers). If there is no fast test - close by compilation, line `решить человеку: нет быстрого теста для <...>` |
| The representative test does not start because of the environment (no stand, no network, no access) | Do not fake the result. Close by compilation. In «Проверки» - the exact command and the error, line `решить человеку: запустить <команда>` |
| `cleanup`: files outside the substep still refer to legacy | In a unit `tech` - add a substep `usage` for these files before `cleanup`, and do it. In a unit of phase 4 - remove what has no references; the rest - `решить человеку` |
| Which name to give to a class or a method, which package to put it in | By the architecture plan, `MR-40`, `MR-45`. If the plan does not have it - by the pattern of the nearby classes of the same layer |
| Remove an old class that has no references now? | Yes (Step 5, item 6) |
| Somebody already answered this | Section 6 of the migration map or the doc notes: `grep -n "<ключевое слово>" .gigacode/data/migration/MIGRATION-MAP.md .gigacode/data/migration/doc-notes/*.md` |
| The human gave a path to the documentation before | Read it yourself: `grep -rn "<ключевые слова>" <путь>`, then the necessary parts |
| Other tests (not the representative test) failed already BEFORE your changes | Do not fix them. Write it in «Проверки» and add a line in «Входящие» |
| You want to fix something nearby «заодно» | Not permitted. Write a line in «Входящие» - and continue by the unit card |
