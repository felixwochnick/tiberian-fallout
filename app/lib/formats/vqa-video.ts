import { readVqaHeader, type VqaHeader } from './vqa'

/**
 * Westwood VQA video frames (after FFmpeg's vqavideo.c). Each frame is a grid of
 * blocks (4 × 2 or 4 × 4 pixels) looked up in a codebook of vectors:
 *
 * - Palette videos (VQA 2): an 8 bit codebook and palette (CBF*, CBP*, CPL0, VPTZ).
 * - High colour videos (VQA 3, Tiberian Sun): a codebook of RGB555 vectors, updated by
 *   VQFL chunks before a frame, and a per-row RLE of vector indices (VPTR / VPRZ).
 *
 * The *Z chunks are compressed with Westwood's LCW ("format 80").
 */

const tag = (bytes: Uint8Array, at: number) => String.fromCharCode(bytes[at]!, bytes[at + 1]!, bytes[at + 2]!, bytes[at + 3]!)
const be32 = (bytes: Uint8Array, at: number) => ((bytes[at]! << 24) | (bytes[at + 1]! << 16) | (bytes[at + 2]! << 8) | bytes[at + 3]!) >>> 0

const MAX_CODEBOOK_SIZE = 0x100000
const MAX_VECTORS = 0x4000

/** LCW / "format 80" decompression into `dest`; returns the number of bytes written. */
export function decodeFormat80(src: Uint8Array, dest: Uint8Array) {
  let s = 0
  let d = 0
  // the "new" scheme makes copies relative to the destination
  let relative = false
  if (src[0] === 0) {
    relative = true
    s = 1
  }
  const copy = (from: number, count: number) => {
    if (from < 0 || from + count > dest.length || d + count > dest.length) throw new Error('LCW: Kopie außerhalb des Puffers')
    for (let i = 0; i < count; i++) dest[d + i] = dest[from + i]!
    d += count
  }
  while (s < src.length) {
    const op = src[s++]!
    if (op === 0x80) break
    if (op === 0xFF) {
      const count = src[s]! | (src[s + 1]! << 8)
      let from = src[s + 2]! | (src[s + 3]! << 8)
      s += 4
      if (relative) from = d - from
      copy(from, count)
    }
    else if (op === 0xFE) {
      const count = src[s]! | (src[s + 1]! << 8)
      const value = src[s + 2]!
      s += 3
      dest.fill(value, d, Math.min(dest.length, d + count))
      d += count
    }
    else if ((op & 0xC0) === 0xC0) {
      const count = (op & 0x3F) + 3
      let from = src[s]! | (src[s + 1]! << 8)
      s += 2
      if (relative) from = d - from
      copy(from, count)
    }
    else if (op > 0x80) {
      const count = op & 0x3F
      dest.set(src.subarray(s, s + count), d)
      s += count
      d += count
    }
    else {
      const count = ((op & 0x70) >> 4) + 3
      const back = src[s++]! | ((op & 0x0F) << 8)
      copy(d - back, count)
    }
  }
  return d
}

export class VqaVideo {
  readonly header: VqaHeader
  readonly hicolor: boolean
  /** Byte offsets of the VQFR chunks in the file, one per frame */
  private readonly frames: number[] = []
  /** For each frame: VQFL chunks (codebook updates) that come before it */
  private readonly loose = new Map<number, number[]>()
  private readonly vectorWidth: number
  private readonly vectorHeight: number
  private codebook = new Uint8Array(MAX_CODEBOOK_SIZE)
  private nextCodebook = new Uint8Array(MAX_CODEBOOK_SIZE)
  private nextCodebookSize = 0
  private partialCountdown: number
  private readonly partialCount: number
  private readonly decodeBuffer: Uint8Array
  private readonly palette = new Uint8Array(256 * 3)
  /** The frame as 8 bit indices (palette) or RGB555 (high colour) */
  private readonly indexed: Uint8Array
  private readonly rgb555: Uint16Array
  /** The current picture as RGBA */
  readonly rgba: Uint8ClampedArray<ArrayBuffer>
  private next = 0

  constructor(private readonly bytes: Uint8Array) {
    this.header = readVqaHeader(bytes)
    const h = 20
    this.vectorWidth = bytes[h + 10]!
    this.vectorHeight = bytes[h + 11]!
    this.partialCount = this.partialCountdown = bytes[h + 13]!
    const colours = bytes[h + 14]! | (bytes[h + 15]! << 8)
    this.hicolor = colours === 0
    const { width, height } = this.header
    this.decodeBuffer = new Uint8Array((width / this.vectorWidth) * (height / this.vectorHeight) * 2)
    this.indexed = new Uint8Array(width * height)
    this.rgb555 = new Uint16Array(width * height)
    this.rgba = new Uint8ClampedArray(width * height * 4)

    // solid colour vectors at the end of the 8 bit codebook
    const size = this.vectorWidth * this.vectorHeight
    let at = (this.vectorHeight === 4 ? 0xFF00 : 0xF00) * size
    for (let i = 0; i < 256; i++) {
      this.codebook.fill(i, at, at + size)
      at += size
    }

    // index the chunks after the header
    let pos = 12
    let pendingLoose: number[] = []
    while (pos + 8 <= bytes.length) {
      const type = tag(bytes, pos)
      const size = be32(bytes, pos + 4)
      if (type === 'VQFR') {
        if (pendingLoose.length) this.loose.set(this.frames.length, pendingLoose)
        pendingLoose = []
        this.frames.push(pos)
      }
      else if (type === 'VQFL') {
        pendingLoose.push(pos)
      }
      pos += 8 + size + (size & 1)
    }
  }

  get frameCount() {
    return this.frames.length
  }

