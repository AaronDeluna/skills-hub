# Управление зависимостями в Gradle - понятия, без которых нельзя проверять правила

Прочитай этот файл один раз сверху вниз. Здесь определён каждый термин, который
используют файлы правил Gradle. Запоминать наизусть не нужно - можно возвращаться к
конкретному разделу во время проверки правила.

## 1. Какие файлы управляют зависимостями

| Файл | Что там лежит | Почему обязательно смотреть |
|---|---|---|
| `settings.gradle(.kts)` | список модулей (`include`), `pluginManagement`, `dependencyResolutionManagement` (центральные репозитории, version catalog) | задаёт структуру проекта; репозитории могут быть объявлены ТОЛЬКО здесь |
| `build.gradle(.kts)` (корневой) | плагины, иногда блоки `allprojects { }` / `subprojects { }` | эти блоки могут незаметно внедрять зависимости/репозитории во все модули |
| `build.gradle(.kts)` (в модуле) | блоки `plugins { }` и `dependencies { }` модуля | основной объект ревью |
| `gradle/libs.versions.toml` | **version catalog**: центральный список версий, библиотек, бандлов, плагинов | рекомендуемый единый источник истины для версий |
| `gradle.properties` | свойства вида ключ=значение; команды иногда держат версии здесь (`springVersion=6.1.2`) | устаревший способ централизации версий - но это тоже централизация |
| `buildSrc/` или `build-logic/` | **convention-плагины** - Gradle-код, применяемый к модулям | могут добавлять модулям зависимости невидимо; всегда проверяй эти каталоги |
| скрипты через `apply from: 'x.gradle'` | произвольная общая логика сборки | то же самое - могут невидимо добавлять зависимости |
| `gradle.lockfile`, `*.lockfile` | фиксация (locking) зависимостей | если есть - команда пиннит разрезолвленные версии; хороший знак |

DSL два: Groovy DSL (`build.gradle`) и Kotlin DSL (`build.gradle.kts`). Одно и то же
объявление выглядит чуть по-разному; твои поиски должны покрывать оба варианта:

```groovy
// Groovy DSL
implementation 'org.apache.commons:commons-lang3:3.14.0'
implementation project(':core')
```
```kotlin
// Kotlin DSL
implementation("org.apache.commons:commons-lang3:3.14.0")
implementation(project(":core"))
```

## 2. Координаты зависимостей и формы записи

Координата зависимости - `group:artifact:version`, например
`com.fasterxml.jackson.core:jackson-databind:2.17.1`. Встречаются такие формы записи:

| Форма | Пример | Значение |
|---|---|---|
| Строковый литерал | `implementation("g:a:1.2.3")` | прямое объявление с зашитой версией |
| Без версии | `implementation("g:a")` | версия приходит из platform/BOM или constraint - это нормально, найди откуда |
| Ссылка на каталог | `implementation(libs.jackson.databind)` | версия живёт в `libs.versions.toml`; точки в алиасе соответствуют дефисам в каталоге (`jackson-databind`) |
| Проект | `implementation(project(":core"))` | зависимость от другого модуля этой же сборки |
| Platform | `implementation(platform("g:bom:1.0"))` | импорт BOM: пиннит версии целого семейства библиотек |
| Enforced platform | `enforcedPlatform(...)` | то же, но перекрывает даже явно запрошенные версии - грубый инструмент, стоит флажить |
| Файлы | `implementation(files("libs/x.jar"))`, `fileTree(...)` | jar, закоммиченный в репозиторий - полностью обходит управление зависимостями |
| Constraint | `constraints { implementation("g:a:1.2.3") }` | НЕ добавляет зависимость; только пиннит её версию, ЕСЛИ она появится транзитивно |

## 3. Конфигурации (scope-ы) и что они значат

«Конфигурация» - слово Gradle для области действия зависимости. Важные:

| Конфигурация | Значение | Типичные ошибки, которые ищем |
|---|---|---|
| `implementation` | нужна для компиляции и работы этого модуля; **скрыта** от compile classpath потребителей | правильный вариант по умолчанию почти для всего |
| `api` | как implementation, но **протекает** к потребителям: все, кто зависит от модуля, компилируются и против неё | злоупотребление; `api` в модуле-приложении (листе), который никто не потребляет |
| `compileOnly` | только компиляция, в рантайме отсутствует (аннотации, provided-стиль servlet API) | использование для того, что реально нужно в рантайме → `ClassNotFoundException` |
| `runtimeOnly` | только рантайм, не в compile classpath (JDBC-драйверы, реализации логирования) | драйверы как `implementation` (работает, но загрязняет compile classpath) |
| `testImplementation` / `testRuntimeOnly` | то же для тестов | тестовые библиотеки (JUnit, Mockito, AssertJ) в `implementation` - протекают в боевой classpath |
| `annotationProcessor` / `kapt` / `ksp` | обработчики аннотаций (Lombok, MapStruct, Dagger) | процессор как `implementation` - замедляет сборку, загрязняет classpath |
| `developmentOnly` | Spring Boot dev tools | почти не путают |
| `compile`, `runtime`, `testCompile`, `testRuntime` | **удалённые** легаси-конфигурации (Gradle < 7) | любое вхождение = очень старые скрипты сборки - флажить |

