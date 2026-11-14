import type * as THREE from 'three'
import type { Battlefield } from './battlefield'
import type { Combat } from './combat'
import type { Economy } from './economy'
import type { Side } from './models'
import type { Order, OrderResult } from './orders'
import type { Handicap, Owner } from './players'
import type { Observation } from './ai/view'

/** A player with a base on the battlefield: the human player, a computer player */
export interface MatchPlayer {
  /** What their units and buildings carry as owner */
  id: Owner
  colour: number
  side: Side
  economy: Economy
  /** What they play with (a computer player's level), see Handicap */
  handicap: Handicap
  /** Where they started (their MCV): known to all players, like the start positions of the original */
  start?: THREE.Vector3
}

/**
 * What the battlefield view hands to the game mode (skirmish or campaign mission) once
 * the map is ready: the mode decides what stands on it at the start and what happens
 * on it, the view only knows how to put things there.
 */
export interface Field {
  battlefield: Battlefield
  combat: Combat
  /** House colour of the human player */
  colour: number
  /** Puts a structure of the player's base on the map (cells); `built` clicks like a finished building */
  buildStructure: (id: string, x: number, z: number, built?: boolean) => Promise<THREE.Object3D | undefined>
  /** Puts a unit (RULES.INI id) on the map, the player's unless `owner` says otherwise; `side` (default: the player's) sets its look */
  addUnit: (id: string, at: THREE.Vector3, colour?: number, owner?: Owner, side?: Side) => Promise<THREE.Object3D>
  /**
   * A dropship flies in from the map edge and brings the player units (soldiers, an MCV)
   * to `at`; `landed` is called when it is down, the promise settles once the last is out
   */
  dropship: (ids: string[], at: THREE.Vector3, landed?: () => void) => Promise<void>
  /**
   * Another player with a base of their own joins (a computer player): from now on their
   * production runs and their units and buildings belong to `id`
   */
  join: (player: { id: Owner, colour: number, side: Side, credits: number, start?: THREE.Vector3 }) => MatchPlayer
  /** Where the human player started (for the others to know) */
  setStart: (at: THREE.Vector3) => void
  /** Carries out a player's order (only their own units and buildings) */
  order: (owner: Owner, order: Order) => OrderResult
  /** What a player knows of the battlefield now, and how to ask where things fit */
  observe: (owner: Owner) => Observation | undefined
}
