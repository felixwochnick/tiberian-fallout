/**
 * Relay between an agent outside the browser (scripts/agent.mjs, e.g. Claude in a
 * terminal) and the running game: the agent posts a command, the game page fetches
 * it by long polling, runs it and posts the result back, which answers the agent.
 * Only in development; everything is kept in memory.
 */

export interface AgentCommand {
  id: number
  cmd: string
  args: unknown[]
}

interface Pending {
  resolve: (value: unknown) => void
  reject: (error: Error) => void
  timer: ReturnType<typeof setTimeout>
}

interface Relay {
  next: number
  queue: AgentCommand[]
  /** Game pages waiting for a command */
  pollers: ((command?: AgentCommand) => void)[]
  pending: Map<number, Pending>
  /** When a game page last asked for commands (ms) */
  lastPoll: number
}

// kept on globalThis so a reload of this module in the dev server keeps the connection
const relay: Relay = ((globalThis as { __agentRelay?: Relay }).__agentRelay ??= {
  next: 1, queue: [], pollers: [], pending: new Map(), lastPoll: 0,
})

/** A game page is connected (polling now, or did a moment ago) */
export function gameLinked() {
  return relay.pollers.length > 0 || Date.now() - relay.lastPoll < 5000
}

/** Hands a command to the game and resolves with its result; rejects after `timeoutMs`. */
export function sendToGame(cmd: string, args: unknown[], timeoutMs: number) {
  const command: AgentCommand = { id: relay.next++, cmd, args }
  return new Promise<unknown>((resolve, reject) => {
    const timer = setTimeout(() => {
      relay.pending.delete(command.id)
      const i = relay.queue.indexOf(command)
      if (i >= 0) relay.queue.splice(i, 1)
      reject(new Error(`Keine Antwort vom Spiel nach ${timeoutMs / 1000} s`))
    }, timeoutMs)
    relay.pending.set(command.id, { resolve, reject, timer })
    const poller = relay.pollers.shift()
    if (poller) poller(command)
    else relay.queue.push(command)
  })
}

/**
 * The next command for the game page, waiting up to `waitMs` (undefined if none came
 * or the page went away, `signal`).
 */
export function nextCommand(waitMs: number, signal: AbortSignal) {
  relay.lastPoll = Date.now()
  const queued = relay.queue.shift()
  if (queued) return Promise.resolve(queued)
  return new Promise<AgentCommand | undefined>((resolve) => {
    const poller = (command?: AgentCommand) => {
      clearTimeout(timer)
      signal.removeEventListener('abort', leave)
      relay.lastPoll = Date.now()
      resolve(command)
    }
    const leave = () => {
      const i = relay.pollers.indexOf(poller)
      if (i >= 0) relay.pollers.splice(i, 1)
      poller()
    }
    const timer = setTimeout(leave, waitMs)
    signal.addEventListener('abort', leave)
    relay.pollers.push(poller)
  })
}

/** The game page answered a command. */
export function settleCommand(id: number, result: unknown, error?: string) {
  const pending = relay.pending.get(id)
  if (!pending) return
  relay.pending.delete(id)
  clearTimeout(pending.timer)
  if (error) pending.reject(new Error(error))
  else pending.resolve(result)
}
