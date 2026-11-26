#!/usr/bin/env python3
"""
Проверка управления зависимостями проекта автотестов (скилл de-pvatf-dependency-review). Запуск из корня проекта:

  python3 <каталог скилла>/scripts/deps.py scan
      - система сборки, модули, тип проекта, проверки правил D-* по файлам сборки;
        пишет .gigacode/data/dependency/DEPS.json и FINDINGS.md (deps_status: scanned)
  python3 <каталог скилла>/scripts/deps.py tree [--timeout 540] [--no-build]
      - дерево зависимостей сборщиком (Maven: dependency:tree и dependency:analyze, Gradle: dependencies),
        транзитивные конфликты -> строки D-10 и D-22 (deps_status: tree-done)
  python3 <каталог скилла>/scripts/deps.py next
      - следующая строка со статусом TODO или CANDIDATE и что проверить; «ВСЁ ПРОВЕРЕНО» - таких нет
  python3 <каталог скилла>/scripts/deps.py mark <N-n> <PASS|VIOLATION|N/A|NEEDS-HUMAN> --note "<текст>" [--where <файл:строка>] [--level <уровень>]
  python3 <каталог скилла>/scripts/deps.py add <D-id> --where <файл:строка> --note "<текст>" [--level <уровень>]
      - ещё одно нарушение того же правила (статус VIOLATION)
  python3 <каталог скилла>/scripts/deps.py report --summary "<2-3 предложения вывода>"
      - DEPENDENCY-ANALYSIS.md по шаблону (deps_status: reported); строки TODO или CANDIDATE остались - код 1

Файлы проекта скрипт не меняет. Код выхода: 0 - готово, 1 - условие не выполнено (смотри вывод),
2 - неверный запуск. Python 3.8+, только стандартная библиотека.
"""
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frame_versions  # noqa: E402

import pvatf_paths as pp  # noqa: E402 - копия shared/scripts
DATA = pp.kind_dir("deps-review", "dependency")
STATE = DATA / "DEPS.json"
FINDINGS = DATA / "FINDINGS.md"
REPORT = DATA / "DEPENDENCY-ANALYSIS.md"
TREE = DATA / "tree.txt"
SKIP = frame_versions.SKIP_DIRS
STATUSES = ("PASS", "VIOLATION", "N/A", "NEEDS-HUMAN")
LEVEL_ORDER = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}

# id -> (уровень, кто проверяет, заголовок, чем грозит, как исправить)
RULES = {
    "D-01": ("CRITICAL", "script", "Динамические версии",
             "сборка в разные дни берёт разные версии: вчера зелёная, сегодня красная без единой правки",
             "заменить диапазон, LATEST, RELEASE или «+» на точную версию"),
    "D-02": ("WARNING", "script", "SNAPSHOT-зависимости",
             "SNAPSHOT меняется без смены номера: прогон нельзя повторить, а артефакт может исчезнуть из репозитория",
             "перейти на выпущенную версию; SNAPSHOT оставить только для модулей самого проекта"),
    "D-03": ("CRITICAL", "script", "Зависимость из локального файла",
             "jar с диска разработчика не попадёт на CI и к коллегам, его версия нигде не видна",
             "опубликовать артефакт в репозиторий и подключить по координатам"),
    "D-04": ("CRITICAL", "script", "Одна библиотека в разных версиях в разных модулях",
             "модули собираются и проходят тесты с разными версиями, а вместе в одном прогоне падают в рантайме",
             "объявить версию один раз: dependencyManagement корня, version catalog или platform"),
    "D-05": ("WARNING", "script", "Версии зашиты в объявлениях зависимостей",
             "нет единого источника версий: при обновлении часть мест забудут, версии разъедутся",
             "перенести версии в properties/dependencyManagement (Maven) или libs.versions.toml (Gradle)"),
    "D-06": ("WARNING", "script", "Семейство библиотек без BOM",
             "части одного семейства подбираются вручную и расходятся по версиям - типичная причина NoSuchMethodError",
             "импортировать BOM семейства (scope import / platform) и убрать версии у его артефактов"),
    "D-07": ("INFO", "script", "Зависимость объявлена дважды",
             "работает последняя запись, а читающий файл видит обе и не знает, какая действует",
             "оставить одно объявление"),
    "D-08": ("INFO", "script", "Репозитории объявлены в файле сборки модуля",
             "адреса репозиториев расходятся между модулями и машинами, сборка зависит от того, кто её запускает",
             "держать репозитории в settings.xml (Maven) или в settings.gradle (Gradle)"),
    "D-09": ("CRITICAL", "script", "Цикл между модулями",
             "модули нельзя собрать по отдельности, любое изменение тянет пересборку всего круга",
             "вынести общий код в отдельный модуль, на который ссылаются оба"),
    "D-10": ("WARNING", "script", "Транзитивный конфликт версий",
             "библиотеку подтянула другая зависимость и подменила нужную версию: в файлах всё верно, а падает в рантайме",
             "закрепить версию в dependencyManagement / constraints или подключить BOM семейства"),
    "D-11": ("WARNING", "script", "В проекте две системы сборки",
             "одна из систем устарела и расходится с реальной сборкой, а читают её как настоящую",
             "оставить одну систему сборки, вторую удалить"),
    "D-12": ("INFO", "script", "Нет автоматической проверки сходимости версий",
             "расхождение версий заметят только по падению в рантайме",
             "maven-enforcer-plugin с правилом dependencyConvergence (Maven) или failOnVersionConflict (Gradle)"),
    "D-P1": ("CRITICAL", "script", "Версии фрейма PVATF расходятся",
             "модули фрейма разных версий несовместимы между собой: ошибки компиляции и рантайма после любого обновления",
             "одна версия фрейма в одном месте; выровнять - «/opsx-de-pvatf обнови окружение»"),
    "D-P2": ("WARNING", "script", "Артефакты фрейма с версией в каждом объявлении",
             "при обновлении фрейма версию придётся менять в нескольких местах и легко пропустить одно",
             "подключать фрейм так, как велит документация фрейма (BOM, parent или общее свойство) - ответ pvatf-docs в находке"),
    "D-20": ("WARNING", "model", "Scope зависимости",
             "тестовая библиотека в боевом scope протекает потребителям, боевая в test - не видна коду src/main",
             "scope по месту использования: код src/main - compile/implementation, только src/test - test/testImplementation"),
    "D-21": ("INFO", "model", "Exclusion без обоснования",
             "исключение молча убирает класс, который может понадобиться; через год никто не помнит, зачем оно",
             "оставить исключение с комментарием-причиной или убрать"),
    "D-22": ("INFO", "model", "Необъявленные транзитивные и мёртвые зависимости",
             "код опирается на библиотеку, которую привёз сосед: сосед обновится - компиляция сломается",
             "объявить используемое явно, неиспользуемое удалить"),
    "D-23": ("WARNING", "model", "Две библиотеки делают одно и то же",
             "два JSON-парсера или два HTTP-клиента - вдвое больше конфликтов и разный код для одной задачи",
             "выбрать одну библиотеку и перевести на неё код"),
    "D-24": ("WARNING", "model", "Направление зависимостей между модулями",
             "общий модуль зависит от модуля тестов: общий код нельзя использовать без тестов",
             "зависимости идут от тестов к общим модулям, не наоборот"),
}

