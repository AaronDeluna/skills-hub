# Справка: db (базы данных, DataSource, OpenSearch)

Для агента `pvatf-generator`. Имена ниже - что искать в конспекте; в код - только то, что
подтверждено записью `D-<tech>-<n>` или кодом проекта.

## Что искать в конспекте

| Что нужно | Имена из примеров набора |
|-----------|--------------------------|
| сервис | `DatabaseService`, `getService(DatabaseService.class)` |
| клиент базы | `databaseService.dataBaseClient("<имя базы из настроек>")` |
| запрос | `.executeSelect("""<SQL>""")`, `.executeUpdate("""<SQL>""")` |
| проверки | `.should(tableHaveSize(<n>))`, `.firstRow().should(haveCellValue("<колонка>", TextConditions.equalToText("<значение>")))`, `haveNonNullCellValue`, `haveColumn` |
| условия | `TextConditions`, `NumberConditions`, `BooleanConditions` |
| OpenSearch | `OpenSearchService`, `getOpenSearchClient("<кластер>")`, `JsonMatchers` |

## Как писать

1. SQL - текстовый блок `"""..."""`, константа `QUERY_*` из плана. Колонки перечислены явно:
   `SELECT id, status, price FROM orders WHERE id = ?`. `SELECT *` - нельзя.
2. Значения в запрос - только параметрами `?` способом из конспекта. Конкатенация,
   `String.format`, `formatted` - нельзя.
3. Несколько проверок одной таблицы - один запрос и цепочка `.should(...).firstRow().should(...)`,
   а не несколько одинаковых SELECT.
4. Выбор matcher по ожидаемому результату:
   | В ожидаемом результате | Matcher |
   |------------------------|---------|
   | «поле X = Y», «сохраняется значение» | значение колонки (`haveCellValue` + условие) |
   | «поле не пустое», «заполнено» | `haveNonNullCellValue` |
   | «есть колонка X» дословно | `haveColumn` |
   | «найдено N записей», «обновлена 1 строка» | `tableHaveSize(N)` |
5. Имя базы (`dataBaseClient("...")`) - имя подключения из настроек проекта; адрес и логин в
   код не пишутся.
6. Ожидание появления записи (асинхронно) - механизм ожидания из конспекта, не `Thread.sleep`.

## Нельзя -> нужно

- Нельзя: `List<Map<String,Object>> rows = ...getResult(); assertEquals(1, rows.size());`.
  Нужно: `.executeSelect(QUERY_SELECT).should(tableHaveSize(1))`.
- Нельзя: класс `OrderDto` для строки результата. Нужно: matchers по колонкам.

## Пример фрагмента (имена - условные, проверь по конспекту)

```java
// Шаг 4: Проверить запись в таблице orders
orderDbSteps.selectOrder(QUERY_SELECT, orderId)
        .should(tableHaveSize(1))
        .firstRow()
        .should(haveCellValue("status", TextConditions.equalToText(EXPECTED_ACTIVE)));
```
