# Stage 5 subagents: technology analysis, card writer, card checker

Part of the skill `migration-map`. Open this file at Stage 5, when you build the unit card of the unit `tech`.

The reason: at Stage 5, your context is full of the inventory, the doc notes and the matrix.
If you write a unit card «по памяти» from such a context, it is easy to miss data. Thus you
build the unit card from FILES, not from memory. A subagent with a clean context does each
part:

```
5.1 разбор технологии   -> inventory/analysis-<tech>.md   (сабагент читает код, считает командами)
5.2 составитель         -> units/M-<nnn>.md               (сабагент пишет карточку из файлов)
5.3 Card.java           -> механические находки            (скрипт)
5.4 проверяющий         -> смысловые находки               (сабагент сверяет карточку с разбором)
5.5 исправление         -> составитель правит по находкам   (не больше 2 кругов)
```

Do the technologies one at a time, in the order of the map passport. For each technology, do
the full cycle 5.1-5.5, then go to the next technology. Each step of the cycle, except the
script, goes MANDATORILY through its own subagent. Only if the subagent call returned an error
(not «долго» and not «проще самому») -> show the error in the chat, write
`сабагент не запустился: <ошибка>` into the map log, and do this step yourself, with the same
prompts and templates.

---

## 5.1 Subagent «разбор технологии»

This subagent only reads and counts with commands. Its answer is the facts about the code. All
of the unit card stands on these facts:
- who accesses the technology, and how;
- which actions the code does;
- how many checks of each type the code has.

The subagent gets each number with a command and writes the command next to it. Then you can
check the numbers again.

What to put into the prompt:
- the old packages and the classes of the old core of the technology - from the lines `G` and `L` of the migration map;
- the access to the framework service - the names from the doc notes `doc-notes/<tech>.md` (how
  the framework gets the client of the technology);
- the step classes from the architecture plan of this technology (do not count them as consumers);
- the source directories - from the map passport.

If there are more than 25 consumers -> use a number of subagents and divide the files by
packages. Join the tables of their answers into one file. Max 3 subagents at the same time.

**Prompt (copy word for word, replace `<...>`):**
```
Ты разбираешь, как проект автотестов пользуется одной технологией. Только читаешь и
считаешь командами. Не меняй файлы, не запускай сборку и тесты. Каждое число получай
командой и пиши команду рядом. Не рассуждай, верни ТОЛЬКО заполненный шаблон.

Проект: <абсолютный путь к корню>
Технология: <метка> - <название>
Каталоги исходников: <пути>
Старые пакеты и классы старого ядра: <список через |, для grep -E>
Обращения к сервису фрейма в обход шагов: <список через |; нет - "-">
Классы шагов из плана (не потребители): <имена; нет - "-">
<если сабагентов несколько:> Твои файлы - только из пакетов: <пакеты>

Порядок:
1. Потребители: выполни обе команды, объедини списки, убери классы шагов из плана:
   grep -rlE "<старые пакеты и классы>" --include=*.java --include=*.kt <каталоги>
   grep -rlE "<обращения к сервису фрейма>" --include=*.java --include=*.kt <каталоги>
2. Уровень каждого файла: 0 - сам импортирует старый пакет и в нём нет @Test (старое ядро);
   1 - вызывает классы уровня 0; 2 - вызывает уровень 1; и так далее; тест-классы (@Test) -
   на своём уровне, но в таблице помечай «тест».
3. По каждому потребителю (не старому ядру) - командами по файлу, НЕ читая его целиком:
   - строк: wc -l <файл>
   - ассертов: grep -cE "Assertions\.|assert(Equals|True|False|NotNull|Null|That|All)\(|SoftAssertions" <файл>
   - разбор ответа в объект: grep -cE "\.as\([A-Z][A-Za-z0-9_]*\.class\)|readValue\(|fromJson\(|JsonNode|\.extract\(\)" <файл>
   - обращений к старому ядру и библиотеке: grep -cE "<старые пакеты и классы>" <файл>
   - действия: grep -nE "<слова действий: post|get|put|delete|select|insert|update|send|poll|topic|sql>" <файл> | head -15
     -> сверни в список действий («POST /orders», «SELECT orders», «send orders.created»)
   - виды проверок: по 3-5 строкам с ассертами (grep -n ... | head -5) определи, ЧТО
     проверяется: код ответа, поле-строка, поле-число, boolean, дата, наличие поля, null,
     размер массива, строка БД, ячейка БД, запись Kafka
   - DTO ответа: имена классов из `.as(X.class)` / `readValue(..., X.class)`
   - другие технологии в файле: grep -lE "<импорты других технологий из паспорта>" <файл>
4. По каждому классу старого ядра: строк; сколько файлов его вызывают
   (grep -rl "<Имя>" --include=*.java --include=*.kt <каталоги> | wc -l); что делает - по
   именам публичных методов (grep -nE "public " <файл> | head -10), одной строкой.

Верни РОВНО так (заголовки и колонки сохрани):

# Разбор технологии <метка>

## Команды поиска
- старое: `<команда 1>` -> <n> файлов
- фрейм напрямую: `<команда 2 или "-">` -> <n> файлов

## Потребители
| Файл | Строк | Уровень | Тест | Как обращается | Действия | Ассертов | Разбор в объект | Виды проверок | DTO ответа | Другие технологии |
|------|-------|---------|------|----------------|----------|----------|-----------------|---------------|------------|-------------------|
| <путь> | <n> | <n> | да/нет | старая библиотека / старое ядро `<Класс>` / фрейм напрямую | <POST /orders, GET /orders/{id}> | <n> | <n> | <код ответа 3, поле-строка 5> | <OrderDto / -> | <db / -> |

## Классы старого ядра
| Класс | Файл | Строк | Вызывают файлов | Что делает (1 строка) |
|-------|------|-------|-----------------|-----------------------|

## Виды проверок технологии (сводка)
| Вид | Мест | Пример: файл:строка |
|-----|------|---------------------|

## Не удалось
- <файл или команда: причина>     (нет - напиши: нет)
```

