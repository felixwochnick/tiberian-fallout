/**
 * The ground's height levels, like in Tiberian Sun: the ground lies on levels (0, 1,
 * 2 …), plateaus end in cliffs, and ramps lead from one level up to the next. One
 * level is LEVEL_HEIGHT cells high: a cliff towers over a construction yard, like the
 * original's four-level cliffs.
 *
 * Heights belong to the corners of the cells (the grid points), as in the original. A
 * cell whose four corners lie on one level is flat; a cell whose corners differ is
 * rock, a cliff a whole cell wide: straight (two corners up), cut across (three up:
 * the cliff turns or runs diagonally, so plateaus have rounded corners and slanting
 * sides) or the foot of such a turn (one up). Nobody walks or builds on rock. A ramp
 * is a strip of cells two wide and RAMP_LENGTH long whose corners rise evenly by one
 * level, a terrace's step (STEP) a cell: four slopes one after the other; its cells
 * are open. Units go from a cell to its neighbour where both are open
 * and meet at the same height along their whole shared edge.
 *
 * Between the levels the ground steps in terraces of a quarter level (STEP), like the
 * original's low ledges: a cell whose corners differ by such a step is a slope, rough
 * and rocky to look at, but units cross it (nothing is built on it).
 *
 * Cell (x, z) covers x … x+1, z … z+1; the terrain covers `width` × `depth` cells from
 * (x0, z0). Outside it the ground is flat at level 0.
 */

export const LEVEL_HEIGHT = 1.25

/** Terraces a level is divided into: the ground also lies a STEP, 2 STEP … above a level */
export const STEPS = 4
/** Height of a terrace's step (levels) */
export const STEP = 1 / STEPS

/** Cells a ramp takes to climb one level: each climbs a terrace's step */
export const RAMP_LENGTH = STEPS

/** What a cell is: open ground on one level, a ramp, rock (a cliff) or the slope of a terrace's step */
export const Cell = { Flat: 0, Ramp: 1, Rock: 2, Slope: 3 } as const
export type Cell = typeof Cell[keyof typeof Cell]

/** A rectangle of cells that has to stay flat on level 0 (a base, a Tiberium field, a landing spot) */
export interface FlatZone { x: number, z: number, w: number, h: number }

export interface TerrainOptions {
  seed?: number
  /** Highest level (default 2) */
  levels?: number
  /** Cells kept flat on level 0, with a margin round them */
  flat?: FlatZone[]
  /** Free cells round a flat zone before the ground may rise (default 3) */
  margin?: number
  /** Size of the hills in cells (default 16) */
  scale?: number
  /** How much of the map rises above level 0 (0 … 1, default 0.45) */
  hilliness?: number
  /** The cells units can go on (the map); only these have to be reached (default: all) */
  inside?: (x: number, z: number) => boolean
}

export class Terrain {
  /** Height (levels) of every corner: (width + 1) × (depth + 1) */
  readonly heights: Float32Array
  /** The cells that are part of a ramp */
  readonly ramps: Uint8Array
  /** Height of every corner's terrace above its level (levels, in STEPs; included in `heights`) */
  readonly terraces: Float32Array
  /** The cells units can go on: the ways between the levels are worked out over these */
  private inside: (x: number, z: number) => boolean = () => true

  constructor(readonly x0: number, readonly z0: number, readonly width: number, readonly depth: number) {
    this.heights = new Float32Array((width + 1) * (depth + 1))
    this.ramps = new Uint8Array(width * depth)
    this.terraces = new Float32Array((width + 1) * (depth + 1))
  }

  private index(x: number, z: number) {
    const i = x - this.x0
    const j = z - this.z0
    return i < 0 || j < 0 || i >= this.width || j >= this.depth ? -1 : j * this.width + i
  }

  private cornerIndex(px: number, pz: number) {
    const i = px - this.x0
    const j = pz - this.z0
    return i < 0 || j < 0 || i > this.width || j > this.depth ? -1 : j * (this.width + 1) + i
  }

  /** Height (levels) of a corner (grid point) */
  corner(px: number, pz: number) {
    const i = this.cornerIndex(px, pz)
    return i < 0 ? 0 : this.heights[i]!
  }

  setCorner(px: number, pz: number, level: number) {
    const i = this.cornerIndex(px, pz)
    if (i >= 0) this.heights[i] = level
  }

  /** Height of a corner's terrace above its level (levels) */
  terrace(px: number, pz: number) {
    const i = this.cornerIndex(px, pz)
    return i < 0 ? 0 : this.terraces[i]!
  }

