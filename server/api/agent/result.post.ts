import { settleCommand } from '../../utils/agent-relay'

/** The game page answers a command: `{ id, result }` or `{ id, error }`. Development only. */
export default defineEventHandler(async (event) => {
  if (!import.meta.dev) throw createError({ statusCode: 404 })
  const body = await readBody<{ id?: number, result?: unknown, error?: string }>(event)
  if (typeof body?.id !== 'number') throw createError({ statusCode: 400, statusMessage: 'id fehlt' })
  settleCommand(body.id, body.result, body.error)
  return { ok: true }
})
