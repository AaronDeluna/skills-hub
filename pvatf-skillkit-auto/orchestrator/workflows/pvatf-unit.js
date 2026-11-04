export const meta = {
  name: 'pvatf-unit',
  description: 'Один юнит миграции на PVATF по одобренной карте: подшаги по очереди - пакет, исполнитель, компиляция и Unit.java check, судьи по каждому правилу подшага с голосованием, чекпоинт, повторы исполнителя, закрытие и коммит. Порядок и проверки ведёт скрипт, пропустить их нельзя.',
  whenToUse: 'Карта миграции одобрена и нужно выполнить юнит M-<nnn> (или следующий юнит, который выберет NextAction). Аргумент: номер юнита, например M-007, или пусто.',
  phases: [
    { title: 'Вход', detail: 'NextAction, Шаги 1-2 migration-step' },
    { title: 'Подшаги', detail: 'исполнитель -> проверки -> повторы -> закрытие' },
    { title: 'Конец юнита', detail: 'чекпоинты юнита, close.md' },
  ],
}

// ---------- настройки запуска ----------

const input = typeof args === 'string' ? { unit: args } : (args || {})
const REQUESTED = String(input.unit || '').match(/M-\d+/) ? String(input.unit).match(/M-\d+/)[0] : ''
const REPEATS = Number.isInteger(input.repeats) ? input.repeats : 2      // повторов исполнителя на подшаг (manager.md, п.8)
const VOTES = Number.isInteger(input.votes) ? input.votes : 3            // судей на правило, если первый нашёл нарушение
const USE_JUDGES = input.judges !== false                                // судьи по правилам
const USE_CHECKER = input.checker === true                               // ещё и pvatf-checker (check.md, п.9)
const MAX_STEPS = 40
const UNIT_JAVA = 'java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/Unit.java'
const NEXT_JAVA = 'java -Dfile.encoding=UTF-8 .gigacode/skills/orchestrator/scripts/NextAction.java'

// ---------- схемы ответов ----------

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
  type: 'object', required: ['id', 'kind', 'status'],
  properties: { id: { type: 'string' }, kind: { type: 'string' }, title: { type: 'string' }, status: { type: 'string' } },
}
const START = {
  type: 'object', required: ['ok', 'type', 'compile', 'steps'],
  properties: {
    ok: { type: 'boolean' }, stop_reason: { type: 'string' },
    type: { type: 'string', description: 'поле type карточки' },
    compile: { type: 'string', description: 'команда компиляции из паспорта карты' },
    steps: { type: 'array', items: STEP, description: 'таблица «Подшаги» карточки; подшагов нет - пустой список' },
  },
}
const PREP = {
  type: 'object', required: ['ok', 'package', 'result', 'rules', 'checkpoint_command', 'checkpoint_expect'],
  properties: {
    ok: { type: 'boolean' }, stop_reason: { type: 'string' },
    package: { type: 'string', description: 'задание агенту pvatf-executor по шаблону manager.md, все строки' },
    result: { type: 'string', description: '«Итоговый результат» подшага дословно' },
    rules: { type: 'array', items: { type: 'string' }, description: 'номера MR из строки «Правила подшага» вывода Unit.java recite' },
    checkpoint_command: { type: 'string', description: 'команда из поля «Чекпоинт» - только сама команда' },
    checkpoint_expect: { type: 'string', description: 'что должна вывести команда чекпоинта, дословно из поля' },
    old_code: { type: 'string', description: '«Чего в коде быть не должно» (check.md, п.9); нет - "-"' },
  },
}
const CLOSE = {
  type: 'object', required: ['ok', 'steps', 'continue'],
  properties: {
    ok: { type: 'boolean' }, stop_reason: { type: 'string' }, commit: { type: 'string' },
    steps: { type: 'array', items: STEP, description: 'таблица «Подшаги» карточки после этой задачи' },
    continue: { type: 'boolean', description: 'идти ли к следующему подшагу (tech-flow.md, п.5)' },
    continue_reason: { type: 'string' },
  },
}
const REVIEW = {
  type: 'object', required: ['ok', 'mechanical', 'prompts'],
  properties: {
    ok: { type: 'boolean' }, stop_reason: { type: 'string' },
    mechanical: { type: 'string', description: 'вывод п.1 review-subagent.md' },
    prompts: { type: 'array', items: { type: 'string' }, description: 'промпт сабагенту ревью на каждую группу файлов' },
  },
}
const UNIT_END = {
  type: 'object', required: ['ok', 'unit_done', 'steps', 'summary'],
  properties: {
    ok: { type: 'boolean' }, stop_reason: { type: 'string' }, unit_done: { type: 'boolean' },
    steps: { type: 'array', items: STEP }, summary: { type: 'string', description: 'сводка Шага 8 close.md' },
    human: { type: 'array', items: { type: 'string' }, description: 'что осталось на человеке' },
  },
}
const JUDGE = {
  type: 'object', required: ['verdict', 'violations'],
  properties: {
    verdict: { type: 'string', enum: ['нарушено', 'не нарушено', 'не относится'] },
    violations: {
      type: 'array',
      items: {
        type: 'object', required: ['file', 'line', 'what'],
        properties: { file: { type: 'string' }, line: { type: 'integer' }, what: { type: 'string' }, fix: { type: 'string' } },
      },
    },
  },
}
const VERDICT = {
  type: 'object', required: ['ok', 'why'],
  properties: { ok: { type: 'boolean' }, why: { type: 'string' } },
}

