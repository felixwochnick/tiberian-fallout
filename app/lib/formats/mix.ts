import { Blowfish } from './blowfish'
import { hashFilenameClassic, hashFilenameCrc } from './hash'
import { decryptMixKey } from './westwood-key'

export interface MixEntry {
  hash: number
  /** Offset relative to the start of the MIX body */
  offset: number
  length: number
}

export interface MixIndex {
  entries: MixEntry[]
  /** Offset of the archive body; entry offsets are relative to it */
  dataStart: number
  encrypted: boolean
  /** TS/RA2 archives hash names with CRC32, TD/RA ones with the classic hash */
  crcHash: boolean
}

const ENTRY_SIZE = 12
const FLAG_ENCRYPTED = 0x2

async function readBytes(blob: Blob, start: number, length: number) {
  return new Uint8Array(await blob.slice(start, start + length).arrayBuffer())
}

function parseIndex(bytes: Uint8Array) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  const count = view.getUint16(0, true)
  const entries: MixEntry[] = []
  for (let i = 0; i < count; i++) {
    const o = 6 + i * ENTRY_SIZE
    entries.push({
      hash: view.getUint32(o, true),
      offset: view.getUint32(o + 4, true),
      length: view.getUint32(o + 8, true),
    })
  }
  return entries
}

export function hashMixFilename(filename: string, crcHash: boolean) {
  return crcHash ? hashFilenameCrc(filename) : hashFilenameClassic(filename)
}

/**
 * Reader for Westwood MIX archives (TD, RA, TS and RA2 variants, including
 * Blowfish-encrypted headers). Works on Blob slices, so large archives are
 * never loaded into memory as a whole.
 */
export class MixArchive {
  private readonly byHash = new Map<number, MixEntry>()

  private constructor(
    readonly name: string,
    private readonly blob: Blob,
    private readonly dataStart: number,
    readonly entries: MixEntry[],
    readonly encrypted: boolean,
    private readonly useCrcHash: boolean,
  ) {
    for (const entry of entries) this.byHash.set(entry.hash, entry)
  }

  /**
   * Parses the archive index. `read` returns bytes of the archive at the
   * given position, which allows parsing from a partial (streamed) header.
   */
  static async readIndex(read: (start: number, length: number) => Promise<Uint8Array>): Promise<MixIndex> {
    const head = await read(0, 4)
    if (head.length < 4) throw new Error('file too small')
    const view = new DataView(head.buffer, head.byteOffset, 4)

    if (view.getUint16(0, true) !== 0) {
      const count = view.getUint16(0, true)
      const index = await read(0, 6 + count * ENTRY_SIZE)
      return { entries: parseIndex(index), dataStart: 6 + count * ENTRY_SIZE, encrypted: false, crcHash: false }
    }

    const flags = view.getUint16(2, true)
    if (!(flags & FLAG_ENCRYPTED)) {
      const countBytes = await read(4, 2)
      const count = new DataView(countBytes.buffer, countBytes.byteOffset, 2).getUint16(0, true)
      const index = await read(4, 6 + count * ENTRY_SIZE)
      return { entries: parseIndex(index), dataStart: 4 + 6 + count * ENTRY_SIZE, encrypted: false, crcHash: true }
    }

    const fish = new Blowfish(decryptMixKey(await read(4, 80)))
    const first = fish.decrypt(await read(84, 8))
    const count = new DataView(first.buffer).getUint16(0, true)
    const blockCount = Math.floor((13 + count * ENTRY_SIZE) / 8)
    const index = fish.decrypt(await read(84, blockCount * 8))
    return { entries: parseIndex(index), dataStart: 84 + blockCount * 8, encrypted: true, crcHash: true }
  }

  static async open(blob: Blob, name = 'unknown.mix'): Promise<MixArchive> {
    const index = await MixArchive.readIndex((start, length) => readBytes(blob, start, length))
      .catch((error: Error) => {
        throw new Error(`${name}: ${error.message}`)
      })
    const archive = new MixArchive(name, blob, index.dataStart, index.entries, index.encrypted, index.crcHash)
    archive.validate()
    return archive
  }

  private validate() {
    const bodySize = this.blob.size - this.dataStart
    for (const entry of this.entries) {
      if (entry.offset + entry.length > bodySize) {
        throw new Error(`${this.name}: corrupt index (entry beyond end of file)`)
      }
    }
  }

  hash(filename: string) {
    return hashMixFilename(filename, this.useCrcHash)
  }

  has(filename: string) {
    return this.byHash.has(this.hash(filename))
  }

  entry(filename: string) {
    return this.byHash.get(this.hash(filename))
  }

  /** For files whose name is unknown. */
  entryByHash(hash: number) {
    return this.byHash.get(hash)
  }

  entryBlob(entry: MixEntry): Blob {
    const start = this.dataStart + entry.offset
    return this.blob.slice(start, start + entry.length)
  }

  async read(filenameOrEntry: string | MixEntry): Promise<Uint8Array | undefined> {
    const entry = typeof filenameOrEntry === 'string' ? this.entry(filenameOrEntry) : filenameOrEntry
    if (!entry) return undefined
    return new Uint8Array(await this.entryBlob(entry).arrayBuffer())
  }

  /** Opens a MIX inside this one, by filename or by hash if the name is unknown. */
  async openNested(filenameOrHash: string | number): Promise<MixArchive | undefined> {
    const entry = typeof filenameOrHash === 'string' ? this.entry(filenameOrHash) : this.entryByHash(filenameOrHash)
    if (!entry) return undefined
    const name = typeof filenameOrHash === 'string' ? filenameOrHash : `${filenameOrHash.toString(16)}.mix`
    return MixArchive.open(this.entryBlob(entry), name)
  }
}
