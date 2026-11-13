import * as THREE from 'three'
import { expect, it } from 'vitest'
import { Flight } from '../app/lib/game/flight'
import { Unit } from '../app/lib/game/unit'

/**
 * Stand-ins for the battlefield: flat ground, a slope for x ≥ 20, helipads (2 × 2
 * cells, their pad in the middle) on which nothing lands but their own aircraft
 */
function field(pads: [number, number][]) {
  const helipads = pads.map(([x, z]) => {
    const pad = new THREE.Object3D()
    pad.position.set(x, 0, z)
    pad.userData = { id: 'GAHPAD', owner: 'player' }
    return pad
  })
  const onPad = (at: THREE.Vector3) => helipads.some(p => !p.userData.dead && Math.abs(at.x - p.position.x) < 1.3 && Math.abs(at.z - p.position.z) < 1.3)
  const flight = new Flight({
    heightAt: () => 0,
    helipads: owner => helipads.filter(p => !p.userData.dead && p.userData.owner === owner),
    landable: at => at.x < 19.7 && !onPad(at),
  })
  return { flight, helipads }
}

function orca(flight: Flight, at: [number, number], home?: THREE.Object3D, ammo = 5) {
  const object = new THREE.Object3D()
  object.position.set(at[0], 0, at[1])
  object.userData = { owner: 'player' }
  const unit = new Unit(object, [], 4)
  flight.addAircraft(unit, home, ammo)
  return unit
}

function run(flight: Flight, seconds: number) {
  for (let t = 0; t < seconds; t += 0.05) flight.update(0.05)
}

const flat = (unit: Unit) => [Math.round(unit.object.position.x * 10) / 10, Math.round(unit.object.position.z * 10) / 10]

it('with shots left it lands where it is, out of shots it flies to its helipad and reloads', () => {
  const { flight, helipads } = field([[0, 0]])
  const unit = orca(flight, [5, 5], helipads[0])
  expect(flat(unit)).toEqual([0, 0])
  flight.flyTo(unit, new THREE.Vector3(10, 0, 4))
  run(flight, 5)
  expect(flight.airborne(unit)).toBe(true)
  // its work done there: it comes down on the spot, not at home
  flight.done(unit)
  run(flight, 3)
  expect(flight.airborne(unit)).toBe(false)
  expect(flat(unit)).toEqual([10, 4])

  // up again, the shots fired: home to reload
  flight.flyTo(unit, new THREE.Vector3(12, 0, 4))
  run(flight, 3)
  for (let i = 0; i < 5; i++) flight.fired(unit)
  expect(flight.canFire(unit)).toBe(false)
  run(flight, 8)
  expect(flight.airborne(unit)).toBe(false)
  expect(flat(unit)).toEqual([0, 0])
  run(flight, 8)
  expect(flight.ammoOf(unit)).toEqual({ shots: 5, ammo: 5 })
})

it('does not land on a slope, but on flat ground near by', () => {
  const { flight } = field([])
  const unit = orca(flight, [15, 0])
  flight.flyTo(unit, new THREE.Vector3(20.5, 0, 0))
  run(flight, 4)
  flight.done(unit)
  run(flight, 4)
  expect(flight.airborne(unit)).toBe(false)
  expect(unit.object.position.x).toBeLessThan(19.7)
  expect(unit.object.position.x).toBeGreaterThan(18)
})

it('out of shots with no helipad free, it waits by one and takes it once it is free', () => {
  const { flight, helipads } = field([[0, 0]])
  const first = orca(flight, [0, 0], helipads[0])
  const second = orca(flight, [10, 0])
  flight.flyTo(second, new THREE.Vector3(10, 0, 5))
  run(flight, 3)
  for (let i = 0; i < 5; i++) flight.fired(second)
  run(flight, 8)
  // down by the helipad, not on it, and not on the first one
  expect(flight.airborne(second)).toBe(false)
  const wait = second.object.position.clone()
  expect(Math.hypot(wait.x, wait.z)).toBeGreaterThan(1.3)
  expect(Math.hypot(wait.x, wait.z)).toBeLessThan(4.5)
  expect(flight.ammoOf(second)?.shots).toBe(0)

  // the first one leaves: the second takes its helipad
  flight.flyTo(first, new THREE.Vector3(-8, 0, 0))
  run(flight, 6)
  expect(flat(second)).toEqual([0, 0])
  run(flight, 10)
  expect(flight.ammoOf(second)?.shots).toBe(5)
  // the first one, its shots all there, lands out there and stays
  flight.done(first)
  run(flight, 3)
  expect(flat(first)).toEqual([-8, 0])
})

it('a group sent onto a helipad takes the free ones, the rest land by it', () => {
  const { flight, helipads } = field([[0, 0], [6, 0]])
  const group = [orca(flight, [3, 8]), orca(flight, [4, 8]), orca(flight, [5, 8])]
  flight.dock(group, helipads[0]!)
  run(flight, 10)
  for (const unit of group) expect(flight.airborne(unit)).toBe(false)
  const where = group.map(flat)
  expect(where).toContainEqual([0, 0])
  expect(where).toContainEqual([6, 0])
  const waiting = group.find(unit => !['0,0', '6,0'].includes(flat(unit).join(',')))!
  const at = waiting.object.position
  // by the helipad it was sent to, apart from the others
  expect(Math.hypot(at.x, at.z)).toBeLessThan(4.5)
  expect(Math.hypot(at.x - 6, at.z)).toBeGreaterThan(1.3)
})

it('a new aircraft takes a free helipad, or lands next to a taken one', () => {
  const { flight, helipads } = field([[0, 0], [6, 0]])
  const first = orca(flight, [0, 0], helipads[0])
  const second = orca(flight, [0, 0], helipads[0])
  expect(flat(first)).toEqual([0, 0])
  expect(flat(second)).toEqual([6, 0])
  const third = orca(flight, [0, 0], helipads[0])
  run(flight, 6)
  expect(flight.airborne(third)).toBe(false)
  const at = third.object.position
  expect(Math.hypot(at.x, at.z)).toBeGreaterThan(1.3)
  expect(Math.hypot(at.x - 6, at.z)).toBeGreaterThan(1.3)
})
