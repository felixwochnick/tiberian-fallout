import * as THREE from 'three'
import { Battlefield } from './battlefield'
import { CARGO_SLOTS, type CargoSlot, cargoFits, cargoFull, cargoNeeds, loadCargo, SLOT_STAGES, type TiberiumCell, type TiberiumKind } from './tiberium'
import type { Unit } from './unit'

/**
 * The harvesters at work, like in Tiberian Sun: a harvester drives to the nearest
 * Tiberium, stops with its collector (in front, over the ground) over a cell and
 * harvests it stage by stage (clip "Harvest", Tiberium dust and smoke flying), then the
 * next cell, until it is full. Its load is five squares (shown at its frame, see
 * Battlefield.drawFrame): a ripe cell fills one, a small (young) cell a third; green
 * and blue Tiberium are never mixed in a square, but the squares may hold different
 * kinds. Then it drives to the nearest refinery of its owner, turns in front of the
 * dock, backs in (the refinery's "Dock" node: where it stands, facing away) and
 * unloads (clip "Unload": the container is swapped). A full load is worth Storage=
 * bales of the Tiberium's Value= (blue more than green). Then it drives out again and
 * goes back to work.
 *
 * A move order of the player takes it off its work until it is there; then it goes
 * on from where it stands (harvesting the nearest Tiberium, or bringing in its load).
 * The player can also send it onto a Tiberium cell (it harvests there) or into a
 * refinery (it unloads there, full or not).
 */

/** The collector's middle: this far in front of the harvester's origin (cells, see blender/HARV.py, scaled by its SCALE) */
const COLLECTOR = 0.56
/** Seconds to harvest one stage of a cell (one bale) */
const HARVEST_SECONDS = 0.5
/** Where a harvester turns before backing into the dock: this far in front of it (cells) */
const DOCK_APPROACH = 1.4
/** Backing in is slower than driving */
const REVERSE_FACTOR = 0.6
/** Share of the Unload clip after which the container is inside the refinery: the load is credited */
const CREDIT_AT = 0.45
/** Seconds a harvester with nothing to do waits before it looks again */
const IDLE_SECONDS = 3
/** Seconds between two puffs of dust from the collector */
const DUST_INTERVAL = 0.04
/** The tips of the two exhaust stacks behind the cab (cells, the harvester's own space; see blender/HARV.py, scaled by its SCALE) */
const EXHAUSTS = [new THREE.Vector3(-0.18, 0.54, 0.19), new THREE.Vector3(0.18, 0.54, 0.19)]
/** How far from a cell the collector may stand and still reach it (cells) */
const REACH = 0.8

type State =
  | 'waiting' // e.g. the new harvester until its refinery has built up
  | 'leaving' // driving out of the dock
  | 'seeking' // looks for Tiberium
  | 'driving' // on its way to a cell
  | 'aiming' // turning the collector towards the cell
  | 'harvesting'
  | 'returning' // looks for a refinery
  | 'approaching' // on its way to the dock
  | 'turning' // in front of the dock, turning its back to it
  | 'docking' // backing in
  | 'unloading'
  | 'ordered' // driving where the player sent it

interface Harvester {
  unit: Unit
  state: State
  /** Tiberium on board, square by square (also userData.cargo of its object, for its frame) */
  cargo: CargoSlot[]
  timer: number
  /** The cell it harvests or drives to */
  cell?: { x: number, z: number, kind?: TiberiumKind }
  /** Cells it could not get at, left out for a while */
  skip: Set<string>
  refinery?: THREE.Object3D
  credited: boolean
  dust: number
}

export interface HarvestingRules {
  /** Bales in a harvester's full load (its Storage=) */
  capacity: (unit: Unit) => number
  /** Credits a bale of the kind is worth (Value= of [Riparius], [Vinifera]) */
  value: (kind: TiberiumKind) => number
  /** The load of a harvester of `owner` comes in */
  earn: (owner: string, credits: number) => void
}

export class Harvesting {
  private readonly harvesters: Harvester[] = []

  constructor(private readonly battlefield: Battlefield, private readonly rules: () => HarvestingRules) {}