DUP_FAMILIES = [
    ("JSON", {"jackson-databind", "gson", "json", "json-simple", "fastjson", "fastjson2", "moshi"}),
    ("HTTP-клиент", {"okhttp", "httpclient", "httpclient5", "async-http-client", "unirest-java"}),
    ("тест-раннер", {"junit", "junit-jupiter", "junit-jupiter-api", "testng"}),
    ("реализация логов", {"logback-classic", "log4j-core", "slf4j-simple", "log4j-slf4j-impl", "log4j-slf4j2-impl", "slf4j-log4j12"}),
]
TEST_LIBS = {"junit": "org.junit", "junit-jupiter": "org.junit.jupiter", "junit-jupiter-api": "org.junit.jupiter",
             "testng": "org.testng", "assertj-core": "org.assertj", "mockito-core": "org.mockito",
             "hamcrest": "org.hamcrest", "hamcrest-all": "org.hamcrest", "rest-assured": "io.restassured"}


def mask(text, pattern):
    """Блоки по шаблону заменяются пробелами (переводы строк остаются) - смещения строк не меняются."""
    return re.sub(pattern, lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)


def tag(body, name):
    m = re.search(r"<" + name + r">\s*([^<]*?)\s*</" + name + ">", body)
    return m.group(1) if m else ""


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


# ---------- Maven ----------

def parse_pom(path, root):
    raw = frame_versions.read(path)
    text = mask(raw, r"<!--.*?-->")
    head = mask(mask(mask(mask(text, r"<parent>.*?</parent>"), r"<dependencies>.*?</dependencies>"),
                     r"<dependencyManagement>.*?</dependencyManagement>"), r"<build>.*?</build>")
    head = mask(mask(head, r"<profiles>.*?</profiles>"), r"<properties>.*?</properties>")
    parent = re.search(r"<parent>(.*?)</parent>", text, re.S)
    pom = {"file": frame_versions.rel(root, path), "dir": str(Path(path).parent), "text": text,
           "group": tag(head, "groupId") or (tag(parent.group(1), "groupId") if parent else ""),
           "artifact": tag(head, "artifactId"),
           "version": tag(head, "version") or (tag(parent.group(1), "version") if parent else ""),
           "parent": None, "props": {}, "modules": re.findall(r"<module>\s*([^<\s]+)\s*</module>", text),
           "managed": [], "deps": [], "repos": [], "enforcer": False}
    if parent:
        body = parent.group(1)
        pom["parent"] = {"group": tag(body, "groupId"), "artifact": tag(body, "artifactId"),
                         "version": tag(body, "version"), "path": tag(body, "relativePath") or "../pom.xml"}
    for block in re.finditer(r"<properties>(.*?)</properties>", text, re.S):
        for prop in re.finditer(r"<([\w.\-]+)>\s*([^<]*?)\s*</\1>", block.group(1)):
            pom["props"].setdefault(prop.group(1), prop.group(2))
    mgmt = re.search(r"<dependencyManagement>(.*?)</dependencyManagement>", text, re.S)
    if mgmt:
        for d in deps_in(text, mgmt.start(1), mgmt.group(1)):
            pom["managed"].append(d)
    body = mask(mask(text, r"<dependencyManagement>.*?</dependencyManagement>"), r"<plugins>.*?</plugins>")
    body = mask(body, r"<pluginManagement>.*?</pluginManagement>")
    for d in deps_in(text, 0, body):
        pom["deps"].append(d)
    for m in re.finditer(r"<repositories>", body):
        pom["repos"].append(line_of(text, m.start()))
    pom["enforcer"] = "maven-enforcer-plugin" in text and "dependencyConvergence" in text
    return pom


def deps_in(text, base, region):
    found = []
    for block in re.finditer(r"<dependency>(.*?)</dependency>", region, re.S):
        body = block.group(1)
        found.append({"group": tag(body, "groupId"), "artifact": tag(body, "artifactId"),
                      "version": tag(body, "version"), "scope": tag(body, "scope") or "compile",
                      "type": tag(body, "type"), "classifier": tag(body, "classifier"),
                      "system_path": "<systemPath>" in body,
                      "exclusions": re.findall(r"<exclusion>.*?<artifactId>\s*([^<\s]+)\s*</artifactId>.*?</exclusion>", body, re.S),
                      "line": line_of(text, base + block.start())})
    return found


def maven_project(root):
    poms = {}
    top = Path(root) / "pom.xml"
    queue = [top] if top.is_file() else []
    while queue:
        path = queue.pop(0).resolve()
        if str(path) in poms or not path.is_file():
            continue
        pom = parse_pom(path, root)
        poms[str(path)] = pom
        for module in pom["modules"]:
            child = path.parent / module
            queue.append(child / "pom.xml" if child.is_dir() else child)
    others = [f for f in frame_versions.build_files(root) if f.name == "pom.xml" and str(f.resolve()) not in poms]
    for path in others:
        poms[str(path.resolve())] = parse_pom(path.resolve(), root)
    return list(poms.values())


