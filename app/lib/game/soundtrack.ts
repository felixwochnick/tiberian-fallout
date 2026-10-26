import { looksLikeAud } from '../formats/aud'
import { parseIni } from '../formats/ini'
import { MixArchive, type MixEntry } from '../formats/mix'
import type { AssetStore } from '../storage/asset-store'

export interface Track {
  id: string
  title: string
  filename?: string
  /** In the in-game play list (THEME.INI `Normal`); the menu and screen themes are not */
  normal: boolean
  archive: MixArchive
  entry: MixEntry
}

/**
 * Fallback names (from the original THEME.INI), used when TIBSUN.MIX is
 * missing. Entries that stay unnamed are still detected by sniffing the
 * AUD header.
 */
/** Themes that only play on their own screen (Normal=no in THEME.INI) */
const SCREEN_THEMES = new Set(['INTRO', 'MAPS', 'SCORE', 'IONSTORM'])

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

interface Theme {
  title: string
  normal: boolean
}

async function openMix(store: AssetStore, archive: string, nested?: string) {
  const blob = await store.get(archive)
  if (!blob) return undefined
  try {
    const mix = await MixArchive.open(blob, archive)
    return nested ? await mix.openNested(nested) : mix
  }
  catch (error) {
    console.warn(`${nested ?? archive} konnte nicht geöffnet werden`, error)
    return undefined
  }
}

async function readThemeIni(mix: MixArchive | undefined) {
  const bytes = await mix?.read('THEME.INI').catch(() => undefined)
  return bytes && new TextDecoder('latin1').decode(bytes)
}

async function loadThemes(store: AssetStore, local: MixArchive | undefined): Promise<Map<string, Theme>> {
  const themes = new Map(Object.entries(KNOWN_THEMES).map(([id, title]) => [id, { title, normal: !SCREEN_THEMES.has(id) }]))

  // Later sources override earlier ones (Firestorm extends the base game list)
  const sources = [
    await readThemeIni(local),
    await readThemeIni(await openMix(store, 'EXPAND01.MIX')),
    await store.get('THEME.INI').then(f => f?.text()),
  ]

  for (const text of sources) {
    if (!text) continue
    const ini = parseIni(text)
    for (const id of ini.get('THEMES')?.values() ?? []) {
      const section = ini.get(id.toUpperCase())
      const title = section?.get('NAME')?.replace(/^THEME:/i, '')
      if (title) themes.set(id.toUpperCase(), { title, normal: !/^(no|false|0)$/i.test(section?.get('NORMAL') ?? '') })
    }
  }
  return themes
}

export async function loadSoundtrack(store: AssetStore): Promise<Track[]> {
  const tracks: Track[] = []
  const local = await openMix(store, 'TIBSUN.MIX', 'LOCAL.MIX')
  const themes = await loadThemes(store, local)
  const found = new Set<string>()

  function addThemes(archive: MixArchive, label: string, named: Set<number>) {
    for (const [id, { title, normal }] of themes) {
      const entry = archive.entry(`${id}.AUD`)
      if (!entry || named.has(entry.hash) || found.has(id)) continue
      named.add(entry.hash)
      found.add(id)
      tracks.push({ id: `${label}:${id}`, title, filename: `${id}.AUD`, normal, archive, entry })
    }
  }

  for (const scoreFile of ['SCORES.MIX', 'SCORES01.MIX']) {
    const blob = await store.get(scoreFile)
    if (!blob) continue
    const archive = await MixArchive.open(blob, scoreFile)
    const named = new Set<number>()
    addThemes(archive, scoreFile, named)

    let unknown = 0
    for (const entry of archive.entries) {
      if (named.has(entry.hash)) continue
      const head = new Uint8Array(await archive.entryBlob(entry).slice(0, 20).arrayBuffer())
      if (!looksLikeAud(head, entry.length)) continue
      unknown++
      tracks.push({
        id: `${scoreFile}:${entry.hash.toString(16)}`,
        title: `Unbekannter Track ${unknown}`,
        normal: true,
        archive,
        entry,
      })
    }
  }
  // the intro and the map selection theme are not in SCORES.MIX but in TIBSUN.MIX › LOCAL.MIX
  if (local) addThemes(local, 'LOCAL.MIX', new Set())
  return tracks.sort((a, b) => Number(!a.filename) - Number(!b.filename) || a.title.localeCompare(b.title))
}
