# Справка: mobile (Appium Android, iOS)

Для агента `pvatf-generator`. Имена фрейма - только из конспекта `D-mobile-<n>` или кода проекта.

## Что искать в конспекте

| Что нужно | Имена из примеров набора |
|-----------|--------------------------|
| экран | `@Page(pageName = "...")`, `AndroidPage<T>` / `IosPage<T>` |
| элемент | `@PageElement(elementName = "...")`, `AndroidElement` / `IosElement`, `AppiumBy.accessibilityId("...")` |
| действие | `@PageAction(actionName = "...")`, `.click()`, `.sendKeys(...)` |
| проверка | `element.assertIsDisplayed()`, метод `isPageDisplayed()` экрана |

## Как писать

1. Платформа - из технологии плана: «Работа с Appium Android» -> `AndroidPage` / `AndroidElement`,
   iOS - `IosPage` / `IosElement`. Flutter и другие - нет в наборе: `blocked`.
2. Один экран - один класс `<Экран>Page` в пакете `<пакет теста без последней части>.pages`,
   элементы - приватные поля с `@PageElement`, действия - методы с `@PageAction`.
3. Локатор - `accessibilityId` из существующих экранов проекта или из ТК. Нет -> `blocked`,
   причина «нет accessibilityId для <элемент>».
4. Значения из ТК, которые вводятся в поля (email, телефон), - переменные или константы
   плана; текст элементов - аргументы локаторов внутри класса экрана.

## Нельзя -> нужно

- Нельзя: `// TODO: testEmail - DECLARED_ONLY`. Нужно: переменная из плана или `blocked`.
- Нельзя: `assertTrue(element.isDisplayed())`. Нужно: `element.assertIsDisplayed()` (если есть в конспекте).

## Пример фрагмента (имена - условные, проверь по конспекту)

```java
// Шаг 3: Нажать кнопку «Оформить заказ»
OrderConfirmationPage confirmation = orderMobileSteps.openConfirmation().clickOrderButton();
// Шаг 4: Проверить экран подтверждения
confirmation.isPageDisplayed();
```
