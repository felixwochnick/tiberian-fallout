import * as THREE from 'three'
import { Particles, type ParticleSpec } from './particles'

/**
 * The battlefield's effects, made of particles (particles.ts): muzzle flashes, hits,
 * explosions with fire, smoke, sparks and debris and a scorch mark on the ground,
 * rocket trails, the dust and Tiberium shards of a harvester at work, exhaust smoke,
 * and the exhaust of the dropship's turbines with the dust they blow up near the ground.
 * Sizes in cells, times in seconds.
 */

const random = (min: number, max: number) => min + Math.random() * (max - min)
/** A random direction, `up` biased upwards (0: any, 1: straight up) */
function scatter(speed: number, up = 0) {
  const v = new THREE.Vector3(random(-1, 1), random(-1, 1), random(-1, 1))
  if (v.lengthSq() < 1e-6) v.set(0, 1, 0)
  v.normalize()
  v.y = Math.abs(v.y) * up + v.y * (1 - up)
  return v.normalize().multiplyScalar(speed)
}

/** Seconds a scorch mark stays on the ground, fading out at the end */
const SCORCH_SECONDS = 12

export class Effects {
  readonly particles: Particles
  private readonly scorches: { mesh: THREE.Mesh, time: number }[] = []
  private readonly scorchGeometry = new THREE.CircleGeometry(0.5, 20).rotateX(-Math.PI / 2)
  private readonly scorchTexture: THREE.Texture
  private readonly scorchMaterial: THREE.MeshBasicMaterial

  constructor(private readonly scene: THREE.Scene) {
    this.particles = new Particles(scene)
    // a scorch mark: dark in the middle, frayed at the edge
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = 64
    const g = canvas.getContext('2d')!
    for (let i = 0; i < 9; i++) {
      const x = 32 + random(-8, 8)
      const y = 32 + random(-8, 8)
      const gradient = g.createRadialGradient(x, y, 0, x, y, random(14, 26))
      gradient.addColorStop(0, 'rgba(20,16,12,0.5)')
      gradient.addColorStop(1, 'rgba(20,16,12,0)')
      g.fillStyle = gradient
      g.fillRect(0, 0, 64, 64)
    }
    this.scorchTexture = new THREE.CanvasTexture(canvas)
    this.scorchTexture.colorSpace = THREE.SRGBColorSpace
    this.scorchMaterial = new THREE.MeshBasicMaterial({
      map: this.scorchTexture, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2,
    })
  }

  update(seconds: number, pixelsPerCell: number) {
    this.particles.update(seconds, pixelsPerCell)
    for (const scorch of this.scorches) {
      scorch.time += seconds
      const left = SCORCH_SECONDS - scorch.time
      ;(scorch.mesh.material as THREE.MeshBasicMaterial).opacity = Math.min(1, left / 3)
    }
    for (const scorch of this.scorches.filter(s => s.time > SCORCH_SECONDS)) {
      this.scene.remove(scorch.mesh)
      ;(scorch.mesh.material as THREE.Material).dispose()
    }
    this.scorches.splice(0, this.scorches.length, ...this.scorches.filter(s => s.time <= SCORCH_SECONDS))
  }

