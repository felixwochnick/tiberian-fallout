import { GAME_DISCS } from '#shared/game-discs'

/**
 * Pass-through proxy for the freeware CD images. The mirror does not send
 * CORS headers, so the browser cannot fetch it directly. Only the fixed
 * URLs from GAME_DISCS are reachable; nothing is stored on the server.
 */
export default defineEventHandler(async (event) => {
  const disc = GAME_DISCS.find(d => d.id === getRouterParam(event, 'disc'))
  if (!disc) throw createError({ statusCode: 404, statusMessage: 'Unknown disc' })

  const range = getRequestHeader(event, 'range')
  // Stop pulling from the mirror when the browser cancels the download
  const controller = new AbortController()
  event.node.res.on('close', () => controller.abort())

  const upstream = await fetch(disc.url, { headers: range ? { range } : {}, signal: controller.signal })
  if (!upstream.ok || !upstream.body) {
    throw createError({ statusCode: 502, statusMessage: `Mirror responded with ${upstream.status}` })
  }

  setResponseStatus(event, upstream.status)
  for (const header of ['content-length', 'content-range', 'accept-ranges', 'content-type']) {
    const value = upstream.headers.get(header)
    if (value) setResponseHeader(event, header, value)
  }
  return upstream.body
})