### `api` против `implementation` - самое важное различие

Модуль `:core` объявляет `api("com.google.guava:guava:33.0.0-jre")`. Теперь каждый модуль
с `implementation(project(":core"))` может компилироваться против Guava, не объявляя её.
Результат:
- скрытая связность - потребители молча зависят от Guava;
- любое изменение Guava перекомпилирует всех потребителей (медленнее сборка);
- удаление Guava из `:core` ломает модули, которые её никогда не объявляли.

`api` корректна **только** когда публичные типы модуля раскрывают типы библиотеки
(например, публичный метод возвращает `ImmutableList`). Всё остальное - `implementation`.

## 4. Version catalog (`gradle/libs.versions.toml`)

Современный стандарт централизации версий. Структура:

```toml
[versions]
junit = "5.10.2"
allure = "2.25.0"
jackson = "2.17.1"

[libraries]
junit-jupiter = { module = "org.junit.jupiter:junit-jupiter", version.ref = "junit" }
allure-junit5 = { module = "io.qameta.allure:allure-junit5", version.ref = "allure" }
jackson-databind = { module = "com.fasterxml.jackson.core:jackson-databind", version.ref = "jackson" }

[bundles]
testing = ["junit-jupiter", "allure-junit5"]

[plugins]
allure = { id = "io.qameta.allure", version.ref = "allure" }
```

Использование в модуле: `testImplementation(libs.junit.jupiter)`,
`implementation(libs.jackson.databind)`, `alias(libs.plugins.allure)`. В здоровом мультимодульном проекте версии объявлены
**только** в каталоге (или в другом одном месте) - в build-файлах модулей нет числовых
литералов версий.

## 5. BOM / platform

Семейства библиотек (Spring, Jackson, JUnit, Kotlin, AWS SDK, Testcontainers…) публикуют
BOM - POM, который пиннит совместимые версии всех членов семейства. В Gradle:

```kotlin
testImplementation(platform("org.junit:junit-bom:5.10.2"))
testImplementation("org.junit.jupiter:junit-jupiter") // без версии - придёт из BOM
implementation(platform("org.springframework.boot:spring-boot-dependencies:3.3.2"))
implementation("org.springframework.boot:spring-boot-starter-web") // то же самое для приложения
```

Spring Boot-проекты могут вместо этого использовать плагин
`io.spring.dependency-management` - тоже приемлемо. Что НЕприемлемо: члены семейства с
вручную подобранными разными версиями (например, `jackson-databind:2.17.1` рядом с
`jackson-core:2.15.0`) - классический источник `NoSuchMethodError` в рантайме.

## 6. Как Gradle разрешает конфликты версий (отличается от Maven!)

Когда две зависимости тянут одну библиотеку разных версий, Gradle по умолчанию берёт
**самую высокую** версию (Maven берёт «ближайшую» - поведение другое, не путай их).
Следствия:
- Возможны тихие апгрейды; команды иногда борются с ними через `force`.
- `resolutionStrategy { force("g:a:1.0") }` и `eachDependency { useVersion(...) }` -
  грубые инструменты, которые обычно **маскируют** реальный конфликт, а не устраняют его
  причину. Чистые инструменты: constraints, platform/BOM или обновление отставшей
  зависимости.

## 7. Где прячутся зависимости - чек-лист

Прежде чем заключить, что «с зависимостями модуля всё ясно», проверь все укрытия:
1. Блоки `allprojects { }` / `subprojects { }` в **корневом** build-файле.
2. Convention-плагины в `buildSrc/src/main/...` или `build-logic/` (ищи в них
   `dependencies {` и `implementation(`).
3. Скрипты, подключённые через `apply from:`.
4. `buildscript { dependencies { classpath(...) } }` - зависимости времени сборки.
5. Version catalog и `gradle.properties` (там версии, а не зависимости, но это часть картины).

## 8. Полезные команды (запускай, только если есть Gradle wrapper и запуск разрешён)

