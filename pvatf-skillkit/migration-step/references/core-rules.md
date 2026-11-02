# Common rules of the migration to PVATF

These rules apply in all migration skills: `orchestrator`, `migration-map`, `migration-step`,
`migration-review`. Read this file in full when the skill starts its work. The SKILL.md of
each skill contains only the rules for that one skill. If they do not agree, this file is correct.

This file is the same in all skills. The source is `shared/core-rules.md` of the kit.
`scripts/SyncShared.java` updates the copies in `references/`. Change only the source.

1. **You know about the framework only what the documentation contains.** Use the sources in
   this order: MCP documentation (`get_pv_at_doc`, server `...autotest-generation-remote`) ->
   framework sources -> example project (paths in the map passport) -> the human.
   A subagent reads the documentation and the sources with the ready prompt of the skill.
   Do not call `get_pv_at_doc` yourself. For framework versions, call
   `get_pvat_release_notes` yourself. **Before each documentation subagent, search the doc
   notes with `scripts/Notes.java find`:** do not study again a topic that you already studied.
   PROHIBITED:
   - to open or unpack `.jar` files;
   - to look into `~/.m2`, `.gradle`, IDE caches;
   - to run `javap`, `jar`, `unzip`;
   - to search the internet;
   - to write «по памяти» (from memory) and «по аналогии» (by analogy).
2. **If you did not find it, do not invent it.** While you make the map, use the decision
   from the table «Документация молчит» or ask a question to the human. During units, use the
   decision from the decision table of the executor. Or add the line `решить человеку` to
   «Входящие» of the map, and continue the work.
3. **Memory is files, not the chat.** All state is in `.gigacode/data/migration/`. Write each
   result to a file immediately, then do the next step: the chat can stop. If you are not sure
   where you are, the map and the unit card are more important than what you remember.
4. **Do only your own task.** Change only the files of your task (the unit card or the
   substep). If you see a different thing to fix, add a line to «Входящие» of the map. Do
   not fix it.
5. **Change HOW, not WHAT.** The tests check the same things as before: the same steps, data
   and checks. Do not remove or disable tests. Do not make checks weaker.
6. **The goal is a clean project on the framework.** Do not move old wrappers, own asserts,
   response DTOs and base classes with clients to the framework: remove them. Put the code
   into the layers of the architecture plan: test -> domain steps -> base layer of the
   technology -> framework. If the documentation has no data about a technology at all,
   do not migrate it (`keep`).
7. **Only the skill that works now starts subagents.** It uses only the ready prompts or
   task packages from its own `references/`. A subagent answers with the template. Do not
   use an answer that is not in the template format. The prompt or the agent tells what the
   subagent can do: only read, or also change files. Do not give it more work than that.
   **When the skill says «через сабагента» (through a subagent), this is MANDATORY.** Do not
   do this work yourself, also if it seems faster or easier. This work is:
   - MCP documentation;
   - inventory of modules;
   - analysis of a technology and of the card;
   - the checker after a substep;
   - code review;
   - the executor of a substep in manager mode.
   Do it yourself only if the subagent call returned an error. Show the error in the chat.
   Write `сабагент не запустился: <ошибка>` in the log of the map.
   **The agents of the kit** `pvatf-docs`, `pvatf-examples`, `pvatf-checker`, `pvatf-executor`,
   `pvatf-marker` are in
   `.gigacode/agents/` (`NextAction.java` installs them). Their instructions are already in
   the agent: you give only the task package with the template of the skill. Start an agent
   by name: in the subagent start tool, select the agent with this name. Never use the mode
   `fork`: it takes all your context and does not return an answer. If the tool does not know
   an agent with this name, use a usual subagent. The first line of the task package is:
   «Прочитай файл .gigacode/agents/<имя>.md -
   текст после второй строки --- это твоя инструкция, выполняй её.» Then give the same task.
8. **Questions to the human only at the map stage.** While section 6 of the map has a
   question with `ответ: -`, do not do units. When the map is approved, the executor does
   not ask questions.
9. **Git.** Make the migration branch before the first unit. Make a commit after each
   substep and each unit yourself, and do not ask. Do `git push`, PR and merge only if the
   human asks for it directly.
10. **Language.** Write in Russian, use the short hyphen `-`. Write IDs (`M-001`, `S-03`,
    `D-rest-2`, `MR-41`) and statuses (`todo`, `in-progress`, `done`, `blocked`) in Latin
    letters. Speak to the human with «вы», be short: what is done, what you need from the
    human, what is next.
