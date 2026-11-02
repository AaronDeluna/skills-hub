# Unit card template (write strictly by this template)

Path: `.gigacode/data/migration/units/M-<nnn>.md` (the number has three digits: `M-001`, `M-002`...).

**This template is for small units:** `env` of phase 1, `arch`, `cleanup` of phase 4, `markup`
of phase 5, `fix`, `review` after the check. Write a technology unit (type `tech`, phase 2) by another template -
`references/tech-unit-template.md`.

The executor reads the unit card in ANOTHER chat. The executor did not see your analysis and does not examine
the project again. Write the card so that the executor can work by it without guesses: exact file
paths, exact names from the documentation, exact references `D-<tech>-<n>`.

`migration-map` fills the sections before «Журнал выполнения». `migration-step` fills «Журнал выполнения» and «Блокер».
When you make the card, keep these two sections as they are in the template.

```markdown
---
id: M-<nnn>
type: env | core | usage | cleanup | arch | markup | review | fix
core_mode: <только для type: core - new | in-place; для остальных типов `-`>
tech: <метка технологии из матрицы G: rest / ui / db / ... / core>
phase: <1-5; 6 - юниты исправления, их заводит migration-review>
status: todo
depends_on: [<M-nnn>, ...]
covers: [<G-n>, <A-n>, <L-n>, ...]
---

# M-<nnn> · <короткое название>

## Цель
<1-2 предложения: что после этого юнита станет по-другому>

## Целевая картина
Блок `T-<tech>` в разделе 2 карты - как код этой технологии должен выглядеть в конце.
Исполнитель обязан прочитать его до правок. Для `core`, `usage` и `review` - обязательно;
для остальных типов - `-`.

- Блок: `T-<tech>` (файл на несколько технологий - все его блоки: `T-rest`, `T-db`)
- Что из него делает этот юнит: <1-2 строки>
- Что из старого этот юнит НЕ переносит (поимённо): <классы-прослойки, свои ассерты; нет - `-`>

## Файлы юнита
Менять можно ТОЛЬКО эти файлы (и создавать только перечисленные новые).

| Файл (путь от корня проекта) | Строк | Действие |
|------------------------------|-------|----------|
| <путь> | <n> | изменить / создать / удалить |

Тестов в файлах юнита сейчас: <число методов с @Test, или `-` если тестов нет>

## Legacy под удаление в этом юните
Что из старого должно исчезнуть в результате юнита (строки `L-<n>` карты). Для `cleanup` -
свой список (код / сборка / конфиги). Для `usage` - то, что перестаёт использоваться после
переноса этих файлов (если есть). Нет - напиши `-`.

- `L-<n>` - <что удалить: класс / пакет / зависимость / конфиг> - <путь>

## Что сделать
Шаги по порядку. Каждый шаг - конкретное действие со ссылкой на строку карты.

1. <действие> - по `G-<n>` / `A-<n>` / `L-<n>`
2. <действие>

## Показательный тест
ОДИН БЫСТРЫЙ тест, который докажет, что юнит мигрирован успешно. Для `env`-юнитов и `core`
в режиме `new` теста нет (`-`): они проверяются компиляцией.

- Тест: <полный путь к классу>#<метод>   (или `-` и причина, почему теста нет)
- Команда запуска: `<точная команда точечного запуска ОДНОГО этого метода>`
- Ожидаемое время: <n секунд по отчёту прошлых прогонов / время неизвестно, выбран по коду>
- Почему он: <1 строка: какие мигрируемые места он проходит>

## Док-основание
Записи конспекта документации (`doc-notes/<технология>.md`), на которых стоит этот юнит.
Только то, что нужно этому юниту. Исполнитель сначала читает эти записи; чего в них не
хватит - доспросит у сабагента документации и допишет сюда новые ID.

- `D-<tech>-<n>` - <что из этой записи используется в юните>

## Правила юнита
Номера правил кода, которые исполнитель прочитает перед правками (только их) и по которым
юнит проверит сабагент «проверяющий». Строка по типу юнита и добавки - строго по
`references/substep-rules.md`.

`MR-<n>`, `MR-<n>`, ...

## Критерии готовности
- [ ] проект компилируется (команда из паспорта карты)
- [ ] в файлах юнита не осталось старого: `<точный grep-шаблон старых импортов для этого юнита>`
- [ ] число тестов в файлах юнита не уменьшилось
- [ ] показательный тест реально запущен и зелёный (для юнита без теста - убери эту строку)
- [ ] всё из «Legacy под удаление в этом юните» удалено, ссылок на него в проекте нет
- [ ] <свой критерий юнита, если есть>

## Журнал выполнения
(заполняет migration-step)

### Таблица подтверждений
| Что использую из PVATF (класс/аннотация/метод/настройка) | Где в документации |
|----------------------------------------------------------|--------------------|

### Что сделано
-

### Проверки
- компиляция: -
- показательный тест до изменений: -
- показательный тест после изменений (команда и итог): -
- остатки старого (grep): -
- удалённое legacy (что удалено, ссылок осталось: 0): -
- правила кода MR: -
- нить (кто вызывает созданное): -
- число тестов до/после: -

### Коммит
-

### Где остановился (если юнит не закончен)
-

## Блокер
(заполняется только при status: blocked - что именно не найдено/не получилось и какой вопрос
вынесен в раздел 6 карты)
-
```

