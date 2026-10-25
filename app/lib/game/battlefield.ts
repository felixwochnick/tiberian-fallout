import * as THREE from 'three'
import { GLTFLoader, type GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { clone as cloneSkinned } from 'three/examples/jsm/utils/SkeletonUtils.js'
import { SCROLL_DIRECTIONS, type CursorKind, type ScrollDirection } from '../input/cursor'
import { findPath, type NavMap } from './pathfinding'
import { Unit } from './unit'
import { Dropship, type DropshipFlight } from './dropship'

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

/** Height (cells) of the placeholder buildings until they have models */
const PLACEHOLDER_HEIGHT: Record<string, number> = {
  GACNST: 0.55, GAPOWR: 0.6, PROC: 0.45, GASILO: 0.35, GACTWR: 0.5, GAWEAP: 0.6, GAVULC: 0.4, GARADR: 0.7,
}

interface Footprint { x: number, z: number, w: number, h: number, owner: Owner }

export type Owner = 'player' | 'enemy'

/** Structures that join up with their neighbours (see connectWalls) */
const WALLS = new Set(['GASAND'])

/** A deploying MCV stands in the middle of its foundation, facing the front (+z), like
 * the vehicle at the start of the yard's Build clip (see blender/GACNST.py) */
const DEPLOY_HEADING = 0

export const ZOOM = { min: 0.75, max: 2.5, step: 1.15 }

/** How close (CSS pixels) the cursor has to get to the screen edge to scroll */
const EDGE = 12
/** Scroll speed in screen pixels per second at zoom 1 */
const SCROLL_SPEED = 1100

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

/** Plain temperate ground: dry ochre earth like in Tiberian Sun (no cell grid, like the original). */
const GroundShader = {
  vertexShader: /* glsl */ `
    varying vec2 vCell;
    void main() {
      vec4 world = modelMatrix * vec4(position, 1.0);
      vCell = world.xz;
      gl_Position = projectionMatrix * viewMatrix * world;
    }`,
  fragmentShader: /* glsl */ `
    varying vec2 vCell;
    ${NOISE}
    void main() {
      vec2 c = vCell;
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
      gl_FragColor = vec4(earth, 1.0);
    }`,
}

export class Battlefield {
  private readonly renderer: THREE.WebGLRenderer
  private readonly scene = new THREE.Scene()
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
  /** Preview of a structure being placed: its cells, green where it may go, red otherwise */
  private placement?: { w: number, h: number, adjacent: number, preview: THREE.Group, cell?: [number, number], valid: boolean }

  /** Everything selected: one building, or one or more units */
  selection: THREE.Object3D[] = []
  /** The selected object if exactly one is selected */
  get selected() {
    return this.selection.length === 1 ? this.selection[0] : undefined
  }

  /** Rubber band while dragging a selection box (client pixels) */
  private band?: { x0: number, y0: number, x1: number, y1: number }
  private readonly groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)

  constructor(private readonly container: HTMLElement, readonly width: number, readonly height: number) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.setClearColor(0x000000)
    // the ground shader writes display colours itself; the models are lit PBR in sRGB
    this.renderer.outputColorSpace = THREE.SRGBColorSpace
    container.appendChild(this.renderer.domElement)

    // the ground: a rectangle along the screen axes (u right, v down), turned by the
    // azimuth so it lies diagonally over the cell grid
    this.bounds = { u: [0, width], v: [0, height] }
    const geometry = new THREE.PlaneGeometry(width, height)
    geometry.rotateX(-Math.PI / 2)
    geometry.translate(width / 2, 0, height / 2)
    geometry.rotateY(AZIMUTH)
    const material = new THREE.ShaderMaterial(GroundShader)
    this.disposables.push(geometry, material)
    this.scene.add(new THREE.Mesh(geometry, material))

    // light for the models: sun from the top left of the screen like the original's art,
    // a sky fill and soft shadows on the ground
    const sun = new THREE.DirectionalLight(0xfff4e0, 2.6)
    sun.position.set(-6, 9, -2)
    this.scene.add(sun, sun.target, new THREE.HemisphereLight(0xdfe8ff, 0x5a5040, 1.1))
    this.overlayScene.add(this.selectionFrame)
    this.disposables.push(this.selectionFrame.geometry, this.selectionFrame.material as THREE.Material)
    this.u = (this.bounds.u[0] + this.bounds.u[1]) / 2
    this.v = (this.bounds.v[0] + this.bounds.v[1]) / 2
    this.resize()
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

  render() {
    const now = performance.now()
    const seconds = Math.min(0.1, (now - this.lastFrame) / 1000) // no jump after a stall
    this.lastFrame = now
    for (const mixer of this.mixers) mixer.update(seconds)
    for (const item of this.rising) {
      item.time = Math.min(1, item.time + seconds / RISE_SECONDS)
      item.object.scale.y = Math.max(0.02, 1 - (1 - item.time) ** 3)
    }
    this.rising.splice(0, this.rising.length, ...this.rising.filter(item => item.time < 1))
    for (const unit of this.units) unit.update(seconds)
    for (const ship of [...this.aircraft]) ship.update(seconds)
    this.updateDeploying(seconds)
    this.renderer.render(this.scene, this.camera)
    this.drawSelection()
    if (this.selectionFrame.visible) {
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
    if (!hit) return undefined
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
    const point = this.raycaster.ray.intersectPlane(this.groundPlane, new THREE.Vector3())
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
    const units = this.selection.filter(Battlefield.own).map(object => object.userData.unit).filter(Boolean)
    const columns = Math.ceil(Math.sqrt(units.length))
    units.forEach((unit, i) => {
      const offset = new THREE.Vector3((i % columns) - (columns - 1) / 2, 0, Math.floor(i / columns) - (columns - 1) / 2).multiplyScalar(0.45)
      this.walk(unit, point.clone().add(offset))
    })
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
  /** Corner frame and health bar of one selected object, around its outline on screen. */
  private drawFrame(
    object: THREE.Object3D,
    w: number,
    h: number,
    rect: (x0: number, y0: number, x1: number, y1: number, colour: [number, number, number]) => void,
    segment: (ax: number, ay: number, bx: number, by: number, width: number, colour: [number, number, number]) => void,
  ) {
    // buildings stand still: their bounds are taken once (a waving flag would make the frame twitch)
    const bounds: THREE.Box3 = object.userData.kind === 'unit'
      ? new THREE.Box3().setFromObject(object)
      : (object.userData.bounds ??= new THREE.Box3().setFromObject(object))
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
      // corners short strokes along its three edges, a fifth of each edge long
      const size = bounds.getSize(new THREE.Vector3())
      const corner = new THREE.Vector3()
      const end = new THREE.Vector3()
      for (let i = 0; i < 8; i++) {
        corner.set(i & 1 ? bounds.max.x : bounds.min.x, i & 2 ? bounds.max.y : bounds.min.y, i & 4 ? bounds.max.z : bounds.min.z)
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

    // health bar above the frame
    const health = THREE.MathUtils.clamp(object.userData.health ?? 1, 0, 1)
    const colour: [number, number, number] = health > 0.5 ? [0.1, 0.95, 0.15] : health > 0.25 ? [1, 0.85, 0.1] : [1, 0.15, 0.1]
    const cell = 4
    const gap = 1
    const barTop = top - 9
    const cells = Math.max(1, Math.floor((right - left - gap) / (cell + gap)))
    const barRight = left + cells * (cell + gap) + gap
    rect(left, barTop, barRight, barTop + cell + 2 * gap, [0.02, 0.02, 0.02])
    for (let i = 0; i < Math.ceil(cells * health); i++) {
      const x = left + gap + i * (cell + gap)
      rect(x, barTop + gap, x + cell, barTop + gap + cell, colour)
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
    for (const object of this.selection) this.drawFrame(object, w, h, rect, segment)

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

    // where the selected units walk to: an animated dashed green line to a small diamond
    const shift = performance.now() / 1000 * 24
    for (const object of this.selection) {
      const destination = object.userData.unit?.destination as THREE.Vector3 | undefined
      if (!destination) continue
      const [x0, y0] = toScreen(object.position)
      const [x1, y1] = toScreen(destination)
      dashes(x0, y0, x1, y1, shift)
      segment(x1 - 6, y1, x1, y1 - 3, 2, green)
      segment(x1, y1 - 3, x1 + 6, y1, 2, green)
      segment(x1 + 6, y1, x1, y1 + 3, 2, green)
      segment(x1, y1 + 3, x1 - 6, y1, 2, green)
    }

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

  /** Whether a foundation lies on the map, on free ground and close enough to the base */
  canPlace(x: number, z: number, w: number, h: number, adjacent: number) {
    // all four corners on the map (the map is a rectangle in screen axes)
    for (const [cx, cz] of [[x, z], [x + w, z], [x, z + h], [x + w, z + h]] as const) {
      const corner = new THREE.Vector3(cx, 0, cz)
      const u = corner.dot(this.screenRight)
      const v = corner.dot(this.screenDown)
      if (u < this.bounds.u[0] || u > this.bounds.u[1] || v < this.bounds.v[0] || v > this.bounds.v[1]) return false
    }
    const overlaps = (f: Footprint) => x < f.x + f.w && f.x < x + w && z < f.z + f.h && f.z < z + h
    if (this.footprints.some(overlaps)) return false
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
    const material = new THREE.MeshBasicMaterial({ color: 0x3cff4a, transparent: true, opacity: 0.45, depthWrite: false })
    for (let i = 0; i < w; i++) {
      for (let j = 0; j < h; j++) {
        const cell = new THREE.Mesh(geometry, material)
        cell.position.set(i + 0.5, 0.02, j + 0.5)
        preview.add(cell)
      }
    }
    preview.visible = false
    this.scene.add(preview)
    this.placement = { w, h, adjacent, preview, valid: false }
  }

  /** Moves the preview under the cursor; green if it may be placed there, red if not. */
  updatePlacement(clientX: number, clientY: number) {
    const placement = this.placement
    if (!placement) return
    const cell = this.cellAt(clientX, clientY, placement.w, placement.h)
    placement.cell = cell
    placement.preview.visible = !!cell
    if (!cell) return
    placement.preview.position.set(cell[0], 0, cell[1])
    placement.valid = this.canPlace(cell[0], cell[1], placement.w, placement.h, placement.adjacent)
    const material = (placement.preview.children[0] as THREE.Mesh).material as THREE.MeshBasicMaterial
    material.color.set(placement.valid ? 0x3cff4a : 0xff3a2a)
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
    ;(cell?.material as THREE.Material | undefined)?.dispose()
    this.placement = undefined
  }

  /**
   * Puts a structure on the map with its foundation (w × h cells) at cell (x, z): the
   * model from `url` (built up by its own animation), or else a simple placeholder
   * that rises out of the ground.
   */
  async addStructure(id: string, x: number, z: number, w: number, h: number, url?: string, houseColour = 0xd8b43a, owner: Owner = 'player') {
    const centre = new THREE.Vector3(x + w / 2, 0, z + h / 2)
    const footprint = { x, z, w, h, owner }
    this.footprints.push(footprint)
    const object = url ? await this.addBuilding(url, centre, houseColour) : this.addPlaceholder(id, centre, w, h, houseColour)
    object.userData.id = id
    object.userData.owner = owner
    object.userData.footprint = footprint
    this.structures.set(id, [...(this.structures.get(id) ?? []), object])
    if (WALLS.has(id)) this.connectWalls(x, z)
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
    this.scene.add(group)
    this.addSelectable(group)
    this.rising.push({ object: group, time: 0 })
    return group
  }

  /** A point of the map given in screen axes (u across, v down, in cells from the top left corner) */
  mapPoint(u: number, v: number) {
    return this.screenRight.clone().multiplyScalar(u).addScaledVector(this.screenDown, v)
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

  /** Loads a model: "Remap" in the house colour, "Glow*" halos shine additively. */
  private async loadModel(url: string, houseColour: number) {
    const gltf = await new GLTFLoader().loadAsync(url)
    gltf.scene.traverse((node) => {
      const mesh = node as THREE.Mesh
      if (!mesh.isMesh) return
      for (const mat of [mesh.material].flat() as THREE.MeshStandardMaterial[]) {
        if (mat.name === 'Remap') mat.color.set(houseColour)
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
    return this.canPlace(x, z, 3, 3, Infinity) ? [x, z] : undefined
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
    gltf.scene.position.copy(from).setY(0)
    const ship = new Dropship(gltf.scene, gltf.animations, flight)
    ship.onGone = () => {
      this.scene.remove(gltf.scene)
      this.aircraft.splice(this.aircraft.indexOf(ship), 1)
      ship.dispose()
    }
    this.scene.add(gltf.scene)
    this.aircraft.push(ship)
    return ship
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
      mixer.update(0) // the first frame of the build before the model is shown
      this.mixers.push(mixer)
      gltf.scene.userData.mixer = mixer
      gltf.scene.userData.clips = gltf.animations
    }
    gltf.scene.position.copy(at)
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
   * The material "Remap" gets the house colour. Move it with `walkTo`.
   */
  async addUnit(url: string, at: THREE.Vector3, houseColour = 0xd8b43a, owner: 'player' | 'enemy' = 'player') {
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
        if (mat.name === 'Remap') mat.color.set(houseColour)
        this.disposables.push(mat)
        return mat
      })
      if ((mesh.material as THREE.Material[]).length === 1) mesh.material = (mesh.material as THREE.Material[])[0]!
    })
    object.position.copy(at)
    object.userData.kind = 'unit' // can be picked with the selection box
    object.userData.owner = owner
    this.scene.add(object)
    this.addSelectable(object)
    const unit = new Unit(object, gltf.animations)
    object.userData.unit = unit
    this.units.push(unit)
    return unit
  }


  /** The map for pathfinding: cells on the map and not under a building */
  readonly nav: NavMap = {
    free: (x, z) => {
      const centre = new THREE.Vector3(x + 0.5, 0, z + 0.5)
      const u = centre.dot(this.screenRight)
      const v = centre.dot(this.screenDown)
      if (u < this.bounds.u[0] || u > this.bounds.u[1] || v < this.bounds.v[0] || v > this.bounds.v[1]) return false
      return !this.footprints.some(f => x >= f.x && x < f.x + f.w && z >= f.z && z < f.z + f.h)
    },
  }

  /** Sends a unit to a point on the shortest way round the buildings. */
  walk(unit: Unit, to: THREE.Vector3) {
    unit.followPath(findPath(this.nav, unit.object.position, to))
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
  }

  /** Adds an effect object (muzzle flash, hit puff …) to the scene; `remove` takes it away. */
  addEffect(object: THREE.Object3D) {
    this.scene.add(object)
  }

  removeEffect(object: THREE.Object3D) {
    this.scene.remove(object)
  }

  dispose() {
    for (const unit of this.units) unit.dispose()
    for (const ship of this.aircraft) ship.dispose()
    for (const resource of this.disposables) resource.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
