import { describe, expect, it } from 'vitest'
import { wallLinks, type WallMap } from '../app/lib/game/walls'

/** A map with wall pieces on `pieces` and nothing to build on at `blocked` ("x,z") */
const map = (pieces: [number, number][], blocked: [number, number][] = []): WallMap => ({
  piece: (x, z) => pieces.some(([px, pz]) => px === x && pz === z),
  free: (x, z) => !pieces.concat(blocked).some(([bx, bz]) => bx === x && bz === z),
})
const sorted = (cells: [number, number][]) => [...cells].sort(([ax, az], [bx, bz]) => ax - bx || az - bz)

// measured in the original (GDI concrete wall, GuardRange=5)
describe('wall links', () => {
  it('walls up the 4 cells between two pieces 5 cells apart', () => {
    expect(sorted(wallLinks(15, 10, 5, map([[10, 10]])))).toEqual([[11, 10], [12, 10], [13, 10], [14, 10]])
  })

  it('leaves a gap of 5 cells open', () => {
    expect(wallLinks(16, 10, 5, map([[10, 10]]))).toEqual([])
  })

  it('has nothing to wall up next to a piece', () => {
    expect(wallLinks(11, 10, 5, map([[10, 10]]))).toEqual([])
  })

  it('does not link up diagonally', () => {
    expect(wallLinks(13, 13, 5, map([[10, 10]]))).toEqual([])
  })

  it('links up in every direction at once', () => {
    const cells = wallLinks(10, 10, 5, map([[7, 10], [10, 15], [12, 10]]))
    expect(sorted(cells)).toEqual([[8, 10], [9, 10], [10, 11], [10, 12], [10, 13], [10, 14], [11, 10]])
  })

  it('leaves a side open when something is in the way', () => {
    expect(wallLinks(15, 10, 5, map([[10, 10]], [[12, 10]]))).toEqual([])
    // the other side still links up
    expect(sorted(wallLinks(15, 10, 5, map([[10, 10], [15, 13]], [[12, 10]])))).toEqual([[15, 11], [15, 12]])
  })

  it('stops at the nearest piece', () => {
    expect(sorted(wallLinks(15, 10, 5, map([[10, 10], [13, 10]])))).toEqual([[14, 10]])
  })

  it('does not link up without a range (the sandbags)', () => {
    expect(wallLinks(12, 10, 0, map([[10, 10]]))).toEqual([])
  })
})
