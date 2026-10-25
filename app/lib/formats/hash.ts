const CRC_TABLE = (() => {
  const table = new Uint32Array(256)
  for (let n = 0; n < 256; n++) {
    let c = n
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    table[n] = c >>> 0
  }
  return table
})()

export function crc32(data: Uint8Array): number {
  let crc = 0xffffffff
  for (let i = 0; i < data.length; i++) crc = CRC_TABLE[(crc ^ data[i]!) & 0xff]! ^ (crc >>> 8)
  return (crc ^ 0xffffffff) >>> 0
}

/** Filename hash used by Tiberian Sun / Red Alert 2 MIX archives. */
export function hashFilenameCrc(name: string): number {
  const upper = name.toUpperCase()
  const bytes: number[] = Array.from(upper, c => c.charCodeAt(0) & 0xff)
  const length = bytes.length
  const roundedDown = length & ~3
  if (length !== roundedDown) {
    bytes.push(length - roundedDown)
    const padding = 4 - (length % 4)
    for (let p = 1; p < padding; p++) bytes.push(bytes[roundedDown]!)
  }
  return crc32(Uint8Array.from(bytes))
}

/** Filename hash used by Tiberian Dawn / Red Alert MIX archives. */
export function hashFilenameClassic(name: string): number {
  const bytes = Array.from(name.toUpperCase(), c => c.charCodeAt(0) & 0xff)
  while (bytes.length % 4) bytes.push(0)
  let result = 0
  for (let i = 0; i < bytes.length; i += 4) {
    const word = (bytes[i]! | (bytes[i + 1]! << 8) | (bytes[i + 2]! << 16) | (bytes[i + 3]! << 24)) >>> 0
    result = ((((result << 1) | (result >>> 31)) >>> 0) + word) >>> 0
  }
  return result
}
