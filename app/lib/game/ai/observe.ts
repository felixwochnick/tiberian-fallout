import * as THREE from 'three'
import type { Battlefield } from '../battlefield'
import type { Combat } from '../combat'
import type { BuildInfo } from '../cameos'
import { basePower } from '../economy'
import type { MatchPlayer } from '../field'
import { buildable } from '../orders'
import { ownerOf } from '../players'
import { tiberiumPatches } from '../tiberium'
import type { Unit } from '../unit'
import type { BuildChoice, Observation, SeenStructure, SeenUnit } from './view'

/** Walls, gates and pavement: not part of the base proper */
const WALLS = new Set(['GAWALL', 'NAWALL', 'GASAND', 'GAGATE_A', 'GAGATE_B', 'NAGATE_A', 'NAGATE_B', 'GAPAVE', 'GAFSDF', 'NAPOST'])

const round = (n: number) => Math.round(n * 10) / 10

/** What `player` sees of the battlefield now (see PlayerView), and how they can ask it where things fit */
export function observe(battlefield: Battlefield, combat: Combat, player: MatchPlayer, players: MatchPlayer[], techLevel: number): Observation {
  const economy = player.economy
  const infoOf = (object: THREE.Object3D) => economy.rules?.info.get(object.userData.id)
  const health = (object: THREE.Object3D) => Math.max(0, Math.min(1, object.userData.health ?? 1))

  const units: SeenUnit[] = []
  const enemyUnits: SeenUnit[] = []
  for (const { object } of battlefield.units) {
    // under the ground, inside a transport or hanging under a carryall: not to be seen
    if (object.userData.dead || object.userData.underground || object.userData.carried || !object.parent) continue
    const info = infoOf(object)
    const unit = object.userData.unit as Unit
    const seen: SeenUnit = {
      id: object.userData.netId,
      type: object.userData.id,
      owner: ownerOf(object),
      x: round(object.position.x),
      z: round(object.position.z),
      health: health(object),
      category: info?.category === 'structure' || !info ? 'vehicle' : info.category,
      harvester: !!object.userData.harvester,
      moving: unit.walking || battlefield.flight.travelling(unit),
      fighting: combat.busy(object),
    }
    ;(seen.owner === player.id ? units : enemyUnits).push(seen)
  }

  const structures: SeenStructure[] = []
  const enemyStructures: SeenStructure[] = []
  for (const object of battlefield.structureObjects) {
    const f = object.userData.footprint as { x: number, z: number, w: number, h: number } | undefined
    if (object.userData.dead || !f || object.userData.owner === 'neutral') continue
    const gun = object.userData.gun as THREE.Object3D | true | undefined
    const seen: SeenStructure = {
      id: object.userData.netId,
      type: object.userData.id,
      owner: ownerOf(object),
      x: f.x + f.w / 2,
      z: f.z + f.h / 2,
      health: health(object),
      cells: { x: f.x, z: f.z, w: f.w, h: f.h },
      repairing: !!object.userData.repairing,
      wall: WALLS.has(object.userData.id),
      armed: !!infoOf(object)?.weapon || !!gun,
      freeSlot: !gun && !!battlefield.freeSlot(object),
    }
    ;(seen.owner === player.id ? structures : enemyStructures).push(seen)
  }

  const job = economy.production.structure
  return {
    view: {
      me: player.id,
      credits: Math.floor(economy.credits.value),
      power: basePower(economy),
      buildings: [...economy.buildings],
      production: {
        structure: job && { id: job.info.id, ready: job.state === 'ready' },
        units: economy.production.units.map(j => j.info.id),
      },
      options: buildable(economy, techLevel).map(choice),
      towers: [...new Set([...economy.rules?.info.values() ?? []].filter(i => i.powersUp && i.weapon).map(i => i.powersUp!))],
      units,
      structures,
      enemies: { units: enemyUnits, structures: enemyStructures },
      tiberium: tiberiumPatches(battlefield.tiberiumCells),
      starts: players.filter(p => p.start).map(p => ({ owner: p.id, x: round(p.start!.x), z: round(p.start!.z) })),
      centre: { x: round(battlefield.centre.x), z: round(battlefield.centre.z) },
    },
    query: {
      canPlace(x, z, w, h, adjacent, spacing = 0) {
        if (!battlefield.canPlace(x, z, w, h, adjacent, { owner: player.id })) return false
        // the ring of `spacing` cells round it: no building there, so units can pass between
        for (let i = x - spacing; i < x + w + spacing; i++) {
          for (let j = z - spacing; j < z + h + spacing; j++) {
            if ((i < x || i >= x + w || j < z || j >= z + h) && battlefield.buildingOn(i, j)) return false
          }
        }
        return true
      },
      canDeploy(id) {
        const unit = battlefield.objectById(id)?.userData.unit as Unit | undefined
        return !!unit && !!battlefield.deployCell(unit)
      },
      openSpot(x, z) {
        const spot = battlefield.openSpot(new THREE.Vector3(x, 0, z))
        return { x: round(spot.x), z: round(spot.z) }
      },
    },
  }
}

/** A build option as the computer player weighs it */
function choice(info: BuildInfo): BuildChoice {
  const weapon = info.weapon
  return {
    id: info.id,
    structure: info.structure,
    category: info.category,
    cost: info.cost,
    power: info.power,
    foundation: info.foundation,
    adjacent: info.adjacent,
    armed: !!weapon && weapon.damage > 0 && !info.manualOnly,
    antiAir: !!weapon?.aa,
    antiGround: !!weapon?.ag,
    powersUp: info.powersUp,
    wall: info.wall || info.gate || WALLS.has(info.id),
  }
}
