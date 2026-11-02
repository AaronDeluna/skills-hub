# Question filter («Фильтр вопросов») - do it BEFORE you ask the human a question

This file is a part of the skill `migration-map`. The general rules are in `references/core-rules.md`. The rules of the migration map and the order of stages are in `SKILL.md`.

A question to the human is the last resort: it stops all of the migration. Most questions that
you want to ask are not really questions. The answer is already in the documentation or in the
project, or the problem does not exist. Before you write a question into section 6 of the
migration map, do the checks in order. The question stays only if it passed ALL checks.

| No. | Check | If «да» |
|---|----------|-----------|
| 1 | **Is this project data?** Stand addresses, hosts, ports, logins, passwords, tokens, clientId/clientSecret, certificates and their passwords (SSL, keystore, truststore), topics, groups, DB schemas, the OpenShift namespace and cluster, Sbermock addresses and credentials, file paths, setting values. | This is NOT a question. The project already works - thus it has this data. Open `CONNECTIONS.md`. If the data is there - take it from there. If not - do step 1а of Stage 2 again with the words from the question (all 7 items), and look at the git history (`git log --all -p -S "<слово>" \| head -60`). Add what you find to the registry. You can ask the human only if a mandatory value is nowhere, and the project clearly uses it (step 5 of Stage 3, items 1-5). |
| 2 | **Is this about a technology that has a section in `frame-topics.md`?** (SberMock, Kafka, Rest API and others) | If the section exists - the documentation describes it, and your search was bad. Go back to the documentation subagent: a query from the section name («Работа с SberMock подключение к стенду»), not less than 8 wordings, then the ladder of sources. A question is allowed only after all of the ladder. It must have the list of the wordings that you tried. |
| 3 | **Does the project NOT do this NOW?** You ask about a case that is not in the project code («а как проверить заголовок записи Kafka», when no test checks headers). | This is NOT a question. Migrate only what the project really has. If it is not in the inventory and there is no sample file - do not ask and do not plan it. |
| 4 | **Does the documentation do the same thing in a different way?** The documentation does not have «как раньше», but it has its own way to get the same result. | This is NOT a question. Use the way of the documentation. If the documentation does not have the old technique, this means «на фрейме так не делают», not «документация неполная». |
| 5 | **Does the answer change nothing in the migration map?** For any answer of the human, the rows `G`, `L`, `T` and the units stay the same. | This is NOT a question. Do not ask it from caution or «на всякий случай». |
| 6 | **Can you decide it by the rules of this skill?** (no technology in the documentation -> `keep`; no matcher for a standard assert -> keep the assert; the order of technologies; the unit size) | This is NOT a question. Apply the rule. |
| 7 | **Does the documentation simply not describe it?** A library, a driver, annotations, file reading, logging, stands, standard key names, DTOs - things that are in the project, but not in the documentation. | This is NOT a question. Use the decision from the tables «Документация молчит» and «DTO, Jackson, JAXB» of Stage 3. A question «оставить ли X как есть» almost always has the answer in the row «остаётся как есть». |

Write a question that passed the filter into section 6 EXACTLY like this. Without this form,
the question is not valid:

```
- Q-<n> · <вопрос одной фразой, конкретно> · относится к: <G-n / T-tech / A-n / M-nnn>
  - Где это в проекте: <путь к файлу>:<строка> - <что там сейчас делается>
  - Что искал в документации: <формулировки запросов, сколько; что нашёл рядом>
  - Что искал в проекте: <grep-слова; результат>
  - Варианты ответа: <для вопросов про документацию - ровно два: 1) отвечу сам; 2) дам путь к драфт-проекту Platform V. Для остальных вопросов - свои 2-3 варианта>
  - ответ: -
```

If you cannot fill in «Где это в проекте» with a specific file - there is no question (check 3).
The normal number of questions for a project is 0-2 (markup questions are not counted). If you
have more than 2, this almost always means that your search was bad or you did not apply the
decision tables. Do the filter again for each question.
If you yourself offer the option «оставить как есть» in a question and call it recommended -
it is not a question. Apply this option.

These are never questions (decide yourself):
- which addresses, logins, passwords, tokens, certificates, topics, groups, namespaces to use
  for the connection to Kafka, DB, OpenShift, Sbermock, REST (they are in the project -
  `CONNECTIONS.md`);
- which certificates to use (the same that the project uses now);
- how to use a technology (the same way as the project used it before, with the framework
  mechanism);
- what to do with DTOs, models, Jackson, JAXB and custom wrappers over them (the table
  «DTO, Jackson, JAXB» of Stage 3);
- the documentation does not describe deserialization or getting the response body as a string
  (this is correct - you check the response through `.should(...)`);
- keep a technology on the old implementation if the documentation describes it (no - it is
  migrated);
- what to do if there is no matcher (a standard assert and a row in «Входящие»);
- keep Lombok and other general-purpose libraries, a DBMS driver, custom Allure annotations,
  custom reading of test data files (they stay as they are);
- what to do with a module that the tests do not use (remove it as dead code);
- how to set the logging level (`simplelogger.properties`);
- how to set the stands (different keys in the framework properties, by the doc notes);
- what the names of the standard SSL and client keys are (as in the library);
- where to get what the project does not have (`снаружи: <ПЕРЕМЕННАЯ>` and «Входящие»).

All of these are decided by the table «Документация молчит» of Stage 3. These questions are
ALWAYS asked: Spring (Stage 2) and the markup values that are not in the project (Stage 2,
step 1б).

