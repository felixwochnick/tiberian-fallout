import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { decodeAud } from '../app/lib/formats/aud'
import { MixArchive } from '../app/lib/formats/mix'
import { loadSoundtrack } from '../app/lib/game/soundtrack'
import type { AssetStore } from '../app/lib/storage/asset-store'

/**
 * Optional checks against the original game files.
 * Run with TS_DATA=/path/to/folder/with/mix/files pnpm test
 */
const dir = process.env.TS_DATA
const file = (name: string) => new File([readFileSync(join(dir!, name))], name)

describe.skipIf(!dir || !existsSync(join(dir, 'SCORES.MIX')))('original game data', () => {
  it('opens TIBSUN.MIX and finds THEME.INI', async () => {
    const tibsun = await MixArchive.open(file('TIBSUN.MIX'), 'TIBSUN.MIX')
    const local = await tibsun.openNested('LOCAL.MIX')
    const theme = await local?.read('THEME.INI')
    expect(theme?.length).toBeGreaterThan(0)
    console.log(new TextDecoder('latin1').decode(theme).slice(0, 1500))
  })

  it('lists and decodes the soundtrack', async () => {
    const store = { get: async (name: string) => (existsSync(join(dir!, name)) ? file(name) : undefined) } as AssetStore
    const tracks = await loadSoundtrack(store)
    console.log(tracks.map(t => `${t.title} (${t.filename ?? t.entry.hash.toString(16)})`).join('\n'))
    expect(tracks.length).toBeGreaterThan(10)

    const audio = decodeAud((await tracks[0]!.archive.read(tracks[0]!.entry))!)
    console.log(audio.sampleRate, audio.channels, audio.samples.length)
    expect(audio.samples.length).toBeGreaterThan(audio.sampleRate * 30)
  })
})
