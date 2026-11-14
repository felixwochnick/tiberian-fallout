/**
 * Player settings shared by the main menu and the in-game menu, stored per browser.
 */

import { DEFAULT_KEYS, type KeyAction } from './useKeys'

const SETTINGS_KEY = 'tiberian-fallout:settings'

export const AI_LEVELS = ['Leicht', 'Normal', 'Schwer']
export const SPEEDS = ['Sehr langsam', 'Langsam', 'Gemächlich', 'Normal', 'Schnell', 'Sehr schnell', 'Maximal']
/** The game speed a new player starts with (index into SPEEDS): "Schnell", like the original */
export const DEFAULT_SPEED = 4
/** Sizes of the mouse cursor: name and scale of the original's pixels */
export const CURSOR_SIZES = [['Klein', 1], ['Mittel', 1.5], ['Groß', 2]] as const

/** House colours of a skirmish like in Tiberian Sun's multiplayer, as name and colour */
export const HOUSE_COLOURS = [
  ['Gold', 0xd8b43a], ['Rot', 0xb3241a], ['Blau', 0x2f5fd0], ['Grün', 0x3a9a3a],
  ['Orange', 0xe07a1a], ['Lila', 0x8a3ab0], ['Türkis', 0x2aa8a8], ['Grau', 0x8a8a8a],
] as const

/** The landscape of a skirmish: Tiberian Sun's two theaters, or one of them at random each game */
export const THEATER_CHOICES = [['temperate', 'Gemäßigt'], ['snow', 'Schnee'], ['random', 'Zufall']] as const
export type TheaterChoice = typeof THEATER_CHOICES[number][0]

/** Most players in a skirmish */
export const MAX_PLAYERS = 8

export interface SkirmishPlayer {
  name: string
  side: 'gdi' | 'nod'
  /** Index into HOUSE_COLOURS */
  colour: number
  /** Computer player's level (index into AI_LEVELS); null for the human player */
  ai: number | null
}

const settings = reactive({
  /** Overall volume (percent): multiplies the four below */
  master: 50,
  music: 100,
  /** Shots, impacts and explosions */
  shots: 100,
  /** Clicks, building, the dropship, the radar and everything else */
  effects: 100,
  /** EVA, the units' responses and death cries */
  voices: 100,
  aiLevel: 1,
  /** Players of a skirmish; the first one is the human player */
  players: [
    { name: 'Spieler', side: 'gdi', colour: 0, ai: null },
    { name: 'Computer 1', side: 'nod', colour: 1, ai: 1 },
  ] as SkirmishPlayer[],
  credits: 10000,
  /** Skirmish: highest tech level that can be built (TechLevel= in RULES.INI, 1 … 10) */
  techLevel: 10,
  /** Skirmish: the radar works from the start, without a radar building */
  radarAlways: false,
  /** Skirmish: the landscape (theater) */
  theater: 'random' as TheaterChoice,
  /** Game speed, index into SPEEDS */
  speed: DEFAULT_SPEED,
  /** Edge scroll speed, index into SPEEDS */
  scrollSpeed: 3,
  /** Size of the mouse cursor, index into CURSOR_SIZES */
  cursorSize: 1,
  /** Full screen with the mouse kept inside the game */
  mouseCapture: true,
  /**
   * Mouse controls: 'classic' like Tiberian Sun (left click selects and gives orders,
   * right click deselects) or 'modern' like later C&C games (left click selects,
   * right click gives orders)
   */
  controls: 'classic' as 'classic' | 'modern',
  /** Keyboard shortcuts (KeyboardEvent.code per action), see useKeys */
  keys: { ...DEFAULT_KEYS } as Record<KeyAction, string>,
})
let loaded = false

export type VolumeKind = 'music' | 'shots' | 'effects' | 'voices'

/** Volume of one kind of sound (0 … 1): its own setting times the overall volume */
export function volumeOf(kind: VolumeKind) {
  const settings = useSettings()
  return (settings.master / 100) * (settings[kind] / 100)
}

export function useSettings() {
  if (!loaded) {
    loaded = true
    try {
      const stored = JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? '{}')
      // new actions get their default key
      Object.assign(settings, stored, { keys: { ...DEFAULT_KEYS, ...stored.keys } })
    }
    catch {}
    watch(settings, () => {
      try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
      }
      catch {}
    })
  }
  return settings
}
