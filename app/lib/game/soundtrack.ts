import { looksLikeAud } from '../formats/aud'
import { parseIni } from '../formats/ini'
import { MixArchive, type MixEntry } from '../formats/mix'
import type { AssetStore } from '../storage/asset-store'

export interface Track {
  id: string
  title: string
  filename?: string
  archive: MixArchive
  entry: MixEntry
}

/**
 * Fallback names (from the original THEME.INI), used when TIBSUN.MIX is
 * missing. Entries that stay unnamed are still detected by sniffing the
 * AUD header.
 */
const KNOWN_THEMES: Record<string, string> = {
  APPROACH: 'Approach',
  DEFENSE: 'Defense',
  DUSKHOUR: 'Dusk Hour',
  FLURRY: 'Flurry',
  GLOOM: 'Gloom',
  HEROISM: 'Heroism',
  INFRARED: 'Infrared',
  INTRO: 'Intro',
  IONSTORM: 'Ion Storm Ambient',
  LONETROP: 'Lone Troop',
  MADRAP: 'Mad Rap',
  MAPS: 'Map Selection',
  MUTANTS: 'Mutants',
  NODCRUSH: 'Nod Crush',
  PHAROTEK: 'Pharotek',
  REDSKY: 'Red Sky',
  SCORE: 'Score Screen',
  SCOUT: 'Scout',
  STORM: 'Ion Storm',
  TIMEBOMB: 'Time Bomb',
  VALVES1B: 'Valves',
  WHATLURK: 'What Lurks',
}

async function readThemeIni(store: AssetStore, archive: string, nested?: string) {
  const blob = await store.get(archive)
  if (!blob) return undefined
  try {
    let mix: MixArchive | undefined = await MixArchive.open(blob, archive)
    if (nested) mix = await mix.openNested(nested)
    const bytes = await mix?.read('THEME.INI')
    return bytes && new TextDecoder('latin1').decode(bytes)
  }
  catch (error) {
    console.warn(`THEME.INI aus ${archive} konnte nicht gelesen werden`, error)
    return undefined
  }
}

async function loadThemeNames(store: AssetStore): Promise<Map<string, string>> {
  const names = new Map(Object.entries(KNOWN_THEMES))

  // Later sources override earlier ones (Firestorm extends the base game list)
  const sources = [
    await readThemeIni(store, 'TIBSUN.MIX', 'LOCAL.MIX'),
    await readThemeIni(store, 'EXPAND01.MIX'),
    await store.get('THEME.INI').then(f => f?.text()),
  ]

  for (const text of sources) {
    if (!text) continue
    const ini = parseIni(text)
    for (const id of ini.get('THEMES')?.values() ?? []) {
      const title = ini.get(id.toUpperCase())?.get('NAME')?.replace(/^THEME:/i, '')
      if (title) names.set(id.toUpperCase(), title)
    }
  }
  return names
}

export async function loadSoundtrack(store: AssetStore): Promise<Track[]> {
  const tracks: Track[] = []
  const themeNames = await loadThemeNames(store)

  for (const scoreFile of ['SCORES.MIX', 'SCORES01.MIX']) {
    const blob = await store.get(scoreFile)
    if (!blob) continue
    const archive = await MixArchive.open(blob, scoreFile)
    const named = new Set<number>()

    for (const [id, title] of themeNames) {
      const entry = archive.entry(`${id}.AUD`)
      if (!entry || named.has(entry.hash)) continue
      named.add(entry.hash)
      tracks.push({ id: `${scoreFile}:${id}`, title, filename: `${id}.AUD`, archive, entry })
    }

    let unknown = 0
    for (const entry of archive.entries) {
      if (named.has(entry.hash)) continue
      const head = new Uint8Array(await archive.entryBlob(entry).slice(0, 20).arrayBuffer())
      if (!looksLikeAud(head, entry.length)) continue
      unknown++
      tracks.push({
        id: `${scoreFile}:${entry.hash.toString(16)}`,
        title: `Unbekannter Track ${unknown}`,
        archive,
        entry,
      })
    }
  }
  return tracks.sort((a, b) => Number(!a.filename) - Number(!b.filename) || a.title.localeCompare(b.title))
}
