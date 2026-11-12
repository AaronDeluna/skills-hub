# Этапы обновления фрейма

Часть скилла `env-update`. Открывай, только когда SKILL.md направил сюда.

Пути: `E=.gigacode/skills/env-update/scripts/env_update.py`,
`C=.gigacode/skills/env-check/scripts/env_check.py`, рабочая папка
`W=.gigacode/data/autotest/env-update`. Ниже команды даны полностью - копируй их.

## Этап 1 - проверка до обновления

```
python3 .gigacode/skills/env-check/scripts/env_check.py
```
Таймаут команды 1000 секунд. В шапку `ENV-UPDATE.md`: `before_status` - значение `СТАТУС`.
Строка `E6 · компиляция тестов` не `ok` -> обработка ошибок, «компиляция failed до обновления».

## Этап 2 - текущая версия

```
python3 .gigacode/skills/env-update/scripts/env_update.py versions
```
В шапку: `from` - значение `ТЕКУЩАЯ`. Таблицу объявлений перепиши в раздел «Объявления версии»
дословно. `ВЕРСИЯ: не найдена` -> `update_status: failed`, причина «в сборке нет фрейма».

## Этап 3 - release notes

1. Прочитай описание MCP-инструмента `get_pvat_release_notes` и его параметры.
2. Вызови его. Параметр «версия» или «с какой версии» есть -> передай `from` из шапки.
3. Ответ сохрани в файл дословно, целиком: `.gigacode/data/autotest/env-update/release-notes.md`.
   Ничего не сокращай и не пересказывай: из файла версию достаёт скрипт.

## Этап 4 - целевая версия

Человек назвал версию -> бери её. Иначе:
```
python3 .gigacode/skills/env-update/scripts/env_update.py latest .gigacode/data/autotest/env-update/release-notes.md
```
В шапку: `to` - значение `САМАЯ НОВАЯ`. `to` равна `from` или старше -> `update_status: done`,
«уже последняя версия», этапы 5-9 не нужны.

## Этап 5 - что изменилось между версиями

1. Прочитай описание MCP-инструмента `get_pvat_changelog` и его параметры. Вызови его на
   диапазон `from` -> `to` (параметров диапазона нет - на версию `to`). Ответ сохрани
   дословно в `.gigacode/data/autotest/env-update/changelog.md`.
2. Выпиши из changelog в раздел «Изменения» отчёта только то, что может сломать код или
   настройки проекта: удалено, переименовано, изменена сигнатура, deprecated, новый
   обязательный ключ настроек, новая обязательная зависимость. Строка:
   `| <имя как в changelog> | <удалено / переименовано в X / сигнатура / deprecated / ключ / зависимость> | <версия> |`.
   Нельзя: «улучшена работа Kafka». Нужно: «`KafkaService.consumerClient()` | переименовано в
   `kafkaConsumerClient()` | 3.5.0».
3. Имена из первой колонки - по одному на строку - в `.gigacode/data/autotest/env-update/names.txt`.
4. Где они в проекте:
   ```
   python3 .gigacode/skills/env-update/scripts/env_update.py usages .gigacode/data/autotest/env-update/names.txt
   ```
   Число мест по каждому имени допиши в таблицу «Изменения» (колонка «Мест в проекте»).

## Этап 6 - замена версии

```
python3 .gigacode/skills/env-update/scripts/env_update.py bump <to>
```
Строки `ИЗМЕНЕНО` перепиши в раздел «Файлы сборки». Объявление с пометкой «другая версия»
(вторая линейка, например perfeccionista) меняешь, только если changelog прямо называет
её новую версию: `bump <версия> --only <номер строки из этапа 2>`.

## Этап 7 - компиляция после обновления

```
python3 .gigacode/skills/env-check/scripts/env_check.py --timeout 1800
```
Таймаут команды 1900 секунд. `E6` ok и мест из этапа 5 нет -> этап 9. Иначе - этап 8.

## Этап 8 - исправления (не больше 3 кругов)

Один круг:
1. Ошибки компиляции по файлам:
   ```
   python3 .gigacode/skills/env-update/scripts/env_update.py errors
   ```
2. На каждый `СИМВОЛ` и на каждое место из этапа 5 найди замену - строго в таком порядке:
   - таблица «Изменения» (changelog назвал новое имя) -> бери оттуда;
   - конспект: `python3 .gigacode/skills/env-check/scripts/notes.py find <tech> <имя>`;
   - агент `pvatf-docs`, задание по шаблону `references/autotest-rules.md`, правило 3 (не
     больше 5 вопросов), вопрос: «Чем заменить `<имя>` в версии <to>: класс, метод, пример
     вызова». Ответ - в конспект `.gigacode/data/doc-notes/<tech>.md`, ID - `notes.py next <tech>`.
3. Замены нет ни в одном источнике -> место не трогай, строка в «Осталось человеку».
4. Правь только файлы из вывода `errors` и `usages`. Меняй только то, что назвал источник:
   имя, импорт, порядок аргументов. Логику теста не меняй.
5. Каждую правку - строкой в раздел «Исправления»: `| <файл:строка> | <было> | <стало> | <основание> |`.
6. Запусти этап 7. `E6` ok -> этап 9. Нет и круг третий -> этап 9, ветка «откат».

## Этап 9 - итог

**Успех** (`E6` ok): `update_status: done`. Запусти ещё раз
`python3 .gigacode/skills/env-update/scripts/env_update.py versions` - все строки бывшей
текущей версии теперь `to`. Покажи итог по шаблону SKILL.md.

**Откат** (не сошлось за 3 круга или человек попросил):
1. `python3 .gigacode/skills/env-update/scripts/env_update.py rollback`
2. Правки кода из раздела «Исправления» верни: `git checkout -- <файл>` по каждому файлу.
3. `python3 .gigacode/skills/env-check/scripts/env_check.py` - компиляция снова `ok`.
4. `update_status: rolled-back`; в «Осталось человеку» - ошибки, которые не удалось исправить.