// ---------- помощники ----------

/** Команды через агента pvatf-runner; вывод - как есть. Ответ не на все команды - ошибка. */
async function run(label, commands) {
  const prompt = 'Выполни команды по порядку, из корня проекта, и верни код выхода и вывод каждой.\n'
    + commands.map((c, i) => `${i + 1}. ${c}`).join('\n')
  for (let attempt = 0; attempt < 2; attempt++) {
    const answer = await agent(prompt, { agentType: 'pvatf-runner', schema: RUN, label })
    if (answer && Array.isArray(answer.results) && answer.results.length === commands.length) {
      return answer.results
    }
  }
  throw new Error(`pvatf-runner не вернул вывод команд: ${label}`)
}

function manager(task, body, schema, label) {
  return agent(`Задача: ${task}\nПроект: ${ctx.root}\nЮнит: ${ctx.unit}\n${body}`, { agentType: 'pvatf-manager', schema, label })
}

function lines(text) {
  return String(text || '').split('\n').map(l => l.trimEnd()).filter(l => l.trim() !== '')
}

function head(text, n) {
  return lines(text).slice(0, n).join('\n')
}

function stepTitle(s) {
  return s.id ? `${s.id} · ${s.kind} · ${s.title || ''}` : `весь юнит (подшагов нет) · ${s.kind}`
}

/** Изменённые .java/.kt вне .gigacode/ по git status. */
function changedSources(porcelain) {
  return lines(porcelain)
    .filter(l => !l.startsWith(' D') && !l.startsWith('D '))
    .map(l => l.slice(3).split(' -> ').pop().replace(/^"|"$/g, ''))
    .filter(p => !p.startsWith('.gigacode/') && /\.(java|kt)$/.test(p))
}

/** Строки находок Unit.java check (без шапки CHECK и итоговой строки). */
function checkFindings(output) {
  return lines(output).filter(l => !/^CHECK /.test(l) && !/^ИТОГ: находок/.test(l) && !/^КЛАССИФИКАТОР:/.test(l))
}

function checkCount(output) {
  const all = [...String(output || '').matchAll(/ИТОГ: находок (\d+)/g)]
  return all.length ? Number(all[all.length - 1][1]) : -1
}

