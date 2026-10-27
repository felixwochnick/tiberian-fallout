import * as THREE from 'three'
import { GLTFLoader, type GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { clone as cloneSkinned } from 'three/examples/jsm/utils/SkeletonUtils.js'
import { SCROLL_DIRECTIONS, type CursorKind, type ScrollDirection } from '../input/cursor'
import { findPath, type NavMap } from './pathfinding'
import { Cell, LEVEL_HEIGHT, Terrain, type TerrainOptions } from './terrain'
import { terrainGeometry } from './terrain-mesh'
import { Unit } from './unit'
import { Dropship, type DropshipFlight } from './dropship'
import { CARGO_SLOTS, type CargoSlot, SLOT_STAGES, TIBERIUM_RIPE, type TiberiumCell, type TiberiumKind } from './tiberium'
import { applyHouseColour, MODELS, type Side } from './models'
import { Effects } from './effects'
import { SIGN_FPS, type SignFrames, type SignKind } from './signs'

/**
 * The battlefield in Tiberian Sun's view: a 3D scene seen through an orthographic
 * camera at the original's fixed angle, so map cells show as 2:1 diamonds
 * (48 × 24 pixels at zoom 1). The camera cannot turn; it only scrolls over the map
 * and zooms within limits.
 *
 * World axes: one map cell is one unit and the cells follow the world's X and Z
 * axes, so they show as diamonds. The map itself is laid out the other way round,
 * like in the original: diamond-shaped in cells, so on screen it is a rectangle whose
 * edges run parallel to the camera's scrolling (`width` across, `height` down, both in
 * cell units along the screen axes). The view is kept inside it.
 */

/** Looking down at 30°, so a square cell is drawn half as high as wide. */
const ELEVATION = THREE.MathUtils.degToRad(30)
/** Turned by 45°, so the cell edges run diagonally across the screen. */
const AZIMUTH = THREE.MathUtils.degToRad(45)
/** Screen pixels per world unit at zoom 1: a cell diamond is 48 pixels wide. */
const PIXELS_PER_CELL = 48 / Math.SQRT2

/** Seconds a placeholder building takes to rise out of the ground */
const RISE_SECONDS = 1.2
/** Seconds a sold building without a Build clip takes to sink away */
const SELL_SECONDS = 1.2
/** Blinking of the drawn signs over buildings while the original ones are missing: times a second */
const SIGN_BLINK = 2

/** Seconds between two growth steps of the Tiberium: one cell grows a stage */
const TIBERIUM_GROWTH = 15
/** How far (cells) the green shine of Tiberium reaches over the ground round a field */
const TIBERIUM_SHINE = 4

/** Height (cells) of the placeholder buildings until they have models */
const PLACEHOLDER_HEIGHT: Record<string, number> = {
  GACNST: 0.55, GAPOWR: 0.6, PROC: 0.45, GASILO: 0.35, GACTWR: 0.5, GAWEAP: 0.6, GAVULC: 0.4, GARADR: 0.7,
}

interface Footprint { x: number, z: number, w: number, h: number, owner: Owner, wall?: boolean }

export type Owner = 'player' | 'enemy'

/** Structures that join up with their neighbours (see connectWalls) */
const WALLS = new Set(['GASAND'])

/** A deploying MCV stands in the middle of its foundation, facing the front (+z), like
 * the vehicle at the start of the yard's Build clip (see blender/GACNST.py) */
const DEPLOY_HEADING = 0

export const ZOOM = { min: 0.75, max: 2.5, step: 1.15 }

/**
 * Towards the sun: in front of the map on the left of the screen, high up (55°), so the
 * shadows fall backwards to the right. Along the ground, the screen's right is
 * (cos, 0, -sin) of the azimuth and its down (towards the viewer) (sin, 0, cos).
 */
const SUN_DIRECTION = new THREE.Vector3(Math.sin(AZIMUTH) - Math.cos(AZIMUTH), 0, Math.cos(AZIMUTH) + Math.sin(AZIMUTH))
  .normalize()
  .setY(Math.tan(THREE.MathUtils.degToRad(55)))
  .normalize()
/** How far the sun's shadow camera stands from the ground it looks at */
const SUN_DISTANCE = 60
/** Texels of the shadow map along each side */
const SHADOW_MAP_SIZE = 2048

/** How close (CSS pixels) the cursor has to get to the screen edge to scroll */
const EDGE = 12
/** Scroll speed in screen pixels per second at zoom 1 */
const SCROLL_SPEED = 1100

/**
 * The light of the map: gloomy like in Tiberian Sun, a pale, weak sun and little light
 * from the sky. The ground is not lit (its shader writes display colours), so it is
 * darkened and greyed by GROUND_LIGHT and GROUND_GREY to match.
 */
const SUN_LIGHT = { colour: 0xffeccc, intensity: 1.6 }
const SKY_LIGHT = { sky: 0x9aa6b8, ground: 0x3a342a, intensity: 0.55 }
const GROUND_LIGHT = 0.68
const GROUND_GREY = 0.25

const NOISE = /* glsl */ `
  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
  }
  float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
  }
  float fbm(vec2 p) {
    return noise(p) * 0.5 + noise(p * 2.03) * 0.3 + noise(p * 4.1) * 0.2;
  }`

/**
/**
 * Plain temperate ground: dry ochre earth like in Tiberian Sun (no cell grid, like the
 * original). Tiberium colours it, like in help/tiberium/: `tibMap` holds one texel per
 * cell over the rectangle `tibRect` (x, z of its corner, its size in cells), red = the
 * cell's growth stage / 3, green = the shine of the Tiberium round it (TIBERIUM_SHINE
 * cells far, see Battlefield.shineTiberium), blue = how much of that shine comes from
 * blue Tiberium (it tints the ground bluish instead of green). Filtered between the cells and frayed by
 * noise, the shine colours the ground olive green far round a field (keeping its grain,
 * so it does not look like fog), greener under the crystals, where it also glows a
 * little, pulsing slowly (`time` in seconds).
 */
const GroundShader = {
  vertexShader: /* glsl */ `
    attribute float shade;
    attribute float rock;
    attribute float ramp;
    varying float vRock;
    varying float vRamp;
    varying vec2 vCell;
    varying vec3 vNormal;
    varying float vHeight;
    varying float vShade;
    void main() {
      vec4 world = modelMatrix * vec4(position, 1.0);
      vCell = world.xz;
      vHeight = world.y;
      vShade = shade;
      vRock = rock;
      vRamp = ramp;
      vNormal = normalize(mat3(modelMatrix) * normal);
      gl_Position = projectionMatrix * viewMatrix * world;
    }`,
  fragmentShader: /* glsl */ `
    varying vec2 vCell;
    varying vec3 vNormal;
    varying float vHeight;
    varying float vShade;
    varying float vRock;
    varying float vRamp;
    uniform sampler2D tibMap;
    uniform vec4 tibRect;
    uniform float time;
    uniform vec3 sun;
    uniform vec4 area;
    uniform vec2 screenRight;
    uniform vec2 screenDown;
    ${NOISE}
    void main() {
      vec2 c = vCell;
      // only the map (a rectangle along the screen axes)
      float u = dot(c, screenRight);
      float v = dot(c, screenDown);
      if (u < area.x || u > area.y || v < area.z || v > area.w) discard;
      // dry ochre earth like Tiberian Sun's temperate ground: large lighter and darker
      // patches, fine sandy grain, scattered pebbles and a hint of dry grass here and there
      float patches = fbm(c * 0.09);
      float mottle = fbm(c * 0.45 + 7.0);
      float grain = fbm(c * 6.0 + 3.0);
      vec3 earth = mix(vec3(0.41, 0.28, 0.15), vec3(0.57, 0.42, 0.24), patches);
      earth = mix(earth, vec3(0.36, 0.26, 0.15), smoothstep(0.55, 0.75, mottle) * 0.6);
      // dry grass / olive tint in a few places
      float grass = smoothstep(0.62, 0.78, fbm(c * 0.07 + 41.0));
      earth = mix(earth, vec3(0.42, 0.4, 0.22), grass * 0.55);
      earth *= 0.88 + 0.24 * grain;
      // pebbles: tiny dark specks with a lit edge
      float pebble = smoothstep(0.86, 0.9, noise(c * 9.0 + 17.0));
      earth = mix(earth, vec3(0.3, 0.23, 0.15), pebble * 0.7);
      float glint = smoothstep(0.9, 0.93, noise(c * 9.0 + 17.3));
      earth += vec3(0.08, 0.07, 0.05) * glint;
      // Tiberium: olive green far round a field, greener under the crystals
      vec2 warp = vec2(fbm(c * 0.9 + 3.1), fbm(c * 0.9 + 8.7)) - 0.5;
      vec4 tibCell = texture2D(tibMap, (c + warp * 0.9 - tibRect.xy) / tibRect.zw);
      float tib = tibCell.r;
      float shine = tibCell.g;
      float blue = tibCell.b;
      // colour the earth, not cover it: its grain, patches and pebbles stay as they are
      float tint = smoothstep(0.04, 0.55, shine + (fbm(c * 1.1 + 2.0) - 0.5) * 0.18);
      float lum = dot(earth, vec3(0.3, 0.55, 0.15));
      earth = mix(earth, lum * mix(vec3(0.92, 1.12, 0.42), vec3(0.66, 0.86, 1.2), blue), tint * 0.85);
      float cover = smoothstep(0.12, 0.3, tib + (fbm(c * 2.3 + 5.0) - 0.5) * 0.2);
      earth = mix(earth, lum * mix(vec3(0.7, 1.05, 0.36), vec3(0.5, 0.8, 1.25), blue), cover * 0.6);
      // grit of broken crystals
      float speck = smoothstep(0.87, 0.91, noise(c * 13.0 + 29.0)) * cover;
      earth = mix(earth, mix(vec3(0.3, 0.72, 0.24), vec3(0.25, 0.5, 0.9), blue), speck * 0.8);
      // round the cliffs: stony ground, grey gravel and broken rock, with a ragged edge
      float stony = smoothstep(0.3, 0.7, vRock + (fbm(c * 1.6 + 13.0) - 0.5) * 0.8);
      vec3 gravel = mix(vec3(0.34, 0.32, 0.29), vec3(0.56, 0.53, 0.48), fbm(c * 4.0 + 3.0));
      gravel *= 0.8 + 0.4 * grain;
      gravel = mix(gravel, vec3(0.22, 0.21, 0.2), smoothstep(0.8, 0.86, noise(c * 7.0 + 5.0)) * 0.8);
      earth = mix(earth, gravel, stony * 0.85);
      // cliffs: grey rock in upright columns with dark clefts between them (like
      // Tiberian Sun's), lighter on the rim, darker and browner towards the scree at the foot
      vec3 n = normalize(vNormal);
      float steep = 1.0 - smoothstep(0.55, 0.85, n.y);
      float along = abs(n.x) > abs(n.z) ? c.y : c.x;
      float columns = fbm(vec2(along * 5.0, vHeight * 0.6));
      float cleft = smoothstep(0.42, 0.3, abs(fbm(vec2(along * 2.6 + 11.0, vHeight * 0.35)) - 0.5) * 3.0);
      vec3 rock = mix(vec3(0.42, 0.41, 0.39), vec3(0.7, 0.69, 0.66), columns);
      rock *= 0.85 + 0.25 * fbm(vec2(along * 14.0, vHeight * 3.0));
      rock *= 1.0 - cleft * 0.45;
      float rise = fract(vHeight / ${LEVEL_HEIGHT.toFixed(2)} + 0.001);
      rock *= mix(0.7, 1.05, smoothstep(0.0, 0.9, rise));
      // scree: grey-brown gravel at the foot, ragged where it meets the rock
      vec3 scree = mix(vec3(0.27, 0.24, 0.2), vec3(0.4, 0.36, 0.3), fbm(c * 7.0 + vHeight * 9.0));
      float screeLine = 0.12 + 0.14 * fbm(vec2(along * 3.0, 1.0));
      rock = mix(rock, scree, smoothstep(screeLine + 0.04, screeLine - 0.04, rise) * 0.75);
      earth = mix(earth, rock, steep);
      // lit by the sun like the models: flat ground as before, slopes facing it brighter, the others darker
      vec3 l = normalize(sun);
      // on ramps and slopes the light picks out lumps and hollows of the rock (bumps in
      // the normal from the noise's slope), large ones and fine grit
      float relief = max(steep, smoothstep(0.15, 0.6, vRamp)) + vRock * 0.3;
      vec2 e = vec2(0.03, 0.0);
      vec2 coarse = vec2(fbm(c * 2.2 + e.xy) - fbm(c * 2.2 - e.xy), fbm(c * 2.2 + e.yx) - fbm(c * 2.2 - e.yx));
      vec2 fine = vec2(noise(c * 9.0 + e.xy * 3.0) - noise(c * 9.0 - e.xy * 3.0), noise(c * 9.0 + e.yx * 3.0) - noise(c * 9.0 - e.yx * 3.0));
      vec2 tilt = (coarse * 9.0 + fine * 2.5) * relief;
      vec3 bumped = normalize(n - vec3(tilt.x, 0.0, tilt.y));
      float lit = (0.45 + 0.75 * max(dot(bumped, l), 0.0)) / (0.45 + 0.75 * l.y);
      // hollows hold shadow
      lit *= 1.0 - 0.25 * relief * smoothstep(0.5, 0.25, fbm(c * 2.2));
      // ramps: rough broken rock and stony earth, ridges and clefts running down the
      // slope, ragged where they meet the ground round them
      vec2 down = normalize(n.xz + vec2(1e-4));
      vec2 slope = vec2(dot(c, down), dot(c, vec2(-down.y, down.x)));
      float ridges = fbm(vec2(slope.x * 1.2, slope.y * 4.5) + 31.0);
      vec3 rampRock = mix(vec3(0.28, 0.26, 0.23), vec3(0.55, 0.52, 0.47), ridges);
      rampRock = mix(rampRock, vec3(0.45, 0.36, 0.25), smoothstep(0.45, 0.7, fbm(c * 1.3 + 9.0)) * 0.5);
      rampRock *= 0.7 + 0.5 * fbm(c * 6.0 + 4.0);
      rampRock *= 1.0 - smoothstep(0.62, 0.7, fbm(vec2(slope.x * 2.0, slope.y * 7.0) + 2.0)) * 0.45;
      // only where it slopes: a ramp's four steps (and a terrace's slope) show as bands
      // of broken rock with earth between them, where one step levels out into the next
      float sloping = smoothstep(0.995, 0.94, n.y);
      float onRamp = smoothstep(0.15, 0.45, vRamp + (fbm(c * 2.2 + 21.0) - 0.5) * 0.4) * sloping;
      earth = mix(earth, rampRock, onRamp * 0.9);
      earth *= lit * vShade;
      // the gloomy light of the map: darker and greyer
      earth = mix(earth, vec3(dot(earth, vec3(0.3, 0.55, 0.15))), ${GROUND_GREY.toFixed(2)}) * ${GROUND_LIGHT.toFixed(2)};
      // under the crystals the ground glows a little, pulsing slowly out of step
      float pulse = 0.5 + 0.5 * sin(time * 3.14159 + fbm(c * 0.5) * 6.0);
      earth *= 1.0 + mix(vec3(0.02, 0.12, 0.02), vec3(0.02, 0.06, 0.14), blue) * cover * pulse;
      gl_FragColor = vec4(earth, 1.0);
    }`,
}

/** How much of a unit's size (half its longest side) keeps buildings off the cells round it */
const UNIT_BLOCK_SHARE = 0.7

/** How far (cells) openSpot looks for a cell to stand on */
const OPEN_SEARCH = 6

/**
 * The postures of the vehicles that dig (see Unit.change): the clip into it, the
 * posture's name (its idle and fire clips) and the clip out of it
 */
const POSTURES = {
  /** The Tick Tank dug in, nose down, its turret out of its tail */
  dig: { in: 'Deploy', posture: 'Deployed', out: 'Undeploy' },
  /** The subterranean APC under the ground */
  tunnel: { in: 'Burrow', posture: 'Underground', out: 'Surface' },
} as const
/** Units that dig in where they stand */
const DIGGERS = new Set(['TTNK'])
/** Units that go under the ground to get somewhere */
const TUNNELLERS = new Set(['SAPC'])
/** Farther than this (cells) the subterranean APC goes under the ground; nearer it drives */
const TUNNEL_MIN = 8
/** How many soldiers the transports carry (Passengers=) */
const TRANSPORTS: Record<string, number> = { SAPC: 5 }
/** A soldier this near (cells) to its transport gets in */
const BOARD_REACH = 0.8
/** How far from the transport (cells) the soldiers get out */
const UNLOAD_DISTANCE = 0.9
/** Under the ground it is this much faster than on it */
const TUNNEL_SPEED = 1.5

export class Battlefield {
  private readonly renderer: THREE.WebGLRenderer
  private readonly scene = new THREE.Scene()
  /** Fire, smoke, dust, sparks … (particles), for the fighting, the harvesters and the aircraft */
  readonly effects = new Effects(this.scene)
  /** The dropships' engine nodes, found once per ship: jets out of the nozzles and the lift vents */
  private readonly engines = new WeakMap<THREE.Object3D, { plumes: THREE.Object3D[], lifts: THREE.Object3D[], fires: THREE.Object3D[], blast?: THREE.Object3D, blasted: boolean }>()
  private readonly camera = new THREE.OrthographicCamera()
  /** From the looked-at ground point towards the camera */
  private readonly offset = new THREE.Vector3(
    Math.cos(ELEVATION) * Math.sin(AZIMUTH),
    Math.sin(ELEVATION),
    Math.cos(ELEVATION) * Math.cos(AZIMUTH),
  ).multiplyScalar(100)
  /** Ground directions that move along the screen's x and y axes (y pointing down) */
  private readonly screenRight = new THREE.Vector3(Math.cos(AZIMUTH), 0, -Math.sin(AZIMUTH))
  private readonly screenDown = new THREE.Vector3(Math.sin(AZIMUTH), 0, Math.cos(AZIMUTH))
  /** Ground point in the middle of the screen */
  readonly target = new THREE.Vector3()
  /** The same along screenRight (u) and screenDown (v) */
  private u = 0
  private v = 0
  /** The map diamond's bounding box in (u, v), as shown by the radar */
  private readonly bounds: { u: [number, number], v: [number, number] }
  zoom = 1.5
  private readonly disposables: { dispose(): void }[] = []
  /** Animations of the buildings (construction, flags, lights) */
  private readonly mixers: THREE.AnimationMixer[] = []
  private lastFrame = performance.now()
  readonly units: Unit[] = []
  /** Dropships in the air or on the ground */
  readonly aircraft: Dropship[] = []
  /** MCVs on their way to deploy: they drive onto the middle of their foundation and turn first */
  private readonly deploying: { unit: Unit, x: number, z: number, url: string, houseColour: number, footprint: Footprint, resolve: (yard?: THREE.Object3D) => void }[] = []
  /** Unit models, loaded once and cloned for every unit */
  private readonly unitModels = new Map<string, Promise<GLTF>>()
  /** Buildings and units that can be selected, for picking with the mouse */
  private readonly selectables: THREE.Object3D[] = []
  private readonly raycaster = new THREE.Raycaster()
  /** Foundations of the buildings on the map, in cells */
  private readonly footprints: Footprint[] = []
  /** Buildings on the map by RULES.INI id */
  private readonly structures = new Map<string, THREE.Object3D[]>()
  /** Placeholder buildings still rising out of the ground */
  private readonly rising: { object: THREE.Object3D, time: number }[] = []
  /** Sold buildings folding up: their Build clip runs backwards (or they sink, `shrink`), then they are gone */
  private readonly unbuilding: { object: THREE.Object3D, time: number, seconds: number, shrink: boolean }[] = []
  /** Tiberium on the map by cell ("x,z"): its stage and its model (TIB.glb, one variant) */
  private readonly tiberium = new Map<string, TiberiumCell & { object: THREE.Object3D }>()
  private tiberiumTimer = 0
  /** Seconds for the pulsing shine of the Tiberium on the ground (see GroundShader) */
  private readonly groundTime: THREE.IUniform<number>
  /** The cells' Tiberium stages for the ground shader (see GroundShader) */
  private readonly tiberiumGround: { texture: THREE.DataTexture, x: number, z: number, w: number, h: number }
  /** Preview of a structure being placed: its cells, green where it may go, red otherwise */
  private placement?: {
    w: number, h: number, adjacent: number, preview: THREE.Group,
    materials: { free: THREE.MeshBasicMaterial, blocked: THREE.MeshBasicMaterial },
    cell?: [number, number], valid: boolean,
  }

  /** Everything selected: one building, or one or more units */
  selection: THREE.Object3D[] = []
  /** The selected object if exactly one is selected */
  get selected() {
    return this.selection.length === 1 ? this.selection[0] : undefined
  }

  /** Rubber band while dragging a selection box (client pixels) */
  private band?: { x0: number, y0: number, x1: number, y1: number }
  private readonly groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
  /** The ground's height levels, cliffs and ramps (flat until shapeTerrain) */
  terrain: Terrain
  /** The ground's mesh and the see-through layer over it that takes the shadows */
  private readonly ground: THREE.Mesh
  private readonly shadowLayer: THREE.Mesh
  /** The sun: lights the models and casts their shadows, round the part of the map in view */
  private readonly sun = new THREE.DirectionalLight(SUN_LIGHT.colour, SUN_LIGHT.intensity)

  constructor(private readonly container: HTMLElement, readonly width: number, readonly height: number) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.setClearColor(0x000000)
    // the ground shader writes display colours itself; the models are lit PBR in sRGB
    this.renderer.outputColorSpace = THREE.SRGBColorSpace
    this.renderer.shadowMap.enabled = true
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap
    container.appendChild(this.renderer.domElement)

    // the map: a rectangle along the screen axes (u right, v down), lying diagonally
    // over the cell grid; the ground is made of its cells (see shapeTerrain)
    this.bounds = { u: [0, width], v: [0, height] }
    // one texel per cell over the cells the ground covers (and a free cell round them)
    const corners = [[0, 0], [width, 0], [0, height], [width, height]].map(([u, v]) => this.mapPoint(u!, v!))
    const x0 = Math.floor(Math.min(...corners.map(p => p.x))) - 1
    const z0 = Math.floor(Math.min(...corners.map(p => p.z))) - 1
    const w = Math.ceil(Math.max(...corners.map(p => p.x))) + 1 - x0
    const h = Math.ceil(Math.max(...corners.map(p => p.z))) + 1 - z0
    const texture = new THREE.DataTexture(new Uint8Array(w * h * 4), w, h)
    texture.magFilter = texture.minFilter = THREE.LinearFilter
    texture.needsUpdate = true
    this.tiberiumGround = { texture, x: x0, z: z0, w, h }
    this.terrain = new Terrain(x0, z0, w, h)
    const material = new THREE.ShaderMaterial({
      ...GroundShader,
      uniforms: {
        tibMap: { value: texture },
        tibRect: { value: new THREE.Vector4(x0, z0, w, h) },
        time: { value: 0 },
        sun: { value: SUN_DIRECTION.clone() },
        area: { value: new THREE.Vector4(0, width, 0, height) },
        screenRight: { value: new THREE.Vector2(this.screenRight.x, this.screenRight.z) },
        screenDown: { value: new THREE.Vector2(this.screenDown.x, this.screenDown.z) },
      },
    })
    this.groundTime = material.uniforms.time!
    this.disposables.push(material, texture)
    this.ground = new THREE.Mesh(this.groundGeometry(), material)
    // the cliffs cast their shadows over the ground below them
    this.ground.castShadow = true
    this.scene.add(this.ground)
    // the ground shader knows no light: the shadows lie on a see-through layer over it
    const shadowMaterial = new THREE.ShadowMaterial({ opacity: 0.38, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 })
    this.disposables.push(shadowMaterial)
    this.shadowLayer = new THREE.Mesh(this.ground.geometry, shadowMaterial)
    this.shadowLayer.receiveShadow = true
    this.scene.add(this.shadowLayer)
    this.effects.heightAt = (x, z) => this.heightAt(x, z)

    // light for the models: the sun from the front left, a sky fill and shadows on the ground
    const sun = this.sun
    sun.castShadow = true
    sun.shadow.mapSize.set(SHADOW_MAP_SIZE, SHADOW_MAP_SIZE)
    sun.shadow.bias = -0.0004
    sun.shadow.normalBias = 0.02
    sun.shadow.radius = 3
    this.scene.add(sun, sun.target, new THREE.HemisphereLight(SKY_LIGHT.sky, SKY_LIGHT.ground, SKY_LIGHT.intensity))
    this.overlayScene.add(this.selectionFrame)
    this.disposables.push(this.selectionFrame.geometry, this.selectionFrame.material as THREE.Material)
    this.u = (this.bounds.u[0] + this.bounds.u[1]) / 2
    this.v = (this.bounds.v[0] + this.bounds.v[1]) / 2
    this.resize()
  }

  /** The ground's mesh for the terrain: the cells on the map and a cell round it */
  private groundGeometry() {
    const [u0, u1] = this.bounds.u
    const [v0, v1] = this.bounds.v
    return terrainGeometry(this.terrain, (x, z) => {
      const centre = new THREE.Vector3(x + 0.5, 0, z + 0.5)
      const u = centre.dot(this.screenRight)
      const v = centre.dot(this.screenDown)
      return u > u0 - 1.5 && u < u1 + 1.5 && v > v0 - 1.5 && v < v1 + 1.5
    })
  }

  /**
   * Shapes the ground with plateaus, cliffs and ramps (Terrain.generate); the flat
   * zones (cells) stay level. Call it before anything is put on the map.
   */
  shapeTerrain(options: TerrainOptions) {
    const { x, z, w, h } = this.tiberiumGround
    // only the ways on the map count: every part of it has to be reached on it
    this.terrain = Terrain.generate(x, z, w, h, { inside: (cx, cz) => this.onMap(cx, cz), ...options })
    const geometry = this.groundGeometry()
    this.ground.geometry.dispose()
    this.ground.geometry = geometry
    this.shadowLayer.geometry = geometry
    void this.placeCliffs()
  }

  /** The rock on the cliffs (CLIFF.glb), one instanced mesh per piece */
  private cliffRock: THREE.InstancedMesh[] = []

  /**
   * Puts the rock of CLIFF.glb on the rock cells of the terrain, one piece a cell,
   * picked by which of its corners are up: Straight (two side by side), Cut (three:
   * the cliff runs across the cell), Foot (one: below the end of a cut); two opposite
   * corners up get a Foot each. Variants by position. The cells beside the ramps, whose
   * corners lie between levels, get a Straight as high as they climb, facing downhill,
   * so the rock of the cliff runs down the ramp's sides.
   */
  private async placeCliffs() {
    for (const mesh of this.cliffRock) {
      mesh.removeFromParent()
      mesh.dispose()
    }
    this.cliffRock = []
    const terrain = this.terrain
    const gltf = await this.loadModel(MODELS.CLIFF!, 0)
    if (terrain !== this.terrain) return
    const pieces = new Map<string, THREE.Matrix4[]>()
    const variants: Record<string, number> = { Straight: 4, Cut: 3, Foot: 3 }
    /** A piece on the cell, its own corner `from` turned to the cell's corner `to` (quadrants as ±1, ±1) */
    const putPiece = (kind: string, x: number, z: number, level: number, height: number, from: [number, number], to: [number, number]) => {
      const n = variants[kind]!
      const name = `${kind}${(((x * 7 + z * 13) % n) + n) % n}`
      const angle = Math.atan2(to[0], to[1]) - Math.atan2(from[0], from[1])
      const matrix = new THREE.Matrix4().makeRotationY(angle).multiply(new THREE.Matrix4().makeScale(1, height, 1))
        .setPosition(x + 0.5, level * LEVEL_HEIGHT, z + 0.5)
      pieces.set(name, [...pieces.get(name) ?? [], matrix])
    }
    const [u0, u1] = this.bounds.u
    const [v0, v1] = this.bounds.v
    const onMap = (x: number, z: number) => {
      const point = new THREE.Vector3(x, 0, z)
      const u = point.dot(this.screenRight)
      const v = point.dot(this.screenDown)
      return u > u0 - 1 && u < u1 + 1 && v > v0 - 1 && v < v1 + 1
    }
    /** The corners a, b, c, d of a cell as quadrants round its middle */
    const QUADRANTS: [number, number][] = [[-1, -1], [1, -1], [-1, 1], [1, 1]]
    const { x0, z0, width, depth } = terrain
    for (let z = z0 - 1; z <= z0 + depth; z++) {
      for (let x = x0 - 1; x <= x0 + width; x++) {
        if (terrain.cell(x, z) !== Cell.Rock || !onMap(x + 0.5, z + 0.5)) continue
        const levels = terrain.corners(x, z)
        const mains = [terrain.main(x, z), terrain.main(x + 1, z), terrain.main(x, z + 1), terrain.main(x + 1, z + 1)]
        if (mains.some(l => Math.abs(l - Math.round(l)) > 1e-6)) {
          // beside a ramp: a lower bank of rock, as high as the cell climbs, facing downhill
          const [a, b, c, d] = levels
          const span = Math.max(...levels) - Math.min(...levels)
          const gx = (b + d - a - c) / 2
          const gz = (c + d - a - b) / 2
          if (span < 0.9 || Math.hypot(gx, gz) < 1e-3) continue
          const n = variants.Straight!
          const matrix = new THREE.Matrix4().makeRotationY(Math.atan2(-gx, -gz))
            .multiply(new THREE.Matrix4().makeScale(1, span, 1))
            .setPosition(x + 0.5, Math.min(...levels) * LEVEL_HEIGHT, z + 0.5)
          const name = `Straight${(((x * 7 + z * 13) % n) + n) % n}`
          pieces.set(name, [...pieces.get(name) ?? [], matrix])
          continue
        }
        // which corners are up by their levels; how high the rock stands by their
        // terraces: from the lowest corner below to the middle of the ones up
        const lowMain = Math.min(...mains)
        const up = mains.map(l => l > lowMain)
        const count = up.filter(Boolean).length
        if (count === 0) continue
        const low = Math.min(...levels.filter((_, i) => !up[i]))
        const top = levels.filter((_, i) => up[i]).reduce((sum, l) => sum + l, 0) / count
        const put = (kind: string, from: [number, number], to: [number, number]) => putPiece(kind, x, z, low, top - low, from, to)
        if (count === 2 && up[0] === up[3]) {
          // two opposite corners up
          up.forEach((u, i) => u && put('Foot', [-1, -1], QUADRANTS[i]!))
        }
        else if (count === 2) {
          // downhill: from the side the two corners up are on to the other
          const [i, j] = up.flatMap((u, k) => u ? [k] : [])
          const [qx, qz] = [(QUADRANTS[i!]![0] + QUADRANTS[j!]![0]) / 2, (QUADRANTS[i!]![1] + QUADRANTS[j!]![1]) / 2]
          put('Straight', [0, 1], [-qx, -qz])
        }
        else if (count === 3) {
          put('Cut', [1, 1], QUADRANTS[up.indexOf(false)]!)
        }
        else {
          put('Foot', [-1, -1], QUADRANTS[up.indexOf(true)]!)
        }
      }
    }
    for (const [name, matrices] of pieces) {
      const source = gltf.scene.getObjectByName(name) as THREE.Mesh | undefined
      if (!source?.isMesh) continue
      const mesh = new THREE.InstancedMesh(source.geometry, source.material, matrices.length)
      matrices.forEach((m, i) => mesh.setMatrixAt(i, m))
      mesh.castShadow = true
      mesh.receiveShadow = true
      this.scene.add(mesh)
      this.cliffRock.push(mesh)
    }
  }

  /** Height of the ground at a point (cells) */
  heightAt(x: number, z: number) {
    return this.terrain.heightAt(x, z)
  }

  /** Where a ray from the camera meets the ground: on the plane at the height found there, refined a few times */
  private pickGround(ray: THREE.Ray) {
    let height = 0
    let point: THREE.Vector3 | null = null
    for (let i = 0; i < 6; i++) {
      this.groundPlane.constant = -height
      point = ray.intersectPlane(this.groundPlane, new THREE.Vector3())
      if (!point) return undefined
      const next = this.heightAt(point.x, point.z)
      if (Math.abs(next - height) < 1e-3) break
      height = next
    }
    return point ?? undefined
  }

  resize() {
    const w = this.container.clientWidth
    const h = this.container.clientHeight
    if (!w || !h) return
    this.renderer.setSize(w, h)
    this.updateCamera()
  }

  /** Half the visible ground in (u, v) */
  private halfView() {
    const scale = PIXELS_PER_CELL * this.zoom
    return [this.container.clientWidth / scale / 2, this.container.clientHeight / scale / 2 / Math.sin(ELEVATION)] as const
  }

  /** Keeps the view inside the map; returns whether u and v had to be stopped. */
  private clampView() {
    const [halfU, halfV] = this.halfView()
    const clamp = (value: number, [min, max]: [number, number], half: number) =>
      min + half > max - half ? (min + max) / 2 : THREE.MathUtils.clamp(value, min + half, max - half)
    const u = clamp(this.u, this.bounds.u, halfU)
    const v = clamp(this.v, this.bounds.v, halfV)
    const stopped = { u: u !== this.u, v: v !== this.v }
    this.u = u
    this.v = v
    return stopped
  }

  private updateCamera() {
    this.clampView()
    this.target.copy(this.screenRight).multiplyScalar(this.u).addScaledVector(this.screenDown, this.v)
    const scale = PIXELS_PER_CELL * this.zoom
    const w = this.container.clientWidth / scale / 2
    const h = this.container.clientHeight / scale / 2
    this.camera.left = -w
    this.camera.right = w
    this.camera.top = h
    this.camera.bottom = -h
    this.camera.near = 1
    this.camera.far = 400
    this.camera.updateProjectionMatrix()
    this.camera.position.copy(this.target).add(this.offset)
    this.camera.lookAt(this.target)
    this.updateSun()
  }

  /**
   * The sun's shadows cover the ground in view, with room round it for tall buildings
   * and dropships just outside. Its middle moves in whole texels of the shadow map, so
   * shadow edges do not shimmer while scrolling.
   */
  private updateSun() {
    const [halfU, halfV] = this.halfView()
    const radius = Math.hypot(halfU, halfV) + 4
    const shadow = this.sun.shadow.camera
    shadow.left = -radius
    shadow.right = radius
    shadow.top = radius
    shadow.bottom = -radius
    shadow.near = 1
    shadow.far = SUN_DISTANCE + 40
    shadow.updateProjectionMatrix()
    // the view's middle in the light's own axes, rounded to texels
    const texel = 2 * radius / SHADOW_MAP_SIZE
    const right = new THREE.Vector3().crossVectors(SUN_DIRECTION, new THREE.Vector3(0, 1, 0)).normalize()
    const up = new THREE.Vector3().crossVectors(right, SUN_DIRECTION)
    const centre = new THREE.Vector3()
      .addScaledVector(right, Math.round(this.target.dot(right) / texel) * texel)
      .addScaledVector(up, Math.round(this.target.dot(up) / texel) * texel)
      .addScaledVector(SUN_DIRECTION, this.target.dot(SUN_DIRECTION))
    this.sun.target.position.copy(centre)
    this.sun.position.copy(centre).addScaledVector(SUN_DIRECTION, SUN_DISTANCE)
    this.sun.target.updateMatrixWorld()
  }

  /** Meshes of a model cast shadows and take them, except glowing halos */
  private castShadows(object: THREE.Object3D) {
    object.traverse((node) => {
      const mesh = node as THREE.Mesh
      if (!mesh.isMesh) return
      const glows = ([mesh.material].flat() as THREE.Material[]).some(m => m.name.startsWith('Glow') || m.blending === THREE.AdditiveBlending)
      mesh.castShadow = !glows
      mesh.receiveShadow = !glows
    })
  }

  /** Zooms in (positive steps) or out, within the limits. */
  zoomBy(steps: number) {
    this.zoom = THREE.MathUtils.clamp(this.zoom * ZOOM.step ** steps, ZOOM.min, ZOOM.max)
    this.updateCamera()
  }

  /**
   * Scrolls by a screen distance; stops at the map edge. Returns for each screen
   * axis whether it could move (false = blocked by the edge).
   */
  scrollBy(dx: number, dy: number) {
    const scale = PIXELS_PER_CELL * this.zoom
    this.u += dx / scale
    // a ground step towards the screen's top or bottom is drawn shortened by sin(elevation)
    this.v += dy / scale / Math.sin(ELEVATION)
    const stopped = this.clampView()
    this.updateCamera()
    return { x: !dx || !stopped.u, y: !dy || !stopped.v }
  }

  /**
   * Scrolls when the cursor is at a screen edge and returns the cursor to show:
   * a green scroll arrow, a crossed-out one at the map edge, or the normal arrow.
   */
  edgeScroll(pointer: { x: number, y: number, inside: boolean }, seconds: number): CursorKind {
    if (!pointer.inside) return 'default'
    // the edges of the screen, not of the view (the HUD lies along them)
    const w = window.innerWidth
    const h = window.innerHeight
    const dx = pointer.x <= EDGE ? -1 : pointer.x >= w - 1 - EDGE ? 1 : 0
    const dy = pointer.y <= EDGE ? -1 : pointer.y >= h - 1 - EDGE ? 1 : 0
    if (!dx && !dy) return 'default'
    const distance = SCROLL_SPEED * seconds / Math.hypot(dx, dy)
    const moved = this.scrollBy(dx * distance, dy * distance)
    const direction = (Object.keys(SCROLL_DIRECTIONS) as ScrollDirection[])
      .find(d => SCROLL_DIRECTIONS[d][0] === dx && SCROLL_DIRECTIONS[d][1] === dy)!
    return moved.x && moved.y ? `scroll-${direction}` : `blocked-${direction}`
  }

  /**
   * Draws a frame; `frozen` (the game is paused): everything stands still, only the
   * picture is drawn. `speed` is the game speed: units, animations and effects run
   * that much faster or slower.
   */
  render(frozen = false, speed = 1) {
    const now = performance.now()
    const seconds = frozen ? 0 : Math.min(0.1, (now - this.lastFrame) / 1000) * speed // no jump after a stall
    this.lastFrame = now
    for (const mixer of this.mixers) mixer.update(seconds)
    for (const item of this.rising) {
      item.time = Math.min(1, item.time + seconds / RISE_SECONDS)
      item.object.scale.y = Math.max(0.02, 1 - (1 - item.time) ** 3)
    }
    this.rising.splice(0, this.rising.length, ...this.rising.filter(item => item.time < 1))
    this.updateUnbuilding(seconds)
    for (const unit of this.units) {
      unit.update(seconds)
      // on the ground, up and down the ramps (unless it is up on a refinery's pad)
      const at = unit.object.position
      if (!unit.object.userData.offGround) at.y = this.heightAt(at.x, at.z)
      // earth thrown up while a vehicle digs in or comes out of the ground
      if (seconds > 0 && unit.changingPosture && unit.object.visible) this.effects.dig(at)
      // on to the next waypoint
      const waypoints = unit.object.userData.waypoints as THREE.Vector3[] | undefined
      if (seconds > 0 && !unit.walking && waypoints?.length && !unit.object.userData.dead) this.walk(unit, waypoints.shift()!)
    }
    for (const ship of [...this.aircraft]) {
      ship.update(seconds)
      if (seconds > 0) this.engineEffects(ship.object, seconds)
    }
    this.updateDeploying(seconds)
    this.updateTunnels(seconds)
    this.updateBoarding()
    this.updateDeliveries()
    this.growTiberium(seconds)
    this.groundTime.value = (this.groundTime.value + seconds) % 1000
    this.effects.update(seconds, this.renderer.getDrawingBufferSize(new THREE.Vector2()).y / (this.camera.top - this.camera.bottom))
    this.renderer.render(this.scene, this.camera)
    this.drawSelection()
    if (this.selectionFrame.visible || this.signsShown) {
      this.renderer.autoClear = false
      this.renderer.render(this.overlayScene, this.overlayCamera)
      this.renderer.autoClear = true
    }
  }

  /** Width / height of the scrollable area as drawn on screen (for the radar). */
  get areaAspect() {
    const [u0, u1] = this.bounds.u
    const [v0, v1] = this.bounds.v
    return (u1 - u0) / ((v1 - v0) * Math.sin(ELEVATION))
  }

  /** The visible part of the scrollable area, as fractions of it (x right, y down). */
  viewRect() {
    const [halfU, halfV] = this.halfView()
    const [u0, u1] = this.bounds.u
    const [v0, v1] = this.bounds.v
    return {
      x: (this.u - halfU - u0) / (u1 - u0),
      y: (this.v - halfV - v0) / (v1 - v0),
      width: (2 * halfU) / (u1 - u0),
      height: (2 * halfV) / (v1 - v0),
    }
  }

  /** Scrolls so the view is centred on a point of the ground (world). */
  lookAt(point: THREE.Vector3) {
    this.u = point.dot(this.screenRight)
    this.v = point.dot(this.screenDown)
    this.updateCamera()
  }

  /** Selects all of the player's units that can be picked with a box (not harvesters). */
  selectAllUnits() {
    this.selection = this.selectables.filter(Battlefield.boxSelectable)
    return this.selection.length
  }

  /** Scrolls so the view is centred on a point of the scrollable area (fractions, as viewRect). */
  centerOn(x: number, y: number) {
    const [u0, u1] = this.bounds.u
    const [v0, v1] = this.bounds.v
    this.u = u0 + x * (u1 - u0)
    this.v = v0 + y * (v1 - v0)
    this.updateCamera()
  }

  /**
   * The whole scrollable area seen through the game camera, shrunk to `width` × `height`
   * pixels (keep areaAspect), for the radar. Rendered once into an image.
   */
  renderMinimap(width: number, height: number) {
    const [u0, u1] = this.bounds.u
    const [v0, v1] = this.bounds.v
    const centre = this.screenRight.clone().multiplyScalar((u0 + u1) / 2).addScaledVector(this.screenDown, (v0 + v1) / 2)
    const halfW = (u1 - u0) / 2
    const halfH = ((v1 - v0) / 2) * Math.sin(ELEVATION)
    const camera = new THREE.OrthographicCamera(-halfW, halfW, halfH, -halfH, 1, 400)
    camera.position.copy(centre).add(this.offset)
    camera.lookAt(centre)

    const target = new THREE.WebGLRenderTarget(width, height)
    this.renderer.setRenderTarget(target)
    this.renderer.render(this.scene, camera)
    const pixels = new Uint8Array(width * height * 4)
    this.renderer.readRenderTargetPixels(target, 0, 0, width, height, pixels)
    this.renderer.setRenderTarget(null)
    target.dispose()

    // WebGL rows run bottom-up
    const image = new ImageData(width, height)
    for (let row = 0; row < height; row++) {
      image.data.set(pixels.subarray(row * width * 4, (row + 1) * width * 4), (height - 1 - row) * width * 4)
    }
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    canvas.getContext('2d')!.putImageData(image, 0, 0)
    return canvas
  }

  /** Makes a building or unit selectable with the mouse. */
  addSelectable(object: THREE.Object3D) {
    this.selectables.push(object)
  }

  /** The building or unit under a point of the screen (client pixels), if any. */
  objectAt(clientX: number, clientY: number) {
    const rect = this.renderer.domElement.getBoundingClientRect()
    const x = ((clientX - rect.left) / rect.width) * 2 - 1
    const y = -((clientY - rect.top) / rect.height) * 2 + 1
    if (x < -1 || x > 1 || y < -1 || y > 1) return undefined
    this.raycaster.setFromCamera(new THREE.Vector2(x, y), this.camera)
    const hit = this.raycaster.intersectObjects(this.selectables, true)[0]
    if (!hit) {
      // between a building's parts (its pad's edge, a gap under a pipe) the ray misses
      // the model: a click on its foundation still means the building, not the ground
      const ground = this.pickGround(this.raycaster.ray)
      return ground ? this.selectables.find((object) => {
        const f = object.userData.footprint as Footprint | undefined
        return f && ground.x >= f.x && ground.x < f.x + f.w && ground.z >= f.z && ground.z < f.z + f.h
      }) : undefined
    }
    let node: THREE.Object3D | null = hit.object
    while (node && !this.selectables.includes(node)) node = node.parent
    return node ?? undefined
  }

  /**
   * Selects an object (or nothing). It is framed like in the original by a flat
   * rectangle facing the camera, of which only the corners are drawn, around the
   * object's outline on screen (see drawSelection).
   */
  /** Point on the ground under a point of the screen (client pixels), if it is on the map. */
  groundAt(clientX: number, clientY: number) {
    const rect = this.renderer.domElement.getBoundingClientRect()
    const ndc = new THREE.Vector2(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1)
    this.raycaster.setFromCamera(ndc, this.camera)
    const point = this.pickGround(this.raycaster.ray)
    if (!point) return undefined
    const u = point.dot(this.screenRight)
    const v = point.dot(this.screenDown)
    const [u0, u1] = this.bounds.u
    const [v0, v1] = this.bounds.v
    return u >= u0 && u <= u1 && v >= v0 && v <= v1 ? point : undefined
  }

  /** Whether an object belongs to the player (enemies have userData.owner = 'enemy') */
  static own(object: THREE.Object3D) {
    return (object.userData.owner ?? 'player') === 'player'
  }

  /** Whether own units are selected that can be ordered to move. */
  get canMove() {
    return this.selection.some(object => object.userData.unit && Battlefield.own(object))
  }

  /**
   * Sends the selected units to a point on the ground; several are spread around it
   * in a small grid, so they do not all stand on the same spot.
   */
  orderMove(point: THREE.Vector3) {
    this.clearWaypoints(this.selection)
    const units = this.selection.filter(Battlefield.own).map(object => object.userData.unit).filter(Boolean)
    const columns = Math.ceil(Math.sqrt(units.length))
    units.forEach((unit, i) => {
      const offset = new THREE.Vector3((i % columns) - (columns - 1) / 2, 0, Math.floor(i / columns) - (columns - 1) / 2).multiplyScalar(0.45)
      this.walk(unit, point.clone().add(offset))
    })
  }

  /**
   * Waypoints: each one is added to the way of the selected units (not harvesters, they
   * have their own work); they drive them one after the other. Returns whether any took it.
   */
  addWaypoint(point: THREE.Vector3) {
    let any = false
    for (const object of this.selection) {
      const unit = object.userData.unit as Unit | undefined
      if (!unit || !Battlefield.own(object) || object.userData.harvester) continue
      const waypoints = (object.userData.waypoints ??= []) as THREE.Vector3[]
      if (!unit.walking && !waypoints.length) this.walk(unit, point)
      else waypoints.push(point.clone())
      any = true
    }
    return any
  }

  /** Whether waypoints can be set: own units are selected that can take them */
  get canSetWaypoints() {
    return this.selection.some(object => object.userData.unit && Battlefield.own(object) && !object.userData.harvester)
  }

  /** Forgets the waypoints of these units (they got another order) */
  clearWaypoints(objects: THREE.Object3D[]) {
    for (const object of objects) object.userData.waypoints = undefined
  }

  /**
   * Sells a building: it leaves the map at once (foundation, selection) and folds up
   * like in the original, its Build clip running backwards; one without sinks into the
   * ground. Then it is gone. Returns the seconds this takes.
   */
  unbuild(object: THREE.Object3D) {
    object.userData.dead = true
    this.removeStructure(object)
    const mixer = object.userData.mixer as THREE.AnimationMixer | undefined
    const clip = (object.userData.clips as THREE.AnimationClip[] | undefined)?.find(c => c.name === 'Build')
    if (mixer && clip) {
      const action = mixer.clipAction(clip)
      action.reset()
      action.setLoop(THREE.LoopOnce, 1)
      action.clampWhenFinished = true
      action.timeScale = -1
      action.time = clip.duration
      action.play()
    }
    const seconds = mixer && clip ? clip.duration : SELL_SECONDS
    this.unbuilding.push({ object, time: 0, seconds, shrink: !(mixer && clip) })
    return seconds
  }

  private updateUnbuilding(seconds: number) {
    for (const item of this.unbuilding) {
      item.time += seconds
      if (item.shrink) item.object.scale.y = Math.max(0.02, 1 - item.time / item.seconds)
      if (item.time < item.seconds) continue
      this.scene.remove(item.object)
      const mixer = item.object.userData.mixer as THREE.AnimationMixer | undefined
      const i = mixer ? this.mixers.indexOf(mixer) : -1
      if (i >= 0) this.mixers.splice(i, 1)
    }
    this.unbuilding.splice(0, this.unbuilding.length, ...this.unbuilding.filter(item => item.time < item.seconds))
  }

  /** Whether the selected object can be given a rally point (factories like the barracks). */
  get canSetRallyPoint() {
    return !!this.selected && Battlefield.own(this.selected) && !!this.selected.userData.abilities?.includes('rally')
  }

  /** Sets where units leave to once the selected factory has produced them. */
  setRallyPoint(point: THREE.Vector3) {
    if (this.canSetRallyPoint) this.selected!.userData.rallyPoint = point.clone()
  }

  select(object: THREE.Object3D | undefined) {
    this.selection = object ? [object] : []
  }

  /**
   * Units can be picked by dragging a box; buildings and harvesters cannot. A unit is
   * marked with `userData.kind = 'unit'`, a harvester additionally `userData.harvester`.
   */
  /** A wall (sandbags …): only explosives harm it, and nobody attacks it on purpose */
  static isWall(object: THREE.Object3D) {
    return WALLS.has(object.userData.id)
  }

  static boxSelectable(object: THREE.Object3D) {
    return object.userData.kind === 'unit' && !object.userData.harvester && Battlefield.own(object)
  }

  /** Shows the selection box being dragged from (x0, y0) to (x1, y1), client pixels; undefined hides it. */
  setBand(band?: { x0: number, y0: number, x1: number, y1: number }) {
    this.band = band
  }

  /** Selects all box-selectable units whose centre lies in the screen box (client pixels). */
  selectInBox(x0: number, y0: number, x1: number, y1: number) {
    const rect = this.renderer.domElement.getBoundingClientRect()
    const [left, right] = [Math.min(x0, x1), Math.max(x0, x1)]
    const [top, bottom] = [Math.min(y0, y1), Math.max(y0, y1)]
    this.selection = this.selectables.filter((object) => {
      if (!Battlefield.boxSelectable(object)) return false
      const centre = new THREE.Box3().setFromObject(object).getCenter(new THREE.Vector3()).project(this.camera)
      const x = rect.left + (centre.x + 1) / 2 * rect.width
      const y = rect.top + (1 - centre.y) / 2 * rect.height
      return x >= left && x <= right && y >= top && y <= bottom
    })
    return this.selection.length
  }

  /** Selection frames, health bars and the rubber band: drawn in screen space over the scene, every frame */
  private readonly overlayScene = new THREE.Scene()
  /** The original signs over buildings (setSigns), a texture per frame */
  private signTextures?: Record<SignKind, THREE.Texture[]>
  /** Pixel doubling of the signs (like the cursor on large screens) */
  private signScale = 1
  /** Planes that show the signs on the overlay, reused from frame to frame */
  private readonly signMeshes: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>[] = []
  private readonly signGeometry = new THREE.PlaneGeometry(1, 1)
  /** Signs are on the overlay this frame */
  private signsShown = false

  /** The original signs over buildings (repair, switched off) are loaded; `scale`: pixel doubling */
  setSigns(frames: SignFrames, scale = 1) {
    this.signScale = scale
    this.disposables.push(this.signGeometry)
    const textures = (list: HTMLCanvasElement[]) => list.map((canvas) => {
      const texture = new THREE.CanvasTexture(canvas)
      texture.magFilter = THREE.NearestFilter
      texture.minFilter = THREE.NearestFilter
      texture.generateMipmaps = false
      texture.colorSpace = THREE.SRGBColorSpace
      this.disposables.push(texture)
      return texture
    })
    this.signTextures = { repair: textures(frames.repair), power: textures(frames.power) }
  }

  private signMesh(i: number) {
    let mesh = this.signMeshes[i]
    if (!mesh) {
      const material = new THREE.MeshBasicMaterial({ transparent: true, depthTest: false, depthWrite: false })
      this.disposables.push(material)
      mesh = new THREE.Mesh(this.signGeometry, material)
      mesh.renderOrder = 1 // over the frames and lines
      this.overlayScene.add(mesh)
      this.signMeshes.push(mesh)
    }
    return mesh
  }
  private readonly overlayCamera = new THREE.OrthographicCamera(0, 1, 0, 1, -1, 1)
  private readonly selectionFrame = new THREE.Mesh(
    new THREE.BufferGeometry(),
    new THREE.MeshBasicMaterial({ vertexColors: true, depthTest: false, side: THREE.DoubleSide }),
  )

  /**
   * Corners of the screen rectangle around the selected object's 3D bounds, and above
   * it the health bar like in the original: a row of small cells, green while healthy,
   * yellow when damaged and red when badly damaged (object.userData.health, 0 … 1).
   */
  /**
   * The box a building's frame is drawn round: its foundation, from the ground up to the
   * top of its model, like in the original. While its Build clip runs, parts still lie
   * under the ground or swing out beyond the foundation, so only the height is taken
   * from the model (the height of the finished building, where known); once it stands,
   * the box is kept (a waving flag would make it twitch).
   */
  private buildingBounds(object: THREE.Object3D): THREE.Box3 {
    if (object.userData.bounds) return object.userData.bounds
    const box = new THREE.Box3().setFromObject(object)
    box.min.y = object.position.y
    const height = object.userData.frameHeight as number | undefined
    if (height !== undefined) box.max.y = object.position.y + height
    const footprint = object.userData.footprint as Footprint | undefined
    if (footprint) {
      box.min.x = footprint.x
      box.max.x = footprint.x + footprint.w
      box.min.z = footprint.z
      box.max.z = footprint.z + footprint.h
    }
    const mixer = object.userData.mixer as THREE.AnimationMixer | undefined
    const build = (object.userData.clips as THREE.AnimationClip[] | undefined)?.find(c => c.name === 'Build')
    if (height !== undefined || !build || !mixer?.existingAction(build)?.isRunning()) object.userData.bounds = box
    return box
  }

  /**
   * The box a unit's frame is drawn round: always the same size, measured once when it
   * came onto the map, square round where it stands, so it doesn't change when the unit
   * turns or moves its parts (a Titan firing, a walker's legs).
   */
  private unitBounds(object: THREE.Object3D): THREE.Box3 {
    const { radius, height } = object.userData.frameSize as { radius: number, height: number }
    const at = object.position
    return new THREE.Box3(
      new THREE.Vector3(at.x - radius, at.y, at.z - radius),
      new THREE.Vector3(at.x + radius, at.y + height, at.z + radius),
    )
  }

  /** Middle of a building's frame on screen, in pixels of the battlefield */
  frameCentre(object: THREE.Object3D) {
    const at = this.buildingBounds(object).getCenter(new THREE.Vector3()).project(this.camera)
    return { x: (at.x + 1) / 2 * this.container.clientWidth, y: (1 - at.y) / 2 * this.container.clientHeight }
  }

  /** Corner frame and health bar of one selected object, around its outline on screen. */
  private drawFrame(
    object: THREE.Object3D,
    w: number,
    h: number,
    rect: (x0: number, y0: number, x1: number, y1: number, colour: [number, number, number]) => void,
    segment: (ax: number, ay: number, bx: number, by: number, width: number, colour: [number, number, number]) => void,
    quad: (corners: [number, number][], colour: [number, number, number]) => void,
  ) {
    const bounds = object.userData.kind === 'unit' ? this.unitBounds(object) : this.buildingBounds(object)
    let [left, top, right, bottom] = [Infinity, Infinity, -Infinity, -Infinity]
    for (let i = 0; i < 8; i++) {
      const corner = new THREE.Vector3(
        i & 1 ? bounds.max.x : bounds.min.x,
        i & 2 ? bounds.max.y : bounds.min.y,
        i & 4 ? bounds.max.z : bounds.min.z,
      ).project(this.camera)
      const x = (corner.x + 1) / 2 * w
      const y = (1 - corner.y) / 2 * h
      left = Math.min(left, x)
      right = Math.max(right, x)
      top = Math.min(top, y)
      bottom = Math.max(bottom, y)
    }
    // whole pixels, so the 2 px strokes stay crisp
    ;[left, top, right, bottom] = [Math.round(left), Math.round(top), Math.round(right), Math.round(bottom)]

    const white: [number, number, number] = [0.95, 0.95, 0.95]
    const health = THREE.MathUtils.clamp(object.userData.health ?? 1, 0, 1)
    const colour: [number, number, number] = health > 0.5 ? [0.1, 0.95, 0.15] : health > 0.25 ? [1, 0.85, 0.1] : [1, 0.15, 0.1]
    // a building's health bar lies inside its frame, under the frame's strokes
    if (object.userData.kind !== 'unit') this.drawBuildingHealth(bounds, w, h, health, colour, quad)
    if (object.userData.kind === 'unit') {
      // units: a flat frame facing the camera, only its corners: two strokes each, a
      // sixth of the shorter side long, 2 px thick
      const t = 2
      const l = Math.max(4, Math.round(Math.min(right - left, bottom - top) / 6))
      for (const [x, y, dx, dy] of [[left, top, 1, 1], [right, top, -1, 1], [left, bottom, 1, -1], [right, bottom, -1, -1]] as const) {
        rect(x, y, x + dx * l, y + dy * t, white)
        rect(x, y, x + dx * t, y + dy * l, white)
      }
    }
    else {
      // buildings: a box in 3D round them, like in the original: at each of its eight
      // corners short strokes along its three edges, a fifth of each edge long; only at
      // the six corners of its outline, not at the two inside it (the front one on top
      // and the back one on the ground, behind the building)
      const size = bounds.getSize(new THREE.Vector3())
      const corner = new THREE.Vector3()
      const end = new THREE.Vector3()
      const view = this.camera.getWorldDirection(new THREE.Vector3())
      for (let i = 0; i < 8; i++) {
        corner.set(i & 1 ? bounds.max.x : bounds.min.x, i & 2 ? bounds.max.y : bounds.min.y, i & 4 ? bounds.max.z : bounds.min.z)
        // inside the outline: all three sides of the box at the corner face the camera, or none
        const facing = [view.x, view.y, view.z].filter((d, a) => (i & (1 << a) ? 1 : -1) * d < 0).length
        if (facing === 0 || facing === 3) continue
        const from = corner.clone().project(this.camera)
        const ax = (from.x + 1) / 2 * w
        const ay = (1 - from.y) / 2 * h
        for (const axis of ['x', 'y', 'z'] as const) {
          const inwards = corner[axis] === bounds.max[axis] ? -1 : 1
          end.copy(corner)
          end[axis] += inwards * size[axis] / 5
          end.project(this.camera)
          segment(ax, ay, (end.x + 1) / 2 * w, (1 - end.y) / 2 * h, 1.6, white)
        }
      }
    }

    const cell = 4
    const gap = 1
    if (object.userData.kind !== 'unit') return
    // units: the health bar above the frame
    const barTop = top - 9
    const cells = Math.max(1, Math.floor((right - left - gap) / (cell + gap)))
    const barRight = left + cells * (cell + gap) + gap
    rect(left, barTop, barRight, barTop + cell + 2 * gap, [0.02, 0.02, 0.02])
    for (let i = 0; i < Math.ceil(cells * health); i++) {
      const x = left + gap + i * (cell + gap)
      rect(x, barTop + gap, x + cell, barTop + gap + cell, colour)
    }
    const cargo = object.userData.cargo as CargoSlot[] | undefined
    if (cargo) this.drawCargo(cargo, left, bottom, rect)

  }

  /**
   * A harvester's load in the lower left corner of its frame, like in the original:
   * five squares, filled green or blue by the Tiberium in them (a part-filled one from
   * the bottom up, a third per small cell), empty ones dark.
   */
  private drawCargo(
    cargo: CargoSlot[],
    left: number,
    bottom: number,
    rect: (x0: number, y0: number, x1: number, y1: number, colour: [number, number, number]) => void,
  ) {
    const size = 6
    const gap = 1
    const colours: Record<TiberiumKind, [number, number, number]> = { green: [0.2, 0.9, 0.2], blue: [0.25, 0.55, 1] }
    const x0 = left + 4
    const y1 = bottom - 4
    rect(x0 - gap, y1 - size - gap, x0 + CARGO_SLOTS * (size + gap), y1 + gap, [0.02, 0.02, 0.02])
    for (let i = 0; i < CARGO_SLOTS; i++) {
      const x = x0 + i * (size + gap)
      rect(x, y1 - size, x + size, y1, [0.16, 0.16, 0.14])
      const slot = cargo[i]
      if (!slot) continue
      const filled = Math.round(size * slot.stages / SLOT_STAGES)
      rect(x, y1 - filled, x + size, y1, colours[slot.kind])
    }
  }

  /**
   * A building's health bar runs along the top of its frame like in the original: a row
   * of small cubes from the left corner of the box's top face to its back corner (top
   * middle on screen), just inside the box under that edge. Lost health shows as dark
   * cubes. The cubes are about 4 px on screen whatever the zoom.
   */
  private drawBuildingHealth(
    bounds: THREE.Box3,
    w: number,
    h: number,
    health: number,
    colour: [number, number, number],
    quad: (corners: [number, number][], colour: [number, number, number]) => void,
  ) {
    const toScreen = (p: THREE.Vector3): [number, number] => {
      const at = p.clone().project(this.camera)
      return [(at.x + 1) / 2 * w, (1 - at.y) / 2 * h]
    }
    const corners = [0, 1, 2, 3].map(i => new THREE.Vector3(i & 1 ? bounds.max.x : bounds.min.x, bounds.max.y, i & 2 ? bounds.max.z : bounds.min.z))
    const screen = corners.map(toScreen)
    const left = corners[screen.indexOf(screen.reduce((a, b) => (b[0] < a[0] ? b : a)))]!
    const back = corners[screen.indexOf(screen.reduce((a, b) => (b[1] < a[1] ? b : a)))]!
    const along = back.clone().sub(left)
    const length = along.length()
    if (length <= 0) return
    along.divideScalar(length)
    // into the box across the edge
    const centre = bounds.getCenter(new THREE.Vector3())
    const across = new THREE.Vector3(-along.z, 0, along.x)
    if (across.dot(centre.clone().sub(left)) < 0) across.negate()
    const up = new THREE.Vector3(0, 1, 0)

    // world units per screen pixel along the edge
    const [lx, ly] = toScreen(left)
    const [bx, by] = toScreen(back)
    const perPixel = length / (Math.hypot(bx - lx, by - ly) || 1)
    const size = 4 * perPixel
    const gap = 1.2 * perPixel
    const cells = Math.max(1, Math.floor((length - gap) / (size + gap)))
    const full = Math.ceil(cells * health)
    const dark: [number, number, number] = [0.12, 0.12, 0.12]
    const view = this.camera.getWorldDirection(new THREE.Vector3())
    const shade = (c: [number, number, number], f: number): [number, number, number] => [c[0] * f, c[1] * f, c[2] * f]

    // the back cubes first, the front ones are drawn over them
    for (let i = cells - 1; i >= 0; i--) {
      const base = left.clone()
        .addScaledVector(along, gap + i * (size + gap))
        .addScaledVector(across, gap)
        .addScaledVector(up, -size - gap)
      const c = i < full ? colour : dark
      // the faces that look at the camera: the sides first, the top over them
      const faces: [THREE.Vector3, THREE.Vector3, THREE.Vector3, number][] = [
        [along, across, up, 0.55],
        [across, along, up, 0.75],
        [up, along, across, 1],
      ]
      for (const [normal, a, b, light] of faces) {
        for (const sign of [-1, 1]) {
          if (normal.dot(view) * sign >= 0) continue
          // the face on the `sign` side of the cube along `normal`
          const o = base.clone().addScaledVector(normal, sign > 0 ? size : 0)
          quad([
            toScreen(o),
            toScreen(o.clone().addScaledVector(a, size)),
            toScreen(o.clone().addScaledVector(a, size).addScaledVector(b, size)),
            toScreen(o.clone().addScaledVector(b, size)),
          ], shade(c, light))
        }
      }
    }
  }

  private drawSelection() {
    const w = this.container.clientWidth
    const h = this.container.clientHeight
    const positions: number[] = []
    const colours: number[] = []
    const rect = (x0: number, y0: number, x1: number, y1: number, [r, g, b]: [number, number, number]) => {
      positions.push(x0, y0, 0, x1, y0, 0, x1, y1, 0, x0, y0, 0, x1, y1, 0, x0, y1, 0)
      for (let i = 0; i < 6; i++) colours.push(r, g, b)
    }
    const segment = (ax: number, ay: number, bx: number, by: number, width: number, colour: [number, number, number]) => {
      const len = Math.hypot(bx - ax, by - ay) || 1
      const nx = (-(by - ay) / len) * width / 2
      const ny = ((bx - ax) / len) * width / 2
      positions.push(ax + nx, ay + ny, 0, bx + nx, by + ny, 0, bx - nx, by - ny, 0, ax + nx, ay + ny, 0, bx - nx, by - ny, 0, ax - nx, ay - ny, 0)
      for (let i = 0; i < 6; i++) colours.push(...colour)
    }
    const quad = (corners: [number, number][], colour: [number, number, number]) => {
      const [a, b, c, d] = corners as [[number, number], [number, number], [number, number], [number, number]]
      positions.push(a[0], a[1], 0, b[0], b[1], 0, c[0], c[1], 0, a[0], a[1], 0, c[0], c[1], 0, d[0], d[1], 0)
      for (let i = 0; i < 6; i++) colours.push(...colour)
    }
    for (const object of this.selection) this.drawFrame(object, w, h, rect, segment, quad)

    // the rubber band while dragging: a thin white rectangle
    if (this.band) {
      const box = this.renderer.domElement.getBoundingClientRect()
      const [x0, x1] = [Math.min(this.band.x0, this.band.x1) - box.left, Math.max(this.band.x0, this.band.x1) - box.left].map(Math.round) as [number, number]
      const [y0, y1] = [Math.min(this.band.y0, this.band.y1) - box.top, Math.max(this.band.y0, this.band.y1) - box.top].map(Math.round) as [number, number]
      const white: [number, number, number] = [0.95, 0.95, 0.95]
      rect(x0, y0, x1, y0 + 1, white)
      rect(x0, y1 - 1, x1, y1, white)
      rect(x0, y0, x0 + 1, y1, white)
      rect(x1 - 1, y0, x1, y1, white)
    }

    const toScreen = (p: THREE.Vector3) => {
      const v = p.clone().project(this.camera)
      return [(v.x + 1) / 2 * w, (1 - v.y) / 2 * h] as const
    }
    const green: [number, number, number] = [0.2, 1, 0.25]
    /** Dashes from a to b; `shift` (pixels) moves them along, so the line runs towards b */
    const dashes = (x0: number, y0: number, x1: number, y1: number, shift = 0) => {
      const length = Math.hypot(x1 - x0, y1 - y0)
      for (let d = (shift % 10) - 10; d < length; d += 10) {
        const a = Math.max(0, d) / length
        const b = Math.min(1, (d + 6) / length)
        if (b > a) segment(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b, 2, green)
      }
    }

    // where the selected units walk to: an animated dashed green line to a small diamond,
    // and on along their waypoints
    const shift = performance.now() / 1000 * 24
    for (const object of this.selection) {
      const destination = object.userData.unit?.destination as THREE.Vector3 | undefined
      const waypoints = (object.userData.waypoints ?? []) as THREE.Vector3[]
      let [x0, y0] = toScreen(object.position)
      for (const point of destination ? [destination, ...waypoints] : waypoints) {
        // on the ground there, also partway up a slope (the points of a route carry no height)
        const [x1, y1] = toScreen(point.clone().setY(this.heightAt(point.x, point.z)))
        dashes(x0, y0, x1, y1, shift)
        segment(x1 - 6, y1, x1, y1 - 3, 2, green)
        segment(x1, y1 - 3, x1 + 6, y1, 2, green)
        segment(x1 + 6, y1, x1, y1 + 3, 2, green)
        segment(x1, y1 + 3, x1 - 6, y1, 2, green)
        ;[x0, y0] = [x1, y1]
      }
    }

    // signs over own buildings, like in the original: the crossed-out lightning bolt over
    // one switched off, the wrench over one being repaired (both: one over the other)
    let signs = 0
    const frame = Math.floor(performance.now() / 1000 * SIGN_FPS)
    const blink = Math.floor(performance.now() / 1000 * SIGN_BLINK * 2) % 2 === 0
    for (const object of this.structureObjects) {
      if (object.userData.dead || !(object.userData.poweredOff || object.userData.repairing)) continue
      const box = this.buildingBounds(object)
      const [x, top] = toScreen(new THREE.Vector3((box.min.x + box.max.x) / 2, box.max.y, (box.min.z + box.max.z) / 2))
      let y = top
      for (const kind of (['repair', 'power'] as const).filter(k => k === 'repair' ? object.userData.repairing : object.userData.poweredOff)) {
        const textures = this.signTextures?.[kind]
        if (textures?.length) {
          const texture = textures[frame % textures.length]!
          const image = texture.image as HTMLCanvasElement
          const [sw, sh] = [image.width * this.signScale, image.height * this.signScale]
          const mesh = this.signMesh(signs++)
          // the first picture needs a new shader, the next ones only swap the texture
          if (!mesh.material.map) mesh.material.needsUpdate = true
          mesh.material.map = texture
          // the overlay's y runs downwards: the plane is mirrored so the picture stands upright
          mesh.scale.set(sw, -sh, 1)
          mesh.position.set(Math.round(x - sw / 2) + sw / 2, Math.round(y - sh) + sh / 2, 0)
          mesh.visible = true
          y -= sh * 0.6
          continue
        }
        // without the game data: drawn ones, blinking
        if (!blink) continue
        const cy = y - 14
        if (kind === 'power') {
          const yellow: [number, number, number] = [1, 0.85, 0.1]
          positions.push(x + 3, cy - 10, 0, x - 5, cy + 1, 0, x, cy + 1, 0, x - 3, cy + 10, 0, x + 5, cy - 1, 0, x, cy - 1, 0)
          for (let i = 0; i < 6; i++) colours.push(...yellow)
        }
        else {
          const silver: [number, number, number] = [0.85, 0.85, 0.8]
          segment(x - 6, cy + 6, x + 3, cy - 3, 3, silver)
          // the open jaw
          segment(x + 1, cy - 7, x + 1, cy - 1, 2.5, silver)
          segment(x + 1, cy - 1, x + 7, cy - 1, 2.5, silver)
        }
        y -= 24
      }
    }
    for (let i = signs; i < this.signMeshes.length; i++) this.signMeshes[i]!.visible = false
    this.signsShown = signs > 0

    // rally point of a selected factory: a dashed green line from it to a small flag
    const rally = this.selected?.userData.rallyPoint as THREE.Vector3 | undefined
    if (rally) {
      const [x0, y0] = toScreen(this.selected!.position)
      const [x1, y1] = toScreen(rally)
      dashes(x0, y0, x1, y1)
      // the flag: a pole with a little pennant, over a flat diamond on the ground
      segment(x1 - 7, y1, x1, y1 - 3.5, 2, green)
      segment(x1, y1 - 3.5, x1 + 7, y1, 2, green)
      segment(x1 + 7, y1, x1, y1 + 3.5, 2, green)
      segment(x1, y1 + 3.5, x1 - 7, y1, 2, green)
      segment(x1, y1, x1, y1 - 18, 2, [0.9, 0.9, 0.9])
      positions.push(x1 + 1, y1 - 18, 0, x1 + 11, y1 - 14.5, 0, x1 + 1, y1 - 11, 0)
      for (let i = 0; i < 3; i++) colours.push(1, 0.85, 0.1)
    }

    this.selectionFrame.visible = positions.length > 0
    const geometry = this.selectionFrame.geometry
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colours, 3))
    this.overlayCamera.right = w
    this.overlayCamera.bottom = h
    this.overlayCamera.updateProjectionMatrix()
  }

  /** The cell (lower x and z corner of a foundation of w × h cells) centred under a point of the screen */
  private cellAt(clientX: number, clientY: number, w: number, h: number) {
    const point = this.groundAt(clientX, clientY)
    return point && [Math.round(point.x - w / 2), Math.round(point.z - h / 2)] as [number, number]
  }

  /** Whether one cell can be built on: on the map, level, free of buildings, Tiberium and units (but `except`) */
  private cellFree(cx: number, cz: number, except?: THREE.Object3D) {
    // all four corners on the map (the map is a rectangle in screen axes)
    for (const [x, z] of [[cx, cz], [cx + 1, cz], [cx, cz + 1], [cx + 1, cz + 1]] as const) {
      const corner = new THREE.Vector3(x, 0, z)
      const u = corner.dot(this.screenRight)
      const v = corner.dot(this.screenDown)
      if (u < this.bounds.u[0] || u > this.bounds.u[1] || v < this.bounds.v[0] || v > this.bounds.v[1]) return false
    }
    if (this.terrain.flatLevel(cx, cz, 1, 1) === undefined) return false
    if (this.footprints.some(f => cx >= f.x && cx < f.x + f.w && cz >= f.z && cz < f.z + f.h)) return false
    if (this.tiberium.has(`${cx},${cz}`)) return false
    // a unit standing on it, own or enemy (not one in the air): as far round as it is big
    return !this.units.some(({ object }) => {
      if (object === except || object.userData.dead || object.userData.offGround) return false
      const radius = ((object.userData.frameSize?.radius as number | undefined) ?? 0) * UNIT_BLOCK_SHARE
      const at = object.position
      const dx = Math.max(cx - at.x, 0, at.x - (cx + 1))
      const dz = Math.max(cz - at.z, 0, at.z - (cz + 1))
      return Math.hypot(dx, dz) < radius || (dx === 0 && dz === 0)
    })
  }

  /**
   * Whether a foundation lies on the map, on free ground and close enough to the base.
   * `free` gets for each cell (x first, then z) whether it can be built on; `except` is
   * a unit that may stand there (the MCV that unfolds there).
   */
  canPlace(x: number, z: number, w: number, h: number, adjacent: number, { free = [], except }: { free?: boolean[], except?: THREE.Object3D } = {}) {
    free.length = 0
    for (let i = 0; i < w; i++) {
      for (let j = 0; j < h; j++) free.push(this.cellFree(x + i, z + j, except))
    }
    if (free.includes(false)) return false
    // all on one level: not on a ramp, not across a cliff
    if (this.terrain.flatLevel(x, z, w, h) === undefined) return false
    // gap in cells to the nearest building of the base
    const gap = (f: Footprint) => Math.max(f.x - (x + w), x - (f.x + f.w), f.z - (z + h), z - (f.z + f.h), 0)
    // only the player's own base counts
    const own = this.footprints.filter(f => f.owner === 'player')
    return !own.length || own.some(f => gap(f) <= adjacent)
  }

  /** Starts placing a structure of w × h cells: its cells follow the cursor (see updatePlacement). */
  startPlacement(w: number, h: number, adjacent: number) {
    this.cancelPlacement()
    const preview = new THREE.Group()
    const geometry = new THREE.PlaneGeometry(0.92, 0.92).rotateX(-Math.PI / 2)
    const material = (color: number) => new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.45, depthWrite: false })
    const materials = { free: material(0xffffff), blocked: material(0xff3a2a) }
    for (let i = 0; i < w; i++) {
      for (let j = 0; j < h; j++) {
        const cell = new THREE.Mesh(geometry, materials.free)
        cell.position.set(i + 0.5, 0.02, j + 0.5)
        preview.add(cell)
      }
    }
    preview.visible = false
    this.scene.add(preview)
    this.placement = { w, h, adjacent, preview, materials, valid: false }
  }

  /**
   * Moves the preview under the cursor: white the cells that can be built on, red those
   * that cannot (a unit in the way, a building, Tiberium, a slope); all red if the
   * structure may not go there as a whole (too far from the base, across a cliff).
   */
  updatePlacement(clientX: number, clientY: number) {
    const placement = this.placement
    if (!placement) return
    const cell = this.cellAt(clientX, clientY, placement.w, placement.h)
    placement.cell = cell
    placement.preview.visible = !!cell
    if (!cell) return
    placement.preview.position.set(cell[0], this.heightAt(cell[0] + 0.5, cell[1] + 0.5), cell[1])
    const free: boolean[] = []
    placement.valid = this.canPlace(cell[0], cell[1], placement.w, placement.h, placement.adjacent, { free })
    const anyBlocked = free.includes(false)
    placement.preview.children.forEach((child, i) => {
      const ok = placement.valid || (anyBlocked && free[i])
      ;(child as THREE.Mesh).material = ok ? placement.materials.free : placement.materials.blocked
    })
  }

  /** Where the structure would be placed (its lower corner cell), if it may be placed there */
  get placementCell() {
    return this.placement?.valid ? this.placement.cell : undefined
  }

  cancelPlacement() {
    if (!this.placement) return
    this.scene.remove(this.placement.preview)
    const cell = this.placement.preview.children[0] as THREE.Mesh | undefined
    cell?.geometry.dispose()
    this.placement.materials.free.dispose()
    this.placement.materials.blocked.dispose()
    this.placement = undefined
  }

  /**
   * Puts a structure on the map with its foundation (w × h cells) at cell (x, z): the
   * model from `url` (built up by its own animation), or else a simple placeholder
   * that rises out of the ground.
   */
  async addStructure(id: string, x: number, z: number, w: number, h: number, url?: string, houseColour = 0xd8b43a, owner: Owner = 'player') {
    // on its level (the foundation is flat, see canPlace)
    const centre = new THREE.Vector3(x + w / 2, (this.terrain.flatLevel(x, z, w, h) ?? 0) * LEVEL_HEIGHT, z + h / 2)
    const footprint: Footprint = { x, z, w, h, owner, wall: WALLS.has(id) }
    this.footprints.push(footprint)
    const object = url ? await this.addBuilding(url, centre, houseColour) : this.addPlaceholder(id, centre, w, h, houseColour)
    object.userData.id = id
    object.userData.owner = owner
    object.userData.footprint = footprint
    this.structures.set(id, [...(this.structures.get(id) ?? []), object])
    if (WALLS.has(id)) {
      this.connectWalls(x, z)
      // walls cannot be clicked or picked with a box (Selectable=no in RULES.INI)
      const i = this.selectables.indexOf(object)
      if (i >= 0) this.selectables.splice(i, 1)
    }
    return object
  }

  /** The wall (sandbags …) standing on a cell, if any */
  private wallAt(x: number, z: number) {
    for (const id of WALLS) {
      const wall = this.structuresOf(id).find(o => o.userData.footprint?.x === x && o.userData.footprint?.z === z)
      if (wall) return wall
    }
    return undefined
  }

  /**
   * Joins up the walls on a cell and its four neighbours: each wall model shows an arm
   * (ArmXP, ArmXN, ArmZP, ArmZN) towards every neighbouring cell with a wall, so they
   * make straight walls, corners, T-pieces and crossings.
   */
  connectWalls(x: number, z: number) {
    for (const [cx, cz] of [[x, z], [x + 1, z], [x - 1, z], [x, z + 1], [x, z - 1]] as const) {
      const wall = this.wallAt(cx, cz)
      if (!wall) continue
      // the arms are taken out of the model when not needed (hidden ones would still
      // count for picking and the selection frame); kept here to put them back
      const arms: Record<string, THREE.Object3D> = wall.userData.arms ??= Object.fromEntries(
        ['ArmXP', 'ArmXN', 'ArmZP', 'ArmZN'].map(name => [name, wall.getObjectByName(name)]).filter(([, arm]) => arm))
      const towards = { ArmXP: [1, 0], ArmXN: [-1, 0], ArmZP: [0, 1], ArmZN: [0, -1] } as const
      for (const [name, [dx, dz]] of Object.entries(towards)) {
        const arm = arms[name]
        if (!arm) continue
        if (this.wallAt(cx + dx, cz + dz)) {
          if (!arm.parent) arm.userData.home.add(arm)
        }
        else if (arm.parent) {
          arm.userData.home = arm.parent
          arm.removeFromParent()
        }
      }
    }
  }

  /** The buildings of a kind on the map */
  structuresOf(id: string) {
    return this.structures.get(id) ?? []
  }

  /** A plain building for structures without a model yet: slab, body and a house-colour band */
  private addPlaceholder(id: string, centre: THREE.Vector3, w: number, h: number, houseColour = 0xd8b43a) {
    const height = PLACEHOLDER_HEIGHT[id] ?? 0.5
    const group = new THREE.Group()
    const box = (sx: number, sy: number, sz: number, y: number, colour: number, name?: string) => {
      const geometry = new THREE.BoxGeometry(sx, sy, sz)
      const material = new THREE.MeshStandardMaterial({ color: colour, roughness: 0.85, metalness: 0.1 })
      if (name) material.name = name
      this.disposables.push(geometry, material)
      const mesh = new THREE.Mesh(geometry, material)
      mesh.position.y = y + sy / 2
      group.add(mesh)
    }
    box(w - 0.08, 0.07, h - 0.08, 0, 0x8a857a)
    box(w * 0.72, height, h * 0.72, 0.07, 0xb9a57c)
    box(w * 0.74, height * 0.16, h * 0.74, 0.07 + height * 0.55, houseColour, 'Remap')
    box(w * 0.5, 0.05, h * 0.5, 0.07 + height, 0x6f6a60)
    group.position.copy(centre)
    group.scale.y = 0.02
    this.castShadows(group)
    this.scene.add(group)
    this.addSelectable(group)
    this.rising.push({ object: group, time: 0 })
    return group
  }

  /** A point of the map given in screen axes (u across, v down, in cells from the top left corner) */
  mapPoint(u: number, v: number) {
    return this.screenRight.clone().multiplyScalar(u).addScaledVector(this.screenDown, v)
  }

  /**
   * Where a line from `from` (world) in `direction` (world, on the ground) leaves the
   * map: the point on the map's edge, e.g. where an aircraft comes in or flies off to.
   */
  edgePoint(from: THREE.Vector3, direction: THREE.Vector3) {
    const u = from.dot(this.screenRight)
    const v = from.dot(this.screenDown)
    const du = direction.dot(this.screenRight)
    const dv = direction.dot(this.screenDown)
    const reach = (value: number, step: number, [min, max]: [number, number]) =>
      step > 1e-9 ? (max - value) / step : step < -1e-9 ? (min - value) / step : Infinity
    const t = Math.max(0, Math.min(reach(u, du, this.bounds.u), reach(v, dv, this.bounds.v)))
    return this.mapPoint(u + du * t, v + dv * t)
  }

  /** Size of the map in cells along the screen axes */
  get mapSize() {
    return [this.bounds.u[1] - this.bounds.u[0], this.bounds.v[1] - this.bounds.v[0]] as const
  }

  /** Centre of the map in world coordinates */
  get centre() {
    const u = (this.bounds.u[0] + this.bounds.u[1]) / 2
    const v = (this.bounds.v[0] + this.bounds.v[1]) / 2
    return this.screenRight.clone().multiplyScalar(u).addScaledVector(this.screenDown, v)
  }

  /** Loads a model: "Remap" (and its shades) in the house colour, "Glow*" halos shine additively. */
  private async loadModel(url: string, houseColour: number) {
    const gltf = await new GLTFLoader().loadAsync(url)
    gltf.scene.traverse((node) => {
      const mesh = node as THREE.Mesh
      if (!mesh.isMesh) return
      for (const mat of [mesh.material].flat() as THREE.MeshStandardMaterial[]) {
        applyHouseColour(mat, houseColour)
        if (mat.name.startsWith('Glow')) {
          mat.blending = THREE.AdditiveBlending
          mat.depthWrite = false
        }
        if (mat.map) this.disposables.push(mat.map)
        this.disposables.push(mat)
      }
      this.disposables.push(mesh.geometry)
    })
    return gltf
  }

  /**
   * The cells (lower corner) a mobile construction vehicle would unfold onto: the
   * 3 × 3 cells around it, if they are on the map and free.
   */
  deployCell(unit: Unit): [number, number] | undefined {
    const x = Math.floor(unit.object.position.x) - 1
    const z = Math.floor(unit.object.position.z) - 1
    return this.canPlace(x, z, 3, 3, Infinity, { except: unit.object }) ? [x, z] : undefined
  }

  /**
   * Deploys an MCV into a construction yard (id GACNST, model `url`): it drives to the
   * middle of the foundation, turns to face the front (+z), and is replaced by the
   * yard, whose Build clip starts with exactly this vehicle there and unfolds the yard.
   * Resolves with the yard, or undefined if there is no room.
   */
  deploy(unit: Unit, url: string, houseColour = 0xd8b43a) {
    const cell = this.deployCell(unit)
    if (!cell) return Promise.resolve(undefined)
    // the cells are taken from now on
    const [x, z] = cell
    const footprint: Footprint = { x, z, w: 3, h: 3, owner: (unit.object.userData.owner ?? 'player') as Owner }
    this.footprints.push(footprint)
    unit.walkTo(new THREE.Vector3(x + 1.5, 0, z + 1.5))
    return new Promise<THREE.Object3D | undefined>((resolve) => {
      this.deploying.push({ unit, x, z, url, houseColour, footprint, resolve })
    })
  }

  private updateDeploying(seconds: number) {
    for (const job of [...this.deploying]) {
      const { unit } = job
      const finish = () => {
        this.deploying.splice(this.deploying.indexOf(job), 1)
        this.footprints.splice(this.footprints.indexOf(job.footprint), 1)
      }
      if (unit.object.userData.dead) {
        finish()
        job.resolve(undefined)
        continue
      }
      if (unit.walking) continue
      // facing the front, like the vehicle at the start of the yard's Build clip
      unit.face(unit.object.position.clone().add(new THREE.Vector3(0, 0, 1)), seconds)
      const off = THREE.MathUtils.euclideanModulo(unit.object.rotation.y - DEPLOY_HEADING + Math.PI, 2 * Math.PI) - Math.PI
      if (Math.abs(off) > 0.02) continue
      unit.object.rotation.y = DEPLOY_HEADING
      finish()
      const owner = (unit.object.userData.owner ?? 'player') as Owner
      const wasSelected = this.selection.includes(unit.object)
      this.remove(unit.object)
      this.addStructure('GACNST', job.x, job.z, 3, 3, job.url, job.houseColour, owner).then((yard) => {
        if (wasSelected) this.select(yard)
        job.resolve(yard)
      }, () => job.resolve(undefined))
    }
  }

  /**
   * A dropship (DSHP.glb) that flies in from `from`, lands at `flight.to`, unloads
   * and flies off to `flight.leave`; it is taken off the map when it has gone (or its
   * wreck has burnt out after crash()).
   */
  async addDropship(url: string, from: THREE.Vector3, flight: DropshipFlight, houseColour = 0xd8b43a) {
    const gltf = await this.loadModel(url, houseColour)
    gltf.scene.position.copy(from)
    const ship = new Dropship(gltf.scene, gltf.animations, flight, (x, z) => this.heightAt(x, z))
    ship.onGone = () => {
      this.scene.remove(gltf.scene)
      this.aircraft.splice(this.aircraft.indexOf(ship), 1)
      ship.dispose()
    }
    this.castShadows(gltf.scene)
    this.scene.add(gltf.scene)
    this.aircraft.push(ship)
    return ship
  }

  /**
   * Tiberium (TIB.glb) on the given cells: each cell gets one of the model's variants
   * (A–C), turned by a random multiple of 90°, shows the node of its growth stage
   * (Stage1A … Stage3C) and colours the ground round it. Cells that have Tiberium already keep it.
   * The fields then grow on their own (see growTiberium).
   */
  async addTiberium(url: string, cells: TiberiumCell[]) {
    const gltf = await this.loadModel(url, 0)
    for (const { x, z, stage, kind = 'green' } of cells) {
      const key = `${x},${z}`
      if (this.tiberium.has(key)) continue
      const variant = 'ABC'[Math.floor(Math.random() * 3)]!
      const object = gltf.scene.clone()
      // only the three stages of this variant
      const others: THREE.Object3D[] = []
      object.traverse((node) => {
        if (/^Stage\d[ABC]$/.test(node.name) && !node.name.endsWith(variant)) others.push(node)
      })
      for (const node of others) node.removeFromParent()
      object.position.set(x + 0.5, this.heightAt(x + 0.5, z + 0.5), z + 0.5)
      object.rotation.y = Math.floor(Math.random() * 4) * Math.PI / 2
      object.userData.variant = variant
      if (kind === 'blue') this.paintBlue(object)
      this.castShadows(object)
      this.scene.add(object)
      const cell = { x, z, stage, kind, object }
      this.tiberium.set(key, cell)
      this.showTiberiumStage(cell)
    }
  }

  /** Blue versions of the crystals' materials (TiberiumCrystal, -Deep, -Tip), made once */
  private readonly blueMaterials = new Map<THREE.Material, THREE.Material>()

  /** Turns a Tiberium cell's crystals blue (Vinifera): the same lightness, a blue hue */
  private paintBlue(object: THREE.Object3D) {
    const blue = (original: THREE.Material) => {
      if (!original.name.startsWith('Tiberium') || !(original as THREE.MeshStandardMaterial).isMeshStandardMaterial) return original
      let mat = this.blueMaterials.get(original) as THREE.MeshStandardMaterial | undefined
      if (!mat) {
        mat = (original as THREE.MeshStandardMaterial).clone()
        for (const colour of [mat.color, mat.emissive]) {
          const hsl = colour.getHSL({ h: 0, s: 0, l: 0 })
          // only the crystals, not the grey seed pods
          if (hsl.s > 0.2) colour.setHSL(0.58, hsl.s, hsl.l)
        }
        this.blueMaterials.set(original, mat)
        this.disposables.push(mat)
      }
      return mat
    }
    object.traverse((node) => {
      const mesh = node as THREE.Mesh
      if (mesh.isMesh) mesh.material = Array.isArray(mesh.material) ? mesh.material.map(blue) : blue(mesh.material)
    })
  }

  /** Shows the node of a Tiberium cell's stage, hides the others and stains the ground to match */
  private showTiberiumStage(cell: TiberiumCell & { object: THREE.Object3D }) {
    const shown = `Stage${cell.stage}${cell.object.userData.variant}`
    cell.object.traverse((node) => {
      if (/^Stage\d[ABC]$/.test(node.name)) node.visible = node.name === shown
    })
    const ground = this.tiberiumGround
    const tx = cell.x - ground.x
    const tz = cell.z - ground.z
    if (tx < 0 || tz < 0 || tx >= ground.w || tz >= ground.h) return
    ground.texture.image.data![(tz * ground.w + tx) * 4] = Math.round(cell.stage / TIBERIUM_RIPE * 255)
    this.shineTiberium(cell.x, cell.z)
  }

  /**
   * Works out the green shine on the ground round a Tiberium cell (green channel of the
   * ground's Tiberium texels): at every cell up to TIBERIUM_SHINE cells away, the
   * strongest of the Tiberium cells near it, fading with the distance, riper is brighter.
   */
  private shineTiberium(x: number, z: number) {
    const ground = this.tiberiumGround
    const data = ground.texture.image.data!
    const reach = TIBERIUM_SHINE
    for (let tz = Math.max(0, z - ground.z - reach); tz <= Math.min(ground.h - 1, z - ground.z + reach); tz++) {
      for (let tx = Math.max(0, x - ground.x - reach); tx <= Math.min(ground.w - 1, x - ground.x + reach); tx++) {
        // the strongest shine, and how much of the shine round it is blue
        let shine = 0
        let green = 0
        let blue = 0
        for (let dz = -reach; dz <= reach; dz++) {
          for (let dx = -reach; dx <= reach; dx++) {
            const source = this.tiberium.get(`${ground.x + tx + dx},${ground.z + tz + dz}`)
            if (!source?.stage) continue
            const near = Math.max(0, 1 - Math.hypot(dx, dz) / reach)
            const strength = (0.55 + 0.45 * source.stage / TIBERIUM_RIPE) * near * near * (3 - 2 * near)
            shine = Math.max(shine, strength)
            if (source.kind === 'blue') blue += strength
            else green += strength
          }
        }
        data[(tz * ground.w + tx) * 4 + 1] = Math.round(shine * 255)
        data[(tz * ground.w + tx) * 4 + 2] = Math.round(blue / Math.max(1e-6, blue + green) * 255)
      }
    }
    ground.texture.needsUpdate = true
  }

  /**
   * The cell with Tiberium nearest to `from` (cell centres), if there is any, only of
   * `kind` if given; cells in `skip` ("x,z") are left out.
   */
  nearestTiberium(from: THREE.Vector3, skip?: Set<string>, kind?: TiberiumKind): TiberiumCell | undefined {
    let best: TiberiumCell | undefined
    let bestDistance = Infinity
    for (const [key, cell] of this.tiberium) {
      if (!cell.stage || skip?.has(key) || (kind && (cell.kind ?? 'green') !== kind)) continue
      const d = Math.hypot(cell.x + 0.5 - from.x, cell.z + 0.5 - from.z)
      if (d < bestDistance) {
        best = cell
        bestDistance = d
      }
    }
    return best && { x: best.x, z: best.z, stage: best.stage, kind: best.kind ?? 'green' }
  }

  /** The Tiberium on the cell under a point on the ground, if any is there */
  tiberiumAt(point: THREE.Vector3): TiberiumCell | undefined {
    const cell = this.tiberium.get(`${Math.floor(point.x)},${Math.floor(point.z)}`)
    return cell?.stage ? { x: cell.x, z: cell.z, stage: cell.stage, kind: cell.kind ?? 'green' } : undefined
  }

  /**
   * Harvests a stage of the Tiberium on a cell; returns whether there was any. A cell
   * harvested bare keeps its root: it shows nothing and grows again (growTiberium).
   */
  harvestTiberium(x: number, z: number) {
    const cell = this.tiberium.get(`${x},${z}`)
    if (!cell?.stage) return false
    cell.stage--
    this.showTiberiumStage(cell)
    return true
  }

  /** Every TIBERIUM_GROWTH seconds a random cell that is not ripe yet grows a stage. */
  private growTiberium(seconds: number) {
    this.tiberiumTimer += seconds
    if (this.tiberiumTimer < TIBERIUM_GROWTH) return
    this.tiberiumTimer = 0
    const growing = [...this.tiberium.values()].filter(cell => cell.stage < TIBERIUM_RIPE)
    const cell = growing[Math.floor(Math.random() * growing.length)]
    if (!cell) return
    cell.stage++
    this.showTiberiumStage(cell)
  }

  /**
   * Plays one of a building's clips once from the start (e.g. the construction yard's
   * "Deliver" when a structure is placed); a clip still running starts over.
   * Returns false if the building has no such clip.
   */
  playClip(building: THREE.Object3D, name: string) {
    const mixer = building.userData.mixer as THREE.AnimationMixer | undefined
    const clip = (building.userData.clips as THREE.AnimationClip[] | undefined)?.find(c => c.name === name)
    if (!mixer || !clip) return false
    const action = mixer.clipAction(clip)
    action.setLoop(THREE.LoopOnce, 1)
    action.clampWhenFinished = false
    action.reset().play()
    return true
  }

  /**
   * Places a building model (GLB, 1 unit = 1 cell, origin at the middle of its
   * foundation) with its foundation's centre at `at` (world, on the ground).
   * The material "Remap" gets the house colour, "Glow*" halos around lamps shine additively.
   *
   * Animations of the model: "Build" (played once when `build` is set, else the
   * building stands finished) and "Idle" (looped: waving flag, blinking lights).
   * Other clips (e.g. the construction yard's "Deliver") wait for playClip().
   */
  async addBuilding(url: string, at: THREE.Vector3, houseColour = 0xd8b43a, build = true) {
    const gltf = await this.loadModel(url, houseColour)
    if (gltf.animations.length) {
      const mixer = new THREE.AnimationMixer(gltf.scene)
      for (const clip of gltf.animations) {
        if (clip.name !== 'Build' && clip.name !== 'Idle') continue
        const action = mixer.clipAction(clip).play()
        if (clip.name === 'Build') {
          action.setLoop(THREE.LoopOnce, 1).clampWhenFinished = true
          // the model's own pose is not the finished building: show the clip's last frame
          if (!build) action.time = clip.duration
        }
      }
      // the frame keeps the size of the finished building while it is still being built
      const buildClip = gltf.animations.find(c => c.name === 'Build')
      const buildAction = buildClip && mixer.existingAction(buildClip)
      if (build && buildClip && buildAction) {
        buildAction.time = buildClip.duration
        mixer.update(0)
        gltf.scene.userData.frameHeight = new THREE.Box3().setFromObject(gltf.scene).max.y
        buildAction.reset()
      }
      mixer.update(0) // the first frame of the build before the model is shown
      this.mixers.push(mixer)
      gltf.scene.userData.mixer = mixer
      gltf.scene.userData.clips = gltf.animations
    }
    gltf.scene.position.copy(at)
    this.castShadows(gltf.scene)
    this.scene.add(gltf.scene)
    this.addSelectable(gltf.scene)
    return gltf.scene
  }
  /**
   * Mounts an upgrade (GLB, origin in the middle of its foot) onto a structure: onto its
   * next free place, the empty nodes named Slot… in the structure's model (e.g. the
   * power plant's TurbineSlot1 … 3), in the order of their names. The upgrade becomes
   * part of the structure (selected with it, removed with it) and plays its own "Build"
   * when `build` is set. Returns undefined when all places are taken.
   */
  async addUpgrade(structure: THREE.Object3D, url: string, houseColour = 0xd8b43a, build = true) {
    const slots: THREE.Object3D[] = []
    structure.traverse((node) => {
      if (/Slot\d+$/.test(node.name)) slots.push(node)
    })
    slots.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }))
    const slot = slots.find(s => !s.userData.upgrade)
    if (!slot) return undefined
    slot.userData.upgrade = true // taken while it loads
    const upgrade = await this.addBuilding(url, new THREE.Vector3(), houseColour, build)
    this.selectables.splice(this.selectables.indexOf(upgrade), 1)
    slot.add(upgrade)
    slot.userData.upgrade = upgrade
    return upgrade
  }

  /**
   * Places a unit (GLB with a skinned model and the clips "Idle" and "Walk", 1 unit =
   * 1 cell, origin between its feet, looking along +Z) on the ground at `at`.
   * The material "Remap" (and its shades, e.g. the camouflage) gets the house colour,
   * Nod's units wear dark armour (applyHouseColour). Move it with `walkTo`.
   */
  async addUnit(url: string, at: THREE.Vector3, houseColour = 0xd8b43a, owner: 'player' | 'enemy' = 'player', side: Side = 'gdi') {
    let model = this.unitModels.get(url)
    if (!model) {
      model = new GLTFLoader().loadAsync(url)
      this.unitModels.set(url, model)
      model.then(gltf => gltf.scene.traverse((node) => {
        const mesh = node as THREE.Mesh
        if (mesh.isMesh) this.disposables.push(mesh.geometry)
      })).catch(() => this.unitModels.delete(url))
    }
    const gltf = await model
    const object = cloneSkinned(gltf.scene)
    object.traverse((node) => {
      const mesh = node as THREE.Mesh
      if (!mesh.isMesh) return
      // own materials, so every unit can have its house's colour
      mesh.material = ([mesh.material].flat() as THREE.MeshStandardMaterial[]).map((original) => {
        const mat = original.clone()
        applyHouseColour(mat, houseColour, side)
        this.disposables.push(mat)
        return mat
      })
      if ((mesh.material as THREE.Material[]).length === 1) mesh.material = (mesh.material as THREE.Material[])[0]!
    })
    object.position.copy(at).setY(this.heightAt(at.x, at.z))
    object.userData.kind = 'unit' // can be picked with the selection box
    const unit = new Unit(object, gltf.animations)
    // In its first pose (a new skeleton's bone matrices are all zero, the body would
    // shrink to a point): measured so, the frame came out far too small, and a bounding
    // sphere worked out before the first frame (e.g. by the mouse's picking) left the
    // soldier culled for good. Animated bodies are not culled at all: their pose leaves
    // any sphere measured once.
    unit.update(0)
    object.updateMatrixWorld(true)
    object.traverse((node) => {
      const mesh = node as THREE.SkinnedMesh
      if (!mesh.isSkinnedMesh) return
      mesh.skeleton.update()
      mesh.computeBoundingBox()
      mesh.computeBoundingSphere()
      mesh.frustumCulled = false
    })
    const box = new THREE.Box3().setFromObject(object)
    object.userData.frameSize = { radius: Math.max(box.max.x - box.min.x, box.max.z - box.min.z) / 2, height: box.max.y - at.y }
    this.castShadows(object)
    object.userData.owner = owner
    this.scene.add(object)
    this.addSelectable(object)
    object.userData.unit = unit
    this.units.push(unit)
    return unit
  }


  /**
   * Whether a unit rolls over enemy walls (Crusher=, see Combat): set by the combat,
   * which knows the rules
   */
  crusher: (object: THREE.Object3D) => boolean = () => false

  /**
   * Whether a cell is on the map and not under a building; for a crusher of `crusher`'s
   * side the walls (sandbags) of its enemies are no obstacle, it drives over them
   */
  private free(x: number, z: number, crusher?: Owner) {
    if (!this.onMap(x, z)) return false
    return !this.footprints.some(f => x >= f.x && x < f.x + f.w && z >= f.z && z < f.z + f.h
      && !(crusher && f.wall && f.owner !== crusher))
  }

  /**
   * Where a unit can stand at or near `at`: the point itself if its cell is on the map,
   * free and not rock (a cliff; `flat`: flat ground, no slope or ramp either), else the
   * middle of the nearest such cell (up to OPEN_SEARCH cells away)
   */
  openSpot(at: THREE.Vector3, flat = false) {
    const open = (x: number, z: number) => this.free(x, z) && (flat ? this.terrain.cell(x, z) === Cell.Flat : this.terrain.cell(x, z) !== Cell.Rock)
    const x0 = Math.floor(at.x)
    const z0 = Math.floor(at.z)
    if (open(x0, z0)) return at.clone()
    for (let r = 1; r <= OPEN_SEARCH; r++) {
      let best: THREE.Vector3 | undefined
      for (let dz = -r; dz <= r; dz++) {
        for (let dx = -r; dx <= r; dx++) {
          if (Math.max(Math.abs(dx), Math.abs(dz)) !== r || !open(x0 + dx, z0 + dz)) continue
          const spot = new THREE.Vector3(x0 + dx + 0.5, 0, z0 + dz + 0.5)
          if (!best || spot.distanceToSquared(at) < best.distanceToSquared(at)) best = spot
        }
      }
      if (best) return best
    }
    return at.clone()
  }

  /** Whether a cell's middle is on the map */
  private onMap(x: number, z: number) {
    const centre = new THREE.Vector3(x + 0.5, 0, z + 0.5)
    const u = centre.dot(this.screenRight)
    const v = centre.dot(this.screenDown)
    return u >= this.bounds.u[0] && u <= this.bounds.u[1] && v >= this.bounds.v[0] && v <= this.bounds.v[1]
  }

  /** Whether one can step from a cell to its neighbour: not over a cliff or up a ramp's side */
  private readonly step = (x: number, z: number, dx: number, dz: number) => this.terrain.passable(x, z, dx, dz)

  /** The map for pathfinding: cells on the map and not under a building, steps not over cliffs */
  readonly nav: NavMap = { free: (x, z) => this.free(x, z), step: this.step }

  /** The map for one unit's way: a crusher's leads over enemy walls */
  navFor(object: THREE.Object3D): NavMap {
    if (!this.crusher(object)) return this.nav
    const owner = (object.userData.owner ?? 'player') as Owner
    return { free: (x, z) => this.free(x, z, owner), step: this.step }
  }

  /** Sends a unit to a point on the shortest way round the buildings. */
  walk(unit: Unit, to: THREE.Vector3) {
    const object = unit.object
    // under the ground: on to the new place
    const tunnel = this.tunnels.find(t => t.unit === unit)
    if (tunnel) {
      // coming up already: from there
      if (tunnel.phase === 'up') tunnel.next = to
      else tunnel.to = this.openSpot(to, true)
      return
    }
    // dug in: out of the ground first
    if (unit.posture === POSTURES.dig.posture || unit.changingPosture) {
      void unit.change(POSTURES.dig.out, undefined).then(() => {
        if (!object.userData.dead) this.walk(unit, to)
      })
      return
    }
    // the subterranean APC goes far under the ground, where the ground lets it dig (under it already: on under it)
    if (unit.posture === POSTURES.tunnel.posture
      || (TUNNELLERS.has(object.userData.id) && object.position.distanceTo(to) > TUNNEL_MIN && this.canDig(object.position))) {
      this.burrow(unit, to)
      return
    }
    unit.followPath(findPath(this.navFor(object), object.position, to))
  }

  /** The soldiers a transport carries (out of the scene meanwhile) */
  static passengers(transport: THREE.Object3D): Unit[] {
    return (transport.userData.passengers ??= []) as Unit[]
  }

  /** How many soldiers a unit can carry (0: it is no transport) */
  static capacity(object: THREE.Object3D) {
    return TRANSPORTS[object.userData.id as string] ?? 0
  }

  /** Whether a soldier can get into a transport: of the same side, there is room, it is up on the ground */
  canBoard(unit: Unit, transport: THREE.Object3D) {
    const passengers = Battlefield.passengers(transport)
    const coming = this.units.filter(u => u.object.userData.boarding === transport && u !== unit).length
    return unit.infantry && !unit.object.userData.dead && !transport.userData.dead && transport.parent === this.scene
      && transport.userData.owner === unit.object.userData.owner && !transport.userData.underground
      && passengers.length + coming < Battlefield.capacity(transport)
  }

  /** Sends soldiers into a transport (those for whom there is room); returns how many go */
  board(units: Unit[], transport: THREE.Object3D) {
    let going = 0
    for (const unit of units) {
      if (!this.canBoard(unit, transport)) continue
      unit.object.userData.boarding = transport
      unit.followPath(findPath(this.navFor(unit.object), unit.object.position, transport.position))
      going++
    }
    return going
  }

  /** The soldiers on their way into a transport: in when they reach it, after it when it drives off */
  private updateBoarding() {
    for (const unit of [...this.units]) {
      const transport = unit.object.userData.boarding as THREE.Object3D | undefined
      if (!transport) continue
      const room = Battlefield.passengers(transport).length < Battlefield.capacity(transport)
      if (unit.object.userData.dead || transport.userData.dead || transport.parent !== this.scene || transport.userData.underground || !room) {
        delete unit.object.userData.boarding
        continue
      }
      const distance = Math.hypot(unit.object.position.x - transport.position.x, unit.object.position.z - transport.position.z)
      if (distance <= BOARD_REACH) this.embark(unit, transport)
      else if (!unit.walking || (unit.destination && unit.destination.distanceTo(transport.position.clone().setY(unit.destination.y)) > 0.5)) {
        unit.followPath(findPath(this.navFor(unit.object), unit.object.position, transport.position))
      }
    }
  }

  /** Puts soldiers straight into a transport, as many as fit (a mission's Nod APC, loaded from the start); returns them */
  load(transport: THREE.Object3D, units: Unit[]) {
    const loaded = units.filter(unit => this.units.includes(unit) && this.canBoard(unit, transport))
    for (const unit of loaded) this.embark(unit, transport)
    return loaded
  }

  /** A soldier gets in: off the map until the transport lets it out */
  private embark(unit: Unit, transport: THREE.Object3D) {
    delete unit.object.userData.boarding
    unit.stop()
    this.scene.remove(unit.object)
    for (const list of [this.selectables, this.selection] as THREE.Object3D[][]) {
      const i = list.indexOf(unit.object)
      if (i >= 0) list.splice(i, 1)
    }
    this.units.splice(this.units.indexOf(unit), 1)
    Battlefield.passengers(transport).push(unit)
  }

  /** Whether a transport can let its soldiers out where it is: it has some, and is up on the ground */
  canUnload(transport: THREE.Object3D) {
    const unit = transport.userData.unit as Unit | undefined
    return Battlefield.passengers(transport).length > 0 && !transport.userData.dead && !transport.userData.underground
      && !!unit && !unit.changingPosture && !this.tunnels.some(t => t.unit === unit)
  }

  /** Lets the soldiers out round the transport; returns them */
  unload(transport: THREE.Object3D) {
    if (!this.canUnload(transport)) return []
    const out = Battlefield.passengers(transport).splice(0)
    const unit = transport.userData.unit as Unit
    unit.stop()
    out.forEach((passenger, i) => {
      // round it, behind it first (where the door is)
      const angle = transport.rotation.y + Math.PI + (i - (out.length - 1) / 2) * 0.7
      const at = transport.position.clone().add(new THREE.Vector3(Math.sin(angle), 0, Math.cos(angle)).multiplyScalar(UNLOAD_DISTANCE))
      const spot = this.openSpot(at)
      passenger.object.position.copy(spot).setY(this.heightAt(spot.x, spot.z))
      passenger.object.rotation.y = angle
      this.scene.add(passenger.object)
      this.units.push(passenger)
      this.addSelectable(passenger.object)
    })
    return out
  }

  /**
   * When the transport has got where it was sent (on or under the ground) and stands,
   * it lets its soldiers out and hands them to `then` (the missions' Nod APC)
   */
  deliver(transport: THREE.Object3D, then: (soldiers: Unit[]) => void) {
    transport.userData.deliver = then
  }

  private updateDeliveries() {
    for (const unit of this.units) {
      const then = unit.object.userData.deliver as ((soldiers: Unit[]) => void) | undefined
      if (!then || unit.walking || !this.canUnload(unit.object)) continue
      delete unit.object.userData.deliver
      then(this.unload(unit.object))
    }
  }

  /** Units under the ground (the subterranean APC): where they come up again */
  private readonly tunnels: { unit: Unit, to: THREE.Vector3, phase: 'down' | 'moving' | 'up', next?: THREE.Vector3 }[] = []

  /**
   * Whether a vehicle can dig in (or into the ground) at a point: its cell is flat, on
   * the map and free – not on a slope, a ramp or a cliff
   */
  canDig(at: THREE.Vector3) {
    const x = Math.floor(at.x)
    const z = Math.floor(at.z)
    return this.free(x, z) && this.terrain.cell(x, z) === Cell.Flat
  }

  /** Whether a unit digs in where it stands (the Tick Tank, clip Deploy) */
  static digsIn(object: THREE.Object3D) {
    return DIGGERS.has(object.userData.id)
  }

  /**
   * A Tick Tank digs in where it stands (or comes out again, if it is dug in): it
   * stands nose down in the ground, its turret out of its tail. Returns false if the
   * ground there does not let it (a slope, a ramp).
   */
  toggleDigIn(unit: Unit) {
    if (!Battlefield.digsIn(unit.object) || unit.changingPosture) return false
    if (unit.posture === POSTURES.dig.posture) {
      void unit.change(POSTURES.dig.out, undefined)
      return true
    }
    if (!this.canDig(unit.object.position)) return false
    unit.stop()
    void unit.change(POSTURES.dig.in, POSTURES.dig.posture)
    return true
  }

  /**
   * The subterranean APC digs straight down where it stands, goes under the ground in
   * a straight line to the flat cell nearest `to` and comes up there.
   */
  private burrow(unit: Unit, to: THREE.Vector3) {
    const object = unit.object
    const tunnel: (typeof this.tunnels)[number] = { unit, to: this.openSpot(to, true), phase: 'down' }
    this.tunnels.push(tunnel)
    // under the ground already: off at once
    if (unit.posture === POSTURES.tunnel.posture) {
      tunnel.phase = 'moving'
      return
    }
    void unit.change(POSTURES.tunnel.in, POSTURES.tunnel.posture).then(() => {
      if (object.userData.dead) return
      // out of sight and out of reach
      object.userData.underground = true
      object.visible = false
      tunnel.phase = 'moving'
    })
  }

  /** A subterranean APC starts out under the ground, out of sight (a mission's Nod APC on its way in) */
  startUnderground(unit: Unit) {
    if (!TUNNELLERS.has(unit.object.userData.id)) return
    unit.object.userData.underground = true
    unit.object.visible = false
    void unit.change('', POSTURES.tunnel.posture)
  }

  /** A subterranean APC digs into the ground where it stands and is gone (off the map) */
  vanish(unit: Unit) {
    const object = unit.object
    if (!TUNNELLERS.has(object.userData.id) || !this.canDig(object.position)) return false
    void unit.change(POSTURES.tunnel.in, POSTURES.tunnel.posture).then(() => {
      if (!object.userData.dead) this.remove(object)
    })
    return true
  }

  private updateTunnels(seconds: number) {
    for (const tunnel of [...this.tunnels]) {
      const { unit } = tunnel
      const object = unit.object
      if (object.userData.dead) {
        this.tunnels.splice(this.tunnels.indexOf(tunnel), 1)
        continue
      }
      if (tunnel.phase !== 'moving') continue
      const way = tunnel.to.clone().sub(object.position).setY(0)
      const step = unit.speed * TUNNEL_SPEED * seconds
      if (way.length() > step) {
        object.position.addScaledVector(way.normalize(), step)
        object.rotation.y = Math.atan2(way.x, way.z)
        continue
      }
      // there: up again
      object.position.x = tunnel.to.x
      object.position.z = tunnel.to.z
      tunnel.phase = 'up'
      object.visible = true
      void unit.change(POSTURES.tunnel.out, undefined).then(() => {
        object.userData.underground = false
        this.tunnels.splice(this.tunnels.indexOf(tunnel), 1)
        if (tunnel.next && !object.userData.dead) this.walk(unit, tunnel.next)
      })
    }
  }

  /** All buildings on the map */
  get structureObjects() {
    return [...this.structures.values()].flat()
  }

  /** Distance from a point to an object: to the edge of a building's foundation, else to its position */
  static reach(from: THREE.Vector3, object: THREE.Object3D) {
    const f = object.userData.footprint as Footprint | undefined
    if (!f) return Math.hypot(from.x - object.position.x, from.z - object.position.z)
    const dx = Math.max(f.x - from.x, 0, from.x - (f.x + f.w))
    const dz = Math.max(f.z - from.z, 0, from.z - (f.z + f.h))
    return Math.hypot(dx, dz)
  }

  /** The point of an object closest to `from` (on a building's foundation edge, else its position) */
  static closestPoint(from: THREE.Vector3, object: THREE.Object3D) {
    const f = object.userData.footprint as Footprint | undefined
    if (!f) return object.position.clone()
    return new THREE.Vector3(THREE.MathUtils.clamp(from.x, f.x, f.x + f.w), 0, THREE.MathUtils.clamp(from.z, f.z, f.z + f.h))
  }

  /** Takes a destroyed building off the map: its foundation becomes free ground again. */
  removeStructure(object: THREE.Object3D) {
    const drop = <T>(list: T[], item: T) => {
      const i = list.indexOf(item)
      if (i >= 0) list.splice(i, 1)
    }
    drop(this.footprints, object.userData.footprint)
    drop(this.selectables, object)
    drop(this.selection, object)
    const list = this.structures.get(object.userData.id as string)
    if (list) drop(list, object)
    // the neighbouring walls lose their arm towards it
    const footprint = object.userData.footprint as Footprint | undefined
    if (footprint && WALLS.has(object.userData.id)) this.connectWalls(footprint.x, footprint.z)
  }

  /** Takes a unit or building off the map (after it was destroyed). */
  remove(object: THREE.Object3D) {
    this.scene.remove(object)
    const drop = <T>(list: T[], item: T) => {
      const i = list.indexOf(item)
      if (i >= 0) list.splice(i, 1)
    }
    drop(this.selectables, object)
    drop(this.selection, object)
    const unit = object.userData.unit as Unit | undefined
    if (unit) {
      drop(this.units, unit)
      unit.dispose()
    }
    // the soldiers inside a transport go with it
    for (const passenger of Battlefield.passengers(object).splice(0)) passenger.dispose()
  }

  /** Adds an effect object (muzzle flash, hit puff …) to the scene; `remove` takes it away. */
  addEffect(object: THREE.Object3D) {
    this.scene.add(object)
  }

  removeEffect(object: THREE.Object3D) {
    this.scene.remove(object)
  }

  /**
   * The jets of a dropship's engines, as its clips set them (the plumes out of the
   * nozzles, the lift jets downwards: shown by their scale), the dust they blow up near
   * the ground; when it is shot down the burning engine and wreck, and the blast.
   */
  private engineEffects(ship: THREE.Object3D, seconds: number) {
    let nodes = this.engines.get(ship)
    if (!nodes) {
      const named = (pattern: RegExp) => {
        const found: THREE.Object3D[] = []
        ship.traverse(node => pattern.test(node.name) && found.push(node))
        return found
      }
      nodes = { plumes: named(/^Plume\d+$/), lifts: named(/^Lift\d+$/), fires: named(/^(EngineFire|WreckFire)$/), blast: named(/^Blast$/)[0], blasted: false }
      this.engines.set(ship, nodes)
      // the particles take the place of the model's glowing cones (their nodes still tell the thrust)
      for (const node of [...nodes.plumes, ...nodes.lifts, ...nodes.fires]) {
        node.traverse((mesh) => {
          if ((mesh as THREE.Mesh).isMesh) mesh.visible = false
        })
      }
    }
    // as many puffs per second at any frame rate
    const puffs = Math.max(1, Math.round(seconds * 60))
    ship.updateMatrixWorld(true)
    const at = new THREE.Vector3()
    const direction = new THREE.Vector3()
    // a jet: from the node's origin along its own axis (glTF: back is -z, down is -y)
    const jet = (node: THREE.Object3D, axis: THREE.Vector3, strength: number) => {
      if (strength < 0.05) return
      node.getWorldPosition(at)
      direction.copy(axis).transformDirection(node.matrixWorld)
      // a weak jet still shows: the flame's size follows the thrust only partly
      for (let i = 0; i < puffs; i++) this.effects.thrust(at, direction, 0.45 + 0.55 * Math.min(1, strength), at.y)
    }
    for (const plume of nodes.plumes) jet(plume, new THREE.Vector3(0, 0, -1), plume.scale.z)
    for (const lift of nodes.lifts) jet(lift, new THREE.Vector3(0, -1, 0), lift.scale.y)
    for (const fire of nodes.fires) {
      if (fire.scale.x < 0.1) continue
      fire.getWorldPosition(at)
      for (let i = 0; i < puffs; i++) this.effects.burn(at, 0.35 * fire.scale.x)
    }
    // the wreck explodes as it hits the ground
    const blast = nodes.blast
    if (blast) {
      const showing = blast.scale.x > 0.05
      if (showing && !nodes.blasted) this.effects.explosion(blast.getWorldPosition(at), 1.6)
      nodes.blasted = showing
    }
  }

  dispose() {
    this.effects.dispose()
    for (const unit of this.units) unit.dispose()
    for (const ship of this.aircraft) ship.dispose()
    for (const resource of this.disposables) resource.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
