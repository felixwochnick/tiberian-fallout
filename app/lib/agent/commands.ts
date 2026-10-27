import * as THREE from 'three'
import { Battlefield } from '../game/battlefield'
import type { Combat } from '../game/combat'
import type { Harvesting } from '../game/harvesting'
import { type BuildInfo, canBuild, GDI_BUILD_OPTIONS } from '../game/cameos'
import type { Unit } from '../game/unit'
import { basePower, type Skirmish } from '~/composables/useSkirmish'
import type { AgentCommands } from './link'

/**
 * What an agent (scripts/agent.mjs) can do in a running game: read its state and give
 * the orders a player gives with mouse and sidebar. Objects are named by a short
 * number (`ref`) that stays the same as long as they are on the map; positions are
 * world cells (x, z), as in `state` and `map`.
 */
export interface AgentContext {
  battlefield: Battlefield
  skirmish: Skirmish
  combat: Combat
  harvesting: Harvesting
  /** Highest tech level that may be built */
  techLevel: () => number
  /** The game waits (Esc menu, briefing, battle control not established) */
  paused: () => boolean
  /** Game seconds since the battlefield was set up */
  clock: () => number
  /** Puts a finished structure down at a cell, like a click while placing */
  place: (info: BuildInfo, cell: [number, number]) => void
  /** Like a click on the selected MCV, Tick Tank or transport; false if it cannot here */
  deploy: (object: THREE.Object3D) => boolean
  sell: (object: THREE.Object3D) => boolean
  repair: (object: THREE.Object3D) => boolean
  switchPower: (object: THREE.Object3D) => boolean
}

type Ref = number | string

/** Most game seconds one `wait` may take */
const MAX_WAIT = 120

