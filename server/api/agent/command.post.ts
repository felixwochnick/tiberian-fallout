import { gameLinked, sendToGame } from '../../utils/agent-relay'

/**
 * The agent sends a command to the running game: `{ cmd, args }`; answers with the
 * game's result (`{ ok: true, result }`) once the page has run it. Development only.
 */
export default defineEventHandler(async (event) => {
  if (!import.meta.dev) throw createError({ statusCode: 404 })
  const body = await readBody<{ cmd?: string, args?: unknown[] }>(event)
  if (!body?.cmd) throw createError({ statusCode: 400, statusMessage: 'cmd fehlt' })
  if (!gameLinked()) {
    throw createError({ statusCode: 503, statusMessage: 'Kein Spiel verbunden: im Browser ein Gefecht (/skirmish) oder eine Mission starten' })
  }
  try {
    // waiting in the game takes as long as it was asked to
    const wait = body.cmd === 'wait' ? Number(body.args?.[0]) || 0 : 0
    return { ok: true, result: await sendToGame(body.cmd, body.args ?? [], 20_000 + wait * 1000 * 3) }
  }
  catch (error) {
    return { ok: false, error: (error as Error).message }
  }
})