  /** A corner's level without its terrace: the levels the cliffs and ramps lie between */
  main(px: number, pz: number) {
    return this.corner(px, pz) - this.terrace(px, pz)
  }

  /** Levels of a cell's corners: (x, z), (x+1, z), (x, z+1), (x+1, z+1) */
  corners(x: number, z: number): [number, number, number, number] {
    return [this.corner(x, z), this.corner(x + 1, z), this.corner(x, z + 1), this.corner(x + 1, z + 1)]
  }

  /** Whether a cell is part of a ramp */
  ramp(x: number, z: number) {
    const i = this.index(x, z)
    return i >= 0 && this.ramps[i] === 1
  }

  setRamp(x: number, z: number, ramp: boolean) {
    const i = this.index(x, z)
    if (i >= 0) this.ramps[i] = ramp ? 1 : 0
  }

  cell(x: number, z: number): Cell {
    if (this.ramp(x, z)) return Cell.Ramp
    const [a, b, c, d] = this.corners(x, z)
    if (a === b && a === c && a === d) return Cell.Flat
    return Math.max(a, b, c, d) - Math.min(a, b, c, d) <= STEP + 1e-6 ? Cell.Slope : Cell.Rock
  }

  /** The lowest level a cell touches (a flat cell: its level) */
  level(x: number, z: number) {
    return Math.min(...this.corners(x, z))
  }

  /**
   * Whether a cell is split into its two triangles along the diagonal from (x, z) to
   * (x+1, z+1) (else from (x+1, z) to (x, z+1)): along the one whose ends differ less,
   * so a corner on its own (a cliff cut across the cell) gets a triangle to itself
   */
  static splitsMain(a: number, b: number, c: number, d: number) {
    return Math.abs(a - d) < Math.abs(b - c)
  }

  /**
   * Height of the ground (cells) at a point: on flat ground its level; near cliffs and
   * ramps the corners' plane (planeAt) shaped like ground, not like a model: the folds
   * at the top and the foot of a slope rounded off (averaged over SMOOTH_RADIUS), the
   * line of a rim or a foot wavering a little (WARP), and a slope rough with bumps
   * (BUMP, as much as it falls round the point). The ground's mesh is made of it.
   */
  heightAt(px: number, pz: number) {
    const x = Math.floor(px)
    const z = Math.floor(pz)
    // flat all round: nothing to shape
    const level = this.corner(x, z)
    if (this.flatAround(x, z, level)) return level * LEVEL_HEIGHT
    const qx = px + (smoothNoise(px * 0.8, pz * 0.8) - 0.5) * 2 * WARP
    const qz = pz + (smoothNoise(px * 0.8 + 37.1, pz * 0.8 + 11.3) - 0.5) * 2 * WARP
    let sum = 0
    let weights = 0
    let low = Infinity
    let high = -Infinity
    for (let i = -2; i <= 2; i++) {
      for (let j = -2; j <= 2; j++) {
        const w = (3 - Math.abs(i)) * (3 - Math.abs(j))
        const h = this.planeAt(qx + i * SMOOTH_RADIUS / 2, qz + j * SMOOTH_RADIUS / 2)
        sum += h * w
        weights += w
        low = Math.min(low, h)
        high = Math.max(high, h)
      }
    }
    const rough = Math.min(1, (high - low) / (0.3 * LEVEL_HEIGHT))
    const bump = (smoothNoise(px * 3.1, pz * 3.1) - 0.5) * 0.7 + (smoothNoise(px * 7.3 + 5, pz * 7.3 + 9) - 0.5) * 0.3
    return sum / weights + bump * 2 * BUMP * rough
  }

  /** Whether the cells within two of (x, z) are all flat on `level` (far enough from any slope to be left as it is) */
  flatAround(x: number, z: number, level: number) {
    for (let j = z - 2; j <= z + 2; j++) {
      for (let i = x - 2; i <= x + 2; i++) {
        if (this.cell(i, j) !== Cell.Flat || this.corner(i, j) !== level) return false
      }
    }
    return true
  }

