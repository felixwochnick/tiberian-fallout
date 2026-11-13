/** A kind of wall that links up (RULES.INI id) and how far it reaches (see BuildInfo.linkRange) */
export interface WallLink {
  id: string
  range: number
}

/** What the wall links look at round a new piece */
export interface WallMap {
  /** Whether a piece of the same kind (and owner) stands on a cell */
  piece: (x: number, z: number) => boolean
  /** Whether a cell can be built on */
  free: (x: number, z: number) => boolean
}

/** The four directions along the cell grid: walls do not link up diagonally */
const DIRECTIONS = [[1, 0], [-1, 0], [0, 1], [0, -1]] as const

/**
 * The cells a wall piece put down on (x, z) walls up for free, like in the original: in
 * each direction along the grid, the next piece of its kind at most `range` cells away
 * (GuardRange=, 5 for the walls: up to 4 cells between) – if every cell between can be
 * built on. A unit, a building or rough ground in between, and that side stays open.
 */
export function wallLinks(x: number, z: number, range: number, map: WallMap) {
  const cells: [number, number][] = []
  for (const [dx, dz] of DIRECTIONS) {
    const between: [number, number][] = []
    for (let step = 1; step <= range; step++) {
      const [cx, cz] = [x + dx * step, z + dz * step]
      if (map.piece(cx, cz)) {
        cells.push(...between)
        break
      }
      if (!map.free(cx, cz)) break
      between.push([cx, cz])
    }
  }
  return cells
}