  /**
   * A harvester starts work. Standing in `refinery`'s dock (it comes with the
   * refinery) it drives out first, after `wait` seconds.
   */
  add(unit: Unit, refinery?: THREE.Object3D, wait = 0) {
    const harvester: Harvester = { unit, state: 'waiting', cargo: [], timer: wait, skip: new Set(), credited: false, dust: 0 }
    unit.object.userData.cargo = harvester.cargo
    unit.object.userData.harvester = true
    if (refinery) {
      harvester.refinery = refinery
      refinery.userData.dockedBy = harvester
    }
    this.harvesters.push(harvester)
  }

  /** Where a refinery's harvester stands to unload, and the way it faces then (away from the refinery). */
  static dock(refinery: THREE.Object3D) {
    const node = refinery.getObjectByName('Dock')
    if (!node) return { at: refinery.position.clone(), forward: new THREE.Vector3(1, 0, 0) }
    return { at: node.getWorldPosition(new THREE.Vector3()), forward: node.getWorldDirection(new THREE.Vector3()).setY(0).normalize() }
  }

  /** The player sent these units somewhere: harvesters among them leave their work until they are there. */
  order(objects: THREE.Object3D[]) {
    for (const harvester of this.among(objects)) {
      this.takeOff(harvester)
      harvester.state = 'ordered'
    }
  }

  /** The player sent these units onto a Tiberium cell: harvesters among them harvest there, then go on from there. */
  harvest(objects: THREE.Object3D[], cell: TiberiumCell) {
    for (const harvester of this.among(objects)) {
      this.takeOff(harvester)
      harvester.skip.clear()
      harvester.unit.stop()
      this.goTo(harvester, cell)
    }
  }

  /** The player sent these units into a refinery: harvesters among them unload there, full or not. */
  unloadAt(objects: THREE.Object3D[], refinery: THREE.Object3D) {
    for (const harvester of this.among(objects)) {
      this.takeOff(harvester)
      harvester.refinery = refinery
      const { at, forward } = Harvesting.dock(refinery)
      this.battlefield.walk(harvester.unit, at.clone().addScaledVector(forward, DOCK_APPROACH).setY(0))
      harvester.state = 'approaching'
    }
  }

  private among(objects: THREE.Object3D[]) {
    return this.harvesters.filter(harvester => objects.includes(harvester.unit.object))
  }

  /** Off its work: out of the dock it may stand in, down from the refinery's pad */
  private takeOff(h: Harvester) {
    this.release(h)
  }

  update(dt: number) {
    for (const harvester of [...this.harvesters]) {
      if (harvester.unit.object.userData.dead) {
        this.release(harvester)
        this.harvesters.splice(this.harvesters.indexOf(harvester), 1)
        continue
      }
      this.step(harvester, dt)
      this.exhaust(harvester, dt)
    }
  }

  /** Diesel smoke out of the stacks: a little when standing, more when driving, most when harvesting */
  private exhaust(h: Harvester, dt: number) {
    const amount = h.state === 'harvesting' ? 1 : h.unit.walking || h.state === 'leaving' || h.state === 'docking' ? 0.5 : 0.1
    h.unit.object.updateMatrixWorld()
    const puffs = Math.max(1, Math.round(dt * 30))
    for (const stack of EXHAUSTS) {
      const at = h.unit.object.localToWorld(stack.clone())
      for (let i = 0; i < puffs; i++) this.battlefield.effects.exhaust(at, amount)
    }
  }

