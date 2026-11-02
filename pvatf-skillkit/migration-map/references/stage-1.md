# Stage 1 - Overview of the framework from the documentation (doc-notes/common.md)

This file is a part of the skill `migration-map`. The general rules are in `references/core-rules.md`. The rules of the migration map and the order of stages are in `SKILL.md`.

Goal: before you examine the project, find out from the documentation what the framework
gives: which modules it has and for which technologies.

1. Read `references/subagents.md` (section 1) in full. It contains the rules, the task for the
   agent and the template of a doc notes record.
2. Start the agent `pvatf-docs` (the task is in `references/subagents.md`, section 1). Use the
   technology `common - фрейм в целом`. Use EXACTLY these questions:
   1. Какие модули есть во фрейме PVATF и за какую технологию отвечает каждый модуль?
   2. Как подключить фрейм к проекту автотестов: зависимости, BOM, плагины, минимальная
      конфигурация?
   3. Какую структуру проекта автотестов, какие слои и пакеты рекомендует фрейм?
   4. Как написать и запустить простой тест на фрейме: аннотации, базовые классы, раннер?
   5. Есть ли инструкция по миграции или переходу существующего проекта на PVATF?
   6. Как фрейм логирует запросы и ответы (REST, БД, Kafka) и как настроить уровень
      логирования?
   Do not call the tool `get_pv_at_doc` yourself. If the answer is `MCP НЕДОСТУПЕН` ->
   **СТОП**. Tell the human: without the MCP documentation, you cannot start the migration.
3. Write the answers as the records `D-common-1` ... `D-common-6` into
   `.gigacode/data/migration/doc-notes/common.md` (the record template is in `references/subagents.md`).
4. In section 1 of the migration map, in the row «Модули фрейма», write the list: module -
   technology.
5. **Versions.** Call the tool `get_pvat_release_notes` yourself (without parameters). Write
   into the map passport, in the row «Версии фрейма», what it returned: the version of the
   framework (pvat) and the version of perfeccionista - character for character. These
   versions go into the `env` units of the dependencies.
   If the tool is not available or returned an error -> write `не получены: <ошибка>` in
   the row. Then add a question to the human: which versions of the framework and
   perfeccionista to use.
6. **Framework sources and the sample project - find and update them yourself (mandatory).**
   They are the second and the third source after the documentation. Sometimes the
   documentation does not give the answer (for example, how to get the body of a REST
   response). Then find the answer in the framework sources: in their `docs/`, tests and
   samples. Ask the human only if the answer is not there. Thus find the sources now, one time
   for all of the migration. If the sources are already on the disk, do not ask the human for
   the path.
   1) If the human gave the path (in the request or through the orchestrator) -> use it and go
      to item 3.
   2) Find git clones on the disk. Use only directories with source code. Do not use `~/.m2`,
      `.gradle`, `.jar`. Do not unpack and do not decompile:
      ```
      find ~ /home /opt /work /data -maxdepth 6 -type d -name .git \( -path "*platform-v-at*" -o -path "*pvat*" -o -path "*perfeccionista*" \) -not -path "*/.m2/*" -not -path "*/node_modules/*" 2>/dev/null | sed 's#/\.git$##' | sort -u | head -20
      ```
      For each directory that you found, find out what it is:
      `ls <путь>; grep -m5 -nE "<module>|<artifactId>" <путь>/pom.xml 2>/dev/null`.
      - If the framework modules (`rest`, `kafka`, `database`, `websocket`... - as in
        «Модули фрейма» of the map passport) are in it as subdirectories with their own
        `src/main/java` -> these are the **framework sources**.
      - If the name has `draft`, or the project only adds the framework as a dependency and has
        tests -> this is the **sample project**.
      - If it is neither -> it is not applicable.
      - If you found more than one set of framework sources -> use the set with the newest last
        commit (`git -C <путь> log -1 --format=%cd`).
   3) Update: if `git -C <путь> status --short` is empty -> `git -C <путь> pull --ff-only` (do
      not change the branch). If there are changes or `pull` failed -> use what there is and
      write down the cause. Record the version: `git -C <путь> log -1 --format="%h %cd"`.
   4) The documentation directory in the sources: `find <путь> -maxdepth 3 -type d -name docs`.
   5) If you did not find the framework sources -> ask the human one question now, in the
      chat. This is an allowed question of Stage 1. Wait for the answer:
      «Чтобы реже спрашивать вас по ходу миграции, мне нужны исходники фрейма PVATF. Укажите,
      пожалуйста, полный путь к ним на этой машине или адрес git-репозитория - склонирую
      сам. Если исходников нет - напишите «нет».»
      If the answer is an address -> `git clone --depth 1 <адрес> ~/pvatf-sources/<имя репозитория>` and item 4.
      If the answer is a path -> item 3. If the answer is «нет» -> write `-` in the map passport.
   6) Write into the map passport: «Исходники фрейма» - the path, the version (`<хэш> <дата>`,
      `обновлено` / `не обновлено: <причина>`), the directory `docs`; «Проект-пример» - the
      path or `-`.

Mark Stage 1 `[x]`, `map_stage: 2`.

