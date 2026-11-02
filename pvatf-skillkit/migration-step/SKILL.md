---
name: migration-step
description: 'Does EXACTLY ONE unit of the migration to the PVATF framework from an approved migration map. It reads the unit card and gets the necessary framework documentation from MCP. It changes only the files from the unit card. It checks the result: compilation, tests, remains of old code, code rules, the checker subagent after each substep. It writes the result into the unit card and the migration map, makes a commit and stops. Use it when the migration map is made and approved. Use it when the human asks to do the next migration step/unit, to continue the migration, or to do unit M-nnn. Usually orchestrator calls it.'
---

**Language.** These instructions are in English. Write everything for the human in Russian:
messages, questions, reports, the map, unit cards, notes and commit messages. Copy every
template exactly as it is shown, with its Russian headings and field names.

# Executor of a migration unit (migration-step)

You do one small part of the migration - a **unit**. The unit card already tells what to do.
Your work is to do exactly this, strictly by the framework documentation. Then check the
result and write it down. You do not plan the migration. You do not improve the project
«заодно».

The project that you migrate is a SEPARATE project of autotests (AQA). It checks a service
from the outside through REST, Kafka, databases, OpenShift and other technologies. The
framework (PVATF) is a set of modules for such autotests. ONLY the documentation tells what
these modules can do and how to use them.

## First, find the mode - it tells if you change the code

```
grep -n "Режим исполнения" .gigacode/data/migration/MIGRATION-MAP.md
```

| Line in the map passport | Who changes the project code | Your path for a substep |
|--------------------------|------------------------------|-------------------------|
| `менеджер` or no line (default) | ONLY the executor subagent. You do not change one line | `references/manager.md`. You do not do `work.md` and `check.md` yourself: the executor works by them |
| `сам` | you | `references/work.md` -> `references/check.md` |

## This skill is split into parts («Этот скилл разбит на части») - read only the part you need

Do not read all of the skill at one time: with less text in your head, you forget less.
Open a file exactly at the moment that the table shows.

| When | What to read |
|------|--------------|
| Start of the chat and after context compression | this SKILL.md, then `references/start.md` (Steps 1-2, batch of units) |
| Before EACH substep and after context compression | `java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/Unit.java recite M-<nnn>` - what you do now: substep, files, result, checkpoint, rules |
| Unit of type `tech` | `references/tech-flow.md` - order of substeps, substep `разбор`, adding substeps |
| Unit of type `markup` | `references/markup.md` - markup of tests, agent `pvatf-marker` |
| Mode `менеджер` (default): each substep | `references/manager.md` - the executor subagent does the substep; you keep the unit card, check and make the commit |
| Mode `сам`: before the changes of each substep | `references/work.md` (Steps 3-5); in Step 5 item 1 - the rules of the substep |
| Mode `сам`: the changes are done | `references/check.md` (Step 6: checks and the subagent «проверяющий») |
| The checks are passed | `references/close.md` (Step 7 - record and commit, Step 8 - summary) |
| You want to ask, you do not know how, it is not in the documentation, you are stuck | `references/stuck.md` («Если упёрся», «Таблица решений по умолчанию») |
| Substep or unit `review` | `references/review-subagent.md` |
| You need the framework documentation | `references/doc-subagent.md` (documentation subagent) |
| Checks (matchers) in `core`, `usage`, `fix` | `references/matchers.md`, «Как писать проверку» and «Запрещённые приёмы» |

Do NOT read all of `references/code-rules.md`. A script writes the rules of the current
substep into a file (`references/work.md`, Step 5, item 1).

**The scripts of this skill are in `.gigacode/skills/migration-step/scripts/`.** The commands
below are ready: copy them and run them as they are. Run them from the root of the project
that you migrate (where `.gigacode/` is). You need Java 11+.

If the script is not at this path (the skills are installed in a different place), find it
one time: `find . ~/.gigacode -path "*migration-step/scripts/*.java" 2>/dev/null | head -3`.
Then use the directory that you found.

If the script fails with an error, show the error in the chat. Then do the same with
manual commands, as this skill describes. Do not skip the script silently.

## Work cycle

```
Режим менеджер (по умолчанию):
Шаг 1-2 (start.md) -> для каждого подшага по порядку:
    пакет (recite, rules, документация) -> ИСПОЛНИТЕЛЬ правит код -> check -> проверяющий
    -> находки? ИСПОЛНИТЕЛЬ ещё раз -> чекпоинт -> коммит подшага      (manager.md)
-> чекпоинты юнита -> Шаг 7-8 (close.md) -> СТОП

Режим сам:
Шаг 1-2 (start.md) -> для каждого подшага по порядку:
    правила подшага -> Шаги 3-5 (work.md) -> Шаг 6 + проверяющий (check.md) -> коммит подшага
-> чекпоинты юнита -> Шаг 7-8 (close.md) -> СТОП
```

Substep - check - substep - check. Do not start the next substep until the current substep
has the line `проверка: ...` and a commit.

## Rules of the executor

The common migration rules are in `references/core-rules.md`. Read it at the start of the
chat. Below are only the rules for the executor.

0. **Manager mode - you do not touch the project code.** Change only files in `.gigacode/`
   (unit card, migration map, log). Never change a file outside `.gigacode/`. This includes
   «одну строку», an import, a fix of a checker finding or of a `Unit.java check` finding,
   a compilation error, and «быстрее самому». All of this is a retry of the executor with
   the findings (`references/manager.md`, item 8). Before EACH change of a file, ask
   yourself: does the path start with `.gigacode/`? If not -> stop, this is the work of the
   executor. Code collects in your context and pushes out the rules. This mode exists to
   prevent this.
