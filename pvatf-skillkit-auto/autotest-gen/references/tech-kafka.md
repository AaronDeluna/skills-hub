# Справка: kafka

Для агента `pvatf-generator`. Имена ниже - что искать в конспекте; в код - только то, что
подтверждено записью `D-kafka-<n>` или кодом проекта.

## Что искать в конспекте

| Что нужно | Имена из примеров набора |
|-----------|--------------------------|
| сервис | `KafkaService`, `getService(KafkaService.class)` |
| отправка | `kafkaService.producerClient("<продюсер из настроек>").sendRecord(<топик>, <ключ>, <значение>)` |
| чтение | `kafkaService.consumerClient("<консьюмер из настроек>").subscribe(<топик>)` |
| проверки | `.should(KafkaMatchers.haveRecordsCount(NumberConditions.greaterThan(0)))`, другие `KafkaMatchers` |

## Как писать

1. Топик - константа `TOPIC_*` (источник `PROPERTIES_FILE`): имя топика читается из
   настроек ключом из конспекта, строкой в коде не пишется.
2. Имя продюсера и консьюмера - имя клиента из настроек фрейма проекта (`*.properties`
   рядом с конфигурацией окружения). Нет в проекте - `blocked`, вопрос «как объявить
   продюсер и консьюмер Kafka в настройках».
3. Тело сообщения из ТК - файл `TESTDATA_FILE_REF` или строка из шаблона тела; объект-
   событие (`OrderCreatedEvent` с `@Data`) не создаётся.
4. Проверка сообщения: подписка до действия, которое порождает сообщение, если так требует
   конспект; поиск записи по ключу или полю - matcher из конспекта, ожидание - механизм
   фрейма, не цикл с `sleep`.

## Нельзя -> нужно

- Нельзя: `/* TODO: bind consumerName */`. Нужно: имя из настроек или `blocked`.
- Нельзя: `ConsumerRecords<String,String> r = consumer.poll(...); assertTrue(r.count() > 0)`.
  Нужно: `.subscribe(TOPIC_ORDERS).should(KafkaMatchers.haveRecordsCount(NumberConditions.greaterThan(0)))`.

## Пример фрагмента (имена - условные, проверь по конспекту)

```java
// Шаг 2: Отправить сообщение о заказе в топик orders.created
orderKafkaSteps.sendOrderCreated(BODY_2, orderId);
// Шаг 3: Проверить сообщение в топике orders.processed
orderKafkaSteps.processedMessages().should(KafkaMatchers.haveRecordsCount(NumberConditions.greaterThan(0)));
```