def ancestors(pom, by_path):
    chain, seen = [], set()
    while pom and pom["parent"] and pom["file"] not in seen:
        seen.add(pom["file"])
        candidate = (Path(pom["dir"]) / pom["parent"]["path"])
        candidate = candidate / "pom.xml" if candidate.is_dir() else candidate
        pom = by_path.get(str(candidate.resolve()))
        if pom:
            chain.append(pom)
    return chain


def resolve(value, pom, chain, depth=0):
    if depth > 5 or not value:
        return value
    def one(m):
        name = m.group(1)
        if name in ("project.version", "version", "pom.version"):
            return pom["version"]
        for holder in [pom] + chain:
            if name in holder["props"]:
                return holder["props"][name]
        return m.group(0)
    out = re.sub(r"\$\{([\w.\-]+)\}", one, value)
    return resolve(out, pom, chain, depth + 1) if out != value and "${" in out else out


# ---------- Gradle ----------

GRADLE_DEP = re.compile(r"\b(implementation|api|compileOnly|runtimeOnly|testImplementation|testCompileOnly|testRuntimeOnly|"
                        r"annotationProcessor|compile|testCompile|kapt)\s*\(?\s*(platform\(|enforcedPlatform\()?\s*"
                        r"['\"]([\w.\-]+):([\w.\-]+)(?::([^'\"@:]+))?(?::([\w.\-]+))?['\"]")
GRADLE_PROJECT = re.compile(r"project\(\s*(?:path\s*[:=]\s*)?['\"]:?([\w.\-:]+)['\"]")


def gradle_project(root):
    root = Path(root)
    settings = next((root / n for n in ("settings.gradle.kts", "settings.gradle") if (root / n).is_file()), None)
    settings_text = mask(frame_versions.read(settings), r"/\*.*?\*/") if settings else ""
    modules = []
    for inc in re.finditer(r"include\s*\(?([^\n)]*)", settings_text):
        modules += [m.lstrip(":").replace(":", "/") for m in re.findall(r"['\"]([^'\"]+)['\"]", inc.group(1))]
    files = [f for f in frame_versions.build_files(root) if f.name.startswith("build.gradle")]
    props = frame_versions.gradle_properties(frame_versions.build_files(root))
    builds = []
    for f in files:
        text = mask(frame_versions.read(f), r"/\*.*?\*/")
        text = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), text)
        name = frame_versions.rel(root, f.parent) if f.parent.resolve() != root.resolve() else ""
        b = {"file": frame_versions.rel(root, f), "module": name or "(корень)", "text": text, "deps": [], "boms": [],
             "projects": [m.group(1).replace(":", "/") for m in GRADLE_PROJECT.finditer(text)],
             "files": [line_of(text, m.start()) for m in re.finditer(r"\b(files|fileTree)\s*\(", text)],
             "repos": [line_of(text, m.start()) for m in re.finditer(r"\brepositories\s*\{", text)],
             "catalog_refs": len(re.findall(r"\blibs\.[\w.]+", text)), "enforcer": "failOnVersionConflict" in text}
        for m in GRADLE_DEP.finditer(text):
            version = m.group(5) or ""
            ref = re.fullmatch(r"\$\{?([\w.\-]+)\}?", version)
            if ref and ref.group(1) in props:
                version = props[ref.group(1)][2]
            entry = {"group": m.group(3), "artifact": m.group(4), "version": version, "raw": m.group(5) or "",
                     "scope": m.group(1), "line": line_of(text, m.start()), "bom": bool(m.group(2)), "exclusions": []}
            (b["boms"] if entry["bom"] else b["deps"]).append(entry)
        builds.append(b)
    catalog = root / "gradle" / "libs.versions.toml"
    return {"modules": modules, "builds": builds, "catalog": catalog.is_file(),
            "central_repos": "dependencyResolutionManagement" in settings_text}


# ---------- проверки ----------

def dynamic(version):
    v = version.strip()
    return bool(v) and (v[0] in "[(" or v in ("LATEST", "RELEASE") or v.endswith("+") or v.startswith("latest."))


class Findings:
    def __init__(self):
        self.rows = []

    def add(self, rid, status, where, note, level=None):
        self.rows.append({"n": "N-%d" % (len(self.rows) + 1), "id": rid, "level": level or RULES[rid][0],
                          "status": status, "where": where or "-", "note": note.replace("|", "/").replace("\n", " ")})

    def has(self, rid):
        return any(r["id"] == rid for r in self.rows)