  private step(h: Harvester, dt: number) {
    const { unit } = h
    const position = unit.object.position
    switch (h.state) {
      case 'waiting':
        h.timer -= dt
        if (h.timer > 0) return
        h.state = h.refinery?.userData.dockedBy === h ? 'leaving' : 'seeking'
        return

      case 'leaving': {
        // straight out of the dock, then off the refinery's foundation
        const refinery = h.refinery
        if (!refinery) {
          h.state = 'seeking'
          return
        }
        const { at, forward } = Harvesting.dock(refinery)
        const out = at.clone().addScaledVector(forward, DOCK_APPROACH)
        out.y = this.battlefield.heightAt(out.x, out.z)
        unit.drive()
        if (this.moveTowards(h, out, unit.speed * dt)) {
          this.release(h)
          unit.rest()
          h.state = cargoFull(h.cargo) ? 'returning' : 'seeking'
        }
        return
      }

      case 'seeking': {
        if (cargoFull(h.cargo)) {
          h.state = 'returning'
          return
        }
        // a part-filled square is filled up with its kind first, if there is any; with
        // no square left, only that kind will do
        const last = h.cargo.at(-1)
        const open = last && last.stages < SLOT_STAGES ? last.kind : undefined
        const cell = (open && this.battlefield.nearestTiberium(position, h.skip, open))
          || (cargoNeeds(h.cargo) ? undefined : this.battlefield.nearestTiberium(position, h.skip))
        if (!cell) {
          // nothing left to harvest: bring in what it has, or wait for the Tiberium to grow
          h.state = h.cargo.length > 0 ? 'returning' : 'waiting'
          h.timer = IDLE_SECONDS
          h.skip.clear()
          return
        }
        this.goTo(h, cell)
        return
      }

      case 'driving':
        if (!unit.walking) h.state = 'aiming'
        return

      case 'aiming': {
        const cell = h.cell!
        const centre = new THREE.Vector3(cell.x + 0.5, 0, cell.z + 0.5)
        if (!unit.face(centre, dt)) return
        // could it get there? (the way may have ended short of the cell)
        if (this.collector(unit).distanceTo(centre) > REACH) {
          h.skip.add(`${cell.x},${cell.z}`)
          h.state = 'seeking'
          return
        }
        h.state = 'harvesting'
        h.timer = HARVEST_SECONDS
        unit.perform('Harvest')
        return
      }

      case 'harvesting': {
        this.dustFrom(h, dt)
        h.timer -= dt
        if (h.timer > 0) return
        h.timer = HARVEST_SECONDS
        const cell = h.cell!
        const kind = cell.kind ?? 'green'
        if (!cargoFits(h.cargo, kind)) h.state = 'seeking'
        else if (this.battlefield.harvestTiberium(cell.x, cell.z)) loadCargo(h.cargo, kind)
        else h.state = 'seeking' // harvested bare: on to the next cell
        // full, or no room for this kind any more (the last square holds the other)
        if (cargoFull(h.cargo)) h.state = 'returning'
        else if (!cargoFits(h.cargo, kind)) h.state = 'seeking'
        if (h.state !== 'harvesting') unit.rest()
        return
      }

      case 'returning': {
        const refinery = this.nearestRefinery(h)
        if (!refinery) {
          // no refinery: wait, perhaps one gets built
          h.state = 'waiting'
          h.timer = IDLE_SECONDS
          return
        }
        h.refinery = refinery
        const { at, forward } = Harvesting.dock(refinery)
        this.battlefield.walk(unit, at.clone().addScaledVector(forward, DOCK_APPROACH).setY(0))
        h.state = 'approaching'
        return
      }

      case 'approaching': {
        if (unit.walking) return
        const refinery = h.refinery!
        if (refinery.userData.dead) {
          h.state = 'returning'
          return
        }
        // one at a time: wait in front while another one unloads
        if (refinery.userData.dockedBy && refinery.userData.dockedBy !== h) return
        refinery.userData.dockedBy = h
        h.state = 'turning'
        return
      }

      case 'turning': {
        const { forward } = Harvesting.dock(h.refinery!)
        if (!unit.face(position.clone().add(forward), dt)) return
        // square to the dock, so it backs in straight
        unit.object.rotation.y = Math.atan2(forward.x, forward.z)
        h.state = 'docking'
        return
      }

      case 'docking': {
        const { at } = Harvesting.dock(h.refinery!)
        unit.drive(true)
        if (!this.moveTowards(h, at, unit.speed * REVERSE_FACTOR * dt)) return
        h.state = 'unloading'
        h.credited = false
        h.timer = unit.perform('Unload', false) ?? 1
        unit.object.userData.unloadTime = h.timer
        return
      }

      case 'unloading': {
        h.timer -= dt
        const length = unit.object.userData.unloadTime as number
        // the full container is in the refinery: its Tiberium is credited
        if (!h.credited && h.timer <= length * (1 - CREDIT_AT)) {
          h.credited = true
          const credits = this.worth(h)
          if (credits > 0) this.rules().earn(unit.object.userData.owner ?? 'player', credits)
          h.cargo.length = 0
        }
        if (h.timer <= 0) h.state = 'leaving'
        return
      }

      case 'ordered':
        if (unit.walking) return
        h.state = cargoFull(h.cargo) ? 'returning' : 'seeking'
    }
  }

