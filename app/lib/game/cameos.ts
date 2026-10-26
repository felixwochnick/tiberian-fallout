import { parseIni } from '../formats/ini'
import { MixArchive } from '../formats/mix'
import { decodePalette, decodeShp, frameToRgba } from '../formats/shp'
import type { AssetStore } from '../storage/asset-store'

/**
 * Build options of the sidebar and their cameos (the 64 × 48 build pictures).
 * Which picture belongs to an object comes from the game's own RULES.INI
 * (Image=) and ART.INI (Cameo=); the pictures are in CONQUER.MIX and, for the
 * side-specific infantry, in the sidebar archive (SIDEC01.MIX for GDI).
 */

export interface BuildOption {
  /** Object id in RULES.INI */
  id: string
  /** German name as shown on the cameo */
  name: string
}

/** GDI: structures in the left column, units in the right one (as in the original). */
export const GDI_BUILD_OPTIONS: { structures: BuildOption[], units: BuildOption[] } = {
  structures: [
    { id: 'GAPOWR', name: 'GDI-Kraftwerk' },
    { id: 'PROC', name: 'Tiberium-Raffinerie' },
    { id: 'GAPILE', name: 'GDI-Kaserne' },
    { id: 'GASILO', name: 'Tiberium-Silo' },
    { id: 'GACTWR', name: 'Basisturm' },
    { id: 'GAWEAP', name: 'GDI-Waffenfabrik' },
    { id: 'GAVULC', name: 'Vulcankanone' },
    { id: 'GARADR', name: 'Radar' },
  ],
  units: [
    { id: 'E1', name: 'Leichte Infanterie' },
    { id: 'E2', name: 'Grenadier' },
    { id: 'E3', name: 'Raketensoldat' },
    { id: 'ENGINEER', name: 'Ingenieur' },
  ],
}

/**
 * What may be built, after the game's RULES.INI: each object's Prerequisite= lists
 * buildings that must all be owned; generic names (POWER, BARRACKS, FACTORY, RADAR,
 * TECH, PROC) stand for any building of that kind ([General] Prerequisite*=).
 * Structures also need a construction yard.
 */
export interface BuildRules {
  prerequisites: Map<string, string[]>
  generic: Map<string, string[]>
  /** Cost, build time and more of every build option */
  info: Map<string, BuildInfo>
  /** Credits one bale of Tiberium is worth (Value= of [Riparius], the green Tiberium) */
  tiberiumValue: number
  /** The same for the blue Tiberium (Value= of [Vinifera]) */
  blueTiberiumValue: number
  /** Selling and repairing buildings ([General]) */
  upkeep: Upkeep
}

export interface Upkeep {
  /** Share of the cost paid back for a building sold at full strength (RefundPercent=) */
  refund: number
  /** Share of the cost a repair from nothing to full strength costs (RepairPercent=) */
  repairCost: number
  /** Game seconds between two repair steps (RepairRate=, in minutes) */
  repairSeconds: number
  /** Hit points a repair step gives back (RepairStep=) */
  repairStep: number
}

/** Tiberian Sun's values, until the rules are loaded */
export const DEFAULT_UPKEEP: Upkeep = { refund: 0.5, repairCost: 0.2, repairSeconds: 0.96, repairStep: 8 }

export interface BuildInfo {
  id: string
  name: string
  structure: boolean
  cost: number
  /** Regular build time in seconds (at normal game speed and full power) */
  seconds: number
  /** Power produced (+) or used (−) */
  power: number
  /** Foundation in cells (structures) */
  foundation: [number, number]
  /** How many cells away from the base it may be placed (structures) */
  adjacent: number
  /** What a unit says (sound file names in SOUNDS.MIX, without .AUD), from RULES.INI */
  voices: Record<UnitVoice, string[]>
  /** TechLevel= (−1: never buildable) */
  techLevel: number
  /** How far it sees in cells (Sight=): idle units attack enemies within it */
  sight: number
  /** Hit points (Strength=) */
  strength: number
  /** Can be repaired (Repairable=, default yes) */
  repairable: boolean
  /** Can be sold (not Unsellable=) */
  sellable: boolean
  /** Bales of Tiberium it carries (Storage=: the harvester) */
  storage: number
  /** Armor= as index into a warhead's Verses= (none, wood, light, heavy, concrete) */
  armor: number
  /** It rolls over enemy infantry and sandbags in its way (Crusher=) */
  crusher: boolean
  /** A crusher rolls it over (Crushable=: infantry, sandbags) */
  crushable: boolean
  /** Primary= weapon, if it has one */
  weapon?: Weapon
  /**
   * Sounds of its explosion when destroyed: the Report= of its Explosion= animations;
   * buildings without their own sound those of the vehicles' (or the warheads') explosions
   */
  explosionReports: string[]
}