def check_maven(root, f, info):
    poms = maven_project(root)
    by_path = {str((Path(p["dir"]) / Path(p["file"]).name).resolve()): p for p in poms}
    reactor = {p["artifact"] for p in poms}
    multi = len(poms) > 1
    info["modules"] = [p["file"] for p in poms]
    versions = {}
    edges = {p["artifact"]: set() for p in poms}
    for pom in poms:
        chain = ancestors(pom, by_path)
        managed = {(d["group"], d["artifact"]) for holder in [pom] + chain for d in holder["managed"]}
        boms = [d for holder in [pom] + chain for d in holder["managed"] if d["scope"] == "import"]
        literals, seen, families = [], {}, {}
        for d in pom["managed"] + pom["deps"]:
            raw = d["version"]
            version = resolve(raw, pom, chain)
            where = pom["file"] + ":" + str(d["line"])
            coords = d["group"] + ":" + d["artifact"]
            if dynamic(version):
                f.add("D-01", "VIOLATION", where, coords + " версия «" + raw + "»")
            if version.upper().endswith("SNAPSHOT") and d["artifact"] not in reactor:
                f.add("D-02", "VIOLATION", where, coords + ":" + version)
            if d["scope"] == "system" or d["system_path"]:
                f.add("D-03", "VIOLATION", where, coords + " scope system")
            if version and d["artifact"] not in reactor and "${" not in version:
                versions.setdefault(coords, {}).setdefault(version, []).append(where)
        for d in pom["deps"]:
            coords = d["group"] + ":" + d["artifact"]
            where = pom["file"] + ":" + str(d["line"])
            if d["artifact"] in reactor:
                edges[pom["artifact"]].add(d["artifact"])
                continue
            key = coords + ":" + d["classifier"] + ":" + d["type"]
            if key in seen:
                f.add("D-07", "VIOLATION", where, coords + " - ещё раз в строке " + str(seen[key]))
            seen[key] = d["line"]
            if d["version"] and "${" not in d["version"] and not frame_versions.has_marker(coords):
                literals.append(d["line"])
            if d["version"] and (d["group"], d["artifact"]) not in managed and not frame_versions.has_marker(coords):
                families.setdefault(d["group"], {})[d["artifact"]] = resolve(d["version"], pom, chain)
            for ex in d["exclusions"]:
                info["exclusions"].append(where + " " + coords + " без " + ex)
            info["libs"].append({"where": where, "coords": coords, "artifact": d["artifact"], "scope": d["scope"],
                                 "dir": pom["dir"]})
        if literals:
            level = "WARNING" if multi and pom["parent"] else "INFO"
            f.add("D-05", "VIOLATION", pom["file"] + ":" + str(literals[0]),
                  "литералов версий в <dependencies>: %d (строки %s)" % (len(literals), ", ".join(map(str, literals[:8]))), level)
        for group, arts in families.items():
            covered = any(b["group"].split(".")[:2] == group.split(".")[:2] for b in boms)
            if len(arts) >= 3 and not covered:
                differ = len(set(arts.values())) > 1
                f.add("D-06", "VIOLATION", pom["file"], group + ": " + ", ".join(a + ":" + v for a, v in sorted(arts.items())),
                      "WARNING" if differ else "INFO")
        for number in pom["repos"]:
            f.add("D-08", "VIOLATION", pom["file"] + ":" + str(number), "<repositories> в pom.xml")
    for coords, by_version in sorted(versions.items()):
        if len(by_version) > 1:
            f.add("D-04", "VIOLATION", next(iter(by_version.values()))[0],
                  coords + ": " + "; ".join(v + " (" + ", ".join(w[:3]) + ")" for v, w in sorted(by_version.items())))
    if multi and not any(p["enforcer"] for p in poms):
        f.add("D-12", "VIOLATION", poms[0]["file"], "нет maven-enforcer-plugin с dependencyConvergence")
    info["module_edges"] = {k: sorted(v) for k, v in edges.items()}
    return multi


def check_gradle(root, f, info):
    g = gradle_project(root)
    multi = len(g["modules"]) > 0
    info["modules"] = [b["file"] for b in g["builds"]]
    versions, edges = {}, {}
    for b in g["builds"]:
        edges[b["module"]] = set(b["projects"])
        seen, literals, families = {}, [], {}
        boms = b["boms"] + [x for other in g["builds"] for x in other["boms"] if other["module"] == "(корень)"]
        for d in b["deps"] + b["boms"]:
            coords = d["group"] + ":" + d["artifact"]
            where = b["file"] + ":" + str(d["line"])
            if dynamic(d["version"]):
                f.add("D-01", "VIOLATION", where, coords + " версия «" + d["raw"] + "»")
            if d["version"].upper().endswith("SNAPSHOT"):
                f.add("D-02", "VIOLATION", where, coords + ":" + d["version"])
            if d["version"] and not d["bom"]:
                versions.setdefault(coords, {}).setdefault(d["version"], []).append(where)
        for d in b["deps"]:
            coords = d["group"] + ":" + d["artifact"]
            where = b["file"] + ":" + str(d["line"])
            key = d["scope"] + ":" + coords
            if key in seen:
                f.add("D-07", "VIOLATION", where, coords + " - ещё раз в строке " + str(seen[key]))
            seen[key] = d["line"]
            if d["raw"] and not d["raw"].startswith("$") and not frame_versions.has_marker(coords):
                literals.append(d["line"])
            if d["version"] and not frame_versions.has_marker(coords):
                families.setdefault(d["group"], {})[d["artifact"]] = d["version"]
            info["libs"].append({"where": where, "coords": coords, "artifact": d["artifact"],
                                 "scope": d["scope"], "dir": str((Path(root) / b["file"]).parent)})
        for number in b["files"]:
            f.add("D-03", "VIOLATION", b["file"] + ":" + str(number), "зависимость files()/fileTree()")
        if literals and (g["catalog"] or multi):
            f.add("D-05", "VIOLATION", b["file"] + ":" + str(literals[0]),
                  "литералов версий: %d (строки %s)%s" % (len(literals), ", ".join(map(str, literals[:8])),
                                                         "; version catalog есть" if g["catalog"] else ""),
                  "WARNING")
        elif literals:
            f.add("D-05", "VIOLATION", b["file"] + ":" + str(literals[0]),
                  "литералов версий: %d (строки %s)" % (len(literals), ", ".join(map(str, literals[:8]))), "INFO")
        for group, arts in families.items():
            covered = any(x["group"].split(".")[:2] == group.split(".")[:2] for x in boms)
            if len(arts) >= 3 and not covered:
                f.add("D-06", "VIOLATION", b["file"], group + ": " + ", ".join(a + ":" + v for a, v in sorted(arts.items())),
                      "WARNING" if len(set(arts.values())) > 1 else "INFO")
        if g["central_repos"] and b["repos"] and b["module"] != "(корень)":
            f.add("D-08", "VIOLATION", b["file"] + ":" + str(b["repos"][0]), "repositories в модуле при dependencyResolutionManagement")
    for coords, by_version in sorted(versions.items()):
        if len(by_version) > 1:
            f.add("D-04", "VIOLATION", next(iter(by_version.values()))[0],
                  coords + ": " + "; ".join(v + " (" + ", ".join(w[:3]) + ")" for v, w in sorted(by_version.items())))
    if multi and not any(b["enforcer"] for b in g["builds"]):
        f.add("D-12", "VIOLATION", "-", "нет failOnVersionConflict")
    info["module_edges"] = {k: sorted(v) for k, v in edges.items()}
    return multi


def cycles(edges):
    found, state = [], {}

    def visit(node, path):
        state[node] = 1
        for nxt in edges.get(node, ()):
            if state.get(nxt) == 1:
                cycle = path[path.index(nxt):] + [nxt] if nxt in path else [node, nxt]
                if sorted(cycle) not in [sorted(c) for c in found]:
                    found.append(cycle)
            elif nxt in edges and not state.get(nxt):
                visit(nxt, path + [nxt])
        state[node] = 2
    for node in sorted(edges):
        if not state.get(node):
            visit(node, [node])
    return found


