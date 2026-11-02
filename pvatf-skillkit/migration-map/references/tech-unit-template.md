# Template of a technology unit card (type `tech`)

Path: `.gigacode/data/migration/units/M-<nnn>.md`. One `tech` unit is the full migration of ONE
technology: from the analysis to the review. The work in the unit has substeps `S-<nn>`.
The executor does the substeps in their order, all of them one after another in one chat.
The chat context becomes shorter automatically during the work.
If the chat stops before the end, the unit stays `in-progress`. The next chat opens the card
and takes the first substep that is not done.

The executor reads the card in a DIFFERENT chat. The executor did not see your analysis.
Write the card so that the executor can do the work from the card and does not need to guess.

```markdown
---
id: M-<nnn>
type: tech
core_mode: new | in-place
tech: <метка технологии: common / rest / db / kafka / ...>
phase: 2
status: todo
depends_on: [<M-nnn>, ...]
covers: [<G-n>, <L-n>, ...]
---

# M-<nnn> · Миграция технологии <tech>

## Цель
<2-3 предложения с именами: «Все обращения к REST идут через `OrderSteps` и `ClientSteps`.
Проверки ответов - через matchers фрейма. RestAssured и классы `RestHelper`, `BaseApiTest`
удалены».>

## Целевая картина
- Блок: `T-<tech>` в разделе 2 карты (исполнитель читает его до правок)
- Классы, которые появятся (из `ARCHITECTURE.md`): <имена и пакеты>
- Что из старого исчезнет (поимённо): <классы, зависимости, конфиги>

## Разбор технологии
Кто и как обращается к технологии сейчас. Заполняет `migration-map`; подшаг `S-01`
перепроверяет по текущему коду.

Как проект пользуется технологией сейчас (так же будет и после миграции): <1-3 строки из блока `T`>

Данные подключения - копия таблицы «Перенос в фрейм» технологии из `CONNECTIONS.md`
(значения берутся отсюда, у человека не спрашиваются; удалённый старый файл - из истории
основной ветки `git show <ветка>:<файл>`):

| Файл фрейма | Ключ фрейма (со стендом, если стендов несколько) | Значение | Откуда (стенд, старый файл: ключ) |
|-------------|--------------------------------------------------|----------|-----------------------------------|
| <src/test/resources/...properties> | <...> | <адрес заглушек как в проекте / снаружи: SBERMOCK_TOKEN> | <ift, rest.properties: sbermock.host> |

Команды поиска потребителей:
- старая библиотека и старое ядро: `<точная команда grep>`
- прямые обращения к сервису фрейма в обход шагов: `<точная команда grep; обращений нет - "-">`

| Потребитель (файл) | Строк | Как обращается | Какие действия делает | Метод класса шагов, на который переходит | Подшаг |
|--------------------|-------|----------------|-----------------------|-------------------------------------------|--------|
| <путь> | <n> | старая библиотека / старое ядро `<Класс>` / фрейм напрямую | <POST /orders, GET /orders/{id}> | `<OrderSteps.createOrder>`, `<OrderSteps.getOrder>` | S-<nn> |

Отложены в другую технологию (файлы на несколько технологий): <файл - в каком юните; нет - `-`>

## Подшаги
Выполняются строго сверху вниз, по одному. Порядок строк - порядок выполнения.

| ID   | Вид    | Название | Файлов | Статус | Коммит |
|------|--------|----------|--------|--------|--------|
| S-01 | разбор | Перепроверить список потребителей | 0 | todo | - |
| S-02 | env    | <...> | <n> | todo | - |
| S-03 | core   | <...> | <n> | todo | - |
| S-04 | usage  | <...> | <n> | todo | - |
| S-<nn> | cleanup | <...> | <n> | todo | - |
| S-<nn> | review | Ревью кода технологии <tech> | <n> | todo | - |

Статусы подшага: `todo` / `in-progress` / `done` / `blocked`.

## S-01 · разбор · Перепроверить список потребителей
- Файлы: - (код не меняется)
- Что сделать:
  1. Выполнить обе команды из «Разбор технологии».
  2. Сравнить вывод с таблицей потребителей; на каждый новый файл дописать строку и подшаг.
  3. Проверить, что на каждое действие из колонки «Какие действия делает» есть метод в
     подшагах вида `core`.
- Итоговый результат: в таблице потребителей есть каждый файл из вывода команд, у каждого
  заполнены колонки «Метод класса шагов» и «Подшаг».
- Чекпоинт: число строк таблицы потребителей плюс число отложенных файлов = число файлов в
  выводе двух команд (без самих классов шагов).
- Сделано: -

## S-<nn> · <вид> · <название>
- Файлы (менять можно ТОЛЬКО их):

  | Файл (путь от корня проекта) | Строк | Действие |
  |------------------------------|-------|----------|
  | <путь> | <n> | изменить / создать / удалить |

- Что сделать:
  1. <конкретное действие с именами классов и методов и ссылкой на `G-<n>` / `L-<n>` / `D-<tech>-<n>`>
  2. <...>
- Критерии по файлам (только `usage` и `fix`; «Было» - числа из `inventory/analysis-<tech>.md`):

  | Файл | Было | Должно стать | Проверка |
  |------|------|--------------|----------|
  | <путь> | <ассертов 12, разбор в объект 2, обращений к старому 3, DTO `OrderDto`> | <запросы через `OrderSteps.createOrder`; проверки - `.should(...)`: код ответа - `D-rest-2`, поле-строка - `D-rest-3`> | `<grep -cE "assert|RestHelper|OrderDto" <файл>>` -> 0 |

- Итоговый результат: <что будет в проекте после подшага - проверяемый факт с именами>
- Чекпоинт: `<одна команда>` -> <что она должна вывести>
- Показательный тест: <путь к классу>#<метод>, команда `<...>`, ожидаемое время <...>
  (для видов `разбор`, `env`, `core` режима `new` - `-`)
- Док-основание: `D-<tech>-<n>` - <что из записи используется>
- Legacy под удаление: `L-<n>` - <что удалить и путь>; нет - `-`
- Правила подшага: `MR-<n>`, `MR-<n>`, ... (по `references/substep-rules.md`)
- Сделано: -

## Чекпоинты юнита
Выполняются в самом конце, когда все подшаги `done`. Юнит закрывается, только когда сошлись
все. Не сошёлся - исполнитель дописывает подшаг и выполняет его.

| №  | Что проверяется | Команда | Что должно получиться | Итог |
|----|-----------------|---------|-----------------------|------|
| C1 | проект компилируется | `<команда из паспорта>` | успешно | - |
| C2 | старого кода технологии нет | `<grep старых пакетов и классов старого ядра по всему проекту>` | пусто (кроме отложенных файлов: <список или "-">) | - |
| C3 | к фрейму обращаются только классы шагов | `<grep прямых обращений к сервису фрейма>` | только файлы: <классы шагов из плана> | - |
| C4 | каждый созданный класс кто-то вызывает | команда `C4` под таблицей - по каждому классу: <имена> | больше 0 у каждого | - |
| C5 | legacy технологии удалено | `<find / grep по строкам L этого юнита>` | пусто | - |
| C6 | тесты не пропали | `<команда подсчёта @Test>` | не меньше <n> | - |
| C7 | показательный тест технологии | `<команда запуска одного метода>` | зелёный | - |
| C8 | ревью пройдено | отчёт `.gigacode/data/migration/review/M-<nnn>.md` | неисправленных находок нет | - |

Команда `C4`: grep -rl "\b<Имя>\b" --include=*.java --include=*.kt <src> | grep -v "<Имя>.java" | wc -l

## Журнал выполнения
(заполняет migration-step)

### Таблица подтверждений
| Что использую из PVATF (класс/аннотация/метод/настройка) | Где в документации |
|----------------------------------------------------------|--------------------|

### Чаты
| Дата | Сделаны подшаги | Следующий подшаг |
|------|-----------------|------------------|

### Число тестов до начала юнита
-

## Блокер
(заполняется только при status: blocked)
-
```

