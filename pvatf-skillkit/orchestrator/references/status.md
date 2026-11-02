# Migration status

Part of the skill `orchestrator`. Open this file only when SKILL.md sends you here.

Read the table «4. Юниты работ» and show:
- how many units there are in total / `done` / `in-progress` / `todo` / `blocked`;
- by phases: which phase is in progress now;
- which technology is in migration now, and which technologies are next (in the order of the map).
  Also, which technologies stay on the old implementation (`keep`);
- if a technology unit is in progress (`tech`, status `in-progress`): how many of its substeps are done and
  which substep is next - `grep -E "^\| S-[0-9]+" .gigacode/data/migration/units/M-<nnn>.md`
  (only the substep table, do not read the full card);
- which unit is next;
- the open questions (section 6 of the map), if there are open questions. Also say that the migration is stopped until the human answers them;
- the lines `решить человеку` from the section «5. Входящие»: how many and which (`grep -n "решить человеку" .gigacode/data/migration/MIGRATION-MAP.md`).

## Which files keep which data

All files are in one folder in the root of the migrated project: `.gigacode/data/migration/`

| File                       | Contents                                                         | Who writes it        |
|----------------------------|-------------------------------------------------------------------|------------------|
| `MIGRATION-MAP.md`         | The map: the project passport, what we replace with what, the list of units and their statuses, the session log, «что уже изменилось» | `migration-map`, `migration-step` |
| `ARCHITECTURE.md`         | The architecture plan: the layers, packages and classes of the project after the migration, and the task of each class | `migration-map`, `migration-step` |
| `CONNECTIONS.md`           | The connection register: addresses, credentials, certificates, topics, environment variables from the project, and where they go in the framework settings | `migration-map`, `migration-step` |
| `doc-notes/<технология>.md` | The doc notes of the framework documentation from MCP, by technology: questions, answers, the words that were used in the questions | `migration-map`, `migration-step` |
| `units/M-<nnn>.md`         | The card of one unit: files, steps, documentation basis, execution log | `migration-map`, `migration-step` |
| `inventory/<модуль>.md`    | The raw inventory results, by module                        | `migration-map`  |
| `MIGRATION-REVIEW.md`      | The report of the check of the full migration: findings by rounds, verdict | `migration-review` |
| `archive/MAP-ARCHIVE.md`  | The map archive: done units, closed questions, old log - the data that compression removed from the map | `orchestrator` |
| `review/M-<nnn>.md`        | The review report of the migrated code: findings of the subagents and what was done with them | `migration-step` |
| `inventory/technologies.md` | The subagent report: which technologies the project uses (if the human did not name them) | `migration-map`  |


