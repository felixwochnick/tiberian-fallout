/**
 * Minimal ISO 9660 reader – enough to pull the game archives off the
 * Tiberian Sun CD images without loading the whole image into memory.
 */

const SECTOR = 2048

export interface IsoFile {
  path: string
  blob: Blob
}

interface DirRecord {
  name: string
  lba: number
  size: number
  isDir: boolean
}

function parseDirectory(bytes: Uint8Array): DirRecord[] {
  const records: DirRecord[] = []
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  let pos = 0
  while (pos < bytes.length) {
    const length = bytes[pos]!
    if (length === 0) {
      // Records never span sectors; skip padding to the next one
      pos = (Math.floor(pos / SECTOR) + 1) * SECTOR
      continue
    }
    const nameLength = bytes[pos + 32]!
    const rawName = String.fromCharCode(...bytes.subarray(pos + 33, pos + 33 + nameLength))
    if (nameLength !== 1 || (rawName !== '\0' && rawName !== '\x01')) {
      records.push({
        name: rawName.replace(/;\d+$/, '').replace(/\.$/, ''),
        lba: view.getUint32(pos + 2, true),
        size: view.getUint32(pos + 10, true),
        isDir: (bytes[pos + 25]! & 2) !== 0,
      })
    }
    pos += length
  }
  return records
}

export async function listIsoFiles(image: Blob, filter: (path: string) => boolean = () => true): Promise<IsoFile[]> {
  const pvd = new Uint8Array(await image.slice(16 * SECTOR, 17 * SECTOR).arrayBuffer())
  const magic = String.fromCharCode(...pvd.subarray(1, 6))
  if (pvd[0] !== 1 || magic !== 'CD001') throw new Error('Keine gültige ISO-9660-Datei')

  const view = new DataView(pvd.buffer)
  const root: DirRecord = { name: '', lba: view.getUint32(156 + 2, true), size: view.getUint32(156 + 10, true), isDir: true }

  const files: IsoFile[] = []
  const visited = new Set<number>()
  const walk = async (dir: DirRecord, prefix: string) => {
    if (visited.has(dir.lba)) return
    visited.add(dir.lba)
    const bytes = new Uint8Array(await image.slice(dir.lba * SECTOR, dir.lba * SECTOR + dir.size).arrayBuffer())
    for (const record of parseDirectory(bytes)) {
      const path = prefix ? `${prefix}/${record.name}` : record.name
      if (record.isDir) await walk(record, path)
      else if (filter(path)) files.push({ path, blob: image.slice(record.lba * SECTOR, record.lba * SECTOR + record.size) })
    }
  }
  await walk(root, '')
  return files
}

export interface IsoStreamFile {
  path: string
  size: number
}

export interface IsoFileSink {
  write(chunk: Uint8Array): Promise<void>
  close(): Promise<void>
  abort(): Promise<void>
}

/** Directories must appear within this many bytes at the start of the image. */
const MAX_DIRECTORY_PREFIX = 64 * 1024 * 1024

/**
 * Walks the directory tree inside `prefix`. Returns `undefined` when a
 * directory extent lies beyond the bytes received so far.
 */
function scanTree(prefix: Uint8Array, length: number) {
  if (length < 17 * SECTOR) return undefined
  const pvd = prefix.subarray(16 * SECTOR, 17 * SECTOR)
  if (pvd[0] !== 1 || String.fromCharCode(...pvd.subarray(1, 6)) !== 'CD001') {
    throw new Error('Keine gültige ISO-9660-Datei')
  }
  const view = new DataView(pvd.buffer, pvd.byteOffset, pvd.byteLength)
  const files: { path: string, start: number, size: number }[] = []
  const stack: [DirRecord, string][] = [[
    { name: '', lba: view.getUint32(156 + 2, true), size: view.getUint32(156 + 10, true), isDir: true },
    '',
  ]]
  const visited = new Set<number>()
  while (stack.length) {
    const [dir, prefixPath] = stack.pop()!
    if (visited.has(dir.lba)) continue
    visited.add(dir.lba)
    const end = dir.lba * SECTOR + dir.size
    if (end > length) return undefined
    for (const record of parseDirectory(prefix.subarray(dir.lba * SECTOR, end))) {
      const path = prefixPath ? `${prefixPath}/${record.name}` : record.name
      if (record.isDir) stack.push([record, path])
      else files.push({ path, start: record.lba * SECTOR, size: record.size })
    }
  }
  return files
}

/**
 * Extracts files from an ISO image that arrives as a sequential stream
 * (e.g. while it is being downloaded and decompressed). File contents are
 * passed to sinks as they stream by, so the image is never held in memory.
 */
export async function extractIsoStream(
  stream: ReadableStream<Uint8Array>,
  wanted: (path: string) => boolean,
  openSink: (file: IsoStreamFile) => Promise<IsoFileSink>,
): Promise<IsoStreamFile[]> {
  let prefix = new Uint8Array(4 * 1024 * 1024)
  let prefixLength = 0
  let targets: { path: string, start: number, size: number, written: number, sink?: IsoFileSink }[] | undefined
  let position = 0

  const feed = async (chunk: Uint8Array, offset: number) => {
    const chunkEnd = offset + chunk.length
    for (const target of targets!) {
      const from = Math.max(offset, target.start + target.written)
      const to = Math.min(chunkEnd, target.start + target.size)
      if (from >= to) continue
      target.sink ??= await openSink({ path: target.path, size: target.size })
      await target.sink.write(chunk.subarray(from - offset, to - offset))
      target.written += to - from
      if (target.written === target.size) await target.sink.close()
    }
  }

  const reader = stream.getReader()
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      if (!targets) {
        if (prefixLength + value.length > prefix.length) {
          if (prefix.length >= MAX_DIRECTORY_PREFIX) throw new Error('ISO-Verzeichnis nicht am Anfang des Images')
          const grown = new Uint8Array(Math.max(prefix.length * 2, prefixLength + value.length))
          grown.set(prefix.subarray(0, prefixLength))
          prefix = grown
        }
        prefix.set(value, prefixLength)
        prefixLength += value.length
        const files = scanTree(prefix, prefixLength)
        if (files) {
          targets = files.filter(f => wanted(f.path)).map(f => ({ ...f, written: 0 }))
          await feed(prefix.subarray(0, prefixLength), 0)
          position = prefixLength
          prefix = new Uint8Array(0)
        }
        continue
      }
      await feed(value, position)
      position += value.length
      if (targets.every(t => t.written === t.size)) {
        await reader.cancel()
        break
      }
    }
  }
  catch (error) {
    await Promise.all((targets ?? []).filter(t => t.sink && t.written < t.size).map(t => t.sink!.abort()))
    throw error
  }

  if (!targets) throw new Error('ISO-Image unvollständig')
  const missing = targets.filter(t => t.written < t.size)
  if (missing.length) {
    await Promise.all(missing.filter(t => t.sink).map(t => t.sink!.abort()))
    throw new Error(`Download unvollständig: ${missing.map(t => t.path).join(', ')}`)
  }
  return targets.map(t => ({ path: t.path, size: t.size }))
}
