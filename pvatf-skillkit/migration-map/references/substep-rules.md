# Substep rules - which MR numbers each substep needs

This is a common file of the kit. The source is `shared/substep-rules.md`.
`scripts/SyncShared.java` puts the copies into the skills. To change the table, change only the source.

Use of this table:
- `migration-map` fills the field «Правила подшага» in the `tech` card and the field «Правила юнита» in
  the cards of the other types. `scripts/Card.java` checks that the field contains the same rules as the table;
- `migration-step` takes the numbers from this table if the field in the card is empty (old map):
  `scripts/Unit.java rules`.

| Substep kind / unit type | Rules |
|-------------------------|---------|
| `env` | `MR-12`, `MR-16`, `MR-31`, `MR-36`, `MR-47` |
| `core`, mode `new` | `MR-12`, `MR-13`, `MR-24`, `MR-30`, `MR-32`, `MR-41`, `MR-43`, `MR-49`, `MR-50` |
| `core`, mode `in-place` | «то же, что `core` `new`» (all the rules of the row above), plus `MR-7`, `MR-28` |
| `usage` | `MR-9`, `MR-10`, `MR-11`, `MR-12`, `MR-29`, `MR-41`, `MR-42`, `MR-46`, `MR-48`, `MR-50` |
| `cleanup` | `MR-23`, `MR-26`, `MR-27`, `MR-31`, `MR-39` |
| `arch` | `MR-3`, `MR-25`, `MR-26`, `MR-37`, `MR-38`, `MR-39`, `MR-49`, `MR-50` |
| `markup` | `MR-51` |
| `fix` | `MR-9`, `MR-11` and the rules that the findings refer to |
| `review` | all - the checklist of the review subagent (the field in the card is `-`) |

**Additions:**
- step style `flow` (passport line «Стиль шагов») -> add `MR-44` to `core` and `usage`;
- the substep makes a test class or a base test class -> add `MR-46` if it is not there;
- you can add the rules from the block «добавлено человеком» (`MR-H<n>`) to any substep.

Do not write other numbers in the field. Mechanical rules (`var`, imports, setters, names,
`TODO`: `MR-4`, `MR-5`, `MR-6`, `MR-14`, `MR-15`, `MR-17`, `MR-21`, `MR-22`, `MR-33`,
`MR-34`, `MR-35`, `MR-45`) are not in this table: the self-check `Unit.java check` finds them.
