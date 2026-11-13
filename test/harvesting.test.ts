import * as THREE from 'three'
import { expect, it } from 'vitest'
import { Harvesting } from '../app/lib/game/harvesting'
import { type CargoSlot, cargoFits, cargoFull, cargoNeeds, loadCargo, TiberiumStore } from '../app/lib/game/tiberium'
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
    heightAt: () => 0,
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
  for (let t = 0; t < 400; t += 0.05) {
    harvesting.update(0.05)
    unit.update(0.05)
    const s = (harvesting as never as { harvesters: { state: string }[] }).harvesters[0]!.state
    if (states.at(-1) !== s) states.push(s)
  }
  // the whole field (9 ripe cells, 27 stages) brought in over two trips: five ripe
  // cells fill a harvester; a full load is worth its 30 bales
  expect([...cells.values()].every(c => c.stage === 0)).toBe(true)
  expect(credits).toBeCloseTo(27 / 15 * 30 * 25)
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

it('keeps the Tiberium brought in, spends it first and lets go of what no longer fits', () => {
  const store = new TiberiumStore(kind => (kind === 'blue' ? 50 : 25))
  let credits = 1000
  store.follow(credits, 80)
  // a load of green (28 bales) and some blue (10 bales) into a refinery (80 bales)
  credits += 700
  store.bring('green', 700, 80)
  credits += 500
  store.bring('blue', 500, 80)
  store.follow(credits, 80)
  expect(store.bales).toEqual({ green: 28, blue: 10 })
  expect(store.fill(80)).toEqual({ green: 28 / 80, blue: 10 / 80 })
  // more than there is room for: only what fits is stored
  credits += 1500
  store.bring('green', 1500, 80)
  store.follow(credits, 80)
  expect(store.total).toBeCloseTo(80)
  expect(store.worth()).toBeCloseTo(70 * 25 + 10 * 50)
  // 1000 credits spent (while 0 more came in): out of the store, both kinds alike
  credits -= 1000
  store.follow(credits, 80)
  expect(store.worth()).toBeCloseTo(2250 - 1000)
  expect(store.bales.green / store.bales.blue).toBeCloseTo(7)
  // a harvester unloads in the same frame as something is paid: still spent from the store
  credits += 250
  store.bring('green', 250, 80)
  credits -= 400
  store.follow(credits, 80)
  expect(store.worth()).toBeCloseTo(1250 + 250 - 400)
  // the silo is sold: what does not fit into the rest is plain money
  store.follow(credits, 20)
  expect(store.total).toBeCloseTo(20)
  // more spent than is stored: the store is empty, the rest comes out of the money
  credits -= 2000
  store.follow(credits, 20)
  expect(store.total).toBe(0)
  expect(store.fill(20)).toEqual({ green: 0, blue: 0 })
})