## Filling rules

- **The list of files is complete.** The executor must not change files outside the list. If you are not
  sure that a file is necessary, include it. If the unit is larger than the limit of its type (`usage` - 3 files /
  600 lines; `env`, `core`, `arch` - 6 files / 1000 lines), divide the unit.
- **Each step tells «что» (what), with a basis.** Not «мигрировать класс», but «заменить наследование от `<СтарыйБазовыйКласс>` на <механизм из документации> - по `G-3`».
- **The done criteria are facts about specific files, with a command.** Example: «`ReportSteps.java`:
  проверки ответа только через `.should(...)` - `grep -nE "assert(Equals|True|All)\(|JsonNode" <файл>`
  пусто». Do not write: a criterion as one rule code («V19 устранено»), «по возможности»,
  «где получится». The units `usage`, `fix`, `arch` always have a criterion with the command `MR-48`
  from `code-rules.md` for the unit files.
- **The unit limit is strict.** If the work does not fit, make two units. Notes such as «превышение лимита сознательно» do not exist.
- **The grep pattern in the criteria is exact.** Use the same pattern that found these files
  at the inventory (for example, `import <старый.пакет>`).
- **`core` unit, mode `new`: write this directly in the steps:** «создать <что> по `T-<tech>`; старые классы <перечисли> не править и не копировать».
  In the files table, put only the new files (action `создать`) and the files that receive the moved data.
- **`core` unit, mode `in-place`: write this directly in the steps:** «публичные методы (имена, параметры, возвращаемые типы) не менять, тесты и вызывающий код не трогать».
  Then list these public methods. Exception: a unit with the note «сигнатура меняется, вызывающие файлы включены».
- **A test class has only the scenario.** For a file with `@Test`, the card steps never contain «добавить приватный метод в тест».
  An action that the test needs is a method of the step class: the method already
  exists, or the step class is in the unit files with the step «добавить метод».
- **`usage` unit: write the steps from the target picture, not from the old code.** Not «заменить вызов
  `RestHelper.get()` на аналог», but «тест вызывает <механизм фрейма> напрямую и проверяет
  ответ через <matcher> - по `T-rest`, `D-rest-<n>`; ссылки на `RestHelper` убрать».
- **The representative test has an exact command.** The executor must not select the test and
  the command itself. Make the command from the runner in the map passport (a run of one method).
- **Write legacy as specific paths.** Not «удалить старые утилиты», but a list of classes, packages,
  dependency coordinates and config files.
- **Do not write in the card a code solution «по памяти».** Use only the PVATF names from the
  documentation that you wrote in the matrix `G`.