  /** Height of the ground (cells) at a point on the plain triangles between the cells' corners */
  planeAt(px: number, pz: number) {
    const x = Math.floor(px)
    const z = Math.floor(pz)
    const [a, b, c, d] = this.corners(x, z)
    const fx = px - x
    const fz = pz - z
    // a ramp's cell is one of its four steps: flat where it meets the next one, steep in
    // its middle, like a terrace's slope
    if (this.ramp(x, z)) {
      if (a === c && b === d) return (a + (b - a) * step(fx)) * LEVEL_HEIGHT
      if (a === b && c === d) return (a + (c - a) * step(fz)) * LEVEL_HEIGHT
    }
    let level: number
    if (Terrain.splitsMain(a, b, c, d)) {
      // triangles (a, b, d) with fx ≥ fz and (a, d, c)
      level = fx >= fz ? a + (b - a) * fx + (d - b) * fz : a + (c - a) * fz + (d - c) * fx
    }
    else {
      // triangles (a, b, c) with fx + fz ≤ 1 and (b, d, c)
      level = fx + fz <= 1 ? a + (b - a) * fx + (c - a) * fz : d + (c - d) * (1 - fx) + (b - d) * (1 - fz)
    }
    return level * LEVEL_HEIGHT
  }

  /** Levels of the two corners of a cell's edge towards (dx, dz) (one of them 0), in a fixed order */
  edge(x: number, z: number, dx: number, dz: number): [number, number] {
    const [a, b, c, d] = this.corners(x, z)
    if (dx > 0) return [b, d]
    if (dx < 0) return [a, c]
    if (dz > 0) return [c, d]
    return [a, b]
  }

  /** Whether one can go from a cell straight to its neighbour (dx, dz one step, diagonals too) */
  passable(x: number, z: number, dx: number, dz: number): boolean {
    if (dx && dz) {
      // a diagonal step: both ways round the corner must be open
      return this.passable(x, z, dx, 0) && this.passable(x + dx, z, 0, dz)
        && this.passable(x, z, 0, dz) && this.passable(x, z + dz, dx, 0)
    }
    if (this.cell(x, z) === Cell.Rock || this.cell(x + dx, z + dz) === Cell.Rock) return false
    const [a, b] = this.edge(x, z, dx, dz)
    const [c, d] = this.edge(x + dx, z + dz, -dx, -dz)
    return a === c && b === d
  }

  /** The level of a rectangle of cells if it is all flat on one level (a building's foundation), else undefined */
  flatLevel(x: number, z: number, w: number, h: number) {
    const level = this.corner(x, z)
    for (let i = x; i < x + w; i++) {
      for (let j = z; j < z + h; j++) {
        if (this.cell(i, j) !== Cell.Flat || this.corner(i, j) !== level) return undefined
      }
    }
    return level
  }

  /** The cells reachable on foot from (x, z) */
  reachable(x: number, z: number) {
    const seen = new Uint8Array(this.width * this.depth)
    const stack: [number, number][] = [[x, z]]
    seen[this.index(x, z)] = 1
    while (stack.length) {
      const [cx, cz] = stack.pop()!
      for (const [dx, dz] of NEIGHBOURS_4) {
        const i = this.index(cx + dx, cz + dz)
        if (i < 0 || seen[i] || !this.inside(cx + dx, cz + dz) || !this.passable(cx, cz, dx, dz)) continue
        seen[i] = 1
        stack.push([cx + dx, cz + dz])
      }
    }
    return seen
  }

  /**
   * Rolling plateaus and cliffs from smooth noise, the flat zones (with their margin) on
   * level 0, steps of at most one level, no plateaus or gaps too small, and ramps that
   * connect every part of the map to the rest.
   *
   * The levels are first worked out per cell (a plateau: the cells on it); a corner then
   * takes the second highest level of the four cells round it, so the cliffs come to
   * lie on the cells round a plateau, cut across where its outline steps diagonally.
   */
  static generate(x0: number, z0: number, width: number, depth: number, options: TerrainOptions = {}) {
    const { seed = 1, levels = 2, flat = [], margin = 3, scale = 16, hilliness = 0.45, inside = () => true } = options
    const random = mulberry32(seed)
    const noise = valueNoise(random)
    const kept = (x: number, z: number) => flat.some(f =>
      x >= f.x - margin && x < f.x + f.w + margin && z >= f.z - margin && z < f.z + f.h + margin)

    const cells = new CellLevels(x0, z0, width, depth)
    // levels from noise: the lower part of its range stays level 0
    for (let z = z0; z < z0 + depth; z++) {
      for (let x = x0; x < x0 + width; x++) {
        if (kept(x, z)) continue
        const n = (noise(x / scale, z / scale) * 0.7 + noise(x / scale * 2.3 + 17, z / scale * 2.3 + 5) * 0.3)
        const t = (n - (1 - hilliness)) / hilliness
        cells.set(x, z, t <= 0 ? 0 : Math.min(levels, 1 + Math.floor(t * levels)))
      }
    }
    for (let pass = 0; pass < 4; pass++) {
      cells.limitSteps()
      cells.removeSlivers()
      cells.removeSmallRegions(16)
    }
    cells.limitSteps()

    const terrain = new Terrain(x0, z0, width, depth)
    terrain.inside = inside
    for (let pz = z0; pz <= z0 + depth; pz++) {
      for (let px = x0; px <= x0 + width; px++) {
        const round = [cells.get(px - 1, pz - 1), cells.get(px, pz - 1), cells.get(px - 1, pz), cells.get(px, pz)].sort((a, b) => b - a)
        terrain.setCorner(px, pz, round[1]!)
      }
    }
    terrain.limitCells()
    terrain.connect(random, kept)
    terrain.addTerraces(noise, kept)
    return terrain
  }

