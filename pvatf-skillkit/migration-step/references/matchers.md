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