export function agentCommands(ctx: AgentContext): AgentCommands {
  const { battlefield, skirmish, combat, harvesting } = ctx
  const refs = new WeakMap<THREE.Object3D, number>()
  let nextRef = 1
  const refOf = (object: THREE.Object3D) => {
    let ref = refs.get(object)
    if (!ref) refs.set(object, ref = nextRef++)
    return ref
  }

  const alive = () => battlefield.pickable.filter(object => !object.userData.dead)
  function find(ref: Ref) {
    const object = alive().find(o => refOf(o) === Number(ref))
    if (!object) throw new Error(`Kein Objekt mit ref ${ref} (zerstört oder nie da gewesen?)`)
    return object
  }
  /** Own units by refs (a number, "1,2,3" or a list) */
  function ownUnits(list: Ref | Ref[]) {
    const wanted = (Array.isArray(list) ? list : String(list).split(',')).map(Number)
    const objects = wanted.map(find)
    const foreign = objects.filter(o => !o.userData.unit || !Battlefield.own(o))
    if (foreign.length) throw new Error(`Keine eigenen Einheiten: ${foreign.map(refOf).join(', ')}`)
    return objects
  }
  const ground = (x: number, z: number) => {
    if (!Number.isFinite(Number(x)) || !Number.isFinite(Number(z))) throw new Error('x und z (Zellen) fehlen')
    return new THREE.Vector3(Number(x), battlefield.heightAt(Number(x), Number(z)), Number(z))
  }
  const round = (n: number) => Math.round(n * 10) / 10

  /** What can be built right now, structures and units */
  function options() {
    const rules = skirmish.rules
    if (!rules) return []
    return [...GDI_BUILD_OPTIONS.structures, ...GDI_BUILD_OPTIONS.units]
      .map(o => rules.info.get(o.id))
      .filter((info): info is BuildInfo => !!info && canBuild(rules, info.id, skirmish.buildings, info.structure)
        && info.techLevel >= 0 && info.techLevel <= ctx.techLevel())
  }

  function describe(object: THREE.Object3D) {
    const data = object.userData
    const unit = data.unit as Unit | undefined
    const footprint = data.footprint as { x: number, z: number, w: number, h: number } | undefined
    return {
      ref: refOf(object),
      id: data.id as string,
      owner: Battlefield.own(object) ? 'player' : 'enemy',
      ...(data.player ? { player: data.player as string } : {}),
      kind: unit ? 'unit' : 'structure',
      x: round(object.position.x),
      z: round(object.position.z),
      ...(footprint ? { cells: [footprint.x, footprint.z, footprint.w, footprint.h] } : {}),
      health: Math.round((data.health ?? 1) * 100),
      ...(unit?.walking ? { moving: true } : {}),
      ...(data.harvester ? { cargo: (data.cargo as unknown[] | undefined)?.length ?? 0 } : {}),
      ...(data.repairing ? { repairing: true } : {}),
      ...(data.poweredOff ? { offline: true } : {}),
      ...(Battlefield.capacity(object) ? { passengers: Battlefield.passengers(object).length } : {}),
    }
  }

  /** Tiberium fields: the cells grouped by kind into blobs of neighbours, with their middle */
  function tiberiumFields() {
    const cells = battlefield.tiberiumCells
    const seen = new Set<string>()
    const byKey = new Map(cells.map(c => [`${c.x},${c.z}`, c]))
    const fields: { kind: string, x: number, z: number, cells: number, bales: number }[] = []
    for (const start of cells) {
      if (seen.has(`${start.x},${start.z}`)) continue
      const blob = [start]
      seen.add(`${start.x},${start.z}`)
      for (let i = 0; i < blob.length; i++) {
        const c = blob[i]!
        for (let dx = -2; dx <= 2; dx++) {
          for (let dz = -2; dz <= 2; dz++) {
            const key = `${c.x + dx},${c.z + dz}`
            const n = byKey.get(key)
            if (n && !seen.has(key) && n.kind === start.kind) {
              seen.add(key)
              blob.push(n)
            }
          }
        }
      }
      fields.push({
        kind: start.kind ?? 'green',
        x: round(blob.reduce((s, c) => s + c.x + 0.5, 0) / blob.length),
        z: round(blob.reduce((s, c) => s + c.z + 0.5, 0) / blob.length),
        cells: blob.length,
        bales: blob.reduce((s, c) => s + c.stage, 0),
      })
    }
    return fields
  }

  function state() {
    const production = skirmish.production
    const job = (j?: { info: BuildInfo, progress: number, state: string }) =>
      j && { id: j.info.id, progress: Math.round(j.progress * 100), state: j.state }
    return {
      time: Math.round(ctx.clock()),
      paused: ctx.paused(),
      credits: Math.floor(skirmish.credits.value),
      power: basePower(skirmish),
      buildings: skirmish.buildings,
      production: { structure: job(production.structure) ?? null, units: production.units.map(job) },
      canBuild: options().map(info => ({
        id: info.id, structure: info.structure, cost: info.cost, seconds: info.seconds, power: info.power,
        ...(info.structure ? { size: info.foundation, adjacent: info.adjacent } : {}),
      })),
      objects: alive().map(describe),
      tiberium: tiberiumFields(),
      map: { size: [battlefield.width, battlefield.height], centre: [round(battlefield.centre.x), round(battlefield.centre.z)] },
      view: [round(battlefield.target.x), round(battlefield.target.z)],
      hints: skirmish.hints.map(h => h.text),
      ...(skirmish.timer ? { timer: Math.round(skirmish.timer.remaining) } : {}),
    }
  }

  /** Middle of the player's base (construction yard, else any own building), for placing */
  function baseCentre() {
    const own = battlefield.structureObjects.filter(o => Battlefield.own(o) && !o.userData.dead)
    const yard = own.find(o => o.userData.id === 'GACNST') ?? own[0]
    return yard?.position ?? battlefield.centre
  }

  /** The free spot for a w × h structure nearest to `near` (lower corner cell) */
  function findSpot(info: BuildInfo, near: THREE.Vector3) {
    const [w, h] = info.foundation
    const cx = Math.floor(near.x - w / 2)
    const cz = Math.floor(near.z - h / 2)
    for (let r = 0; r < 30; r++) {
      const ring: [number, number][] = []
      for (let dx = -r; dx <= r; dx++) {
        for (let dz = -r; dz <= r; dz++) {
          if (Math.max(Math.abs(dx), Math.abs(dz)) === r) ring.push([cx + dx, cz + dz])
        }
      }
      ring.sort((a, b) => Math.hypot(a[0] - cx, a[1] - cz) - Math.hypot(b[0] - cx, b[1] - cz))
      const spot = ring.find(([x, z]) => battlefield.canPlace(x, z, w, h, info.adjacent))
      if (spot) return spot
    }
  }

  const commands: AgentCommands = {
    help: () => Object.keys(commands),

    state,

    /**
     * Waits `seconds` of game time (at most MAX_WAIT; also gives up once four times
     * as long has passed for real, e.g. while the game waits), then returns the state.
     */
    async wait(seconds: number = 5) {
      const span = Math.min(MAX_WAIT, Math.max(0, Number(seconds) || 0))
      const until = ctx.clock() + span
      const deadline = performance.now() + span * 4000 + 2000
      while (ctx.clock() < until && performance.now() < deadline) await new Promise(resolve => setTimeout(resolve, 100))
      return state()
    },

    /** Cells round (x, z): '.' free, '#' blocked or slope, 'g'/'b' Tiberium, 'S'/'X' own/enemy building, 'u'/'x' own/enemy unit */
    map(x?: number, z?: number, radius: number = 16) {
      const at = x === undefined ? baseCentre() : ground(x, z!)
      const r = Math.min(40, Math.max(2, Math.floor(Number(radius))))
      const x0 = Math.floor(at.x) - r
      const z0 = Math.floor(at.z) - r
      const marks = new Map<string, string>()
      for (const c of battlefield.tiberiumCells) marks.set(`${c.x},${c.z}`, c.kind === 'blue' ? 'b' : 'g')
      for (const object of alive()) {
        const own = Battlefield.own(object)
        const f = object.userData.footprint as { x: number, z: number, w: number, h: number } | undefined
        if (f) {
          for (let i = 0; i < f.w; i++) for (let j = 0; j < f.h; j++) marks.set(`${f.x + i},${f.z + j}`, own ? 'S' : 'X')
        }
        else marks.set(`${Math.floor(object.position.x)},${Math.floor(object.position.z)}`, own ? 'u' : 'x')
      }
      const rows: string[] = []
      for (let cz = z0; cz <= z0 + 2 * r; cz++) {
        let row = ''
        for (let cx = x0; cx <= x0 + 2 * r; cx++) {
          row += marks.get(`${cx},${cz}`) ?? (battlefield.canPlace(cx, cz, 1, 1, Infinity) ? '.' : '#')
        }
        rows.push(`${String(cz).padStart(4)} ${row}`)
      }
      return { x0, z0, note: 'Zeilen = z (links), Spalten = x ab x0', rows }
    },

    /** Starts building a structure or queues a unit (like a left click on its cameo) */
    build(id: string, count: number = 1) {
      const info = options().find(o => o.id === String(id).toUpperCase())
      if (!info) throw new Error(`${id} kann jetzt nicht gebaut werden; möglich: ${options().map(o => o.id).join(', ')}`)
      let started = 0
      for (let i = 0; i < Math.max(1, Number(count)); i++) {
        if (!skirmish.production.start(info)) break
        started++
      }
      if (!started) throw new Error(info.structure ? `Es wird schon gebaut: ${skirmish.production.structure?.info.id}` : 'Warteschlange voll')
      return { started, production: state().production }
    },

    /** Holds a job, or cancels one on hold or a finished structure (like a right click on its cameo) */
    cancel(id: string) {
      const job = skirmish.production.jobFor(String(id).toUpperCase())
      if (!job) throw new Error(`Kein Auftrag für ${id}`)
      if (skirmish.placing?.id === job.info.id) skirmish.placing = undefined
      const refund = skirmish.production.cancel(job)
      skirmish.credits.value += refund
      return { refund: Math.floor(refund) }
    },

    /** Puts the finished structure down: its lower corner at (x, z), or the nearest free spot to the base (or to x, z with `near`) */
    place(x?: number, z?: number, near?: boolean) {
      const job = skirmish.production.structure
      if (!job || job.state !== 'ready') throw new Error('Kein fertiges Gebäude zum Platzieren')
      const info = job.info
      const [w, h] = info.foundation
      let cell: [number, number] | undefined
      if (x === undefined || near) cell = findSpot(info, x === undefined ? baseCentre() : ground(x, z!))
      else if (battlefield.canPlace(Math.floor(x), Math.floor(Number(z)), w, h, info.adjacent)) cell = [Math.floor(x), Math.floor(Number(z))]
      if (!cell) throw new Error(`${info.id} (${w}×${h}) passt dort nicht hin (belegt, Hang, Tiberium oder mehr als ${info.adjacent} Zellen von der Basis)`)
      ctx.place(info, cell)
      return { placed: info.id, cells: [cell[0], cell[1], w, h] }
    },

    /** Unfolds an MCV, digs a Tick Tank in or out, lets a transport's soldiers out */
    deploy(ref: Ref) {
      const object = find(ref)
      if (!Battlefield.own(object) || !object.userData.unit) throw new Error('Keine eigene Einheit')
      if (!ctx.deploy(object)) throw new Error('Geht hier nicht (kein Platz, Hang?)')
      return { deployed: refOf(object) }
    },

    /** Units walk to (x, z) */
    move(units: Ref | Ref[], x: number, z: number) {
      const objects = ownUnits(units)
      combat.stop(objects)
      harvesting.order(objects)
      battlefield.selection = objects
      battlefield.orderMove(ground(x, z))
      return { moving: objects.map(refOf) }
    },

    /** Units walk to (x, z) and fight whatever enemy comes in range on the way */
    attackMove(units: Ref | Ref[], x: number, z: number) {
      const objects = ownUnits(units)
      harvesting.order(objects)
      battlefield.selection = objects
      combat.attackMove(objects, ground(x, z))
      return { attackMoving: objects.map(refOf) }
    },

    /** Units attack a target */
    attack(units: Ref | Ref[], target: Ref) {
      const objects = ownUnits(units)
      const victim = find(target)
      if (!combat.canAttack(objects, victim)) throw new Error('Diese Einheiten können das nicht angreifen (kein Gegner, keine Waffe)')
      battlefield.clearWaypoints(objects)
      battlefield.selection = objects
      combat.attack(objects, victim)
      return { attacking: refOf(victim) }
    },

    /** Units stop what they are doing */
    stop(units: Ref | Ref[]) {
      const objects = ownUnits(units)
      combat.stop(objects)
      harvesting.order(objects)
      battlefield.clearWaypoints(objects)
      for (const object of objects) (object.userData.unit as Unit).stop()
      return { stopped: objects.map(refOf) }
    },

    /** Harvesters harvest the Tiberium at (x, z), or the field nearest to them */
    harvest(units: Ref | Ref[], x?: number, z?: number) {
      const objects = ownUnits(units).filter(o => o.userData.harvester)
      if (!objects.length) throw new Error('Keine Sammler dabei')
      const cell = x === undefined
        ? battlefield.nearestTiberium(objects[0]!.position)
        : battlefield.tiberiumAt(ground(x, z!)) ?? battlefield.nearestTiberium(ground(x, z!))
      if (!cell) throw new Error('Kein Tiberium auf der Karte')
      harvesting.harvest(objects, cell)
      return { harvesting: [cell.x, cell.z] }
    },

    /** Harvesters drive into a refinery and unload */
    unload(units: Ref | Ref[], refinery: Ref) {
      const objects = ownUnits(units).filter(o => o.userData.harvester)
      const target = find(refinery)
      if (!objects.length || target.userData.id !== 'PROC' || !Battlefield.own(target)) throw new Error('Sammler und eigene Raffinerie nötig')
      harvesting.unloadAt(objects, target)
      return { unloading: refOf(target) }
    },

    /** Where a factory sends what it produces */
    rally(factory: Ref, x: number, z: number) {
      const object = find(factory)
      if (!Battlefield.own(object) || !object.userData.abilities?.includes('rally')) throw new Error('Keine eigene Fabrik')
      object.userData.rallyPoint = ground(x, z)
      return { rally: [Number(x), Number(z)] }
    },

    sell(ref: Ref) {
      if (!ctx.sell(find(ref))) throw new Error('Kann nicht verkauft werden')
      return { sold: Number(ref) }
    },

    /** Starts or stops repairing a building */
    repair(ref: Ref) {
      if (!ctx.repair(find(ref))) throw new Error('Nicht beschädigt oder nicht reparierbar')
      return { repairing: !!find(ref).userData.repairing }
    },

    /** Switches a building off or on again */
    power(ref: Ref) {
      if (!ctx.switchPower(find(ref))) throw new Error('Nur Gebäude, die Strom verbrauchen')
      return { offline: !!find(ref).userData.poweredOff }
    },

    /** Moves the camera to (x, z), or to an object's ref with one argument */
    look(x: number | string, z?: number) {
      battlefield.lookAt(z === undefined ? find(x).position : ground(Number(x), z))
      return { view: [round(battlefield.target.x), round(battlefield.target.z)] }
    },

    /** The battlefield as the player sees it (JPEG data URL) */
    screenshot() {
      return { image: battlefield.snapshot() }
    },
  }
  return commands
}
