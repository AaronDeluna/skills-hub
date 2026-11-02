# Review of the migrated code (the substep `review` of a technology unit and the units of type `review`)

The substep `review` closes the unit of each technology. The technology is migrated, the old code is removed.
Then we check the code of THIS technology (not of the full project). Only after that the next technology starts.
Below, «юнит `review`» means two things: the substep `review` in a unit `tech`, and a separate unit `review`
after the migration check. «файлы юнита» means the files of this substep. The task: make sure that
the resulting code obeys the rules `MR` from `references/code-rules.md`. Then fix the
findings, so that the errors do not repeat in the next technologies.
A subagent with a clean context does the check: it did not write this code and does not defend the decisions
of other agents. You do the fixes.

## Work order in the unit `review` («Порядок работы в юните `review`»)

1. **Mechanical check.** For the files of the unit, run the commands from the section «Быстрая
   самопроверка grep-ом» in `references/code-rules.md`. Write the output to the report (step 3).
   Then compare the files of the unit with the architecture plan `.gigacode/data/migration/ARCHITECTURE.md`
   (if it exists). Each class must be in section 3 or 5 of the plan and must do only what is
   written in «За что отвечает». If a class is not in the plan or does the task of a different class -> finding
   `V13`, mark `крупно`.
   **Thread check.** For each class that the substeps `core` of this technology created, run:
   ```
   grep -rl "\b<ИмяКласса>\b" --include=*.java --include=*.kt <src> | grep -v "<ИмяКласса>.java" | wc -l
   <команда поиска прямых обращений к сервису фрейма из раздела «Разбор технологии» карточки>
   ```
   If the first command gave 0 -> finding «класс создан, но не подключён». The second command can find files
   that are not step classes from the plan and are not postponed to a different technology. Then -> finding
   «потребитель не переведён, логика повторяется». Both are `V13`, mark `крупно`.
2. **Review subagents.** Divide the files of the unit into groups of max 8 files. For each group, use
   one subagent with the prompt below, word for word. Run max 3 subagents at the same time. The subagents are mandatory.
   Only if the subagent call returned an error (not «долго» and not «проще самому»):
   - show the error in the chat;
   - write `сабагент не запустился: <ошибка>` in the map log;
   - go through the checklist from the prompt yourself, one file at a time.
3. **Report.** Put the answers of the subagents and the grep output in the file
   `.gigacode/data/migration/review/M-<nnn>.md` (the template is below). If there is no folder, create it:
   `mkdir -p .gigacode/data/migration/review`. First write the report, then
   do the fixes.
4. **Fix.** Go through the report from the top down, one finding at a time:
   - first, open the file yourself and make sure that the finding is real. If the subagent made an error -> mark
     `ложная` and the reason. Do not fix it;
   - a finding with the mark `просто` -> fix it, mark `исправлено`;
   - a finding with the mark `крупно` -> do not do it in THIS substep. Examples: divide a class, move a
     responsibility, change a file to use the step class, connect a class. If it is the substep `review` in a unit
     `tech`: add a substep of type `fix` or `usage` for it at the end of the table «Подшаги» of the card.
     The rules are in «Дописывание подшагов» in `references/tech-flow.md`: up to 3 files, actions with names,
     final result, checkpoint with a command. In the report, mark `подшаг S-<nn>`. This substep runs
     next, and the unit does not close until it is `done`.
     If the finding touches a different technology or the layer structure of the full project,
     or if this is a separate unit `review` -> mark `во
     Входящие` and add an item to the section «5. Входящие» of the map.
5. **Check.** Compilation, the demonstration test from the card, and again the commands
   of the grep self-check. Their result must be clean (except the recorded exceptions).
6. Then do the usual Step 7 and Step 8 of the skill.

When you fix, do not change the meaning of the tests (`MR-9`..`MR-11`) and do not change files outside the card.

## Prompt for the review subagent (copy it word for word, replace <...>)

