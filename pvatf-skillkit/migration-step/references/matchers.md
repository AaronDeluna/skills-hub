# Как спросить документацию про проверки (matchers)

Во фрейме проверки делаются не ассертами, а **matchers**. Какие matchers есть и как они
называются - знает только документация (раздел «Matchers and Conditions»). Здесь НЕТ списка
методов. Здесь - как устроены проверки и какими словами спрашивать документацию, чтобы она
вернула нужный кусок.

**Слова из этого файла - для ЗАПРОСА, а не для кода.** В код и в «Таблицу подтверждений»
идёт только то, что вернул сабагент документации (запись конспекта `D-<tech>-<n>`).

## Как устроены проверки во фрейме (это надо понимать)

1. Операция фрейма возвращает не «сырой» ответ, а **валидируемый объект**:

   | Что сделали | Что вернулось |
   |-------------|---------------|
   | REST-запрос | `ValidatableResponseWrapper` |
   | SQL-запрос | `ValidatableTable` (строка - `ValidatableRow`, колонка - `ValidatableColumn`) |
   | чтение из Kafka | `KafkaConsumerClient`, запись - `ValidatableConsumerRecord` |
   | JSON (тело ответа, ячейка, сообщение, любая строка) | `ValidatableJson` |
   | XML | `ValidatableXml` |

2. Проверка - это вызов у валидируемого объекта: `.should(...)` (жёсткая, как обычный
   ассерт), `.shouldSoft(...)` (все проверки, как soft-assert), `.shouldAny(...)` (хотя бы
   одна). Внутрь передаются matchers.
3. Внутри matchers для гибкого сравнения используются **conditions** (условия для текста,
   чисел, boolean, дат).
4. Отсюда главное: **ответ не надо превращать в свой объект, чтобы его проверить.** Метод,
   который делает запрос, возвращает валидируемый объект наверх, а шаг или тест вызывает у
   него `.should(...)`. Свои DTO ответа, ручной разбор JSON и `assertEquals` для этого не
   нужны (`MR-29`, `MR-41`).

## Как писать проверку - по шагам, без отступлений

Делай это для КАЖДОЙ проверки, которую переводишь. Не придумывай свой способ проверять:
во фрейме всё уже есть, твоя задача - найти готовый matcher и вызвать его.

**Шаг 1. Запиши проверку словами.** Одна строка: что проверяется и с чем сравнивается.
«поле `result.status` ответа равно `true`»; «ячейка `state` строки равна 3»; «в массиве
`result.items` 5 элементов»; «поле `result.date` ответа равно колонке `doc_date` из БД».

**Шаг 2. Определи тип ожидаемого значения** и по таблице - чем проверять:

| Ожидаемое значение | Чем проверять (слова для запроса и конспекта) |
|--------------------|-----------------------------------------------|
| строка | matcher значения поля + условие для текста (`TextConditions`) |
| число (`int`, `long`, `BigDecimal`) | matcher значения поля + условие для чисел (`NumberConditions`) или matcher «значение равно» с числом |
| `true` / `false` | matcher значения поля + условие для boolean (`BooleanConditions`) или «значение равно» с boolean |
| дата, время | matcher значения поля + условие для дат (`DateTimeConditions`) |
| «поля нет» / `null` | отдельный matcher на отсутствие или `null` |
| размер массива, число строк | matcher размера коллекции / размера таблицы |
| весь объект или массив целиком | сравнение с эталонным JSON или matcher для коллекции |
| код ответа, заголовок | matchers ответа REST (`RestMatchers`) |
| ячейка строки БД | matchers строки и таблицы (`DatabaseMatchers`) |

Число НЕ проверяется как текст. Дата НЕ проверяется как текст. Boolean НЕ проверяется как
текст. Если ты пишешь `String.valueOf(...)` или `.toString()`, чтобы передать число или
дату в текстовое условие, - ты выбрал не тот matcher.

**Шаг 3. Возьми имя matcher из конспекта** (`doc-notes/<технология>.md`). Нет в
конспекте -> вопрос сабагенту документации по разделу «Какими словами спрашивать» выше.
Matcher из документации есть всегда для: равенства поля, размера коллекции, null, кода
ответа, ячейки таблицы. Не нашёл - переформулируй запрос, а не пиши свой.

**Шаг 4. Напиши ОДИН вызов проверки у валидируемого объекта**, matchers - прямо внутри
вызова, через запятую:
```java
response.toValidatableJson().shouldSoft(
        <matcher поля fileName>,
        <matcher поля state>,
        <matcher поля reportDate>);
```
`.should(...)` - если проверка одна или старый код падал на первой ошибке.
`.shouldSoft(...)` - если старый код проверял несколько полей через `assertAll` или
`SoftAssertions`.

