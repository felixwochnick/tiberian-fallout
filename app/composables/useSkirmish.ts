import type { InjectionKey } from 'vue'
import type { BuildInfo, BuildRules } from '~/lib/game/cameos'
import { Production } from '~/lib/game/production'

/**
 * State of a running skirmish, shared by the battlefield, the sidebar and the top bar:
 * money, the player's buildings (and so power and what can be built) and production.
 */
export interface Skirmish {
  credits: { value: number }
  rules?: BuildRules
  /** Buildings on the map (RULES.INI ids) */
  buildings: string[]
  production: Production
  /** A finished structure is being placed on the map */
  placing?: BuildInfo
  /** Units that left their factory, to be put on the map by the battlefield */
  arrivals: BuildInfo[]
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

/** Game speed of the setting (Sehr langsam … Maximal) as a factor */
export const SPEED_FACTORS = [0.5, 0.65, 0.8, 1, 1.25, 1.5, 2]

export function createSkirmish(startCredits: number) {
  const sounds = useUiSounds()
  const state: Skirmish = {
    credits: { value: startCredits },
    rules: undefined,
    buildings: [],
    production: new Production(
      (info) => {
        skirmish.arrivals.push(info)
        sounds.speak('evaUnitReady')
      },
      () => sounds.speak('evaConstructionComplete'),
    ),
    placing: undefined,
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
 * "Battle control online": until EVA has said it, the game waits and the player has
 * no cursor and cannot scroll or click anything (Esc still opens the menu).
 */
export function useBattleControl(skirmish: Skirmish) {
  const sounds = useUiSounds()
  let round = 0
  return {
    async establish() {
      const mine = ++round
      skirmish.control = false
      await sounds.speakNow('evaStartGame')
      if (mine === round) skirmish.control = true
    },
    /** Takes control away (and stops one that is being established) */
    drop() {
      round++
      skirmish.control = false
    },
  }
}

/** Power output and drain of the buildings */
export function basePower(skirmish: Skirmish) {
  let output = 0
  let drain = 0
  for (const id of skirmish.buildings) {
    const power = skirmish.rules?.info.get(id)?.power ?? 0
    if (power > 0) output += power
    else drain -= power
  }
  return { output, drain }
}

/** Production slows down when the base uses more power than it has */
export function powerFactor(skirmish: Skirmish) {
  const { output, drain } = basePower(skirmish)
  return drain > output ? Math.max(0.3, output / drain) : 1
}

/** "1:05" */
export function formatTime(seconds: number) {
  const s = Math.round(seconds)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
