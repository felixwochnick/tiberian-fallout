import type { Terrain } from './terrain'
import type { TiberiumKind } from './tiberium'

/**
 * A skirmish map that is fair to every start: the players start on a circle round the
 * middle of the map, at equal angles (two in opposite corners, four in all corners …),
 * and each start gets the same: the same Tiberium fields at the same place seen from
 * it, the same flat ground round it and a flat way to the middle. The fields fought
 * over lie between two neighbouring starts and in the middle, equally far from each.
 * The ground's hills are alike round the middle (Terrain's symmetry, its mirror lines
 * through the starts); what still comes by chance (the ramps) is checked with
 * `unfairness`, and the map shaped anew while one start is far worse off.
 */

/** A point of the map along the screen axes (u across, v down), in cells from the top left corner */
export interface MapSpot { u: number, v: number }

/** Where a Tiberium field lies, how big it is (cells from the middle), and whether a Tiberium tree stands in it */
export interface FieldSpot extends MapSpot {
  radius: number
  kind: TiberiumKind
  /** Small young crystals that grow round their tree, rather than a ripe field */
  young: boolean
  tree: boolean
  /** The start it belongs to (undefined: fought over) */
  start?: number
}

export interface SkirmishLayout {
  starts: MapSpot[]
  fields: FieldSpot[]
  /** Points on the straight ways from each start to the middle, to be kept flat */
  ways: MapSpot[]
}

/** Distance of the starts from the middle, as a share of half the map's smaller side */
export const START_RADIUS = 0.72
/** The first start lies towards the top left corner (screen axes, radians from u towards v) */
const FIRST_START = -0.75 * Math.PI
/**
 * Each start's own fields: angle from the way to the middle (radians), distance (cells),
 * size, kind – enough for a base with a few refineries for a good while (about 15 000
 * credits), with room for the base between them
 */
const OWN_FIELDS: { angle: number, distance: number, radius: number, kind: TiberiumKind, tree: boolean }[] = [
  { angle: 0.95, distance: 11, radius: 5, kind: 'green', tree: true },
  { angle: -1.4, distance: 10, radius: 3, kind: 'blue', tree: false },
  { angle: 2.4, distance: 13, radius: 3, kind: 'green', tree: true },
]
/** The fields between two neighbouring starts: their distance from the middle (share of the starts'), size */
const BETWEEN = { share: 0.6, radius: 2.5 }
/** The rich field in the middle */
const MIDDLE = { radius: 3.5, kind: 'blue' as TiberiumKind }
/** The flat way to the middle: a point every this many cells, from this far out from the start */
const WAY_STEP = 3
const WAY_FROM = 7

/** The starts and fields for `players` players on a map of `size` cells (screen axes) */
export function skirmishLayout(players: number, [width, height]: readonly [number, number]): SkirmishLayout {
  const middle = { u: width / 2, v: height / 2 }
  const at = (angle: number, distance: number, from: MapSpot = middle): MapSpot =>
    ({ u: from.u + Math.cos(angle) * distance, v: from.v + Math.sin(angle) * distance })
  const own = (start: MapSpot, inwards: number, i: number) => OWN_FIELDS.map((f): FieldSpot =>
    ({ ...at(inwards + f.angle, f.distance, start), radius: f.radius, kind: f.kind, young: false, tree: f.tree, start: i }))
  // alone on the map: in the middle
  if (players < 2) return { starts: [middle], fields: own(middle, FIRST_START, 0), ways: [] }
  const radius = START_RADIUS * Math.min(width, height) / 2
  const sector = (2 * Math.PI) / players
  const angles = Array.from({ length: players }, (_, i) => FIRST_START + i * sector)
  const starts = angles.map(angle => at(angle, radius))
  const fields: FieldSpot[] = []
  const ways: MapSpot[] = []
  angles.forEach((angle, i) => {
    const start = starts[i]!
    // seen from the start, the middle lies the other way
    const inwards = angle + Math.PI
    fields.push(...own(start, inwards, i))
    fields.push({ ...at(angle + sector / 2, radius * BETWEEN.share), radius: BETWEEN.radius, kind: 'green', young: true, tree: true })
    for (let d = WAY_FROM; d < radius; d += WAY_STEP) ways.push(at(inwards, d, start))
  })
  fields.push({ ...middle, radius: MIDDLE.radius, kind: MIDDLE.kind, young: false, tree: false })
  return { starts, fields, ways }
}