  /**
   * Terraces from smooth noise: the ground rises or sinks by up to STEPS - 1 steps from
   * its level, in low ledges on the plains and on top of the plateaus alike. They keep
   * to the whole levels: along a cliff (and round the ramps and in the flat zones) the
   * ground lies on its level, at least a cell wide, before a terrace rises or sinks.
   * Neighbouring cells differ by at most one step, so a terrace's edge is a slope one
   * cell wide that units cross. Worked out per cell, like the levels: no terraces too
   * small or too narrow.
   */
  private addTerraces(noise: (x: number, z: number) => number, kept: (x: number, z: number) => boolean) {
    const nearRamp = (x: number, z: number) => {
      for (let j = z - 2; j <= z + 2; j++) for (let i = x - 2; i <= x + 2; i++) if (this.ramp(i, j)) return true
      return false
    }
    const nearRock = (x: number, z: number) => {
      for (let j = z - 2; j <= z + 2; j++) for (let i = x - 2; i <= x + 2; i++) if (this.cell(i, j) === Cell.Rock) return true
      return false
    }
    // within two cells of a cliff: the cell beside it flat on the level, the next one may be a terrace's slope
    const pinned = (x: number, z: number) => kept(x, z) || nearRamp(x, z) || nearRock(x, z)
    // per cell first, in broad areas without slivers, as the levels
    const cells = new CellLevels(this.x0, this.z0, this.width, this.depth)
    for (let z = this.z0; z < this.z0 + this.depth; z++) {
      for (let x = this.x0; x < this.x0 + this.width; x++) {
        if (pinned(x, z)) continue
        const n = noise(x / TERRACE_SCALE + 91.3, z / TERRACE_SCALE + 53.7) * 0.85
          + noise(x / TERRACE_SCALE * 2.2 + 13.1, z / TERRACE_SCALE * 2.2 + 71.9) * 0.15
        // -1 … 1 over the noise's middle range: down, on the level, up
        const t = Math.max(-1, Math.min(1, (n - 0.5) / (0.5 - TERRACE_FROM)))
        cells.set(x, z, Math.round(t * (STEPS - 1)))
      }
    }
    for (let pass = 0; pass < 3; pass++) {
      cells.limitTowardsZero()
      cells.removeSlivers()
      cells.removeSmallRegions(24)
    }
    for (let z = this.z0; z < this.z0 + this.depth; z++) {
      for (let x = this.x0; x < this.x0 + this.width; x++) if (pinned(x, z)) cells.set(x, z, 0)
    }
    cells.limitTowardsZero()
    // a corner: the second highest of the cells round it, so a terrace's edge is a slope one cell wide
    for (let pz = this.z0; pz <= this.z0 + this.depth; pz++) {
      for (let px = this.x0; px <= this.x0 + this.width; px++) {
        const round = [cells.get(px - 1, pz - 1), cells.get(px, pz - 1), cells.get(px - 1, pz), cells.get(px, pz)].sort((a, b) => b - a)
        const i = this.cornerIndex(px, pz)
        this.terraces[i] = round[1]! * STEP
        this.heights[i] = this.heights[i]! + this.terraces[i]!
      }
    }
  }

  /** No cell climbs more than one level: corners higher than that come down */
  private limitCells() {
    for (let changed = true; changed;) {
      changed = false
      for (let z = this.z0 - 1; z <= this.z0 + this.depth; z++) {
        for (let x = this.x0 - 1; x <= this.x0 + this.width; x++) {
          const low = this.level(x, z)
          for (const [px, pz] of [[x, z], [x + 1, z], [x, z + 1], [x + 1, z + 1]] as const) {
            if (this.corner(px, pz) > low + 1) {
              this.setCorner(px, pz, low + 1)
              changed = true
            }
          }
        }
      }
    }
  }