**What to do with the answer.** Write it as it is into
`.gigacode/data/migration/inventory/analysis-<tech>.md`. If the answer is not by the template,
or has no commands, or has no numbers -> do not use it. Start the subagent again. A consumer
can have another technology `migrate` that comes later in the order. Then the file is
postponed (Stage 5, «Файлы на несколько
технологий»): keep it in the analysis, but the card
writer does not take it into the unit card.

---

## 5.2 Subagent «составитель карточки»

This subagent writes ONE file - the unit card of the unit `tech`. It writes strictly by the
template and only from the given files. This is the only map subagent that can write a file.
It does not touch the project code.

What to put into the prompt:
- the unit number, `depends_on`, `core_mode`, the step style, `scope` - from the migration map;
- the paths to the source files (the subagent reads them itself).

**Prompt (copy word for word, replace `<...>`):**
```
Ты пишешь карточку юнита миграции одной технологии на фрейм PVATF. Пишешь ОДИН файл:
<абсолютный путь>/.gigacode/data/migration/units/M-<nnn>.md. Больше ничего не создавай и
не меняй, код проекта не трогай, сборку не запускай. Всё, что пишешь, бери только из
файлов ниже - по памяти ничего не добавляй. Имена классов и методов фрейма - только из
конспекта.

Шаблон карточки и правила «Как писать подшаг» (прочитай целиком и выполни каждое):
<путь к скиллу>/references/tech-unit-template.md

Источники (прочитай):
- разбор технологии: <путь>/.gigacode/data/migration/inventory/analysis-<tech>.md
- целевая картина: блок `T-<tech>` в <путь>/.gigacode/data/migration/MIGRATION-MAP.md (раздел 2), строки `G` и `L` с технологией <tech>
- архитектурный план: строки технологии <tech> и разделы 1-2 в <путь>/.gigacode/data/migration/ARCHITECTURE.md
- конспект: <путь>/.gigacode/data/migration/doc-notes/<tech>.md и doc-notes/common.md
- подключения: раздел <tech> в <путь>/.gigacode/data/migration/CONNECTIONS.md
- отложенные в другую технологию файлы: <список; нет - "-">

Параметры юнита: id M-<nnn>; depends_on [<...>]; core_mode <new|in-place>; стиль шагов <steps|flow>; scope <full|core>.

Как строить:
1. Таблица «Потребители» карточки - из «Потребители» разбора, кроме отложенных файлов.
2. Подшаги по порядку видов из шаблона. `core`: первым - базовый слой технологии, если он
   есть в плане; методы классов шагов - действия из колонки «Действия» разбора, ни одного
   лишнего. `usage`: снизу вверх по колонке «Уровень», тесты последними; лимит - 3 файла и
   600 строк; каждый потребитель - ровно в одном `usage`.
3. В каждом `usage` - таблица «Критерии по файлам»: «Было» - числа из разбора по этому
   файлу (ассертов, разборов в объект, обращений к старому, DTO), «Должно стать» - с
   именами классов шагов и записями `D-<tech>-n` для каждого вида проверок файла.
4. `cleanup` - каждая строка `L` технологии; `review` - все файлы `core` и `usage`.
5. «Правила подшага» - строго по `references/substep-rules.md`: строка вида подшага плюс добавки, других номеров нет.

Верни ТОЛЬКО:
- Файл: <путь> - записан / не записан: <причина>
- Подшагов: <n> (разбор 1, env <n>, core <n>, usage <n>, cleanup <n>, review <n>)
- Потребителей в разборе: <n>, в подшагах usage: <n>, отложено: <n>
- Чего не хватило в источниках: <что и где; нет - "нет">
```

