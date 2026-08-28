# Как писать и запускать тесты-доказательства (JUnit, Maven/Gradle)

Прочитай перед Шагом 4. Здесь: как определить фреймворк, куда класть тест, как его написать,
как прогнать точечно и как прочитать результат.

## Главный принцип теста-доказательства

Тест проверяет **правильное (ожидаемое) поведение**. Тогда:
- тест **упал** -> код ведёт себя неправильно -> баг **ПОДТВЕРЖДЁН**;
- тест **прошёл** -> код корректен -> замечание **НЕ ПОДТВЕРДИЛОСЬ** (псевдопроблема).

Не пиши тест, который «ждёт баг» (`assertThrows` на то, что баг кинет). Пиши тест, который
требует правильного результата. Иначе доказываешь не то и обманываешь себя.

Пример логики: подозреваешь, что `discount(100, 0)` делит на ноль. Правильное поведение -
вернуть 100 (скидки нет). Пишешь `assertEquals(100, discount(100, 0))`. Если внутри деление
на ноль - тест упадёт с `ArithmeticException`, и это доказательство. Если вернёт 100 - бага
нет.

## Тест-фреймворк - определи ДИНАМИЧЕСКИ (не предполагай JUnit 5)

Не зашивай фреймворк. Определи тот, что реально используется в проекте, и пиши свои тесты в
нём же - иначе они не соберутся и не запустятся вместе с остальными.

Важно: **зависимости сборки НЕ дают однозначного ответа** - в одном `pom.xml`/`build.gradle`
часто объявлено сразу несколько раннеров (например, `junit-jupiter` + `junit-vintage`, чтобы
рядом жили JUnit 5 и старые JUnit 4-тесты; или JUnit рядом с TestNG). Поэтому решает не
список зависимостей, а то, что реально написано в тестах.

Как определить (по приоритету):
1. **Существующие тесты в `src/test`** - главный и решающий сигнал. Открой несколько файлов
   (ближайших к области ревью) и посмотри импорт аннотации `@Test`:
   - `org.junit.jupiter.api.Test` -> **JUnit 5** (Jupiter);
   - `org.junit.Test` -> **JUnit 4**;
   - `org.testng.annotations.Test` -> **TestNG**;
   - Kotlin + `io.kotest...`/`kotlin.test` -> Kotest / kotlin-test.
   Повтори их стиль: расположение, статик-импорты ассертов, базовые классы.
2. **Если раннеров в тестах несколько** (проект правда смешанный) - не выбирай «по
   зависимостям», а бери тот, которым написаны тесты **рядом с проверяемым кодом** (в том же
   модуле/пакете); при равенстве - преобладающий. Свой тест пиши в нём.
3. **Зависимости сборки** - только как подсказка, когда тестов ещё нет вообще:
   `org.junit.jupiter*` -> JUnit 5; `junit:junit:4*` -> JUnit 4; `org.testng` -> TestNG.
   Если объявлено несколько - выбрать нельзя, это NEEDS-HUMAN (спроси/отметь), пока не
   появится хоть один тест-образец.
4. Ничего нет (ни тестов, ни зависимостей) -> возьми **JUnit 5** как разумный дефолт, но
   отметь это в отчёте.

Запиши обнаруженный фреймворк в блок «Контекст» заметок и используй его скелет ниже.

Язык теста - под язык кода: Java-код -> Java-тест, Kotlin -> Kotlin-тест (или Java, если
класс public и вызывается просто).

## Именование

- Идентификаторы (класс, метод) - **обычные латинские**, не кириллицей.
- Класс: `ReviewProofF1DiscountTest` (F1 - ID замечания из заметок).
- Метод: короткое английское имя вида `discountWithZeroPercentReturnsOriginalPrice`.
- Человекочитаемое описание - через `@DisplayName("...")`, там можно по-русски.

## Куда класть тест

В тестовый корень модуля, которому принадлежит область ревью:
- Java:   `<модуль>/src/test/java/reviewproof/...`
- Kotlin: `<модуль>/src/test/kotlin/reviewproof/...`

Отдельный пакет `reviewproof` - чтобы в конце всё легко убрать одной папкой. Один тест на
одно замечание.

