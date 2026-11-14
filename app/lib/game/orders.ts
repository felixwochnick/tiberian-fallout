import * as THREE from 'three'
import { Battlefield } from './battlefield'
import type { Combat } from './combat'
import type { Harvesting } from './harvesting'
import { BUILD_OPTIONS, type BuildInfo, canBuild } from './cameos'
import type { Economy } from './economy'
import { type Owner, ownerOf } from './players'

/**
 * Orders: everything a player can tell their units and their base, as plain data that
 * can be sent over the network as it is (JSON). The computer players give theirs this
 * way. In a network match (Colyseus) the human players' orders would come in as such
 * messages too: checked against who sent them (a player only commands their own units
 * and buildings) and carried out the same way, on the server or on every machine.
 * Units and buildings are named by their network id (userData.netId), positions are
 * world cells.
 */
export type Order =
  /** Starts building a structure or queues a unit (a left click on its cameo) */
  | { type: 'build', id: string }
  /** Cancels a job (a right click on a cameo on hold), the money comes back */
  | { type: 'cancel', id: string }
  /** Puts the finished structure down, its lower corner at (x, z); an upgrade onto the building there */
  | { type: 'place', id: string, x: number, z: number }
  /** Unfolds an MCV where it stands */
  | { type: 'deploy', unit: number }
  | { type: 'move', units: number[], x: number, z: number }
  /** Walks there and fights every enemy met on the way */
  | { type: 'attackMove', units: number[], x: number, z: number }
  | { type: 'attack', units: number[], target: number }
  | { type: 'stop', units: number[] }
  /** Harvesters harvest the Tiberium at (x, z), or the field nearest to them */
  | { type: 'harvest', units: number[], x?: number, z?: number }
  /** Where a factory sends what it produces */
  | { type: 'rally', factory: number, x: number, z: number }
  /** Starts or stops repairing a building */
  | { type: 'repair', building: number }
  | { type: 'sell', building: number }

export type OrderResult = { ok: true } | { ok: false, reason: string }

/** What carrying out orders needs of the running game */
export interface OrderContext {
  battlefield: Battlefield
  combat: Combat
  harvesting: Harvesting
  /** The economy of a player in the match */
  economy: (owner: Owner) => Economy | undefined
  /** Highest tech level that may be built */
  techLevel: () => number
  /**
   * Puts a finished structure of `owner` down with its lower corner on `cell` (an
   * upgrade onto the building there, pavement on the free cells); false if it does not fit
   */
  place: (owner: Owner, info: BuildInfo, cell: [number, number]) => boolean
  /** Unfolds an MCV where it stands; false if there is no room */
  deploy: (object: THREE.Object3D) => boolean
  sell: (building: THREE.Object3D) => boolean
  /** Starts or stops repairing a building; false if it cannot be repaired */
  repair: (building: THREE.Object3D) => boolean
}

/** What a player can build now: their side's options whose prerequisites they own, within the tech level */
export function buildable(economy: Economy, techLevel: number): BuildInfo[] {
  const rules = economy.rules
  if (!rules) return []
  const own = BUILD_OPTIONS[economy.side]
  return [...own.structures, ...own.units]
    .map(o => rules.info.get(o.id))
    .filter((info): info is BuildInfo => !!info && canBuild(rules, info.id, economy.buildings, info.structure)
      && info.techLevel >= 0 && info.techLevel <= techLevel)
}

const fail = (reason: string): OrderResult => ({ ok: false, reason })
const OK: OrderResult = { ok: true }

/** Carries out the players' orders on the battlefield */
export class Orders {
  constructor(private readonly ctx: OrderContext) {}