  /** Connected areas of flat cells on one level (4 neighbours, ramps not included) */
  private flatRegions() {
    const seen = new Uint8Array(this.width * this.depth)
    const result: { level: number, cells: [number, number][] }[] = []
    for (let z = this.z0; z < this.z0 + this.depth; z++) {
      for (let x = this.x0; x < this.x0 + this.width; x++) {
        if (seen[this.index(x, z)] || this.cell(x, z) !== Cell.Flat) continue
        const level = this.corner(x, z)
        const cells: [number, number][] = []
        const stack: [number, number][] = [[x, z]]
        seen[this.index(x, z)] = 1
        while (stack.length) {
          const [cx, cz] = stack.pop()!
          cells.push([cx, cz])
          for (const [dx, dz] of NEIGHBOURS_4) {
            const nx = cx + dx
            const nz = cz + dz
            const i = this.index(nx, nz)
            if (i < 0 || seen[i] || this.cell(nx, nz) !== Cell.Flat || this.corner(nx, nz) !== level) continue
            seen[i] = 1
            stack.push([nx, nz])
          }
        }
        result.push({ level, cells })
      }
    }
    return result
  }

  /** Whether every open cell (flat or ramp) is among the `reached` */
  private allReached(reached: Uint8Array) {
    for (let z = this.z0; z < this.z0 + this.depth; z++) {
      for (let x = this.x0; x < this.x0 + this.width; x++) {
        if (!reached[this.index(x, z)] && this.inside(x, z) && this.cell(x, z) !== Cell.Rock) return false
      }
    }
    return true
  }

  /**
   * Ramps until every part of the map can be reached from the rest: each time one on
   * a cliff between the reached part and a part not yet reached; then more ramps onto
   * the bigger plateaus (one for every RAMP_CELLS of their cells), far apart, so there
   * is no long way round to the next one.
   */
  private connect(random: () => number, kept: (x: number, z: number) => boolean) {
    const start = this.flatRegions().sort((a, b) => b.cells.length - a.cells.length)
      .find(r => r.level === 0 && r.cells.some(([x, z]) => this.inside(x, z)))?.cells.find(([x, z]) => this.inside(x, z)) ?? [this.x0, this.z0]
    for (let tries = 0; tries < 400; tries++) {
      const reached = this.reachable(...start)
      if (this.allReached(reached)) break
      if (this.addRamp(random, kept, (i, j) => reached[i] !== reached[j], start)) continue
      // no room for a ramp (a narrow hollow, a small plateau): it is levelled with the ground round it
      if (!this.fillUnreached(reached)) break
    }
    for (const region of this.flatRegions()) {
      if (region.level === 0 || region.cells.length < 40) continue
      const inside = new Set(region.cells.map(([x, z]) => this.index(x, z)))
      for (let i = 0; i < Math.round(region.cells.length / RAMP_CELLS); i++) {
        if (!this.addRamp(random, kept, (i, j) => inside.has(i) !== inside.has(j), start, true)) break
      }
    }
  }

  /**
   * The open cells not reached, and the rock round them, are levelled with the reached
   * ground near them (corners shared with reached cells stay); returns whether
   * anything changed
   */
  private fillUnreached(reached: Uint8Array) {
    const isReached = (x: number, z: number) => this.index(x, z) >= 0 && reached[this.index(x, z)] === 1
    let changed = false
    for (let z = this.z0; z < this.z0 + this.depth; z++) {
      for (let x = this.x0; x < this.x0 + this.width; x++) {
        if (isReached(x, z) || !this.inside(x, z) || this.cell(x, z) === Cell.Rock) continue
        // the most common level of the reached cells near it
        const near = new Map<number, number>()
        for (let j = z - 3; j <= z + 3; j++) {
          for (let i = x - 3; i <= x + 3; i++) {
            if (isReached(i, j)) near.set(this.level(i, j), (near.get(this.level(i, j)) ?? 0) + 1)
          }
        }
        const level = [...near].sort((a, b) => b[1] - a[1])[0]?.[0] ?? 0
        // the cell and the rock round it
        for (let j = z - 1; j <= z + 1; j++) {
          for (let i = x - 1; i <= x + 1; i++) {
            if (isReached(i, j) || (this.cell(i, j) !== Cell.Rock && (i !== x || j !== z))) continue
            for (const [px, pz] of [[i, j], [i + 1, j], [i, j + 1], [i + 1, j + 1]] as const) {
              const touchesReached = isReached(px - 1, pz - 1) || isReached(px, pz - 1) || isReached(px - 1, pz) || isReached(px, pz)
              if (!touchesReached && this.corner(px, pz) !== level) {
                this.setCorner(px, pz, level)
                changed = true
              }
            }
            this.setRamp(i, j, false)
          }
        }
      }
    }
    if (changed) this.limitCells()
    return changed
  }

