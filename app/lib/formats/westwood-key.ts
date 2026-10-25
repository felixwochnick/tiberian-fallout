/**
 * Recovers the Blowfish key of an encrypted RA/TS MIX header.
 *
 * The 80-byte key source is RSA-"signed" with Westwood's private key; applying
 * the public key (e = 65537) to each 40-byte little-endian block yields 39
 * bytes of key material. The first 56 bytes form the Blowfish key.
 */
const PUBLIC_KEY_BASE64 = 'AihRvNoIbTn85FZRYNZRcT+i6KpU+maCsEqr3Q5q+LDB5tH7Tz2qQ38V'
const PUBLIC_EXPONENT = 0x10001n

function decodeModulus(): bigint {
  const der = Uint8Array.from(atob(PUBLIC_KEY_BASE64), c => c.charCodeAt(0))
  // DER INTEGER: 0x02, length, big-endian value
  if (der[0] !== 2) throw new Error('Invalid Westwood public key')
  const length = der[1]!
  let n = 0n
  for (let i = 0; i < length; i++) n = (n << 8n) | BigInt(der[2 + i]!)
  return n
}

function bitLength(n: bigint) {
  return n.toString(2).length
}

function modPow(base: bigint, exp: bigint, mod: bigint): bigint {
  let result = 1n
  base %= mod
  while (exp > 0n) {
    if (exp & 1n) result = (result * base) % mod
    base = (base * base) % mod
    exp >>= 1n
  }
  return result
}

function readLE(bytes: Uint8Array): bigint {
  let n = 0n
  for (let i = bytes.length - 1; i >= 0; i--) n = (n << 8n) | BigInt(bytes[i]!)
  return n
}

function writeLE(n: bigint, out: Uint8Array, offset: number, length: number) {
  for (let i = 0; i < length; i++) {
    out[offset + i] = Number(n & 0xffn)
    n >>= 8n
  }
}

let modulus: bigint | undefined

export function decryptMixKey(keySource: Uint8Array): Uint8Array {
  modulus ??= decodeModulus()
  const outBlock = Math.floor((bitLength(modulus) - 2) / 8) // 39 for the 320-bit key
  const inBlock = outBlock + 1
  const dest = new Uint8Array(Math.ceil(keySource.length / inBlock) * outBlock)

  for (let src = 0, dst = 0; src + inBlock <= keySource.length; src += inBlock, dst += outBlock) {
    const m = readLE(keySource.subarray(src, src + inBlock))
    writeLE(modPow(m, PUBLIC_EXPONENT, modulus), dest, dst, outBlock)
  }
  return dest.slice(0, 56)
}
