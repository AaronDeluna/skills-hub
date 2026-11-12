#!/usr/bin/env python3
"""Для разработчиков набора. Общие файлы лежат в shared/ - это источник. Скиллы ставятся
по отдельности, поэтому каждому нужна своя копия. Что куда копировать - в shared/copies.json:
{"<файл из shared/>": ["<скилл>", ...]}; файл из shared/scripts/ попадает в <скилл>/scripts/,
остальные - в <скилл>/references/. Запуск из папки набора:

  python3 scripts/sync_shared.py          - разложить копии
  python3 scripts/sync_shared.py --check  - проверить, что копии совпадают (код выхода 1 - нет)

Python 3.8+, только стандартная библиотека.
"""
import json
import shutil
import sys
from pathlib import Path


def main(args):
    check = bool(args) and args[0] == "--check"
    shared = Path("shared")
    config = shared / "copies.json"
    if not config.is_file():
        print("Нет " + str(config) + " - запускай из папки набора (там, где shared/)")
        return 2
    copies = json.loads(config.read_text(encoding="utf-8"))
    differ = 0
    for name, skills in copies.items():
        source = shared / name
        content = source.read_bytes()
        for skill in skills:
            target = Path(skill) / name if name.startswith("scripts/") else Path(skill) / "references" / name
            if target.is_file() and target.read_bytes() == content:
                continue
            if check:
                print("РАЗОШЛОСЬ: " + str(target) + " не совпадает с " + str(source))
                differ += 1
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(source), str(target))
                print("обновлено: " + str(target))
    if check:
        print("все копии совпадают" if differ == 0 else "разошлось копий: " + str(differ))
    else:
        print("готово")
    return 0 if differ == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
