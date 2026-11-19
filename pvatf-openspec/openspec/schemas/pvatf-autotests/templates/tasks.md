apply-mode: subagents

## Цель
<автотест <ключ> по design.md>

## 1. G-1 · <технология>
- [ ] 1.1 <действие> (design.md:<строка>)
- [ ] 1.2 Фрагмент теста, шаги <n> (design.md:<строка>)
- [ ] 1.3 `mvn -q test-compile` -> ожидается OK

## N. Сборка и проверка
- [ ] N.1 `python3 .gigacode/skills/autotest-gen/scripts/at_tools.py assemble <ключ>`
- [ ] N.2 `python3 .gigacode/skills/autotest-gen/scripts/at_tools.py check <ключ>` -> находок 0
