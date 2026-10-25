/**
 * The new 3D models (GLB in public/models, built by the scripts in blender/), by the
 * RULES.INI id of the object they show.
 */
export const MODELS: Record<string, string> = {
  GACNST: '/models/GACNST.glb',
  GAPILE: '/models/GAPILE.glb',
  GAPOWR: '/models/GAPOWR.glb',
  GAPOWRUP: '/models/GAPOWRUP.glb',
  GASAND: '/models/GASAND.glb',
  E1: '/models/E1.glb',
  MCV: '/models/MCV.glb',
  DSHP: '/models/DSHP.glb',
  /** Tiberium on one cell: nodes Stage1A … Stage3C (growth stage 1–3, variant A–C), show one */
  TIB: '/models/TIB.glb',
}

/** Units without a model of their own yet use the light infantry's */
export const UNIT_FALLBACK = MODELS.E1!