If the subagent cannot write files -> add «Файл не пиши, верни текст
карточки целиком» to the end of the prompt. Then save the answer into the file yourself, word
for word, with no changes.

---

## 5.3 Mechanical check - the script

```
java -Dfile.encoding=UTF-8 .gigacode/skills/migration-map/scripts/Card.java M-<nnn>
```

The script checks:
- the fields of each substep;
- empty words;
- the file limits;
- «Правила подшага»;
- the command `MR-48` in the checkpoints of `usage`;
- the consumer coverage (each consumer is in exactly one `usage`);
- «Критерии по файлам» in each `usage`;
- the lines `L` of the technology;
- that the references `D-<tech>-n` point to existing doc notes records;
- «создал - подключи»;
- the number of lines of the files.

If the result is `находок 0` -> go to 5.4. If there are findings -> keep them for 5.5.

---

## 5.4 Subagent «проверяющий карточки»

This subagent compares the meaning: the things that the script does not see.

**Prompt (copy word for word, replace `<...>`):**
```
Ты проверяешь карточку юнита миграции на фрейм PVATF. Только читаешь и находишь
нарушения: ничего не меняй. Свои правила не придумывай, вкусовые замечания не пиши.

Карточка: <путь>/.gigacode/data/migration/units/M-<nnn>.md
Разбор технологии: <путь>/.gigacode/data/migration/inventory/analysis-<tech>.md
Шаблон и правила «Как писать подшаг»: <путь к скиллу>/references/tech-unit-template.md
Конспект: <путь>/.gigacode/data/migration/doc-notes/<tech>.md

Проверь по пунктам:
К1. Каждое действие из колонки «Действия» разбора есть методом в подшагах `core`; в `core`
    нет методов, которых нет в разборе.
К2. В «Критериях по файлам» каждого `usage` числа «Было» совпадают с разбором по этому файлу.
К3. Для каждого вида проверок файла из разбора в «Должно стать» названа запись `D-<tech>-n`,
    и в конспекте эта запись про такой вид проверки.
К4. «Что сделать» каждого подшага - действия с именами файлов, классов, методов; по ним
    можно работать, ничего не додумывая.
К5. «Итоговый результат» - по строке на каждый файл подшага, проверяемый факт.
К6. «Чекпоинт» проверяет именно «Итоговый результат» этого подшага.
К7. `usage` идут снизу вверх по уровням из разбора, тесты последними.
К8. DTO ответа из разбора удаляются: метод возвращает валидируемый объект, вызывающие
    переходят на `.should(...)`.
К9. Нет шагов, которые правят или повторяют старое ядро («перевести RestHelper на PVATF»),
    делегатов, фасадов, вложенных классов, вспомогательных методов в тест-классах.

Верни РОВНО так:

## Находки
| Пункт | Подшаг | Что не так (1 строка) | Как исправить (1 строка) |
|-------|--------|-----------------------|--------------------------|
| К<n> | S-<nn> | <...> | <...> |

## Без находок
- <пункты без находок через запятую>
```

---

## 5.5 Correction

1. Put the findings of the script (5.3) and of the checker (5.4) into one list.
2. If there are no findings -> the unit card is accepted. Next - a line in section 4 of the migration map (Stage 5, «Для
   каждого юнита»).
3. If there are findings -> start the card writer again. Use the same prompt and add at the end
   «Карточка уже
   есть. Исправь в ней ТОЛЬКО эти находки, остальное не трогай:» and the list. Then do 5.3
   and 5.4 again.
4. Max two correction rounds. If findings are still there after the second round -> correct them
   yourself (usually 1-2 lines). Run 5.3 again and write into the map log:
   `M-<nnn>: карточка дописана вручную, находки: <коротко>`.
