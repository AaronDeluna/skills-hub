# pvatf-openspec

Набор PVATF (миграция, автотесты по ТК, окружение, обновление фрейма, ревью, разметка,
зависимости) поверх OpenSpec. Каждая работа - изменение `openspec/changes/<имя>/`:
proposal -> (tc) -> design -> tasks -> apply -> архив. Артефакты пишут скрипты набора,
модель только запускает их; apply выполняют скиллы набора и агенты pvatf-*.

| Что | Где |
|-----|-----|
| Установка и как пользоваться | [INSTALL.md](INSTALL.md) |
| Схема автотеста по ТК | `openspec/schemas/pvatf-autotests/` (proposal -> tc -> design -> tasks) |
| Схема остальных работ | `openspec/schemas/pvatf-work/` (proposal -> design -> tasks) |
| Создание изменений и «что дальше» | `skills/de-pvatf-orchestrator/scripts/os_work.py` |
| Артефакты автотеста | `skills/de-pvatf-autotest-plan/scripts/os_artifacts.py` |
| Точка входа | скилл `de-pvatf-orchestrator`, Шаг 0 (режим OpenSpec) |

Всё по работе лежит в `openspec/changes/<имя>/` (план автотеста и карта миграции - это `design.md` изменения,
рабочие файлы - `outputs/`), общее для проекта - в `openspec/pvatf/`. Пути считает `skills/*/scripts/pvatf_paths.py`.
В проекте без `openspec/config.yaml` набор работает как pvatf-skillkit (файлы в `.gigacode/data/`).
