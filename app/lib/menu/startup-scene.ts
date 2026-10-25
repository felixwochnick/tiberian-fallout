import * as THREE from 'three'
import { GLTFLoader, type GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import { HologramShader } from './hologram'
import { glintTexture } from './textures'

/**
 * Rebuild of Tiberian Sun's STARTUP.VQA.
 *
 * Models, baked grime textures, the camera move and the rising discs come
 * from Blender (blender/startup_menu.py → public/models/startup-menu.glb).
 * This class adds what is time-driven on top: hologram (see hologram.ts),
 * glint and the low-fi look of the original video.
 */

export const MODEL_URL = '/models/startup-menu.glb'

/** Timeline in seconds (matches the 6 s of the original video and its sound). */
export const TIMELINE = {
  hologram: [3.6, 4.0],
  glint: [3.55, 4.2],
  logo: [4.3, 4.85],
  emblems: [4.75, 5.3],
  end: 6,
} as const

const clamp01 = (x: number) => Math.min(1, Math.max(0, x))
const progress = ([a, b]: readonly [number, number], t: number) => clamp01((t - a) / (b - a))
const easeOut = (x: number) => 1 - (1 - x) ** 3

/** Film grain and 15 bit colour (RGB555 like the VQA videos). */
const LowFiShader = {
  uniforms: {
    tDiffuse: { value: null as THREE.Texture | null },
    time: { value: 0 },
    grain: { value: 0.055 },
    levels: { value: 32 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }`,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform float time;
    uniform float grain;
    uniform float levels;
    varying vec2 vUv;
    float hash(vec2 p) {
      return fract(sin(dot(p, vec2(12.9898, 78.233)) + time * 61.7) * 43758.5453);
    }
    void main() {
      vec4 color = texture2D(tDiffuse, vUv);
      color.rgb += (hash(gl_FragCoord.xy) - 0.5) * grain;
      color.rgb = floor(color.rgb * levels + 0.5) / levels;
      gl_FragColor = color;
    }`,
}

export class StartupScene {
  readonly renderer: THREE.WebGLRenderer
  private readonly scene = new THREE.Scene()
  private camera!: THREE.PerspectiveCamera
  private mixer!: THREE.AnimationMixer
  private actions: THREE.AnimationAction[] = []
  private readonly composer: EffectComposer
  private readonly bloom: UnrealBloomPass
  private readonly lowFi: ShaderPass
  private readonly hologram: ShaderPass
  /** Vertical FOV from Blender, designed for a 16:10 frame. */
  private baseFov = 38
  private readonly disposables: { dispose(): void }[] = []

  /** Effects are designed in the XY plane; glTF is Y-up, so this group lays them flat. */
  private readonly overlay = new THREE.Group()
  private glint!: THREE.Sprite
  private risingParts: THREE.Object3D[] = []

  static async create(container: HTMLElement) {
    const gltf = await new GLTFLoader().loadAsync(MODEL_URL)
    return new StartupScene(container, gltf)
  }

  private constructor(private readonly container: HTMLElement, gltf: GLTF) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping
    this.renderer.toneMappingExposure = 0.95
    this.renderer.setClearColor(0x000000)
    container.appendChild(this.renderer.domElement)

    this.setupModel(gltf)
    this.buildLights()

    this.overlay.rotation.x = -Math.PI / 2
    this.scene.add(this.overlay)
    this.buildGlint()
    this.buildHalfShade()

    this.composer = new EffectComposer(this.renderer)
    this.composer.addPass(new RenderPass(this.scene, this.camera))
    this.hologram = new ShaderPass(HologramShader)
    this.composer.addPass(this.hologram)
    this.bloom = new UnrealBloomPass(new THREE.Vector2(640, 400), 0.15, 0.5, 0.9)
    this.composer.addPass(this.bloom)
    this.composer.addPass(new OutputPass())
    this.lowFi = new ShaderPass(LowFiShader)
    this.composer.addPass(this.lowFi)

    this.resize()
    this.render(0)
  }

  private track<T extends { dispose(): void }>(resource: T): T {
    this.disposables.push(resource)
    return resource
  }

  private setupModel(gltf: GLTF) {
    this.scene.add(gltf.scene)
    const camera = gltf.cameras[0]
    if (!(camera instanceof THREE.PerspectiveCamera)) throw new Error('Startup model has no perspective camera')
    this.camera = camera
    this.baseFov = camera.fov

    this.mixer = new THREE.AnimationMixer(gltf.scene)
    // The time is set explicitly every frame (see render), so the actions never run on their own
    this.actions = gltf.animations.map(clip => this.mixer.clipAction(clip).play())

    this.risingParts = ['OuterRing', 'SegRing', 'RibRing', 'CentrePlate']
      .map(name => gltf.scene.getObjectByName(name))
      .filter((o): o is THREE.Object3D => !!o)
  }

  private buildLights() {
    this.scene.add(new THREE.AmbientLight(0xfff1dd, 0.35))
    // Blender key light (-1.2, 1.6, 5.2) converted to glTF's Y-up axes
    const key = new THREE.SpotLight(0xfff0d2, 110, 14, 0.8, 0.85, 1.4)
    key.position.set(-1.2, 5.2, -1.6)
    key.target.position.set(0, 0, 0)
    this.scene.add(key, key.target)
    const fill = new THREE.PointLight(0xffd59a, 3, 6, 1.5)
    fill.position.set(1.4, 1.2, 1)
    this.scene.add(fill)
  }

  private buildGlint() {
    this.glint = new THREE.Sprite(this.track(new THREE.SpriteMaterial({
      map: this.track(glintTexture()),
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      depthTest: false,
    })))
    this.glint.position.set(0, 0, 0.3)
    this.glint.renderOrder = 10
    this.overlay.add(this.glint)
  }

  /** The original has a slightly lighter right half, split at the vertical rod. */
  private buildHalfShade() {
    const shade = new THREE.Mesh(
      this.track(new THREE.PlaneGeometry(8, 12)),
      this.track(new THREE.MeshBasicMaterial({ color: 0xfff2d8, transparent: true, opacity: 0.03, blending: THREE.AdditiveBlending, depthWrite: false })),
    )
    shade.position.set(4, 0, 0.25)
    shade.renderOrder = 5
    this.overlay.add(shade)
  }

  resize() {
    const { clientWidth: w, clientHeight: h } = this.container
    if (!w || !h) return
    this.renderer.setSize(w, h)
    this.composer.setSize(w, h)
    // Wider than 16:10: keep the height and show more of the plate at the sides.
    // Narrower: keep the width of the 16:10 frame, so the machine always fits.
    const aspect = w / h
    const design = 16 / 10
    this.camera.aspect = aspect
    this.camera.fov = aspect >= design
      ? this.baseFov
      : THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(this.baseFov) / 2) * design / aspect))
    this.camera.updateProjectionMatrix()
  }

  /** Renders the state of the animation at time `t` (seconds). */
  render(t: number) {
    // Set each action's time directly: mixer.setTime() would restart actions that
    // already finished, which made the camera jump back to its start pose
    const time = Math.min(Math.max(t, 0), TIMELINE.end - 1e-3)
    for (const action of this.actions) {
      action.enabled = true
      action.paused = false
      action.time = time
    }
    this.mixer.update(0)

    // Deep inside the shaft the discs are in darkness and light up as they rise
    for (const part of this.risingParts) {
      const light = THREE.MathUtils.lerp(0.15, 1, clamp01(1 + part.position.y / 1.4))
      part.traverse((o) => {
        const material = (o as THREE.Mesh).material as THREE.MeshStandardMaterial | undefined
        material?.color?.setScalar(light)
      })
    }

    const h = easeOut(progress(TIMELINE.hologram, t))
    const holo = this.hologram.uniforms
    holo.intensity!.value = h
    holo.time!.value = performance.now() / 1000
    this.camera.updateMatrixWorld()
    holo.cameraPos!.value.setFromMatrixPosition(this.camera.matrixWorld)
    holo.cameraWorld!.value.copy(this.camera.matrixWorld)
    holo.projectionInverse!.value.copy(this.camera.projectionMatrixInverse)
    this.bloom.strength = 0.12 + h * 0.35

    const g = progress(TIMELINE.glint, t)
    const glint = g > 0 && g < 1 ? Math.sin(g * Math.PI) : 0
    this.glint.material.opacity = glint
    this.glint.scale.setScalar(0.6 + glint * 2.4)
    this.glint.material.rotation = g * 0.6

    // Grain keeps moving after the animation has ended
    this.lowFi.uniforms.time!.value = performance.now() / 1000
    this.composer.render()
  }

  dispose() {
    this.scene.traverse((o) => {
      const mesh = o as THREE.Mesh
      if (!mesh.isMesh) return
      mesh.geometry.dispose()
      const material = mesh.material as THREE.MeshStandardMaterial
      for (const map of [material.map, material.normalMap, material.roughnessMap, material.metalnessMap, material.alphaMap]) map?.dispose()
      material.dispose()
    })
    for (const resource of this.disposables) resource.dispose()
    this.composer.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
