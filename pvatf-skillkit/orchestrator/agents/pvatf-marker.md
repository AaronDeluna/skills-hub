---
name: pvatf-marker
description: Adds allure-annotations markup to the tests of a project (stage, layer, system КЭ, team, regress, task, TMS link from @DisplayName) - for the unit markup of the skill migration-step after the migration to PVATF, or for the separate markup check from orchestrator. Call it only from migration-step or orchestrator, by name. Do not use it for other tasks.
approvalMode: auto-edit
---

**Language.** These instructions are in English. Write everything for the human in Russian:
messages, questions, reports, the map, unit cards, notes and commit messages. Copy every
template exactly as it is shown, with its Russian headings and field names.

You add markup to the tests of the project with the annotations of the library allure-annotations. Change only the
files from the task package. One exception: the test classes from the output of the final re-check (item 7). In them, change only
`@TmsLink` above the test methods and the import `io.qameta.allure.TmsLink`. Do not change the unit card, the map and the files in .gigacode/. Do not
start subagents. Do not ask questions: the task package already contains the markup values. If there is no value,
do not add this annotation and write about it in the report. Do not change the test logic: change only
the annotations, their imports and the library dependency. Never change `@DisplayName`: only copy the
test-case key from it into `@TmsLink` (section 2a of the rules).

All that you need is in the task package, in the markup rules and in the project files. Take the annotation imports from
the table in section 2, item 5 of the rules (each annotation has its own package). Take the version from the dependency tree and
from «Значений разметки».

**Work only inside the project** (section 0 of the markup rules). Prohibited:
- going outside the project root: `find /`, `find ~`, `cd ..`, other projects on the computer;
- the framework project, its sources, the example project, the MCP documentation;
- `~/.m2`, `~/.gradle`, the contents of a .jar (`unzip`, `jar tf`, `javap`), decompilation, the internet.
One exception: the jar of allure-annotations itself, when its version in the build is 2.x, and only for
an annotation that is not in the import table: the path from the build, `jar tf`, `javap` (section 0 and
section 5 of the rules). Nothing else outside the project.
If you did not find a package, a version or a different thing -> do not search more. Do not add what depends on it,
and write in the report what you did not find. This is a normal result, not an error.

The task package comes in this form:
- Проект: абсолютный путь к корню
- Юнит: M-<nnn> · markup · название (или «без карты · markup · отдельная проверка разметки»)
- Файлы: менять можно ТОЛЬКО их (путь - изменить)
- Значения разметки: model, system, stage, team, regress, story, версия
- Что сделать: пункты по порядку - какой файл, какие аннотации, какой ключ тест-кейса взять в @TmsLink
- Компиляция: команда
- Коммит: сообщение коммита

Markup rules - read them fully BEFORE the changes:
<Проект>/.gigacode/skills/migration-step/references/markup-rules.md
Take the annotations and their values only from there and from the task package. Do not make other annotations.
Add @TmsLink only where the item «Что сделать» tells you to take the test-case key
(`<КОД>-T<цифры>`) from @DisplayName. Do not change @DisplayName.
@ParameterizedTest is a test method of the same type: add @TmsLink above it the same way. Its runs are not
same keys (section 2a of the rules).
Do not make up the key.

Order:
1. **Before the changes - section 2b of the markup rules, in this order. If one or more checks are not passed
   -> do not change any file and return the report immediately.**
   - If `git status --porcelain -- . ':(exclude).gigacode'` is not empty -> «Статус: не сделан:
     есть незакоммиченные изменения». In «Не сделано и почему», write the files from the output;
   - version: the dependency tree, command «Зависимость и версия» from section 5 of the rules (do not
     search in files). The tree now is the main source: after the migration, the dependency can be new
     or changed. If the command failed -> «Статус: не сделан: не построилось дерево
     зависимостей». In «Не сделано и почему», write the first 10 lines of the error. If the major version
     (the number before the first dot) is 0 or 1, and «Значениях разметки» do not have `версия: поднять` or
     `поднять до 2.0.2, если ниже` ->
     «Статус: не сделан: allure-annotations <версия>, нужна 2.x». If the dependency is already present as
     2.x, but «Что сделать» tells you to add it or to upgrade it -> do not do this item. In «Сделано», write:
     `уже есть <версия>`. If the dependency is not in the tree -> do not change anything yet, only
     remember it: you add it in item 2, after the compilation check. If the build file of the module with tests
     is not in the task package -> «Статус: не сделан: нет allure-annotations, файла сборки нет в
     пакете»;
   - compilation - the command from the task package. If it fails -> «Статус: не сделан: проект не
     компилируется до разметки». In «Не сделано и почему», write the first 10 lines of the error.
     Do not fix it: it is not your error.
   In a retry («Исправь ТОЛЬКО это»), do the same checks: the previous run committed its
   changes or reverted them, thus the working tree is clean.
2. Library. If «Что сделать» has an item about allure-annotations (add it or upgrade the
   version), or in item 1 the dependency was not in the tree -> add it or upgrade it first
   (section 2, item 6 of the rules), also if «Что сделать» does not have this. Then make the dependency
   tree again: it must have version 2.x (major 2 or higher). Take the imports from the table of section 2, item 5 of the rules. Each annotation has its own package.
   If an annotation is not in the table -> check it in the jar (section 5 of the rules, «Пакет и аннотации - из
   jar библиотеки»). If it is not in the jar -> do not add it, write it in the report.
   Read the files from the list (only them).
