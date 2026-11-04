export const meta = {
  name: 'pvatf-migrate',
  description: 'Продолжает миграцию на PVATF по одобренной карте: спрашивает NextAction, какой юнит следующий, и выполняет юниты по очереди workflow pvatf-unit - пока они закрываются, но не больше заданного числа. На любом другом действии (карта, вопросы, ревью, блокер) останавливается и говорит, что делать.',
  whenToUse: 'Карта миграции одобрена, вопросов без ответа нет, нужно продолжить миграцию. Аргумент: сколько юнитов сделать за запуск (по умолчанию 3).',
  phases: [
    { title: 'Юниты', detail: 'NextAction -> pvatf-unit, пока юниты закрываются' },
  ],
}

const input = typeof args === 'number' ? { max: args } : typeof args === 'string' ? { max: parseInt(args, 10) } : (args || {})
const MAX_UNITS = Number.isInteger(input.max) && input.max > 0 ? input.max : 3
const NEXT_JAVA = 'java -Dfile.encoding=UTF-8 .gigacode/skills/orchestrator/scripts/NextAction.java'

const RUN = {
  type: 'object', required: ['results'],
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object', required: ['command', 'exit', 'output'],
        properties: { command: { type: 'string' }, exit: { type: 'integer' }, output: { type: 'string' } },
      },
    },
  },
}

/** Что сказать человеку на действие NextAction, которое не юнит (orchestrator SKILL.md, Шаг 2). */
const HINTS = {
  'агенты установлены': 'Перезапустите GigaCode (агенты читаются при запуске) и запустите workflow снова.',
  'migration-map': 'Карту строит скилл: /orchestrator Продолжи миграцию',
  'одобрение карты': 'Карту нужно одобрить: /orchestrator Продолжи миграцию',
  'вопросы': 'В карте вопросы без ответа: /orchestrator Продолжи миграцию',
  'migration-review': 'Все юниты done - проверка миграции: /orchestrator Проверь миграцию',
  'финал': 'Миграция закончена: /orchestrator Покажи статус миграции',
}

phase('Юниты')
const results = []
for (let i = 0; i < MAX_UNITS; i++) {
  let next = null
  for (let attempt = 0; attempt < 2 && !next; attempt++) {
    const answer = await agent(`Выполни команду из корня проекта и верни код выхода и вывод.\n1. ${NEXT_JAVA}`,
      { agentType: 'pvatf-runner', schema: RUN, label: 'NextAction' })
    next = answer && answer.results && answer.results[0] ? answer.results[0] : null
  }
  if (!next) {
    results.push({ status: 'stopped', reason: 'pvatf-runner не вернул вывод NextAction' })
    break
  }
  const action = (next.output.match(/ДЕЙСТВИЕ:\s*(.*)/) || [])[1] || ''
  const why = (next.output.match(/ПОЧЕМУ:\s*(.*)/) || [])[1] || ''
  log(`ДЕЙСТВИЕ: ${action}`)
  const unit = (action.match(/^migration-step (M-\d+)$/) || [])[1]
  if (!unit) {
    const key = Object.keys(HINTS).find(k => action.startsWith(k))
    results.push({ status: 'stopped', action, reason: why, next: key ? HINTS[key] : 'Продолжите через /orchestrator' })
    break
  }
  const result = await workflow('pvatf-unit', { unit })
  results.push(result || { status: 'stopped', unit, reason: 'pvatf-unit не вернул результат' })
  if (!result || result.status !== 'done') break
}

const done = results.filter(r => r.status === 'done').map(r => r.unit)
const last = results[results.length - 1] || {}
return {
  units_done: done,
  last,
  human: results.flatMap(r => r.human || []),
  next: last.status === 'done' ? 'Запустите workflow снова, чтобы продолжить' : (last.next || last.reason || ''),
}