def imports_in(folder, package):
    main = Path(folder) / "src" / "main"
    if not main.is_dir():
        return False
    for path in main.rglob("*.java"):
        if ("import " + package) in frame_versions.read(path):
            return True
    return False


def is_autotests(root, info):
    """Проект автотестов: в сборке фрейм PVATF или тест-библиотеки, а в src/main нет точки входа приложения."""
    markers = [l for l in info["libs"] if frame_versions.has_marker(l["coords"]) or l["artifact"] in TEST_LIBS]
    for path in Path(root).rglob("*.java"):
        if "src/main" in str(path).replace("\\", "/") and not set(path.parts) & SKIP:
            body = frame_versions.read(path)
            if "@SpringBootApplication" in body or "static void main(" in body:
                return False
    return bool(markers)


def cmd_scan(root):
    systems = []
    if Path("pom.xml").is_file():
        systems.append("Maven")
    if any(Path(n).is_file() for n in ("build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts")):
        systems.append("Gradle")
    if not systems:
        print("НЕТ СБОРКИ: в корне нет pom.xml, build.gradle, settings.gradle - это не Maven- и не Gradle-проект")
        return 1
    f = Findings()
    info = {"libs": [], "exclusions": [], "modules": [], "module_edges": {}}
    multi = False
    if "Gradle" in systems:
        multi = check_gradle(root, f, info) or multi
    if "Maven" in systems:
        multi = check_maven(root, f, info) or multi
    if len(systems) == 2:
        f.add("D-11", "VIOLATION", "pom.xml", "есть и pom.xml, и build.gradle")
    for cycle in cycles(info["module_edges"]):
        f.add("D-09", "VIOLATION", "-", " -> ".join(cycle))
    decl = frame_versions.declarations(root)
    values = sorted({d["value"] for d in decl}, key=frame_versions.version_key)
    if len(values) > 1:
        f.add("D-P1", "VIOLATION", decl[0]["file"] + ":" + str(decl[0]["line"]),
              "версии фрейма: " + "; ".join(v + " (" + ", ".join(d["file"] + ":" + str(d["line"]) for d in decl if d["value"] == v)[:120] + ")" for v in values))
    literal = [d for d in decl if d["kind"] in ("dependency", "артефакт")]
    if len(literal) >= 2:
        f.add("D-P2", "CANDIDATE", literal[0]["file"] + ":" + str(literal[0]["line"]),
              "версия фрейма записана в %d объявлениях: %s; как подключать по документации - вопрос pvatf-docs"
              % (len(literal), ", ".join(d["name"] for d in literal[:5])))
    autotests = is_autotests(root, info)
    # кандидаты для правил модели
    present = {l["artifact"] for l in info["libs"]}
    dup = []
    for name, family in DUP_FAMILIES:
        hit = sorted(present & family)
        if name == "тест-раннер":
            hit = sorted({"junit" if h == "junit" else ("testng" if h == "testng" else "junit5") for h in hit})
        if len(hit) > 1:
            dup.append(name + ": " + ", ".join(hit))
    f.add("D-23", "CANDIDATE" if dup else "PASS", "-", "; ".join(dup) if dup else "пересекающихся по назначению библиотек нет")
    scope = []
    for lib in info["libs"]:
        package = TEST_LIBS.get(lib["artifact"])
        if package and lib["scope"] in ("compile", "implementation", "api", "runtime", "compileOnly"):
            used = imports_in(lib["dir"], package)
            scope.append(lib["coords"] + " в " + lib["scope"] + " (" + lib["where"] + ")"
                         + (" - используется в src/main" if used else " - в src/main не используется"))
    f.add("D-20", "CANDIDATE" if scope else "TODO", "-",
          "; ".join(scope) if scope else "тестовых библиотек вне test-scope скрипт не нашёл; проверь остальные по references/rules.md")
    f.add("D-21", "CANDIDATE" if info["exclusions"] else "PASS", "-",
          "; ".join(info["exclusions"][:12]) if info["exclusions"] else "exclusion-ов нет")
    f.add("D-22", "TODO", "-", "deps.py tree ещё не запускался")
    if multi:
        f.add("D-24", "TODO", "-", "связи модулей: " + "; ".join(k + " -> " + (", ".join(v) or "нет")
                                                          for k, v in info["module_edges"].items()))
    else:
        f.add("D-24", "N/A", "-", "один модуль")
    f.add("D-10", "TODO", "-", "deps.py tree ещё не запускался")
    for rid, rule in RULES.items():
        if rule[1] == "script" and not f.has(rid):
            na = (rid == "D-09" and not multi) or (rid == "D-12" and not multi) or (rid in ("D-P1", "D-P2") and not decl)
            f.add(rid, "N/A" if na else "PASS", "-", "одномодульный проект" if rid in ("D-09", "D-12") and na
                  else ("фрейм в сборке не найден" if na else "нарушений нет"))
    meta = {"deps_status": "scanned", "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "build": " + ".join(systems), "structure": "мультимодуль, модулей: %d" % len(info["modules"]) if multi else "монолит",
            "type": "автотесты" if autotests else "приложение или библиотека", "files": len(info["modules"]),
            "frame": ", ".join(values) or "не найден", "tree": "не запускался", "edges": info["module_edges"]}
    save(meta, f.rows)
    print("СБОРКА: " + meta["build"] + " · СТРУКТУРА: " + meta["structure"] + " · ТИП: " + meta["type"])
    print("ФРЕЙМ: " + meta["frame"])
    summary(f.rows)
    print("ДАЛЬШЕ: deps.py tree")
    return 0


# ---------- состояние ----------

def save(meta, rows):
    DATA.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    out = ["---"] + ["%s: %s" % (k, meta[k]) for k in ("deps_status", "date", "build", "structure", "type", "tree")] + ["---", "",
           "# Находки по зависимостям", "", "| N | Правило | Уровень | Статус | Где | Что |", "|---|---|---|---|---|---|"]
    out += ["| %s | %s | %s | %s | %s | %s |" % (r["n"], r["id"], r["level"], r["status"], r["where"], r["note"]) for r in rows]
    FINDINGS.write_text("\n".join(out) + "\n", encoding="utf-8")


