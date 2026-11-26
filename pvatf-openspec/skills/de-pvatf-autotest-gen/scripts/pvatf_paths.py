#!/usr/bin/env python3
"""
Где лежат рабочие файлы набора PVATF. Общий модуль (копия из shared/scripts).

Два режима, выбираются по файлу openspec/config.yaml в корне проекта:
- OpenSpec: всё по работе - в каталоге изменения openspec/changes/<имя>/:
  артефакты (proposal.md, design.md, tasks.md, tc/) и рабочие файлы скиллов (outputs/).
  План автотеста и карта миграции - это design.md своего изменения.
  Общее для проекта (конспект документации, паспорт окружения ENV.json, очередь ТК) -
  в openspec/pvatf/.
- Обычный (файла нет): всё в .gigacode/data/, как в pvatf-skillkit.

Изменение ищется по ключам .openspec.yaml: x-pvatf-kind (вид) и x-pvatf-tc / x-pvatf-object
(объект). Нет нужного изменения - создаётся (каталог и .openspec.yaml; CLI не нужен).
Python 3.8+, только стандартная библиотека.
"""
import re
from datetime import date
from pathlib import Path

OPENSPEC = Path("openspec")
LEGACY = Path(".gigacode") / "data"
SCHEMA = {"autotest": "pvatf-autotests"}  # остальные виды - pvatf-work


def on():
    """Режим OpenSpec: в корне проекта есть openspec/config.yaml."""
    return (OPENSPEC / "config.yaml").is_file()


def root():
    """Общий каталог проекта: конспекты документации (doc-notes/, migration/doc-notes/)."""
    return OPENSPEC / "pvatf" if on() else LEGACY


def env_dir():
    """ENV.json, ENV-INIT.md, ENV-SETUP.md, release-notes.md, QUEUE.md, de-pvatf-env-update/."""
    return OPENSPEC / "pvatf" / "env" if on() else LEGACY / "autotest"


def meta(folder):
    result = {}
    try:
        text = (Path(folder) / ".openspec.yaml").read_text(encoding="utf-8")
    except OSError:
        return result
    for line in text.splitlines():
        m = re.match(r"^([\w-]+):\s*(.*?)\s*$", line)
        if m:
            result[m.group(1)] = m.group(2).strip("\"'")
    return result


def changes(kind=None):
    """Активные изменения набора (не архив): [(каталог, meta)], по имени."""
    base = OPENSPEC / "changes"
    result = []
    for folder in sorted(base.iterdir()) if base.is_dir() else []:
        if folder.name == "archive" or not folder.is_dir():
            continue
        m = meta(folder)
        if m.get("x-pvatf-kind") and (kind is None or m["x-pvatf-kind"] == kind):
            result.append((folder, m))
    return result


def same(a, b):
    return str(a).replace("\\", "/").strip("./").lower() == str(b).replace("\\", "/").strip("./").lower()


def find_change(kind, obj=None):
    for folder, m in changes(kind):
        if obj is None or same(m.get("x-pvatf-tc") or m.get("x-pvatf-object", "-"), obj):
            return folder
    return None


def change_name(kind, obj, task=""):
    if kind == "de-pvatf-autotest-review":
        obj = Path(obj).stem
    slug = re.sub(r"[^a-z0-9]+", "-", str(obj).lower()).strip("-")
    if not slug and str(obj).strip() not in ("", "-"):
        # объект без латиницы и цифр («тест один») - короткий хэш, иначе разные объекты получат одно имя
        slug = __import__("hashlib").sha256(str(obj).encode("utf-8")).hexdigest()[:8]
    return "-".join(p for p in (task.lower(), kind, "" if slug in ("", "-") else slug) if p)


