import * as THREE from 'three'
import { expect, it } from 'vitest'
import { Harvesting } from '../app/lib/game/harvesting'
import { type CargoSlot, cargoFits, cargoFull, cargoNeeds, loadCargo } from '../app/lib/game/tiberium'
import { Unit } from '../app/lib/game/unit'

/** A harvester in a small field next to its refinery (stand-ins for the battlefield) */
it('harvests, docks, unloads and goes back to work', () => {
  const cells = new Map<string, { x: number, z: number, stage: number }>()
  for (let x = 8; x < 11; x++) {
    for (let z = -1; z < 2; z++) cells.set(`${x},${z}`, { x, z, stage: 3 })
  }
  const refinery = new THREE.Group()
  refinery.position.set(0, 0, 0)
  const dock = new THREE.Object3D()
  dock.name = 'Dock'
  dock.position.set(1.25, 0.03, 0)
  dock.rotation.y = Math.PI / 2 // +Z points to +X: away from the plant
  refinery.add(dock)
  refinery.userData = { id: 'PROC', owner: 'player', footprint: { x: -2, z: -1.5, w: 4, h: 3 } }
  refinery.updateMatrixWorld(true)
  const battlefield = {
    nearestTiberium(from: THREE.Vector3, skip?: Set<string>) {
      let best
      let d = Infinity
      for (const [k, c] of cells) {
        if (!c.stage || skip?.has(k)) continue
        const e = Math.hypot(c.x + 0.5 - from.x, c.z + 0.5 - from.z)
        if (e < d) {
          d = e
          best = c
        }
      }
      return best && { ...best }
    },
    harvestTiberium(x: number, z: number) {
      const c = cells.get(`${x},${z}`)
      if (!c?.stage) return false
      c.stage--
      return true
    },
    walk(unit: Unit, to: THREE.Vector3) { unit.walkTo(to) },
    structuresOf: () => [refinery],
    effects: { exhaust() {}, harvestDust() {} },
  }
  const object = new THREE.Object3D()
  object.userData = { owner: 'player' }
  const unit = new Unit(object, [], 0.5)
  let credits = 0
  const states: string[] = []
  const harvesting = new Harvesting(battlefield as never, () => ({ capacity: () => 30, value: () => 25, earn: (_, c) => {
    credits += c
  } }))
  const at = Harvesting.dock(refinery)
  object.position.copy(at.at)
  object.rotation.y = Math.atan2(at.forward.x, at.forward.z)
  harvesting.add(unit, refinery, 1)
  for (let t = 0; t < 200; t += 0.05) {
    harvesting.update(0.05)
    unit.update(0.05)
    const s = (harvesting as never as { harvesters: { state: string }[] }).harvesters[0]!.state
    if (states.at(-1) !== s) states.push(s)
  }
  // the whole field (9 ripe cells, 27 stages) brought in over two trips: five ripe
  // cells fill a harvester; a full load is worth its 30 bales
  expect([...cells.values()].every(c => c.stage === 0)).toBe(true)
  expect(credits).toBe(27 / 15 * 30 * 25)
  expect(states.filter(s => s === 'unloading')).toHaveLength(2)
  expect(states.slice(0, 6)).toEqual(['waiting', 'leaving', 'seeking', 'driving', 'aiming', 'harvesting'])
})

it('fills five squares, a ripe cell or three small ones each, never mixing green and blue in one', () => {
  const cargo: CargoSlot[] = []
  // three small green cells: one square
  for (let i = 0; i < 3; i++) loadCargo(cargo, 'green')
  expect(cargo).toEqual([{ kind: 'green', stages: 3 }])
  // one small green cell begins the next square; blue does not go in there
  loadCargo(cargo, 'green')
  loadCargo(cargo, 'blue')
  expect(cargo).toEqual([{ kind: 'green', stages: 3 }, { kind: 'green', stages: 1 }, { kind: 'blue', stages: 1 }])
  // two more ripe blue cells (6 stages): the blue square fills, one more, and a third begun
  for (let i = 0; i < 6; i++) loadCargo(cargo, 'blue')
  expect(cargo.map(s => s.stages)).toEqual([3, 1, 3, 3, 1])
  expect(cargoFull(cargo)).toBe(false)
  // no new square left: only blue fits now
  expect(cargoNeeds(cargo)).toBe('blue')
  expect(cargoFits(cargo, 'green')).toBe(false)
  expect(loadCargo(cargo, 'green')).toBe(false)
  loadCargo(cargo, 'blue')
  loadCargo(cargo, 'blue')
  expect(cargoFull(cargo)).toBe(true)
})

it('takes one green and four blue', () => {
  const cargo: CargoSlot[] = []
  for (let i = 0; i < 3; i++) loadCargo(cargo, 'green')
  for (let i = 0; i < 12; i++) loadCargo(cargo, 'blue')
  expect(cargo.map(s => s.kind)).toEqual(['green', 'blue', 'blue', 'blue', 'blue'])
  expect(cargoFull(cargo)).toBe(true)
})