/** Судьи: по агенту на правило; правило с «нарушено» перепроверяют ещё VOTES-1 судей, решает большинство. */
async function judges(rules, files, result) {
  const ask = rule => () => agent(
    `Проект: ${ctx.root}\nПравило: ${rule}\n`
      + `Текст правила: ${rule === 'ИТОГ' ? 'проверь, достигнут ли «Что шаг должен был сделать»' : `.gigacode/data/migration/tmp/rules-now.md, раздел «${rule} ·»`}\n`
      + `Что шаг должен был сделать: ${result}\nФайлы шага:\n${files.map(f => `- ${f}`).join('\n')}\nБаза: ${ctx.base}`,
    { agentType: 'pvatf-judge', schema: JUDGE, label: `судья ${rule}` })
  const first = await parallel(rules.map(ask))
  const suspects = rules.filter((r, i) => first[i] && first[i].verdict === 'нарушено')
  const unchecked = rules.filter((r, i) => !first[i])
  const confirmed = []
  for (const rule of suspects) {
    const more = VOTES > 1 ? await parallel(Array.from({ length: VOTES - 1 }, () => ask(rule))) : []
    const yes = 1 + more.filter(a => a && a.verdict === 'нарушено').length
    const voted = 1 + more.filter(a => a).length
    log(`${rule}: нарушено у ${yes} из ${voted} судей`)
    if (yes * 2 > voted) {
      const first0 = first[rules.indexOf(rule)]
      for (const v of first0.violations.length ? first0.violations : [{ file: files[0] || '-', line: 1, what: 'правило нарушено' }]) {
        confirmed.push(`${rule} ${v.file}:${v.line} - ${v.what}${v.fix ? ` (как исправить: ${v.fix})` : ''} [судьи: ${yes} из ${voted}]`)
      }
    }
  }
  return { confirmed, suspects: suspects.length, unchecked }
}

async function checkpoint(prep) {
  if (!prep.checkpoint_command || prep.checkpoint_command.trim() === '-') {
    return { ok: true, output: 'чекпоинта нет' }
  }
  const [r] = await run('чекпоинт', [prep.checkpoint_command])
  const verdict = await agent(
    `Сравни вывод команды с ожидаемым результатом. Только сравни, ничего не запускай и не исправляй.\n`
      + `Команда: ${prep.checkpoint_command}\nОжидается: ${prep.checkpoint_expect}\nКод выхода: ${r.exit}\nВывод:\n${r.output || '(пусто)'}`,
    { schema: VERDICT, label: 'сверка чекпоинта' })
  return { ok: !!(verdict && verdict.ok), output: `${head(r.output, 20) || '(пусто)'}${verdict ? ` - ${verdict.why}` : ''}` }
}

// ---------- вход ----------

const ctx = { root: '', unit: '', base: '', compile: '' }
phase('Вход')

const [pwd, next] = await run('NextAction', ['pwd', `${NEXT_JAVA} ${REQUESTED}`.trim()])
ctx.root = lines(pwd.output)[0]
const action = (next.output.match(/ДЕЙСТВИЕ:\s*(.*)/) || [])[1] || ''
const why = (next.output.match(/ПОЧЕМУ:\s*(.*)/) || [])[1] || ''
log(`ДЕЙСТВИЕ: ${action}`)
const picked = action.match(/^migration-step (M-\d+)$/)
if (!picked) {
  return { status: 'stopped', reason: `NextAction: ${action} - ${why}`, next: action === 'агенты установлены'
    ? 'Перезапустите GigaCode и запустите workflow снова'
    : 'Это действие - не юнит: продолжите через /orchestrator' }
}
ctx.unit = picked[1]

const start = await manager('start', `Сделай Шаги 1-2 скилла migration-step (\`references/start.md\`) для этого юнита: ворота, карточка,
git и ветка миграции, \`status: in-progress\` в карточке и в таблице карты. Юнит \`tech\` - карточку читай так, как в
\`references/tech-flow.md\`, п.1. Подшаги НЕ выполняй. Ворота не пройдены или работать нельзя -> ok: false, причина - в stop_reason.
Верни тип юнита, команду компиляции из паспорта карты и таблицу «Подшаги» карточки.`, START, 'вход в юнит')
if (!start || !start.ok) {
  return { status: 'stopped', unit: ctx.unit, reason: start ? start.stop_reason : 'менеджер не ответил по схеме' }
}
if (start.type === 'markup') {
  return { status: 'stopped', unit: ctx.unit, reason: 'юнит markup делает агент pvatf-marker по references/markup.md: запустите /orchestrator Продолжи миграцию' }
}
ctx.compile = start.compile
let steps = start.steps.length ? start.steps : [{ id: '', kind: start.type, title: '', status: 'todo' }]
const doneNow = []
const human = []

// ---------- подшаги ----------

phase('Подшаги')