/** A cell (world x, z) */
type CellAt = readonly [number, number]

const STEPS: [number, number, number][] = [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1],
  [1, 1, Math.SQRT2], [1, -1, Math.SQRT2], [-1, 1, Math.SQRT2], [-1, -1, Math.SQRT2]]

/**
 * The length of the shortest ways from a cell to every cell of the terrain it can reach
 * on the map, in 8 directions like the units walk (diagonals √2, not round a blocked
 * corner); Infinity where it cannot get. Indexed like the terrain's cells.
 */
export function wayLengths(terrain: Terrain, [fx, fz]: CellAt, inside: (x: number, z: number) => boolean) {
  const { x0, z0, width, depth } = terrain
  const lengths = new Float64Array(width * depth).fill(Infinity)
  const index = (x: number, z: number) => (z - z0) * width + (x - x0)
  // a binary heap of cell indices by their length so far
  const heap: number[] = []
  const push = (i: number) => {
    heap.push(i)
    for (let c = heap.length - 1; c > 0;) {
      const p = (c - 1) >> 1
      if (lengths[heap[p]!]! <= lengths[i]!) break
      heap[c] = heap[p]!
      heap[p] = i
      c = p
    }
  }
  const pop = () => {
    const top = heap[0]!
    const last = heap.pop()!
    if (heap.length) {
      heap[0] = last
      for (let p = 0; ;) {
        const l = 2 * p + 1
        const r = l + 1
        let m = p
        if (l < heap.length && lengths[heap[l]!]! < lengths[heap[m]!]!) m = l
        if (r < heap.length && lengths[heap[r]!]! < lengths[heap[m]!]!) m = r
        if (m === p) break
        ;[heap[p], heap[m]] = [heap[m]!, heap[p]!]
        p = m
      }
    }
    return top
  }
  if (fx < x0 || fz < z0 || fx >= x0 + width || fz >= z0 + depth) return { at: () => Infinity }
  lengths[index(fx, fz)] = 0
  push(index(fx, fz))
  const done = new Uint8Array(width * depth)
  while (heap.length) {
    const i = pop()
    if (done[i]) continue
    done[i] = 1
    const x = x0 + (i % width)
    const z = z0 + Math.floor(i / width)
    for (const [dx, dz, cost] of STEPS) {
      const nx = x + dx
      const nz = z + dz
      if (nx < x0 || nz < z0 || nx >= x0 + width || nz >= z0 + depth || !inside(nx, nz) || !terrain.passable(x, z, dx, dz)) continue
      const j = index(nx, nz)
      if (lengths[i]! + cost >= lengths[j]!) continue
      lengths[j] = lengths[i]! + cost
      push(j)
    }
  }
  return { at: (x: number, z: number) => x < x0 || z < z0 || x >= x0 + width || z >= z0 + depth ? Infinity : lengths[index(x, z)]! }
}

/** The length of the way between two cells over open ground, in 8 directions */
const openWay = (a: CellAt, b: CellAt) => {
  const dx = Math.abs(a[0] - b[0])
  const dz = Math.abs(a[1] - b[1])
  return Math.max(dx, dz) + (Math.SQRT2 - 1) * Math.min(dx, dz)
}

/**
 * How unfair the ground is to the starts: for each kind of goal – the middle, the
 * start's own fields, the next start – how much longer than over open ground each
 * start's way is (the detour), and by what share the biggest detour is bigger than the
 * smallest (0: all alike; Infinity: one cannot get there at all). `goals[i]` are start
 * i's goals, in the same order for every start.
 */
export function unfairness(terrain: Terrain, starts: CellAt[], goals: CellAt[][], inside: (x: number, z: number) => boolean) {
  const detours = starts.map((start, i) => {
    const ways = wayLengths(terrain, start, inside)
    return goals[i]!.map(goal => ways.at(goal[0], goal[1]) / Math.max(1, openWay(start, goal)))
  })
  let worst = 0
  for (let g = 0; g < (goals[0]?.length ?? 0); g++) {
    const kind = detours.map(d => d[g]!)
    const biggest = Math.max(...kind)
    if (!Number.isFinite(biggest)) return Infinity
    worst = Math.max(worst, (biggest - Math.min(...kind)) / biggest)
  }
  return worst
}