  /** Back to the first frame */
  rewind() {
    this.next = 0
    this.partialCountdown = this.partialCount
    this.nextCodebookSize = 0
  }

  /** Decodes the next frame into `rgba`; false at the end. */
  decodeNext() {
    if (this.next >= this.frames.length) return false
    const index = this.next++
    for (const at of this.loose.get(index) ?? []) this.decodeChunks(at, true)
    this.decodeChunks(this.frames[index]!, false)
    return true
  }

  /** The sub-chunks of a VQFR (frame) or VQFL (codebook update) chunk */
  private decodeChunks(at: number, codebookOnly: boolean) {
    const bytes = this.bytes
    const end = at + 8 + be32(bytes, at + 4)
    const chunks = new Map<string, Uint8Array>()
    let pos = at + 8
    while (pos + 8 <= end) {
      const type = tag(bytes, pos)
      const size = be32(bytes, pos + 4)
      chunks.set(type, bytes.subarray(pos + 8, pos + 8 + size))
      pos += 8 + size + (size & 1)
    }
    const cbfz = chunks.get('CBFZ')
    const cbf0 = chunks.get('CBF0')
    if (cbfz) decodeFormat80(cbfz, this.codebook)
    if (cbf0) this.codebook.set(cbf0.subarray(0, MAX_CODEBOOK_SIZE))
    if (codebookOnly) return
    if (this.hicolor) this.drawHicolor(chunks)
    else this.drawPalette(chunks)
  }

  private drawHicolor(chunks: Map<string, Uint8Array>) {
    const { width, height } = this.header
    const vh = this.vectorHeight
    const vptr = chunks.get('VPTR')
    const vprz = chunks.get('VPRZ')
    if (vptr) this.decodeBuffer.set(vptr.subarray(0, this.decodeBuffer.length))
    else if (vprz) decodeFormat80(vprz, this.decodeBuffer)
    else return

    const buf = this.decodeBuffer
    const book = this.codebook
    const out = this.rgb555
    let p = 0
    const vectorBytes = 4 * vh * 2
    for (let y = 0; y < height; y += vh) {
      let x = 0
      while (x < width) {
        if (p + 2 > buf.length) return
        let code = buf[p]! | (buf[p + 1]! << 8)
        p += 2
        const type = code >> 13
        code &= 0x1FFF
        let vector = 0
        let count = 0
        if (type === 0) {
          x += 4 * code // skip: the blocks stay as they are
          continue
        }
        else if (type < 3) {
          vector = code & 0xFF
          count = ((code & 0x1F00) >> 7) + 1 + type
        }
        else if (type < 5) {
          vector = code
          count = 1
        }
        else if (type < 7) {
          vector = code
          count = buf[p++]!
        }
        else {
          return
        }
        while (count-- > 0 && x < width) {
          if (vector >= MAX_VECTORS) return
          let src = vector * vectorBytes
          for (let row = 0; row < vh; row++) {
            const o = (y + row) * width + x
            for (let col = 0; col < 4; col++) {
              out[o + col] = book[src]! | (book[src + 1]! << 8)
              src += 2
            }
          }
          // type 2: each further block reads its own vector index
          if (type === 2 && count > 0) vector = buf[p++]!
          x += 4
        }
      }
    }
    // RGB555 to RGBA
    const rgba = this.rgba
    for (let i = 0; i < out.length; i++) {
      const c = out[i]!
      const r = (c >> 10) & 31
      const g = (c >> 5) & 31
      const b = c & 31
      rgba[i * 4] = (r << 3) | (r >> 2)
      rgba[i * 4 + 1] = (g << 3) | (g >> 2)
      rgba[i * 4 + 2] = (b << 3) | (b >> 2)
      rgba[i * 4 + 3] = 255
    }
  }

  private drawPalette(chunks: Map<string, Uint8Array>) {
    const { width, height } = this.header
    const vh = this.vectorHeight
    const cpl = chunks.get('CPL0')
    if (cpl) {
      for (let i = 0; i < Math.min(768, cpl.length); i++) this.palette[i] = (cpl[i]! * 4) | ((cpl[i]! * 4) >> 6)
    }
    const vptz = chunks.get('VPTZ')
    if (vptz) {
      decodeFormat80(vptz, this.decodeBuffer)
      const shift = vh === 4 ? 4 : 3
      const half = this.decodeBuffer.length / 2
      let lo = 0
      for (let y = 0; y < height; y += vh) {
        for (let x = 0; x < width; x += 4, lo++) {
          let vector = ((this.decodeBuffer[half + lo]! << 8) | this.decodeBuffer[lo]!) << shift
          for (let row = 0; row < vh; row++) {
            const o = (y + row) * width + x
            for (let col = 0; col < 4; col++) this.indexed[o + col] = this.codebook[vector++]!
          }
        }
      }
    }
    // partial codebooks: collected over several frames, then swapped in
    const cbp = chunks.get('CBP0') ?? chunks.get('CBPZ')
    if (cbp) {
      this.nextCodebook.set(cbp, this.nextCodebookSize)
      this.nextCodebookSize += cbp.length
      if (--this.partialCountdown <= 0) {
        const collected = this.nextCodebook.subarray(0, this.nextCodebookSize)
        if (chunks.has('CBPZ')) decodeFormat80(collected, this.codebook)
        else this.codebook.set(collected)
        this.nextCodebookSize = 0
        this.partialCountdown = this.partialCount
      }
    }
    const rgba = this.rgba
    const pal = this.palette
    for (let i = 0; i < this.indexed.length; i++) {
      const c = this.indexed[i]! * 3
      rgba[i * 4] = pal[c]!
      rgba[i * 4 + 1] = pal[c + 1]!
      rgba[i * 4 + 2] = pal[c + 2]!
      rgba[i * 4 + 3] = 255
    }
  }
}
