import { nextCommand } from '../../utils/agent-relay'

/** The game page asks for the next command of the agent (long polling; 204 if none came). Development only. */
export default defineEventHandler(async (event) => {
  if (!import.meta.dev) throw createError({ statusCode: 404 })
  const controller = new AbortController()
  event.node.res.on('close', () => controller.abort())
  const command = await nextCommand(20_000, controller.signal)
  if (!command) {
    setResponseStatus(event, 204)
    return null
  }
  return command
})
