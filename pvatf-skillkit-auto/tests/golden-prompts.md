# Золотые промпты оркестратора

Для разработчиков набора (CLAUDE.md, правило 10). После смены модели или текста скилла
прогоните каждую строку в тестовом проекте и сверьте три колонки. Скрипты отдельно
проверяет `python3 scripts/selftest.py`.

| Состояние проекта | Промпт | Аргумент next_action.py | ДЕЙСТВИЕ | Какой скилл запущен |
|-------------------|--------|-------------------------|----------|---------------------|
| агентов нет в `.gigacode/agents/` | `/orchestrator Проверь окружение` | `env check` | `агенты установлены` | никакой, просьба перезапустить GigaCode |
| `ENV.json` нет | `/orchestrator Сгенерируй автотест по ТК tc.md` | `autotest tc.md` | `env-check` | `env-check`, режим check |
| `ENV.json` ok | `/orchestrator Сгенерируй автотест по ТК tc.md` | `autotest tc.md` | `autotest-plan` | `autotest-plan` с файлом `tc.md` |
| `ENV.json` ok | `/orchestrator Проверь тест-кейс tc.md` | `autotest tc.md` | `autotest-plan` | `autotest-plan`, шаги 1-3 |
| `PLAN.md` planned | `/orchestrator Продолжи генерацию CMN-T120` | `autotest CMN-T120` | `autotest-gen CMN-T120` | `autotest-gen` |
| `PLAN.md` checked | `/orchestrator Продолжи генерацию CMN-T120` | `autotest CMN-T120` | `финал CMN-T120` | никакой, итог из `CHECK.md` |
| `TC-CHECK.md` FAIL | `/orchestrator Продолжи генерацию BAD-T1` | `autotest BAD-T1` | `autotest-plan BAD-T1` | `autotest-plan`: показать находки, план не строить |
| `ENV.json` ok | `/orchestrator Проверь автотест src/test/java/ru/demo/tests/PayTest.java` | `review src/test/java/ru/demo/tests/PayTest.java` | `autotest-review src/test/java/ru/demo/tests/PayTest.java` | `autotest-review`, шаги 1-8, `approve all --target-only` без вопросов |
| `REVIEW-PLAN.md` fixing | `/orchestrator Продолжи проверку автотеста` | `review` | `autotest-review <файл>` | `autotest-review` с шага 4 |
| `ENV.json` ok | `/orchestrator Оптимизируй тест` | `review` | `autotest-review` | никакой, итог с `Нужно от человека: путь к тест-классу` |
| любое | `/orchestrator Настрой окружение` | `env setup` | `env-setup` | `env-check`, режим setup |
| компиляция ok | `/orchestrator Обнови окружение` | `env update` | `env-update` | `env-update`, этапы 1-9 |
| `ENV-UPDATE.md` in-progress | `/orchestrator Продолжи обновление` | `env update` | `env-update` | `env-update` с этапа `update_stage` |
| компиляция failed | `/orchestrator Обнови фрейм` | `env update` | `env-setup` | `env-check`, режим setup |
| карты нет | `/orchestrator Мигрируй проект на PVATF` | - | `migration-map` | `migration-map`, Этап 1 |
| карта approved, есть todo | `/orchestrator Продолжи миграцию` | - | `migration-step M-<nnn>` | `migration-step` |
