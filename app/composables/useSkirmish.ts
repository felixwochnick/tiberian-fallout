import type { InjectionKey } from 'vue'
import type { BuildInfo } from '~/lib/game/cameos'
import type { Economy } from '~/lib/game/economy'
import type { Side } from '~/lib/game/models'
import { Production } from '~/lib/game/production'

export { basePower, onlineBuildings, powerFactor } from '~/lib/game/economy'

/**
 * State of a running skirmish, shared by the battlefield, the sidebar and the top bar:
 * the human player's economy (money, buildings, production; the computer players have
 * their own, see Economy) and what the HUD shows.
 */
export interface Skirmish extends Economy {
  /** Mode of the sidebar buttons: clicks on the battlefield repair, sell, switch off or set waypoints */
  mode?: BaseMode
  /** A finished structure is being placed on the map */
  placing?: BuildInfo
  /** The player's special weapons, charging or ready (for the sidebar) */
  specials: Special[]
  /** A special weapon waits for the player to pick its target on the map (its id) */
  targeting?: string
  /**
   * Battle control has been established ("Battle control online"): until then the
   * player sees no cursor and can neither scroll nor click anything.
   */
  control: boolean
  /** Mission hints shown under the top bar, newest last */
  hints: Hint[]
  /** A transmission playing in the radar, and what to do when it has ended */
  radarMovie?: { bytes: Uint8Array, done: () => void }
  /** Mission countdown shown in the top bar ("Zeit: 09:34"), in game seconds */
  timer?: { remaining: number, running: boolean, onEnd?: () => void }
}

export type BaseMode = 'repair' | 'sell' | 'power' | 'waypoint'

/** A special weapon in the sidebar */
export interface Special {
  id: string
  name: string
  /** Its cameo (SidebarImage= of the rules) */
  cameo: string
  /** 0 … 1 */
  progress: number
  ready: boolean
  /** The firestorm is on */
  active: boolean
}

export interface Hint {
  id: number
  text: string
  /** Game seconds left until it fades */
  remaining: number
}

/** Seconds a hint stays */
export const HINT_SECONDS = 9
/** Most hints shown at once */
const MAX_HINTS = 3
let hintId = 0

/** Shows a hint under the top bar (with the incoming message sound). */
export function showHint(skirmish: Skirmish, text: string, seconds = HINT_SECONDS) {
  skirmish.hints.push({ id: hintId++, text, remaining: seconds })
  if (skirmish.hints.length > MAX_HINTS) skirmish.hints.splice(0, skirmish.hints.length - MAX_HINTS)
}

/** Lets hints fade and the countdown run; game seconds */
export function tickMissionDisplay(skirmish: Skirmish, seconds: number) {
  for (const hint of skirmish.hints) hint.remaining -= seconds
  if (skirmish.hints.some(h => h.remaining <= 0)) skirmish.hints = skirmish.hints.filter(h => h.remaining > 0)
  const timer = skirmish.timer
  if (timer?.running) {
    timer.remaining = Math.max(0, timer.remaining - seconds)
    if (timer.remaining <= 0) {
      timer.running = false
      timer.onEnd?.()
    }
  }
}

const KEY: InjectionKey<Skirmish> = Symbol('skirmish')

/**
 * Game speed of the setting (Sehr langsam … Maximal) as a factor of the game logic's
 * 15 frames a second, like the original's seven steps (frames a second 10, 12, 15, 20,
 * 30, 45, 60): its default, the fifth step ("Schnell", also ours), runs at 30
 */
export const SPEED_FACTORS = [10, 12, 15, 20, 30, 45, 60].map(fps => fps / 15)

/**
 * The pace of the loops that show nothing of the game's progress (blinking lights,
 * waving flags, the radar dish, the Tiberium trees): the default game speed's, whatever
 * the setting, so a faster game makes the units faster, not the scenery
 */
export const AMBIENT_SPEED = SPEED_FACTORS[DEFAULT_SPEED]!

export function createSkirmish(startCredits: number, side: Side = 'gdi') {
  const sounds = useUiSounds()
  const state: Skirmish = {
    credits: { value: startCredits },
    side,
    rules: undefined,
    buildings: [],
    offline: [],
    mode: undefined,
    production: new Production(
      (info) => {
        skirmish.arrivals.push(info)
        sounds.speak('evaUnitReady')
      },
      () => sounds.speak('evaConstructionComplete'),
    ),
    placing: undefined,
    specials: [],
    targeting: undefined,
    arrivals: [],
    control: false,
    hints: [],
    timer: undefined,
  }
  const skirmish = reactive(state) as Skirmish
  provide(KEY, skirmish)
  return skirmish
}

export function useSkirmish() {
  return inject(KEY)
}

/**
 * "Establishing battlefield control, stand by": EVA says it when control is taken away
 * (a mission starts); until then and until she has said it, the game waits and the
 * player has no cursor and cannot scroll or click anything (Esc still opens the menu).
 */
export function useBattleControl(skirmish: Skirmish) {
  const sounds = useUiSounds()
  let round = 0
  /** What EVA says since control was taken away, if she has said it already */
  let announcement: Promise<void> | undefined
  return {
    /** Gives control (back), once EVA has said it (said now if not when it was taken) */
    async establish() {
      const mine = ++round
      skirmish.control = false
      await (announcement ?? sounds.speakNow('evaStartGame'))
      announcement = undefined
      if (mine === round) skirmish.control = true
    },
    /**
     * Takes control away (and stops one that is being established); with `announce`
     * EVA says right away that it is being handed over.
     */
    drop(announce = false) {
      round++
      skirmish.control = false
      announcement = announce ? sounds.speakNow('evaStartGame') : undefined
    },
  }
}

/** "1:05" */
export function formatTime(seconds: number) {
  const s = Math.round(seconds)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