  /** The flash of a shot leaving the muzzle along `direction`, with a wisp of smoke; `heavy` for cannons */
  muzzleFlash(at: THREE.Vector3, direction: THREE.Vector3, heavy = false) {
    const p = this.particles
    const k = heavy ? 2.4 : 1.3
    const dir = direction.clone().setY(direction.y).normalize()
    p.emit({ position: at, life: 0.06 * k, size: [0.16 * k, 0.24 * k], colour: [0xfff6d8, 0xffa040], alpha: [1, 0.2], additive: true })
    for (let i = 0; i < 3; i++) {
      // the flame tongue out of the barrel
      p.emit({ position: at.clone().addScaledVector(dir, 0.04 * (i + 1) * k), velocity: dir.clone().multiplyScalar(1.5 * k),
               life: 0.05 * k, size: [0.1 * k * (1 - i * 0.25), 0.05], colour: [0xffe7a0, 0xff6a10], additive: true })
    }
    for (let i = 0; i < (heavy ? 5 : 2); i++) {
      p.emit({ position: at, velocity: dir.clone().multiplyScalar(random(0.2, 0.5) * k).add(scatter(0.1, 0.6)), life: random(0.5, 0.9) * k,
               size: [0.08 * k, 0.3 * k], colour: [0xb8b0a0, 0x8a8478], alpha: [0.35, 0], fadeIn: 0.1, drag: 2, gravity: -0.15,
               spin: random(-1, 1), sprite: 'smoke' })
    }
  }

  /** A bullet hits: dust from the ground, sparks off armour (`hard`) */
  bulletHit(at: THREE.Vector3, hard: boolean) {
    const p = this.particles
    if (hard) {
      for (let i = 0; i < 5; i++) {
        p.emit({ position: at, velocity: scatter(random(0.8, 1.8), 0.5), life: random(0.15, 0.3), size: [0.04, 0.015],
                 colour: [0xfff0c0, 0xff7a20], gravity: 4, drag: 1, additive: true, sprite: 'spark' })
      }
      p.emit({ position: at, life: 0.05, size: [0.1, 0.14], colour: [0xfff2d0, 0xffb060], additive: true })
    }
    for (let i = 0; i < 3; i++) {
      p.emit({ position: at.clone().add(scatter(0.03)), velocity: scatter(random(0.2, 0.5), 0.8), life: random(0.4, 0.7),
               size: [0.07, 0.22], colour: [0xc8b48c, 0xa08c6c], alpha: [0.6, 0], fadeIn: 0.1, drag: 3, gravity: 0.3,
               spin: random(-2, 2), sprite: 'smoke' })
    }
  }

  /** Welding on a building being repaired (DefaultRepairParticleSystem=WeldingSys): a spray of sparks and a flash */
  weld(at: THREE.Vector3) {
    const p = this.particles
    for (let i = 0; i < 6; i++) {
      p.emit({ position: at, velocity: scatter(random(0.6, 1.4), 0.6), life: random(0.2, 0.4), size: [0.035, 0.012],
               colour: [0xfffbe0, 0x9fd0ff], gravity: 3, drag: 1, additive: true, sprite: 'spark' })
    }
    p.emit({ position: at, life: 0.06, size: [0.08, 0.12], colour: [0xe8f4ff, 0x9fd0ff], additive: true })
  }

  /**
   * Something rolled over: a burst sandbag throws up a cloud of sand and clods, a
   * soldier a little dust and dark spatter.
   */
  crush(at: THREE.Vector3, wall: boolean) {
    const p = this.particles
    const ground = at.clone().setY(0.04)
    for (let i = 0; i < (wall ? 8 : 3); i++) {
      p.emit({ position: ground.clone().add(scatter(wall ? 0.25 : 0.08).setY(0)), velocity: scatter(random(0.2, 0.6), 0.6),
               life: random(0.8, 1.5), size: [wall ? 0.2 : 0.1, random(0.5, wall ? 0.9 : 0.4)], colour: [0xd8c8a0, 0xb0a080],
               alpha: [0.7, 0], fadeIn: 0.1, drag: 1.5, gravity: -0.05, spin: random(-1, 1), sprite: 'smoke' })
    }
    for (let i = 0; i < (wall ? 10 : 6); i++) {
      p.emit({ position: ground, velocity: scatter(random(0.6, 1.4), 0.7), life: random(0.4, 0.7), size: [0.045, 0.035],
               colour: wall ? [0x8a7a58, 0x6a5c40] : [0x5a1810, 0x3a100a], gravity: 5, drag: 0.5, sprite: 'smoke' })
    }
  }