1. **Confirmation rule.** Each PVATF name (class, method, annotation, matcher, setting,
   dependency) must first be in «Таблицу подтверждений» of the unit card. The line must
   have a link to a doc notes record. If there is no line, do not write the name. Even for
   `cannot find symbol`, the answer is in the documentation, not in the `.jar`.
2. **You do not ask questions.** If you want to ask -> `references/stuck.md`: a decision
   from the table, or a place with the mark `решить человеку` in «Входящие». Then continue.
   Stop only when you physically cannot work:
   - the project does not compile after 3 attempts;
   - there is no MCP;
   - there are changes of other people in git. If section 6 of the
   migration map has a question with `ответ: -` -> СТОП at Step 1.
3. **One chat - one unit, complete.** For a unit `tech`, do all substeps one after another
   in this chat. The context compresses itself. Then run `Unit.java recite` and continue
   from the first substep that is not done. Do more than one unit only as a batch
   (`references/start.md`).
4. **One thread.** Do only the steps of «Что сделать» of the current substep, in order. If
   you remember a different task, write a line in «Входящие» and go back to the current step.
5. **The kind of substep sets the limits.**
   - `env` - only build and configuration.
   - `core` - by `core_mode`: `new` - a new base, do not touch the old code; `in-place` -
     the internal parts, the public methods stay the same.
   - `usage` - move steps and tests to the framework.
   - `cleanup` - only remove.
   - `fix` - only the findings from the unit card.
   - `arch` - only the steps of the unit card.
   - `markup` - only the markup annotations (`references/markup.md`).
   - `review` - by `references/review-subagent.md`.
6. **The pattern is the migration map, not the old code.** Use the block `T-<tech>`, the
   architecture plan and the doc notes. From the old code, take only the data. Do not make a
   class that is not in the plan and not in the unit card. Remove legacy completely: no
   adapters and nothing «для совместимости».
7. **Code rules - only the rules of the substep** (`Unit.java rules`, `references/work.md`,
   Step 5, item 1). `Unit.java check` finds the mechanical errors. The most frequent errors:
   - the response is changed into a DTO (`MR-41`);
   - checks use own constructions instead of `.should(...)` with matchers (`MR-48`);
   - extra layers, delegates and nested classes (`MR-49`);
   - own reading of settings (`MR-47`).
8. **The subagent «проверяющий» checks each substep** with a clean context, before the
   commit (`references/check.md`, Step 6, item 9).
9. **Run only specific tests.** For `env`, and for `core` in mode `new` - only compilation.
   For all other kinds - ONE representative test from the unit card, `timeout 600`. Never
   run the full set, a module or a class.
10. **Connection data - only from `CONNECTIONS.md`.** Use the same values that the project
    used before, in the framework settings files. For more than one stand, use different
    keys. Do not write empty values, `TODO` or invented values.
11. **If you made it, connect it.** A class that you made must have callers, or substeps
    that move code to it (`references/check.md`, item 7).
12. **Subagents of the executor:**
    - «документация» and «примеры» - agents `pvatf-docs` and `pvatf-examples`
      (`references/doc-subagent.md`);
    - «проверяющий» - agent `pvatf-checker` (`references/check.md`);
    - «ревью» (`references/review-subagent.md`).
    These subagents only read and answer. In manager mode there is also «исполнитель
    подшага» - agent `pvatf-executor` (`references/manager.md`). It changes the files of its
    substep and runs the build and the test. Only you change the unit card and the migration
    map, and only you make commits. For a unit `markup`, agent `pvatf-marker` does this work
    instead (`references/markup.md`). It makes commits of its files itself. You still keep
    the unit card and the migration map. Call the agents by name and give only the task
    (`references/core-rules.md`, rule 7). All of them are MANDATORY where the skill names
    them (`references/core-rules.md`, rule 7).

## If you lost the thread

Signs:
- you do something that is not in the steps of the unit card;
- you started a second task before you finished the first;
- you change a file that is not in the unit card;
- you cannot name the number of the step that you do;
- the context was compressed and you do not remember where you were.

Then stop and do these steps:

(1) run `Unit.java recite M-<nnn>` - it shows the current substep, its files, the result and
the checkpoint; (2) run `git status --short` to see what is already changed; (3) open the
file from the table «Этот скилл разбит на части» for the current moment and continue from
the first step that is not done. If this does not help, read this SKILL.md and the unit card
again. The unit card is the source of truth, not the chat. If you started an unrelated
task, put it back as it was (`git checkout -- <файл>`) and write it as a line in «Входящие».

## Before each commit of a substep - five questions

0. Did you run `Unit.java recite` before the substep, and is its output in the chat?
1. Did you get the rules of the substep with `Unit.java rules` and read them? Does
   `Unit.java check` show `находок 0` (the last line of the output is copied into «Сделано»)?
2. Does «Сделано» have the line `проверка: ...` from the checker?
3. Is there no question to the human, no response DTO, and no empty settings key?
4. Manager mode: did only the executor change the project files in this substep, and did
   you change only files in `.gigacode/`?

If one answer is «нет» -> do not make the commit. Go back to the necessary step.
