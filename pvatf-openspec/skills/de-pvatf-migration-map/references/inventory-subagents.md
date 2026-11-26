# Сабагенты Этапа 2: инвентаризация модулей и технологии проекта (для de-pvatf-migration-map)

Часть скилла `de-pvatf-migration-map`. Открывай на Этапе 2, когда запускаешь этих сабагентов.
Общий список сабагентов карты - `references/subagents.md`.

# 1. Сабагент инвентаризации модулей

## Обязательное требование

Подсчёты по исходникам модулей (Этап 2, п.2) выполняются **только через сабагентов**. Вывод
grep по большому модулю огромный - к тебе он попадать не должен, тебе нужен только свёрнутый
результат. Единственное исключение - инструмент сабагентов физически отсутствует: тогда
считай сам по `references/inventory-guide.md`, по одному модулю, и запиши это в журнал карты.

## Сколько сабагентов

```
число сабагентов = min(3, число модулей)
```

Раздели модули между ними как можно ровнее, без пересечений, чтобы вместе покрыть ВСЕ модули.
Один модуль в проекте - один сабагент.

## Промпт (копируй дословно, подставь <...>)

```
Ты делаешь инвентаризацию исходников для СПИСКА модулей одного проекта. Только считаешь и
ищешь командами. Не меняй файлы. Не читай target/, build/, .gradle/, .idea/, *.jar, *.class.
Не открывай файлы целиком, кроме случаев, когда это прямо сказано. Верни ТОЛЬКО заполненные
шаблоны (по одному на модуль), без рассуждений и без сырого вывода команд.

Проект: <абсолютный путь к корню проекта>
Модули (обработай КАЖДЫЙ): <модуль: путь к его каталогу src>, <модуль: путь>

Для КАЖДОГО модуля (SRC - его каталог src) выполни команды:

1. find SRC \( -name "*.java" -o -name "*.kt" \) | wc -l
2. find SRC \( -name "*.java" -o -name "*.kt" \) -exec cat {} + | wc -l
3. grep -rE "^\s*@Test\b" --include=*.java --include=*.kt SRC | wc -l
4. grep -rhoE "^import (static )?[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+" --include=*.java --include=*.kt SRC | sed -E "s/^import (static )?//" | sort | uniq -c | sort -rn | head -40
5. grep -rhoE "(extends|implements) [A-Z][A-Za-z0-9_<>, ]+" --include=*.java SRC | sort | uniq -c | sort -rn | head -30
6. grep -rhoE "^\s*@[A-Z][A-Za-z0-9_]+" --include=*.java --include=*.kt SRC | sed -E "s/^\s+//" | sort | uniq -c | sort -rn | head -30
7. find SRC \( -name "*.java" -o -name "*.kt" \) -exec wc -l {} + | sort -rn | head -15
8. find SRC -path "*resources*" -type f | head -40
9. grep -rlE "^import (static )?(ru\.sber\.qa|io\.perfeccionista)\." --include=*.java --include=*.kt SRC | wc -l
10. find SRC -name "*Utils.java" -o -name "*Helper.java" -o -name "*Wrapper.java" -o -name "Base*.java" -o -name "Abstract*.java" | head -40

Верни на каждый модуль РОВНО такой шаблон (заголовки сохрани):

# Инвентаризация: <модуль>

- Файлов: <n> · Строк: <n> · Тестов (@Test): <n>
- Уже на PVATF файлов: <n>

## Топ импортов (пакет - сколько раз)
- <пакет> - <n>      (JDK-пакеты java.*, javax.* не перечисляй)

## Базовые классы / интерфейсы (имя - сколько наследников)
- <имя> - <n>

## Аннотации (имя - сколько)
- <имя> - <n>

## Большие файлы (путь - строк)
- <путь> - <n>

## Конфиги и ресурсы
- <путь>

## Самописные обёртки и базовые классы (кандидаты в legacy)
- <путь>

## Команды, которые не выполнились
- <номер команды: ошибка>   (если все выполнились - напиши: нет)
```

## Что делать с результатами

1. Каждый шаблон запиши как есть в `openspec/changes/<имя>/outputs/inventory/<модуль>.md`.
2. **Ворота:** шаблон должен быть на КАЖДЫЙ модуль из паспорта. Не хватает - дозапусти
   сабагента на недостающие модули.
3. Файлы-образцы для матрицы (Этап 3) выбираешь и читаешь ты сам - не больше 3 на шаблон.

# 2. Сабагент технологий проекта

## Когда запускать

Этап 2, п.0, **только если пользователь сам не назвал технологии**. Назвал - сабагент не
нужен, бери список пользователя. Сабагент один, запускается один раз на весь проект.

## Промпт (копируй дословно, подставь <...>)

