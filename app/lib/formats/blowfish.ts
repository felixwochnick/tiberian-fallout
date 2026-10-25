import { BLOWFISH_P, BLOWFISH_S } from './blowfish-tables'

/**
 * Standard Blowfish (ECB). Westwood uses the plain algorithm on raw bytes,
 * so each 8-byte block is read as two big-endian 32-bit words.
 */
export class Blowfish {
  private readonly p: Uint32Array
  private readonly s: Uint32Array

  constructor(key: Uint8Array) {
    this.p = Uint32Array.from(BLOWFISH_P)
    this.s = Uint32Array.from(BLOWFISH_S)

    for (let i = 0, j = 0; i < 18; i++) {
      let word = 0
      for (let k = 0; k < 4; k++) word = (word << 8) | key[j++ % key.length]!
      this.p[i]! ^= word >>> 0
    }

    const block = new Uint32Array(2)
    for (let i = 0; i < 18; i += 2) {
      this.encryptBlock(block)
      this.p[i] = block[0]!
      this.p[i + 1] = block[1]!
    }
    for (let i = 0; i < 1024; i += 2) {
      this.encryptBlock(block)
      this.s[i] = block[0]!
      this.s[i + 1] = block[1]!
    }
  }

  private f(x: number): number {
    const s = this.s
    const a = s[x >>> 24]!
    const b = s[256 + ((x >>> 16) & 0xff)]!
    const c = s[512 + ((x >>> 8) & 0xff)]!
    const d = s[768 + (x & 0xff)]!
    return ((((a + b) >>> 0) ^ c) + d) >>> 0
  }

  encryptBlock(block: Uint32Array) {
    let l = block[0]!
    let r = block[1]!
    for (let i = 0; i < 16; i++) {
      l = (l ^ this.p[i]!) >>> 0
      r = (r ^ this.f(l)) >>> 0
      ;[l, r] = [r, l]
    }
    ;[l, r] = [r, l]
    block[0] = (l ^ this.p[17]!) >>> 0
    block[1] = (r ^ this.p[16]!) >>> 0
  }

  decryptBlock(block: Uint32Array) {
    let l = block[0]!
    let r = block[1]!
    for (let i = 17; i > 1; i--) {
      l = (l ^ this.p[i]!) >>> 0
      r = (r ^ this.f(l)) >>> 0
      ;[l, r] = [r, l]
    }
    ;[l, r] = [r, l]
    block[0] = (l ^ this.p[0]!) >>> 0
    block[1] = (r ^ this.p[1]!) >>> 0
  }

  /** Decrypts whole 8-byte blocks of `data` (trailing partial block is ignored). */
  decrypt(data: Uint8Array): Uint8Array {
    const out = new Uint8Array(data.length - (data.length % 8))
    const view = new DataView(data.buffer, data.byteOffset, data.byteLength)
    const outView = new DataView(out.buffer)
    const block = new Uint32Array(2)
    for (let o = 0; o < out.length; o += 8) {
      block[0] = view.getUint32(o)
      block[1] = view.getUint32(o + 4)
      this.decryptBlock(block)
      outView.setUint32(o, block[0]!)
      outView.setUint32(o + 4, block[1]!)
    }
    return out
  }
}
