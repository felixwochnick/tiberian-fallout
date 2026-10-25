import * as THREE from 'three'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { type MissionMap, WorldMap } from './world-map'

/**
 * The map selection screen before a mission, rebuilt after the original: the map above,
 * below a plate of dark, worn metal, edged by a straight brass rail; on the plate the
 * briefing text between the turning GDI coin (left) and globe (right).
 *
 * Laid out in the original's 640 × 400 screen units (y down), drawn at any size:
 * the plate and rail are one fragment shader on a full-screen quad, the coin is a
 * small 3D scene drawn into its own viewport.
 */

export const SCREEN_WIDTH = 640
export const SCREEN_HEIGHT = 400

/** The rail, straight across: the screen is split 3/5 map above, 2/5 plate with the text below (screen units) */
const RAIL_LOW = 240
/** Middle of the plate below the rail: coin and globe sit there */
const PLATE_MIDDLE = (RAIL_LOW + SCREEN_HEIGHT) / 2
/** Where the coin sits (centre) and how big it is (screen units) */
const COIN = { x: 62, y: PLATE_MIDDLE, size: 76 }
/** Seconds per turn of the coin */
const COIN_TURN = 2.6
/** The globe on the right of the plate (centre and size, screen units) */
const GLOBE = { x: 580, y: PLATE_MIDDLE, size: 86 }
/** Seconds per turn of the globe */
const GLOBE_TURN = 8

