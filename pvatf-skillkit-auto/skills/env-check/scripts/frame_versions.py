"""Где в файлах сборки объявлена версия фрейма PVATF. Модуль: его импортируют env_check.py и
env_update.py из той же папки scripts/. Ещё две команды (запуск из корня проекта):

  python3 frame_versions.py latest <файл>         - самая новая версия по заголовкам release notes
  python3 frame_versions.py offline [<путь> ...]  - версия без MCP: исходники фрейма (теги git), потом
      проект-пример (версия фрейма в его сборке). Путей нет - ищет git-клоны фрейма на диске
      (~, /home, /opt, /work, /data, глубина 6; ~/.m2, jar и распаковка не используются).
  Код выхода: 0 - версия найдена, 1 - нет, 2 - неверный запуск.

Объявление - строка файла, где версия записана буквально: свойство (<pvat.version>3.4.1</pvat.version>,
pvatVersion=3.4.1, pvat = "3.4.1" в libs.versions.toml) или версия прямо в зависимости,
parent, плагине (<version>3.4.1</version>, "ru.sber.pvat:core:3.4.1"). Версия-ссылка
(${pvat.version}, $pvatVersion, version.ref) разворачивается до строки, где стоит число.
Python 3.8+, только стандартная библиотека.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

FRAME_MARKERS = ["pvat", "pv-at", "platform-v-at", "perfeccionista", "sbt-at", "ru.sber.qa"]
BUILD_NAMES = {"pom.xml", "build.gradle", "build.gradle.kts", "gradle.properties", "libs.versions.toml", "settings.gradle", "settings.gradle.kts"}
SKIP_DIRS = {".git", ".gigacode", ".idea", ".gradle", "target", "build", "out", "node_modules"}
VERSION = re.compile(r"^[0-9]+(\.[0-9A-Za-z\-]+)*$")


def has_marker(text):
    low = text.lower()
    return any(marker in low for marker in FRAME_MARKERS)


def walk(root):
    root = Path(root)
    stack = [root]
    while stack:
        folder = stack.pop()
        try:
            entries = sorted(folder.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name not in SKIP_DIRS:
                    stack.append(entry)
            elif entry.is_file():
                yield entry


def build_files(root):
    return sorted((f for f in walk(root) if f.name in BUILD_NAMES), key=str)


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def rel(root, path):
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def maven_properties(files):
    """Свойства <имя>значение</имя> из блоков <properties> всех pom.xml: имя -> (файл, строка, значение)."""
    props = {}
    for f in files:
        if f.name != "pom.xml":
            continue
        text = read(f)
        for block in re.finditer(r"<properties>(.*?)</properties>", text, re.S):
            for prop in re.finditer(r"<([\w.\-]+)>\s*([^<\s]+)\s*</\1>", block.group(1)):
                offset = block.start(1) + prop.start()
                props.setdefault(prop.group(1), (f, line_of(text, offset), prop.group(2)))
    return props


def gradle_properties(files):
    props = {}
    for f in files:
        text = read(f)
        if f.name == "gradle.properties":
            for number, line in enumerate(text.splitlines(), 1):
                kv = re.match(r"\s*([\w.\-]+)\s*[=:]\s*([^\s#]+)\s*$", line)
                if kv:
                    props.setdefault(kv.group(1), (f, number, kv.group(2)))
        elif f.name.startswith("build.gradle"):
            for m in re.finditer(r"(?:set\(\s*|ext\.|val\s+|def\s+)?['\"]?([\w.\-]+)['\"]?\s*(?:=|,)\s*['\"]([0-9][\w.\-]*)['\"]", text):
                props.setdefault(m.group(1), (f, line_of(text, m.start()), m.group(2)))
    return props


def toml_versions(files):
    versions = {}
    for f in files:
        if f.name != "libs.versions.toml":
            continue
        section = ""
        for number, line in enumerate(read(f).splitlines(), 1):
            head = re.match(r"\s*\[([\w\-]+)\]", line)
            if head:
                section = head.group(1)
                continue
            kv = re.match(r"\s*([\w.\-]+)\s*=\s*['\"]([^'\"]+)['\"]", line)
            if kv and section == "versions":
                versions.setdefault(kv.group(1), (f, number, kv.group(2)))
    return versions


def declarations(root):
    """Список объявлений версии фрейма: file, line, kind, name, value, via."""
    files = build_files(root)
    found = {}

    def add(f, number, kind, name, value, via):
        if not VERSION.match(value):
            return
        key = (rel(root, f), number)
        if key not in found:
            found[key] = {"file": key[0], "line": number, "kind": kind, "name": name, "value": value, "via": via}

    mprops, gprops, tversions = maven_properties(files), gradle_properties(files), toml_versions(files)
    for f in files:
        text = read(f)
        if f.name == "pom.xml":
            for block in re.finditer(r"<(dependency|parent|plugin)>(.*?)</\1>", text, re.S):
                body = block.group(2)
                group = re.search(r"<groupId>\s*([^<\s]+)\s*</groupId>", body)
                artifact = re.search(r"<artifactId>\s*([^<\s]+)\s*</artifactId>", body)
                version = re.search(r"<version>\s*([^<\s]+)\s*</version>", body)
                coords = (group.group(1) if group else "") + ":" + (artifact.group(1) if artifact else "")
                if not version or not has_marker(coords):
                    continue
                ref = re.fullmatch(r"\$\{([\w.\-]+)\}", version.group(1))
                if ref:
                    prop = mprops.get(ref.group(1))
                    if prop:
                        add(prop[0], prop[1], "свойство", ref.group(1), prop[2], coords)
                else:
                    add(f, line_of(text, block.start(2) + version.start()), block.group(1), coords, version.group(1), coords)
            for name, (pf, number, value) in mprops.items():
                if pf == f and has_marker(name) and "version" in name.lower():
                    add(pf, number, "свойство", name, value, name)
        elif f.name.startswith("build.gradle"):
            for m in re.finditer(r"['\"]([\w.\-]+):([\w.\-]+):([^'\"]+)['\"]", text):
                coords = m.group(1) + ":" + m.group(2)
                if not has_marker(coords):
                    continue
                value = m.group(3)
                ref = re.fullmatch(r"\$\{?([\w.\-]+)\}?", value)
                if ref:
                    prop = gprops.get(ref.group(1)) or gprops.get(ref.group(1).replace("project.", ""))
                    if prop:
                        add(prop[0], prop[1], "свойство", ref.group(1), prop[2], coords)
                else:
                    add(f, line_of(text, m.start()), "артефакт", coords, value, coords)
        elif f.name == "libs.versions.toml":
            for number, line in enumerate(text.splitlines(), 1):
                lib = re.search(r"(?:module\s*=\s*['\"]|group\s*=\s*['\"]|['\"])([\w.\-]+:[\w.\-]+)", line)
                if not lib or not has_marker(lib.group(1) + line):
                    continue
                ref = re.search(r"version\.ref\s*=\s*['\"]([\w.\-]+)['\"]", line)
                literal = re.search(r"version\s*=\s*['\"]([0-9][^'\"]*)['\"]|['\"][\w.\-]+:[\w.\-]+:([0-9][^'\"]*)['\"]", line)
                if ref and ref.group(1) in tversions:
                    tf, tn, tv = tversions[ref.group(1)]
                    add(tf, tn, "свойство", ref.group(1), tv, lib.group(1))
                elif literal:
                    add(f, number, "артефакт", lib.group(1), literal.group(1) or literal.group(2), lib.group(1))
            for name, (tf, number, value) in tversions.items():
                if tf == f and has_marker(name):
                    add(tf, number, "свойство", name, value, name)
        elif f.name == "gradle.properties":
            for name, (pf, number, value) in gprops.items():
                if pf == f and has_marker(name):
                    add(pf, number, "свойство", name, value, name)
    return sorted(found.values(), key=lambda d: (d["file"], d["line"]))


# дата 20.10.2025 / 20.1.25 - не версия
DATE = re.compile(r"(?<![\w.])[0-9]{1,2}\.[0-9]{1,2}\.(?:[0-9]{4}|[0-9]{2})(?![\w.])")
# строка-заголовок релиза: markdown-заголовок, жирный текст или слово «версия / version / релиз / release»
HEADING = re.compile(r"^\s*(#{1,6}\s|[-*]?\s*\*\*|(версия|version|релиз|release)\b)", re.I)


def newest(text, allow_snapshot=False):
    """Номера версий в тексте release notes -> (самая новая стабильная или предварительная, все по убыванию).
    Даты (20.10.2025) не версии. Есть версии в строках-заголовках релизов -> берутся только они: номера из текста
    описаний (версии библиотек, Java, стендов) самой новой версией фрейма не становятся."""
    text = DATE.sub(" ", text or "")
    heads = "\n".join(line for line in text.split("\n") if HEADING.match(line))
    if re.search(r"[0-9]+\.[0-9]+", heads):
        text = heads
    found = []
    for m in re.finditer(r"(?<![\w.])v?([0-9]+\.[0-9]+(?:\.[0-9]+){0,2}(?:-[0-9A-Za-z.]+)?)(?![\w.])", text):
        value = m.group(1)
        if "SNAPSHOT" in value.upper() and not allow_snapshot:
            continue
        if value not in found:
            found.append(value)
    ordered = sorted(found, key=version_key, reverse=True)
    stable = [v for v in ordered if "-" not in v]
    return (stable[0] if stable else (ordered[0] if ordered else None)), ordered


def version_key(value):
    """Ключ сравнения версий: 3.10.0 > 3.9.2; 3.5.0 > 3.5.0-RC1 > 3.5.0-SNAPSHOT."""
    main, _, suffix = value.partition("-")
    numbers = tuple(int(p) if p.isdigit() else 0 for p in re.split(r"[.]", main))
    numbers = numbers + (0,) * (6 - len(numbers))
    if not suffix:
        rank = 3
    elif suffix.upper().startswith("RC"):
        rank = 2
    elif "SNAPSHOT" in suffix.upper():
        rank = 0
    else:
        rank = 1
    return numbers, rank, suffix


# ---------- версия без MCP ----------

MODULE_DIRS = {"rest", "kafka", "database", "websocket", "grpc", "core", "environment", "environment-junit5", "allure2"}
SOURCE_NAMES = re.compile(r"platform-v-at|pvat|perfeccionista", re.I)


def find_clones():
    """git-клоны фрейма и проектов-примеров на диске - те же правила, что в migration-map, Этап 1, п.6."""
    default = (os.path.expanduser("~"), "/home", "/opt", "/work", "/data")
    # PVATF_SEARCH_ROOTS - свои каталоги поиска через «:» (например, где лежат клоны в контуре)
    custom = [r for r in os.environ.get("PVATF_SEARCH_ROOTS", "").split(":") if r]
    roots = [r for r in (custom or default) if os.path.isdir(r)]
    command = ["find"] + roots + ["-maxdepth", "6", "-type", "d", "-name", ".git", "-not", "-path", "*/.m2/*",
                                  "-not", "-path", "*/node_modules/*"]
    try:
        out = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    found = []
    for line in out.decode("utf-8", "replace").splitlines():
        folder = line[:-len("/.git")] if line.endswith("/.git") else line
        if SOURCE_NAMES.search(folder) and folder not in found:
            found.append(folder)
    return sorted(found)[:20]


def kind_of(path):
    """исходники фрейма (подкаталоги-модули со своим src/main/java), проект-пример (подключает фрейм) или None."""
    path = Path(path)
    modules = [d for d in path.iterdir() if d.is_dir() and d.name in MODULE_DIRS and (d / "src" / "main" / "java").is_dir()] \
        if path.is_dir() else []
    if modules:
        return "исходники фрейма"
    if path.is_dir() and declarations(path):
        return "проект-пример"
    return None


def source_version(path):
    """Версия исходников фрейма: самый новый тег git вида v<версия>, иначе <version> корневого pom без SNAPSHOT."""
    try:
        out = subprocess.run(["git", "-C", str(path), "tag", "--list"], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=60).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    tags = [t.strip().lstrip("vV") for t in out.splitlines()]
    tags = [t for t in tags if VERSION.match(t) and "." in t and "SNAPSHOT" not in t.upper()]
    if tags:
        return max(tags, key=version_key), "тег git"
    pom = read(Path(path) / "pom.xml")
    head = re.sub(r"<(parent|dependencies|dependencyManagement|build|profiles)>.*?</\1>", "", pom, flags=re.S)
    m = re.search(r"<version>\s*([^<\s]+)\s*</version>", head)
    if m and VERSION.match(m.group(1)) and "SNAPSHOT" not in m.group(1).upper():
        return m.group(1), "pom.xml"
    return None, "-"


def offline(paths):
    """[(вид, путь, версия, откуда)] по найденным источникам; первым - лучший."""
    rows = []
    given = {str(Path(p).resolve()) for p in paths}
    here = Path.cwd().resolve()
    # пути от человека или из паспорта + найденные git-клоны: исходники фрейма ищутся всегда
    for path in dict.fromkeys(list(paths) + find_clones()):
        if Path(path).resolve() == here:
            continue  # сам проект - не источник своей же версии
        kind = kind_of(path)
        if kind == "исходники фрейма":
            version, where = source_version(path)
            rows.append((kind, str(path), version, where))
        elif kind == "проект-пример":
            decl = [d for d in declarations(path) if "SNAPSHOT" not in d["value"].upper()]
            frame = [d for d in decl if "perfeccionista" not in d["name"].lower()] or decl
            if frame:
                best = max(frame, key=lambda d: version_key(d["value"]))
                rows.append((kind, str(path), best["value"], best["file"] + ":" + str(best["line"])))
                for d in decl:
                    if "perfeccionista" in d["name"].lower():
                        rows.append(("perfeccionista", str(path), d["value"], d["file"] + ":" + str(d["line"])))
    order = {"исходники фрейма": 0, "проект-пример": 1, "perfeccionista": 2}
    # исходники фрейма - всегда первыми; среди проектов-примеров названный человеком важнее найденного
    rows.sort(key=lambda r: (order[r[0]], str(Path(r[1]).resolve()) not in given, r[2] is None,
                             tuple(-n for n in version_key(r[2] or "0")[0])))
    return rows


def main(args):
    if len(args) == 2 and args[0] == "latest":
        latest, _ = newest(read(Path(args[1])))
        print("САМАЯ НОВАЯ: " + (latest or "-"))
        return 0 if latest else 1
    if args and args[0] == "offline":
        rows = offline(args[1:])
        for kind, path, version, where in rows:
            if kind != "perfeccionista":
                print("ИСТОЧНИК: %s · %s · версия %s (%s)" % (kind, path, version or "не найдена", where))
        best = next((r for r in rows if r[2] and r[0] != "perfeccionista"), None)
        perf = next((r for r in rows if r[0] == "perfeccionista"), None)
        print("ВЕРСИЯ БЕЗ MCP: " + ("%s · %s %s" % (best[2], best[0], best[1]) if best else "не найдена"))
        print("PERFECCIONISTA БЕЗ MCP: " + ("%s · проект-пример %s (%s)" % (perf[2], perf[1], perf[3]) if perf else "не найдена"))
        return 0 if best else 1
    print("Использование: frame_versions.py latest <файл> | offline [<путь> ...]")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