```
Ты проверяешь Java-код проекта автотестов после миграции на фрейм PVATF. Ты только читаешь
и находишь нарушения. Ничего не меняй, не запускай сборку и тесты. Проверяй ТОЛЬКО
перечисленные файлы и ТОЛЬКО по чек-листу ниже - свои правила не придумывай и вкусовые
замечания не пиши. Верни ТОЛЬКО таблицу находок по шаблону.

Проект: <абсолютный путь к корню проекта>
Файлы (прочитай КАЖДЫЙ целиком):
- <путь>
- <путь>
Стиль шагов: <flow / steps - из паспорта карты; карты нет - steps>
Старые пакеты и классы, которых в коде быть не должно: <список из раздела «Чего НЕ будет» блока T и grep-шаблон из карточки>

Чек-лист (код правила - что считается нарушением):
V1 var - в коде есть `var` вместо явного типа (переменная, for, try, лямбда).
V2 полное имя - класс написан с пакетом прямо в коде (`org.apache.kafka.common.header.Header h`) вместо `import`. Не находка: `@ru.sber.qa.allure.system.System(...)` в файле, где есть `java.lang.System`.
V3 импорты - неиспользуемый импорт; импорт со звёздочкой; импорт старого пакета из списка выше.
V4 ассерты - проверка через Assertions / assertEquals / assertTrue / assertThat / AssertJ / Hamcrest / SoftAssertions или через свой метод assertXxx / checkXxx, хотя это проверка ответа REST, JSON, таблицы БД или записи Kafka (для них во фрейме есть matchers: .should(...)).
V5 сеттеры - объект создан через `new` и следом 4 и более вызовов setXxx подряд вместо билдера.
V6 сервис - цепочка `Environment.getForCurrentThread().getService(...)` повторяется в двух и более методах одного класса.
V7 конфигурация - класс конфигурации фрейма (*EnvironmentConfiguration, *ServiceConfiguration) лежит не в пакете config.
V8 прослойка - свой класс или метод, который только заворачивает клиент или сервис фрейма (RestHelper, ApiClient, DbUtils, KafkaHelper, базовый класс ради доступа к клиенту; базовый тест-класс только с аннотациями фрейма - не прослойка).
V9 старое - остался вызов или упоминание класса из списка «быть не должно»; закомментированный старый код; комментарии «мигрировано», «было - стало»; TODO / FIXME.
V10 порядок - приватный метод стоит выше публичного; поля не в начале класса.
V11 длинный метод - метод длиннее 40 строк ИЛИ вложенность (if / for / try внутри друг друга) глубже 3 уровней.
V12 метод делает несколько дел - в одном методе и отправка, и ожидание, и разбор, и проверка, которые читаются как отдельные шаги; имя метода с «And».
V13 класс делает несколько дел - класс длиннее 500 строк ИЛИ в одном классе работа с разными технологиями (REST и БД и Kafka вместе) ИЛИ имя вида Utils / Helper / Common / Manager с несвязанными методами.
V14 дублирование - один и тот же блок кода из 5 и более строк повторён в двух и более местах.
V15 мёртвый код - приватный метод, поле, параметр или переменная, которые нигде не используются.
V16 плохие имена - имена из одной буквы (кроме счётчика цикла), tmp / data1 / obj, имя не говорит, что делает метод; имя не по соглашениям Java: метод, переменная, параметр или поле с нижним подчёркиванием или с большой буквы (create_order, order_id, test_create_order - нужно createOrder, orderId), класс не с большой буквы или с подчёркиванием, пакет с большими буквами или подчёркиванием. Подчёркивание допустимо только в константах static final (DEFAULT_TIMEOUT).
V17 хардкод - адрес, хост, порт, логин, пароль, таймаут числом прямо в коде теста или шага.
V18 глушение - пустой catch; catch (Exception e) без действия; Thread.sleep; @SuppressWarnings; @Disabled / @Ignore на тесте.
V19 DTO ответа - ответ запроса (REST, БД, Kafka) превращается в свой объект (`.as(X.class)`, `readValue`, `fromJson`, ручной маппинг в сеттеры) только для того, чтобы потом сравнить поля; метод, который делает запрос, возвращает DTO / String / Map вместо валидируемого объекта фрейма; класс DTO, на который нет ни одной ссылки; значение достаётся из ответа, строки БД или сообщения руками (геттер DTO, jsonPath().get, getString, value()) в переменную или сразу в проверку, хотя его можно проверить через .should() на валидируемом объекте; проверка переведена наполовину - ассерт убран, а DTO, геттер или свой check-метод остались. Как исправить - всегда «переписать цепочку целиком: метод возвращает валидируемый объект, проверка через .should(), DTO удалить, если на него больше нет ссылок».
V20 логика в тесте - в классе с @Test есть вспомогательный (не тестовый) метод - приватный, protected или static, - который отправляет запрос, ходит в БД или Kafka, читает файл, собирает SQL, выбирает схему или алиас, маппит ответ или строку таблицы в объект; одинаковый служебный метод скопирован в несколько тест-классов; одно и то же обращение к фрейму (getForCurrentThread / restClient / dataBaseClient / executeSelect / consumerClient / producerClient) повторяется в теле двух и более тестов вместо шага; ветвление (if / switch / цикл с условием) в теле тестового метода. НЕ нарушение: разовое короткое обращение к фрейму прямо в теле одного тестового метода с проверкой через .should().
V21 ручное логирование - код сам логирует то, что уже логирует фрейм: вызов логгера или System.out.println с URL, заголовками, телом запроса или ответа, кодом статуса, текстом SQL или его результатом, сообщением Kafka; строки «Отправляем запрос», «Получен ответ», «Выполняем SQL» вокруг вызова фрейма; .log().all(), RequestLoggingFilter / ResponseLoggingFilter, .prettyPrint(), .peek(); свой фильтр или перехватчик ради логирования; поле логгера или @Slf4j, которым никто не пользуется; логгер не из org.slf4j (импорт org.apache.logging.log4j, java.util.logging, ch.qos.logback). НЕ нарушение: сообщение о ходе сценария с предметным значением («создан заказ 123»).
V22 флоу (проверяй, только если выше указано «Стиль шагов: flow») - тест с несколькими шагами написан не цепочкой FlowRunner; в шаге цепочки лямбда длиннее 3 строк, с условием или циклом; запросы или проверки лежат в тесте, а не в методах класса-флоу; один класс-флоу на несвязанные сценарии; отдельный флоу на один тест при наличии подходящего; одинаковые методы в двух флоу; свой метод или класс повторяет готовые шаги, которые дают подключённые интерфейсы технологий фрейма (свой «выполнить select», своя загрузка и подстановка SQL). В стиле flow НЕ считай нарушением: класс-флоу работает с несколькими технологиями (V13), метод-проверка флоу вызывает .should(), метод-действие сохраняет ответ в поле.
V23 аннотации фрейма - аннотации подключения фрейма (@ExtendWith(PerfeccionistaExtension.class), @SetEnvironmentConfiguration(...)) повторены на тест-классе, хотя в проекте есть базовый тест-класс с ними или эти же аннотации стоят на трёх и более тест-классах; в базовом тест-классе лежит лишнее: клиенты и сервисы фрейма в полях, методы запросов, методы проверок, хелперы; два базовых тест-класса для одной конфигурации окружения. НЕ нарушение: сам базовый тест-класс с аннотациями фрейма и наследование тестов от него.
V24 своя конфигурация - код сам читает настройки подключений или сам собирает подключение, хотя это делает фрейм по своим файлам настроек: свой ConfigReader / PropertyReader / PropertiesLoader, интерфейс Owner и ConfigFactory.create, new Properties() с load, ResourceBundle, System.getProperty / System.getenv ради адреса, логина, алиаса, топика; свой конфигурационный класс, который хранит или отдаёт настройки подключения уже мигрированной технологии (DbConfig, DatabaseProperties, KafkaConfig, ApiConfig, класс с хостами, TestConfig с url / login / password), и любое обращение к нему из мигрированного кода; свои Properties для Kafka-клиента (bootstrap.servers, сериализаторы, SSL), своя строка JDBC или DataSource, базовый URL в коде; класс-переходник, который читает старый конфиг и передаёт значения фрейму. НЕ нарушение: получение собственного параметра проекта (тестовые данные) способом из документации фрейма; классы конфигурации самого фрейма (*EnvironmentConfiguration, *ServiceConfiguration) в пакете config.
V25 своя конструкция вокруг проверки - метод-обёртка, который возвращает matcher фрейма (jsonTextMatcher и подобные); свой класс, реализующий интерфейс matcher или condition; список matchers (List<...Matcher>, matchers.add в цикле, shouldSoft(matchers.toArray(...)), метод, возвращающий список matchers); число, дата или boolean проверяются текстовым условием (equalToText(String.valueOf(...))) или строкой-выражением вместо matcher поля; ответ перечитан из истории запросов (getRestHistory().getLast()) и разобран в JsonNode (JacksonHelper, .path(...), textOrNull/intOrNull); свои compareNumbers, assertDatesEqual для сравнения с ответом или БД; любой assertAll, в том числе assertAll с лямбдами () -> response.should(...) (группа проверок - .shouldSoft(...), именованный шаг - Allure.step("...", () -> ...) или @Step). НЕ нарушение: ожидаемое значение взято из строки БД (getCellValue) и передано в matcher фрейма.
V26 лишний слой - метод-делегат: тело - только вызов метода другого класса с теми же параметрами (фасад после деления класса, «пакетные делегаты»); вложенный, внутренний или анонимный класс в классе шагов, класс-держатель; два и больше метода с одинаковым телом, которые отличаются только путём, таблицей, файлом SQL или заголовком (должен быть один метод базового слоя с параметром); класс «всё общее» (...Common, ...Helper, ...Utils) со сложенными вместе константами, доступом к сервисам и хелперами. НЕ нарушение: один класс базового слоя технологии с общими операциями get/post/put/delete, выполнить SQL (он в плане).

Для каждого файла пройди чек-лист по порядку V1..V26. Находку пиши, только если можешь
указать номер строки. Сомневаешься - не пиши.

Сложность исправления:
- просто - правка в пределах этого файла, не меняет, кто кого вызывает (V1-V7, V9, V10, V15-V18, а также V11/V12/V14, если хватает вынести приватный метод в этом же классе; V19, если DTO используется только в этом файле);
- крупно - нужно делить класс, переносить код между классами или менять вызывающие файлы (V8, V13, V20, остальные случаи V11/V12/V14/V19).

Верни РОВНО так (заголовки сохрани):

## Находки

| Файл | Строка | Правило | Что не так (1 строка) | Как исправить (1 строка) | Сложность |
|------|--------|---------|-----------------------|--------------------------|-----------|
| <путь> | <n> | V<n> | <...> | <...> | просто / крупно |

## Файлы без находок
- <путь>     (нет таких - напиши: нет)

## Файлы, которые не удалось прочитать
- <путь: причина>     (нет таких - напиши: нет)
```