export interface Weapon {
  name: string
  damage: number
  /** Frames between shots (the game runs 15 frames a second at normal speed) */
  rof: number
  /** Range in cells */
  range: number
  /** Damage factor per armor type, from the warhead's Verses= */
  verses: number[]
  /** Firing sounds (SOUNDS.MIX, one picked at random) */
  reports: string[]
  /** Sounds of the explosion where it lands: the Report= of the warhead's AnimList= animations */
  impactReports: string[]
  /** It can damage walls and sandbags (the warhead's Wall=: grenades, rockets, shells – not rifles) */
  wall: boolean
  /** What flies (the weapon's Projectile=); undefined: invisible, the hit is at once */
  projectile?: Projectile
  /** Cells per second the projectile flies (from Speed=, leptons per frame) */
  speed: number
  /** Radius of the explosion in cells (the warhead's CellSpread=), 0: only the target */
  spread: number
  /** Share of the damage at the edge of the explosion (PercentAtMax=) */
  percentAtMax: number
}

export interface Projectile {
  /** Thrown in a high arc to a point on the ground (grenades: Arcing=) */
  arcing: boolean
  /** Steers after its target (missiles: ROT= > 0) */
  homing: boolean
}

const ARMOR_TYPES = ['none', 'wood', 'light', 'heavy', 'concrete']
/** Speed= is in leptons (1/256 cell) per frame; from this speed on a shot hits at once */
const LEPTONS_PER_CELL = 256
const INSTANT_SPEED = 100
/** Projectiles fly at the game's "fast" setting: at 15 frames a second rockets would crawl */
const PROJECTILE_FRAMES_PER_SECOND = 30
const MIN_PROJECTILE_SPEED = 2

export type UnitVoice = 'select' | 'move' | 'attack' | 'die'

const CONSTRUCTION_YARDS = ['GACNST', 'NACNST']
/** These crush whatever RULES.INI says: the Titan and the heavy vehicles */
const CRUSHERS = new Set(['MMCH', 'HARV', 'MCV'])
/** Walls are crushable unless RULES.INI says otherwise */
const CRUSHABLE_WALLS = new Set(['GASAND'])

const yes = (value?: string) => /^(yes|true|1)$/i.test(value ?? '')

