import type { IsoFileSink } from '../formats/iso9660'
import { hashMixFilename, MixArchive, type MixIndex } from '../formats/mix'
import type { FileWriter } from '../storage/asset-store'

class NeedMoreData extends Error {}

interface Target {
  name: string
  start: number
  end: number
  written: number
  writer?: FileWriter
}

/**
 * Receives a MIX archive as a sequential stream and writes only the
 * requested entries to storage, e.g. one short video out of the 470 MB
 * cutscene archive.
 */
export class MixEntrySink implements IsoFileSink {
  private header = new Uint8Array(0)
  private position = 0
  private targets: Target[] | undefined

  constructor(
    private readonly entryNames: string[],
    private readonly openWriter: (name: string) => Promise<FileWriter>,
  ) {}

  private async tryParseIndex(): Promise<MixIndex | undefined> {
    const read = async (start: number, length: number) => {
      if (start + length > this.header.length) throw new NeedMoreData()
      return this.header.slice(start, start + length)
    }
    try {
      return await MixArchive.readIndex(read)
    }
    catch (error) {
      if (error instanceof NeedMoreData) return undefined
      throw error
    }
  }

  async write(chunk: Uint8Array) {
    const offset = this.position
    this.position += chunk.length

    if (!this.targets) {
      const grown = new Uint8Array(this.header.length + chunk.length)
      grown.set(this.header)
      grown.set(chunk, this.header.length)
      this.header = grown
      const index = await this.tryParseIndex()
      if (!index) return

      this.targets = this.entryNames.map((name) => {
        const entry = index.entries.find(e => e.hash === hashMixFilename(name, index.crcHash))
        if (!entry) throw new Error(`${name} fehlt im Archiv`)
        const start = index.dataStart + entry.offset
        return { name, start, end: start + entry.length, written: 0 }
      })
      const buffered = this.header
      this.header = new Uint8Array(0)
      await this.feed(buffered, 0)
      return
    }
    await this.feed(chunk, offset)
  }

  private async feed(chunk: Uint8Array, offset: number) {
    for (const target of this.targets!) {
      const from = Math.max(offset, target.start + target.written)
      const to = Math.min(offset + chunk.length, target.end)
      if (from >= to) continue
      target.writer ??= await this.openWriter(target.name)
      await target.writer.write(chunk.subarray(from - offset, to - offset))
      target.written += to - from
      if (target.start + target.written === target.end) await target.writer.close()
    }
  }

  async close() {
    const missing = (this.targets ?? []).filter(t => t.start + t.written < t.end)
    if (!this.targets || missing.length) {
      await this.abort()
      throw new Error(`Unvollständig: ${(missing.length ? missing.map(t => t.name) : this.entryNames).join(', ')}`)
    }
  }

  async abort() {
    await Promise.all((this.targets ?? [])
      .filter(t => t.writer && t.start + t.written < t.end)
      .map(t => t.writer!.abort()))
  }
}