**Шаг 5. Откуда ожидаемое значение.** Ожидаемое - это ДАННЫЕ: константа, параметр шага,
значение из строки БД (`row.getCellValue("doc_date", ...)`) - их передаёшь в matcher как
ожидаемое. Фактическое значение (то, что вернул сервис) НИКОГДА не достаётся руками -
его проверяет matcher у объекта, который вернул запрос.

## Запрещённые приёмы (видели в реальных миграциях - не повторяй)

Каждый пункт: как нельзя -> как нужно. Имена в примерах - чтобы узнать приём в коде; в
свой код имена берёшь из конспекта.

**1. Своя обёртка над matcher.** Метод, который возвращает matcher и внутри только
вызывает matcher фрейма:
```java
// НЕЛЬЗЯ
static ValidatableJsonMatcher jsonTextMatcher(String path, String expected, String message) {
    return JsonMatchers.haveJsonValue(path, TextConditions.equalToText(expected), message);
}
response.should(ReportServiceCommon.jsonTextMatcher("result.name", name, "Проверка name"));
// НУЖНО - matcher фрейма прямо в проверке
response.should(JsonMatchers.haveJsonValue("result.name", TextConditions.equalToText(name), "Проверка name"));
```
Признак: метод возвращает тип `...Matcher` или `...Condition`, а в теле одна строка
`return <КлассФрейма>.<метод>(...)`. Такой метод не нужен - удали его, вызывающие пишут
matcher фрейма сами.

**2. Свой класс matcher или condition.** `class X implements ValidatableJsonMatcher`,
`implements TextCondition`, `implements ...Matcher`, анонимный класс с `check(...)` или
`test(...)` - НЕЛЬЗЯ никогда. Во фрейме есть условия для текста, чисел, дат, null. Нужного
не нашлось после 8 формулировок запроса -> подшаг `blocked`, вопрос человеку. Свой matcher
не пиши.

**3. Список matchers и цикл.**
```java
// НЕЛЬЗЯ
List<ValidatableJsonMatcher> matchers = new ArrayList<>();
for (int i = 0; i < rows.size(); i++) {
    matchers.add(jsonTextMatcher("result.items[" + i + "].name", rows.get(i).getCellValue("name", String.class), "..."));
}
response.shouldSoft(matchers.toArray(new ValidatableJsonMatcher[0]));
```
Matchers не собираются в список, не возвращаются из методов списками
(`List<...Matcher> cardPageInfoMatchers(...)`) и не складываются в цикле. Проверка массива
целиком - это отдельный вопрос документации: «как проверить все элементы массива JSON» /
«как сравнить массив JSON с таблицей БД» / «как сравнить с эталонным JSON». Документация
не дала способа -> вопрос человеку в раздел 6 карты, а не цикл.

**4. Одно условие на всё.** Всё подряд проверяется текстом
(`TextConditions.equalToText(String.valueOf(number))`) или строкой-выражением
(`evaluateJsonPathExpression("result.count == " + count)`). НЕЛЬЗЯ: выбирай matcher по
типу (Шаг 2). Строка-выражение (`evaluate...Expression`) - только для условия, которое не
выразить matcher поля (например, «одно поле больше другого»); «поле равно значению» -
всегда matcher поля.

**5. Перечитать ответ и разобрать его руками.**
```java
// НЕЛЬЗЯ
String body = restService().getRestHistory().getLast().response().body();
JsonNode result = JacksonHelper.convertStringToJson(body).path("result");
assertEquals(row.getCellValue("state", Integer.class), intOrNull(result, "state"));
```
Нельзя: брать ответ из истории запросов, превращать его в `JsonNode`, доставать поля
через `.path(...)`, `textOrNull`, `intOrNull`, `getJsonPath().get(...)` и сравнивать.
Шаг, который сделал запрос, возвращает валидируемый объект; проверка - у него.

**6. Ассерты вместо matchers.** `assertAll(...)`, `assertEquals`, `assertTrue`,
`assertNotNull`, свои `compareNumbers`, `assertDatesEqual`, `bigDecimalsEqual`,
`normalizeDateFraction` для сравнения с ответом или строкой БД - НЕЛЬЗЯ. Для чисел и дат
есть условия фрейма.

