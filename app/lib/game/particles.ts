import * as THREE from 'three'

/**
 * Particles for the battlefield's effects (fire, smoke, dust, sparks …): sprites
 * that always face the camera, each with its own life, motion, size, colour and
 * opacity over its life. Two layers: glowing ones add their light (fire, flashes,
 * sparks, engine jets), the others cover what is behind them (smoke, dust).
 *
 * The sprites are drawn as points with a texture from a small atlas made on a
 * canvas: a soft glow, a puff of smoke, a spark, a crystal shard.
 */

export type Sprite = 'glow' | 'smoke' | 'spark' | 'shard'
const SPRITES: Sprite[] = ['glow', 'smoke', 'spark', 'shard']

export interface ParticleSpec {
  position: THREE.Vector3
  velocity?: THREE.Vector3
  /** Seconds it lives */
  life: number
  /** Seconds before it appears */
  delay?: number
  /** Diameter in cells at birth and at death */
  size: [number, number]
  /** Colour at birth and at death */
  colour: [THREE.ColorRepresentation, THREE.ColorRepresentation]
  /** Opacity at its height and at death; it fades in over the first `fadeIn` share of its life */
  alpha?: [number, number]
  fadeIn?: number
  /** Cells per second² pulling down (negative: it rises, like hot smoke) */
  gravity?: number
  /** Share of its speed it loses per second (air drag) */
  drag?: number
  /** Radians per second the sprite turns */
  spin?: number
  sprite?: Sprite
  /** Adds its light (fire, glow) instead of covering (smoke, dust) */
  additive?: boolean
}

interface Particle {
  position: THREE.Vector3
  velocity: THREE.Vector3
  age: number
  life: number
  size0: number
  size1: number
  colour0: THREE.Color
  colour1: THREE.Color
  alpha0: number
  alpha1: number
  fadeIn: number
  gravity: number
  drag: number
  rotation: number
  spin: number
  sprite: number
}

const VERTEX = /* glsl */ `
  attribute float size;
  attribute vec4 tint;
  attribute float rotation;
  attribute float sprite;
  uniform float pixelsPerCell;
  varying vec4 vTint;
  varying float vRotation;
  varying float vSprite;
  void main() {
    vTint = tint;
    vRotation = rotation;
    vSprite = sprite;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = size * pixelsPerCell;
  }
`

const FRAGMENT = /* glsl */ `
  uniform sampler2D atlas;
  varying vec4 vTint;
  varying float vRotation;
  varying float vSprite;
  void main() {
    vec2 p = gl_PointCoord - 0.5;
    float c = cos(vRotation);
    float s = sin(vRotation);
    p = vec2(c * p.x - s * p.y, s * p.x + c * p.y) + 0.5;
    if (p.x < 0.0 || p.x > 1.0 || p.y < 0.0 || p.y > 1.0) discard;
    vec4 texel = texture2D(atlas, vec2((vSprite + p.x) / ${SPRITES.length}.0, 1.0 - p.y));
    float alpha = texel.a * vTint.a;
    if (alpha < 0.004) discard;
    gl_FragColor = vec4(texel.rgb * vTint.rgb, alpha);
  }
`