export async function loadBuildRules(store: AssetStore): Promise<BuildRules | undefined> {
  const tibsun = await store.get('TIBSUN.MIX')
  if (!tibsun) return undefined
  const local = await (await MixArchive.open(tibsun, 'TIBSUN.MIX')).openNested('LOCAL.MIX')
  const bytes = await local?.read('RULES.INI')
  if (!bytes) return undefined
  const rules = parseIni(new TextDecoder('latin1').decode(bytes))
  const list = (value?: string) => (value ?? '').split(',').map(s => s.trim().toUpperCase()).filter(Boolean)
  const general = rules.get('GENERAL')
  const generic = new Map<string, string[]>([
    ['POWER', list(general?.get('PREREQUISITEPOWER'))],
    ['FACTORY', list(general?.get('PREREQUISITEFACTORY'))],
    ['BARRACKS', list(general?.get('PREREQUISITEBARRACKS'))],
    ['RADAR', list(general?.get('PREREQUISITERADAR'))],
    ['TECH', list(general?.get('PREREQUISITETECH'))],
    ['PROC', list(general?.get('PREREQUISITEPROC') ?? 'PROC')],
  ])
  // minutes to produce an item of 1000 credits
  const buildSpeed = Number(general?.get('BUILDSPEED') ?? 0.8)
  const artBytes = await local?.read('ART.INI')
  const art = artBytes ? parseIni(new TextDecoder('latin1').decode(artBytes)) : new Map()
  /** The sounds of animations (explosions): their Report=, from RULES.INI or ART.INI */
  const reportsOf = (anims?: string) => list(anims).flatMap(anim => list(rules.get(anim)?.get('REPORT') ?? art.get(anim)?.get('REPORT')))
  const prerequisites = new Map<string, string[]>()
  const info = new Map<string, BuildInfo>()
  // infantry can be crushed unless its section says Crushable=no (cyborgs …)
  const infantry = new Set([...(rules.get('INFANTRYTYPES')?.values() ?? [])].map(id => id.trim().toUpperCase()))
  /** Hit points, armor and weapon of an object (with its weapon's warhead) */
  const combat = (section?: Map<string, string>) => {
    const weaponName = section?.get('PRIMARY')
    const weapon = weaponName && weaponName.toLowerCase() !== 'none' ? rules.get(weaponName.toUpperCase()) : undefined
    const warhead = weapon && rules.get((weapon.get('WARHEAD') ?? '').toUpperCase())
    const projectile = weapon && rules.get((weapon.get('PROJECTILE') ?? '').toUpperCase())
    // invisible projectiles (bullets, lasers) hit at once; so do very fast ones
    const speed = Number(weapon?.get('SPEED') ?? 100)
    const visible = !!projectile && !yes(projectile.get('INVISO')) && (projectile.get('IMAGE') ?? 'none').toLowerCase() !== 'none'
      && speed < INSTANT_SPEED
    return {
      strength: Number(section?.get('STRENGTH') ?? 100),
      repairable: !/^(no|false|0)$/i.test(section?.get('REPAIRABLE') ?? ''),
      sellable: !yes(section?.get('UNSELLABLE')),
      storage: Number(section?.get('STORAGE') ?? 0),
      sight: Number(section?.get('SIGHT') ?? 5),
      armor: Math.max(0, ARMOR_TYPES.indexOf((section?.get('ARMOR') ?? 'none').toLowerCase())),
      weapon: weapon && {
        name: weaponName!,
        damage: Number(weapon.get('DAMAGE') ?? 0),
        rof: Number(weapon.get('ROF') ?? 15),
        range: Number(weapon.get('RANGE') ?? 1),
        verses: list(warhead?.get('VERSES') ?? '100%').map(v => Number.parseFloat(v) / 100),
        reports: list(weapon.get('REPORT')),
        impactReports: reportsOf(warhead?.get('ANIMLIST')),
        wall: yes(warhead?.get('WALL')),
        projectile: visible
          ? { arcing: yes(projectile!.get('ARCING')), homing: Number(projectile!.get('ROT') ?? 0) > 0 }
          : undefined,
        speed: Math.max(MIN_PROJECTILE_SPEED, (speed / LEPTONS_PER_CELL) * PROJECTILE_FRAMES_PER_SECOND),
        spread: Number(warhead?.get('CELLSPREAD') ?? 0),
        percentAtMax: Number(warhead?.get('PERCENTATMAX') ?? 1),
      },
      explosionReports: reportsOf(section?.get('EXPLOSION')),
    }
  }
  const add = (option: BuildOption, structure: boolean) => {
    const section = rules.get(option.id)
    prerequisites.set(option.id, list(section?.get('PREREQUISITE')))
    const cost = Number(section?.get('COST') ?? 0)
    const image = section?.get('IMAGE') ?? option.id
    const [fw, fh] = (art.get(image.toUpperCase())?.get('FOUNDATION') ?? art.get(option.id)?.get('FOUNDATION') ?? '1x1').split('x').map(Number)
    info.set(option.id, {
      id: option.id,
      name: option.name,
      structure,
      cost,
      seconds: (cost / 1000) * buildSpeed * 60,
      power: Number(section?.get('POWER') ?? 0),
      foundation: [fw || 1, fh || 1],
      adjacent: Number(section?.get('ADJACENT') ?? 2),
      techLevel: Number(section?.get('TECHLEVEL') ?? 1),
      ...combat(section),
      crusher: CRUSHERS.has(option.id) || yes(section?.get('CRUSHER')),
      crushable: section?.has('CRUSHABLE') ? yes(section.get('CRUSHABLE')) : infantry.has(option.id) || CRUSHABLE_WALLS.has(option.id),
      voices: {
        select: list(section?.get('VOICESELECT')),
        move: list(section?.get('VOICEMOVE')),
        attack: list(section?.get('VOICEATTACK')),
        die: list(section?.get('VOICEDIE')),
      },
    })
  }
  for (const option of GDI_BUILD_OPTIONS.structures) add(option, true)
  for (const option of GDI_BUILD_OPTIONS.units) add(option, false)
  // the construction yard is never built from the sidebar, but it is part of the base
  add({ id: 'GACNST', name: 'Bauhof' }, true)
  // nor are the sandbags (TechLevel=-1), which some missions put round a base
  add({ id: 'GASAND', name: 'Sandsäcke' }, true)
  // units the missions bring along that are not built from the sidebar (yet): they
  // need their weapon, armor and voices all the same
  for (const option of [
    { id: 'SMECH', name: 'Wolverine' },
    { id: 'MMCH', name: 'Titan' },
    { id: 'HARV', name: 'Sammler' },
    { id: 'MCV', name: 'MBF' },
  ]) {
    if (!info.has(option.id)) add(option, false)
  }
  // a building that has no explosion of its own sounds like the vehicles blowing up
  // (failing that, like the explosions of the warheads)
  const all = [...info.values()]
  const blasts = [...new Set(all.flatMap(i => i.explosionReports))]
  const fallback = blasts.length ? blasts : [...new Set(all.flatMap(i => i.weapon?.impactReports ?? []))]
  for (const building of all) {
    if (building.structure && !building.explosionReports.length) building.explosionReports = fallback
  }
  // "50%" or ".5"
  const share = (value: string | undefined, fallback: number) =>
    value ? Number.parseFloat(value) / (value.trim().endsWith('%') ? 100 : 1) : fallback
  const upkeep: Upkeep = {
    refund: share(general?.get('REFUNDPERCENT'), DEFAULT_UPKEEP.refund),
    repairCost: share(general?.get('REPAIRPERCENT'), DEFAULT_UPKEEP.repairCost),
    repairSeconds: Number(general?.get('REPAIRRATE') ?? DEFAULT_UPKEEP.repairSeconds / 60) * 60,
    repairStep: Number(general?.get('REPAIRSTEP') ?? DEFAULT_UPKEEP.repairStep),
  }
  return { prerequisites, generic, info, tiberiumValue: Number(rules.get('RIPARIUS')?.get('VALUE') ?? 25),
    blueTiberiumValue: Number(rules.get('VINIFERA')?.get('VALUE') ?? 50), upkeep }
}