| Команда | Что показывает |
|---|---|
| `./gradlew projects` | список модулей |
| `./gradlew :app:dependencies --configuration runtimeClasspath` | полное разрезолвленное дерево зависимостей одного модуля |
| `./gradlew :app:dependencyInsight --dependency jackson-databind` | почему выбрана конкретная версия |
| `./gradlew buildEnvironment` | зависимости времени сборки (плагины) |

Для большинства правил достаточно статического чтения файлов; запускай команды только
когда правило это предлагает и окружение позволяет. Никогда не запускай произвольный код
проекта.

## 9. Проект автотестов - что меняется

Иногда проверяемый проект - не приложение, а отдельный проект автотестов (тестовый
фреймворк): JUnit 5/TestNG, Selenide/Selenium, RestAssured, Allure, Cucumber,
Testcontainers, WireMock, Awaitility. Все правила применяются БЕЗ изменений; отличаются
только типичные примеры и одна деталь со scope-ами.

Универсальный принцип для конфигураций - важно, ОТКУДА код использует библиотеку:
- код в `src/main` использует библиотеку → `implementation`;
- библиотека нужна только коду в `src/test` → `testImplementation`.

В проекте автотестов степы, клиенты и утилиты часто лежат в `src/main` - тогда JUnit или
Selenide в `implementation` НЕ нарушение. В обычном приложении та же строка - нарушение.
Определи назначение проекта на Шаге 2 SKILL.md и суди по нему.

Типичные семейства и ловушки автотестов:
- `org.junit.*` - выравнивай через BOM `org.junit:junit-bom`. JUnit 4 (`junit:junit`) и
  JUnit 5 вместе допустимы только через `junit-vintage-engine` (осознанная миграция),
  иначе флажь пару.
- `io.qameta.allure` - все артефакты `allure-*` одной версии (есть
  `io.qameta.allure:allure-bom`). Allure требует агента `org.aspectj:aspectjweaver`:
  он подключается как javaagent (обычно отдельная конфигурация `agent` или
  `testRuntimeOnly`), а не как обычная `implementation`, и его версия должна
  соответствовать требованиям используемой версии Allure.
- `org.seleniumhq.selenium` - члены семейства одной версии. Selenide уже тянет Selenium
  транзитивно: явное добавление своих версий Selenium рядом с Selenide - источник
  конфликтов (проверяй по G-C-07/G-C-13).
- `org.testcontainers` - через `org.testcontainers:testcontainers-bom`.

## 10. Дерево зависимостей и транзитивные конфликты (частая причина «проект не собрать»)

Многие реальные проблемы не видны в самих build-файлах: их создают **транзитивные**
зависимости - притянутые не напрямую, а через другие библиотеки. Gradle берёт самую
высокую версию (§6), поэтому одна транзитивная библиотека может молча подняться до версии,
несовместимой с остальным кодом, - и проект падает в рантайме, хотя в `dependencies { }`
всё выглядит нормально.

Поэтому, **если есть Gradle wrapper и запуск разрешён**, не ограничивайся чтением
build-файлов - посмотри дерево:
```
./gradlew :app:dependencies --configuration runtimeClasspath
./gradlew :app:dependencyInsight --dependency jackson-databind
```
На что смотреть: пометки `->` (версия подменена при резолюции); один и тот же
`group:artifact` разных версий в разных ветках; разъехавшиеся транзитивные версии членов
одного семейства (jackson-*, spring-*, junit-*, selenium-*) - кандидат на platform/BOM.
Найденное записывай под тем же правилом, что и по смыслу (обычно G-C-07 - выравнивание
семейств, или конфликт версий), с пометкой «транзитивно, из dependencies».

Если запуск НЕ разрешён - отметь в отчёте («Требует внимания человека»), что полную
картину даёт `./gradlew :<модуль>:dependencies`, а статический обзор build-файлов
транзитивные конфликты пропускает.

## 11. Мини-глоссарий

- **Модуль / подпроект** - компонент мультимодульной сборки со своим build-файлом.
- **Конфигурация** - именованная область действия зависимости (`implementation`, `api`, …).
- **Version catalog** - центральный TOML-файл с версиями/библиотеками/плагинами.
- **BOM / platform** - импортируемый POM, пиннящий версии семейства библиотек.
- **Convention-плагин** - общая логика сборки в `buildSrc`/`build-logic`, применяемая к модулям.
- **Транзитивная зависимость** - притянута косвенно, через прямую зависимость.
- **Расхождение версий (version drift)** - одна библиотека с разными версиями в разных модулях.
