# Установка pvatf-openspec

Набор PVATF поверх OpenSpec: каждая работа - изменение `openspec/changes/<имя>/` с артефактами
proposal -> (tc) -> design -> tasks -> apply -> архив. Документ читается человеком и агентом:
агенту достаточно сказать «установи pvatf-openspec по INSTALL.md» - он идёт по шагам.

## Пререквизиты

1. CLI OpenSpec 1.12 или новее (Node.js 20.19+):
   ```
   npm install -g @fission-ai/openspec@latest
   openspec --version
   ```
2. GigaCode CLI: `gigacode --version`.
3. Python 3.8+ - скрипты набора.

## 1. Скиллы, агенты, команды

Вариант А - расширение GigaCode (каталог этого пакета в клоне):
```
gigacode
/extensions install /полный/путь/к/pvatf-openspec
```
Агенты расширение не ставит: скопируйте `agents/` пакета в `.gigacode/agents/` проекта.

Вариант Б - копированием в проект:

| Из пакета | В проект |
|-----------|----------|
| `skills/*` | `.gigacode/skills/` |
| `agents/*` | `.gigacode/agents/` |
| `commands/*` | `.gigacode/commands/` |

## 2. Каталог openspec/ проекта

Отдельный проект автотестов (основной случай):

| Из пакета | В проект |
|-----------|----------|
| `openspec/schemas/pvatf-autotests/` | `openspec/schemas/pvatf-autotests/` |
| `openspec/schemas/pvatf-work/` | `openspec/schemas/pvatf-work/` |
| `openspec/config-example/config.yaml` | `openspec/config.yaml` (поправить `context`) |

Создайте пустые `openspec/changes/` и `openspec/specs/`, если их нет.
`openspec init` / `openspec update` не запускайте - они перезапишут скиллы стандартными.

Автотесты в репозитории сервиса, где уже стоит openspec-de: вторую основную схему не ставьте.
Скопируйте только схемы `pvatf-autotests` и `pvatf-work` в `openspec/schemas/` - изменения
набора создаются с явной схемой (`openspec new change --schema ...`, это делает os_work.py),
`schema:` в config.yaml не меняйте.

## 3. Проверка

```
openspec --version
openspec schema validate pvatf-autotests
openspec schema validate pvatf-work
ls .gigacode/skills/orchestrator/SKILL.md .gigacode/agents/pvatf-generator.md .gigacode/agents/pvatf-artifacts.md
python3 .gigacode/skills/orchestrator/scripts/os_work.py next
```
Последняя команда печатает `ИЗМЕНЕНИЯ: нет` и `ДЕЙСТВИЕ: создай изменение ...` - всё стоит.

## Как пользоваться

В чате GigaCode: `/orchestrator <просьба>` (или команда `/pvatf <просьба>`).

| Просьба | Изменение |
|---------|-----------|
| «сгенерируй автотест по CMN-T120» | `autotest-cmn-t120` (схема pvatf-autotests) |
| «проверь тест-кейс CMN-T120» | `autotest-cmn-t120` с остановкой после артефакта tc; «сгенерируй автотест по CMN-T120» снимает остановку |
| «настрой окружение» | `env-setup` |
| «обнови фрейм» | `frame-update` |
| «мигрируй проект на PVATF» | `migration` (сначала карта migration-map) |
| «проверь автотест src/test/java/.../XTest.java» | `autotest-review-xtest` |
| «разметь тесты» | `markup` |
| «проверь зависимости» | `deps-review` |
| «продолжи» | следующее действие по активному изменению |

Код задачи в просьбе («по задаче ABCDE-123») попадает в имя изменения: `abcde-123-autotest-cmn-t120`.

## Где что лежит

| Что | Где |
|-----|-----|
| Работа (автотест, миграция, окружение, ...) | `openspec/changes/<имя>/`: `proposal.md`, `design.md`, `tasks.md`, рабочие файлы скиллов - `outputs/` |
| План автотеста по ТК | `design.md` изменения `autotest-<ключ>`; ТК и его проверка - `tc/<ключ>.md` |
| Карта миграции | `design.md` изменения `migration`; юниты - группы `tasks.md`; карточки юнитов - `outputs/units/` |
| Общее для проекта | `openspec/pvatf/`: конспект документации фрейма (`doc-notes/`, `migration/doc-notes/`), паспорт окружения `env/ENV.json`, `env/release-notes.md` |
| Готовые работы | `openspec/changes/archive/<дата>-<имя>/` после архива |

Каталога `.gigacode/data/` в режиме OpenSpec нет.
