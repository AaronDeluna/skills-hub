# Stage 4 - Architecture problems (section 3 of the migration map) and the architecture plan

This file is a part of the skill `migration-map`. The general rules are in `references/core-rules.md`. The rules of the migration map and the order of stages are in `SKILL.md`.

The target architecture is **the architecture that the framework documentation describes**
(the sections about the project structure and the layers). First, look at the record
`D-common-3` in `doc-notes/common.md`. If it is not sufficient, start the documentation
subagent (technology `common`) with these questions:
- «какие слои и пакеты
должны быть в проекте автотестов»;
- «где должна лежать логика шагов - отправка запросов,
запросы в БД - в тест-классе или в отдельном слое (Flow, steps), пример»;
- «что в каком слое лежит»;
- «кто кого может вызывать»;
- «что фрейм запрещает в структуре проекта».

Write the answers into `doc-notes/common.md`. Write the target architecture in 5-10 lines at
the start of section 3 of the migration map. Compare the project with it and write the
deviations. What to look for and which commands to use - see `references/inventory-guide.md`,
the section «Архитектура».

For each problem, write a row `A-<n>`: what is wrong -> where (modules, number of files, 1-2
examples) -> how it must be -> basis (`D-<tech>-<n>` or `нет в доке - на решение человека`)
-> when to fix:
- `вместе` - the problem disappears itself when the code moves to PVATF by the documentation;
- `после` - separate work after the migration.

Fix the architecture AFTER the migration. There is no term `до`. If you think that a problem
blocks the migration - this is a question to the human in section 6.

Bad architecture is also migration work: each `A-<n>` must go into units at Stage 5. Do NOT
make a unit from a problem that has no basis in the documentation. Write it as a question in
section 6. The human decides.

**Architecture plan - the file `.gigacode/data/migration/ARCHITECTURE.md`.** This is the
planned architecture of the project AFTER the migration: the layers, the package tree, and the
class table (which class is responsible for what). The unit executor uses it to decide where
each code goes, and does not make unnecessary classes. Make it here, after the blocks `T` of
all technologies:
1. Read `references/architecture-template.md` - the template and the rules.
2. Section 1 (layers) and section 2 (package tree) - by the target architecture from the start
   of section 3 of the migration map.
   - If the step style in the map passport is `flow` -> the step layer in the plan is the flow
     classes. Make section 3 by the part of the template «Если стиль шагов - flow». Decide
     which flows are necessary by the test scenarios (which steps come one after the other in
     one test), not by the old classes.
   - Keep the packages that the project already has and that fit, with their names. Make a
     new package only if a layer has no place.
3. Section 3 (classes) - collect it from the blocks `T` («Что будет», «Слой шагов», «Данные проекта») and
   from the problems `A`: all new classes, all classes that stay, the test classes and the
   data - one row for each package. Check EACH row against the 10 rules from the template:
   1) one responsibility;
   2) no repetitions;
   3) something calls it;
   4) a clear name;
   5) one technology;
   6) not one class for everything;
   7) no unnecessary classes;
   8) the base test class;
   9) it agrees with the block `T`;
   10) layers without unnecessary items (one base class for each technology, no facades and no
       nested classes).
4. If the plan does not agree with the block `T` (an unnecessary class, two classes for one
   task) -> correct the block `T` and the plan so that they agree.
5. If you cannot decide how to split the step classes (by API, by entity, by service) - first
   look at how the project does it now and at the record `D-common-3`. Ask the human a
   question only after the question filter.

**Stop because of size.** If the stop condition of Stage 2 was true - stop again after Stage 4
and ask the human to continue in a new chat.

Check: the file `ARCHITECTURE.md` exists. In its section 3, each row has the fields «За что
отвечает» and «Кто вызывает» filled in. Mark Stage 4 `[x]`, `map_stage: 5`.

