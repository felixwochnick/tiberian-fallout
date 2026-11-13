import { Cell, type FlatZone, mulberry32, type Terrain, valueNoise } from './terrain'

/**
 * The landscape on the terrain, after Tiberian Sun's two theaters (TEMPERAT.INI,
 * SNOW.INI): the temperate one is ochre earth ("Clear") with patches of sand, green
 * grass and rough, stony ground, blended into each other like the original's LAT
 * tiles, and its terrain objects are leafy trees, conifers, bare trees, bushes and
 * boulders; the snow one is snow with sheets of ice and rock showing through, snowy
 * conifers and rocks.
 *
 * Everything here is worked out from the map's seed: the same map gets the same
 * landscape. The ground shader draws the cover (groundCover); the battlefield puts
 * the terrain objects (scatterProps, PROPS.glb) on the map, the trees and big rocks
 * block their cell like the original's (Foundation=1x1), the rest is for the eye.
 */

export type Theater = 'temperate' | 'snow'

/** The theaters as the skirmish dialog offers them (German labels) */
export const THEATERS: [Theater, string][] = [['temperate', 'Gemäßigt'], ['snow', 'Schnee']]

/** A terrain object on a cell: a variant of PROPS.glb (node name), turned and scaled */
export interface Prop {
  kind: string
  x: number
  z: number
  /** Radians about the vertical */
  rotation: number
  scale: number
  /** Whether it blocks its cell (trees, big rocks) */
  blocks: boolean
}

/** Variants of PROPS.glb per theater with their weight, by what they are */
const KINDS: Record<Theater, Record<'tree' | 'forest' | 'bush' | 'rock', [string, number][]>> = {
  temperate: {
    tree: [['Oak1', 3], ['Oak2', 3], ['Oak3', 2], ['Pine1', 2], ['Pine2', 1], ['Dead1', 1], ['Dead2', 1]],
    forest: [['Oak1', 3], ['Oak2', 3], ['Oak3', 3], ['Pine1', 3], ['Pine2', 2]],
    bush: [['Bush1', 1], ['Bush2', 1], ['Bush3', 1]],
    rock: [['Rock1', 1], ['Rock2', 2], ['Rock3', 2]],
  },
  snow: {
    tree: [['SnowPine1', 3], ['SnowPine2', 3], ['SnowPine3', 2], ['SnowDead1', 1]],
    forest: [['SnowPine1', 3], ['SnowPine2', 3], ['SnowPine3', 2]],
    bush: [['SnowBush1', 1]],
    rock: [['SnowRock1', 1], ['SnowRock2', 2]],
  },
}

/** Variants that do not block their cell: low bushes and the small stones */
const LOW = new Set(['Bush1', 'Bush2', 'Bush3', 'SnowBush1', 'Rock3', 'SnowRock2'])

/** Size of the cover's patches in cells (noise scale) */
const PATCH = { sand: 15, grass: 11, rough: 7, ice: 13 }

/**
 * The ground's cover of every cell of the terrain as RGBA texels (one per cell, rows
 * along x, like the battlefield's Tiberium texture): temperate R sand, G grass,
 * B rough ground; snow R ice, B rock showing through (G unused). 255 is all of it; the
 * ground shader frays the edges between them with noise. Rough ground gathers round
 * the cliffs and on the terraces' slopes, sand and ice in the low land.
 */