**7. Хелпер «достать значение».** Методы `jsonTextValue`, `jsonNumber`, `jsonLong`,
`cellOf`, `dayOf`, `textOrNull` и подобные, которые достают значение из ответа, чтобы
потом сравнить, - НЕЛЬЗЯ (см. п.5). Достать значение можно только для ДАННЫХ следующего
шага (id для следующего запроса) - способом из документации.

**Перед тем как закончить подшаг** - выполни по своим файлам команду проверки `MR-48` из
`code-rules.md`. Любая строка в выводе - это один из приёмов выше: переделай.

## Какими словами спрашивать

Запрос собирай из трёх частей: **название раздела** + **класс matchers** + **что
проверяешь**. Название раздела - «Matchers and Conditions». Класс - из таблицы:

| Что проверяет старый код | Ключевые слова для запроса |
|--------------------------|----------------------------|
| код ответа REST, заголовки, куки, тело ответа | `RestMatchers`, `ValidatableResponseWrapper`, REST matchers, статус, заголовок, тело |
| поля JSON, наличие ключа, значение по jsonPath, сравнение с эталонным JSON, JSON-схема, размер массива | `JsonMatchers`, `ValidatableJson`, JSON matchers, jsonPath, `toValidatableJson` |
| строки и ячейки таблицы БД, количество строк, null в ячейке, JSON в ячейке | `DatabaseMatchers`, `ValidatableTable`, `ValidatableRow`, Table matchers, ячейка, колонка |
| сообщения Kafka: количество, ключ, значение, ожидание сообщения | `KafkaMatchers`, `KafkaConsumerClient`, `ValidatableConsumerRecord`, Kafka matchers, запись, ключ, значение |
| XML: значение по пути, сравнение, схема | `XmlMatchers`, `ValidatableXml`, XML matchers, xmlPath |
| сравнение текста: равно, содержит, начинается, регулярное выражение, пусто | `TextConditions`, Text conditions |
| сравнение чисел: больше, меньше, равно | `NumberConditions`, Number conditions |
| true / false | `BooleanConditions`, Boolean conditions |
| даты: равно, раньше, позже, в диапазоне | `DateTimeConditions`, DateTime conditions |
| несколько проверок, чтобы упали все сразу (soft assert, assertAll) | `shouldSoft`, мягкая проверка |
| своё сообщение об ошибке в проверке | `errorMessage`, кастомное сообщение matcher |

## Примеры вопросов сабагенту документации

Вопрос ставь про конкретную проверку из файла юнита, а не «какие есть matchers»:

| В старом коде | Вопрос сабагенту | Раздел документации в промпте |
|---------------|------------------|-------------------------------|
| `assertEquals(200, response.statusCode())` | «Каким matcher из RestMatchers проверить код ответа REST через .should()?» | Matchers and Conditions |
| `assertEquals("x", json.getString("a.b"))` | «Каким matcher из JsonMatchers проверить, что значение JSON по jsonPath равно строке?» | Matchers and Conditions |
| `assertTrue(list.size() > 0)` по массиву в JSON | «Каким matcher из JsonMatchers проверить размер коллекции в JSON по jsonPath с NumberConditions?» | Matchers and Conditions |
| `assertEquals(1, rows.size())` | «Каким matcher из DatabaseMatchers проверить количество строк ValidatableTable?» | Matchers and Conditions |
| `assertEquals("x", row.get("col"))` | «Каким matcher из DatabaseMatchers проверить значение ячейки ValidatableRow по имени колонки?» | Matchers and Conditions |
| ожидание сообщения в топике и проверка поля | «Каким matcher из KafkaMatchers дождаться записи в топике и проверить значение записи как JSON?» | Matchers and Conditions |
| ответ десериализуется в DTO и сравниваются поля | «Как из ValidatableResponseWrapper получить ValidatableJson и проверить поля тела ответа без десериализации в объект?» | Matchers and Conditions |
| `SoftAssertions` / `assertAll` | «Как выполнить несколько matchers так, чтобы были проверены все (shouldSoft)?» | Matchers and Conditions |

Правила запроса:
- одна проверка - один вопрос; не больше 5 вопросов за запуск сабагента;
- в вопросе называй класс matchers и валидируемый объект из таблицы выше - по этим словам
  векторная база находит нужный кусок;
- одинаковые проверки спрашивай один раз: ответ записан в конспект, дальше бери оттуда;
- документация вернула matcher - в код идёт имя ровно как в ответе;
- после 8 формулировок matcher не нашёлся - это исключение из `MR-29`: стандартный ассерт
  остаётся, запись во «Входящие».
