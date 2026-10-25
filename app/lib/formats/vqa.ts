import { decodeImaAdpcm, type DecodedAudio, type ImaAdpcmState } from './aud'

/**
 * Minimal Westwood VQA reader: header and sound track.
 * (Frame decoding is not needed yet – scenes are rebuilt in Three.js.)
 */

export interface VqaHeader {
  frames: number
  width: number
  height: number
  fps: number
  sampleRate: number
  channels: number
  sampleBits: number
}

const ascii = (bytes: Uint8Array, at: number) => String.fromCharCode(...bytes.subarray(at, at + 4))

export function readVqaHeader(bytes: Uint8Array): VqaHeader {
  if (ascii(bytes, 0) !== 'FORM' || ascii(bytes, 8) !== 'WVQA' || ascii(bytes, 12) !== 'VQHD') {
    throw new Error('Keine VQA-Datei')
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  const h = 20 // start of VQHD payload
  return {
    frames: view.getUint16(h + 4, true),
    width: view.getUint16(h + 6, true),
    height: view.getUint16(h + 8, true),
    fps: view.getUint8(h + 12),
    sampleRate: view.getUint16(h + 24, true),
    channels: view.getUint8(h + 26),
    sampleBits: view.getUint8(h + 27),
  }
}

/** Collects and decodes the SND0/SND2 chunks of a VQA file. */
export function decodeVqaAudio(bytes: Uint8Array): DecodedAudio {
  const header = readVqaHeader(bytes)
  if (!header.channels) throw new Error('VQA enthält keine Tonspur')
  const stereo = header.channels === 2
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)

  // Gather the compressed data per channel first
  const parts: Uint8Array[][] = [[], []]
  let compressed = true
  let pos = 12
  while (pos + 8 <= bytes.length) {
    const id = ascii(bytes, pos)
    const length = view.getUint32(pos + 4, false)
    const data = bytes.subarray(pos + 8, pos + 8 + length)
    if (id === 'SND0' || id === 'SND2') {
      compressed = id === 'SND2'
      if (stereo) {
        // Each chunk holds the left half followed by the right half
        parts[0]!.push(data.subarray(0, length >> 1))
        parts[1]!.push(data.subarray(length >> 1, (length >> 1) * 2))
      }
      else {
        parts[0]!.push(data)
      }
    }
    // Sound chunks are top-level; frame chunks (VQFR, ...) are skipped as a whole
    pos += 8 + length
    if (pos & 1) pos++ // chunks are word aligned
  }
  if (!compressed) throw new Error('Unkomprimierter VQA-Ton wird nicht unterstützt')

  const channels = stereo ? 2 : 1
  const perChannel = parts[0]!.reduce((n, p) => n + p.length * 2, 0)
  const samples = new Int16Array(perChannel * channels)
  for (let c = 0; c < channels; c++) {
    const state: ImaAdpcmState = { index: 0, current: 0 }
    let offset = c
    for (const part of parts[c]!) {
      decodeImaAdpcm(part, state, samples, offset, channels)
      offset += part.length * 2 * channels
    }
  }
  return { sampleRate: header.sampleRate, channels: channels as 1 | 2, samples }
}
