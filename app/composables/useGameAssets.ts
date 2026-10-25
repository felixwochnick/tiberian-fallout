import { discFileName, discOutputFiles, GAME_DISCS, isWantedDiscFile, type GameDisc } from '#shared/game-discs'
import { MixEntrySink } from '~/lib/download/mix-entry-sink'
import { listRemoteZip, openRemoteZipEntry } from '~/lib/download/remote-zip'
import { extractIsoStream, listIsoFiles } from '~/lib/formats/iso9660'
import { getAssetStore, type StoredFile } from '~/lib/storage/asset-store'

/** Files we keep from an installation / CD. Everything else is ignored. */
const RELEVANT_FILE = /\.(mix|ini)$/i

/** Archives that must be present to play the soundtrack. */
export const REQUIRED_FOR_MUSIC = ['SCORES.MIX']

export interface ImportProgress {
  /** File currently being written */
  file: string
  done: number
  total: number
  /** Set while downloading: the disc being processed */
  disc?: string
}

/** Shared across all composable instances so any component can cancel. */
let abortController: AbortController | undefined

function basename(path: string) {
  return path.split(/[\\/]/).pop() ?? path
}

export function useGameAssets() {
  const files = useState<StoredFile[]>('game-assets:files', () => [])
  const persistent = useState('game-assets:persistent', () => false)
  const loaded = useState('game-assets:loaded', () => false)
  const importing = useState('game-assets:importing', () => false)
  const progress = useState<ImportProgress | null>('game-assets:progress', () => null)
  const error = useState<string | null>('game-assets:error', () => null)
  const downloadError = useState<string | null>('game-assets:download-error', () => null)

  const hasMusic = computed(() =>
    REQUIRED_FOR_MUSIC.every(name => files.value.some(f => f.name === name)),
  )

  const isDiscLoaded = (disc: GameDisc) =>
    discOutputFiles(disc).every(name => files.value.some(f => f.name === name))

  async function refresh() {
    const store = await getAssetStore()
    persistent.value = store.persistent
    files.value = await store.list()
    loaded.value = true
  }

  /** Expands ISO images and filters the selection down to game archives. */
  async function collect(selection: File[]) {
    const collected = new Map<string, Blob>()
    for (const file of selection) {
      if (/\.iso$/i.test(file.name)) {
        const isoFiles = await listIsoFiles(file, path => RELEVANT_FILE.test(path))
        for (const entry of isoFiles) {
          const name = basename(entry.path).toUpperCase()
          if (!collected.has(name)) collected.set(name, entry.blob)
        }
      }
      else if (RELEVANT_FILE.test(file.name)) {
        const name = file.name.toUpperCase()
        if (!collected.has(name)) collected.set(name, file)
      }
    }
    return collected
  }

  async function importFiles(selection: File[]) {
    if (importing.value) return
    importing.value = true
    error.value = null
    try {
      const store = await getAssetStore()
      const collected = await collect(selection)
      if (collected.size === 0) {
        throw new Error('In der Auswahl wurden keine Tiberian-Sun-Dateien (*.mix / *.iso) gefunden.')
      }

      const total = [...collected.values()].reduce((sum, blob) => sum + blob.size, 0)
      let done = 0
      for (const [name, blob] of collected) {
        const before = done
        progress.value = { file: name, done, total }
        await store.put(name, blob, (written) => {
          progress.value = { file: name, done: before + written, total }
        })
        done = before + blob.size
      }
      await refresh()
    }
    catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    }
    finally {
      importing.value = false
      progress.value = null
    }
  }

  /**
   * Downloads the freeware CD images through the server proxy and extracts
   * the game archives while the data streams in.
   */
  async function downloadDiscs(discs: GameDisc[]) {
    if (importing.value || !discs.length) return
    importing.value = true
    downloadError.value = null
    abortController = new AbortController()
    const { signal } = abortController
    const total = discs.reduce((sum, disc) => sum + disc.size, 0)
    let finished = 0

    try {
      const store = await getAssetStore()
      for (const disc of discs) {
        const url = `/api/game-data/${disc.id}`
        const iso = (await listRemoteZip(url, signal)).find(e => /\.iso$/i.test(e.name))
        if (!iso) throw new Error(`${disc.title}: kein CD-Image im Archiv gefunden`)

        let file = 'Lese Inhaltsverzeichnis …'
        let received = 0
        const report = () => {
          progress.value = { disc: disc.title, file, done: finished + received, total }
        }
        report()

        const stream = await openRemoteZipEntry(url, iso, (bytes) => {
          received = bytes
          report()
        }, signal)

        // Only fetch what is still missing (e.g. files added in a later version)
        const stored = new Set((await store.list()).map(f => f.name))
        // entries of a kept archive come with the archive itself
        const missingEntries = (archive: string) => disc.keep?.includes(archive) ? [] : (disc.extract[archive] ?? []).filter(n => !stored.has(n))
        const kept = (name: string) => !!disc.keep?.includes(name) && !stored.has(name)
        const wanted = (path: string) => {
          const name = discFileName(path)
          return (isWantedDiscFile(path) && !stored.has(name)) || kept(name) || missingEntries(name).length > 0
        }

        await extractIsoStream(stream, wanted, async (entry) => {
          const name = discFileName(entry.path)
          const entries = missingEntries(name)
          if (entries.length) {
            return new MixEntrySink(entries, (entryName) => {
              file = entryName
              report()
              return store.createWriter(entryName)
            })
          }
          file = name
          report()
          return store.createWriter(name)
        })
        finished += disc.size
        await refresh()
      }
    }
    catch (e) {
      downloadError.value = signal.aborted
        ? 'Download abgebrochen.'
        : `Download fehlgeschlagen: ${e instanceof Error ? e.message : String(e)}`
      await refresh()
    }
    finally {
      importing.value = false
      progress.value = null
      abortController = undefined
    }
  }

  function cancel() {
    abortController?.abort()
  }

  async function clear() {
    const store = await getAssetStore()
    await store.clear()
    await refresh()
  }

  return {
    discs: GAME_DISCS,
    files,
    persistent,
    loaded,
    importing,
    progress,
    error,
    downloadError,
    hasMusic,
    isDiscLoaded,
    refresh,
    importFiles,
    downloadDiscs,
    cancel,
    clear,
  }
}
