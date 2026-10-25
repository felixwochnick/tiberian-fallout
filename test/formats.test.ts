import { describe, expect, it } from 'vitest'
import { decodeAud, looksLikeAud } from '../app/lib/formats/aud'
import { Blowfish } from '../app/lib/formats/blowfish'
import { crc32, hashFilenameCrc } from '../app/lib/formats/hash'
import { parseIni } from '../app/lib/formats/ini'
import { MixArchive } from '../app/lib/formats/mix'
import { decodePalette, decodeShp } from '../app/lib/formats/shp'
import { decryptMixKey } from '../app/lib/formats/westwood-key'

const hex = (bytes: Uint8Array) => [...bytes].map(b => b.toString(16).padStart(2, '0')).join('')
const fromHex = (s: string) => Uint8Array.from(s.match(/../g)!, b => Number.parseInt(b, 16))

describe('blowfish', () => {
  it('matches the reference test vectors', () => {
    // Schneier's published vectors (key, ciphertext of plaintext)
    const vectors = [
      ['0000000000000000', '0000000000000000', '4ef997456198dd78'],
      ['ffffffffffffffff', 'ffffffffffffffff', '51866fd5b85ecb8a'],
      ['0123456789abcdef', '1111111111111111', '61f9c3802281b096'],
    ]
    for (const [key, plain, cipher] of vectors) {
      expect(hex(new Blowfish(fromHex(key!)).decrypt(fromHex(cipher!)))).toBe(plain)
    }
  })
})

describe('hashing', () => {
  it('computes standard crc32', () => {
    expect(crc32(new TextEncoder().encode('123456789'))).toBe(0xcbf43926)
  })

  it('pads TS filenames before hashing', () => {
    // length 8 (no padding) is a plain CRC of the uppercase name
    expect(hashFilenameCrc('local.mx')).toBe(crc32(new TextEncoder().encode('LOCAL.MX')))
    // "A.B" -> "A.B" + chr(3)
    expect(hashFilenameCrc('a.b')).toBe(crc32(Uint8Array.from([65, 46, 66, 3])))
  })
})

describe('mix', () => {
  it('reads an unencrypted TS archive', async () => {
    const payload = new TextEncoder().encode('[Themes]\n1=DUSK\n')
    const header = new DataView(new ArrayBuffer(4 + 6 + 12))
    header.setUint32(0, 0, true) // flags
    header.setUint16(4, 1, true)
    header.setUint32(6, payload.length, true)
    header.setUint32(10, hashFilenameCrc('THEME.INI'), true)
    header.setUint32(14, 0, true)
    header.setUint32(18, payload.length, true)

    const mix = await MixArchive.open(new Blob([header.buffer, payload]), 'TEST.MIX')
    expect(mix.encrypted).toBe(false)
    expect(mix.has('theme.ini')).toBe(true)
    const text = new TextDecoder().decode(await mix.read('THEME.INI'))
    expect(parseIni(text).get('THEMES')?.get('1')).toBe('DUSK')
  })

  it('derives a 56 byte blowfish key from a key source', () => {
    expect(decryptMixKey(new Uint8Array(80).fill(7))).toHaveLength(56)
  })
})

describe('aud', () => {
  it('decodes IMA ADPCM chunks', () => {
    const compressed = new Uint8Array(16).fill(0x77)
    const outputSize = compressed.length * 4
    const bytes = new Uint8Array(12 + 8 + compressed.length)
    const view = new DataView(bytes.buffer)
    view.setUint16(0, 22050, true)
    view.setUint32(2, 8 + compressed.length, true)
    view.setUint32(6, outputSize, true)
    view.setUint8(10, 2) // 16 bit mono
    view.setUint8(11, 99)
    view.setUint16(12, compressed.length, true)
    view.setUint16(14, outputSize, true)
    view.setUint32(16, 0xdeaf, true)
    bytes.set(compressed, 20)

    expect(looksLikeAud(bytes, bytes.length)).toBe(true)
    const audio = decodeAud(bytes)
    expect(audio.sampleRate).toBe(22050)
    expect(audio.samples).toHaveLength(outputSize / 2)
    // nibble 7 is the largest positive step, so the waveform must rise monotonically
    for (let i = 1; i < audio.samples.length; i++) expect(audio.samples[i]).toBeGreaterThanOrEqual(audio.samples[i - 1]!)
  })
})

describe('shp', () => {
  it('decodes a frame with zero runs (format 3) into the full canvas', () => {
    // 4×3 canvas, one frame: 2×2 at (1,1); rows "0 x1 07" = [transparent, 7] and "05 06" = [5, 6]
    const header = [0, 0, 4, 0, 3, 0, 1, 0]
    const frame = [1, 0, 1, 0, 2, 0, 2, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 32, 0, 0, 0]
    const rows = [5, 0, 0, 1, 7, 4, 0, 5, 6]
    const shp = decodeShp(Uint8Array.from([...header, ...frame, ...rows]))
    expect(shp.width).toBe(4)
    expect(shp.height).toBe(3)
    expect([...shp.frames[0]!.pixels]).toEqual([0, 0, 0, 0, 0, 0, 7, 0, 0, 5, 6, 0])
  })

  it('expands 6 bit palettes to 8 bit', () => {
    const palette = decodePalette(Uint8Array.from({ length: 768 }, (_, i) => (i < 3 ? 63 : 0)))
    expect([...palette.subarray(0, 4)]).toEqual([255, 255, 255, 0])
  })
})

describe('build prerequisites', () => {
  it('needs all listed buildings, generic names stand for any of their kind', async () => {
    const { canBuild } = await import('../app/lib/game/cameos')
    const rules = {
      prerequisites: new Map([['GAWEAP', ['PROC', 'GAPILE']], ['E1', ['BARRACKS']], ['GAPOWR', []]]),
      generic: new Map([['BARRACKS', ['NAHAND', 'GAPILE']]]),
      info: new Map(),
    }
    expect(canBuild(rules, 'GAWEAP', ['GACNST', 'PROC'], true)).toBe(false)
    expect(canBuild(rules, 'GAWEAP', ['GACNST', 'PROC', 'GAPILE'], true)).toBe(true)
    expect(canBuild(rules, 'E1', ['GAPILE'], false)).toBe(true)
    expect(canBuild(rules, 'E1', ['GAPOWR'], false)).toBe(false)
    // structures need a construction yard
    expect(canBuild(rules, 'GAPOWR', ['GAPILE'], true)).toBe(false)
  })
})
