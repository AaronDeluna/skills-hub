---
name: migration-map
description: 'Makes a detailed migration map of a test-automation project to the framework PVATF BEFORE any change to the code. The map has: an overview of the framework; doc notes from the MCP documentation for each technology of the project (REST, Kafka, DB and others); an inventory of the project (what is used and where); a matrix "current state -> target state in PVATF"; architecture problems; a split of all the work into small units with order and dependencies. The result is files in .gigacode/data/migration/. The agent uses them in each next chat. Does not change the project code. Use when the human asks to make a migration map or plan, to analyze the project before the migration to PVATF, or to update the migration map. Usually orchestrator calls it.'
---

**Language.** These instructions are in English. Write everything for the human in Russian:
messages, questions, reports, the map, unit cards, notes and commit messages. Copy every
template exactly as it is shown, with its Russian headings and field names.

# Migration map to PVATF (migration-map)

You make the **migration map**. The migration map is a set of files. Other chats use these
files to migrate the project in small parts. The unit executor does not see this chat. The
unit executor does not examine the project again. The migration map must let the executor work
without guesses. **You do not migrate anything. You do not change the project code.** You
only read the project and write the files of the migration map.

The project to migrate is a SEPARATE test-automation project (AQA). It tests a service from
the outside through REST, Kafka, databases, OpenShift and other technologies. The framework
(PVATF) is a set of modules for such autotests. ONLY the framework documentation tells what
these modules can do.

First, read `references/core-rules.md`. It contains the general migration rules.

## The skill has stages - read only the current stage

Do not read all of the skill at once. Less text in memory means fewer forgotten rules.

| When | What to read |
|-------|---------------|
| Start of the chat | this SKILL.md, then «Старт» below |
| Stage 1 - framework overview, versions, framework sources | `references/stage-1.md` |
| Stage 2 - map passport, Spring, connections, inventory | `references/stage-2.md` |
| Stage 3 - documentation for each technology and the matrix «как сейчас -> как в PVATF» | `references/stage-3.md` |
| Stage 4 - architecture problems and the architecture plan | `references/stage-4.md` |
| Stage 5 - units and unit cards | `references/stage-5.md` |
| Stage 5 - unit card of a `tech` unit (analysis, composer, check) | `references/card-subagents.md` |
| Stage 6 - show the migration map to the human, update of the migration map | `references/stage-6.md` |
| You want to ask the human a question | `references/questions-filter.md` - use the filter first |
| You need a subagent | `references/subagents.md`, its section |

**The scripts of this skill are in `.gigacode/skills/migration-map/scripts/`.** The commands
below are ready to use. Copy them and run them as they are, from the root of the project to
migrate (the directory with `.gigacode/`). You need Java 11+.

If the script is not at this path (the skills are installed in a different place), find it one
time: `find . ~/.gigacode -path "*migration-map/scripts/*.java" 2>/dev/null | head -3`. Then
use the directory that you found.

If the script stops with an error, show the error in the chat. Then do the same work with
manual commands, as this skill describes. Do not skip a script silently.

When you finish a stage, **immediately** mark it `[x]` in section 0 of the migration map and
update `map_stage` in the header. Only after that, open the next file. Write the results into
the files while you do the stage.

## Rules of the migration map

1. **Do not touch the project code.** Do not make changes, commits or branches. Write only into
   `.gigacode/data/migration/`.
2. **Do not read all of the project.** Count and search with commands (`find`, `grep`, `wc`).
   Open a full file only as a sample - not more than 3 for one usage pattern
   (`references/inventory-guide.md`). Exception: the settings and connection files at Stage 2.
3. **Each replacement in the migration map has a documentation basis** - a doc notes record
   `D-<tech>-<n>`. If there is no basis, write `НЕТ В ДОКЕ`.
   Then use the table «Документация молчит» (Stage 3). Ask the human a question only if this table has no row for it and the
   question passed the filter.
4. **If the documentation has no technology, that technology is not migrated (`keep`).**
   Some technologies or their parts (a specific DBMS, a broker) are not in the documentation.
   They stay on the old implementation. Do not make a `tech` unit for it. Do not write its code
   into legacy. Only `arch` units are allowed for it.
5. **Old wrappers and checks do not move.** These are legacy to remove:
   - wrappers around libraries;
   - custom asserts;
   - custom JSON comparators and parsers;
   - response DTOs made only to compare fields.

   Use the framework mechanisms instead: the request returns a validatable object, and you do
   the checks on it through `.should(...)` with matchers.
6. **Migrate technologies one at a time and to the end, from the simple to the complex.** Stage
   2 sets the order.
7. **The target state comes first.** At Stage 3, write a block `T` for each technology. The
   block shows how the code looks at the end, from the documentation, not from the old classes.
   All units lead to this block.
8. **Subagents of the migration map** - use only the subagents that `references/subagents.md`
   describes:
   - documentation;
   - technologies of the project;
   - inventory of modules;
   - examples;
   - analysis of a technology;
   - unit card composer;
   - unit card checker.

   Documentation and examples are the agents `pvatf-docs` and `pvatf-examples`. Call them by
   name and give them only the task (`references/core-rules.md`, rule 7). All subagents except
   the composer only read and answer by the template. The composer writes exactly one file - its
   unit card. Nobody changes the project code.

## Start («Старт») - make the migration map or find where to continue

```
mkdir -p .gigacode/data/migration/units .gigacode/data/migration/inventory .gigacode/data/migration/doc-notes
ls .gigacode/data/migration/
```

- No `MIGRATION-MAP.md` -> make it EXACTLY by the template from `references/map-template.md`,
  with `map_status: building`, `map_stage: 1`. The field `scope`: if the human asks to migrate
  only the core or not to touch the tests -> `core`, else `full`. Then go to
  `references/stage-1.md`.
- `MIGRATION-MAP.md` exists -> read the header and section 0. Open the stage file from
  `map_stage`. Do not do the completed stages again.
- The human asks to update the migration map (the project changed, the answers of the human
  change the migration map) -> `references/stage-6.md`, «Обновление карты».

## Final summary

- which stages you did in this chat, the current `map_stage` and `map_status`;
- the paths to the files: `MIGRATION-MAP.md`, the doc notes `doc-notes/*.md`, the number of
  unit cards;
- the open questions to the human;
- what is next: «Откройте новый чат и напишите: `/orchestrator Продолжи миграцию`».

## If you lost the thread

Open `MIGRATION-MAP.md`: the header and section 0. They show which stage is done. Open the
file of this stage and continue from the first item that is not done. Do not do completed work
again.