export function groundCover(terrain: Terrain, theater: Theater, seed: number) {
  const random = mulberry32(seed ^ 0x5eed)
  const noise = valueNoise(random)
  const { x0, z0, width, depth } = terrain
  const data = new Uint8Array(width * depth * 4)
  const field = (x: number, z: number, scale: number, offset: number) =>
    noise(x / scale + offset, z / scale + offset * 1.7) * 0.7 + noise(x / scale * 2.7 + offset, z / scale * 2.7) * 0.3
  /** 0 … 1 above a threshold of a noise field, soft over `soft` */
  const patch = (value: number, threshold: number, soft = 0.08) => Math.min(1, Math.max(0, (value - threshold) / soft))
  for (let z = z0; z < z0 + depth; z++) {
    for (let x = x0; x < x0 + width; x++) {
      const i = ((z - z0) * width + (x - x0)) * 4
      const cell = terrain.cell(x, z)
      // rough near rock: the cells round a cliff and the slopes
      let nearRock = 0
      for (let dz = -2; dz <= 2; dz++) {
        for (let dx = -2; dx <= 2; dx++) {
          if (terrain.cell(x + dx, z + dz) === Cell.Rock) nearRock = Math.max(nearRock, 1 - Math.hypot(dx, dz) / 3)
        }
      }
      const slope = cell === Cell.Slope ? 0.6 : 0
      const rough = Math.max(patch(field(x, z, PATCH.rough, 3.1), 0.68), nearRock * 0.8, slope)
      const low = terrain.level(x, z) === 0 ? 1 : 0.4
      if (theater === 'snow') {
        const ice = patch(field(x, z, PATCH.ice, 7.3), 0.66) * low * (cell === Cell.Flat ? 1 : 0)
        data[i] = Math.round(ice * 255)
        data[i + 2] = Math.round(Math.max(rough * 0.9, 0) * 255)
      }
      else {
        const sand = patch(field(x, z, PATCH.sand, 11.7), 0.6) * low
        const grass = patch(field(x, z, PATCH.grass, 23.9), 0.62) * (1 - sand)
        data[i] = Math.round(sand * 255)
        data[i + 1] = Math.round(grass * 255)
        data[i + 2] = Math.round(rough * (1 - grass * 0.6) * 255)
      }
      data[i + 3] = 255
    }
  }
  return data
}

/** Share of the cells in a clump of trees that get one */
const CLUMP_DENSITY = 0.6
/** Share of the cells at the foot of a cliff with a tree: the original's rows of trees there */
const CLIFF_FOOT_TREES = 0.3
/** Share of the open cells elsewhere with a lone tree, a bush or a rock */
const LONE = { tree: 0.025, bush: 0.03, rock: 0.015 }

/**
 * Terrain objects for the map, like the original's: small clumps of trees (a handful
 * each) where a noise field is high, rows of trees along the foot of the cliffs, lone
 * trees, bushes and rocks elsewhere (rocks more on rough ground, trees more on grass).
 * Only on flat cells on the map (`onMap`) outside the flat zones (bases, Tiberium
 * fields) with a margin, away from the ramps, whose neighbours are flat on the same
 * level or rock (a cliff). A blocking object never cuts a way: it only goes where the
 * open cells round it stay joined to each other (so every place stays reachable).
 */
