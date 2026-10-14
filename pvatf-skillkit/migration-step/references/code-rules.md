# Правила кода при миграции (MR) - оглавление и самопроверка

Правила про то, КАК писать код. ЧТО писать (какие классы и методы фрейма) - только из
документации MCP (конспект `doc-notes/`).

Сами правила расписаны подробно в папке `references/rules/` - у каждого правила: что
делать, зачем, как делать по шагам, пример «нельзя / нужно», исключения и как проверить.
Этот файл - оглавление: какие файлы правил читать, короткий список всех правил и общая
самопроверка grep-ом.

## Как пользоваться (обязательно)

1. **Шаг 5, до первой строки кода:** прочитай ЦЕЛИКОМ файлы правил из таблицы ниже для вида
   своего подшага. Не «пробеги глазами», а прочитай: в них примеры того, что ревью
   возвращает чаще всего.
2. **Шаг 6:** пройди таблицу «Все правила» по КАЖДОМУ изменённому файлу и выполни
   самопроверку grep-ом (конец этого файла). Результаты - в «Проверки» карточки рядом с
   `правила кода MR`.
3. Сомневаешься в правиле - открой его полный текст в файле из колонки «Файл».

| Вид подшага | Какие файлы правил прочитать |
|-------------|------------------------------|
| `env` | `rules/frame-config.md`, `rules/legacy-clean.md` |
| `core` | `rules/layers.md`, `rules/checks.md`, `rules/frame-config.md`, `rules/code-style.md`, `rules/structure-names.md` |
| `usage`, `fix`, `arch` | ВСЕ файлы: `rules/test-meaning.md`, `rules/layers.md`, `rules/checks.md`, `rules/frame-config.md`, `rules/code-style.md`, `rules/structure-names.md`, `rules/legacy-clean.md` |
| `cleanup` | `rules/legacy-clean.md`, `rules/frame-config.md` |
| `review` | файлы правил не читаешь заранее; открываешь правило, когда исправляешь находку по нему |

**Правила действуют на весь файл юнита, а не только на твои строки.** Открыл файл юнита и
видишь в нём нарушение `MR-33`, `MR-34`, `MR-35`, `MR-36`, `MR-41`, `MR-42`, `MR-43`,
`MR-49` или `MR-4` - исправь, даже если эту строку писал не ты. Файлы ВНЕ юнита не трогай -
нарушение там запиши во «Входящие» карты.

Приоритет при конфликте: документация фрейма > кодстайл проекта (checkstyle, паспорт
карты) > блок «добавлено человеком» внизу > правила `MR`.

## Все правила (коротко)

Короткая строка - напоминание, а не правило. Правило - полный текст в файле.

