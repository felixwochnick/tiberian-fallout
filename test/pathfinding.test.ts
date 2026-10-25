import * as THREE from 'three'
import { describe, expect, it } from 'vitest'
import { findPath, lineFree, type NavMap } from '../app/lib/game/pathfinding'

/** 20 × 20 cells with a wall at x = 10 from z = 0 to 14 (a gap above) */
const map: NavMap = {
  free: (x, z) => x >= 0 && x < 20 && z >= 0 && z < 20 && !(x === 10 && z < 15),
}
const v = (x: number, z: number) => new THREE.Vector3(x, 0, z)

describe('pathfinding', () => {
  it('goes straight when nothing is in the way', () => {
    const path = findPath(map, v(1.5, 1.5), v(8.5, 6.5))
    expect(path).toHaveLength(1)
    expect(path[0]!.x).toBeCloseTo(8.5)
  })

  it('goes round a wall, never through it', () => {
    const path = findPath(map, v(5.5, 5.5), v(15.5, 5.5))
    expect(path.length).toBeGreaterThan(1)
    let from = v(5.5, 5.5)
    for (const point of path) {
      expect(lineFree(map, from, point)).toBe(true)
      from = point
    }
    // the way leads through the gap above the wall
    expect(Math.max(...path.map(p => p.z))).toBeGreaterThanOrEqual(15)
    expect(path.at(-1)!.x).toBeCloseTo(15.5)
  })

  it('takes the shortest way (about the length of the detour through the gap)', () => {
    const path = findPath(map, v(5.5, 5.5), v(15.5, 5.5))
    let length = 0
    let from = v(5.5, 5.5)
    for (const point of path) {
      length += from.distanceTo(point)
      from = point
    }
    // the ideal way hugs the wall's end: about 21.7; via the cell centres next to it a bit more
    expect(length).toBeGreaterThan(21)
    expect(length).toBeLessThan(24)
  })

  it('ends next to a target that lies inside a wall', () => {
    const path = findPath(map, v(5.5, 5.5), v(10.5, 5.5))
    const end = path.at(-1)!
    expect(map.free(Math.floor(end.x), Math.floor(end.z))).toBe(true)
  })
})