  /**
   * Places a ramp, two cells wide and RAMP_LENGTH long, up a straight cliff one level
   * high: its top cells are the cliff's, the others the flat cells below it, between
   * flat ground at the foot and on top. Where `across(foot, top)` (cell indices) holds;
   * far from the other ramps when `spread`. A ramp that would cut off cells reached
   * from `start` (its raised sides close a narrow pass) is not taken. Returns whether
   * one was found.
   */
  private addRamp(random: () => number, kept: (x: number, z: number) => boolean, across: (foot: number, top: number) => boolean,
    start: [number, number], spread = false) {
    const candidates: { x: number, z: number, dx: number, dz: number, sx: number, sz: number, level: number, score: number }[] = []
    // the ramps there are, to keep new ones away from them
    const ramps: [number, number][] = []
    if (spread) {
      for (let j = 0; j < this.depth; j++) {
        for (let i = 0; i < this.width; i++) {
          if (this.ramps[j * this.width + i]) ramps.push([this.x0 + i, this.z0 + j])
        }
      }
    }
    const flatAt = (x: number, z: number, level: number) => this.index(x, z) >= 0 && this.inside(x, z) && this.cell(x, z) === Cell.Flat && this.corner(x, z) === level
    // a straight cliff cell rising one level from `level` towards (dx, dz)
    const straight = (x: number, z: number, dx: number, dz: number, level: number) => {
      if (this.index(x, z) < 0 || !this.inside(x, z) || this.ramp(x, z)) return false
      const [l0, l1] = this.edge(x, z, -dx, -dz)
      const [h0, h1] = this.edge(x, z, dx, dz)
      return l0 === level && l1 === level && h0 === level + 1 && h1 === level + 1
    }
    for (let z = this.z0; z < this.z0 + this.depth; z++) {
      for (let x = this.x0; x < this.x0 + this.width; x++) {
        if (kept(x, z)) continue
        for (const [dx, dz] of NEIGHBOURS_4) {
          const level = this.edge(x, z, -dx, -dz)[0]
          if (!straight(x, z, dx, dz, level)) continue
          // the second lane beside it
          for (const side of [1, -1]) {
            const sx = dz * side
            const sz = dx * side
            const ok = [[x, z], [x + sx, z + sz]].every(([cx, cz]) =>
              straight(cx!, cz!, dx, dz, level) && !kept(cx!, cz!)
              && Array.from({ length: RAMP_LENGTH + 1 }, (_, k) => k + 1)
                .every(k => flatAt(cx! - dx * k, cz! - dz * k, level) && !kept(cx! - dx * k, cz! - dz * k))
              && flatAt(cx! + dx, cz! + dz, level + 1) && flatAt(cx! + dx * 2, cz! + dz * 2, level + 1))
            if (!ok || !across(this.index(x - dx * RAMP_LENGTH, z - dz * RAMP_LENGTH), this.index(x + dx, z + dz))) continue
            let score = random()
            if (spread) {
              const nearest = Math.min(...ramps.map(([rx, rz]) => Math.hypot(rx - x, rz - z)))
              if (nearest < RAMP_SPACING) continue
              score += nearest / 10
            }
            candidates.push({ x, z, dx, dz, sx, sz, level, score })
          }
        }
      }
    }
    const before = this.reachable(...start)
    for (const { x, z, dx, dz, sx, sz, level } of candidates.sort((a, b) => b.score - a.score).slice(0, 12)) {
      // the lines of corners across the ramp, from its top edge (k = 0) down to its foot
      const corners: { px: number, pz: number, k: number }[] = []
      for (let k = 0; k <= RAMP_LENGTH; k++) {
        const ox = x + (dx > 0 ? 1 : 0) - dx * k
        const oz = z + (dz > 0 ? 1 : 0) - dz * k
        for (let n = 0; n < 3; n++) {
          corners.push(dx ? { px: ox, pz: Math.min(z, z + sz) + n, k } : { px: Math.min(x, x + sx) + n, pz: oz, k })
        }
      }
      const saved = corners.map(({ px, pz }) => this.corner(px, pz))
      const lay = (ramp: boolean) => {
        for (let k = 0; k < RAMP_LENGTH; k++) {
          this.setRamp(x - dx * k, z - dz * k, ramp)
          this.setRamp(x + sx - dx * k, z + sz - dz * k, ramp)
        }
      }
      for (const { px, pz, k } of corners) this.setCorner(px, pz, level + 1 - k / RAMP_LENGTH)
      lay(true)
      // every open cell reached before still is (its raised sides turn the cells beside it to rock)
      const after = this.reachable(...start)
      const rock = (i: number) => this.cell(this.x0 + i % this.width, this.z0 + Math.floor(i / this.width)) === Cell.Rock
      if (before.every((r, i) => !r || after[i] || rock(i))) return true
      corners.forEach(({ px, pz }, i) => this.setCorner(px, pz, saved[i]!))
      lay(false)
    }
    return false
  }
}

