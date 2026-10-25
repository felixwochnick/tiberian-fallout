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
}

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
  /** Armor= as index into a warhead's Verses= (none, wood, light, heavy, concrete) */
  armor: number
  /** Primary= weapon, if it has one */
  weapon?: Weapon
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
}

const ARMOR_TYPES = ['none', 'wood', 'light', 'heavy', 'concrete']

export type UnitVoice = 'select' | 'move' | 'attack' | 'die'

const CONSTRUCTION_YARDS = ['GACNST', 'NACNST']

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
  const prerequisites = new Map<string, string[]>()
  const info = new Map<string, BuildInfo>()
  /** Hit points, armor and weapon of an object (with its weapon's warhead) */
  const combat = (section?: Map<string, string>) => {
    const weaponName = section?.get('PRIMARY')
    const weapon = weaponName && weaponName.toLowerCase() !== 'none' ? rules.get(weaponName.toUpperCase()) : undefined
    const warhead = weapon && rules.get((weapon.get('WARHEAD') ?? '').toUpperCase())
    return {
      strength: Number(section?.get('STRENGTH') ?? 100),
      sight: Number(section?.get('SIGHT') ?? 5),
      armor: Math.max(0, ARMOR_TYPES.indexOf((section?.get('ARMOR') ?? 'none').toLowerCase())),
      weapon: weapon && {
        name: weaponName!,
        damage: Number(weapon.get('DAMAGE') ?? 0),
        rof: Number(weapon.get('ROF') ?? 15),
        range: Number(weapon.get('RANGE') ?? 1),
        verses: list(warhead?.get('VERSES') ?? '100%').map(v => Number.parseFloat(v) / 100),
        reports: list(weapon.get('REPORT')),
      },
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
  return { prerequisites, generic, info }
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
