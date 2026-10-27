import * as THREE from 'three'
import type { Unit } from './unit'

/**
 * Units in the air, like in Tiberian Sun: aircraft (the Orca, the Harpy) and the
 * jumpjet infantry. They fly straight to where they are sent, high over buildings and
 * cliffs, rising first (clip "TakeOff") and coming down where they stop ("Land").
 * Aircraft belong to a helipad (their home): they stand on its Pad when idle, carry
 * Ammo= shots and fly back to reload there once these are spent. Jumpjets land where
 * they are sent.
 *
 * While up, the unit is in the posture "Fly" (its Fly clip loops, "FireFly" is its shot,
 * see Unit.change); the battlefield leaves its height to the flight (userData.offGround). userData.air marks it as a target
 * only weapons that hit the air can hit (AA=, see Combat).
 */

/** Cruising height over the ground, cells: aircraft and jumpjets */
const HEIGHT = { aircraft: 1.6, jumpjet: 0.9 }
/** Cells per game second climbing or sinking */
const CLIMB = 1.2
/** Game seconds on the pad for one shot to come back */
const RELOAD_SECONDS = 1.5
/** How fast it turns in the air (radians per game second) */
const TURN = 3

type Phase = 'landed' | 'rising' | 'flying' | 'sinking'

interface Flyer {
  unit: Unit
  kind: 'aircraft' | 'jumpjet'
  phase: Phase
  /** Where it flies to (on the ground below), if anywhere */
  to?: THREE.Vector3
  /** Its helipad (aircraft) */
  home?: THREE.Object3D
  /** Going home to reload */
  returning: boolean
  /** Shots it carries (Ammo=), and how many it has left */
  ammo: number
  shots: number
  reload: number
}

export interface FlightGround {
  heightAt: (x: number, z: number) => number
}

export class Flight {
  private readonly flyers = new Map<Unit, Flyer>()

  /** It takes off or comes down (for its sounds) */
  sound: (unit: Unit, event: 'takeOff' | 'land') => void = () => {}

  constructor(private readonly ground: FlightGround) {}

  /** An aircraft of a helipad: it stands on the pad, `ammo` shots on board (0: unlimited) */
  addAircraft(unit: Unit, home: THREE.Object3D | undefined, ammo: number) {
    const flyer = this.add(unit, 'aircraft')
    flyer.home = home
    flyer.ammo = flyer.shots = ammo
    if (home) {
      home.userData.aircraft = unit
      unit.object.position.copy(Flight.pad(home))
    }
  }

  /** A jumpjet soldier, standing on the ground */
  addJumpjet(unit: Unit) {
    this.add(unit, 'jumpjet')
  }

  private add(unit: Unit, kind: Flyer['kind']) {
    const flyer: Flyer = { unit, kind, phase: 'landed', returning: false, ammo: 0, shots: 0, reload: 0 }
    unit.object.userData.offGround = true
    unit.object.userData.flyer = kind
    this.flyers.set(unit, flyer)
    return flyer
  }

  /** Whether a unit is one of these (it flies instead of walking) */
  has(unit: Unit) {
    return this.flyers.has(unit)
  }

  /** Where an aircraft stands on a helipad: its Pad node, else the pad's middle */
  static pad(home: THREE.Object3D) {
    home.updateMatrixWorld(true)
    return home.getObjectByName('Pad')?.getWorldPosition(new THREE.Vector3()) ?? home.position.clone()
  }

  /** Sends it to a point (on the ground below): up, over there, down (aircraft over their target stay up while fighting) */
  flyTo(unit: Unit, to: THREE.Vector3) {
    const flyer = this.flyers.get(unit)
    if (!flyer) return
    flyer.returning = false
    flyer.to = to.clone()
  }

  /** It is in the air (not on the ground or a pad) */
  airborne(unit: Unit) {
    const flyer = this.flyers.get(unit)
    return !!flyer && flyer.phase !== 'landed'
  }

  /** It is on its way somewhere (not hovering, not on the ground) */
  travelling(unit: Unit) {
    const flyer = this.flyers.get(unit)
    return !!flyer && (!!flyer.to || flyer.phase === 'rising')
  }

  /** May it fire now: aircraft need shots left (and fly home when they run out) */
  canFire(unit: Unit) {
    const flyer = this.flyers.get(unit)
    if (!flyer || !flyer.ammo) return true
    return flyer.shots > 0 && !flyer.returning
  }

