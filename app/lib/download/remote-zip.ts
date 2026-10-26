/**
 * Streams an entry out of a ZIP file on a server while the archive comes in, front to
 * back in one plain download. There are no range requests: the mirror sits behind
 * Cloudflare, which answers them with the whole file (HTTP 200) whenever the archive is
 * not in its cache yet, so they cannot be relied on.
 */

export interface RemoteZipEntry {
  name: string
  method: number
  compressedSize: number
  size: number
}

const LOCAL_SIGNATURE = 0x04034b50
/** Bit 3 of the flags: sizes follow the data instead of standing in the header */
const DATA_DESCRIPTOR = 0x08

/** Reads a byte stream in pieces of exactly the requested length. */
class ByteReader {
  private buffer: Uint8Array = new Uint8Array(0)

  constructor(private readonly reader: ReadableStreamDefaultReader<Uint8Array>) {}

  /** Exactly `length` bytes, or fewer once the stream has ended */
  async read(length: number) {
    while (this.buffer.length < length) {
      const { done, value } = await this.reader.read()
      if (done) break
      const joined = new Uint8Array(this.buffer.length + value.length)
      joined.set(this.buffer)
      joined.set(value, this.buffer.length)
      this.buffer = joined
    }
    const bytes = this.buffer.subarray(0, length)
    this.buffer = this.buffer.subarray(bytes.length)
    return bytes
  }

  /** Up to `limit` bytes, as they come in (empty once the stream has ended) */
  async chunk(limit: number) {
    if (!this.buffer.length) {
      const { done, value } = await this.reader.read()
      if (done) return new Uint8Array(0)
      this.buffer = value
    }
    const bytes = this.buffer.subarray(0, limit)
    this.buffer = this.buffer.subarray(bytes.length)
    return bytes
  }

  cancel() {
    return this.reader.cancel().catch(() => {})
  }
}

/**
 * Downloads the ZIP at `url` and streams the uncompressed content of the first entry
 * that `wanted` accepts. Entries before it are skipped as they come in; when the stream
 * is cancelled or ends, so does the download. `onProgress` reports the number of bytes
 * received of the whole archive.
 */
export async function openRemoteZipEntry(
  url: string,
  wanted: (name: string) => boolean,
  onProgress?: (received: number) => void,
  signal?: AbortSignal,
): Promise<{ entry: RemoteZipEntry, stream: ReadableStream<Uint8Array> }> {
  const response = await fetch(url, { signal })
  if (!response.ok || !response.body) throw new Error(`Download fehlgeschlagen (HTTP ${response.status})`)

  let received = 0
  const reader = new ByteReader(response.body.pipeThrough(new TransformStream<Uint8Array, Uint8Array>({
    transform(chunk, controller) {
      received += chunk.byteLength
      onProgress?.(received)
      controller.enqueue(chunk)
    },
  })).getReader())

  try {
    for (;;) {
      const header = await reader.read(30)
      const view = new DataView(header.buffer, header.byteOffset, header.byteLength)
      if (header.length < 30 || view.getUint32(0, true) !== LOCAL_SIGNATURE) throw new Error('Kein passender Eintrag im ZIP-Archiv gefunden')
      const flags = view.getUint16(6, true)
      const name = new TextDecoder().decode(await reader.read(view.getUint16(26, true)))
      await reader.read(view.getUint16(28, true)) // extra field
      const entry: RemoteZipEntry = {
        name,
        method: view.getUint16(8, true),
        compressedSize: view.getUint32(18, true),
        size: view.getUint32(22, true),
      }
      if (flags & DATA_DESCRIPTOR || entry.compressedSize === 0xffffffff) throw new Error('Nicht unterstütztes ZIP-Format')

      if (!wanted(name)) {
        for (let left = entry.compressedSize; left > 0;) {
          const bytes = await reader.chunk(left)
          if (!bytes.length) throw new Error('Download unvollständig')
          left -= bytes.length
        }
        continue
      }

      let left = entry.compressedSize
      const data = new ReadableStream<Uint8Array>({
        async pull(controller) {
          if (!left) {
            controller.close()
            await reader.cancel()
            return
          }
          const bytes = await reader.chunk(left)
          if (!bytes.length) {
            controller.error(new Error('Download unvollständig'))
            return
          }
          left -= bytes.length
          controller.enqueue(bytes.slice())
        },
        cancel: () => reader.cancel(),
      })

      if (entry.method === 0) return { entry, stream: data }
      if (entry.method === 8) return { entry, stream: data.pipeThrough(new DecompressionStream('deflate-raw') as unknown as TransformStream<Uint8Array, Uint8Array>) }
      throw new Error(`Nicht unterstützte ZIP-Kompression (${entry.method})`)
    }
  }
  catch (e) {
    await reader.cancel()
    throw e
  }
}
