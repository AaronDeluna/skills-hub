# Справка: tools (Fixtures, Таймауты, TestContainers, SberMock, OpenShift, DataConverter, Toggler, Launcher)

Для агента `pvatf-generator`. Имена фрейма - только из конспекта (`D-fixtures-`, `D-sbermock-`,
`D-toggler-` и т.д.) или кода проекта.

## Что искать в конспекте

| Сервис | Имена из примеров набора |
|--------|--------------------------|
| Fixtures | `FixtureService`, `executeFixture("<имя фикстуры>")`, `FixtureSetUpResult<T>`, `getNotNullResult()` |
| SberMock | `SberMockService`, `sberMockClient("<клиент>")`, `enableRestEmulation(<id>)` |
| TestContainers / OpenShift | `ContainerService`, `containerServiceClient("<клиент>")`, `checkPodsStatus("<сервис>")` |
| Toggler | `TogglerService`, `togglerClientWithRestore()`, `changeActivityFeature(...)` |
| Launcher | `LauncherService`, `launcherClient()`, `changeActivityForVersion(...)` |
| DataConverter | `DataConverterService` |
| Таймауты | в примерах набора нет - только конспект |

## Как писать

1. Подготовка (фикстура, включение эмуляции, переключение фичи) - тип шага SETUP; если ТК
   требует вернуть как было - клиент «с восстановлением» (`...WithRestore`) или шаг
   TEARDOWN из конспекта.
2. Имя фикстуры, клиента, id эмуляции - из ТК или настроек проекта; придумывать нельзя.
3. Результат фикстуры для следующих шагов - одна переменная с явным типом из конспекта.
4. Проверка (поды готовы, эмуляция включена) - matcher или метод проверки фрейма из
   конспекта; нет - `blocked`. `assertTrue(... .isEnabled())` - нельзя.
5. `var` - нельзя: тип клиента - как в конспекте (`LauncherClient`, `TogglerClient`).

## Нельзя -> нужно

- Нельзя: `var launcherClient = launcherService.launcherClient();`. Нужно: `LauncherClient launcherClient = ...` (тип из конспекта).
- Нельзя: `assertNotNull(user)` после фикстуры. Нужно: `getNotNullResult()` уже падает на пустом результате - отдельная проверка не нужна.

## Пример фрагмента (имена - условные, проверь по конспекту)

```java
// Шаг 1: Подготовить пользователя фикстурой «Создание пользователя»
User user = fixtureSteps.createUser(FIXTURE_CREATE_USER);
```
