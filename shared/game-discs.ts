/**
 * Freeware CD images of Tiberian Sun (released by EA in 2010),
 * mirrored by the community site cnc-comm.com as ZIP archives.
 */
export interface GameDisc {
  id: string
  title: string
  description: string
  url: string
  /** Size of the ZIP download in bytes */
  size: number
  optional: boolean
  /** Archive whose presence shows that this disc has been imported */
  marker: string
  /** Single files taken out of archives that are otherwise skipped */
  extract: Record<string, string[]>
  /** Archives that are otherwise skipped but kept whole (their extract entries are then read from them) */
  keep?: string[]
}

export const GAME_DISCS: GameDisc[] = [
  {
    id: 'gdi',
    title: 'Tiberian Sun',
    description: 'Basisspiel (GDI-CD): Grafiken, Sounds, Karten und Soundtrack',
    url: 'https://downloads.cnc-comm.com/tiberian-sun/iso/TS_GDI.zip',
    size: 575_892_953,
    optional: false,
    marker: 'TIBSUN.MIX',
    // The Westwood logo and the 6 second animation that opens the main menu (for their sound)
    extract: { 'MOVIES01.MIX': ['STARTUP.VQA', 'WWLOGO.VQA'] },
    // all GDI videos: briefings, the radar transmissions and in-mission sequences (~490 MB)
    keep: ['MOVIES01.MIX'],
  },
  {
    id: 'firestorm',
    title: 'Firestorm',
    description: 'Erweiterung: zusätzliche Einheiten, Karten und Musik',
    url: 'https://downloads.cnc-comm.com/tiberian-sun/iso/TS_Firestorm.zip',
    size: 521_033_163,
    optional: true,
    marker: 'EXPAND01.MIX',
    extract: {},
  },
]

/**
 * Archives we keep from the CDs. The cutscene archives (MOVIES*.MIX, ~450 MB
 * each) and installer data are skipped to save browser storage.
 */
export function isWantedDiscFile(path: string) {
  const name = discFileName(path)
  return name.endsWith('.MIX') && !name.startsWith('MOVIES') && name !== 'SETUP.MIX'
}

export function discFileName(path: string) {
  return path.split('/').pop()!.toUpperCase()
}

/** All files a disc contributes to the asset store (entries of kept archives are read from them). */
export function discOutputFiles(disc: GameDisc) {
  const extracted = Object.entries(disc.extract).filter(([archive]) => !disc.keep?.includes(archive)).flatMap(([, files]) => files)
  return [disc.marker, ...(disc.keep ?? []), ...extracted]
}
