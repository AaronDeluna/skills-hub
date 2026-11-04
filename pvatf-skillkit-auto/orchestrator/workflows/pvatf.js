export const meta = {
  name: 'pvatf',
  description: 'Единая команда набора PVATF (автономная версия). migrate - миграция от и до: карта, юниты (через pvatf-unit), разметка, проверка миграции, финал. markup - проверка и постановка разметки тестов без миграции. status - где сейчас миграция. Значения разметки можно передать сразу: system=CI02546875 stage=ift team="Payments" model=tms. Нет значения - workflow останавливается с вопросами; повторный запуск продолжает с того же места.',
  whenToUse: 'Любая работа по миграции проекта автотестов на PVATF или по разметке тестов. Аргумент - строка: "migrate", "migrate M-007", "markup", "markup check", "status" и значения key=value.',
  phases: [
    { title: 'Команда', detail: 'разбор аргументов, NextAction' },
    { title: 'Работа', detail: 'карта, юниты, разметка, проверка - по NextAction' },
    { title: 'Итог', detail: 'что сделано и что осталось человеку' },
  ],
}

// ---------- аргументы ----------

const KEYS = ['upgrade', 'model', 'system', 'stage', 'team', 'regress', 'story']

function parseArgs(raw) {
  if (raw && typeof raw === 'object') {
    return { command: raw.command || 'migrate', unit: raw.unit || '', check: !!raw.check, values: raw.values || {}, max: raw.max }
  }
  const text = String(raw || '')
  const values = {}
  for (const m of text.matchAll(/([a-z]+)=("([^"]*)"|'([^']*)'|\S+)/g)) {
    if (KEYS.includes(m[1])) values[m[1]] = m[3] !== undefined ? m[3] : m[4] !== undefined ? m[4] : m[2]
  }
  const rest = text.replace(/([a-z]+)=("[^"]*"|'[^']*'|\S+)/g, ' ').trim().split(/\s+/).filter(Boolean)
  const command = ['migrate', 'markup', 'status'].includes(rest[0]) ? rest[0] : 'migrate'
  const unit = (text.match(/\bM-\d+\b/) || [])[0] || ''
  const maxWord = rest.find(w => /^\d+$/.test(w))
  return { command, unit, check: rest.includes('check'), values, max: maxWord ? Number(maxWord) : undefined }
}

const input = parseArgs(args)
const MAX_ACTIONS = 200
const MAX_UNITS = Number.isInteger(input.max) && input.max > 0 ? input.max : 1000
const NEXT_JAVA = 'java -Dfile.encoding=UTF-8 .gigacode/skills/orchestrator/scripts/NextAction.java'
const PROGRESS = '.gigacode/data/migration/tmp/progress.md'

// ---------- схемы ----------

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
const STEP = {
  type: 'object', required: ['ok', 'done', 'requests', 'questions', 'summary'],
  properties: {
    ok: { type: 'boolean', description: 'false - работать дальше нельзя, причина в stop_reason' },
    done: { type: 'boolean', description: 'задача сделана целиком' },
    stop_reason: { type: 'string' },
    requests: {
      type: 'array', description: 'задания сабагентам, которые ты сам запустить не можешь; workflow запустит их и вернёт ответы',
      items: {
        type: 'object', required: ['agent', 'prompt'],
        properties: {
          agent: { type: 'string', enum: ['pvatf-docs', 'pvatf-examples', 'pvatf-marker', 'pvatf-checker', 'general'] },
          prompt: { type: 'string', description: 'задание дословно, по шаблону из файла скилла' },
        },
      },
    },
    questions: {
      type: 'array', description: 'вопросы разметки человеку, ровно текстом из колонки «Вопрос» правил разметки',
      items: {
        type: 'object', required: ['key', 'text'],
        properties: {
          id: { type: 'string', description: 'Q-<n> из раздела 6 карты, если вопрос записан туда' },
          key: { type: 'string', enum: KEYS },
          text: { type: 'string' },
          options: { type: 'array', items: { type: 'string' } },
        },
      },
    },
    summary: { type: 'string', description: 'что сделано в этом вызове, 1-3 строки' },
    human: { type: 'array', items: { type: 'string' }, description: 'что осталось на человеке' },
  },
}

// ---------- помощники ----------

async function run(label, commands) {
  const prompt = 'Выполни команды по порядку, из корня проекта, и верни код выхода и вывод каждой.\n'
    + commands.map((c, i) => `${i + 1}. ${c}`).join('\n')
  for (let attempt = 0; attempt < 2; attempt++) {
    const answer = await agent(prompt, { agentType: 'pvatf-runner', schema: RUN, label })
    if (answer && Array.isArray(answer.results) && answer.results.length === commands.length) return answer.results
  }
  throw new Error(`pvatf-runner не вернул вывод команд: ${label}`)
}

async function nextAction(unit) {
  const [r] = await run('NextAction', [`${NEXT_JAVA} ${unit || ''}`.trim()])
  return {
    raw: r.output,
    action: (r.output.match(/ДЕЙСТВИЕ:\s*(.*)/) || [])[1] || '',
    why: (r.output.match(/ПОЧЕМУ:\s*(.*)/) || [])[1] || '',
    note: (r.output.match(/ЗАМЕТКА:\s*(.*)/) || [])[1] || '',
  }
}

/** Значение для вопроса разметки из аргументов; не подходит под варианты - нет значения. */
function valueFor(q) {
  const v = input.values[q.key]
  if (v === undefined || v === '') return undefined
  if (q.options && q.options.length && !q.options.includes(v)) return undefined
  return v
}

const PROTOCOL = `
Как отвечать workflow (схема ответа):
- Нужен сабагент (документация pvatf-docs, примеры pvatf-examples, разметка pvatf-marker, проверяющий pvatf-checker, любой
  другой сабагент из файлов скилла - agent: general) -> сам его НЕ запускай. Сначала запиши в ${PROGRESS}, что уже сделано и
  что делать с ответами, потом верни задания в requests (задание - дословно по шаблону из файла скилла) и done: false.
  Workflow запустит их и вызовет тебя снова с ответами.
- Скилл велит задать вопрос разметки человеку или вывести блок <<<PVATF-QUESTIONS -> не задавай и блок не выводи:
  запиши вопросы в раздел 6 карты, как велит скилл (если это миграция), и верни их в questions (key, текст ровно из
  колонки «Вопрос», варианты из колонки «Ответ»), done: false.
- Скилл велит остановиться и открыть новый чат -> это конец задачи: done: true.
- Тебя вызвали снова: сначала прочитай ${PROGRESS} и продолжай с того места; ответы ниже - ответы на твои задания и вопросы.
- Задача сделана -> done: true, requests и questions пустые.`

/**
 * Шаг по файлам скилла через pvatf-manager. Задания сабагентам запускает сам workflow и
 * возвращает ответы; вопросы разметки закрывает значениями из аргументов или останавливается.
 */
async function skillStep(task, body, label) {
  let extra = ''
  for (let round = 0; round < 12; round++) {
    let answer = null
    for (let attempt = 0; attempt < 2 && !answer; attempt++) {
      answer = await agent(`Задача: ${task}\nПроект: ${ctx.root}\n${body}\n${PROTOCOL}${extra}`,
        { agentType: 'pvatf-manager', schema: STEP, label: `${label}${round ? ` (${round + 1})` : ''}` })
    }
    if (!answer) return { ok: false, done: false, stop_reason: `${label}: менеджер не ответил по схеме` }
    if (answer.summary) log(`${label}: ${answer.summary}`)
    if (!answer.ok || answer.done) return answer
    extra = ''
    if (answer.questions.length) {
      const missing = answer.questions.filter(q => valueFor(q) === undefined)
      if (missing.length) return { ...answer, stopped: 'questions', questions: missing }
      extra += '\n\nОтветы человека на вопросы разметки (переданы в команде; впиши их, как велит скилл):\n'
        + answer.questions.map(q => `- ${q.id ? `${q.id} ` : ''}${q.key}: ${valueFor(q)}`).join('\n')
        + `\nТо же в формате приложения: {"answers": {${answer.questions.filter(q => q.id).map(q => `"${q.id}": "${valueFor(q)}"`).join(', ')}}}`
    }
    if (answer.requests.length) {
      const results = await parallel(answer.requests.map((r, i) => () => agent(r.prompt,
        r.agent === 'general' ? { label: `${label}: сабагент ${i + 1}` } : { agentType: r.agent, label: `${label}: ${r.agent} ${i + 1}` })))
      extra += '\n\nОтветы на твои задания сабагентам (в том же порядке):\n'
        + results.map((r, i) => `--- Задание ${i + 1} (${answer.requests[i].agent}):\n${r === null ? 'сабагент не ответил - сделай это сам по файлу скилла' : typeof r === 'string' ? r : JSON.stringify(r)}`).join('\n')
    }
    if (!answer.questions.length && !answer.requests.length) extra = '\n\nЗадача не закончена (done: false) - продолжай с того места, где остановился.'
  }
  return { ok: false, done: false, stop_reason: `${label}: не закончено за 12 вызовов менеджера` }
}

function questionsResult(step, where) {
  return {
    status: 'questions',
    where,
    questions: step.questions.map(q => ({ key: q.key, text: q.text, options: q.options || [] })),
    next: `Ответьте значениями и запустите снова: /pvatf ${input.command}${input.check ? ' check' : ''} `
      + step.questions.map(q => `${q.key}=${q.options && q.options.length ? `<${q.options.join('|')}>` : '<значение>'}`).join(' '),
  }
}

// ---------- старт ----------

const ctx = { root: '' }
phase('Команда')
const [pwd] = await run('корень проекта', ['pwd'])
ctx.root = String(pwd.output).trim().split('\n')[0]
log(`команда: ${input.command}${input.unit ? ` ${input.unit}` : ''}${input.check ? ' check' : ''}; значения: ${Object.keys(input.values).join(', ') || '-'}`)
const first = await nextAction('')
if (first.action === 'агенты установлены') {
  return { status: 'restart', reason: first.why, next: `Перезапустите GigaCode и запустите снова: /pvatf ${typeof args === 'string' ? args : input.command}` }
}

// ---------- status ----------

if (input.command === 'status') {
  const step = await skillStep('status', `Покажи статус миграции по \`.gigacode/skills/orchestrator/references/status.md\`. Ничего не меняй.
NextAction сейчас: ДЕЙСТВИЕ: ${first.action}; ПОЧЕМУ: ${first.why}`, 'статус')
  return { status: 'status', next_action: first.action, why: first.why, summary: step.summary, human: step.human || [] }
}

// ---------- markup ----------

if (input.command === 'markup') {
  phase('Работа')
  const step = await skillStep('markup', `Сделай отдельную проверку разметки по \`.gigacode/skills/orchestrator/references/markup.md\`
(правила - \`.gigacode/skills/orchestrator/references/markup-rules.md\`). Просьба человека: ${input.check
    ? '«проверь разметку» - только проверить; на вопрос «Поставить недостающие аннотации...? да/нет» ответ человека: нет'
    : '«разметь тесты» - проверить и поставить'}.
Агента pvatf-marker сам не запускай: задание ему (раздел 5, п.4 markup.md) верни в requests, agent: pvatf-marker. Его отчёт придёт
тебе следующим вызовом - дальше раздел 5, п.5-7 и итоговый ответ (раздел 6), его текст - в summary.`, 'разметка')
  if (step.stopped === 'questions') return questionsResult(step, 'разметка тестов')
  return { status: step.ok ? (step.done ? 'done' : 'stopped') : 'stopped', reason: step.stop_reason || '', summary: step.summary, human: step.human || [],
    report: '.gigacode/data/markup/MARKUP-REPORT.md' }
}

// ---------- migrate ----------

phase('Работа')
const log0 = []
const human = []
let units = 0
let previous = ''
let same = 0
let finalStep = null
let stop = null

for (let i = 0; i < MAX_ACTIONS && !stop; i++) {
  const next = i === 0 && !input.unit ? first : await nextAction(i === 0 ? input.unit : '')
  if (next.note) human.push(`NextAction: ${next.note}`)
  const state = `${next.action}|${next.why}`
  same = state === previous ? same + 1 : 0
  previous = state
  if (same >= 2) { stop = { status: 'stopped', reason: `нет продвижения: NextAction трижды подряд «${next.action}» - ${next.why}` }; break }
  log(`ДЕЙСТВИЕ: ${next.action}`)
  log0.push(next.action)
  const action = next.action

  if (action === 'агенты установлены') { stop = { status: 'restart', reason: next.why, next: 'Перезапустите GigaCode и запустите /pvatf migrate снова' }; break }

  if (action === 'migration-map' || action === 'вопросы разметки' || action === 'одобрение карты') {
    const step = await skillStep('map', `Выполни скилл \`migration-map\` (\`.gigacode/skills/migration-map/SKILL.md\`): ровно ОДИН этап - текущий
(\`map_stage\` в шапке карты; карты нет - «Старт» и Этап 1). Закончил этап -> отметь его, как велит скилл, и done: true.
NextAction: ДЕЙСТВИЕ: ${action}; ПОЧЕМУ: ${next.why}
${action === 'одобрение карты' ? 'Карта построена - доделай самопроверку Этапа 6 и поставь map_status: approved, как велит скилл.' : ''}`, 'карта')
    if (step.stopped === 'questions') return { ...questionsResult(step, 'вопросы разметки на Этапе 2 карты'), done_actions: log0, human }
    if (!step.ok) { stop = { status: 'stopped', reason: step.stop_reason }; break }
    if (step.human) human.push(...step.human)
    continue
  }

  if (action === 'вопросы') {
    const step = await skillStep('questions', 'Доведи записи раздела 6 карты до решения по `.gigacode/skills/orchestrator/references/questions.md`.', 'решения раздела 6')
    if (!step.ok) { stop = { status: 'stopped', reason: step.stop_reason }; break }
    continue
  }

  const single = action.match(/^migration-step (M-\d+)$/)
  const batch = action.match(/^migration-step пачка:\s*(.*)$/)
  if (single || batch) {
    const ids = single ? [single[1]] : (batch[1].match(/M-\d+/g) || [])
    for (const unit of ids) {
      if (units >= MAX_UNITS) { stop = { status: 'paused', reason: `сделано юнитов: ${units} (лимит запуска)` }; break }
      let result = await workflow('pvatf-unit', { unit })
      if (result && result.status === 'markup') {
        const step = await skillStep('unit-markup', `Юнит: ${unit} (тип markup). Выполни его по скиллу \`migration-step\`
(\`.gigacode/skills/migration-step/SKILL.md\`, потом \`references/markup.md\`) до конца: Шаги 1-2, разметка, закрытие (close.md).
Агента pvatf-marker сам не запускай - задание ему верни в requests (agent: pvatf-marker).`, `юнит ${unit}`)
        result = step.ok && step.done ? { status: 'done', unit, human: step.human || [], summary: step.summary }
          : step.stopped === 'questions' ? null : { status: 'stopped', unit, reason: step.stop_reason }
        if (!result) return { ...questionsResult(step, `разметка, юнит ${unit}`), done_actions: log0, human }
      }
      if (!result) { stop = { status: 'stopped', unit, reason: 'pvatf-unit не вернул результат' }; break }
      if (result.human) human.push(...result.human)
      if (result.status === 'done') { units++; continue }
      if (result.status === 'paused') { log(`${unit}: пауза - ${result.reason}`); break }   // NextAction решит, что дальше
      stop = { status: result.status, unit, reason: result.reason }
      break
    }
    if (input.unit && !stop) { stop = { status: 'done', reason: `юнит ${input.unit} выполнен` } }
    continue
  }

  if (action === 'migration-review') {
    const step = await skillStep('review', `Выполни скилл \`migration-review\` (\`.gigacode/skills/migration-review/SKILL.md\`) - один круг проверки миграции.
Сабагентов ревью сам не запускай: их задания верни в requests (agent: general), дальше - по ответам.`, 'проверка миграции')
    if (!step.ok) { stop = { status: 'stopped', reason: step.stop_reason }; break }
    if (step.human) human.push(...step.human)
    continue
  }

  if (action === 'финал') {
    finalStep = await skillStep('final', 'Сделай финал миграции по `.gigacode/skills/orchestrator/references/final.md`. Итоговый текст - в summary.', 'финал')
    if (finalStep.human) human.push(...finalStep.human)
    stop = { status: finalStep.ok ? 'done' : 'stopped', reason: finalStep.ok ? 'миграция закончена' : finalStep.stop_reason }
    break
  }

  // карта повреждена, нельзя, нечего делать, заблокировано, ядро готово, проверка не сходится
  stop = { status: 'stopped', reason: `${action}: ${next.why}`, next: action === 'заблокировано'
    ? 'Блокеры - в разделе «Блокер» карточек blocked и строках «решить человеку» карты'
    : 'Посмотрите причину; продолжить - /pvatf migrate' }
}

// ---------- итог ----------

phase('Итог')
return {
  ...(stop || { status: 'paused', reason: `за запуск выполнено ${MAX_ACTIONS} действий - запустите снова` }),
  units_done: units,
  actions: log0,
  summary: finalStep ? finalStep.summary : '',
  human,
}
