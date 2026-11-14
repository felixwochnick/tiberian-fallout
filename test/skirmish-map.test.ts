import { describe, expect, it } from 'vitest'
import { skirmishLayout, unfairness } from '../app/lib/game/skirmish-map'
import { type FlatZone, Terrain } from '../app/lib/game/terrain'

const SIZE: [number, number] = [128, 128]
const distance = (a: { u: number, v: number }, b: { u: number, v: number }) => Math.hypot(a.u - b.u, a.v - b.v)

describe('skirmish map', () => {
  for (const players of [2, 3, 4, 5, 8]) {
    it(`${players} players: every start as far from the middle, from its neighbours and from its own fields`, () => {
      const { starts, fields } = skirmishLayout(players, SIZE)
      const middle = { u: 64, v: 64 }
      expect(starts).toHaveLength(players)
      const fromMiddle = starts.map(s => distance(s, middle))
      expect(Math.max(...fromMiddle) - Math.min(...fromMiddle)).toBeLessThan(1e-9)
      const neighbours = starts.map((s, i) => distance(s, starts[(i + 1) % players]!))
      expect(Math.max(...neighbours) - Math.min(...neighbours)).toBeLessThan(1e-9)
      // on the map, with room for a base towards every edge
      for (const s of starts) {
        expect(Math.min(s.u, s.v, 128 - s.u, 128 - s.v)).toBeGreaterThan(15)
      }
      // each start's own fields: the same, at the same distances
      const own = starts.map((s, i) => fields.filter(f => f.start === i).map(f => `${f.kind} ${f.radius} ${distance(f, s).toFixed(6)}`).join())
      expect(new Set(own).size).toBe(1)
      // the fields fought over: as far from the two starts beside them (and the middle one from all)
      for (const field of fields.filter(f => f.start === undefined)) {
        const near = starts.map(s => distance(field, s)).sort((a, b) => a - b)
        expect(near[1]! - near[0]!).toBeLessThan(1e-9)
      }
    })
  }

  it('alike round the middle: the ground at mirrored cells is the same', () => {
    // a square of world cells, the middle at (40, 40), four starts on the diagonals
    const symmetry = { x: 40, z: 40, order: 4, angle: Math.PI / 4 }
    const t = Terrain.generate(0, 0, 80, 80, { seed: 7, symmetry })
    let same = 0
    let all = 0
    for (let z = 0; z < 80; z++) {
      for (let x = 0; x < 80; x++) {
        // turned by 90° round the middle
        const [rx, rz] = [79 - z, x]
        all++
        if (t.level(x, z) === t.level(rx, rz)) same++
      }
    }
    // the ramps (and what is smoothed round them) come by chance, the rest is alike
    expect(same / all).toBeGreaterThan(0.85)
  })

  for (const players of [2, 4, 6]) {
    it(`${players} players: the ground gives no start much longer ways`, () => {
      const { starts, fields, ways } = skirmishLayout(players, SIZE)
      // the map's screen axes to world cells, as the battlefield lays them out (turned by 45°)
      const c = Math.SQRT1_2
      const world = ({ u, v }: { u: number, v: number }) => [Math.round(c * u + c * v), Math.round(-c * u + c * v)] as const
      // the cells round the map, as Battlefield lays them out for 128 × 128
      const [x0, z0, w, h] = [-1, -92, 183, 184]
      const inside = (x: number, z: number) => {
        const u = c * (x + 0.5) - c * (z + 0.5)
        const v = c * (x + 0.5) + c * (z + 0.5)
        return u >= 0 && u <= 128 && v >= 0 && v <= 128
      }
      const around = ([x, z]: readonly [number, number], r: number): FlatZone => ({ x: x - r, z: z - r, w: 2 * r + 1, h: 2 * r + 1 })
      const startCells = starts.map(world)
      const middle = world({ u: 64, v: 64 })
      const flat = [around(middle, 4), ...startCells.map(s => around(s, 6)), ...fields.map(f => around(world(f), Math.ceil(f.radius) + 1)),
        ...ways.map(w => around(world(w), 0))]
      const goals = startCells.map((_, i) => [middle, ...fields.filter(f => f.start === i).map(world), startCells[(i + 1) % players]!])
      const t = Terrain.generate(x0, z0, w, h, {
        seed: 11, flat, inside,
        symmetry: { x: middle[0], z: middle[1], order: players, angle: Math.atan2(startCells[0]![1] - middle[1], startCells[0]![0] - middle[0]) },
      })
      // the battlefield takes it up to a share of 0.1 (FAIR_ENOUGH), else it shapes the ground anew
      expect(unfairness(t, startCells, goals, inside)).toBeLessThan(0.1)
    }, 20000)
  }

  it('a start that cannot get to its goals is as unfair as can be', () => {
    // a plateau with a ring of cliff round the second start, no ramp (Terrain.generate would add one)
    const t = new Terrain(0, 0, 40, 20)
    for (let z = 4; z <= 16; z++) for (let x = 24; x <= 36; x++) t.setCorner(x, z, 1)
    const inside = () => true
    expect(unfairness(t, [[5, 10], [30, 10]], [[[20, 2]], [[20, 2]]], inside)).toBe(Infinity)
    expect(unfairness(t, [[5, 10], [12, 10]], [[[20, 2]], [[20, 2]]], inside)).toBeLessThan(0.1)
  })
})
