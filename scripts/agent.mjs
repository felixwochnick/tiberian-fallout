#!/usr/bin/env node
/**
 * Plays the running game from the terminal (an agent like Claude, or by hand): sends one
 * command to the game page open in the browser (dev server only, see
 * server/utils/agent-relay.ts and app/lib/agent/commands.ts) and prints the answer as JSON.
 *
 *   node scripts/agent.mjs help
 *   node scripts/agent.mjs state
 *   node scripts/agent.mjs deploy 1
 *   node scripts/agent.mjs build GAPOWR
 *   node scripts/agent.mjs place                # next to the base
 *   node scripts/agent.mjs move 3,4,5 70 60
 *   node scripts/agent.mjs wait 10              # game seconds, then the state
 *   node scripts/agent.mjs screenshot shot.jpg  # saves the picture
 *
 * Arguments that look like numbers are sent as numbers. AGENT_URL sets the server
 * (default http://localhost:3000).
 */
import { writeFileSync } from 'node:fs'

const base = process.env.AGENT_URL ?? 'http://localhost:3000'
const [cmd = 'help', ...rest] = process.argv.slice(2)

// screenshot takes the file to save to, not an argument for the game
const file = cmd === 'screenshot' ? rest.shift() ?? 'screenshot.jpg' : undefined
const args = rest.map(arg => (arg !== '' && !Number.isNaN(Number(arg)) ? Number(arg) : arg === 'true' ? true : arg === 'false' ? false : arg))

let answer
try {
  const response = await fetch(`${base}/api/agent/command`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ cmd, args }),
  })
  answer = response.ok ? await response.json() : { ok: false, error: `${response.status} ${response.statusText}` }
}
catch (error) {
  answer = { ok: false, error: `Server nicht erreichbar (${base}): ${error.message}; läuft \`pnpm dev\`?` }
}

if (answer.ok && file && answer.result?.image) {
  writeFileSync(file, Buffer.from(answer.result.image.split(',')[1], 'base64'))
  answer.result = { saved: file }
}
if (answer.ok && cmd === 'map' && answer.result?.rows) {
  const { x0, rows } = answer.result
  console.log(`x ab ${x0} →  . frei  # blockiert/Hang  g/b Tiberium  S/X Gebäude eigen/Feind  u/x Einheit eigen/Feind`)
  console.log(rows.join('\n'))
}
else console.log(JSON.stringify(answer.ok ? answer.result : { error: answer.error }, null, 1))
process.exit(answer.ok ? 0 : 1)