  /**
   * An explosion of `size` (cells across the fireball): a white flash, a fireball
   * rolling up, sparks and dark debris flying, smoke that rises and drifts away, and a
   * scorch mark on the ground; `delay` seconds from now.
   */
  explosion(at: THREE.Vector3, size = 0.5, delay = 0) {
    const s = Math.max(0.2, size)
    const p = { emit: (spec: ParticleSpec) => this.particles.emit({ ...spec, delay: (spec.delay ?? 0) + delay }) }
    p.emit({ position: at, life: 0.08, size: [s * 0.9, s * 1.4], colour: [0xfff0d0, 0xff9a40], alpha: [0.8, 0], additive: true })
    for (let i = 0; i < 8; i++) {
      p.emit({ position: at.clone().add(scatter(s * 0.15)), velocity: scatter(random(0.5, 1.4) * s, 0.4), life: random(0.35, 0.65),
               size: [s * random(0.3, 0.5), s * random(0.7, 1.0)], colour: [0xffb040, 0x901800], alpha: [0.75, 0], drag: 3, gravity: -0.6 * s,
               spin: random(-2, 2), additive: true, sprite: 'smoke' })
    }
    // the dark heart of the fireball, smoke rolling out of it
    for (let i = 0; i < 4; i++) {
      p.emit({ position: at.clone().add(scatter(s * 0.1)), velocity: scatter(random(0.3, 0.7) * s, 0.6), delay: 0.04, life: random(0.5, 0.8),
               size: [s * 0.4, s * 0.9], colour: [0x3a2a1c, 0x2a2420], alpha: [0.7, 0], fadeIn: 0.2, drag: 2.5, gravity: -0.4 * s,
               spin: random(-1, 1), sprite: 'smoke' })
    }
    for (let i = 0; i < 12; i++) {
      p.emit({ position: at, velocity: scatter(random(1.5, 3.5) * Math.sqrt(s), 0.6), life: random(0.3, 0.7), size: [0.04, 0.015],
               colour: [0xfff0c0, 0xff5a10], gravity: 5, drag: 0.8, additive: true, sprite: 'spark' })
    }
    for (let i = 0; i < 6; i++) {
      p.emit({ position: at, velocity: scatter(random(1, 2.2) * Math.sqrt(s), 0.8), life: random(0.5, 0.9), size: [0.05, 0.04],
               colour: [0x2a2622, 0x1a1816], alpha: [1, 0.8], gravity: 6, spin: random(-8, 8), sprite: 'shard' })
    }
    for (let i = 0; i < 9; i++) {
      p.emit({ position: at.clone().add(scatter(s * 0.2)), velocity: scatter(random(0.15, 0.4) * s, 0.7).add(new THREE.Vector3(0.08, 0, 0)),
               delay: random(0.05, 0.25), life: random(1.6, 2.8), size: [s * 0.5, s * random(1.4, 2.0)],
               colour: [0x4a4440, 0x8a8580], alpha: [0.6, 0], fadeIn: 0.15, drag: 1.2, gravity: -0.25, spin: random(-0.6, 0.6), sprite: 'smoke' })
    }
    if (at.y < 0.6) this.scorch(at, s * 1.4)
  }

  /** A dark mark on the ground where something exploded */
  scorch(at: THREE.Vector3, diameter: number) {
    const mesh = new THREE.Mesh(this.scorchGeometry, this.scorchMaterial.clone())
    mesh.position.set(at.x, 0.006, at.z)
    mesh.rotation.y = Math.random() * Math.PI * 2
    mesh.scale.setScalar(diameter)
    mesh.renderOrder = 1
    this.scene.add(mesh)
    this.scorches.push({ mesh, time: 0 })
  }