  /** Carries out an order of `owner`, if it is theirs to give */
  issue(owner: Owner, order: Order): OrderResult {
    const { battlefield, combat, harvesting } = this.ctx
    const economy = this.ctx.economy(owner)
    if (!economy) return fail(`Kein Spieler ${owner}`)
    /** The player's own units among the ids (the others are left out) */
    const units = (ids: number[]) => ids.map(id => battlefield.objectById(id))
      .filter((o): o is THREE.Object3D => !!o?.userData.unit && ownerOf(o) === owner)
    /** One of the player's own objects */
    const own = (id: number) => {
      const object = battlefield.objectById(id)
      return object && ownerOf(object) === owner ? object : undefined
    }
    const ground = (x: number, z: number) => new THREE.Vector3(x, battlefield.heightAt(x, z), z)
    switch (order.type) {
      case 'build': {
        const info = buildable(economy, this.ctx.techLevel()).find(o => o.id === order.id)
        if (!info) return fail(`${order.id} kann nicht gebaut werden`)
        return economy.production.start(info) ? OK : fail('Fabrik belegt')
      }
      case 'cancel': {
        const job = economy.production.jobFor(order.id)
        if (!job) return fail(`Kein Auftrag für ${order.id}`)
        economy.credits.value += economy.production.cancel(job)
        return OK
      }
      case 'place': {
        const job = economy.production.structure
        if (job?.state !== 'ready' || job.info.id !== order.id) return fail(`${order.id} ist nicht fertig`)
        return this.ctx.place(owner, job.info, [Math.floor(order.x), Math.floor(order.z)]) ? OK : fail('Passt dort nicht hin')
      }
      case 'deploy': {
        const object = own(order.unit)
        return object?.userData.unit && this.ctx.deploy(object) ? OK : fail('Kann hier nicht entfalten')
      }
      case 'move': {
        const objects = units(order.units)
        combat.stop(objects)
        harvesting.order(objects)
        battlefield.moveUnits(objects, battlefield.openSpot(ground(order.x, order.z)))
        return objects.length ? OK : fail('Keine eigenen Einheiten')
      }
      case 'attackMove': {
        const objects = units(order.units)
        harvesting.order(objects)
        battlefield.clearWaypoints(objects)
        const point = battlefield.openSpot(ground(order.x, order.z))
        // spread round the point like a move, so they do not all crowd one spot
        objects.forEach((object, i) => combat.attackMove([object], battlefield.openSpot(point.clone().add(Battlefield.spread(i, objects.length)))))
        return objects.length ? OK : fail('Keine eigenen Einheiten')
      }
      case 'attack': {
        const objects = units(order.units)
        const target = battlefield.objectById(order.target)
        if (!target) return fail('Kein Ziel')
        battlefield.clearWaypoints(objects)
        harvesting.order(objects)
        combat.attack(objects, target)
        return OK
      }
      case 'stop': {
        const objects = units(order.units)
        combat.stop(objects)
        harvesting.order(objects)
        battlefield.clearWaypoints(objects)
        for (const object of objects) (object.userData.unit as { stop: () => void }).stop()
        return OK
      }
      case 'harvest': {
        const objects = units(order.units).filter(o => o.userData.harvester)
        if (!objects.length) return fail('Keine Sammler')
        const cell = order.x === undefined || order.z === undefined
          ? battlefield.nearestTiberium(objects[0]!.position)
          : battlefield.tiberiumAt(ground(order.x, order.z)) ?? battlefield.nearestTiberium(ground(order.x, order.z))
        if (!cell) return fail('Kein Tiberium')
        harvesting.harvest(objects, cell)
        return OK
      }
      case 'rally': {
        const factory = own(order.factory)
        if (!factory?.userData.abilities?.includes('rally')) return fail('Keine eigene Fabrik')
        factory.userData.rallyPoint = battlefield.openSpot(ground(order.x, order.z))
        return OK
      }
      case 'repair': {
        const building = own(order.building)
        return building && this.ctx.repair(building) ? OK : fail('Kann nicht repariert werden')
      }
      case 'sell': {
        const building = own(order.building)
        return building && this.ctx.sell(building) ? OK : fail('Kann nicht verkauft werden')
      }
    }
  }
}
