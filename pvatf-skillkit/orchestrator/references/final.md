# End of the migration

Part of the skill `orchestrator`. Open this file only when SKILL.md sends you here.

1. Say that all units of the map are done and that the migration check found no findings (give the round number).
2. Examine the section «5. Входящие» of the map. If it has items that nobody analyzed, tell this to the human.
   Then suggest to start `migration-map` (map update) to change these items into units.
3. Give the names of the reports: `.gigacode/data/migration/MIGRATION-REVIEW.md` and
   `.gigacode/data/migration/review/*.md`.
4. **Service folder.** Ask one question: «Миграция завершена. Удалить служебные файлы
   миграции `.gigacode/data/migration/`? да / нет». Only after the answer «да», run:
   `git rm -r --cached .gigacode/data/migration 2>/dev/null; rm -r .gigacode/data/migration`.
   WARNING: Without «да», do not delete anything. Do not suggest the deletion if one of these is true:
   - there are units that are not done;
   - there are open questions;
   - `review_status` is not `clean`.