def load():
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        return data["meta"], data["rows"]
    except (OSError, ValueError, KeyError):
        print("НЕТ ДАННЫХ: сначала deps.py scan")
        sys.exit(1)


def summary(rows):
    count = {lvl: sum(1 for r in rows if r["status"] == "VIOLATION" and r["level"] == lvl) for lvl in LEVEL_ORDER}
    left = [r["n"] + " " + r["id"] for r in rows if r["status"] in ("TODO", "CANDIDATE")]
    print("НАРУШЕНИЙ: CRITICAL %d · WARNING %d · INFO %d · NEEDS-HUMAN %d"
          % (count["CRITICAL"], count["WARNING"], count["INFO"], sum(1 for r in rows if r["status"] == "NEEDS-HUMAN")))
    print("ПРОВЕРИТЬ: " + (", ".join(left) if left else "нет"))


# ---------- дерево ----------

def run(argv, timeout):
    try:
        res = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return res.returncode, res.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return None, ""
    except OSError as error:
        return -1, str(error)


def major(v):
    m = re.match(r"(\d+)", v or "")
    return m.group(1) if m else v


def cmd_tree(args):
    meta, rows = load()
    timeout = int(args[args.index("--timeout") + 1]) if "--timeout" in args else 540
    rows = [r for r in rows if r["id"] not in ("D-10", "D-22")]  # строки D-10 и D-22 ставит только tree: повтор не дублирует
    added = []

    def add(rid, status, where, note, level=None):
        added.append({"n": "", "id": rid, "level": level or RULES[rid][0], "status": status, "where": where, "note": note})

    if "--no-build" in args:
        add("D-10", "NEEDS-HUMAN", "-", "сборщик не запускали (--no-build): транзитивные конфликты не проверены; "
            "команда: mvn dependency:tree -Dverbose или ./gradlew dependencies")
        add("D-22", "TODO", "-", "дерева нет: проверь по references/rules.md, раздел D-22, по файлам")
        meta["tree"] = "не построено: --no-build"
    elif "Maven" in meta["build"]:
        mvn = ["./mvnw"] if Path("mvnw").is_file() else ([shutil.which("mvn")] if shutil.which("mvn") else None)
        if not mvn:
            add("D-10", "NEEDS-HUMAN", "-", "mvn не найден: транзитивные конфликты не проверены; команда: mvn dependency:tree -Dverbose")
            add("D-22", "TODO", "-", "дерева нет: проверь по references/rules.md, раздел D-22, по файлам")
            meta["tree"] = "не построено: mvn не найден"
        else:
            started = time.time()
            code, out = run(mvn + ["-B", "dependency:tree", "-Dverbose"], timeout)
            tree_rows(code, out, timeout, add, meta, maven_conflicts)
            left = int(timeout - (time.time() - started))
            code2, out2 = run(mvn + ["-B", "dependency:analyze", "-DignoreNonCompile=true"], left) if code is not None and left >= 30 else (None, "")
            analyze_rows(code2, out2, add)
    else:
        gradle = ["./gradlew"] if Path("gradlew").is_file() else ([shutil.which("gradle")] if shutil.which("gradle") else None)
        if not gradle:
            add("D-10", "NEEDS-HUMAN", "-", "gradle не найден: транзитивные конфликты не проверены; команда: ./gradlew dependencies")
            meta["tree"] = "не построено: gradle не найден"
        else:
            tasks = ["dependencies"] + [":" + m.replace("/", ":") + ":dependencies"
                                        for m in meta.get("edges", {}) if m != "(корень)"]
            code, out = run(gradle + tasks + ["--configuration", "testRuntimeClasspath", "--console=plain"], timeout)
            tree_rows(code, out, timeout, add, meta, gradle_conflicts)
        add("D-22", "TODO", "-", "у Gradle нет dependency:analyze: проверь по references/rules.md, раздел D-22")
    for row in added:
        rows.append(row)
    for i, r in enumerate(rows, 1):
        r["n"] = "N-%d" % i
    meta["deps_status"] = "tree-done"
    save(meta, rows)
    if "таймаут" in meta["tree"]:
        print("ТАЙМАУТ: сборщик не уложился в %d секунд - повтори ту же команду (не больше 2 раз), он продолжит со скачанного" % timeout)
    print("ДЕРЕВО: " + meta["tree"])
    summary(rows)
    print("ДАЛЬШЕ: deps.py next")
    return 0


def tree_rows(code, out, timeout, add, meta, parse):
    DATA.mkdir(parents=True, exist_ok=True)
    TREE.write_text(out, encoding="utf-8")
    if code is None:
        add("D-10", "NEEDS-HUMAN", "-", "дерево не построено: таймаут %d секунд" % timeout)
        meta["tree"] = "не построено: таймаут"
        return
    if code != 0:
        first = next((l for l in out.splitlines() if "ERROR" in l), "код %s" % code)
        add("D-10", "NEEDS-HUMAN", "-", "дерево не построено: " + first.strip()[:200])
        meta["tree"] = "не построено: сборщик вернул ошибку"
        return
    conflicts, minor = parse(out)
    for module, coords, wanted, chosen, risk in conflicts:
        add("D-10", "VIOLATION", "модуль " + module, "%s: нужна %s, выбрана %s (%s; транзитивно, из дерева)" % (coords, wanted, chosen, risk))
    if not conflicts:
        add("D-10", "PASS", "-", "опасных конфликтов нет; безопасных подмен версии: %d" % minor)
    meta["tree"] = "построено: опасных конфликтов %d, безопасных подмен %d" % (len(conflicts), minor)


def maven_conflicts(out):
    found, minor, module, seen = [], 0, "-", set()
    for line in out.splitlines():
        head = re.search(r"dependency(?:-plugin)?:[\d.]+:tree .*@ ([\w.\-]+)", line)
        if head:
            module = head.group(1)
            continue
        m = re.search(r"([\w.\-]+):([\w.\-]+):\w+:([\w.\-]+)(?::\w+)? - omitted for conflict with ([\w.\-]+)", line)
        if not m:
            continue
        coords, wanted, chosen = m.group(1) + ":" + m.group(2), m.group(3), m.group(4)
        lower = frame_versions.version_key(chosen) < frame_versions.version_key(wanted)
        if (lower or major(chosen) != major(wanted)) and (module, coords, wanted, chosen) not in seen:
            seen.add((module, coords, wanted, chosen))
            found.append((module, coords, wanted, chosen, "версия понижена" if lower else "другая мажорная версия"))
        else:
            minor += 1
    return found, minor


