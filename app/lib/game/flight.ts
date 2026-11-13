import * as THREE from 'three'
import type { Unit } from './unit'

/**
 * Units in the air, like in Tiberian Sun: aircraft (the Orca, the Harpy) and the
 * jumpjet infantry. They fly straight to where they are sent, high over buildings and
 * cliffs, rising first (clip "TakeOff") and coming down where they stop ("Land").
 *
 * Aircraft carry Ammo= shots. Only once these are spent do they fly to a helipad of
 * their side by themselves to reload: a free one (a pad is kept for the aircraft that
 * stands on it or flies to it), else they land by the nearest one and wait there until
 * one comes free. With shots left, an aircraft whose work is done (its target gone, or
 * there where it was sent) lands where it is: on flat free ground, not on a slope, a
 * ramp or a building; with no such place near by it stays in the air. Sent onto a
 * helipad, a group of aircraft takes it and the free pads nearest to it; those left
 * over land by it and wait. Jumpjets land where they are sent.
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
/** How far round itself (cells) an aircraft looks for a place to land */
const LAND_REACH = 2
/** How far round a helipad (cells) an aircraft waiting for it looks for a place to land */
const WAIT_REACH = 4
/** Steps (cells) between the places it tries, outwards in rings */
const SPOT_STEP = 0.5
/** How far apart (cells) units of the air stand on the ground */
const CLEARANCE = 0.95
/** Game seconds between looks for a free helipad or a place to land */
const LOOK_SECONDS = 0.5

type Phase = 'landed' | 'rising' | 'flying' | 'sinking'

interface Flyer {
  unit: Unit
  kind: 'aircraft' | 'jumpjet'
  phase: Phase
  /** Where it flies to (on the ground below), if anywhere */
  to?: THREE.Vector3
  /** It comes down there; else it waits in the air there (an aircraft, ready to fight) */
  land: boolean
  /** The helipad it stands on or flies to: kept for it, no other aircraft takes it meanwhile */
  pad?: THREE.Object3D
  /** It wants a helipad (out of shots, or sent onto one): until it is down on one */
  wants: boolean
  /** The helipad it waits by while none is free */
  by?: THREE.Object3D
  /** Shots it carries (Ammo=), and how many it has left */
  ammo: number
  shots: number
  reload: number
  /** Game seconds until it looks again for a free helipad or a place to land */
  look: number
}

export interface FlightGround {
  heightAt: (x: number, z: number) => number
  /** The helipads of a side that still stand */
  helipads: (owner: string) => THREE.Object3D[]
  /** Whether an aircraft can come down at a point: flat free ground, no slope, building or vehicle there */
  landable: (at: THREE.Vector3) => boolean
}

export class Flight {
  private readonly flyers = new Map<Unit, Flyer>()

  /** It takes off or comes down (for its sounds) */
  sound: (unit: Unit, event: 'takeOff' | 'land') => void = () => {}

  constructor(private readonly ground: FlightGround) {}

  /**
   * An aircraft from a helipad, `ammo` shots on board (0: unlimited, it needs no pad): it
   * stands on that pad, or on a free one of its side; with none free it rises and lands by it
   */
  addAircraft(unit: Unit, home: THREE.Object3D | undefined, ammo: number) {
    const flyer = this.add(unit, 'aircraft')
    flyer.ammo = flyer.shots = ammo
    if (!home) return
    const pad = !ammo ? undefined : this.padFree(home, flyer) ? home : this.freePad(flyer, home.position)
    unit.object.position.copy(Flight.pad(pad ?? home))
    if (pad) this.claim(flyer, pad)
    else this.settle(flyer, Flight.pad(home), WAIT_REACH)
  }

  /** A jumpjet soldier, standing on the ground */
  addJumpjet(unit: Unit) {
    this.add(unit, 'jumpjet')
  }