## Map of review codes to the rules MR

V1 - `MR-33` · V2 - `MR-4` · V3 - `MR-5`, `MR-6` · V4 - `MR-29` · V5 - `MR-34` · V6 - `MR-35` ·
V7 - `MR-36` · V8 - `MR-13`, `MR-30` · V9 - `MR-17`, `MR-20`, `MR-21`, `MR-23` · V10 - `MR-1` ·
V11, V12 - `MR-37` · V13 - `MR-38` · V14, V15 - `MR-39` · V16 - `MR-40`, `MR-45` · V17 - `MR-15` ·
V18 - `MR-14`, `MR-22`, `MR-10` · V19 - `MR-41` · V20 - `MR-42` · V21 - `MR-43` · V22 - `MR-44` · V23 - `MR-46` · V24 - `MR-47` · V25 - `MR-48` · V26 - `MR-49`, `MR-30`.

How to fix: read the text of the related rule `MR` in `references/code-rules.md`.
For V4, V19 and V25, read `references/matchers.md` (how to write a check, the prohibited methods, how to ask the documentation about the necessary matcher).

## Report template `.gigacode/data/migration/review/M-<nnn>.md`

```markdown
# Ревью M-<nnn> · <технология> · <дата>

## Самопроверка grep-ом (до исправлений)
- var: <n строк>
- сеттеры подряд: <файл - n>
- getForCurrentThread(): <файл - n>
- ассерты: <n строк>
- полные имена классов: <n строк>

## Находки сабагентов

| № | Файл | Строка | Правило | Что не так | Как исправить | Сложность | Итог |
|---|------|--------|---------|------------|---------------|-----------|------|
| 1 | <путь> | <n> | V<n> | <...> | <...> | просто / крупно | исправлено / ложная: <причина> / во Входящие |

## Итог
- находок всего: <n> · исправлено: <n> · ложных: <n> · ушло во Входящие: <n>
- самопроверка grep-ом после исправлений: <чисто / что осталось и почему>
```