def gradle_conflicts(out):
    found, minor, module, seen = [], 0, "-", set()
    for line in out.splitlines():
        head = re.match(r"(?:Root project|Project) '?:?([\w.\-:]*)'?", line.strip())
        if head:
            module = head.group(1).replace(":", "/") or "(корень)"
            continue
        m = re.search(r"([\w.\-]+):([\w.\-]+):([\w.\-]+) -> ([\w.\-]+)", line)
        if not m or "(c)" in line:
            continue
        coords, wanted, chosen = m.group(1) + ":" + m.group(2), m.group(3), m.group(4)
        if major(chosen) != major(wanted) and (module, coords) not in seen:
            seen.add((module, coords))
            found.append((module, coords, wanted, chosen, "другая мажорная версия"))
        else:
            minor += 1
    return found, minor


# Объявлены, но кодом не импортируются - это нормально: грузятся по имени (D-22, п. 1 правил)
LOADED_BY_NAME = [
    "postgresql", "ojdbc", "mysql-connector", "mariadb-java-client", "mssql-jdbc", "h2", "hsqldb", "clickhouse-jdbc",
    "slf4j-simple", "slf4j-log4j12", "slf4j-reload4j", "logback-classic", "log4j-slf4j", "log4j-core", "log4j:log4j",
    "allure-", "aspectjweaver", "junit-platform-", "junit-jupiter-engine", "junit-vintage-engine",
    "byte-buddy-agent", "selenium-", "webdrivermanager",
]


def loaded_by_name(coords):
    return (frame_versions.has_marker(coords) or coords.endswith(":junit-jupiter")
            or any(part in coords for part in LOADED_BY_NAME))


def analyze_rows(code, out, add):
    if code is None or code != 0:
        add("D-22", "TODO", "-", "dependency:analyze не отработал: проверь по references/rules.md, раздел D-22, по файлам")
        return
    modules, module, mode = {}, "-", None
    for line in out.splitlines():
        head = re.search(r"--- (?:maven-)?dependency(?:-plugin)?:[\d.]+:analyze .*@ ([\w.\-]+) ---", line)
        if head:
            module, mode = head.group(1), None
            modules.setdefault(module, {"used": [], "unused": []})
            continue
        if "Used undeclared dependencies found" in line:
            mode = "used"
        elif "Unused declared dependencies found" in line:
            mode = "unused"
        elif mode is not None:
            m = re.search(r"\]\s+([\w.\-]+:[\w.\-]+):\w+:[\w.\-]+", line)
            if m and " found:" not in line:
                modules.setdefault(module, {"used": [], "unused": []})[mode].append(m.group(1))
            else:
                mode = None
    found = 0
    for module in sorted(modules):
        used = sorted(set(modules[module]["used"]))
        unused = sorted(set(modules[module]["unused"]))
        if used:
            found += 1
            add("D-22", "VIOLATION", "модуль " + module, "используются без объявления (dependency:analyze): "
                + ", ".join(used) + " - объявить явно", level="WARNING")
        dead = [c for c in unused if not loaded_by_name(c)]
        skipped = [c for c in unused if loaded_by_name(c)]
        if dead:
            found += 1
            add("D-22", "NEEDS-HUMAN", "модуль " + module, "объявлены и не импортируются кодом (dependency:analyze): "
                + ", ".join(dead) + " - удалить?" + (" Не считаются (грузятся по имени): " + ", ".join(skipped) if skipped else ""))
    if not found:
        add("D-22", "PASS", "-", "dependency:analyze: замечаний нет")


# ---------- next / mark / add / report ----------

def cmd_next():
    meta, rows = load()
    row = next((r for r in rows if r["status"] in ("TODO", "CANDIDATE")), None)
    if not row:
        print("ВСЁ ПРОВЕРЕНО: строк TODO и CANDIDATE нет")
        print("ДАЛЬШЕ: deps.py report --summary \"<2-3 предложения>\"")
        return 0
    rule = RULES[row["id"]]
    print("СТРОКА: %s · %s · %s · %s" % (row["n"], row["id"], rule[2], row["status"]))
    print("ДАННЫЕ: " + row["note"])
    print("ТИП ПРОЕКТА: " + meta["type"])
    print("КАК ПРОВЕРИТЬ: references/rules.md, раздел " + row["id"])
    print("ЗАПИСАТЬ: deps.py mark %s <PASS|VIOLATION|N/A|NEEDS-HUMAN> --note \"<что увидел>\" [--where <файл:строка>]" % row["n"])
    print("ЕЩЁ МЕСТО ТОГО ЖЕ ПРАВИЛА: deps.py add %s --where <файл:строка> --note \"<что не так>\"" % row["id"])
    return 0


def option(args, name):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else ""


def cmd_mark(args):
    if len(args) < 2 or args[1] not in STATUSES or not option(args, "--note"):
        print("Использование: deps.py mark <N-n> <PASS|VIOLATION|N/A|NEEDS-HUMAN> --note \"<текст>\" [--where <файл:строка>]")
        return 2
    meta, rows = load()
    row = next((r for r in rows if r["n"] == args[0]), None)
    if not row:
        print("НЕТ СТРОКИ: " + args[0])
        return 1
    row["status"], row["note"] = args[1], option(args, "--note").replace("|", "/")
    row["where"] = option(args, "--where") or row["where"]
    level = option(args, "--level")
    if level and level not in LEVEL_ORDER:
        print("НЕВЕРНО: --level " + level + " - CRITICAL, WARNING или INFO")
        return 2
    row["level"] = level or row["level"]
    save(meta, rows)
    print("ЗАПИСАНО: %s %s %s" % (row["n"], row["id"], row["status"]))
    return 0