def ensure_change(kind, obj="-", task=""):
    """Каталог изменения вида kind для объекта obj; нет - создаётся."""
    found = find_change(kind, None if obj in ("-", None) and kind != "autotest" else obj)
    if found:
        return found
    folder = OPENSPEC / "changes" / change_name(kind, obj, task)
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["schema: " + SCHEMA.get(kind, "pvatf-work"), "created: " + date.today().isoformat(),
             "skip_specs: true", 'x-pvatf-kind: "' + kind + '"']
    lines.append(('x-pvatf-tc: "' if kind == "autotest" else 'x-pvatf-object: "') + str(obj).replace('"', "") + '"')
    (folder / ".openspec.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder


# ---------- автотест по ТК ----------

def autotest_dir(key, create=True):
    """Рабочие файлы автотеста по ТК: TC.md, TC-CHECK.md, ENV-TC.md, fragments/, CHECK.md."""
    if not on():
        return LEGACY / "autotest" / key
    folder = ensure_change("autotest", key) if create else find_change("autotest", key)
    return (folder or OPENSPEC / "changes" / change_name("autotest", key)) / "outputs"


def plan_file(key, create=True):
    """План автотеста: design.md изменения (OpenSpec) или PLAN.md (обычный режим)."""
    if not on():
        return LEGACY / "autotest" / key / "PLAN.md"
    return autotest_dir(key, create).parent / "design.md"


def autotest_keys():
    """Ключи ТК, у которых есть TC.md."""
    if not on():
        base = LEGACY / "autotest"
        return sorted(p.parent.name for p in base.glob("*/TC.md")) if base.is_dir() else []
    return sorted(m.get("x-pvatf-tc", "") for f, m in changes("autotest") if (f / "outputs" / "TC.md").is_file())


def next_no_tc_key():
    """Следующий свободный служебный ключ работы без ТК: NOTC-<n> (среди активных, архивных и обычных работ)."""
    used = list(autotest_keys())
    if on():
        used += [m.get("x-pvatf-tc", "") for f, m in changes("autotest")]
        used += [meta(f).get("x-pvatf-tc", "") for f in (OPENSPEC / "changes" / "archive").glob("*") if f.is_dir()]
    numbers = [int(k.split("-")[1]) for k in used if re.fullmatch(r"NOTC-[0-9]+", k or "")]
    return "NOTC-" + str(max(numbers, default=0) + 1)


def plan_files():
    """Все планы автотестов: [(ключ, путь)]."""
    if not on():
        base = LEGACY / "autotest"
        return [(p.parent.name, p) for p in sorted(base.glob("*/PLAN.md"))] if base.is_dir() else []
    return [(m.get("x-pvatf-tc", ""), f / "design.md") for f, m in changes("autotest") if (f / "design.md").is_file()]


# ---------- миграция и другие виды ----------

def _change(kind, create, obj="-"):
    found = ensure_change(kind, obj) if create else find_change(kind, None if obj == "-" else obj)
    return found or OPENSPEC / "changes" / change_name(kind, obj)


def migration_dir(create=True):
    """Рабочие файлы миграции: карточки юнитов, инвентаризация, CONNECTIONS.md, tmp/."""
    if not on():
        return LEGACY / "migration"
    return _change("migration", create) / "outputs"


def map_file(create=True):
    """Карта миграции: design.md изменения migration (OpenSpec) или MIGRATION-MAP.md."""
    if not on():
        return LEGACY / "migration" / "MIGRATION-MAP.md"
    return _change("migration", create) / "design.md"


def migration_notes():
    """Конспект документации миграции (общий для проекта)."""
    return root() / "migration" / "doc-notes"


def review_dir(test_file, create=True):
    """Рабочие файлы ревью автотеста: REVIEW-PLAN.md, REVIEW.md, копии."""
    if not on():
        return LEGACY / "de-pvatf-autotest-review" / Path(test_file).stem
    return _change("de-pvatf-autotest-review", create, str(test_file).replace("\\", "/")) / "outputs"


def kind_dir(kind, legacy, create=True):
    """Рабочие файлы вида без объекта (deps-review, markup)."""
    return _change(kind, create) / "outputs" if on() else LEGACY / legacy


def review_plans():
    """Все планы ревью автотестов (REVIEW-PLAN.md)."""
    if not on():
        base = LEGACY / "de-pvatf-autotest-review"
        return sorted(base.glob("*/REVIEW-PLAN.md")) if base.is_dir() else []
    return [f / "outputs" / "REVIEW-PLAN.md" for f, m in changes("de-pvatf-autotest-review") if (f / "outputs" / "REVIEW-PLAN.md").is_file()]
