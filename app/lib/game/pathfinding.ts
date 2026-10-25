import * as THREE from 'three'

/**
 * Pathfinding on the map's cells (one cell is one world unit; cell (x, z) covers
 * x … x+1, z … z+1). Buildings block their foundation's cells. A* with 8 directions
 * finds the shortest way (diagonals cost √2 and may not cut a blocked corner); the
 * path is then pulled straight wherever the line between two points stays on free
 * cells, so units walk direct lines instead of zig-zagging from cell to cell.
 */

export interface NavMap {
  /** Whether a cell can be walked on (on the map and not under a building) */
  free: (x: number, z: number) => boolean
}

/** Search budget, so an unreachable target cannot freeze the game */
const MAX_NODES = 40000
/** How far around a blocked target cell to look for the nearest free one */
const SNAP_RADIUS = 12

const cell = (p: THREE.Vector3) => [Math.floor(p.x), Math.floor(p.z)] as const
const key = (x: number, z: number) => `${x},${z}`

/** Small binary heap of nodes ordered by f = g + h */
class Heap {
  private items: { x: number, z: number, f: number }[] = []
  get size() {
    return this.items.length
  }

  push(item: { x: number, z: number, f: number }) {
    const items = this.items
    items.push(item)
    let i = items.length - 1
    while (i > 0) {
      const parent = (i - 1) >> 1
      if (items[parent]!.f <= items[i]!.f) break
      ;[items[parent], items[i]] = [items[i]!, items[parent]!]
      i = parent
    }
  }

  pop() {
    const items = this.items
    const top = items[0]!
    const last = items.pop()!
    if (items.length) {
      items[0] = last
      let i = 0
      for (;;) {
        const l = 2 * i + 1
        const r = l + 1
        let smallest = i
        if (l < items.length && items[l]!.f < items[smallest]!.f) smallest = l
        if (r < items.length && items[r]!.f < items[smallest]!.f) smallest = r
        if (smallest === i) break
        ;[items[smallest], items[i]] = [items[i]!, items[smallest]!]
        i = smallest
      }
    }
    return top
  }
}

/** The nearest free cell to (x, z), searching outwards in rings */
function nearestFree(map: NavMap, x: number, z: number) {
  if (map.free(x, z)) return [x, z] as const
  for (let r = 1; r <= SNAP_RADIUS; r++) {
    let best: [number, number] | undefined
    let bestD = Infinity
    for (let dx = -r; dx <= r; dx++) {
      for (let dz = -r; dz <= r; dz++) {
        if (Math.max(Math.abs(dx), Math.abs(dz)) !== r || !map.free(x + dx, z + dz)) continue
        const d = dx * dx + dz * dz
        if (d < bestD) {
          bestD = d
          best = [x + dx, z + dz]
        }
      }
    }
    if (best) return best
  }
  return undefined
}

/** Whether the straight line from a to b only crosses free cells (sampled finely) */
export function lineFree(map: NavMap, a: THREE.Vector3, b: THREE.Vector3) {
  const distance = Math.hypot(b.x - a.x, b.z - a.z)
  const steps = Math.max(1, Math.ceil(distance / 0.2))
  for (let i = 1; i < steps; i++) {
    const t = i / steps
    const x = a.x + (b.x - a.x) * t
    const z = a.z + (b.z - a.z) * t
    if (!map.free(Math.floor(x), Math.floor(z))) return false
    // keep a little distance to walls: the unit's body must not graze a corner
    for (const [ox, oz] of [[0.18, 0], [-0.18, 0], [0, 0.18], [0, -0.18]]) {
      if (!map.free(Math.floor(x + ox!), Math.floor(z + oz!))) return false
    }
  }
  return true
}

/**
 * The shortest way from `from` to `to` (world, on the ground) as waypoints, ending at
 * `to` or, if that lies under a building, at the nearest free spot. Empty if there is
 * no way.
 */
export function findPath(map: NavMap, from: THREE.Vector3, to: THREE.Vector3): THREE.Vector3[] {
  const [sx, sz] = cell(from)
  const goalCell = nearestFree(map, ...cell(to))
  if (!goalCell) return []
  const [gx, gz] = goalCell
  const goal = map.free(...cell(to)) ? to.clone().setY(0) : new THREE.Vector3(gx + 0.5, 0, gz + 0.5)
  if (lineFree(map, from, goal)) return [goal]

  const h = (x: number, z: number) => {
    const dx = Math.abs(x - gx)
    const dz = Math.abs(z - gz)
    return Math.max(dx, dz) + (Math.SQRT2 - 1) * Math.min(dx, dz) // octile distance
  }
  const open = new Heap()
  const g = new Map<string, number>([[key(sx, sz), 0]])
  const came = new Map<string, string>()
  open.push({ x: sx, z: sz, f: h(sx, sz) })
  let found = false
  let expanded = 0
  while (open.size && expanded++ < MAX_NODES) {
    const { x, z } = open.pop()
    if (x === gx && z === gz) {
      found = true
      break
    }
    const here = g.get(key(x, z))!
    for (let dx = -1; dx <= 1; dx++) {
      for (let dz = -1; dz <= 1; dz++) {
        if (!dx && !dz) continue
        const nx = x + dx
        const nz = z + dz
        if (!map.free(nx, nz)) continue
        // diagonal steps may not squeeze past a blocked corner
        if (dx && dz && (!map.free(x + dx, z) || !map.free(x, z + dz))) continue
        const cost = here + (dx && dz ? Math.SQRT2 : 1)
        const k = key(nx, nz)
        if (cost >= (g.get(k) ?? Infinity)) continue
        g.set(k, cost)
        came.set(k, key(x, z))
        open.push({ x: nx, z: nz, f: cost + h(nx, nz) })
      }
    }
  }
  if (!found) return []

  // cells from the goal back to the start, as cell centres
  const cells: THREE.Vector3[] = []
  for (let k: string | undefined = key(gx, gz); k && k !== key(sx, sz); k = came.get(k)) {
    const [x, z] = k.split(',').map(Number)
    cells.unshift(new THREE.Vector3(x! + 0.5, 0, z! + 0.5))
  }
  cells[cells.length - 1] = goal

  // string pulling: from each point go straight to the farthest point still in sight
  const path: THREE.Vector3[] = []
  let anchor = from.clone().setY(0)
  let i = 0
  while (i < cells.length) {
    let far = i
    for (let j = cells.length - 1; j > i; j--) {
      if (lineFree(map, anchor, cells[j]!)) {
        far = j
        break
      }
    }
    path.push(cells[far]!)
    anchor = cells[far]!
    i = far + 1
  }
  return path
}