/** The sprites side by side on one canvas: white, the alpha carries the shape */
function atlas() {
  const cell = 64
  const canvas = document.createElement('canvas')
  canvas.width = cell * SPRITES.length
  canvas.height = cell
  const g = canvas.getContext('2d')!
  const centre = cell / 2
  // a soft glow, bright in the middle
  let x = 0
  let gradient = g.createRadialGradient(x + centre, centre, 0, x + centre, centre, centre)
  gradient.addColorStop(0, 'rgba(255,255,255,1)')
  gradient.addColorStop(0.25, 'rgba(255,255,255,0.75)')
  gradient.addColorStop(0.6, 'rgba(255,255,255,0.2)')
  gradient.addColorStop(1, 'rgba(255,255,255,0)')
  g.fillStyle = gradient
  g.fillRect(x, 0, cell, cell)
  // a puff of smoke: overlapping soft blobs, shaded a little darker at the bottom
  x = cell
  const random = mulberry(7)
  for (let i = 0; i < 14; i++) {
    const a = random() * Math.PI * 2
    const d = random() * cell * 0.2
    const r = cell * (0.16 + random() * 0.14)
    const bx = x + centre + Math.cos(a) * d
    const by = centre + Math.sin(a) * d
    const shade = Math.round(200 + 55 * (1 - (by - centre + cell * 0.3) / (cell * 0.6)))
    gradient = g.createRadialGradient(bx, by, 0, bx, by, r)
    gradient.addColorStop(0, `rgba(${shade},${shade},${shade},0.8)`)
    gradient.addColorStop(1, `rgba(${shade},${shade},${shade},0)`)
    g.fillStyle = gradient
    g.fillRect(x, 0, cell, cell)
  }
  // a spark: a hot point with a short glow
  x = cell * 2
  gradient = g.createRadialGradient(x + centre, centre, 0, x + centre, centre, centre * 0.6)
  gradient.addColorStop(0, 'rgba(255,255,255,1)')
  gradient.addColorStop(0.3, 'rgba(255,255,255,0.9)')
  gradient.addColorStop(1, 'rgba(255,255,255,0)')
  g.fillStyle = gradient
  g.fillRect(x, 0, cell, cell)
  // a crystal shard: a lit diamond
  x = cell * 3
  g.beginPath()
  g.moveTo(x + centre, cell * 0.12)
  g.lineTo(x + cell * 0.66, centre)
  g.lineTo(x + centre, cell * 0.88)
  g.lineTo(x + cell * 0.34, centre)
  g.closePath()
  gradient = g.createLinearGradient(x + cell * 0.34, 0, x + cell * 0.66, cell)
  gradient.addColorStop(0, 'rgba(255,255,255,1)')
  gradient.addColorStop(1, 'rgba(160,160,160,0.9)')
  g.fillStyle = gradient
  g.fill()
  // the shades as drawn: the shader works in display colours
  return new THREE.CanvasTexture(canvas)
}