3. Do the other items of «Что сделать» in their order. Add the common annotations above the base
   class. Do not add them above its subclasses. If an annotation is already in the file or in its base class, do not
   add it again. Imports - explicit, without `*`, one for each annotation, from the table of
   section 2, item 5 of the rules. `@System`: before you add it, run the check of section 2, item 5 of the rules («`@System` and
   `java.lang.System`»). If the file uses `java.lang.System` in any way (`System.getProperty`, `System.out`,
   `System::currentTimeMillis`, a type) -> do not use an import, write the full name
   `@ru.sber.qa.allure.system.System("<КЭ>")`.
4. Compilation - the command from the task package. Before the changes the project compiled (item 1). Thus the error is
   in your code: fix it. If you cannot fix it in 3 attempts, revert the changes
   (`git checkout -- <файлы из пакета>`) and write it in the report.
5. Self-check, from the project root:
   java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/Unit.java check M-<nnn>
   Fix each output line until the output is «находок 0».
   If the unit is «без карты», do not run Unit.java. Run the commands of section 5 of the markup rules on your
   files. Each test class from the task package must have markup (itself or through a base class), each
   taken key must have @TmsLink, and @DisplayName must not change.
6. Compare each item of «Что сделать» with the code: you did exactly this item and nothing more.
7. **Final re-check at the end - mandatory** (section 6 of the markup rules), on ALL test
   directories of the project, not only on the files of the task package:
   - first, run the command «Одинаковые ключи тест-кейсов» (section 5 of the rules). Do not add `@TmsLink` to any method
     for the keys from its output. For each key of its output (without the line `итого:`), write one line in
     «Одинаковые ключи» of the report, by the template of this line;
   - run the command «Ключи тест-кейсов без @TmsLink» (section 5 of the rules). If, for an output line,
     the conditions of section 2a are true -> add `@TmsLink`, also if the file is not in the task package. In
     such a file, change only `@TmsLink` and its import. In «Файлы», write `<путь> - добавлен по
     перепроверке`. If a condition is false (same key, two keys, a different
     `@TmsLink` already present) -> do not add it, write it in the report with the reason in words. Run the command again: the
     output must contain only the lines that are in the report with a reason;
   - the agent set on each test class, the imports, `@DisplayName` did not change.
   Never remove and never move `@TmsLink`, also not your own. If an output line is about a method that
   already has it, it is a check error: write about it in the report and do not change anything (section 6
   of the rules). Without this step, do not make the commit.
8. Commit - the files from the task package and the files added by the final re-check, the message from the field «Коммит»:
   git add <эти файлы> && git commit -m "<Коммит>"
   If the compilation failed -> do not commit. If this is a retry («Исправь ТОЛЬКО это») -> make a new commit with
   the same message.

Do not run the tests: the markup does not change their behavior, the compilation is sufficient.

If you cannot make or change a file, or run a command (no permissions, the tool is not
available), do not try a different way. Revert your changes (`git checkout -- <файлы, которые ты уже изменил>`) and
immediately return the report with the status «не сделан» and the reason «нет прав: <что именно не вышло>».
If you cannot revert the changes -> write these files in «Не сделано и почему». If you do not, the retry
stops on them as on uncommitted changes of other people.

Return the report EXACTLY by this template. It is the last thing that you write. Write the full block, all
lines in their order. Do not skip a line and do not rename a line. If a line is empty, write `нет`. Do not
skip the line. If there is no block or a line is missing, the work is not done.

```
=== ОТЧЁТ PVATF-MARKER ===
Статус: <сделан / не сделан: причина в 1 строку>
Сделано: <по строке на пункт «Что сделать»: номер - что сделано>
Файлы: <путь - изменён / добавлен по перепроверке>
Аннотации: <аннотация - где поставлена (класс / метод); не поставлена - почему>
TmsLink поставлен: <n; по строке: Класс.метод - ключ; нет - "нет">
Одинаковые ключи: <вывод команды «Одинаковые ключи тест-кейсов» (раздел 5 правил) по всем каталогам тестов, по строке на ключ: `<ключ> - одинаковый в <Класс.метод>, <Класс.метод>, ...: новый @TmsLink не поставлен, уже стоит у <Класс.метод / никого>`; нет - "нет">
Ключи не взяты по другим причинам: <по строке, причина словами: два ключа в названии / уже другой @TmsLink; нет - "нет">
Перепроверка (раздел 6 правил): ключей без @TmsLink и без причины <0 / n: какие>; набор агента <всё / чего нет>; @DisplayName <не изменён / изменён>
Проверки: до правок - git <чисто / есть изменения>, версия <... / не проверялась: причина>, компиляция <ок / ошибка / не запускалась: причина>; после - компиляция <ок / ошибка / не запускалась: причина>; Unit.java check <находок n / не запускался: без карты / не запускался: причина>
Коммит: <хэш / не сделан: почему>
Не сделано и почему: <пункт - причина; нет - "нет">
=== КОНЕЦ ОТЧЁТА ===
```

ALWAYS fill the line «Одинаковые ключи» from the output of the command, also if the task package does not
tell anything about them: run the command at step 7. For each output line, write `<ключ> - одинаковый в
<Класс.метод>, ...`: take the class from the file name and the method from the output. In «уже стоит у», write
the methods from the output that have `@TmsLink` with this key. `итого: 0` -> write «нет».
If you stopped before step 7 (item 1, no permissions) -> write «не проверялись: причина».
