# How to make the project inventory (and keep your context small)

Read this file before Stage 2. The main idea: **count and search with commands, do not read files**.
Immediately make the output of each command into a short entry in `inventory/<модуль>.md`. Limit
long output with `| head -<n>`.

What NOT to do:
- do not open all classes one after the other «чтобы понять проект»;
- do not read `target/`, `build/`, `.gradle/`, `.idea/`, `node_modules/`, `*.jar`, `*.class`;
- do not look into `~/.m2` and caches - the framework API comes only from the MCP documentation.

In all commands, `<SRC>` is the source root of the module (for example `module-a/src`).

## 1. Map passport

```
ls                                                  # что в корне
ls pom.xml build.gradle build.gradle.kts settings.gradle settings.gradle.kts 2>/dev/null
ls mvnw gradlew 2>/dev/null                         # есть ли wrapper
git branch -a | head -30                            # ветки, основная ветка, конвенция имён
git log --oneline -15                               # конвенция коммитов
ls checkstyle.xml config/checkstyle .editorconfig 2>/dev/null
```

Modules: Maven - `grep -n "<module>" pom.xml`; Gradle - `grep -n "include" settings.gradle*`.

Find the test framework by the imports, not by the dependencies:
```
grep -rhoE "import org\.(junit\.jupiter\.api|junit|testng\.annotations)\.Test" --include=*.java --include=*.kt . | sort | uniq -c
```

Runner: use the wrapper (`./mvnw` / `./gradlew`) first. Make sure that it starts
(`<RUN> -v` / `<RUN> --version`). Commands for the map passport:
```
<RUN> -q -DskipTests compile test-compile      # Maven
<RUN> compileJava compileTestJava              # Gradle
```
Do not run the full project to find out if the tests can run locally. Look at README/CI
(`Jenkinsfile`, `.gitlab-ci.yml`). If it is not clear, ask the human. Write the result into the
map passport as it is.

## 2. Inventory of one module

Do one module at a time. After each module, immediately write `inventory/<модуль>.md`.

Size:
```
find <SRC> -name "*.java" -o -name "*.kt" | wc -l
find <SRC> \( -name "*.java" -o -name "*.kt" \) -exec cat {} + | wc -l
```

Top imports by packages (the first 3 segments) - the main input for the matrix `G`:
```
grep -rhoE "^import (static )?[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+" --include=*.java --include=*.kt <SRC> | sed -E "s/^import (static )?//" | sort | uniq -c | sort -rn | head -60
```

For each non-JDK package from the top - how many files use it:
```
grep -rlE "^import (static )?<пакет>\." --include=*.java --include=*.kt <SRC> | wc -l
```

Base classes and interfaces (what the classes extend):
```
grep -rhoE "(extends|implements) [A-Z][A-Za-z0-9_<>, ]+" --include=*.java <SRC> | sort | uniq -c | sort -rn | head -40
```

Annotations (which annotations and how many):
```
grep -rhoE "^\s*@[A-Z][A-Za-z0-9_]+" --include=*.java --include=*.kt <SRC> | sed -E "s/^\s+//" | sort | uniq -c | sort -rn | head -40
```

How many tests:
```
grep -rE "^\s*@Test\b" --include=*.java --include=*.kt <SRC> | wc -l
```

Large files (candidates for separate units and for architecture problems):
```
find <SRC> \( -name "*.java" -o -name "*.kt" \) -exec wc -l {} + | sort -rn | head -20
```

Package structure (only directories, 4 levels):
```
find <SRC> -type d -maxdepth 8 | head -80
```

Configs and resources:
```
find <SRC> -path "*resources*" -type f | head -60
```

What is already on PVATF (the framework package is `ru.sber.qa`, under it `io.perfeccionista.framework`):
```
grep -rlE "^import (static )?(ru\.sber\.qa|io\.perfeccionista)\." --include=*.java --include=*.kt <SRC> | wc -l
```
An import of these packages is a use of the framework. Compare this use with the documentation to find out if it is correct.

## 3. Samples

For each usage pattern (a line of the future matrix `G`), open 1-3 sample files. Use the most
typical file, and if possible a small one. Read only as much as you need to describe the
pattern in one line of the matrix. Write the sample path into the column «Образец в проекте».

## 4. Format of inventory/<модуль>.md

```markdown
# Инвентаризация: <модуль>

- Файлов: <n> · Строк: <n> · Тестов (@Test): <n>
- Уже на PVATF файлов: <n>

## Топ импортов (пакет - файлов)
- <пакет> - <n>

## Базовые классы / интерфейсы (имя - сколько наследников)
- <имя> - <n>

## Аннотации (имя - сколько)
- <имя> - <n>

## Большие файлы (путь - строк)
- <путь> - <n>

## Конфиги
- <путь> - <что это, 3-5 слов>

## Заметки
- <что бросилось в глаза: самописные обёртки, дубли, странности>
```

## 5. Architecture («Архитектура», for Stage 4)

Take the target architecture from the documentation (the record `D-common-3` in `doc-notes/common.md`; if it does not give enough - use the documentation subagent).
First read it. Write the layers and the rules in 5-10 lines into the notes. Then check the project.
What to check usually (do each check with a command, with a number and 1-2 examples):

| What to check | How to search |
|---------------|-----------|
| Tests work directly with the low level (driver, HTTP client, SQL) and skip the layer that the documentation tells to use | `grep -rl` on the low-level imports in the test directory |
| Custom wrappers over things that the framework already gives | classes `*Utils`, `*Helper`, `*Wrapper`, `Base*` - compare with the documentation |
| Giant classes | the list of large files (> 500 lines) |
| Duplication (the same code in a number of modules) | the same class names: `find . -name "*.java" -exec basename {} \; \| sort \| uniq -d` |
| Hardcoded values (addresses, logins, timeouts in the code) | `grep -rnE "https?://\|Thread\.sleep\|password" --include=*.java <SRC> \| head -30` |
| Shared mutable static state | `grep -rnE "static [^f(]*=" --include=*.java <SRC> \| grep -v final \| head -30` |
| The code is not in the layer/package that the documentation tells to use | the package structure compared with the structure from the documentation |
| Your own code in the framework package | `grep -rlE "^package ru\.sber\.qa" --include=*.java <SRC>` |

If you found a problem, but the documentation has no rule about it - this is not your decision.
Write the basis
`нет в доке - на решение человека`, and put a question into section 6 of the migration map.
