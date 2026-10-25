import * as THREE from 'three'

/** Small deterministic PRNG so textures look the same on every visit. */
function random(seed: number) {
  let s = seed >>> 0
  return () => {
    s = (s + 0x6d2b79f5) >>> 0
    let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function canvasTexture(size: number, draw: (ctx: CanvasRenderingContext2D, rnd: () => number) => void, seed = 1) {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const ctx = canvas.getContext('2d')!
  draw(ctx, random(seed))
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 8
  return texture
}

/** Four-pointed lens glint used when the hologram powers up. */
export function glintTexture() {
  return canvasTexture(256, (ctx) => {
    const c = 128
    const g = ctx.createRadialGradient(c, c, 0, c, c, c)
    g.addColorStop(0, 'rgba(255,255,255,1)')
    g.addColorStop(0.12, 'rgba(230,255,240,0.8)')
    g.addColorStop(0.4, 'rgba(160,255,200,0.15)')
    g.addColorStop(1, 'rgba(0,0,0,0)')
    ctx.fillStyle = g
    ctx.fillRect(0, 0, 256, 256)
    ctx.globalCompositeOperation = 'lighter'
    for (const [w, h] of [[256, 5], [5, 256], [160, 2], [2, 160]]) {
      const ray = ctx.createRadialGradient(c, c, 0, c, c, Math.max(w!, h!) / 2)
      ray.addColorStop(0, 'rgba(255,255,255,0.95)')
      ray.addColorStop(1, 'rgba(255,255,255,0)')
      ctx.fillStyle = ray
      ctx.fillRect(c - w! / 2, c - h! / 2, w!, h!)
    }
  })
}