  /** A shot was fired: one less on board; the last one sends it home */
  fired(unit: Unit) {
    const flyer = this.flyers.get(unit)
    if (!flyer?.ammo) return
    flyer.shots = Math.max(0, flyer.shots - 1)
    if (!flyer.shots) this.goHome(flyer)
  }

  private goHome(flyer: Flyer) {
    if (!flyer.home || flyer.home.userData.dead) {
      flyer.to = undefined
      return
    }
    flyer.returning = true
    flyer.to = Flight.pad(flyer.home)
  }

  /**
   * An aircraft with nothing more to do (its target gone) flies home and lands on its
   * pad, like in the original; jumpjets stay where they are
   */
  done(unit: Unit) {
    const flyer = this.flyers.get(unit)
    if (flyer?.kind === 'aircraft' && flyer.phase !== 'landed' && !flyer.to) this.goHome(flyer)
  }

  /** An aircraft standing on the ground: it waits for orders, it does not go after enemies by itself */
  grounded(unit: Unit) {
    const flyer = this.flyers.get(unit)
    return flyer?.kind === 'aircraft' && flyer.phase === 'landed'
  }

  /** Shots it has left and carries, for its pips */
  ammoOf(unit: Unit) {
    const flyer = this.flyers.get(unit)
    return flyer?.ammo ? { shots: flyer.shots, ammo: flyer.ammo } : undefined
  }

  update(seconds: number) {
    for (const flyer of [...this.flyers.values()]) {
      const { unit } = flyer
      const object = unit.object
      if (object.userData.dead) {
        if (flyer.home?.userData.aircraft === unit) flyer.home.userData.aircraft = undefined
        this.flyers.delete(unit)
        continue
      }
      const position = object.position
      const floor = this.ground.heightAt(position.x, position.z)
      const cruise = floor + HEIGHT[flyer.kind]
      const there = !flyer.to || Math.hypot(flyer.to.x - position.x, flyer.to.z - position.z) < 0.05
      switch (flyer.phase) {
        case 'landed':
          position.y = floor
          // reloading on its pad
          if (flyer.ammo && flyer.shots < flyer.ammo && flyer.home && Flight.near(position, Flight.pad(flyer.home))) {
            flyer.reload += seconds
            if (flyer.reload >= RELOAD_SECONDS) {
              flyer.reload = 0
              flyer.shots++
            }
          }
          if (!there) {
            flyer.phase = 'rising'
            this.sound(unit, 'takeOff')
            void unit.change('TakeOff', 'Fly')
          }
          break
        case 'rising':
          position.y = Math.min(cruise, position.y + CLIMB * seconds)
          if (position.y >= cruise - 1e-3) flyer.phase = 'flying'
          break
        case 'flying': {
          position.y = THREE.MathUtils.lerp(position.y, cruise, Math.min(1, seconds * 3))
          if (there) {
            // aircraft come down only at home; elsewhere they wait in the air
            const landing = flyer.kind === 'jumpjet' || flyer.returning
            flyer.to = undefined
            flyer.returning = false
            if (landing) {
              flyer.phase = 'sinking'
              this.sound(unit, 'land')
              void unit.change('Land', undefined)
            }
            break
          }
          const to = flyer.to!
          const way = new THREE.Vector3(to.x - position.x, 0, to.z - position.z)
          const distance = way.length()
          const step = Math.min(distance, unit.speed * seconds)
          position.addScaledVector(way, step / distance)
          // turning towards where it flies
          const heading = Math.atan2(way.x, way.z)
          const turn = THREE.MathUtils.euclideanModulo(heading - object.rotation.y + Math.PI, 2 * Math.PI) - Math.PI
          object.rotation.y += THREE.MathUtils.clamp(turn, -TURN * seconds, TURN * seconds)
          break
        }
        case 'sinking':
          position.y = Math.max(floor, position.y - CLIMB * seconds)
          if (position.y <= floor + 1e-3) {
            flyer.phase = 'landed'
            flyer.to = undefined
          }
          break
      }
    }
  }

  /** Whether two points are within a few hundredths of a cell (ignoring height) */
  private static near(a: THREE.Vector3, b: THREE.Vector3) {
    return Math.hypot(a.x - b.x, a.z - b.z) < 0.1
  }
}
