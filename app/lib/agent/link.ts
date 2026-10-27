/**
 * The game page's end of the agent relay (server/utils/agent-relay.ts): fetches the
 * agent's commands by long polling, runs them with `commands` and posts the results
 * back. Development only; returns the function that disconnects again.
 */

export type AgentHandler = (...args: never[]) => unknown
export type AgentCommands = Record<string, AgentHandler>

/** Pause after a failed request (dev server restarting …) */
const RETRY_MS = 2000

export function linkAgent(commands: AgentCommands) {
  const controller = new AbortController()
  const { signal } = controller

  async function run(cmd: string, args: unknown[]) {
    const handler = Object.hasOwn(commands, cmd) ? commands[cmd] : undefined
    if (!handler) throw new Error(`Unbekannter Befehl "${cmd}", verfügbar: ${Object.keys(commands).join(', ')}`)
    return await (handler as (...a: unknown[]) => unknown)(...args)
  }

  async function loop() {
    while (!signal.aborted) {
      try {
        const response = await fetch('/api/agent/poll', { signal })
        if (response.status !== 200) {
          if (!response.ok) await new Promise(resolve => setTimeout(resolve, RETRY_MS))
          continue
        }
        const { id, cmd, args } = await response.json() as { id: number, cmd: string, args: unknown[] }
        let answer: { id: number, result?: unknown, error?: string }
        try {
          answer = { id, result: await run(cmd, args) ?? null }
        }
        catch (error) {
          answer = { id, error: (error as Error).message ?? String(error) }
        }
        await fetch('/api/agent/result', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(answer),
          signal,
        })
      }
      catch {
        if (!signal.aborted) await new Promise(resolve => setTimeout(resolve, RETRY_MS))
      }
    }
  }
  loop()
  return () => controller.abort()
}