| Правило | Коротко | Файл |
|---------|---------|------|
| MR-1 | порядок в классе: константы, поля, конструкторы, public, protected, private в конце | `rules/structure-names.md` |
| MR-2 | новые поля `private`, по возможности `final` | `rules/structure-names.md` |
| MR-3 | в мигрируемый класс не добавляется новая ответственность | `rules/structure-names.md` |
| MR-4 | классы через `import`, не полным именем в коде | `rules/structure-names.md` |
| MR-5 | неиспользуемые импорты удалены, без `*` | `rules/structure-names.md` |
| MR-6 | старых импортов не осталось | `rules/structure-names.md` |
| MR-7 | ничего не переименовывать без шага карточки | `rules/structure-names.md` |
| MR-8 | нет своих классов в `package ru.sber.qa` | `rules/structure-names.md` |
| MR-9 | тест проверяет то же, что раньше | `rules/test-meaning.md` |
| MR-10 | тесты не пропадают и не отключаются | `rules/test-meaning.md` |
| MR-11 | проверки не ослабляются | `rules/test-meaning.md` |
| MR-12 | каждое имя фрейма - из «Таблицы подтверждений» | `rules/frame-config.md` |
| MR-13 | своё не пишется там, где фрейм даёт | `rules/frame-config.md` |
| MR-14 | без `Thread.sleep` | `rules/frame-config.md` |
| MR-15 | без хардкода подключений | `rules/frame-config.md` |
| MR-16 | зависимости и версии - только из документации и паспорта | `rules/frame-config.md` |
| MR-17 | старый код удаляется, не комментируется | `rules/legacy-clean.md` |
| MR-18 | нетронутое не переформатируется | `rules/legacy-clean.md` |
| MR-19 | кодстайл проекта | `rules/code-style.md` |
| MR-20 | Javadoc и комментарии как в проекте, без «мигрировано» | `rules/legacy-clean.md` |
| MR-21 | без `TODO` / `FIXME` | `rules/legacy-clean.md` |
| MR-22 | ошибки не глушатся | `rules/legacy-clean.md` |
| MR-23 | двух реализаций не бывает | `rules/legacy-clean.md` |
| MR-24 | никаких мостиков между старым и фреймом | `rules/legacy-clean.md` |
| MR-25 | старая архитектура не переезжает | `rules/legacy-clean.md` |
| MR-26 | удаляется только то, на что нет ссылок | `rules/legacy-clean.md` |
| MR-27 | удаляется до конца | `rules/legacy-clean.md` |
| MR-28 | `in-place`: публичные методы ядра не меняются | `rules/structure-names.md` |
| MR-29 | проверки - на matchers фрейма | `rules/checks.md` |
| MR-30 | к фрейму обращаются только общий класс технологии или класс шагов; своих прослоек нет | `rules/layers.md` |
| MR-31 | технологии `keep` не трогать | `rules/frame-config.md` |
| MR-32 | из старого кода берутся данные, а не механика | `rules/legacy-clean.md` |
| MR-33 | `var` запрещён | `rules/code-style.md` |
| MR-34 | 4+ сеттера подряд - билдер | `rules/code-style.md` |
| MR-35 | сервис фрейма получается в одном месте класса | `rules/layers.md` |
| MR-36 | конфигурация фрейма - в пакете `config` | `rules/frame-config.md` |
| MR-37 | метод до 40 строк, вложенность до 3 | `rules/code-style.md` |
| MR-38 | класс делает одно дело, до 500 строк | `rules/layers.md` |
| MR-39 | без дублей и мёртвого кода | `rules/code-style.md` |
| MR-40 | говорящие имена | `rules/structure-names.md` |
| MR-41 | ответ не превращается в DTO ради проверки, разбирай цепочку | `rules/checks.md` |
| MR-42 | тест-класс чистый, без вспомогательных методов | `rules/layers.md` |
| MR-43 | запросы и ответы руками не логируются; `simplelogger.properties` | `rules/frame-config.md` |
| MR-44 | стиль `flow`: цепочка FlowRunner | `rules/layers.md` |
| MR-45 | имена по соглашениям Java, без `_` | `rules/structure-names.md` |
| MR-46 | аннотации фрейма - в базовом тест-классе | `rules/frame-config.md` |
| MR-47 | настройки подключений читает фрейм | `rules/frame-config.md` |
| MR-48 | проверка = готовый matcher нужного вида прямо в `.should(...)` | `rules/checks.md` |
| MR-49 | ровно три слоя (тест -> шаги -> общий класс технологии), без вложенных классов, обёрток над обёртками и дублей механики | `rules/layers.md` |
| MR-50 | Spring - по решению паспорта: `keep` со стартером фрейма или `remove` полностью | `rules/frame-config.md` |

## Самопроверка grep-ом (Шаг 6, по файлам юнита)

