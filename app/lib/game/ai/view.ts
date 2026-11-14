import type { Owner } from '../players'
import type { TiberiumPatch } from '../tiberium'

/**
 * What a player knows of the battlefield at one moment, as plain data: their money and
 * production, their own units and buildings, those of the others, the Tiberium. The
 * computer players decide on this alone (see ComputerPlayer) and answer with orders, so
 * they could just as well run where a network match keeps its state (a Colyseus room)
 * as here in the browser. There is no fog of war: every player sees the whole map.
 */
export interface PlayerView {
  /** The player this is for */
  me: Owner
  credits: number
  power: { output: number, drain: number }
  /** RULES.INI ids of their buildings, one per building */
  buildings: string[]
  production: {
    /** The structure being built (or ready to be placed) */
    structure?: { id: string, ready: boolean }
    /** Units queued, the first one in work */
    units: string[]
  }
  /** What they can build now */
  options: BuildChoice[]
  /** Buildings that guns go onto (the component tower): no defence until one is mounted */
  towers: string[]
  /** Their own units and buildings */
  units: SeenUnit[]
  structures: SeenStructure[]
  /** Everyone else's */
  enemies: { units: SeenUnit[], structures: SeenStructure[] }
  tiberium: TiberiumPatch[]
  /** Where every player started (world cells) */
  starts: { owner: Owner, x: number, z: number }[]
  /** Middle of the map */
  centre: { x: number, z: number }
}

/** Something that can be built, with what matters for deciding on it */
export interface BuildChoice {
  id: string
  structure: boolean
  category: 'structure' | 'infantry' | 'vehicle' | 'aircraft'
  cost: number
  power: number
  /** Cells (width along x, depth along z) */
  foundation: [number, number]
  /** How far (cells) from the base it may stand */
  adjacent: number
  /** It fires at enemies of its own accord (a weapon that does damage) */
  armed: boolean
  /** Its weapon reaches aircraft */
  antiAir: boolean
  /** Its weapon reaches the ground */
  antiGround: boolean
  /** An upgrade that goes onto this building (the component tower's guns) */
  powersUp?: string
  /** A wall or gate */
  wall: boolean
}

interface Seen {
  /** Network id: what orders name it by */
  id: number
  /** RULES.INI id */
  type: string
  owner: Owner
  x: number
  z: number
  /** 0 … 1 */
  health: number
}

export interface SeenUnit extends Seen {
  category: 'infantry' | 'vehicle' | 'aircraft'
  harvester: boolean
  /** It is walking (or flying) somewhere */
  moving: boolean
  /** It is fighting, or on an attack-move */
  fighting: boolean
}

export interface SeenStructure extends Seen {
  /** Its foundation (lower corner, size) */
  cells: { x: number, z: number, w: number, h: number }
  repairing: boolean
  /** A wall, a gate or pavement */
  wall: boolean
  /** It fires (its own weapon or a gun mounted on it) */
  armed: boolean
  /** Upgrades can go onto it (a component tower without its gun, a power plant with a free turbine place) */
  freeSlot: boolean
}

/** What a player can ask of the battlefield beyond what they see */
export interface WorldQuery {
  /**
   * Whether a w × h structure fits with its lower corner at (x, z), within `adjacent`
   * cells of their base, with `spacing` cells to their other buildings kept free
   */
  canPlace: (x: number, z: number, w: number, h: number, adjacent: number, spacing?: number) => boolean
  /** Whether an MCV (network id) can unfold where it stands */
  canDeploy: (unit: number) => boolean
  /** The nearest place at or round (x, z) where units can stand */
  openSpot: (x: number, z: number) => { x: number, z: number }
}

export interface Observation {
  view: PlayerView
  query: WorldQuery
}
