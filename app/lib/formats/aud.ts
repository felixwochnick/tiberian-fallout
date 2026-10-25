/**
 * Westwood AUD decoder (IMA ADPCM variant used by Tiberian Sun music and speech).
 */

const INDEX_ADJUST = [-1, -1, -1, -1, 2, 4, 6, 8]
const STEP_TABLE = [
  7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88,
  97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658,
  724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660,
  4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818,
  18500, 20350, 22385, 24623, 27086, 29794, 32767,
]

const FORMAT_IMA_ADPCM = 99
const FORMAT_WESTWOOD = 1
const CHUNK_MAGIC = 0xdeaf
const HEADER_SIZE = 12

export interface AudHeader {
  sampleRate: number
  dataSize: number
  outputSize: number
  channels: 1 | 2
  sampleBits: 8 | 16
  format: number
}

export interface DecodedAudio {
  sampleRate: number
  channels: 1 | 2
  /** Interleaved 16-bit PCM */
  samples: Int16Array
}

export function readAudHeader(bytes: Uint8Array): AudHeader | undefined {
  if (bytes.length < HEADER_SIZE) return undefined
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  const flags = view.getUint8(10)
  const header: AudHeader = {
    sampleRate: view.getUint16(0, true),
    dataSize: view.getUint32(2, true),
    outputSize: view.getUint32(6, true),
    channels: flags & 1 ? 2 : 1,
    sampleBits: flags & 2 ? 16 : 8,
    format: view.getUint8(11),
  }
  return header
}

/** Cheap sniffing test, used to find music tracks whose filenames are unknown. */
export function looksLikeAud(bytes: Uint8Array, totalLength: number): boolean {
  const header = readAudHeader(bytes)
  if (!header) return false
  if (header.format !== FORMAT_IMA_ADPCM && header.format !== FORMAT_WESTWOOD) return false
  if (header.sampleRate < 4000 || header.sampleRate > 48000) return false
  if (header.dataSize + HEADER_SIZE !== totalLength) return false
  if (bytes.length >= HEADER_SIZE + 8) {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
    if (view.getUint32(HEADER_SIZE + 4, true) !== CHUNK_MAGIC) return false
  }
  return true
}

export interface ImaAdpcmState {
  index: number
  current: number
}

export function decodeImaNibble(nibble: number, state: ImaAdpcmState) {
  const step = STEP_TABLE[state.index]!
  const magnitude = nibble & 7
  let delta = ((step * magnitude) >> 2) + (step >> 3)
  if (nibble & 8) delta = -delta
  state.current = Math.max(-32768, Math.min(32767, state.current + delta))
  state.index = Math.max(0, Math.min(88, state.index + INDEX_ADJUST[magnitude]!))
  return state.current
}

/** Decodes Westwood IMA ADPCM (low nibble first), continuing from `state`. */
export function decodeImaAdpcm(bytes: Uint8Array, state: ImaAdpcmState, out: Int16Array, offset = 0, stride = 1) {
  let o = offset
  for (let i = 0; i < bytes.length; i++) {
    out[o] = decodeImaNibble(bytes[i]! & 0xf, state)
    o += stride
    out[o] = decodeImaNibble(bytes[i]! >> 4, state)
    o += stride
  }
}

export function decodeAud(bytes: Uint8Array): DecodedAudio {
  const header = readAudHeader(bytes)
  if (!header) throw new Error('Not an AUD file')
  if (header.format !== FORMAT_IMA_ADPCM) throw new Error(`Unsupported AUD format ${header.format}`)

  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  const samples = new Int16Array(header.outputSize >> 1)
  let out = 0
  const state: ImaAdpcmState = { index: 0, current: 0 }
  let pos = HEADER_SIZE
  const end = Math.min(bytes.length, HEADER_SIZE + header.dataSize)

  while (pos + 8 <= end && out < samples.length) {
    const compressedSize = view.getUint16(pos, true)
    if (view.getUint32(pos + 4, true) !== CHUNK_MAGIC) throw new Error('Corrupt AUD chunk header')
    pos += 8
    const chunkEnd = Math.min(pos + compressedSize, end)
    for (; pos < chunkEnd && out < samples.length; pos++) {
      const b = bytes[pos]!
      samples[out++] = decodeImaNibble(b & 0xf, state)
      if (out < samples.length) samples[out++] = decodeImaNibble(b >> 4, state)
    }
    pos = chunkEnd
  }

  return { sampleRate: header.sampleRate, channels: header.channels, samples: samples.subarray(0, out) }
}

export function toAudioBuffer(ctx: BaseAudioContext, audio: DecodedAudio): AudioBuffer {
  const frames = Math.floor(audio.samples.length / audio.channels)
  const buffer = ctx.createBuffer(audio.channels, Math.max(frames, 1), audio.sampleRate)
  for (let c = 0; c < audio.channels; c++) {
    const data = buffer.getChannelData(c)
    for (let i = 0; i < frames; i++) data[i] = audio.samples[i * audio.channels + c]! / 32768
  }
  return buffer
}