/** The levels per cell the generator starts from, before they go to the corners */
class CellLevels {
  readonly levels: Int8Array

  constructor(readonly x0: number, readonly z0: number, readonly width: number, readonly depth: number) {
    this.levels = new Int8Array(width * depth)
  }

  private index(x: number, z: number) {
    const i = x - this.x0
    const j = z - this.z0
    return i < 0 || j < 0 || i >= this.width || j >= this.depth ? -1 : j * this.width + i
  }

  get(x: number, z: number) {
    const i = this.index(x, z)
    return i < 0 ? 0 : this.levels[i]!
  }

  set(x: number, z: number, level: number) {
    const i = this.index(x, z)
    if (i >= 0) this.levels[i] = level
  }

  /** Neighbours (also diagonal) differ by at most one level: higher cells come down */
  limitSteps() {
    for (let changed = true; changed;) {
      changed = false
      for (let z = this.z0; z < this.z0 + this.depth; z++) {
        for (let x = this.x0; x < this.x0 + this.width; x++) {
          const l = this.get(x, z)
          let lowest = l
          for (const [dx, dz] of NEIGHBOURS_8) lowest = Math.min(lowest, this.get(x + dx, z + dz))
          if (l - lowest > 1) {
            this.set(x, z, lowest + 1)
            changed = true
          }
        }
      }
    }
  }

  /**
   * Neighbours (also diagonal) differ by at most one: cells come towards 0 (raised ones
   * down, sunk ones up) until they do
   */
  limitTowardsZero() {
    for (let changed = true; changed;) {
      changed = false
      for (let z = this.z0; z < this.z0 + this.depth; z++) {
        for (let x = this.x0; x < this.x0 + this.width; x++) {
          const l = this.get(x, z)
          if (l === 0) continue
          let lowest = l
          let highest = l
          for (const [dx, dz] of NEIGHBOURS_8) {
            lowest = Math.min(lowest, this.get(x + dx, z + dz))
            highest = Math.max(highest, this.get(x + dx, z + dz))
          }
          const to = l > 0 ? Math.max(0, Math.min(l, lowest + 1)) : Math.min(0, Math.max(l, highest - 1))
          if (to !== l) {
            this.set(x, z, to)
            changed = true
          }
        }
      }
    }
  }

  /**
   * A raised cell stays only if a SLIVER × SLIVER block at its level or higher contains
   * it, so no narrow ridges or spikes stand out; likewise no narrow gaps between cliffs
   */
  removeSlivers() {
    const offsets = Array.from({ length: SLIVER }, (_, i) => -i)
    const block = Array.from({ length: SLIVER * SLIVER }, (_, i) => [i % SLIVER, Math.floor(i / SLIVER)] as const)
    for (let pass = 0, changed = true; changed && pass < 20; pass++) {
      changed = false
      for (let z = this.z0; z < this.z0 + this.depth; z++) {
        for (let x = this.x0; x < this.x0 + this.width; x++) {
          const l = this.get(x, z)
          const blockAtLeast = (level: number, higher: boolean) => offsets.some(ox => offsets.some(oz =>
            block.every(([bx, bz]) => {
              const other = this.get(x + ox + bx, z + oz + bz)
              return higher ? other >= level : other <= level
            })))
          if (l > 0 && !blockAtLeast(l, true)) {
            this.set(x, z, l - 1)
            changed = true
          }
          else if (!blockAtLeast(l, false)) {
            this.set(x, z, l + 1)
            changed = true
          }
        }
      }
    }
  }