## Which substeps and in which order

The order of the substep kinds is fixed. The kind sets the limits of the substep.
These limits are the same as the limits in the executor SKILL.md for the `env`, `core`,
`usage`, `cleanup` and `review` units.

| № | Kind | What it does | Number of substeps | Limit of one substep |
|---|------|--------------|--------------------|----------------------|
| 1 | `разбор` | does a check of the consumer list against the current code; does not change the code | one, always `S-01` | - |
| 2 | `env` | configuration of the technology; moves the values into the settings files of the framework | 1-2 | 6 files |
| 3 | `core` | makes the step classes of the technology (mode `new`) or changes the internals of the core (`in-place`) | one for each step class or for each group of actions | 6 files, 1000 lines |
| 4 | `usage` | moves the consumers to the step classes and their checks to matchers | as many as necessary: each consumer is in exactly one substep; from the bottom level to the top level, the tests are last | 3 files, 600 lines |
| 5 | `cleanup` | removes the legacy of the technology: code -> build -> configs | 1-3 | 15 files to remove |
| 6 | `review` | review of the technology code by subagents; fixes the simple findings | one for each 15 files | 15 files |

After `review`, the executor adds substeps of the kind `fix` or `usage` for the review findings
and for the unit checkpoints that failed. You do not plan these substeps.

Technology `common`: it has the substeps `env` (configuration of the framework,
`simplelogger.properties`) and `core` (the base test class).
Usually it has no `usage`, `cleanup` and `review` substeps. Its classes go into the `review`
of the first technology after it.
Remove from the table the checkpoints that this technology does not have.

## How to write a substep (strict)

The executor must understand the substep without the map and without this chat. Do a check of each substep:

1. **The name tells the result, with names.** Not «мигрировать тесты заказов», but «`OrderTests`,
   `OrderCancelTests`: запросы через `OrderSteps`, проверки на matchers».
2. **«Что сделать» has numbered actions, and each action has a name.** The name of a file,
   class, method or doc-notes record. «Заменить в `OrderTests` вызовы `RestHelper.post(...)` на
   `OrderSteps.createOrder(...)` - по `G-4`, `D-rest-3`». Do not use words without content:
   «мигрировать», «адаптировать», «привести в порядок», «при необходимости», «и так далее»,
   «соответствующие», «доработать».
3. **«Итоговый результат» is a fact that you can check with your eyes or with a command.** «В
   `OrderTests` нет импортов `io.restassured`; все запросы идут через `OrderSteps`; проверки
   - `.should(...)`». Not «тесты переведены на фрейм».
4. **«Чекпоинт» is one command and the expected output.** Usually it is a grep that must give
   an empty output, or a counter that must be more than zero. The checkpoint checks exactly the
   «Итоговый результат» of this substep.
5. **Substep `core`: the methods have names.** «Создать `OrderSteps` с методами `createOrder`,
   `getOrder`, `cancelOrder`; каждый возвращает валидируемый объект». The list of methods is the
   list of actions from the column «Какие действия делает» of the consumer table.
   Do not put into the list a method that no consumer needs.
6. **Substep `usage`: the connection step is explicit.** «Заменить в `<файл>` обращения `<какие>` на
   вызовы `<КлассШагов>.<метод>`; свой код запроса из файла убрать; проверки `<какие>`
   заменить на matchers по `D-<tech>-<n>`». The checkpoint: a grep for the old calls and the
   direct calls in the substep files gives an empty output.
7. **Each consumer from the table «Разбор технологии» is in exactly one `usage`
   substep,** and the column «Подшаг» has the number of this substep.
8. **The same card connects each class that the card makes.** After the `core` substep that
   makes a class, there is at least one `usage` substep that moves files to this class.
   If no file needs the class, do not make the class.
9. **The unit checkpoints have exact commands.** Make them from the search commands in «Разбор
   технологии» and from the `L` rows of the unit. The executor does not make up commands.
10. Do not write a code solution «по памяти» (from memory) in the card. Take the PVATF names only from the doc notes.
11. **Write «Итоговый результат» as one separate line for each file of the substep**, with the
    class name and with the result in this class:
    - `OrderSteps.java`: запросы через `RestSteps.post(...)`, каждый метод возвращает
      валидируемый объект;
    - `OrderTests.java`: проверки ответа - только `.should(...)` / `.shouldSoft(...)`
      matchers фрейма; `assertEquals`, `JsonNode`, свои обёртки над matcher - нет;
    - `OrderDto.java`: удалён.
    Do not write a rule code instead of a fact («V19 устранено», «по MR-41»). The executor
    cannot check a thing that the executor does not see.
12. **The substeps `usage` and `fix` have «Критерии по файлам»**: one row for each file with
    the action `изменить`. «Было» contains the numbers from the technology analysis
    (`inventory/analysis-<tech>.md`), not a guess. Then the executor sees the volume of work.
    The executor cannot report «перевёл» after moving 3 checks of 12.
    «Должно стать» contains the names of the step classes and a doc-notes record for EACH kind
    of check in the file. «Проверка» contains a command and the expected output.
13. **In «Чекпоинте» (the checkpoint) of the substeps `usage` and `fix`, always write the `MR-48` command** for the
    substep files (own matchers, lists of matchers, `JsonNode`, asserts). The expected output is
    «пусто».
14. **Substep `env`: each key has a value.** «Что сделать»: «создать / дополнить
    `<файл фрейма>` ключами из таблицы «Данные подключения»; сертификаты `<файлы>`
    подключить так, как велит `D-<tech>-<n>`». «Итоговый результат» is a list of
    `ключ = значение` for each framework file. The checkpoint: a grep for empty values and
    placeholders in the framework files gives an empty output:
    `grep -nE "=\s*$|TODO|changeme|<[^>]+>" <файлы фрейма>`.
15. **The substep limit is strict.** If the work is larger than the limit, divide it into two
    substeps. A note «превышение лимита сознательно» is not allowed.
16. **«Правила подшага» has the numbers of the code rules that the executor reads before the
    changes.** The executor reads ONLY these rules (not all rules). The subagent «проверяющий»
    (the checker) uses the same rules to check the substep. Take the row for the substep kind
    from the table (the next paragraph tells where it is). Add the additional rules from the conditions under that
    table. For the substeps `разбор` and `review`, the field value is `-`.

    The table and the additional rules are in `references/substep-rules.md` (one file for all
    of the kit). The script `scripts/Card.java` checks the field with the same table.
    If a mandatory number is missing or an extra number is present, this is a finding.
