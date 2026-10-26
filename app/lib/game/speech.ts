import { MixArchive, type MixEntry } from '../formats/mix'
import type { AssetStore } from '../storage/asset-store'

/**
 * The computer voices: EVA (GDI) and CABAL (Nod), from Tiberian Sun and Firestorm.
 * There is no list of the messages in the game data (Tiberian Sun has no EVA.INI),
 * so the file names are found by trying the naming scheme of the speech archives
 * ("00-I018.AUD": voice, I = in-game message / N = mission speech, number); files
 * whose name doesn't fit are listed by their hash.
 */
export interface SpeechFile {
  voice: 'EVA' | 'CABAL'
  /** Archive, e.g. SPEECH01.MIX */
  archive: string
  /** File name, or the hash in hex when the name is not known */
  name: string
  /** What is said, where known */
  title?: string
  mix: MixArchive
  entry: MixEntry
}

const ARCHIVES: { container: string, nested: string, voice: SpeechFile['voice'] }[] = [
  { container: 'TIBSUN.MIX', nested: 'SPEECH01.MIX', voice: 'EVA' },
  { container: 'TIBSUN.MIX', nested: 'SPEECH02.MIX', voice: 'CABAL' },
  { container: 'EXPAND01.MIX', nested: 'E01VOX01.MIX', voice: 'EVA' },
  { container: 'EXPAND01.MIX', nested: 'E01VOX02.MIX', voice: 'CABAL' },
]

/** Prefixes that occur in the speech archives */
const PREFIXES = ['00-I', '00-N', '01-I', '01-N', '19-N', '22-N']

/** What is said, where known (the same for EVA and CABAL; see also UI_SOUNDS in menu/audio.ts) */
export const SPEECH_TITLES: Record<string, string> = {
  '00-I016.AUD': 'Hier nicht platzierbar',
  '00-I018.AUD': 'Konstruktion abgeschlossen',
  '00-I020.AUD': 'Eingehende Übertragung',
  '00-I022.AUD': 'Nicht genügend Geldmittel',
  '00-I024.AUD': 'Zu wenig Energie',
  '00-I026.AUD': 'Einsatz erfolgreich',
  '00-I028.AUD': 'Einsatz fehlgeschlagen',
  '00-I032.AUD': 'Neue Konstruktionsmöglichkeiten',
  '00-I040.AUD': 'Reparatur',
  '00-I058.AUD': 'Countdown gestartet',
  '00-I060.AUD': 'Countdown gestoppt',
  '00-I062.AUD': 'Ausbildung',
  '00-I064.AUD': 'Nicht möglich, Bau läuft',
  '00-I074.AUD': 'Einheit verloren',
  '00-I076.AUD': 'Einheit bereit',
  '00-I082.AUD': 'Unsere Basis wird angegriffen (Gebäude angegriffen)',
  '00-I090.AUD': 'Sammler wird angegriffen',
  '00-I122.AUD': 'Noch 20 Minuten',
  '00-I124.AUD': 'Noch 10 Minuten',
  '00-I126.AUD': 'Noch 5 Minuten',
  '00-I128.AUD': 'Noch 4 Minuten',
  '00-I130.AUD': 'Noch 3 Minuten',
  '00-I132.AUD': 'Noch 2 Minuten',
  '00-I134.AUD': 'Noch 1 Minute',
  '00-I200.AUD': 'Gefechtskontrolle wird übergeben, bitte warten',
  '00-I216.AUD': 'Bau',
  '00-I218.AUD': 'Angehalten',
  '00-I220.AUD': 'Abgebrochen',
  '00-I228.AUD': 'Gebäude verkauft',
  '00-I230.AUD': 'Gebäude abgeschaltet',
  '00-I232.AUD': 'Gebäude eingeschaltet',
}

export async function loadSpeech(store: AssetStore) {
  const files: SpeechFile[] = []
  const containers = new Map<string, MixArchive | undefined>()
  for (const { container, nested, voice } of ARCHIVES) {
    if (!containers.has(container)) {
      const blob = await store.get(container)
      containers.set(container, blob && await MixArchive.open(blob, container).catch(() => undefined))
    }
    const mix = await containers.get(container)?.openNested(nested).catch(() => undefined)
    if (!mix) continue
    const names = new Map<number, string>()
    for (const prefix of PREFIXES) {
      for (let i = 0; i < 1000; i++) {
        const name = `${prefix}${String(i).padStart(3, '0')}.AUD`
        const entry = mix.entry(name)
        if (entry) names.set(entry.hash, name)
      }
    }
    for (const entry of mix.entries) {
      const name = names.get(entry.hash)
      files.push({
        voice,
        archive: nested,
        name: name ?? `#${(entry.hash >>> 0).toString(16).toUpperCase().padStart(8, '0')}`,
        title: name && SPEECH_TITLES[name],
        mix,
        entry,
      })
    }
  }
  // named files in order, the unnamed ones last
  return files.sort((a, b) => Number(a.name.startsWith('#')) - Number(b.name.startsWith('#')) || a.name.localeCompare(b.name))
}