  /** A rocket's exhaust: a hot core at its tail and smoke left behind (call every frame) */
  rocketTrail(at: THREE.Vector3, back: THREE.Vector3) {
    const p = this.particles
    p.emit({ position: at, velocity: back.clone().multiplyScalar(0.4), life: 0.08, size: [0.09, 0.03], colour: [0xfff0b0, 0xff6a10], additive: true })
    p.emit({ position: at.clone().add(scatter(0.01)), velocity: scatter(0.05, 0.5), life: random(0.6, 1.0), size: [0.05, 0.2],
             colour: [0xd8d2c8, 0x9a958e], alpha: [0.5, 0], fadeIn: 0.05, drag: 1.5, gravity: -0.1, spin: random(-1, 1), sprite: 'smoke' })
  }

  /** A glowing shell's trail (call every frame) */
  tracer(at: THREE.Vector3) {
    this.particles.emit({ position: at, life: 0.12, size: [0.06, 0.02], colour: [0xffe0a0, 0xff7020], alpha: [0.8, 0], additive: true })
  }

  /**
   * A harvester's collector at work at `at` (on the ground): clouds of dust, green
   * Tiberium shards thrown up and falling back, a green shimmer.
   */
  harvestDust(at: THREE.Vector3, across: THREE.Vector3, kind: 'green' | 'blue' = 'green') {
    const p = this.particles
    const blue = kind === 'blue'
    const spot = () => at.clone().addScaledVector(across, random(-0.22, 0.22)).setY(random(0.02, 0.08))
    // dust thrown up by the drum, billowing and drifting
    p.emit({ position: spot(), velocity: scatter(random(0.15, 0.4), 0.7), life: random(1.0, 1.8), size: [0.2, random(0.6, 0.95)],
            colour: [0xddd0b0, 0xb8ab90], alpha: [0.7, 0], fadeIn: 0.12, drag: 1.2, gravity: -0.1, spin: random(-1, 1), sprite: 'smoke' })
    // Tiberium dust: a greenish (bluish) haze
    p.emit({ position: spot(), velocity: scatter(random(0.1, 0.25), 0.8), life: random(0.8, 1.3), size: [0.15, random(0.4, 0.6)],
            colour: blue ? [0x90c0f0, 0x7090b8] : [0xa8e080, 0x80a868], alpha: [0.45, 0], fadeIn: 0.15, drag: 1.4, gravity: -0.12, spin: random(-1, 1), sprite: 'smoke' })
    // crystal shards flung up, glinting, falling back
    for (let i = 0; i < 2; i++) {
      p.emit({ position: spot(), velocity: scatter(random(0.7, 1.4), 0.85), life: random(0.45, 0.8), size: [0.06, 0.04],
               colour: blue ? [0xa0e0ff, 0x2070e0] : [0xc8ff80, 0x40c020], gravity: 4, spin: random(-12, 12), additive: true, sprite: 'shard' })
    }
    if (Math.random() < 0.5) {
      p.emit({ position: spot().setY(0.12), velocity: scatter(0.12, 0.9), life: random(0.5, 0.9), size: [0.2, 0.45],
               colour: blue ? [0x50a0ff, 0x103080] : [0x60ff40, 0x208010], alpha: [0.3, 0], fadeIn: 0.2, gravity: -0.2, additive: true })
    }
  }

  /** Smoke out of an exhaust stack; `amount` 0 … 1 (idling … working hard) */
  exhaust(at: THREE.Vector3, amount: number) {
    if (Math.random() > 0.25 + 0.75 * amount) return
    this.particles.emit({
      position: at, velocity: new THREE.Vector3(random(-0.05, 0.05), random(0.25, 0.45), random(-0.05, 0.05)), life: random(0.8, 1.4),
      size: [0.06, random(0.25, 0.4)], colour: [0x2e2c2a, 0x6a6662], alpha: [0.3 + 0.35 * amount, 0], fadeIn: 0.1, drag: 0.8,
      spin: random(-1, 1), sprite: 'smoke',
    })
  }