```
grep -nE "(^|[^A-Za-z0-9_])var +[A-Za-z_][A-Za-z0-9_]* *(=|:)" <файлы юнита>          # MR-33: должно быть пусто
grep -cE "\.set[A-Z][A-Za-z0-9]*\(" <файл>                                          # MR-34: 4 и больше подряд на один объект - переделай на билдер
grep -c "getForCurrentThread()" <файл>                                               # MR-35: больше, чем разных сервисов в файле, - вынеси в один метод
grep -nE "Assertions\.|assert(Equals|True|False|NotNull|Null|That|All)\(|SoftAssertions" <файлы юнита>   # MR-29: в usage-подшаге каждая строка либо заменена, либо записана во «Входящие»
grep -nE "\.as\([A-Z][A-Za-z0-9_]*\.class\)|readValue\(|fromJson\(|\.getObject\(|\.extract\(\)" <файлы юнита>   # MR-41: ответ превращают в объект - замени на проверку через .should(), если это ради проверки
grep -nE "List<[A-Za-z]*(Matcher|Condition)|(Matcher|Condition)\[\]|for *\([A-Za-z<>]*(Matcher|Condition)|forEach\([a-z]*::should|(implements|extends) +[A-Za-z]*(Matcher|Condition)|(String\.valueOf|toString)\(.*\)" <файлы юнита> | grep -E "Matcher|Condition|should"   # MR-48: список, цикл, свои matchers, сравнение числа строкой - должно быть пусто
grep -nE "^\s*(public|private|protected)[^=(]*(Matcher|Condition)[A-Za-z<>?, ]* +[a-z][A-Za-z0-9]*\(" <файлы юнита>   # MR-48: метод возвращает matcher - должно быть пусто
grep -nE "^\s+(public |private |protected )?(static )?(final )?(class|interface|enum|record) [A-Z]" <файлы юнита>   # MR-49: вложенные классы - пусто (кроме Builder по MR-34)
grep -nE "new [A-Z][A-Za-z0-9]*\(\) *\{" <файлы юнита>                                                           # MR-49: анонимные классы - пусто
grep -nE "abstract class|extends [A-Z][A-Za-z0-9]*(Steps|Requests|Client|Helper|Base)\b" <файлы юнита>          # MR-49: наследование ради общего кода - пусто (кроме тест-класс extends BaseTest)
grep -nE "class [A-Z][A-Za-z0-9]*(Service|Facade|Manager|Executor|Processor|Handler|Wrapper|Helper|Utils)\b" <файлы юнита>   # MR-49, MR-30: лишний уровень или прослойка - пусто
grep -nE "^[^/*]*[^A-Za-z0-9_.\"](org|com|ru|io|java)\.[a-z0-9_]+\.[a-z0-9_.]+\.[A-Z]" <файлы юнита> | grep -v "^[0-9]*:\(import\|package\)"   # MR-4: полное имя класса в коде
grep -nE "\b(log|logger|LOG|LOGGER)\.(info|debug|trace|warn|error)\(|System\.(out|err)\.print|\.log\(\)\.(all|body|headers|ifValidationFails)|(Request|Response)LoggingFilter|\.prettyPrint\(|\.prettyPeek\(|\.peek\(" <файлы юнита>   # MR-43: строка логирует запрос, ответ, SQL или сообщение - удали; остаётся только сообщение о ходе сценария
grep -nE "ConfigFactory\.create|new Properties\(\)|getResourceAsStream\(|ResourceBundle\.getBundle|System\.(getProperty|getenv)\(|@Value\(|PropertiesLoader|ConfigReader|PropertyReader" <файлы юнита>   # MR-47: своё чтение настроек - значения в файлы настроек фрейма, код чтения удалить
```
Проверка имён `MR-45` - отдельной командой, смотри только строки, которые ты написал:
```
grep -nE "(^|[ .(])[a-z][A-Za-z0-9]*_[A-Za-z0-9_]*( *\(| *=| *;|,|\))" <файлы юнита>   # метод, переменная или параметр с нижним подчёркиванием: переименуй
```
Паспорт карты «Spring: remove» - дополнительно `MR-50`:
```
grep -nE "org\.springframework|@Autowired|@SpringBootTest|@ContextConfiguration|@Component|@Configuration|@Bean" <файлы юнита>   # в новых и переписанных файлах - пусто
```
Для каждого тест-класса (файл с `@Test`) - `MR-46` и `MR-42`:
```
grep -nE "@ExtendWith\(PerfeccionistaExtension|@SetEnvironmentConfiguration" <тест-класс>   # пусто, если есть базовый тест-класс
grep -nE "^\s*(private|protected|static) .*\(.*\)\s*(throws [A-Za-z, ]+)?\{" <тест-класс>   # пусто (кроме @BeforeEach/@AfterEach и подобных)
grep -cE "getForCurrentThread\(\)|restClient\(\)|dataBaseClient\(|executeSelect\(|consumerClient\(|producerClient\(" <тест-класс>   # одно и то же действие в 2+ тестах - вынеси в шаг
```
Для каждого нового метода класса шагов - вопрос `MR-49`: «чем он отличается от соседнего,
кроме адреса и тела?» Ничем, тело одинаковое на 5+ строк - механика не вынесена.

---

## Правила: добавлено человеком

<!-- Этот блок пишет команда руками. Сюда добавляются правила, специфичные для вашего фрейма
     и проектов (формат: MR-H<n> · название. Правило. Исключения.). Эти правила приоритетнее
     правил MR выше. Пусто = дополнительных правил пока нет. -->

(пусто)