/** A small seeded random generator, so the smoke sprite is the same every time */
function mulberry(seed: number) {
  return () => {
    seed = (seed + 0x6D2B79F5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** One layer of particles (additive or covering) as a point cloud */
class Layer {
  readonly particles: Particle[] = []
  readonly points: THREE.Points
  private readonly geometry = new THREE.BufferGeometry()
  private readonly positions: Float32Array
  private readonly tints: Float32Array
  private readonly sizes: Float32Array
  private readonly rotations: Float32Array
  private readonly sprites: Float32Array

  constructor(readonly capacity: number, material: THREE.ShaderMaterial) {
    this.positions = new Float32Array(capacity * 3)
    this.tints = new Float32Array(capacity * 4)
    this.sizes = new Float32Array(capacity)
    this.rotations = new Float32Array(capacity)
    this.sprites = new Float32Array(capacity)
    const attribute = (array: Float32Array, size: number) => new THREE.BufferAttribute(array, size).setUsage(THREE.DynamicDrawUsage)
    this.geometry.setAttribute('position', attribute(this.positions, 3))
    this.geometry.setAttribute('tint', attribute(this.tints, 4))
    this.geometry.setAttribute('size', attribute(this.sizes, 1))
    this.geometry.setAttribute('rotation', attribute(this.rotations, 1))
    this.geometry.setAttribute('sprite', attribute(this.sprites, 1))
    this.geometry.setDrawRange(0, 0)
    this.points = new THREE.Points(this.geometry, material)
    this.points.frustumCulled = false
  }

  update(seconds: number) {
    const colour = new THREE.Color()
    let n = 0
    for (const p of this.particles) {
      p.age += seconds
      if (p.age < 0 || p.age >= p.life) continue
      p.velocity.multiplyScalar(Math.max(0, 1 - p.drag * seconds))
      p.velocity.y -= p.gravity * seconds
      p.position.addScaledVector(p.velocity, seconds)
      p.rotation += p.spin * seconds
    }
    // the dead are dropped; the living (born already) are written out
    let write = 0
    for (const p of this.particles) {
      if (p.age >= p.life) continue
      this.particles[write++] = p
    }
    this.particles.length = write
    for (const p of this.particles) {
      if (p.age < 0 || n >= this.capacity) continue
      const t = p.age / p.life
      const fade = p.fadeIn > 0 ? Math.min(1, t / p.fadeIn) : 1
      // the shader writes display colours (sRGB) straight out, like the ground's
      colour.copy(p.colour0).lerp(p.colour1, t).convertLinearToSRGB()
      this.positions.set([p.position.x, p.position.y, p.position.z], n * 3)
      this.tints.set([colour.r, colour.g, colour.b, (p.alpha0 + (p.alpha1 - p.alpha0) * t) * fade], n * 4)
      this.sizes[n] = p.size0 + (p.size1 - p.size0) * t
      this.rotations[n] = p.rotation
      this.sprites[n] = p.sprite
      n++
    }
    for (const name of ['position', 'tint', 'size', 'rotation', 'sprite']) this.geometry.getAttribute(name).needsUpdate = true
    this.geometry.setDrawRange(0, n)
  }

  dispose() {
    this.geometry.dispose()
  }
}

export class Particles {
  private readonly texture = atlas()
  private readonly uniforms = { atlas: { value: this.texture as THREE.Texture }, pixelsPerCell: { value: 50 } }
  private readonly glowing: Layer
  private readonly covering: Layer
  private readonly materials: THREE.ShaderMaterial[] = []

  constructor(scene: THREE.Scene, capacity = 6000) {
    const material = (blending: THREE.Blending) => {
      const mat = new THREE.ShaderMaterial({
        uniforms: this.uniforms,
        vertexShader: VERTEX,
        fragmentShader: FRAGMENT,
        transparent: true,
        depthWrite: false,
        blending,
      })
      this.materials.push(mat)
      return mat
    }
    this.covering = new Layer(capacity, material(THREE.NormalBlending))
    this.glowing = new Layer(capacity, material(THREE.AdditiveBlending))
    // the smoke over the models, the glow over the smoke
    this.covering.points.renderOrder = 10
    this.glowing.points.renderOrder = 11
    scene.add(this.covering.points, this.glowing.points)
  }

  emit(spec: ParticleSpec) {
    const layer = spec.additive ? this.glowing : this.covering
    if (layer.particles.length >= layer.capacity) return
    layer.particles.push({
      position: spec.position.clone(),
      velocity: spec.velocity?.clone() ?? new THREE.Vector3(),
      age: -(spec.delay ?? 0),
      life: spec.life,
      size0: spec.size[0],
      size1: spec.size[1],
      colour0: new THREE.Color(spec.colour[0]),
      colour1: new THREE.Color(spec.colour[1]),
      alpha0: spec.alpha?.[0] ?? 1,
      alpha1: spec.alpha?.[1] ?? 0,
      fadeIn: spec.fadeIn ?? 0,
      gravity: spec.gravity ?? 0,
      drag: spec.drag ?? 0,
      rotation: Math.random() * Math.PI * 2,
      spin: spec.spin ?? 0,
      sprite: SPRITES.indexOf(spec.sprite ?? 'glow'),
    })
  }

  /** Moves them on; `pixelsPerCell`: drawing-buffer pixels per cell on screen */
  update(seconds: number, pixelsPerCell: number) {
    this.uniforms.pixelsPerCell.value = pixelsPerCell
    this.covering.update(seconds)
    this.glowing.update(seconds)
  }

  dispose() {
    this.covering.dispose()
    this.glowing.dispose()
    for (const mat of this.materials) mat.dispose()
    this.texture.dispose()
  }
}
