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
