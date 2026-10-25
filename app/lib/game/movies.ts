import { MixArchive } from '../formats/mix'
import type { AssetStore } from '../storage/asset-store'

/**
 * The videos of the game (VQA). They are in the movie archives of the CDs (MOVIES01.MIX
 * for GDI, MOVIES02.MIX for Nod, MOVIES03.MIX for Firestorm), single ones may also be
 * stored on their own. The names come from XCC's "global mix database" (the archives
 * themselves only hold hashes of the names).
 */

export type MovieKind = 'radar' | 'mission' | 'briefing' | 'other'

export interface MovieInfo {
  name: string
  title: string
  kind: MovieKind
}

/** GDI videos in MOVIES01.MIX */
export const GDI_MOVIES: MovieInfo[] = [
  // short transmissions shown in the radar during missions
  { name: 'GDI01_SB.VQA', title: 'Radar: GDI-Mission 1', kind: 'radar' },
  { name: 'GDI02_SB.VQA', title: 'Radar: GDI-Mission 2', kind: 'radar' },
  { name: 'GDI03_SB.VQA', title: 'Radar: GDI-Mission 3', kind: 'radar' },
  // sequences during missions
  { name: 'TRAINROB.VQA', title: 'Zugüberfall', kind: 'mission' },
  { name: 'ORCASTRK.VQA', title: 'Orca-Angriff', kind: 'mission' },
  { name: 'DISKDEST.VQA', title: 'Disc zerstört', kind: 'mission' },
  { name: 'RETRBTN.VQA', title: 'Vergeltung', kind: 'mission' },
  { name: 'HIDESEEK.VQA', title: 'Versteckspiel', kind: 'mission' },
  { name: 'PODASSLT.VQA', title: 'Drop-Pod-Angriff', kind: 'mission' },
  { name: 'UFOGUARD.VQA', title: 'UFO-Wache', kind: 'mission' },
  { name: 'ICESKATE.VQA', title: 'Auf dem Eis', kind: 'mission' },
  { name: 'NOWCNOT.VQA', title: 'Jetzt sieht man es …', kind: 'mission' },
  { name: 'BEACHEAD.VQA', title: 'Brückenkopf', kind: 'mission' },
  { name: 'KILLMECH.VQA', title: 'Mech-Abschuss', kind: 'mission' },
  { name: 'COUP.VQA', title: 'Putsch', kind: 'mission' },
  { name: 'EMPULSE.VQA', title: 'EMP', kind: 'mission' },
  { name: 'MECHATAK.VQA', title: 'Mech-Angriff', kind: 'mission' },
  { name: 'UNSTPBLE.VQA', title: 'Unaufhaltsam', kind: 'mission' },
  { name: 'GENWIN01.VQA', title: 'Sieg', kind: 'mission' },
  { name: 'NOD_FLAG.VQA', title: 'Nod-Flagge', kind: 'mission' },
  { name: 'N_LOGO_W.VQA', title: 'Nod-Logo', kind: 'mission' },
  // briefings
  ...['M02', 'M03', 'M04', 'M05', 'M06', 'M07', 'M08', 'M09A', 'M09B', 'M09C', 'M10A', 'M11', 'M12A'].map(m => ({
    name: `GDI_${m}.VQA`, title: `Briefing GDI ${m.slice(1)}`, kind: 'briefing' as const,
  })),
  { name: 'GDIM09CW.VQA', title: 'Briefing GDI 09 C (Variante)', kind: 'briefing' },
  { name: 'GDIM09D1.VQA', title: 'Briefing GDI 09 D', kind: 'briefing' },
  { name: 'EVA.VQA', title: 'EVA', kind: 'other' },
  { name: 'INTRO.VQA', title: 'Intro', kind: 'other' },
  { name: 'GDI_FINL.VQA', title: 'GDI-Finale', kind: 'other' },
  { name: 'STARTUP.VQA', title: 'Startanimation', kind: 'other' },
  { name: 'WWLOGO.VQA', title: 'Westwood-Logo', kind: 'other' },
]

const ARCHIVES = ['MOVIES01.MIX', 'MOVIES02.MIX', 'MOVIES03.MIX']
const opened = new WeakMap<AssetStore, Promise<MixArchive[]>>()

/** The movie archives that are in the store (opened once) */
function movieArchives(store: AssetStore) {
  let archives = opened.get(store)
  if (!archives) {
    archives = Promise.all(ARCHIVES.map(async (archive) => {
      const blob = await store.get(archive)
      return blob && MixArchive.open(blob, archive)
    })).then(list => list.filter((a): a is MixArchive => !!a))
    // remember only what was found, so archives loaded later are seen too
    archives.then(list => list.length || opened.delete(store))
    opened.set(store, archives)
  }
  return archives
}

/** A video's bytes: stored on its own or read from one of the movie archives. */
export async function readMovie(store: AssetStore, name: string) {
  const single = await store.get(name)
  if (single) return new Uint8Array(await single.arrayBuffer())
  for (const archive of await movieArchives(store)) {
    if (archive.has(name)) return archive.read(name)
  }
  return undefined
}

/** Which of the known videos are there */
export async function availableMovies(store: AssetStore) {
  const archives = await movieArchives(store)
  const found: MovieInfo[] = []
  for (const movie of GDI_MOVIES) {
    if (archives.some(a => a.has(movie.name)) || await store.get(movie.name)) found.push(movie)
  }
  return found
}
