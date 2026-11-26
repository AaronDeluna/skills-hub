# pvatf-openspec

Скиллы фрейма PVATF поверх OpenSpec: изменение `openspec/changes/<имя>/` -> proposal -> tc -> design -> tasks -> apply.

- Точка входа - скилл `de-pvatf-orchestrator` (команда `/opsx-de-pvatf`): он выбирает изменение и следующий шаг.
- Артефакты изменения пишет скрипт `os_artifacts.py`, не ты: инструкцию артефакта бери из
  `openspec instructions <артефакт> --change <имя> --json`, не по памяти.
- Ванильные скиллы `openspec-*`, если установлены, для изменений PVATF не используй.
