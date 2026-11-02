# Scope of the migration (`scope`)

Part of the skill `orchestrator`. Open this file only when SKILL.md sends you here.

| `scope` | What it means | Which units you can do |
|---------|----------------|-----------------------------|
| `full`  | full migration (default) | all |
| `core`  | only the core, do not change the tests | units `env`; in units `tech` - only the substeps `разбор`, `env`, `core` (`migration-step` itself obeys this); units `arch`, `cleanup`, `review` are not available |

Change `scope` only if the human asks for it directly:
- «переведи только ядро», «тесты не трогай» -> write `scope: core` in the header of the map;
- «мигрируй всё», «продолжи полную миграцию», «теперь переводи тесты» -> `scope: full`.
Do not change `scope` yourself. If there is no map yet, give the request about the scope to `migration-map`.
If the map is already made as `full` and the human asks «только ядро» -> the cards of the `core` units
are written for a different mode. Start `migration-map` in update mode (Stage 6) and give it the
request: it writes the `core` cards again. The change `core` -> `full` does not need a map update.

The order of the work is fixed in the map. Do not discuss it. The order:
- Java 17, if the project has a lower version (the very first unit).
- Then the dependencies of all technologies.
- Then the technologies one by one, from simple to complex. Each technology is one unit, done to the end.
  The substeps: analysis -> environment -> step classes -> migration of the steps and tests ->
  removal of legacy -> code review of the technology by subagents and fix of the findings.
- Then the architecture.
- Then the final cleanup.

When all units are `done`, do the final check of the full project (`migration-review`).
