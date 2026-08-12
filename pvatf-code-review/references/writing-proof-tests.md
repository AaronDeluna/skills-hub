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

## Фреймворк и язык

- **Только JUnit 5** (`org.junit.jupiter`): импорт `org.junit.jupiter.api.Test`, ассерты
  `org.junit.jupiter.api.Assertions`. JUnit 4 не используем.
- Язык теста - под язык кода: Java-код -> Java-тест, Kotlin -> Kotlin-тест (или Java, если
  класс public и вызывается просто).
- Посмотри существующие тесты в `src/test` и повтори их стиль (расположение, статик-импорты).

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

## Скелеты

Java:
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

Kotlin:
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

Ожидаемое исключение (когда правильное поведение - именно бросить):
```java
assertThrows(IllegalArgumentException.class, () -> obj.method(null));
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

## Как прогнать точечно (только свой тест, а не всю базу)

Maven:
```
mvn -q -pl <относительный/путь/модуля> -Dtest='ReviewProofF1*' test
# JUnit5 через surefire: если не подхватывает, добавь -DfailIfNoTests=false
```

Gradle:
```
./gradlew :<модуль>:test --tests 'reviewproof.ReviewProofF1*'
```

Проверка зелёной базы (Шаг 2) - те же команды без фильтра по классу, либо просто
`mvn -q test` / `./gradlew test` для области ревью.

## Компиляция и checkstyle (Шаг 2 и обязательный Шаг 6)

Компиляция боевого кода и тестов (без прогона тестов):
```
mvn -q -DskipTests compile test-compile        # Maven
./gradlew compileJava compileTestJava           # Gradle (для Kotlin: compileKotlin compileTestKotlin)
```

Checkstyle - только если он настроен в проекте. Признаки: плагин `maven-checkstyle-plugin`
в `pom.xml`, плагин `checkstyle` в Gradle, или файл `checkstyle.xml` / каталог
`config/checkstyle/`.
```
mvn -q checkstyle:check                          # Maven
./gradlew checkstyleMain checkstyleTest          # Gradle
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