/** Whether an option can be built with the buildings owned (object ids). */
export function canBuild(rules: BuildRules, id: string, owned: string[], structure: boolean) {
  if (structure && !owned.some(b => CONSTRUCTION_YARDS.includes(b))) return false
  return (rules.prerequisites.get(id) ?? []).every((need) => {
    const any = rules.generic.get(need)
    return any ? any.some(b => owned.includes(b)) : owned.includes(need)
  })
}

/** Cameo pictures as data URLs, by object id; missing ones are left out. */
export async function loadCameos(store: AssetStore, ids: string[]): Promise<Map<string, string>> {
  const cameos = new Map<string, string>()
  const tibsun = await store.get('TIBSUN.MIX')
  if (!tibsun) return cameos
  const archive = await MixArchive.open(tibsun, 'TIBSUN.MIX')
  const [local, conquer, sidebar, cache] = await Promise.all(
    ['LOCAL.MIX', 'CONQUER.MIX', 'SIDEC01.MIX', 'CACHE.MIX'].map(name => archive.openNested(name)),
  )
  const text = async (name: string) => {
    const bytes = await local?.read(name)
    return bytes ? parseIni(new TextDecoder('latin1').decode(bytes)) : new Map()
  }
  const [rules, art] = await Promise.all([text('RULES.INI'), text('ART.INI')])
  const pal = await cache?.read('CAMEO.PAL')
  if (!pal) return cameos
  const palette = decodePalette(pal)

  for (const id of ids) {
    const image = rules.get(id)?.get('IMAGE') ?? id
    const cameo = art.get(image)?.get('CAMEO') ?? art.get(id)?.get('CAMEO')
    if (!cameo) continue
    const bytes = await sidebar?.read(`${cameo}.SHP`) ?? await conquer?.read(`${cameo}.SHP`)
    if (!bytes) continue
    const shp = decodeShp(bytes)
    const canvas = document.createElement('canvas')
    canvas.width = shp.width
    canvas.height = shp.height
    const rgba = frameToRgba(shp, shp.frames[0]!, palette)
    for (let i = 3; i < rgba.length; i += 4) rgba[i] = 255 // cameos are full pictures, index 0 is black
    canvas.getContext('2d')!.putImageData(new ImageData(rgba, shp.width, shp.height), 0, 0)
    cameos.set(id, canvas.toDataURL())
  }
  return cameos
}
