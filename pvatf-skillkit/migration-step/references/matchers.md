# How to ask the documentation about checks (matchers)

In the framework, checks do not use asserts. Checks use **matchers**. Only the documentation
knows which matchers exist and what their names are (the section «Matchers and Conditions»).
This file does NOT have a list of methods. This file tells how the checks work and which words
to use in a query, so that the documentation returns the necessary part.

**The words from this file are for the QUERY, not for the code.** Into the code and into the
«Таблицу подтверждений» put only what the documentation subagent returned (the doc-notes record `D-<tech>-<n>`).

## How the checks work in the framework (you must understand this)

1. A framework operation does not return a «сырой» (raw) response. It returns a **validatable object**:

   | What you did | What you get |
   |--------------|--------------|
   | REST request | `ValidatableResponseWrapper` |
   | SQL query | `ValidatableTable` (row - `ValidatableRow`, column - `ValidatableColumn`) |
   | read from Kafka | `KafkaConsumerClient`, record - `ValidatableConsumerRecord` |
   | JSON (response body, cell, message, any string) | `ValidatableJson` |
   | XML | `ValidatableXml` |

2. A check is a call on the validatable object:
   - `.should(...)` (strict, as a usual assert);
   - `.shouldSoft(...)` (all checks, as a soft assert);
   - `.shouldAny(...)` (at least one).
   You give matchers to this call.
3. Matchers use **conditions** for a flexible comparison (conditions for text, numbers,
   boolean, dates).
4. The main result of this: **do not change the response into your own object to check it.**
   The method that sends the request returns the validatable object to the caller.
   The step or the test calls `.should(...)` on it. For this, you do not need your own
   response DTOs, manual JSON parsing or `assertEquals` (`MR-29`, `MR-41`).

## How to write a check («Как писать проверку») - step by step, with no deviations

Do these steps for EACH check that you move. Do not make up your own way to check.
The framework already has everything. Your task is to find a ready matcher and call it.

**Step 1. Write the check in words.** One line: what you check and what you compare it with.
«поле `result.status` ответа равно `true`»; «ячейка `state` строки равна 3»; «в массиве
`result.items` 5 элементов»; «поле `result.date` ответа равно колонке `doc_date` из БД».

**Step 2. Find the type of the expected value.** Then find in the table what to use for the check:

| Expected value | What to use for the check (words for the query and the doc notes) |
|----------------|--------------------------------------------------------------------|
| string | matcher значения поля + условие для текста (`TextConditions`) |
| number (`int`, `long`, `BigDecimal`) | matcher значения поля + условие для чисел (`NumberConditions`) или matcher «значение равно» с числом |
| `true` / `false` | matcher значения поля + условие для boolean (`BooleanConditions`) или «значение равно» с boolean |
| date, time | matcher значения поля + условие для дат (`DateTimeConditions`) |
| «поля нет» / `null` | отдельный matcher на отсутствие или `null` |
| array size, number of rows | matcher размера коллекции / размера таблицы |
| the full object or the full array | сравнение с эталонным JSON или matcher для коллекции |
| response code, header | matchers ответа REST (`RestMatchers`) |
| cell of a DB row | matchers строки и таблицы (`DatabaseMatchers`) |

Do NOT check a number as text. Do NOT check a date as text. Do NOT check a boolean as text.
If you write `String.valueOf(...)` or `.toString()` to give a number or a date to a text
condition, you selected the wrong matcher.

**Step 3. Take the matcher name from the doc notes** (`doc-notes/<технология>.md`).
If the doc notes do not have it -> ask the documentation subagent. Use the section
«Какими словами спрашивать» below.
The documentation always has a matcher for: field equality, collection size, null, response
code, table cell. If you did not find it, write the query again in different words. Do not write your own matcher.

**Step 4. Write ONE check call on the validatable object.** Put the matchers directly in the
call, separated by commas:
```java
response.toValidatableJson().shouldSoft(
        <matcher поля fileName>,
        <matcher поля state>,
        <matcher поля reportDate>);
```
Use `.should(...)` if there is one check, or if the old code stopped at the first error.
Use `.shouldSoft(...)` if the old code checked a number of fields with `assertAll` or
`SoftAssertions`.

**Step 5. Where the expected value comes from.** The expected value is DATA: a constant, a step
parameter, a value from a DB row (`row.getCellValue("doc_date", ...)`). Give it to the matcher
as the expected value. NEVER get the actual value (the value that the service returned) manually.
The matcher checks it on the object that the request returned.

## Prohibited methods («Запрещённые приёмы»; we saw them in real migrations - do not do them again)

Each item: the wrong way -> the correct way. The names in the examples help you to find the
method in the code. For your own code, take the names from the doc notes.

