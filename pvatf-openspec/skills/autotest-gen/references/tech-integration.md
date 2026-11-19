# Справка: integration (REST, gRPC, GraphQL, WebSocket)

Для агента `pvatf-generator`. Имена ниже - что искать в конспекте; в код - только то, что
подтверждено записью `D-<tech>-<n>` или кодом проекта.

## Что искать в конспекте

| Что нужно | Имена из примеров набора |
|-----------|--------------------------|
| сервис REST | `RestService`, `Environment.getForCurrentThread().getService(RestService.class)` |
| запрос | `restService.restClient().post(spec -> spec.header(...).body(...), "<путь>")`, `.get(...)`, `.put(...)`, `.delete(...)` |
| проверки ответа | `.should(haveStatusCode(<код>), haveBodyJsonValueEqualTo("<путь>", <значение>))` |
| WebSocket | `WebSocketService` |
| gRPC / GraphQL | в примерах набора нет - только конспект |

## Как писать

1. Класс шагов: `<Предметная область>Steps` (или класс из задания). Сервис - поле класса.
2. Метод шага = один запрос + проверки этого запроса, возвращает валидируемый ответ фрейма
   (тип - как в конспекте), если значение из ответа нужно следующим шагам.
3. Путь запроса - константа `PATH_*` из плана; базовый адрес - из настроек фрейма (ключ из
   конспекта), не строкой в коде.
4. Тело запроса из ТК (`BODY_*`, источник `TESTDATA_FILE_REF`) - файл
   `src/test/resources/<значение>`; поля `__имя__` в нём - подстановка переменных способом из
   конспекта (шаблон тела). Нет способа в конспекте - `blocked`.
5. Шаг «Проверить значение поля» по ответу прошлого шага - вызов `.should(...)` у ответа из
   переменной, не новый запрос.
6. Валидация по схеме (JSON Schema): matcher из конспекта; схема - файл в
   `src/test/resources/schemas/`. Адрес сервиса валидации из ТК в код не пишется.

## Нельзя -> нужно

- Нельзя: `assertEquals(200, response.statusCode())`. Нужно: `.should(haveStatusCode(EXPECTED_STATUS_200))`.
- Нельзя: `restService.getRestHistory().getLast().response().jsonPath()` (MR-48). Нужно: одно
  значение достаётся у валидируемого ответа способом из конспекта.
- Нельзя: `.header("Authorization", "Bearer eyJ...")`. Нужно: токен - переменная из шага авторизации.

## Пример фрагмента (имена - условные, проверь по конспекту)

```java
// Шаг 1: Отправить запрос POST /productList
ValidatableResponse productList = productSteps.requestProductList(BODY_1);
// Шаг 2: Проверить значение поля status.statusCode
productList.should(haveBodyJsonValueEqualTo(JSON_PATH_STATUS_STATUSCODE, 0));
```
