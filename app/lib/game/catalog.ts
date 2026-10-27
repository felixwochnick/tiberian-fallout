import { MixArchive } from '../formats/mix'
import { decodePalette, decodeShp, frameToRgba } from '../formats/shp'
import type { AssetStore } from '../storage/asset-store'
import { expansionArchive, gameIni } from './gamefiles'

/**
 * Everything the game knows about: all buildings, infantry, vehicles and aircraft
 * listed in RULES.INI, with their cameo picture (ART.INI Cameo=, from the game's
 * archives). For the dev catalog page.
 */

export type Category = 'building' | 'infantry' | 'vehicle' | 'aircraft'

export interface CatalogEntry {
  id: string
  category: Category
  name: string
  owner: string
  cost: number
  techLevel: number
  strength: number
  /** Name of the cameo picture in the game's files */
  cameoName?: string
  /** The cameo as data URL, if it was found */
  cameo?: string
}

const SECTIONS: [string, Category][] = [
  ['BUILDINGTYPES', 'building'],
  ['INFANTRYTYPES', 'infantry'],
  ['VEHICLETYPES', 'vehicle'],
  ['AIRCRAFTTYPES', 'aircraft'],
]

export async function loadCatalog(store: AssetStore): Promise<CatalogEntry[]> {
  const tibsun = await store.get('TIBSUN.MIX')
  if (!tibsun) return []
  const archive = await MixArchive.open(tibsun, 'TIBSUN.MIX')
  // cameos are in CONQUER.MIX, side-specific ones in the sidebar archives
  const [cache, ...pictures] = await Promise.all(
    ['CACHE.MIX', 'CONQUER.MIX', 'SIDEC01.MIX', 'SIDEC02.MIX'].map(name => archive.openNested(name)),
  )
  // with Firestorm: its rules, art and cameos too
  const [rules, art] = await Promise.all([gameIni(store, 'RULES.INI'), gameIni(store, 'ART.INI')])
  if (!rules || !art) return []
  const expansion = await expansionArchive(store)
  if (expansion) {
    pictures.push(expansion, ...(await Promise.all(['ECACHE01.MIX', 0x30F90780].map(name => expansion.openNested(name).catch(() => undefined)))))
  }
  const pal = await cache?.read('CAMEO.PAL')
  const palette = pal && decodePalette(pal)

  const picture = async (name: string) => {
    if (!palette) return undefined
    for (const mix of pictures) {
      const bytes = await mix?.read(`${name}.SHP`)
      if (!bytes) continue
      const shp = decodeShp(bytes)
      const rgba = frameToRgba(shp, shp.frames[0]!, palette)
      for (let i = 3; i < rgba.length; i += 4) rgba[i] = 255
      const canvas = document.createElement('canvas')
      canvas.width = shp.width
      canvas.height = shp.height
      canvas.getContext('2d')!.putImageData(new ImageData(rgba, shp.width, shp.height), 0, 0)
      return canvas.toDataURL()
    }
    return undefined
  }

  const entries: CatalogEntry[] = []
  const seen = new Set<string>()
  for (const [section, category] of SECTIONS) {
    for (const raw of rules.get(section)?.values() ?? []) {
      const id = raw.trim().toUpperCase()
      if (!id || seen.has(id)) continue
      seen.add(id)
      const own = rules.get(id)
      const image = (own?.get('IMAGE') ?? id).toUpperCase()
      const cameoName = (art.get(image)?.get('CAMEO') ?? art.get(id)?.get('CAMEO'))?.toUpperCase()
      entries.push({
        id,
        category,
        name: own?.get('NAME') ?? id,
        owner: own?.get('OWNER') ?? '',
        cost: Number(own?.get('COST') ?? 0),
        techLevel: Number(own?.get('TECHLEVEL') ?? -1),
        strength: Number(own?.get('STRENGTH') ?? 0),
        cameoName,
        cameo: cameoName && cameoName !== 'XXICON' ? await picture(cameoName) : undefined,
      })
    }
  }
  return entries
}