const PanelShader = {
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = vec4(position.xy, 0.0, 1.0);
    }`,
  fragmentShader: /* glsl */ `
    uniform vec2 uScreen;
    uniform float uRailLow;
    uniform float uPixel;
    varying vec2 vUv;

    float hash(vec2 p) {
      return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
    }
    float noise(vec2 p) {
      vec2 i = floor(p), f = fract(p);
      vec2 u = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
    }
    float fbm(vec2 p) {
      float v = 0.0, a = 0.5;
      for (int i = 0; i < 5; i++) {
        v += a * noise(p);
        p = p * 2.03 + 17.1;
        a *= 0.5;
      }
      return v;
    }

    // signed distance to the rail line: < 0 above it (the map), > 0 below it (the plate)
    float rail(vec2 p) {
      return p.y - uRailLow;
    }

    void main() {
      vec2 p = vUv * uScreen;
      p.y = uScreen.y - p.y; // screen units, y down
      float d = rail(p);


      // ---- the plate: dark, worn metal with rust and pits
      float grime = fbm(p * vec2(0.035, 0.05));
      float fine = fbm(p * 0.22);
      float pits = smoothstep(0.72, 0.8, noise(p * 0.45 + 3.0)) * smoothstep(0.5, 0.7, fbm(p * 0.03 + 9.0));
      vec3 plate = mix(vec3(0.055, 0.05, 0.045), vec3(0.17, 0.14, 0.11), grime);
      plate = mix(plate, vec3(0.22, 0.14, 0.07), smoothstep(0.6, 0.85, fbm(p * 0.02 + 4.0)) * 0.35); // rust
      plate *= 0.8 + 0.4 * fine;
      plate *= 1.0 - pits * 0.35;
      // light from the top left, the plate darker towards the bottom
      plate *= mix(1.1, 0.75, p.y / uScreen.y);
      // the rail's shadow on the plate
      plate *= mix(0.45, 1.0, smoothstep(3.0, 12.0, d));

      // above the rail the map shows through
      vec3 colour = plate;
      float alpha = d < 0.0 ? 0.0 : 1.0;

      // ---- the brass rail: a round bar, lit from the top left
      float width = 3.6;
      float across = d / width;
      float bar = 1.0 - smoothstep(1.0 - uPixel / width, 1.0, abs(across));
      if (bar > 0.0) {
        float z = sqrt(max(0.0, 1.0 - across * across));
        vec3 n = normalize(vec3(0.0, -across, z * 1.2));
        vec3 l = normalize(vec3(-0.3, -0.7, 0.65)); // y down: light from above
        float diffuse = max(dot(n, l), 0.0);
        float spec = pow(max(dot(reflect(-l, n), vec3(0, 0, 1)), 0.0), 18.0);
        vec3 brass = vec3(0.8, 0.72, 0.5) * (0.3 + 0.9 * diffuse) + vec3(1.0, 0.97, 0.85) * spec * 0.7;
        // a dark edge around the bar
        brass *= mix(0.35, 1.0, smoothstep(0.98, 0.7, abs(across)));
        colour = mix(colour, brass, bar);
        alpha = max(alpha, bar);
      }
      // the rail's shadow falls onto the map too
      if (d < 0.0) {
        float shadow = (1.0 - smoothstep(0.0, 8.0, -d)) * 0.5;
        colour = mix(vec3(0.0), colour, bar);
        alpha = max(alpha, shadow);
      }
      gl_FragColor = vec4(colour, alpha);
    }`,
}

/**
 * Colours of the GDI emblem in the main menu (emblem.ts): the eagle a deep, dark gold,
 * the openings glowing lemon-yellow, almost white right of the centre
 */
const COIN_COLOURS = {
  glow: ['#ffffbd', '#ffe65c'],
  eagle: ['#3d2b09', '#614712'],
  edge: '#b08a28',
}
/** Thickness of the coin, in its radii */
const COIN_THICKNESS = 0.08

/**
 * The inside of the glass coin, like the GDI emblem of the main menu: golden glass
 * glowing lemon-yellow (almost white right of the centre), the eagle of
 * public/logos/gdi.svg in it in a deep, dark gold, a dark seam at the edge.
 */
async function coinInside(size: number) {
  const svg = await (await fetch('/logos/gdi.svg')).text()
  const emblem = new Path2D(/\sd="([^"]+)"/.exec(svg)![1]!)
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const ctx = canvas.getContext('2d')!
  const hot = [size * 0.65, size * 0.52] as const
  const glow = ctx.createRadialGradient(...hot, 0, ...hot, size * 0.65)
  glow.addColorStop(0, COIN_COLOURS.glow[0]!)
  glow.addColorStop(1, COIN_COLOURS.glow[1]!)
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, size, size)
  // the eagle (the SVG's filled parts), a little soft as seen through glass
  const ink = ctx.createRadialGradient(...hot, 0, ...hot, size * 0.65)
  ink.addColorStop(0, COIN_COLOURS.eagle[1]!)
  ink.addColorStop(1, COIN_COLOURS.eagle[0]!)
  ctx.save()
  ctx.filter = `blur(${size / 600}px)`
  ctx.translate(size / 2, size / 2)
  ctx.scale(size / 1000, size / 1000)
  ctx.fillStyle = ink
  ctx.fill(emblem, 'evenodd')
  ctx.restore()
  // darker towards the edge, with a thin dark seam
  const edge = ctx.createRadialGradient(size / 2, size / 2, size * 0.3, size / 2, size / 2, size / 2)
  edge.addColorStop(0, 'rgba(0, 0, 0, 0)')
  edge.addColorStop(0.92, 'rgba(40, 25, 0, 0.25)')
  edge.addColorStop(1, 'rgba(40, 25, 0, 0.7)')
  ctx.fillStyle = edge
  ctx.fillRect(0, 0, size, size)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 8
  return texture
}

/** The glare on the glass: a soft, pale reflection over the top left, brighter at its rim */
function glassGlare(size: number) {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, size, size)
  ctx.save()
  ctx.beginPath()
  ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2)
  ctx.clip()
  ctx.filter = `blur(${size / 40}px)`
  // a broad, cloudy reflection on the upper left
  ctx.fillStyle = 'rgba(255, 250, 230, 0.32)'
  ctx.beginPath()
  ctx.ellipse(size * 0.3, size * 0.32, size * 0.32, size * 0.16, -Math.PI / 4, 0, Math.PI * 2)
  ctx.fill()
  // a small, bright spot
  ctx.fillStyle = 'rgba(255, 255, 255, 0.55)'
  ctx.beginPath()
  ctx.ellipse(size * 0.27, size * 0.25, size * 0.08, size * 0.035, -Math.PI / 4, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}

/** Colours of the globe: dark glossy seas, orange-gold land with glowing green coasts, a golden lattice */
const GLOBE_COLOURS = {
  sea: '#060503',
  land: '#d84a08',
  coast: '#3cff3c',
  lattice: 0xc8901c,
}

/**
 * The globe's surface (equirectangular): the land of Natural Earth (public/geo/land.json,
 * outer rings as lon/lat pairs) in orange, its coasts in green. `glow` is the same with
 * only the land's glow and the coasts, for the emissive map.
 */
async function globeTextures(width: number) {
  const { rings } = await (await fetch('/geo/land.json')).json() as { rings: number[][] }
  const height = width / 2
  const draw = (sea: string, land: string, coastWidth: number) => {
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = sea
    ctx.fillRect(0, 0, width, height)
    const path = new Path2D()
    for (const ring of rings) {
      for (let i = 0; i < ring.length; i += 2) {
        const x = (ring[i]! + 180) / 360 * width
        const y = (90 - ring[i + 1]!) / 180 * height
        if (i) path.lineTo(x, y)
        else path.moveTo(x, y)
      }
      path.closePath()
    }
    ctx.fillStyle = land
    ctx.fill(path)
    ctx.strokeStyle = GLOBE_COLOURS.coast
    ctx.lineWidth = coastWidth
    ctx.lineJoin = 'round'
    ctx.stroke(path)
    const texture = new THREE.CanvasTexture(canvas)
    texture.colorSpace = THREE.SRGBColorSpace
    texture.anisotropy = 8
    return texture
  }
  return { map: draw(GLOBE_COLOURS.sea, GLOBE_COLOURS.land, width / 700), glow: draw('#000', '#3a1000', width / 700) }
}

/** A small 3D scene drawn into a square of the screen */
interface Inset {
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  /** Centre and size in screen units */
  at: { x: number, y: number, size: number }
}

export class MapScreenScene {
  private readonly renderer: THREE.WebGLRenderer
  private readonly panelScene = new THREE.Scene()
  private readonly panelCamera = new THREE.Camera()
  private readonly panel: THREE.ShaderMaterial
  private readonly coinScene = new THREE.Scene()
  private readonly coinCamera = new THREE.PerspectiveCamera(22, 1, 0.1, 20)
  private readonly coin = new THREE.Group()
  private readonly globeScene = new THREE.Scene()
  private readonly globeCamera = new THREE.PerspectiveCamera(22, 1, 0.1, 20)
  /** Turns about its own (tilted) axis */
  private readonly globe = new THREE.Group()
  private readonly insets: Inset[]
  private readonly disposables: { dispose: () => void }[] = []
  private frame = 0
  private readonly started = performance.now()
  private last = performance.now()

  static async create(container: HTMLElement, map?: MissionMap) {
    const [inside, earth, world] = await Promise.all([coinInside(1024), globeTextures(2048), map ? WorldMap.load(map) : undefined])
    return new MapScreenScene(container, inside, earth, world)
  }

  private constructor(
    private readonly container: HTMLElement,
    inside: THREE.Texture,
    earth: { map: THREE.Texture, glow: THREE.Texture },
    /** The map of the mission's region, above the plate */
    readonly world?: WorldMap,
  ) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.outputColorSpace = THREE.SRGBColorSpace
    this.renderer.autoClear = false
    container.appendChild(this.renderer.domElement)

    // the plate and the rail
    this.panel = new THREE.ShaderMaterial({
      vertexShader: PanelShader.vertexShader,
      fragmentShader: PanelShader.fragmentShader,
      uniforms: {
        uScreen: { value: new THREE.Vector2(SCREEN_WIDTH, SCREEN_HEIGHT) },
        uRailLow: { value: RAIL_LOW },
        uPixel: { value: 1 },
      },
      transparent: true,
      depthTest: false,
    })
    const quad = new THREE.PlaneGeometry(2, 2)
    this.panelScene.add(new THREE.Mesh(quad, this.panel))

    // the coin: a gold disc with the eagle on both faces, turning about its upright axis
    const pmrem = new THREE.PMREMGenerator(this.renderer)
    const environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
    this.coinScene.environment = environment
    const sun = new THREE.DirectionalLight(0xfff0d0, 2.2)
    sun.position.set(-2, 3, 4)
    this.coinScene.add(sun, new THREE.AmbientLight(0xffffff, 0.25))
    // a coin of golden glass: the glowing inside with the eagle in the middle, the
    // glass faces only add their reflections (additive), the edge is golden glass
    const core = new THREE.CircleGeometry(1, 96)
    const coreMaterial = new THREE.MeshBasicMaterial({ map: inside, side: THREE.DoubleSide })
    const faces = new THREE.CylinderGeometry(1, 1, COIN_THICKNESS, 96, 1)
    faces.rotateX(Math.PI / 2)
    const glare = glassGlare(256)
    const glassMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x000000,
      emissive: 0xffffff,
      emissiveMap: glare,
      roughness: 0.06,
      clearcoat: 1,
      clearcoatRoughness: 0.04,
      envMapIntensity: 1.6,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
    const edge = new THREE.CylinderGeometry(1, 1, COIN_THICKNESS, 96, 1, true)
    edge.rotateX(Math.PI / 2)
    const edgeMaterial = new THREE.MeshStandardMaterial({ color: COIN_COLOURS.edge, emissive: COIN_COLOURS.edge, emissiveIntensity: 0.45, roughness: 0.15, metalness: 0.2 })
    const glassMesh = new THREE.Mesh(faces, glassMaterial)
    glassMesh.renderOrder = 1
    this.coin.add(new THREE.Mesh(core, coreMaterial), new THREE.Mesh(edge, edgeMaterial), glassMesh)
    // a slightly oval coin, like the original's
    this.coin.scale.set(1, 1.1, 1)
    this.coinScene.add(this.coin)
    this.coinCamera.position.set(0, 0, 6.2)
    this.disposables.push(quad, this.panel, core, coreMaterial, inside, faces, glassMaterial, glare, edge, edgeMaterial, environment, pmrem)

    // the globe: glossy, the land glowing orange, a golden lattice around it, its axis tilted
    this.globeScene.environment = environment
    const globeSun = new THREE.DirectionalLight(0xffe070, 2.6)
    globeSun.position.set(-3, 2, 3)
    this.globeScene.add(globeSun, new THREE.AmbientLight(0xffffff, 0.05))
    const sphere = new THREE.SphereGeometry(1, 96, 48)
    // matte, so the seas stay black; the warm light turns the land yellow where it faces it
    const surface = new THREE.MeshLambertMaterial({
      map: earth.map,
      emissive: 0xffffff,
      emissiveMap: earth.glow,
    })
    const lattice = new THREE.WireframeGeometry(new THREE.IcosahedronGeometry(1.012, 5))
    const latticeMaterial = new THREE.LineBasicMaterial({ color: GLOBE_COLOURS.lattice, transparent: true, opacity: 0.3 })
    this.globe.add(new THREE.Mesh(sphere, surface), new THREE.LineSegments(lattice, latticeMaterial))
    const tilt = new THREE.Group()
    tilt.rotation.set(0.35, 0, 0.4)
    tilt.add(this.globe)
    this.globeScene.add(tilt)
    this.globeCamera.position.set(0, 0, 5.6)
    this.disposables.push(sphere, surface, earth.map, earth.glow, lattice, latticeMaterial)

    this.insets = [
      { scene: this.coinScene, camera: this.coinCamera, at: COIN },
      { scene: this.globeScene, camera: this.globeCamera, at: GLOBE },
    ]

    this.resize()
    this.frame = requestAnimationFrame(this.render)
  }

  /** The canvas fills the container; call when it changes size */
  resize() {
    const { clientWidth: width, clientHeight: height } = this.container
    if (!width || !height) return
    this.renderer.setSize(width, height)
    this.panel.uniforms.uPixel!.value = SCREEN_WIDTH / (width * this.renderer.getPixelRatio()) * 1.5
  }

  private readonly render = () => {
    this.frame = requestAnimationFrame(this.render)
    const { clientWidth: width, clientHeight: height } = this.container
    if (!width || !height) return
    const now = performance.now()
    const seconds = (now - this.started) / 1000
    const delta = Math.min(0.1, (now - this.last) / 1000)
    this.last = now
    this.renderer.setViewport(0, 0, width, height)
    this.renderer.setScissorTest(false)
    this.renderer.clear()
    const ratio = this.renderer.getPixelRatio()
    this.world?.render(this.renderer, delta, Math.round(width * ratio), Math.round(height * ratio))
    this.renderer.render(this.panelScene, this.panelCamera)

    this.coin.rotation.y = (seconds / COIN_TURN) * Math.PI * 2
    this.globe.rotation.y = (seconds / GLOBE_TURN) * Math.PI * 2
    // coin and globe each in their own square, measured in screen units
    const unit = width / SCREEN_WIDTH
    for (const { scene, camera, at } of this.insets) {
      const size = at.size * unit * 1.25
      const x = at.x * unit - size / 2
      const y = height - at.y * unit - size / 2 // WebGL: from the bottom
      this.renderer.setViewport(x, y, size, size)
      this.renderer.setScissor(x, y, size, size)
      this.renderer.setScissorTest(true)
      this.renderer.clearDepth()
      this.renderer.render(scene, camera)
    }
    this.renderer.setScissorTest(false)
  }

  dispose() {
    cancelAnimationFrame(this.frame)
    this.world?.dispose()
    for (const item of this.disposables) item.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