export function scatterProps(terrain: Terrain, theater: Theater, seed: number, cover: Uint8Array,
  { onMap, keep = [], margin = 2 }: { onMap: (x: number, z: number) => boolean, keep?: FlatZone[], margin?: number }) {
  const random = mulberry32(seed ^ 0x7ee5)
  const noise = valueNoise(random)
  const { x0, z0, width, depth } = terrain
  const kinds = KINDS[theater]
  const pick = (list: [string, number][]) => {
    let r = random() * list.reduce((sum, [, w]) => sum + w, 0)
    for (const [kind, w] of list) {
      r -= w
      if (r < 0) return kind
    }
    return list[0]![0]
  }
  const kept = (x: number, z: number) => keep.some(f =>
    x >= f.x - margin && x < f.x + f.w + margin && z >= f.z - margin && z < f.z + f.h + margin)
  const blocked = new Set<string>()
  const key = (x: number, z: number) => `${x},${z}`
  /** A neighbour one can step onto from a cell on `level`: flat on that level, on the map, nothing on it */
  const open = (x: number, z: number, level: number) =>
    onMap(x, z) && terrain.cell(x, z) === Cell.Flat && terrain.corner(x, z) === level && !blocked.has(key(x, z))
  /**
   * A flat cell on the map whose eight neighbours are flat on its level or rock (they
   * cannot be reached from it then; slopes and ramps could, they rule it out), no ramp
   * within two cells; with how many of the neighbours are rock (the foot or the top of a cliff)
   */
  const plain = (x: number, z: number) => {
    if (!onMap(x, z) || kept(x, z) || terrain.cell(x, z) !== Cell.Flat) return undefined
    const level = terrain.corner(x, z)
    let rock = 0
    for (let dz = -1; dz <= 1; dz++) {
      for (let dx = -1; dx <= 1; dx++) {
        const cell = terrain.cell(x + dx, z + dz)
        if (cell === Cell.Rock) rock++
        else if (!onMap(x + dx, z + dz) || cell !== Cell.Flat || terrain.corner(x + dx, z + dz) !== level) return undefined
      }
    }
    for (let dz = -2; dz <= 2; dz++) {
      for (let dx = -2; dx <= 2; dx++) {
        if (terrain.cell(x + dx, z + dz) === Cell.Ramp) return undefined
      }
    }
    return { level, rock }
  }
  // the ring of eight round a cell, in order round it
  const RING: [number, number][] = [[-1, -1], [0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0]]
  /**
   * Whether blocking (x, z) keeps its open neighbours joined: going round the ring, the
   * open cells form one run (corner cells count only with an open edge cell beside them,
   * as nobody cuts a blocked corner)
   */
  const keepsWays = (x: number, z: number, level: number) => {
    const ring = RING.map(([dx, dz]) => open(x + dx, z + dz, level))
    // a corner cell is only joined to the ring through its edge neighbours
    const joined = ring.map((o, k) => o && (k % 2 === 1 || ring[(k + 1) % 8] || ring[(k + 7) % 8]))
    let runs = 0
    for (let k = 0; k < 8; k++) {
      if (joined[k] && !joined[(k + 7) % 8]) runs++
    }
    const count = joined.filter(Boolean).length
    return count === 8 || (runs === 1 && count >= 3)
  }
  const props: Prop[] = []
  const put = (x: number, z: number, level: number, kind: string) => {
    const blocks = !LOW.has(kind)
    if (blocks) {
      if (!keepsWays(x, z, level)) return
      blocked.add(key(x, z))
    }
    props.push({ kind, x, z, rotation: random() * Math.PI * 2, scale: 0.85 + random() * 0.3, blocks })
  }
  const cells: [number, number][] = []
  for (let z = z0; z < z0 + depth; z++) {
    for (let x = x0; x < x0 + width; x++) cells.push([x, z])
  }
  // in random order, so no direction is preferred where ways would be cut
  for (let i = cells.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1))
    ;[cells[i], cells[j]] = [cells[j]!, cells[i]!]
  }
  for (const [x, z] of cells) {
    const here = plain(x, z)
    if (!here) continue
    const { level, rock } = here
    const i = ((z - z0) * width + (x - x0)) * 4
    const grass = cover[i + 1]! / 255
    const rough = cover[i + 2]! / 255
    const sand = theater === 'temperate' ? cover[i]! / 255 : 0
    const ice = theater === 'snow' ? cover[i]! / 255 : 0
    if (ice > 0.3) continue
    // below a cliff (its rock higher than the cell) rather than on its rim
    const foot = rock > 0 && terrain.level(x, z) === level && [[1, 0], [-1, 0], [0, 1], [0, -1]]
      .some(([dx, dz]) => terrain.cell(x + dx!, z + dz!) === Cell.Rock && Math.max(...terrain.corners(x + dx!, z + dz!)) > level)
    const clump = noise(x / 5, z / 5) * 0.7 + noise(x / 2, z / 2 + 40) * 0.3
    const r = random()
    if (foot && sand < 0.5) {
      if (r < CLIFF_FOOT_TREES) put(x, z, level, pick(kinds.forest))
      else if (r < CLIFF_FOOT_TREES + 0.1) put(x, z, level, pick(r < CLIFF_FOOT_TREES + 0.05 ? kinds.rock : kinds.bush))
    }
    else if (clump > 0.7 - grass * 0.05 && sand < 0.5) {
      if (r < CLUMP_DENSITY) put(x, z, level, pick(kinds.forest))
      else if (r < CLUMP_DENSITY + 0.15) put(x, z, level, pick(kinds.bush))
    }
    else if (r < LONE.tree * (1 + grass * 2) * (1 - sand * 0.8)) put(x, z, level, pick(kinds.tree))
    else if (r < 0.1 && r > 0.1 - LONE.bush * (1 + grass)) put(x, z, level, pick(kinds.bush))
    else if (r > 1 - LONE.rock * (1 + rough * 4)) put(x, z, level, pick(kinds.rock))
  }
  return props
}