```
Ты определяешь, с какими технологиями работает проект автотестов. Только считаешь и ищешь
командами. Не меняй файлы. Не читай target/, build/, .gradle/, .idea/, *.jar, *.class. Файлы
исходников целиком не открывай. Верни ТОЛЬКО заполненный шаблон отчёта, без рассуждений и
без сырого вывода команд.

Проект: <абсолютный путь к корню проекта>

Выполни команды из корня проекта:

1. find . \( -name pom.xml -o -name "build.gradle" -o -name "build.gradle.kts" -o -name "libs.versions.toml" \) -not -path "*/target/*" -not -path "*/build/*"
2. Для каждого найденного файла сборки:
   grep -hoE "<artifactId>[^<]+</artifactId>|['\"][a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+(:[^'\"]*)?['\"]" <файл> | sort -u
3. grep -rhoE "^import (static )?[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+" --include=*.java --include=*.kt . | sed -E "s/^import (static )?//" | sort | uniq -c | sort -rn | head -80
4. find . -path "*resources*" -type f \( -name "*.properties" -o -name "*.yml" -o -name "*.yaml" -o -name "*.conf" -o -name "*.json" \) -not -path "*/target/*" -not -path "*/build/*" | head -60
5. grep -rhoiE "(jdbc:[a-z0-9]+|kafka|bootstrap\.servers|grpc|graphql|wss?://|openshift|kubernetes|elastic|opensearch|selenide|playwright|appium|rabbit|mq|redis|mongo|s3|ftp|smtp|otel|opentelemetry)" --include=*.properties --include=*.yml --include=*.yaml --include=*.conf . | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn | head -40

По результатам определи технологии. Подсказка, по каким признакам (зависимость или пакет
импорта -> технология):
- io.restassured, okhttp3, org.apache.http, retrofit2, feign, java.net.http -> rest
- java.sql, javax.sql, org.sql2o, org.jooq, org.hibernate, org.springframework.jdbc, jdbc:... -> db (впиши КАКАЯ база: postgresql / oracle / mssql / ... - по драйверу и строке jdbc)
- org.apache.kafka, org.springframework.kafka -> kafka
- io.grpc, com.google.protobuf -> grpc
- graphql -> graphql
- websocket, org.java_websocket -> websocket
- com.codeborne.selenide, org.openqa.selenium -> ui-selenide
- com.microsoft.playwright -> ui-playwright
- io.appium -> appium-android / appium-ios
- io.fabric8, io.kubernetes, openshift -> openshift
- org.opensearch, org.elasticsearch, co.elastic -> opensearch
- org.testcontainers -> testcontainers
- io.qameta.allure -> allure
- org.awaitility -> timeouts
- com.github.tomakehurst.wiremock, org.mockserver -> моки (sbermock)
- io.opentelemetry -> otel
- com.rabbitmq, javax.jms, com.ibm.mq -> очередь, не Kafka (впиши какая)
- org.junit.jupiter -> runner JUnit 5; org.junit (без jupiter) -> runner JUnit 4; org.testng -> runner TestNG; io.cucumber -> runner Cucumber
- org.assertj, org.hamcrest, net.javacrumbs.jsonunit, org.skyscreamer.jsonassert -> проверки (asserts)
Нашёл технологию, которой нет в подсказке, - тоже впиши, своими словами.
Признаков технологии нет - не вписывай её.

Верни РОВНО такой шаблон (заголовки сохрани):

# Технологии проекта

| Метка | Технология (что именно) | Признак: зависимости | Признак: импорты (пакет - сколько раз) | Признак: конфиги | Модули |
|-------|-------------------------|----------------------|-----------------------------------------|------------------|--------|
| <rest> | <REST API, RestAssured> | <io.rest-assured:rest-assured> | <io.restassured - 143> | <-> | <модули, где встречается> |

## Тест-фреймворк
- <JUnit 5 / TestNG / ...> - <признак>

## Библиотеки проверок
- <AssertJ / Hamcrest / JsonUnit / свои классы> - <пакет - сколько раз>

## Пакеты из топа импортов, которые не удалось отнести к технологии
- <пакет - сколько раз>     (JDK-пакеты java.*, javax.* не перечисляй; нет - напиши: нет)

## Команды, которые не выполнились
- <номер команды: ошибка>   (если все выполнились - напиши: нет)
```

## Что делать с отчётом

1. Запиши отчёт как есть в `openspec/changes/<имя>/outputs/inventory/technologies.md`.
2. Каждая строка таблицы отчёта -> строка таблицы «Технологии проекта» в паспорте карты
   (метку сверь с `references/frame-topics.md`, порядок расставь по правилу из Этапа 2).
3. «Пакеты, которые не удалось отнести» - не выбрасывай: на Этапе 3 каждый такой пакет
   должен попасть либо в строку `G`, либо в «остаётся как есть».
4. Отчёт не по шаблону -> запусти сабагента ещё раз с тем же заданием. Только если
   вызов сабагента вернул ошибку (не «долго» и не «проще самому») -> покажи ошибку в чате, запиши в журнал карты `сабагент не запустился: <ошибка>` - выполни команды промпта сам.
