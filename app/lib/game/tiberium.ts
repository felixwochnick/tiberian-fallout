/** Green Tiberium (Riparius) or the rarer, more valuable blue (Vinifera) */
export type TiberiumKind = 'green' | 'blue'

/** One cell of a Tiberium field and its growth stage (1 young … 3 ripe, see blender/TIB.py); green unless said */
export interface TiberiumCell { x: number, z: number, stage: number, kind?: TiberiumKind }

/** Highest growth stage of Tiberium */
export const TIBERIUM_RIPE = 3

/**
 * The cells of a roundish Tiberium field around the cell (cx, cz), `radius` cells
 * across from the middle with a ragged edge: ripe in the middle, younger outwards, with
 * a few gaps, so the crystals stand in loose clumps like in Tiberian Sun.
 */
export function tiberiumField(cx: number, cz: number, radius: number, kind: TiberiumKind = 'green', random = Math.random): TiberiumCell[] {
  const cells: TiberiumCell[] = []
  const reach = Math.ceil(radius * 1.2)
  for (let dx = -reach; dx <= reach; dx++) {
    for (let dz = -reach; dz <= reach; dz++) {
      const d = Math.hypot(dx, dz) / radius * (0.8 + 0.4 * random())
      if (d > 1 || random() < 0.15) continue
      cells.push({ x: cx + dx, z: cz + dz, stage: d < 0.45 ? 3 : d < 0.8 ? 2 : 1, kind })
    }
  }
  return cells
}

/** A field of Tiberium as a player sees it: its middle, how many cells and growth stages (bales) it has */
export interface TiberiumPatch { kind: TiberiumKind, x: number, z: number, cells: number, bales: number }

/** The cells grouped by kind into fields of neighbours (up to two cells apart), with their middle */
export function tiberiumPatches(cells: TiberiumCell[]): TiberiumPatch[] {
  const seen = new Set<string>()
  const byKey = new Map(cells.map(c => [`${c.x},${c.z}`, c]))
  const patches: TiberiumPatch[] = []
  for (const start of cells) {
    if (seen.has(`${start.x},${start.z}`)) continue
    const kind = start.kind ?? 'green'
    const blob = [start]
    seen.add(`${start.x},${start.z}`)
    for (let i = 0; i < blob.length; i++) {
      const c = blob[i]!
      for (let dx = -2; dx <= 2; dx++) {
        for (let dz = -2; dz <= 2; dz++) {
          const key = `${c.x + dx},${c.z + dz}`
          const n = byKey.get(key)
          if (n && !seen.has(key) && (n.kind ?? 'green') === kind) {
            seen.add(key)
            blob.push(n)
          }
        }
      }
    }
    patches.push({
      kind,
      x: blob.reduce((s, c) => s + c.x + 0.5, 0) / blob.length,
      z: blob.reduce((s, c) => s + c.z + 0.5, 0) / blob.length,
      cells: blob.length,
      bales: blob.reduce((s, c) => s + c.stage, 0),
    })
  }
  return patches
}

/** A harvester's load is shown as this many squares; it is full when they all are */
export const CARGO_SLOTS = 5
/** Growth stages that fill one square: a ripe cell fills one, a young (small) cell a third */
export const SLOT_STAGES = TIBERIUM_RIPE

/** One square of a harvester's load: one kind of Tiberium only, `stages` of SLOT_STAGES */
export interface CargoSlot { kind: TiberiumKind, stages: number }

/**
 * Whether one more stage of `kind` fits: into the last square if it holds the same kind
 * and is not full yet, otherwise into a new square. Green and blue are never mixed in
 * a square; a square begun with one kind and left for the other stays part-filled.
 */
export function cargoFits(cargo: CargoSlot[], kind: TiberiumKind) {
  const last = cargo.at(-1)
  return (last?.kind === kind && last.stages < SLOT_STAGES) || cargo.length < CARGO_SLOTS
}

/** Loads one stage of `kind` (if it fits, see cargoFits); returns whether it did. */
export function loadCargo(cargo: CargoSlot[], kind: TiberiumKind) {
  const last = cargo.at(-1)
  if (last?.kind === kind && last.stages < SLOT_STAGES) last.stages++
  else if (cargo.length < CARGO_SLOTS) cargo.push({ kind, stages: 1 })
  else return false
  return true
}

/** Nothing fits any more, of either kind */
export function cargoFull(cargo: CargoSlot[]) {
  return !cargoFits(cargo, 'green') && !cargoFits(cargo, 'blue')
}

/**
 * The only kind that still fits when there is no new square left: that of the last,
 * part-filled square (undefined: either kind fits, or none)
 */
export function cargoNeeds(cargo: CargoSlot[]): TiberiumKind | undefined {
  const last = cargo.at(-1)
  return cargo.length >= CARGO_SLOTS && last && last.stages < SLOT_STAGES ? last.kind : undefined
}

/**
 * The Tiberium a side keeps in its refineries and silos (Storage= bales each), like in
 * the original: what the harvesters bring in is stored there as far as there is room,
 * and money is spent from it first. It is part of the side's credits (what does not
 * fit stays plain money; the original loses it). By kind, for the green and blue pips.
 */
export class TiberiumStore {
  /** Bales stored, by kind */
  readonly bales: Record<TiberiumKind, number> = { green: 0, blue: 0 }
  /** The credits as last seen (see follow) */
  private seen?: number

  /** `value`: credits a bale of the kind is worth (Value=) */
  constructor(private readonly value: (kind: TiberiumKind) => number) {}

  get total() {
    return this.bales.green + this.bales.blue
  }

  /** Credits' worth of Tiberium a harvester brought in (and added to the credits): stored as far as `capacity` bales allow */
  bring(kind: TiberiumKind, credits: number, capacity: number) {
    const room = Math.max(0, capacity - this.total)
    this.bales[kind] += Math.min(credits / this.value(kind), room)
    if (this.seen !== undefined) this.seen += credits
  }

  /**
   * The side's credits, once a frame: what has been spent since (they went down) comes
   * out of the store first; with the refineries and silos now holding `capacity` bales,
   * what no longer fits is plain money
   */
  follow(credits: number, capacity: number) {
    if (this.seen !== undefined && credits < this.seen) this.take(this.worth(), this.seen - credits)
    this.seen = credits
    if (this.total > capacity) this.scale(capacity / this.total)
  }

  /** Share of `capacity` bales filled, by kind */
  fill(capacity: number): Record<TiberiumKind, number> {
    if (capacity <= 0) return { green: 0, blue: 0 }
    return { green: Math.min(1, this.bales.green / capacity), blue: Math.min(1, this.bales.blue / capacity) }
  }

  /** Credits the stored Tiberium is worth */
  worth() {
    return this.bales.green * this.value('green') + this.bales.blue * this.value('blue')
  }

  /** Credits spent out of the store: of both kinds alike */
  private take(worth: number, credits: number) {
    this.scale(worth > credits ? 1 - credits / worth : 0)
  }

  private scale(factor: number) {
    this.bales.green *= factor
    this.bales.blue *= factor
  }
}