**1. Your own wrapper around a matcher.** A method that returns a matcher and only calls a
framework matcher:
```java
// НЕЛЬЗЯ
static ValidatableJsonMatcher jsonTextMatcher(String path, String expected, String message) {
    return JsonMatchers.haveJsonValue(path, TextConditions.equalToText(expected), message);
}
response.should(ReportServiceCommon.jsonTextMatcher("result.name", name, "Проверка name"));
// НУЖНО - matcher фрейма прямо в проверке
response.should(JsonMatchers.haveJsonValue("result.name", TextConditions.equalToText(name), "Проверка name"));
```
How to find it: the method returns the type `...Matcher` or `...Condition`, and its body has one line
`return <КлассФрейма>.<метод>(...)`. You do not need this method. Remove it. The callers write
the framework matcher themselves.

**2. Your own matcher class or condition class.** NEVER write `class X implements ValidatableJsonMatcher`,
`implements TextCondition`, `implements ...Matcher`, or an anonymous class with `check(...)` or
`test(...)`. The framework has conditions for text, numbers, dates, null.
If you did not find the necessary one (doc notes, subagent, the `docs` folder of the framework
sources) -> keep the standard JUnit assert (`MR-29`). Add a line to «Входящие».
Do not write your own matcher. Do not ask a question.

**3. A list of matchers and a loop.**
```java
// НЕЛЬЗЯ
List<ValidatableJsonMatcher> matchers = new ArrayList<>();
for (int i = 0; i < rows.size(); i++) {
    matchers.add(jsonTextMatcher("result.items[" + i + "].name", rows.get(i).getCellValue("name", String.class), "..."));
}
response.shouldSoft(matchers.toArray(new ValidatableJsonMatcher[0]));
```
Do not collect matchers into a list. Do not return matchers from methods as lists
(`List<...Matcher> cardPageInfoMatchers(...)`). Do not add matchers in a loop. First, ask the
documentation: «как проверить все элементы массива JSON» / «как сравнить массив JSON с
таблицей БД» / «как сравнить с эталонным JSON». If the documentation did not give a way -> you
can use this way (do not ask a question):
```java
// МОЖНО, если matcher для массива целиком нет
for (int i = 0; i < rows.size(); i++) {
    ValidatableRow row = rows.get(i);
    String item = "result.items[" + i + "]";
    response.shouldSoft(
            JsonMatchers.haveJsonValue(item + ".name", TextConditions.equalToText(row.getCellValue("name", String.class)), "name"),
            JsonMatchers.haveJsonValueEqualTo(item + ".count", row.getCellValue("count", Integer.class)));
}
```
One check call for each element, the matchers directly in it, no list and no helpers.

**4. One condition for everything.** Everything is checked as text
(`TextConditions.equalToText(String.valueOf(number))`) or as an expression string
(`evaluateJsonPathExpression("result.count == " + count)`). This is PROHIBITED: select the
matcher by the type (Step 2). Use an expression string (`evaluate...Expression`) only for a
condition that a field matcher cannot express (for example, «одно поле больше другого»).
For «поле равно значению», always use a field matcher.

**5. Read the response again and parse it manually.**
```java
// НЕЛЬЗЯ
String body = restService().getRestHistory().getLast().response().body();
JsonNode result = JacksonHelper.convertStringToJson(body).path("result");
assertEquals(row.getCellValue("state", Integer.class), intOrNull(result, "state"));
```
Do not do these things:
- take the response from the request history;
- change the response into `JsonNode`;
- get fields with `.path(...)`, `textOrNull`, `intOrNull`, `getJsonPath().get(...)` and compare them.
The step that sent the request returns a validatable object. Do the check on this object.

**6. Asserts instead of matchers.** PROHIBITED for a comparison with the response or with a DB row:
`assertAll(...)`, `assertEquals`, `assertTrue`, `assertNotNull`, your own `compareNumbers`,
`assertDatesEqual`, `bigDecimalsEqual`, `normalizeDateFraction`.
The framework has conditions for numbers and dates.

**7. A «достать значение» (get the value) helper.** PROHIBITED: the methods `jsonTextValue`, `jsonNumber`, `jsonLong`,
`cellOf`, `dayOf`, `textOrNull` and similar methods that get a value from the response to
compare it later (see item 5). You can get a value only as DATA for the next step (an id for
the next request). Use the way from the documentation for this.

