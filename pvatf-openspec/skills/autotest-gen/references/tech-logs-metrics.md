# Справка: logs_metrics (Единый Аудит, журналы ЕФС и ППРБ, PVM-ABYSS, метрики, СУП)

Для агента `pvatf-generator`. Имена фрейма - только из конспекта (`D-audit-`, `D-journal-`,
`D-abyss-`, `D-metrics-`, `D-sup-`) или кода проекта.

## Что искать в конспекте

| Что нужно | Имена из примеров набора |
|-----------|--------------------------|
| аудит | `AuditService`, `AuditFlow`, `auditFlow.unifiedAudit("<клиент>")`, `getValues(...)` |
| журналы | `JournalService`, `JournalFlow` (`ufs`, `pprb`), `JournalSearchRequest.Condition` |
| PVM-ABYSS | `UnofficialPvmAbyssClient`, `UnofficialPvmAbyssClientConfiguration.Builder`, `getRequiredValues(...)` |
| метрики | `MetricService`, `MetricsFlow`, `metricsService("<клиент>")`, `getMetrics(...)` |
| результат | `ValidatableJson` и его проверки (`filter(...)`, matchers из конспекта) |
| условия | `NumberConditions.equalTo(...)`, `TextConditions` |

## Как писать

1. Поиск записи - по значению из прошлого шага (id заказа, rqUID) - переменная плана, не литерал.
2. Ожидание появления записи - механизм фрейма (условие количества записей, таймаут из
   конспекта), не `Thread.sleep` и не цикл.
3. Проверки полей записи - у `ValidatableJson` способом из конспекта. `assertThat(response).isNotNull()` - нельзя:
   пустой результат ловит само условие поиска.
4. Имена клиентов (`"audit"`, `"ufs"`, `"esa"`) - из настроек проекта; нет - `blocked`.
5. Записи аудита и журнала не превращаются в объект (`AuditRecord` с `@Data` - нельзя).

## Нельзя -> нужно

- Нельзя: `assertThat(response).isNotNull(); response.filter("...").isNotEmpty();`.
  Нужно: проверка у `ValidatableJson` matcher из конспекта, одной цепочкой.

## Пример фрагмента (имена - условные, проверь по конспекту)

```java
// Шаг 5: Проверить запись аудита о смене статуса заказа
auditSteps.findByOrder(orderId).should(haveJsonValueEqualTo(JSON_PATH_EVENT_TYPE, EXPECTED_ORDER_STATUS_CHANGED));
```