for (let guard = 0; guard < MAX_STEPS; guard++) {
  const step = steps.find(s => s.status !== 'done')
  if (!step) break
  const sid = step.id
  log(`подшаг ${stepTitle(step)}`)

  // разбор и review менеджер делает сам (manager.md, «Цикл подшага»)
  if (step.kind === 'разбор') {
    const closed = await manager('razbor', `Подшаг: ${stepTitle(step)}
Выполни подшаг \`разбор\` сам, по \`references/tech-flow.md\`, «Подшаг \`разбор\`», и закрой его по tech-flow.md, п.4.
Верни таблицу «Подшаги» после него и реши по tech-flow.md, п.5, идти ли дальше.`, CLOSE, `разбор ${sid}`)
    if (!closed || !closed.ok) return { status: 'stopped', unit: ctx.unit, step: sid, reason: closed ? closed.stop_reason : 'нет ответа менеджера' }
    steps = closed.steps; doneNow.push(sid)
    if (!closed.continue) return { status: 'paused', unit: ctx.unit, done: doneNow, reason: closed.continue_reason }
    continue
  }
  if (step.kind === 'review') {
    const prepared = await manager('review-prepare', `Подшаг: ${stepTitle(step)}
Выполни подшаг \`review\` по \`references/review-subagent.md\`, «Порядок работы», ТОЛЬКО п.1 (механическая проверка и нить) и подготовь п.2:
раздели файлы на группы не больше 8 и для каждой группы заполни «Промпт сабагенту ревью» дословно. Сабагентов не запускай - их запустит workflow.`,
      REVIEW, `review ${sid}: подготовка`)
    if (!prepared || !prepared.ok) return { status: 'stopped', unit: ctx.unit, step: sid, reason: prepared ? prepared.stop_reason : 'нет ответа менеджера' }
    const answers = await parallel(prepared.prompts.map((p, i) => () => agent(p, { label: `ревью: группа ${i + 1}` })))
    const closed = await manager('review-apply', `Подшаг: ${stepTitle(step)}
Сабагенты ревью ответили. Сделай п.3-6 \`references/review-subagent.md\` (отчёт, исправление, проверка) и закрой подшаг по tech-flow.md, п.4.
Верни таблицу «Подшаги» после этого и реши по tech-flow.md, п.5, идти ли дальше.
Механическая проверка (п.1):
${prepared.mechanical}
${answers.map((a, i) => `Ответ сабагента ${i + 1}:\n${a === null ? 'сабагент не ответил - пройди чек-лист по его группе сам' : a}`).join('\n\n')}`,
      CLOSE, `review ${sid}: исправление`)
    if (!closed || !closed.ok) return { status: 'stopped', unit: ctx.unit, step: sid, reason: closed ? closed.stop_reason : 'нет ответа менеджера' }
    steps = closed.steps; doneNow.push(sid)
    if (!closed.continue) return { status: 'paused', unit: ctx.unit, done: doneNow, reason: closed.continue_reason }
    continue
  }

  // остальные подшаги: пакет -> исполнитель -> проверки -> повторы
  const prep = await manager('prepare', `Подшаг: ${stepTitle(step)}
Подготовь пакет подшага по \`references/manager.md\`, «Цикл подшага», п.1-2: \`Unit.java recite\` и \`Unit.java rules\` для этого
подшага, статус подшага \`in-progress\`, документация (п.2), «Таблица подтверждений» в карточке. Потом заполни задание агенту
\`pvatf-executor\` по разделу «Задание агенту \`pvatf-executor\`» того же файла - все строки. Исполнителя НЕ запускай.`,
    PREP, `пакет ${sid}`)
  if (!prep || !prep.ok) return { status: 'stopped', unit: ctx.unit, step: sid, reason: prep ? prep.stop_reason : 'нет ответа менеджера' }

  const [base] = await run(`база ${sid}`, ['git rev-parse HEAD'])
  ctx.base = lines(base.output)[0]
  const target = sid ? `${ctx.unit} ${sid}` : ctx.unit
  const rules = [...new Set([...(prep.rules || []).filter(r => /^MR-[0-9H]+$/.test(r)), 'ИТОГ'])]

  let report = ''
  let findings = []
  let compiled = false
  let summary = ''
  let attempt = 0
  for (; attempt <= REPEATS; attempt++) {
    const task = attempt === 0 ? prep.package
      : `${prep.package}\n\nПодшаг уже начат. Исправь ТОЛЬКО это, остальное не трогай:\n${findings.map(f => `- ${f}`).join('\n')}`
    report = String(await agent(task, { agentType: 'pvatf-executor', label: `исполнитель ${sid}${attempt ? ` (повтор ${attempt})` : ''}` }) || '')
    const status = (report.match(/Статус:\s*(сделан|не сделан[^\n]*)/) || [])[1] || 'не по шаблону'
    log(`исполнитель: ${status}`)

    const [headNow] = await run('HEAD', ['git rev-parse HEAD'])
    if (lines(headNow.output)[0] !== ctx.base) {
      await run('откат коммита исполнителя', [`git reset --soft ${ctx.base}`])   // manager.md, п.4
    }
    const [comp, check, porcelain] = await run(`проверки ${sid}`, [
      ctx.compile,
      `${UNIT_JAVA} check ${target}`,
      "git status --porcelain --untracked-files=all -- . ':(exclude).gigacode'",
    ])
    compiled = comp.exit === 0
    findings = []
    if (!compiled) findings.push(`компиляция не проходит:\n${head(comp.output, 15)}`)
    const mechanical = checkCount(check.output)
    findings.push(...checkFindings(check.output))
    if (mechanical < 0) findings.push(`Unit.java check не дал строку «ИТОГ: находок»: ${head(check.output, 5)}`)

    let judged = { confirmed: [], suspects: 0, unchecked: [] }
    let point = { ok: false, output: 'не запускался' }
    if (compiled && mechanical === 0) {
      const files = changedSources(porcelain.output)
      if (USE_JUDGES && files.length) {
        judged = await judges(rules, files, prep.result)
        findings.push(...judged.confirmed)
      }
      if (USE_CHECKER && files.length) {
        const checker = String(await agent(`Проект: ${ctx.root}\nЧто шаг должен был сделать: ${prep.result}\n`
          + `Чего в коде быть не должно: ${prep.old_code || '-'}\nФайлы шага:\n${files.map(f => `- ${f} - изменён`).join('\n')}`,
          { agentType: 'pvatf-checker', label: `проверяющий ${sid}` }) || '')
        const table = (checker.split('## Находки')[1] || '').split('##')[0]
        findings.push(...lines(table).filter(l => /^\|/.test(l) && !/^\|\s*(Файл|-)/.test(l)).map(l => `проверяющий: ${l}`))
      }
      point = await checkpoint(prep)
      if (!point.ok) findings.push(`чекпоинт не сошёлся: ${point.output}`)
    }
    summary = `компиляция ${compiled ? 'ок' : 'ошибка'}; Unit.java check находок ${mechanical}; `
      + `судьи: правил ${rules.length}, подозрений ${judged.suspects}, подтверждено ${judged.confirmed.length}`
      + `${judged.unchecked.length ? `, не ответили: ${judged.unchecked.join(', ')}` : ''}; чекпоинт: ${point.output}`
    log(summary)
    if (!findings.length) break
  }

  if (!compiled) {
    const blocked = await manager('block-step', `Подшаг: ${stepTitle(step)}
Подшаг не закрыт: проект не компилируется после ${REPEATS} повторов исполнителя. Сделай по \`references/manager.md\`, п.8 (подшаг
\`blocked\`) и \`references/tech-flow.md\`, п.6 (стоп чата: записи в карточку и карту, коммит карты и карточки).
Ошибка компиляции:
${findings[0]}
Последний отчёт исполнителя:
${report}`, CLOSE, `блокер ${sid}`)
    return { status: 'blocked', unit: ctx.unit, step: sid, done: doneNow, reason: blocked && blocked.stop_reason ? blocked.stop_reason : 'проект не компилируется' }
  }

  const leftovers = findings
  if (leftovers.length) human.push(...leftovers.map(f => `${ctx.unit} ${sid}: ${f}`))
  const closed = await manager('close-step', `Подшаг: ${stepTitle(step)}
Закрой подшаг по \`references/manager.md\`, «Цикл подшага», п.9 и \`references/tech-flow.md\`, п.4: «Сделано» подшага, статус \`done\`,
коммит файлов подшага и карточки, хэш - в колонку «Коммит». Проверки уже сделал workflow - сам их не повторяй, запиши их итог.
Отчёт исполнителя:
${report}
Проверки workflow: ${summary}
Строка проверки для «Сделано»: \`проверка: workflow - повторов ${attempt > REPEATS ? REPEATS : attempt}, осталось ${leftovers.length}\`
${leftovers.length ? `Не исправлено за ${REPEATS} повтора - каждую строку впиши во «Входящие» карты как \`решить человеку: <файл>:<строка> - <что>\`:\n${leftovers.map(f => `- ${f}`).join('\n')}` : 'Осталось после повторов: нет'}
Потом реши по tech-flow.md, п.5, идти ли дальше, и верни таблицу «Подшаги».`, CLOSE, `закрытие ${sid}`)
  if (!closed || !closed.ok) return { status: 'stopped', unit: ctx.unit, step: sid, done: doneNow, reason: closed ? closed.stop_reason : 'нет ответа менеджера' }

  // ворота: подшаг закрыт по-настоящему - статус done в карточке, коммит есть, дерево чистое
  const [row, tree, headAfter] = await run(`ворота ${sid}`, [
    sid ? `grep -n "^| ${sid} |" .gigacode/data/migration/units/${ctx.unit}.md` : `grep -n "^status:" .gigacode/data/migration/units/${ctx.unit}.md`,
    "git status --porcelain -- . ':(exclude).gigacode'",
    'git rev-parse HEAD',
  ])
  const rowDone = sid ? (row.output.split('|')[5] || '').trim() === 'done' : true
  const problems = []
  if (!rowDone) problems.push(`в карточке у ${sid} статус не done: ${head(row.output, 1)}`)
  if (lines(tree.output).length) problems.push(`незакоммиченные файлы: ${head(tree.output, 5)}`)
  if (lines(headAfter.output)[0] === ctx.base) problems.push('коммита подшага нет')
  if (problems.length) {
    return { status: 'stopped', unit: ctx.unit, step: sid, done: doneNow, reason: `подшаг не закрыт: ${problems.join('; ')}` }
  }
  doneNow.push(sid || ctx.unit)
  steps = closed.steps.length ? closed.steps : steps.map(s => s === step ? { ...s, status: 'done' } : s)
  if (!closed.continue) return { status: 'paused', unit: ctx.unit, done: doneNow, human, reason: closed.continue_reason }
}

// ---------- конец юнита ----------

phase('Конец юнита')
if (steps.some(s => s.status !== 'done')) {
  return { status: 'stopped', unit: ctx.unit, done: doneNow, human, reason: `подшагов больше ${MAX_STEPS} за запуск - запустите workflow ещё раз` }
}
const end = await manager('close-unit', `Все подшаги done (сделаны в этом запуске: ${doneNow.join(', ') || '-'}).
Выполни «Конец юнита» (\`references/tech-flow.md\`, п.7: чекпоинты юнита), потом \`references/close.md\` (Шаг 7 - запись и коммит,
Шаг 8 - сводка). Юнит без подшагов - сразу close.md. Чекпоинт юнита не сошёлся -> допиши подшаг по tech-flow.md, п.7,
верни ok: true, unit_done: false и таблицу «Подшаги» с новым подшагом.`, UNIT_END, 'закрытие юнита')
if (!end || !end.ok) return { status: 'stopped', unit: ctx.unit, done: doneNow, human, reason: end ? end.stop_reason : 'нет ответа менеджера' }
if (!end.unit_done) {
  // чекпоинт юнита дописал подшаг: следующий запуск продолжит с него (вход берёт первый подшаг не done)
  return { status: 'paused', unit: ctx.unit, done: doneNow, human, reason: 'чекпоинт юнита дописал подшаг - запустите workflow ещё раз, он продолжит с него' }
}
const [card] = await run('ворота юнита', [`grep -n "^status:" .gigacode/data/migration/units/${ctx.unit}.md`])
if (!/status:\s*done/.test(card.output)) {
  return { status: 'stopped', unit: ctx.unit, done: doneNow, human, reason: `менеджер сказал «юнит закрыт», а в карточке ${head(card.output, 1)}` }
}
return { status: 'done', unit: ctx.unit, done: doneNow, human: [...human, ...(end.human || [])], summary: end.summary }
