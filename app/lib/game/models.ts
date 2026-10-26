import * as THREE from 'three'

/**
 * The new 3D models (GLB in public/models, built by the scripts in blender/), by the
 * RULES.INI id of the object they show.
 */
export const MODELS: Record<string, string> = {
  GACNST: '/models/GACNST.glb',
  GAPILE: '/models/GAPILE.glb',
  GAPOWR: '/models/GAPOWR.glb',
  GAPOWRUP: '/models/GAPOWRUP.glb',
  PROC: '/models/PROC.glb',
  GASAND: '/models/GASAND.glb',
  E1: '/models/E1.glb',
  E2: '/models/E2.glb',
  E3: '/models/E3.glb',
  ENGINEER: '/models/ENGINEER.glb',
  MCV: '/models/MCV.glb',
  HARV: '/models/HARV.glb',
  SMECH: '/models/SMECH.glb',
  MMCH: '/models/MMCH.glb',
  DSHP: '/models/DSHP.glb',
  /** Tiberium on one cell: nodes Stage1A … Stage3C (growth stage 1–3, variant A–C), show one */
  TIB: '/models/TIB.glb',
}

/** Units without a model of their own yet use the light infantry's */
export const UNIT_FALLBACK = MODELS.E1!

/**
 * How far the light camouflage is brightened towards the GDI sand's brightness (0: the
 * plain shade, 1: just as bright); gold is the sand either way, the other colours get
 * darker with less
 */
const LIGHT_CAMO_BRIGHTENING = 0.5

/** The two sides: GDI wears camouflage in shades of the house colour, Nod dark armour */
export type Side = 'gdi' | 'nod'

/**
 * Nod's camouflage shades: near black with a hint of the house colour; the shade's own
 * lightness only sets the blotches apart (sRGB HSL)
 */
const NOD_LIGHTNESS = { base: 0.06, range: 0.22 }
const NOD_SATURATION = 0.3

/**
 * Paints a model's material in the house colour, in three grades like the original:
 *  - "Remap": the colour as it is (accents: bands, shoulder pads);
 *  - extras remapLightness / remapSaturation (set in blender/): a shade of it, e.g. the
 *    strong camouflage of the infantry, the MCV and the harvester (brown-yellow for
 *    gold, red for red);
 *  - with remapLuminance as well: the light camouflage of the buildings and walkers, a
 *    grey pattern (texture) tinted with a pale shade, brightened towards the GDI sand
 *    (red or blue at the gold's lightness look much darker).
 * For Nod the uniform is dark armour, the house colour stays on the accents: materials
 * with the extra nodColour (armour, helmet, packs) take that colour, the shades become
 * near black.
 */
export function applyHouseColour(mat: THREE.MeshStandardMaterial, houseColour: number, side: Side = 'gdi') {
  const shade = mat.userData as { remapLightness?: number, remapSaturation?: number, remapLuminance?: number, nodColour?: string }
  if (side === 'nod' && shade.nodColour) {
    mat.color.set(shade.nodColour)
    return
  }
  if (mat.name !== 'Remap' && shade.remapLightness === undefined) return
  mat.color.set(houseColour)
  if (shade.remapLightness === undefined) return
  // in sRGB like the factors, which were taken from the colour picker's view
  const { h, s, l } = mat.color.getHSL({ h: 0, s: 0, l: 0 }, THREE.SRGBColorSpace)
  const saturation = s * (shade.remapSaturation ?? 1)
  const lightness = l * shade.remapLightness
  if (side === 'nod') {
    mat.color.setHSL(h, saturation * NOD_SATURATION, NOD_LIGHTNESS.base + lightness * NOD_LIGHTNESS.range, THREE.SRGBColorSpace)
    return
  }
  mat.color.setHSL(h, saturation, lightness, THREE.SRGBColorSpace)
  const target = shade.remapLuminance
  if (target === undefined) return
  // the lightness at which the shade is as bright as the target; the colour is linear
  // here, like the target
  let low = 0
  let high = 1
  for (let i = 0; i < 16; i++) {
    const mid = (low + high) / 2
    mat.color.setHSL(h, saturation, mid, THREE.SRGBColorSpace)
    const luminance = 0.2126 * mat.color.r + 0.7152 * mat.color.g + 0.0722 * mat.color.b
    if (luminance < target) low = mid
    else high = mid
  }
  mat.color.setHSL(h, saturation, THREE.MathUtils.lerp(lightness, (low + high) / 2, LIGHT_CAMO_BRIGHTENING), THREE.SRGBColorSpace)
}
