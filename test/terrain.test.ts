import { describe, expect, it } from 'vitest'
import { Cell, LEVEL_HEIGHT, RAMP_LENGTH, STEP, Terrain } from '../app/lib/game/terrain'

/** A plateau (level 1) on the corners x ≥ 5, a straight cliff on the cells x = 4 */
function plateau() {
  const t = new Terrain(0, 0, 10, 8)
  for (let pz = 0; pz <= 8; pz++) for (let px = 5; px <= 10; px++) t.setCorner(px, pz, 1)
  return t
}

describe('terrain', () => {
  it('makes the cells between levels rock, a whole cell wide, that nobody crosses', () => {
    const t = plateau()
    expect(t.cell(4, 3)).toBe(Cell.Rock)
    expect(t.cell(3, 3)).toBe(Cell.Flat)
    expect(t.cell(5, 3)).toBe(Cell.Flat)
    expect(t.planeAt(4.5, 3.5)).toBeCloseTo(LEVEL_HEIGHT / 2)
    expect(t.passable(3, 3, 1, 0)).toBe(false)
    expect(t.flatLevel(5, 0, 3, 3)).toBe(1)
    expect(t.flatLevel(3, 0, 3, 3)).toBeUndefined()
  })

  it('leaves flat ground flat and rounds the folds of a slope', () => {
    const t = plateau()
    expect(t.heightAt(1.3, 3.7)).toBe(0)
    expect(t.heightAt(7.3, 3.7)).toBeCloseTo(LEVEL_HEIGHT, 6)
    // just below the rim: lower than the plateau, higher than the plain slope there
    const rim = t.heightAt(4.97, 3.5)
    expect(rim).toBeLessThan(LEVEL_HEIGHT)
    expect(rim).toBeGreaterThan(t.planeAt(4.6, 3.5))
  })

  it('cuts a corner diagonally across a cell', () => {
    const t = new Terrain(0, 0, 6, 6)
    for (const [px, pz] of [[2, 2], [3, 2], [2, 3]]) t.setCorner(px!, pz!, 1)
    // cell (2, 2): three corners up, the one at (3, 3) down: the rim runs from (3, 2) to (2, 3)
    expect(t.cell(2, 2)).toBe(Cell.Rock)
    expect(t.planeAt(2.4, 2.4)).toBeCloseTo(LEVEL_HEIGHT)
    expect(t.planeAt(2.75, 2.75)).toBeCloseTo(LEVEL_HEIGHT / 2)
  })

  it('lets units up a ramp, not over the rock beside it', () => {
    const t = plateau()
    // a ramp up the cliff at z = 3, 4: the cliff's cells (x = 4) and the three below them, a step each
    expect(RAMP_LENGTH).toBe(1 / STEP)
    for (let k = 0; k <= RAMP_LENGTH; k++) for (let pz = 3; pz <= 5; pz++) t.setCorner(5 - k, pz, 1 - k / RAMP_LENGTH)
    for (let x = 1; x <= 4; x++) for (const z of [3, 4]) t.setRamp(x, z, true)
    expect(t.planeAt(3, 3.5)).toBeCloseTo(LEVEL_HEIGHT / 2)
    expect(t.corner(2, 3)).toBe(STEP)
    expect(t.passable(0, 3, 1, 0)).toBe(true) // onto the foot of the ramp
    expect(t.passable(2, 3, 1, 0)).toBe(true) // up along it
    expect(t.passable(4, 3, 1, 0)).toBe(true) // off its top onto the plateau
    expect(t.passable(4, 2, 1, 0)).toBe(false) // the cliff beside it
    expect(t.passable(3, 4, 0, 1)).toBe(false) // down the ramp's side
  })

  it('lets units over the slope of a terrace, not build on it', () => {
    const t = new Terrain(0, 0, 10, 8)
    // a terrace one step up on the corners x ≥ 5
    for (let pz = 0; pz <= 8; pz++) for (let px = 5; px <= 10; px++) t.setCorner(px, pz, STEP)
    expect(t.cell(4, 3)).toBe(Cell.Slope)
    expect(t.passable(3, 3, 1, 0)).toBe(true)
    expect(t.passable(4, 3, 1, 0)).toBe(true)
    expect(t.flatLevel(3, 0, 3, 3)).toBeUndefined()
    expect(t.flatLevel(5, 0, 3, 3)).toBe(STEP)
  })

  it('generates plateaus that can all be reached, and keeps the flat zones flat', () => {
    const zone = { x: 30, z: 30, w: 8, h: 8 }
    for (const seed of [1, 7, 23, 99]) {
      const t = Terrain.generate(0, 0, 80, 80, { seed, flat: [zone] })
      expect(t.flatLevel(zone.x, zone.z, zone.w, zone.h)).toBe(0)
      expect(new Set(t.heights).size).toBeGreaterThan(1)
      const reached = t.reachable(zone.x, zone.z)
      let rock = 0
      let slope = 0
      for (let z = 0; z < 80; z++) {
        for (let x = 0; x < 80; x++) {
          const cell = t.cell(x, z)
          if (cell === Cell.Slope) slope++
          if (cell === Cell.Rock) rock++
          else expect(reached[z * 80 + x], `cell ${x},${z} (seed ${seed})`).toBe(1)
          // no cell climbs more than one level (and a terrace's step)
          const corners = t.corners(x, z)
          expect(Math.max(...corners) - Math.min(...corners)).toBeLessThanOrEqual(1 + STEP)
          // terraces in quarter levels (ramps climb in thirds, on rock and ramps)
          if (cell === Cell.Flat || cell === Cell.Slope) for (const c of corners) expect((c / STEP) % 1).toBeCloseTo(0, 6)
        }
      }
      expect(rock).toBeGreaterThan(0)
      expect(slope).toBeGreaterThan(0)
      // along the cliffs the ground lies on its level, a cell wide, before a terrace
      for (let z = 1; z < 79; z++) {
        for (let x = 1; x < 79; x++) {
          // (the rock beside a ramp climbs with it)
          if (t.cell(x, z) !== Cell.Rock || t.corners(x, z).some(c => c % 1 !== 0)) continue
          for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]] as const) {
            const cell = t.cell(x + dx, z + dz)
            if (cell === Cell.Flat) expect(t.corner(x + dx, z + dz) % 1, `beside ${x},${z} (seed ${seed})`).toBe(0)
            else if (![-1, 0, 1].some(i => [-1, 0, 1].some(j => t.ramp(x + dx + i, z + dz + j)))) {
              expect(cell, `beside ${x},${z} (seed ${seed})`).not.toBe(Cell.Slope)
            }
          }
        }
      }
    }
  })
})
