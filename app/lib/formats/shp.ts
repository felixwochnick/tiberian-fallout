/**
 * Tiberian Sun SHP sprites: a set of palette-indexed frames of equal canvas size.
 * Each frame stores only its non-empty rectangle, either raw or with runs of
 * transparent pixels (index 0) compressed.
 */

export interface ShpFrame {
  /** Palette indices for the full canvas (width × height), 0 = transparent */
  pixels: Uint8Array
}

export interface Shp {
  width: number
  height: number
  frames: ShpFrame[]
}

const FRAME_HEADER = 24

export function decodeShp(bytes: Uint8Array): Shp {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  if (view.getUint16(0, true) !== 0) throw new Error('Keine Tiberian-Sun-SHP-Datei')
  const width = view.getUint16(2, true)
  const height = view.getUint16(4, true)
  const count = view.getUint16(6, true)
  const frames: ShpFrame[] = []
  for (let f = 0; f < count; f++) {
    const h = 8 + f * FRAME_HEADER
    const x = view.getUint16(h, true)
    const y = view.getUint16(h + 2, true)
    const w = view.getUint16(h + 4, true)
    const rows = view.getUint16(h + 6, true)
    const format = view.getUint8(h + 8)
    let offset = view.getUint32(h + 20, true)
    const pixels = new Uint8Array(width * height)
    frames.push({ pixels })
    if (!w || !rows || !offset) continue // empty frame

    for (let row = 0; row < rows; row++) {
      const target = (y + row) * width + x
      if (format === 3) {
        // length-prefixed scanline; 0 is followed by a count of transparent pixels
        const end = offset + view.getUint16(offset, true)
        let pos = offset + 2
        let col = 0
        while (pos < end && col < w) {
          const value = bytes[pos++]!
          if (value === 0) col += bytes[pos++]!
          else pixels[target + col++] = value
        }
        offset = end
      }
      else {
        // format 2: length-prefixed raw scanline, otherwise raw rows of the frame width
        const length = format === 2 ? view.getUint16(offset, true) - 2 : w
        if (format === 2) offset += 2
        pixels.set(bytes.subarray(offset, offset + Math.min(length, w)), target)
        offset += length
      }
    }
  }
  return { width, height, frames }
}

/** Westwood palette: 256 RGB entries with 6 bit per channel. */
export function decodePalette(bytes: Uint8Array) {
  const rgb = new Uint8Array(768)
  for (let i = 0; i < 768; i++) rgb[i] = Math.round((bytes[i]! & 63) * 255 / 63)
  return rgb
}

/** RGBA image of a frame, with palette index 0 transparent. */
export function frameToRgba(shp: Shp, frame: ShpFrame, palette: Uint8Array) {
  const rgba = new Uint8ClampedArray(shp.width * shp.height * 4)
  frame.pixels.forEach((index, i) => {
    if (!index) return
    rgba[i * 4] = palette[index * 3]!
    rgba[i * 4 + 1] = palette[index * 3 + 1]!
    rgba[i * 4 + 2] = palette[index * 3 + 2]!
    rgba[i * 4 + 3] = 255
  })
  return rgba
}
