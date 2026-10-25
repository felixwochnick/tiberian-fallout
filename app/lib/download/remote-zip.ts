/**
 * Reads single entries from a ZIP file on a server that supports HTTP range
 * requests, without downloading the rest of the archive.
 */

export interface RemoteZipEntry {
  name: string
  method: number
  compressedSize: number
  size: number
  localHeaderOffset: number
}

const EOCD_SIGNATURE = 0x06054b50
const CENTRAL_SIGNATURE = 0x02014b50
const LOCAL_SIGNATURE = 0x04034b50

async function fetchRange(url: string, range: string, signal?: AbortSignal) {
  const response = await fetch(url, { headers: { range }, signal })
  if (response.status !== 206) throw new Error(`Server unterstützt keine Teil-Downloads (HTTP ${response.status})`)
  return new Uint8Array(await response.arrayBuffer())
}

export async function listRemoteZip(url: string, signal?: AbortSignal): Promise<RemoteZipEntry[]> {
  const tail = await fetchRange(url, 'bytes=-65558', signal)
  const view = new DataView(tail.buffer)

  let eocd = -1
  for (let i = tail.length - 22; i >= 0; i--) {
    if (view.getUint32(i, true) === EOCD_SIGNATURE) {
      eocd = i
      break
    }
  }
  if (eocd < 0) throw new Error('Ungültiges ZIP-Archiv')

  const count = view.getUint16(eocd + 10, true)
  const cdSize = view.getUint32(eocd + 12, true)
  const cdOffset = view.getUint32(eocd + 16, true)
  if (cdOffset === 0xffffffff) throw new Error('ZIP64-Archive werden nicht unterstützt')

  const cd = await fetchRange(url, `bytes=${cdOffset}-${cdOffset + cdSize - 1}`, signal)
  const cdView = new DataView(cd.buffer)
  const entries: RemoteZipEntry[] = []
  let pos = 0
  for (let i = 0; i < count; i++) {
    if (cdView.getUint32(pos, true) !== CENTRAL_SIGNATURE) throw new Error('Beschädigtes ZIP-Inhaltsverzeichnis')
    const nameLength = cdView.getUint16(pos + 28, true)
    const extraLength = cdView.getUint16(pos + 30, true)
    const commentLength = cdView.getUint16(pos + 32, true)
    entries.push({
      method: cdView.getUint16(pos + 10, true),
      compressedSize: cdView.getUint32(pos + 20, true),
      size: cdView.getUint32(pos + 24, true),
      localHeaderOffset: cdView.getUint32(pos + 42, true),
      name: new TextDecoder().decode(cd.subarray(pos + 46, pos + 46 + nameLength)),
    })
    pos += 46 + nameLength + extraLength + commentLength
  }
  return entries
}

/**
 * Streams the uncompressed content of a ZIP entry.
 * `onProgress` reports the number of compressed bytes received.
 */
export async function openRemoteZipEntry(
  url: string,
  entry: RemoteZipEntry,
  onProgress?: (received: number) => void,
  signal?: AbortSignal,
): Promise<ReadableStream<Uint8Array>> {
  const header = await fetchRange(url, `bytes=${entry.localHeaderOffset}-${entry.localHeaderOffset + 29}`, signal)
  const view = new DataView(header.buffer)
  if (view.getUint32(0, true) !== LOCAL_SIGNATURE) throw new Error('Beschädigter ZIP-Eintrag')
  const dataStart = entry.localHeaderOffset + 30 + view.getUint16(26, true) + view.getUint16(28, true)

  const response = await fetch(url, {
    headers: { range: `bytes=${dataStart}-${dataStart + entry.compressedSize - 1}` },
    signal,
  })
  if (response.status !== 206 || !response.body) throw new Error(`Download fehlgeschlagen (HTTP ${response.status})`)

  let received = 0
  const counted = response.body.pipeThrough(new TransformStream<Uint8Array, Uint8Array>({
    transform(chunk, controller) {
      received += chunk.byteLength
      onProgress?.(received)
      controller.enqueue(chunk)
    },
  }))

  if (entry.method === 0) return counted
  if (entry.method === 8) return counted.pipeThrough(new DecompressionStream('deflate-raw') as unknown as TransformStream<Uint8Array, Uint8Array>)
  throw new Error(`Nicht unterstützte ZIP-Kompression (${entry.method})`)
}
