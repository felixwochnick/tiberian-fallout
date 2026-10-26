import type * as THREE from 'three'
import type { Battlefield } from './battlefield'
import type { Combat } from './combat'
import type { Side } from './models'

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
  addUnit: (id: string, at: THREE.Vector3, colour?: number, owner?: 'player' | 'enemy', side?: Side) => Promise<THREE.Object3D>
  /**
   * A dropship flies in from the map edge and brings the player units (soldiers, an MCV)
   * to `at`; `landed` is called when it is down, the promise settles once the last is out
   */
  dropship: (ids: string[], at: THREE.Vector3, landed?: () => void) => Promise<void>
}