  /** Plateaus and hollows of fewer than `min` cells take the level round them */
  removeSmallRegions(min: number) {
    const seen = new Uint8Array(this.width * this.depth)
    for (let z = this.z0; z < this.z0 + this.depth; z++) {
      for (let x = this.x0; x < this.x0 + this.width; x++) {
        if (seen[this.index(x, z)]) continue
        const level = this.get(x, z)
        const cells: [number, number][] = []
        const stack: [number, number][] = [[x, z]]
        seen[this.index(x, z)] = 1
        while (stack.length) {
          const [cx, cz] = stack.pop()!
          cells.push([cx, cz])
          for (const [dx, dz] of NEIGHBOURS_4) {
            const i = this.index(cx + dx, cz + dz)
            if (i < 0 || seen[i] || this.get(cx + dx, cz + dz) !== level) continue
            seen[i] = 1
            stack.push([cx + dx, cz + dz])
          }
        }
        if (cells.length >= min) continue
        const around = new Map<number, number>()
        for (const [cx, cz] of cells) {
          for (const [dx, dz] of NEIGHBOURS_4) {
            const l = this.get(cx + dx, cz + dz)
            if (l !== level) around.set(l, (around.get(l) ?? 0) + 1)
          }
        }
        const to = [...around].sort((a, b) => b[1] - a[1])[0]?.[0]
        if (to === undefined) continue
        for (const [cx, cz] of cells) this.set(cx, cz, to)
      }
    }
  }
}

/** How far round a point the ground is averaged, rounding off the folds of the slopes (cells) */
const SMOOTH_RADIUS = 0.35
/** How far the lines of rims and feet waver (cells) */
const WARP = 0.15
/** How high the bumps on a slope are (cells) */
const BUMP = 0.06

/** Size of the terraces in cells */
const TERRACE_SCALE = 20
/** The part of the noise's range at either end that stays on the lowest / highest terrace (below 0.5) */
const TERRACE_FROM = 0.15

/** How much the steps of a ramp level out where they meet (see step()) */
const RAMP_STEP_FLATNESS = 0.8

/** A plateau gets a ramp for every so many of its cells */
const RAMP_CELLS = 90
/** How far apart the extra ramps are at least (cells) */
const RAMP_SPACING = 10
/** The smallest block of cells a plateau or a gap between cliffs is made of */
const SLIVER = 3

const NEIGHBOURS_4: [number, number][] = [[1, 0], [-1, 0], [0, 1], [0, -1]]
const NEIGHBOURS_8: [number, number][] = [...NEIGHBOURS_4, [1, 1], [1, -1], [-1, 1], [-1, -1]]

/** A small seeded random number generator (0 … 1) */
function mulberry32(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6D2B79F5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * The rise across one step of a ramp (t 0 … 1): flat at both ends, steepest in the
 * middle (RAMP_STEP_FLATNESS: 0 a straight slope, 1 level at the ends)
 */
function step(t: number) {
  return t - RAMP_STEP_FLATNESS * Math.sin(2 * Math.PI * t) / (2 * Math.PI)
}

/** Smooth value noise (0 … 1) on a fixed lattice, the same on every map */
function smoothNoise(x: number, z: number) {
  const i = Math.floor(x)
  const j = Math.floor(z)
  const fx = x - i
  const fz = z - j
  const sx = fx * fx * (3 - 2 * fx)
  const sz = fz * fz * (3 - 2 * fz)
  const at = (a: number, b: number) => {
    const h = Math.sin(a * 127.1 + b * 311.7) * 43758.5453
    return h - Math.floor(h)
  }
  const top = at(i, j) * (1 - sx) + at(i + 1, j) * sx
  const bottom = at(i, j + 1) * (1 - sx) + at(i + 1, j + 1) * sx
  return top * (1 - sz) + bottom * sz
}

/** Smooth value noise (0 … 1) on a lattice of random values */
function valueNoise(random: () => number) {
  const size = 256
  const values = Float32Array.from({ length: size * size }, random)
  const at = (i: number, j: number) => values[(((j % size) + size) % size) * size + (((i % size) + size) % size)]!
  const smooth = (t: number) => t * t * (3 - 2 * t)
  return (x: number, z: number) => {
    const i = Math.floor(x)
    const j = Math.floor(z)
    const fx = smooth(x - i)
    const fz = smooth(z - j)
    const top = at(i, j) * (1 - fx) + at(i + 1, j) * fx
    const bottom = at(i, j + 1) * (1 - fx) + at(i + 1, j + 1) * fx
    return top * (1 - fz) + bottom * fz
  }
}
