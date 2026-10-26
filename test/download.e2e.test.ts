import { describe, expect, it } from 'vitest'
import { isWantedDiscFile } from '../shared/game-discs'
import { openRemoteZipEntry } from '../app/lib/download/remote-zip'
import { extractIsoStream } from '../app/lib/formats/iso9660'
import { MixArchive } from '../app/lib/formats/mix'
import { MixEntrySink } from '../app/lib/download/mix-entry-sink'
import { decodeVqaAudio } from '../app/lib/formats/vqa'

/**
 * End-to-end check of the download pipeline against a running dev server.
 * Run with E2E_BASE=http://localhost:3000 pnpm test
 */
const base = process.env.E2E_BASE

describe.skipIf(!base)('game data download', () => {
  it('rejects unknown discs', async () => {
    expect((await fetch(`${base}/api/game-data/nope`)).status).toBe(404)
  })

  it('streams the first archive off the GDI disc', async () => {
    const url = `${base}/api/game-data/gdi`
    let received = 0
    const { entry: iso, stream } = await openRemoteZipEntry(url, name => name.endsWith('.iso'), (n) => { received = n })
    expect(iso.size).toBeGreaterThan(700_000_000)
    const parts: Uint8Array[] = []
    const files = await extractIsoStream(stream, p => p === 'MAPS01.MIX', async () => ({
      write: async (chunk) => { parts.push(chunk.slice()) },
      close: async () => {},
      abort: async () => {},
    }))

    expect(files).toEqual([{ path: 'MAPS01.MIX', size: 3_668_236 }])
    // stops as soon as the wanted file is complete instead of downloading everything
    expect(received).toBeLessThan(iso.compressedSize / 2)
    const mix = await MixArchive.open(new Blob(parts as BlobPart[]), 'MAPS01.MIX')
    expect(mix.entries.length).toBeGreaterThan(0)
    console.log('MAPS01.MIX', mix.encrypted ? 'encrypted' : 'plain', mix.entries.length, 'entries; downloaded', received)
  }, 120_000)

  it('extracts STARTUP.VQA out of the streamed cutscene archive', async () => {
    const url = `${base}/api/game-data/gdi`
    const { stream } = await openRemoteZipEntry(url, name => name.endsWith('.iso'))
    const parts: Uint8Array[] = []
    let closed = false
    await extractIsoStream(stream, p => p === 'MOVIES01.MIX', async () => new MixEntrySink(['STARTUP.VQA'], async () => ({
      write: async (chunk) => { parts.push(chunk.slice()) },
      close: async () => { closed = true },
      abort: async () => {},
    })))
    expect(closed).toBe(true)
    const vqa = new Uint8Array(await new Blob(parts as BlobPart[]).arrayBuffer())
    const audio = decodeVqaAudio(vqa)
    expect(audio.channels).toBe(2)
    expect(audio.samples.length / 2 / audio.sampleRate).toBeCloseTo(6, 1)
  }, 300_000)

  it('selects the game archives from the disc listing', () => {
    expect(['MAPS01.MIX', 'INSTALL/TIBSUN.MIX', 'SCORES.MIX', 'MULTI.MIX', 'SIDECD01.MIX'].every(isWantedDiscFile)).toBe(true)
    expect(['MOVIES01.MIX', 'SETUP/SETUP.MIX', 'AUTORUN.EXE'].some(isWantedDiscFile)).toBe(false)
  })
})
