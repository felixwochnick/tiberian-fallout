/**
 * Persists the imported original game files in the browser's
 * Origin Private File System (OPFS). Falls back to an in-memory store
 * when OPFS is not available (e.g. private windows).
 */

const DIR_NAME = 'tiberian-sun'

export interface StoredFile {
  name: string
  size: number
}

export interface FileWriter {
  write(chunk: Uint8Array): Promise<void>
  close(): Promise<void>
  abort(): Promise<void>
}

export interface AssetStore {
  readonly persistent: boolean
  list(): Promise<StoredFile[]>
  get(name: string): Promise<File | undefined>
  put(name: string, data: Blob, onProgress?: (written: number) => void): Promise<void>
  /** Streams a file into the store; it only becomes visible after `close()`. */
  createWriter(name: string): Promise<FileWriter>
  clear(): Promise<void>
}

class MemoryStore implements AssetStore {
  readonly persistent = false
  private files = new Map<string, File>()

  async list() {
    return [...this.files.values()].map(f => ({ name: f.name, size: f.size }))
  }

  async get(name: string) {
    return this.files.get(name.toUpperCase())
  }

  async put(name: string, data: Blob) {
    const key = name.toUpperCase()
    this.files.set(key, new File([data], key))
  }

  async createWriter(name: string): Promise<FileWriter> {
    const parts: Uint8Array[] = []
    return {
      write: async (chunk) => {
        parts.push(chunk.slice())
      },
      close: async () => this.put(name, new Blob(parts as BlobPart[])),
      abort: async () => {
        parts.length = 0
      },
    }
  }

  async clear() {
    this.files.clear()
  }
}

class OpfsStore implements AssetStore {
  readonly persistent = true

  constructor(private readonly dir: FileSystemDirectoryHandle) {}

  async list() {
    const files: StoredFile[] = []
    // @ts-expect-error -- async iteration of directory handles is not yet in all TS DOM libs
    for await (const handle of this.dir.values() as AsyncIterable<FileSystemHandle>) {
      if (handle.kind !== 'file') continue
      const file = await (handle as FileSystemFileHandle).getFile()
      files.push({ name: handle.name, size: file.size })
    }
    return files.sort((a, b) => a.name.localeCompare(b.name))
  }

  async get(name: string) {
    try {
      const handle = await this.dir.getFileHandle(name.toUpperCase())
      return await handle.getFile()
    }
    catch {
      return undefined
    }
  }

  async put(name: string, data: Blob, onProgress?: (written: number) => void) {
    const handle = await this.dir.getFileHandle(name.toUpperCase(), { create: true })
    const writable = await handle.createWritable()
    try {
      const chunkSize = 8 * 1024 * 1024
      for (let offset = 0; offset < data.size; offset += chunkSize) {
        await writable.write(data.slice(offset, offset + chunkSize))
        onProgress?.(Math.min(offset + chunkSize, data.size))
      }
      await writable.close()
    }
    catch (error) {
      await writable.abort().catch(() => {})
      throw error
    }
  }

  async createWriter(name: string): Promise<FileWriter> {
    const key = name.toUpperCase()
    const existed = await this.dir.getFileHandle(key).then(() => true, () => false)
    const handle = await this.dir.getFileHandle(key, { create: true })
    // Writes go to a swap file; the previous content stays intact until close()
    const writable = await handle.createWritable()
    return {
      write: chunk => writable.write(chunk as BufferSource),
      close: () => writable.close(),
      abort: async () => {
        await writable.abort().catch(() => {})
        if (!existed) await this.dir.removeEntry(key).catch(() => {})
      },
    }
  }

  async clear() {
    for (const file of await this.list()) await this.dir.removeEntry(file.name)
  }
}

let store: Promise<AssetStore> | undefined

export function getAssetStore(): Promise<AssetStore> {
  store ??= (async () => {
    try {
      const root = await navigator.storage.getDirectory()
      const dir = await root.getDirectoryHandle(DIR_NAME, { create: true })
      const probe = await dir.getFileHandle('.probe', { create: true })
      if (typeof probe.createWritable !== 'function') throw new Error('createWritable unsupported')
      await dir.removeEntry('.probe')
      await navigator.storage.persist?.().catch(() => false)
      return new OpfsStore(dir)
    }
    catch {
      return new MemoryStore()
    }
  })()
  return store
}