  /** Drives to a cell, so that its collector comes to stand over it */
  private goTo(h: Harvester, cell: TiberiumCell) {
    const { unit } = h
    const position = unit.object.position
    h.cell = cell
    const centre = new THREE.Vector3(cell.x + 0.5, 0, cell.z + 0.5)
    const way = centre.clone().sub(position).setY(0)
    if (way.length() < 1e-3) way.set(Math.sin(unit.object.rotation.y), 0, Math.cos(unit.object.rotation.y))
    // it stands back by the collector's reach, so the collector is over the cell
    const stand = centre.clone().addScaledVector(way.normalize(), -COLLECTOR)
    if (stand.distanceTo(position) < 0.15) h.state = 'aiming'
    else {
      this.battlefield.walk(unit, stand)
      h.state = 'driving'
    }
  }

  /** Credits of a harvester's load: each stage a share of a full load's Storage= bales */
  private worth(h: Harvester) {
    const rules = this.rules()
    const bales = Math.max(1, rules.capacity(h.unit)) / (CARGO_SLOTS * SLOT_STAGES)
    return Math.round(h.cargo.reduce((sum, slot) => sum + slot.stages * bales * rules.value(slot.kind), 0))
  }

  /** Where the collector is now (on the ground) */
  private collector(unit: Unit) {
    const heading = unit.object.rotation.y
    const at = unit.object.position.clone().add(new THREE.Vector3(Math.sin(heading), 0, Math.cos(heading)).multiplyScalar(COLLECTOR))
    return at.setY(this.battlefield.heightAt(at.x, at.z))
  }

  /** Moves the harvester straight towards `to` (also up onto the refinery's pad); true when there. */
  private moveTowards(h: Harvester, to: THREE.Vector3, step: number) {
    // its height is its own while it docks (the battlefield no longer keeps it on the ground)
    h.unit.object.userData.offGround = true
    const position = h.unit.object.position
    const way = to.clone().sub(position)
    const distance = way.length()
    if (distance <= step) {
      position.copy(to)
      return true
    }
    position.addScaledVector(way, step / distance)
    return false
  }

  /** The dock is free again (the harvester drove out, was sent away or destroyed) */
  private release(h: Harvester) {
    h.unit.object.userData.offGround = false
    if (h.refinery?.userData.dockedBy === h) h.refinery.userData.dockedBy = undefined
  }

  /** The nearest refinery of the harvester's owner that still stands */
  private nearestRefinery(h: Harvester) {
    const owner = h.unit.object.userData.owner ?? 'player'
    const position = h.unit.object.position
    let best: THREE.Object3D | undefined
    let bestDistance = Infinity
    for (const refinery of this.battlefield.structuresOf('PROC')) {
      if (refinery.userData.dead || (refinery.userData.owner ?? 'player') !== owner) continue
      const d = Battlefield.reach(position, refinery)
      if (d < bestDistance) {
        best = refinery
        bestDistance = d
      }
    }
    return best
  }

  /** Dust, Tiberium shards and a green shimmer rise from the collector while it harvests. */
  private dustFrom(h: Harvester, dt: number) {
    h.dust -= dt
    const heading = h.unit.object.rotation.y
    // as many puffs per second at any frame rate
    for (; h.dust <= 0; h.dust += DUST_INTERVAL) {
      this.battlefield.effects.harvestDust(this.collector(h.unit), new THREE.Vector3(Math.cos(heading), 0, -Math.sin(heading)), h.cell?.kind)
    }
  }

  dispose() {
    this.harvesters.length = 0
  }
}
