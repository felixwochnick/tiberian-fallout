import { describe, expect, it } from 'vitest'
import { groundCover, scatterProps, type Theater } from '../app/lib/game/landscape'
import { Cell, Terrain } from '../app/lib/game/terrain'

const SIZE = 64

/** The open cells reachable from (x, z) over passable steps, not through the blocked ones */
function reach(t: Terrain, x: number, z: number, blocked: Set<string>) {
  const seen = new Set([`${x},${z}`])
  const stack: [number, number][] = [[x, z]]
  while (stack.length) {
    const [cx, cz] = stack.pop()!
    for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]] as const) {
      const [nx, nz] = [cx + dx, cz + dz]
      const key = `${nx},${nz}`
      if (nx < 0 || nz < 0 || nx >= SIZE || nz >= SIZE || seen.has(key) || blocked.has(key) || !t.passable(cx, cz, dx, dz)) continue
      seen.add(key)
      stack.push([nx, nz])
    }
  }
  return seen
}

describe('landscape', () => {
  for (const theater of ['temperate', 'snow'] as Theater[]) {
    for (const seed of [3, 17, 4242]) {
      it(`${theater}, seed ${seed}: the trees and rocks never cut a way, and keep off the bases`, () => {
        const base = { x: 28, z: 28, w: 8, h: 8 }
        const t = Terrain.generate(0, 0, SIZE, SIZE, { seed, flat: [base] })
        const cover = groundCover(t, theater, seed)
        const props = scatterProps(t, theater, seed, cover, { onMap: (x, z) => x >= 0 && z >= 0 && x < SIZE && z < SIZE, keep: [base] })
        expect(props.length).toBeGreaterThan(40)
        const blocked = new Set(props.filter(p => p.blocks).map(p => `${p.x},${p.z}`))
        const before = reach(t, 30, 30, new Set())
        const after = reach(t, 30, 30, blocked)
        // every cell reachable before still is, but for those the objects stand on
        for (const key of before) {
          if (!blocked.has(key)) expect(after.has(key), key).toBe(true)
        }
        for (const p of props) {
          expect(t.cell(p.x, p.z)).toBe(Cell.Flat)
          expect(p.x >= base.x - 2 && p.x < base.x + base.w + 2 && p.z >= base.z - 2 && p.z < base.z + base.h + 2).toBe(false)
        }
      })
    }
  }
})
