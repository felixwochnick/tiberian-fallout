import { MixArchive } from '../formats/mix'
import { decodePalette, decodeShp, frameToRgba } from '../formats/shp'
import type { AssetStore } from '../storage/asset-store'

/**
 * The signs over buildings, as in Tiberian Sun (CACHE.MIX, in the mouse palette): the
 * wrench over one being repaired (WRENCH.SHP) and the crossed-out lightning bolt over
 * one switched off (POWEROFF.SHP). Each is a short animation that runs round and round.
 */
export type SignKind = 'repair' | 'power'

export type SignFrames = Record<SignKind, HTMLCanvasElement[]>

const FILES: Record<SignKind, string> = { repair: 'WRENCH.SHP', power: 'POWEROFF.SHP' }

/** Frames per second of the signs */
export const SIGN_FPS = 8

export async function loadSigns(store: AssetStore): Promise<SignFrames | undefined> {
  const tibsun = await store.get('TIBSUN.MIX')
  if (!tibsun) return undefined
  const cache = await (await MixArchive.open(tibsun, 'TIBSUN.MIX')).openNested('CACHE.MIX')
  const palBytes = await cache?.read('MOUSEPAL.PAL')
  if (!cache || !palBytes) return undefined
  const palette = decodePalette(palBytes)
  const signs: Partial<SignFrames> = {}
  for (const [kind, file] of Object.entries(FILES) as [SignKind, string][]) {
    const bytes = await cache.read(file)
    if (!bytes) return undefined
    const shp = decodeShp(bytes)
    // whole frames, so the sign stays in place while it changes
    signs[kind] = shp.frames.map((frame) => {
      const canvas = document.createElement('canvas')
      canvas.width = shp.width
      canvas.height = shp.height
      canvas.getContext('2d')!.putImageData(new ImageData(frameToRgba(shp, frame, palette), shp.width, shp.height), 0, 0)
      return canvas
    })
  }
  return signs as SignFrames
}