  /**
   * A turbine's exhaust at `at` blowing along `direction`, `strength` 0 … 1 (the
   * dropship has turbines, no jets: no flame): hot air shimmering out of the nozzle,
   * a faint grey trail of exhaust drifting off; near the ground (`ground`: the height
   * above it) it blows dust up all round.
   */
  thrust(at: THREE.Vector3, direction: THREE.Vector3, strength: number, ground = Infinity) {
    const p = this.particles
    const dir = direction.clone().normalize()
    // hot air: barely there, lighter than what is behind it, widening as it slows
    p.emit({ position: at.clone().add(scatter(0.03)), velocity: dir.clone().multiplyScalar(random(2, 3) * strength).add(scatter(0.15)),
             life: random(0.25, 0.4), size: [0.25 * strength, 0.6 * strength], colour: [0xe8e6e0, 0xd8d6d0], alpha: [0.1, 0], fadeIn: 0.15,
             drag: 2.5, spin: random(-2, 2), sprite: 'smoke' })
    // the exhaust: thin grey wisps trailing off
    if (Math.random() < 0.5 * strength) {
      p.emit({ position: at.clone().addScaledVector(dir, 0.15), velocity: dir.clone().multiplyScalar(random(1.2, 1.8) * strength).add(scatter(0.1)),
               life: random(0.7, 1.1), size: [0.2, 0.7], colour: [0x9a9894, 0xb4b2ae], alpha: [0.14, 0], fadeIn: 0.2, drag: 1.8,
               spin: random(-1, 1), sprite: 'smoke' })
    }
    // the jet hits the ground: dust blown out in a ring
    const reach = 1.6
    if (ground < reach && dir.y < -0.5) {
      const k = (1 - ground / reach) * strength
      const below = at.clone().addScaledVector(dir, ground / -dir.y).setY(0.03)
      for (let i = 0; i < 2; i++) {
        if (Math.random() > k) continue
        const out = new THREE.Vector3(random(-1, 1), 0, random(-1, 1)).normalize()
        p.emit({ position: below.clone().addScaledVector(out, random(0.05, 0.3)), velocity: out.multiplyScalar(random(1.2, 2.2) * k).setY(random(0.05, 0.25)),
                 life: random(0.8, 1.4), size: [0.25, random(0.8, 1.2)], colour: [0xd8c8a4, 0xb0a084], alpha: [0.6 * k, 0], fadeIn: 0.1,
                 drag: 1.6, spin: random(-1, 1), sprite: 'smoke' })
      }
    }
  }

  /** Something burns at `at` (a wreck): flames and thick dark smoke (call every frame) */
  burn(at: THREE.Vector3, size = 0.4) {
    const p = this.particles
    if (Math.random() < 0.7) {
      p.emit({ position: at.clone().add(scatter(size * 0.3).setY(0)), velocity: new THREE.Vector3(0, random(0.3, 0.6), 0), life: random(0.3, 0.5),
               size: [size * 0.5, size * 0.2], colour: [0xffd070, 0xc02a08], alpha: [0.9, 0], additive: true, spin: random(-2, 2), sprite: 'smoke' })
    }
    if (Math.random() < 0.5) {
      p.emit({ position: at.clone().add(scatter(size * 0.2)).setY(at.y + size * 0.3), velocity: new THREE.Vector3(random(0.05, 0.15), random(0.35, 0.6), 0),
               life: random(2, 3), size: [size * 0.6, size * 2.2], colour: [0x24201c, 0x5a5652], alpha: [0.55, 0], fadeIn: 0.1, drag: 0.4,
               spin: random(-0.5, 0.5), sprite: 'smoke' })
    }
  }

  dispose() {
    this.particles.dispose()
    for (const scorch of this.scorches) {
      this.scene.remove(scorch.mesh)
      ;(scorch.mesh.material as THREE.Material).dispose()
    }
    this.scorchGeometry.dispose()
    this.scorchTexture.dispose()
    this.scorchMaterial.dispose()
  }
}