## Скелеты (возьми под обнаруженный фреймворк)

JUnit 5 (Jupiter), Java:
```java
package reviewproof;

import app.Pricing;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;

class ReviewProofF1DiscountTest {
    @Test
    @DisplayName("Скидка 0% возвращает исходную цену")
    void discountWithZeroPercentReturnsOriginalPrice() {
        // правильное поведение: скидка 0% -> цена не меняется
        assertEquals(100, new Pricing().discount(100, 0));
    }
}
```

JUnit 5 (Jupiter), Kotlin:
```kotlin
package reviewproof

import app.Pricing
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Assertions.assertEquals

class ReviewProofF1DiscountTest {
    @Test
    @DisplayName("Скидка 0% возвращает исходную цену")
    fun discountWithZeroPercentReturnsOriginalPrice() {
        assertEquals(100, Pricing().discount(100, 0))
    }
}
```

JUnit 4, Java (если в проекте JUnit 4):
```java
package reviewproof;

import app.Pricing;
import org.junit.Test;
import static org.junit.Assert.*;

public class ReviewProofF1DiscountTest {
    @Test
    public void discountWithZeroPercentReturnsOriginalPrice() {
        assertEquals(100, new Pricing().discount(100, 0));
    }
}
```

TestNG, Java (если в проекте TestNG):
```java
package reviewproof;

import app.Pricing;
import org.testng.annotations.Test;
import static org.testng.Assert.assertEquals;

public class ReviewProofF1DiscountTest {
    @Test
    public void discountWithZeroPercentReturnsOriginalPrice() {
        assertEquals(new Pricing().discount(100, 0), 100); // в TestNG порядок: actual, expected
    }
}
```

Ожидаемое исключение (когда правильное поведение - именно бросить):
```
JUnit 5: assertThrows(IllegalArgumentException.class, () -> obj.method(null));
JUnit 4: @Test(expected = IllegalArgumentException.class)
TestNG:  @Test(expectedExceptions = IllegalArgumentException.class)
```

Конкурентность (JUnit 5, Java) - проверяем инвариант под нагрузкой:
```java
int threads = 8, perThread = 1000;
ExecutorService pool = Executors.newFixedThreadPool(threads);
CountDownLatch latch = new CountDownLatch(threads);
Counter counter = new Counter(); // проверяемый класс
for (int i = 0; i < threads; i++) pool.submit(() -> {
    for (int j = 0; j < perThread; j++) counter.increment();
    latch.countDown();
});
latch.await();
pool.shutdown();
assertEquals(threads * perThread, counter.get()); // упадёт, если не потокобезопасно
```
(явные типы, без `var` - в проекте `var` запрещён; нужны импорты
`java.util.concurrent.ExecutorService/Executors/CountDownLatch`.)

## Сначала определи раннер ДИНАМИЧЕСКИ (не зашивай `mvn`/`./gradlew`)

Не предполагай конкретную команду сборки - определи её по проекту. Ниже команды написаны
через плейсхолдер `<RUN>`; сначала вычисли, что это за команда, и дальше подставляй её.

1. **Какая система сборки** (по файлам в корне модуля/проекта): есть `pom.xml` -> Maven;
   есть `build.gradle` / `build.gradle.kts` / `settings.gradle(.kts)` -> Gradle. Есть и то,
   и другое - бери ту, к которой относится область ревью (где лежит проверяемый код).
2. **Есть ли wrapper** (предпочитается системному бинарнику - он фиксирует версию сборщика):
   - Maven: `./mvnw` (или `mvnw.cmd` на Windows) рядом с проектом -> `<RUN>` = `./mvnw`.
     Иначе, если в `PATH` есть `mvn` -> `<RUN>` = `mvn`.
   - Gradle: `./gradlew` (или `gradlew.bat`) -> `<RUN>` = `./gradlew`.
     Иначе, если в `PATH` есть `gradle` -> `<RUN>` = `gradle`.
   Wrapper обычно лежит в корне проекта; если область ревью - вложенный модуль, ищи wrapper
   вверх по дереву до корня.
3. **Проверь, что раннер рабочий**, прежде чем полагаться на него: Maven - `<RUN> -v`,
   Gradle - `<RUN> --version`. Команда не находится или падает -> раннера фактически нет.