**8. `assertAll` around framework checks.** PROHIBITED: framework matchers inside the lambdas of
`assertAll`:
```java
// НЕЛЬЗЯ
assertAll("ШАГ 4. Блок debiting.requisites",
        () -> response.should(JsonMatchers.haveJsonValueEqualTo("debiting.requisites.type", "FL")),
        () -> response.should(JsonMatchers.haveJsonValueEqualTo("debiting.requisites.kpp", "0")));
// НУЖНО - несколько проверок сразу: один вызов .shouldSoft(...)
response.shouldSoft(
        JsonMatchers.haveJsonValueEqualTo("debiting.requisites.type", "FL"),
        JsonMatchers.haveJsonValueEqualTo("debiting.requisites.kpp", "0"));
// НУЖНО - если проверки должны быть отдельным шагом в отчёте: обычный шаг Allure
Allure.step("ШАГ 4. Блок debiting.requisites", () -> response.shouldSoft(
        JsonMatchers.haveJsonValueEqualTo("debiting.requisites.type", "FL"),
        JsonMatchers.haveJsonValueEqualTo("debiting.requisites.kpp", "0")));
```
Do not use `assertAll` at all: not around framework matchers, not around steps, not as a
«заголовка» of a group of checks.
- If you need a group of checks, use `.shouldSoft(...)`.
- If you need a named step in the report, use `Allure.step("<описание>", () -> ...)` (or a step method with `@Step`).
  Inside it, put the usual step calls and check calls.
The text from the `assertAll` title becomes the step description. The standard asserts that
stay because of `MR-29` (no matcher found) also do not use `assertAll`: write them one after another.

**Before you finish the substep**, run the check command `MR-48` from
`code-rules.md` on your files. Each line in the output is one of the methods above: change it.

## Which words to use in a query («Какими словами спрашивать»)

Make the query from three parts: **the section name** + **the matchers class** + **what you
check**. The section name is «Matchers and Conditions». Take the class from the table:

| What the old code checks | Keywords for the query |
|--------------------------|------------------------|
| REST response code, headers, cookies, response body | `RestMatchers`, `ValidatableResponseWrapper`, REST matchers, статус, заголовок, тело |
| JSON fields, presence of a key, value by jsonPath, comparison with a reference JSON, JSON schema, array size | `JsonMatchers`, `ValidatableJson`, JSON matchers, jsonPath, `toValidatableJson` |
| rows and cells of a DB table, cell value equals X, typified cell value, number of rows, null in a cell, JSON in a cell | `DatabaseMatchers`, `ValidatableTable`, `ValidatableRow`, Table matchers, ячейка, колонка, cell value equal, typified cell value |
| Kafka messages: number, key, value, wait for a message | `KafkaMatchers`, `KafkaConsumerClient`, `ValidatableConsumerRecord`, Kafka matchers, запись, ключ, значение |
| XML: value by path, comparison, schema | `XmlMatchers`, `ValidatableXml`, XML matchers, xmlPath |
| text comparison: equals, contains, starts with, regular expression, empty | `TextConditions`, Text conditions |
| number comparison: more than, less than, equals | `NumberConditions`, Number conditions |
| true / false | `BooleanConditions`, Boolean conditions |
| dates: equals, before, after, in a range | `DateTimeConditions`, DateTime conditions |
| a number of checks, so that all of them fail together (soft assert, assertAll) | `shouldSoft`, мягкая проверка |
| your own error message in the check | `errorMessage`, кастомное сообщение matcher |

## Examples of questions to the documentation subagent

Ask the question about one specific check from the unit file. Do not ask «какие есть matchers»:

| In the old code | Question to the subagent | Documentation section in the task |
|-----------------|--------------------------|-----------------------------------|
| `assertEquals(200, response.statusCode())` | «Каким matcher из RestMatchers проверить код ответа REST через .should()?» | Matchers and Conditions |
| `assertEquals("x", json.getString("a.b"))` | «Каким matcher из JsonMatchers проверить, что значение JSON по jsonPath равно строке?» | Matchers and Conditions |
| `assertTrue(list.size() > 0)` for an array in JSON | «Каким matcher из JsonMatchers проверить размер коллекции в JSON по jsonPath с NumberConditions?» | Matchers and Conditions |
| `assertEquals(1, rows.size())` | «Каким matcher из DatabaseMatchers проверить количество строк ValidatableTable?» | Matchers and Conditions |
| `assertEquals("x", row.get("col"))` | «Каким matcher из DatabaseMatchers проверить значение ячейки ValidatableRow по имени колонки?» | Matchers and Conditions |
| wait for a message in a topic and check a field | «Каким matcher из KafkaMatchers дождаться записи в топике и проверить значение записи как JSON?» | Matchers and Conditions |
| the response is deserialized into a DTO and the fields are compared | «Как из ValidatableResponseWrapper получить ValidatableJson и проверить поля тела ответа без десериализации в объект?» | Matchers and Conditions |
| `SoftAssertions` / `assertAll` | «Как выполнить несколько matchers так, чтобы были проверены все (shouldSoft)?» | Matchers and Conditions |

Query rules:
- one check - one question; not more than 5 questions for one subagent run;
- in the question, name the matchers class and the validatable object from the table above.
  The vector database finds the necessary part by these words;
- ask about identical checks one time only: the answer goes into the doc notes, then take it from there;
- if the documentation returned a matcher, put the name into the code exactly as in the answer;
- if no matcher is found after 8 different query texts, this is an exception from `MR-29`:
  the standard assert stays, and you add a record to «Входящие».