  private add(unit: Unit, kind: Flyer['kind']) {
    const flyer: Flyer = { unit, kind, phase: 'landed', land: false, wants: false, ammo: 0, shots: 0, reload: 0, look: 0 }
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

  /** Sends it to a point (on the ground below): up, over there; aircraft wait in the air there (to fight), jumpjets come down */
  flyTo(unit: Unit, to: THREE.Vector3) {
    const flyer = this.flyers.get(unit)
    if (!flyer) return
    this.release(flyer)
    flyer.wants = false
    flyer.by = undefined
    flyer.land = false
    flyer.to = to.clone()
  }

  /**
   * Sends aircraft onto a helipad to reload: the first onto it (if it is free), the
   * others onto the free helipads nearest to it; those for which there is none land by
   * it and wait for one to come free
   */
  dock(units: Unit[], helipad: THREE.Object3D) {
    for (const unit of units) {
      const flyer = this.flyers.get(unit)
      if (flyer?.kind !== 'aircraft' || !flyer.ammo) continue
      // already standing on it
      if (flyer.pad === helipad && flyer.phase === 'landed' && !flyer.to) continue
      this.release(flyer)
      flyer.wants = true
      flyer.by = helipad
      this.seek(flyer, true)
    }
  }

  /** Whether it reloads on helipads (an aircraft with Ammo=) */
  reloads(unit: Unit) {
    return !!this.flyers.get(unit)?.ammo
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

  /** May it fire now: aircraft need shots left */
  canFire(unit: Unit) {
    const flyer = this.flyers.get(unit)
    return !flyer?.ammo || flyer.shots > 0
  }

  /** A shot was fired: one less on board; the last one sends it to a helipad */
  fired(unit: Unit) {
    const flyer = this.flyers.get(unit)
    if (!flyer?.ammo) return
    flyer.shots = Math.max(0, flyer.shots - 1)
    if (flyer.shots) return
    flyer.wants = true
    flyer.by = undefined
    this.seek(flyer, true)
  }

  /**
   * An aircraft with nothing more to do (no target, there where it was sent): out of
   * shots it flies to a helipad, else it lands where it is; jumpjets are down already
   */
  done(unit: Unit) {
    const flyer = this.flyers.get(unit)
    if (flyer?.kind !== 'aircraft' || flyer.phase !== 'flying' || flyer.to || flyer.look > 0) return
    if (flyer.ammo && !flyer.shots) flyer.wants = true
    if (flyer.wants) this.seek(flyer, true)
    else {
      flyer.look = LOOK_SECONDS
      this.settle(flyer, unit.object.position, LAND_REACH)
    }
  }

  /**
   * An aircraft on the ground, or on its way down (onto a helipad or a place to land):
   * it waits for orders, it does not go after enemies by itself
   */
  grounded(unit: Unit) {
    const flyer = this.flyers.get(unit)
    return flyer?.kind === 'aircraft' && (flyer.phase === 'landed' || flyer.phase === 'sinking' || flyer.land || flyer.wants)
  }

  /** Shots it has left and carries, for its pips */
  ammoOf(unit: Unit) {
    const flyer = this.flyers.get(unit)
    return flyer?.ammo ? { shots: flyer.shots, ammo: flyer.ammo } : undefined
  }

  /** Whether a helipad is free for this aircraft: nobody else stands on it or flies to it */
  private padFree(helipad: THREE.Object3D, flyer: Flyer) {
    const holder = helipad.userData.aircraft as Unit | undefined
    return !helipad.userData.dead && (!holder || holder === flyer.unit || !this.flyers.has(holder))
  }

  /** The free helipad of its side nearest to a point, if any */
  private freePad(flyer: Flyer, near: THREE.Vector3) {
    return this.nearest(this.helipadsOf(flyer).filter(p => this.padFree(p, flyer)), near)
  }

  private helipadsOf(flyer: Flyer) {
    return this.ground.helipads((flyer.unit.object.userData.owner as string | undefined) ?? 'player')
  }

  private nearest(helipads: THREE.Object3D[], near: THREE.Vector3) {
    let best: THREE.Object3D | undefined
    let distance = Infinity
    for (const helipad of helipads) {
      const d = Math.hypot(helipad.position.x - near.x, helipad.position.z - near.z)
      if (d < distance) {
        best = helipad
        distance = d
      }
    }
    return best
  }

  /** It takes a helipad for itself (and gives up the one it had) */
  private claim(flyer: Flyer, helipad: THREE.Object3D) {
    if (flyer.pad !== helipad) this.release(flyer)
    flyer.pad = helipad
    helipad.userData.aircraft = flyer.unit
  }

  /** It gives up its helipad: another aircraft may take it */
  private release(flyer: Flyer) {
    if (flyer.pad?.userData.aircraft === flyer.unit) flyer.pad.userData.aircraft = undefined
    flyer.pad = undefined
  }

  /**
   * An aircraft that wants a helipad: onto a free one (the nearest to the one it waits
   * by), else down by the nearest one (or where it is, if there is none) to wait.
   * `fresh`: it has just come to want one (else it only looks for a free one again, and
   * for a place by the helipad if it has none yet)
   */
  private seek(flyer: Flyer, fresh: boolean) {
    flyer.look = LOOK_SECONDS
    const position = flyer.unit.object.position
    const by = flyer.by && !flyer.by.userData.dead ? flyer.by : this.nearest(this.helipadsOf(flyer), position)
    const pad = this.freePad(flyer, (by ?? flyer.unit.object).position)
    if (pad) {
      this.claim(flyer, pad)
      flyer.by = undefined
      flyer.to = Flight.pad(pad)
      flyer.land = true
      return
    }
    // waiting already, or on its way to its place
    if (!fresh && by === flyer.by && (flyer.to || flyer.phase === 'landed' || flyer.phase === 'sinking')) return
    flyer.by = by
    if (this.settle(flyer, by ? Flight.pad(by) : position, by ? WAIT_REACH : LAND_REACH) || !by) return
    // no room by the helipad: it waits over it, a bit off
    const off = new THREE.Vector3(position.x - by.position.x, 0, position.z - by.position.z)
    if (off.lengthSq() < 1e-6) off.set(1, 0, 0)
    flyer.to = Flight.pad(by).addScaledVector(off.normalize(), 1.5)
  }

  /**
   * Down at the place nearest to `near` (within `reach` cells) where it can land; with
   * none it stays where it is (in the air). Returns whether it found one.
   */
  private settle(flyer: Flyer, near: THREE.Vector3, reach: number) {
    const spot = this.spot(flyer, near, reach)
    flyer.to = spot
    flyer.land = !!spot
    return !!spot
  }

  /**
   * Where an aircraft can come down at or round `near`: flat free ground (see
   * FlightGround.landable), not too close to other units of the air on the ground or on
   * their way down. Rings of places outwards, half a cell apart; in the first ring with
   * room the place nearest to the aircraft.
   */
  private spot(flyer: Flyer, near: THREE.Vector3, reach: number) {
    const from = flyer.unit.object.position
    for (let r = 0; r <= reach + 1e-6; r += SPOT_STEP) {
      const count = r ? Math.ceil((2 * Math.PI * r) / SPOT_STEP) : 1
      let best: THREE.Vector3 | undefined
      for (let i = 0; i < count; i++) {
        const angle = (i / count) * 2 * Math.PI
        const at = new THREE.Vector3(near.x + r * Math.sin(angle), 0, near.z + r * Math.cos(angle))
        if (best && Math.hypot(at.x - from.x, at.z - from.z) >= Math.hypot(best.x - from.x, best.z - from.z)) continue
        if (this.ground.landable(at) && !this.crowded(flyer, at)) best = at
      }
      if (best) return best.setY(this.ground.heightAt(best.x, best.z))
    }
  }

  /** Whether another unit of the air stands at a point, comes down there or is about to */
  private crowded(flyer: Flyer, at: THREE.Vector3) {
    for (const other of this.flyers.values()) {
      if (other === flyer || other.unit.object.userData.dead) continue
      const down = other.phase === 'landed' || other.phase === 'sinking' ? other.unit.object.position : undefined
      const landing = other.land ? other.to : undefined
      for (const p of [down, landing]) {
        if (p && Math.hypot(p.x - at.x, p.z - at.z) < CLEARANCE) return true
      }
    }
    return false
  }

  update(seconds: number) {
    for (const flyer of [...this.flyers.values()]) {
      const { unit } = flyer
      const object = unit.object
      if (object.userData.dead) {
        this.release(flyer)
        this.flyers.delete(unit)
        continue
      }
      flyer.look = Math.max(0, flyer.look - seconds)
      // its helipad is gone: on its way to it (or out of shots on it) it looks for another one
      if (flyer.pad?.userData.dead) {
        this.release(flyer)
        if (flyer.wants || (flyer.ammo && !flyer.shots)) {
          flyer.wants = true
          this.seek(flyer, true)
        }
      }
      // waiting for a helipad: is one free now?
      if (flyer.wants && !flyer.pad && !flyer.look) this.seek(flyer, false)
      const position = object.position
      const floor = this.ground.heightAt(position.x, position.z)
      const cruise = floor + HEIGHT[flyer.kind]
      const there = !flyer.to || Math.hypot(flyer.to.x - position.x, flyer.to.z - position.z) < 0.05
      switch (flyer.phase) {
        case 'landed':
          position.y = floor
          // reloading on its pad
          if (flyer.ammo && flyer.shots < flyer.ammo && flyer.pad && Flight.near(position, Flight.pad(flyer.pad))) {
            flyer.reload += seconds
            if (flyer.reload >= RELOAD_SECONDS) {
              flyer.reload = 0
              flyer.shots++
            }
          }
          if (there) {
            flyer.to = undefined
            flyer.land = false
            // down on its helipad: it has what it wanted
            if (flyer.pad && Flight.near(position, Flight.pad(flyer.pad))) {
              flyer.wants = false
              flyer.by = undefined
            }
          }
          else {
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
            // aircraft come down onto a helipad or a place to land; elsewhere they wait in the air
            const landing = flyer.kind === 'jumpjet' || flyer.land
            flyer.to = undefined
            flyer.land = false
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
          if (position.y <= floor + 1e-3) flyer.phase = 'landed'
          break
      }
    }
  }

  /** Whether two points are within a few hundredths of a cell (ignoring height) */
  private static near(a: THREE.Vector3, b: THREE.Vector3) {
    return Math.hypot(a.x - b.x, a.z - b.z) < 0.1
  }
}