4. **Раннера нет / запуск запрещён** -> прогон невозможен: тесты всё равно пиши, но их
   статус в отчёте `НЕ УДАЛОСЬ ПРОВЕРИТЬ (раннер недоступен)` с точной командой (уже с
   подставленным `<RUN>`), которую человек выполнит вручную.

Запиши определённый `<RUN>` и систему сборки в блок «Контекст» заметок и используй дальше.

## Как прогнать точечно (только свой тест, а не всю базу)

Подставляй вычисленный `<RUN>`.

Maven (`<RUN>` = `./mvnw` или `mvn`):
```
<RUN> -q -pl <относительный/путь/модуля> -Dtest='ReviewProofF1*' -DfailIfNoTests=false test
```

Gradle (`<RUN>` = `./gradlew` или `gradle`):
```
<RUN> :<модуль>:test --tests 'reviewproof.ReviewProofF1*'
```

Проверка зелёной базы (Шаг 2) - те же команды без фильтра по классу, либо просто
`<RUN> test` для области ревью.

## Компиляция и checkstyle (Шаг 2 и обязательный Шаг 6)

Компиляция боевого кода и тестов (без прогона тестов), с тем же `<RUN>`:
```
<RUN> -q -DskipTests compile test-compile        # Maven
<RUN> compileJava compileTestJava                 # Gradle (для Kotlin: compileKotlin compileTestKotlin)
```

Checkstyle - только если он настроен в проекте. Признаки: плагин `maven-checkstyle-plugin`
в `pom.xml`, плагин `checkstyle` в Gradle, или файл `checkstyle.xml` / каталог
`config/checkstyle/`.
```
<RUN> -q checkstyle:check                          # Maven
<RUN> checkstyleMain checkstyleTest                # Gradle
```
Если checkstyle не настроен - не запускай и отметь «не настроен». Если настроен - твои
добавленные тестовые файлы обязаны проходить его без новых нарушений: оформляй их сразу по
правилам проекта (порядок и отсутствие лишних импортов, отступы, длина строк, при
необходимости javadoc). При падении смотри отчёт checkstyle (`target/checkstyle-result.xml`
или `build/reports/checkstyle/`) и правь СВОИ файлы, а не боевой код.

## Как прочитать результат

- **Тест упал (FAILED/ERROR)** и упал ПО ТОЙ причине, что ты предсказывал (тот ассерт или
  то исключение) -> **ПОДТВЕРЖДЕНО**. Сохрани в заметки текст падения (ожидал X, получил Y,
  или стектрейс исключения) - он пойдёт в отчёт как доказательство.
- **Тест прошёл (PASSED)** -> **НЕ ПОДТВЕРДИЛОСЬ**. Поведение корректно, замечание снимается.
- **Тест упал не по той причине** (компиляция, NPE в самом тесте, не тот класс) -> это не
  доказательство. Почини тест; не выходит - **НЕ УДАЛОСЬ ПРОВЕРИТЬ**, опиши помеху.
- **Сборку/тесты запустить нельзя** (нет окружения) -> **НЕ УДАЛОСЬ ПРОВЕРИТЬ (сборка
  недоступна)**; оставь тест как заготовку и дай в отчёте точную команду прогона.

## Важные предостережения

- Не трогай боевой код, чтобы тест позеленел. Ты измеряешь, а не чинишь.
- Тесту нужен доступ к проверяемому классу: тот же модуль и корректный пакет/видимость.
  Если класс package-private - положи тест в тот же пакет (не в `reviewproof`), это
  допустимое исключение; отметь такие файлы в отчёте, чтобы потом убрать.
- Не оставляй после себя красную сборку случайно. Осознанно оставленный регрессионный тест
  на реальный баг - законно красный, но это должно быть явно указано в отчёте.
- Прогоняй тесты по одному/последовательно: параллельные прогоны в одном модуле мешают друг
  другу (общий каталог сборки).
- В коде тестов **не используй `var`** - он запрещён в проекте. Пиши явные типы. Также держи
  тесты чистыми по checkstyle (см. Шаг 6): порядок и отсутствие лишних импортов, отступы,
  длина строк.
