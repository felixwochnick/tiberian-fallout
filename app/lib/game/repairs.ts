import * as THREE from 'three'
import type { Battlefield } from './battlefield'
import type { Upkeep } from './cameos'

/**
 * Buildings repaired with the sidebar's repair button, like in Tiberian Sun: every
 * RepairRate= a building gets RepairStep= hit points back, sparks flying from welding,
 * and each step costs its share of RepairPercent= of the building's cost. The repair
 * stops when the building is whole, when the money runs out, or when the player clicks
 * it again. A building under repair has `userData.repairing` (a wrench blinks over it).
 */
export interface RepairRules {
  upkeep: Upkeep
  /** Strength= and Cost= of a building */
  info: (object: THREE.Object3D) => { strength: number, cost: number } | undefined
  /** Takes whole credits; false if there are not that many */
  pay: (credits: number) => boolean
  /** A repair stopped because the money ran out */
  broke: (object: THREE.Object3D) => void
}

interface Repair {
  /** Seconds until the next step */
  timer: number
  /** Credits owed for the steps so far, not paid yet (only whole credits are taken) */
  owed: number
}

export class Repairs {
  private readonly repairs = new Map<THREE.Object3D, Repair>()

  constructor(private readonly battlefield: Battlefield, private readonly rules: () => RepairRules) {}

  /** Whether a building has lost hit points */
  damaged(object: THREE.Object3D) {
    const strength = this.rules().info(object)?.strength
    return !!strength && (object.userData.hp ?? strength) < strength
  }

  /** Starts repairing a building, or stops it if it is being repaired. Returns whether it is repaired now. */
  toggle(object: THREE.Object3D) {
    if (this.repairs.has(object)) {
      this.stop(object)
      return false
    }
    this.repairs.set(object, { timer: 0, owed: 0 })
    object.userData.repairing = true
    return true
  }

  update(seconds: number) {
    const rules = this.rules()
    for (const [object, repair] of this.repairs) {
      const info = rules.info(object)
      if (object.userData.dead || !info) {
        this.stop(object)
        continue
      }
      repair.timer -= seconds
      if (repair.timer > 0) continue
      repair.timer += rules.upkeep.repairSeconds
      const hp = (object.userData.hp as number | undefined) ?? info.strength
      if (hp >= info.strength) {
        this.stop(object)
        continue
      }
      const step = Math.min(rules.upkeep.repairStep, info.strength - hp)
      repair.owed += info.cost * rules.upkeep.repairCost * step / info.strength
      const credits = Math.floor(repair.owed)
      if (credits > 0 && !rules.pay(credits)) {
        this.stop(object)
        rules.broke(object)
        continue
      }
      repair.owed -= credits
      object.userData.hp = hp + step
      object.userData.health = (hp + step) / info.strength
      this.sparks(object)
    }
  }

  /** Welding somewhere on the building's roof */
  private sparks(object: THREE.Object3D) {
    const footprint = object.userData.footprint as { x: number, z: number, w: number, h: number } | undefined
    if (!footprint) return
    const top = new THREE.Box3().setFromObject(object).max.y
    const at = new THREE.Vector3(
      footprint.x + footprint.w * (0.25 + Math.random() * 0.5),
      top * (0.5 + Math.random() * 0.4),
      footprint.z + footprint.h * (0.25 + Math.random() * 0.5),
    )
    this.battlefield.effects.weld(at)
  }

  private stop(object: THREE.Object3D) {
    this.repairs.delete(object)
    object.userData.repairing = undefined
  }

  dispose() {
    for (const object of [...this.repairs.keys()]) this.stop(object)
  }
}