def cmd_add(args):
    if not args or args[0] not in RULES or not option(args, "--where") or not option(args, "--note"):
        print("Использование: deps.py add <D-id> --where <файл:строка> --note \"<текст>\"")
        return 2
    meta, rows = load()
    level = option(args, "--level") or RULES[args[0]][0]
    if level not in LEVEL_ORDER:
        print("НЕВЕРНО: --level " + level + " - CRITICAL, WARNING или INFO")
        return 2
    rows.append({"n": "N-%d" % (len(rows) + 1), "id": args[0], "level": level, "status": "VIOLATION",
                 "where": option(args, "--where"), "note": option(args, "--note").replace("|", "/")})
    save(meta, rows)
    print("ДОБАВЛЕНО: %s %s" % (rows[-1]["n"], args[0]))
    return 0


CONFLICT_RULES = ("D-P1", "D-04", "D-10", "D-06", "D-23")


def cmd_report(args):
    text = option(args, "--summary")
    if not text:
        print("Использование: deps.py report --summary \"<2-3 предложения вывода>\"")
        return 2
    meta, rows = load()
    left = [r["n"] + " " + r["id"] for r in rows if r["status"] in ("TODO", "CANDIDATE")]
    if left:
        print("НЕ ПРОВЕРЕНО: " + ", ".join(left) + " - сначала deps.py next и mark")
        return 1
    bad = sorted((r for r in rows if r["status"] == "VIOLATION"), key=lambda r: (LEVEL_ORDER[r["level"]], r["id"]))
    for i, r in enumerate(bad, 1):
        r["f"] = "F-%d" % i
    human = [r for r in rows if r["status"] == "NEEDS-HUMAN"]
    passed = [r for r in rows if r["status"] in ("PASS", "N/A")]

    def short(level):
        items = [r for r in bad if r["level"] == level]
        return str(len(items)), "; ".join(sorted({RULES[r["id"]][2] for r in items})) or "-"

    out = ["# Анализ управления зависимостями", "", text.strip(), "",
           "| Важность | Сколько | Про что коротко |", "|---|---|---|",
           "| 🔴 Критично | %s | %s |" % short("CRITICAL"), "| 🟡 Предупреждения | %s | %s |" % short("WARNING"),
           "| 🔵 Замечания | %s | %s |" % short("INFO"), "",
           "**Проект:** %s · **Сборка:** %s · **Структура:** %s · **Тип:** %s · **Фрейм:** %s · **Дата:** %s · "
           "**Файлов сборки:** %s · **Правил:** %d · **Дерево зависимостей:** %s"
           % (Path(".").resolve().name, meta["build"], meta["structure"], meta["type"], meta["frame"], meta["date"],
              meta["files"], len(RULES), meta["tree"]), "", "## Пересечения и конфликты зависимостей", ""]
    conflicts = [r for r in bad if r["id"] in CONFLICT_RULES]
    if conflicts:
        for r in conflicts:
            rule = RULES[r["id"]]
            out.append("%s (%s, %s). %s. Где: %s. Чем грозит: %s. Как развести: %s." % (
                r["f"], r["id"], rule[2], r["note"].rstrip("."), r["where"], rule[3], rule[4]))
            out.append("")
    else:
        out += ["Существенных конфликтов и пересечений зависимостей не найдено.", ""]
    for level, title in (("CRITICAL", "## 🔴 Критично"), ("WARNING", "## 🟡 Предупреждения"), ("INFO", "## 🔵 Замечания")):
        out += [title, ""]
        items = [r for r in bad if r["level"] == level]
        if not items:
            out += ["Нет.", ""]
        for r in items:
            rule = RULES[r["id"]]
            if r["id"] in CONFLICT_RULES:
                out += ["### %s · %s · `%s`" % (r["f"], rule[2], r["id"]), "- см. раздел про конфликты", ""]
                continue
            out += ["### %s · %s · `%s`" % (r["f"], rule[2], r["id"]), "- **Где:** " + r["where"],
                    "- **Что не так:** " + r["note"].rstrip(".") + ". На практике: " + rule[3] + ".",
                    "- **Как исправить:** " + rule[4] + ".", ""]
    out += ["## Требует внимания человека", ""]
    out += ["- %s · %s · %s" % (r["id"], r["where"], r["note"]) for r in human] or ["Нет."]
    edges = meta.get("edges", {})
    out += ["", "<details>", "<summary>Пройденные проверки (%d) и карта модулей</summary>" % len(passed), "",
            "**Пройдено:**", ""] + ["- %s - %s" % (r["id"], r["note"]) for r in passed] + ["", "**Карта модулей:**", ""]
    out += (["- %s -> %s" % (k, ", ".join(v) or "нет") for k, v in edges.items()] if len(edges) > 1 else ["N/A"])
    out += ["</details>", ""]
    REPORT.write_text("\n".join(out), encoding="utf-8")
    meta["deps_status"] = "reported"
    save(meta, rows)
    count = {lvl: sum(1 for r in bad if r["level"] == lvl) for lvl in LEVEL_ORDER}
    print("ОТЧЁТ: " + str(REPORT).replace("\\", "/"))
    print("НАХОДКИ: критично %d · предупреждений %d · замечаний %d · человеку %d"
          % (count["CRITICAL"], count["WARNING"], count["INFO"], len(human)))
    print("ГЛАВНОЕ: " + ("%s %s - %s" % (bad[0]["f"], RULES[bad[0]["id"]][2], bad[0]["where"]) if bad else "нет"))
    frame = sorted({r["id"] for r in bad if r["id"] in ("D-P1", "D-P2")})
    print("ФРЕЙМ: " + (", ".join(frame) + " - /opsx-de-pvatf обнови окружение выровняет версию фрейма" if frame else "ok"))
    return 0


def main(args):
    commands = {"scan": lambda: cmd_scan("."), "tree": lambda: cmd_tree(args[1:]), "next": cmd_next,
                "mark": lambda: cmd_mark(args[1:]), "add": lambda: cmd_add(args[1:]), "report": lambda: cmd_report(args[1:])}
    if not args or args[0] not in commands:
        print("Использование: deps.py scan | tree [--timeout 540] [--no-build] | next | mark <N-n> <статус> --note ... | "
              "add <D-id> --where ... --note ... | report --summary ...")
        return 2
    return commands[args[0]]()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
