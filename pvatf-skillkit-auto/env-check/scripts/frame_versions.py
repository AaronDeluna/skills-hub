"""Где в файлах сборки объявлена версия фрейма PVATF. Общий модуль набора: источник -
shared/scripts/frame_versions.py, копии в скиллах env-check и env-update раскладывает
scripts/sync_shared.py. Сам не запускается - его импортируют env_check.py и env_update.py.

Объявление - строка файла, где версия записана буквально: свойство (<pvat.version>3.4.1</pvat.version>,
pvatVersion=3.4.1, pvat = "3.4.1" в libs.versions.toml) или версия прямо в зависимости,
parent, плагине (<version>3.4.1</version>, "ru.sber.pvat:core:3.4.1"). Версия-ссылка
(${pvat.version}, $pvatVersion, version.ref) разворачивается до строки, где стоит число.
Python 3.8+, только стандартная библиотека.
"""
import re
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
