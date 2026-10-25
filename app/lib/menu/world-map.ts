import * as THREE from 'three'

/**
 * The map of the briefing: the earth as a sphere, seen from above a region, rebuilt
 * after the original's map selection. The terrain is one fragment shader (a ray onto
 * the sphere per pixel: shaded relief on the land, dark seas glowing at the coasts, the
 * lines of latitude and longitude), so the same picture serves the globe at the start
 * and the close view it zooms down to. Borders, the territories of GDI and Nod and the
 * targets are vectors drawn over it on a 2D canvas, sharp at any zoom.
 *
 * Data (public/geo, from Natural Earth, public domain): regions.json with the land,
 * the countries (ids like `USA`, `DEU`) and the states of some countries (ids like
 * `US-NV`, `DE-BY`); relief.jpg, the shaded relief of the whole world.
 */

export type Owner = 'gdi' | 'nod'

export interface MissionMap {
  /** The middle of the view [longitude, latitude] */
  center: [number, number]
  /** How many degrees of longitude the view shows across */
  span: number
  /** Who holds which country or state (states are drawn over their country) */
  regions: Record<string, Owner>
  /** Regions that can be clicked: each starts a mission (default: the briefing's own) */
  targets: { region: string, mission?: string }[]
}

interface Region {
  id: string
  name: string
  rings: number[][]
  /** Middle (unit vector) and angular radius of the region, to skip it when out of sight */
  centre: THREE.Vector3
  radius: number
  /** Where its crosshair sits: the centroid of its largest part */
  label: THREE.Vector3
}

interface GeoData {
  land: number[][]
  countries: Region[]
  states: Region[]
}

/** The crosshair: radius of its inner ring and how far its spokes reach (outer ring = 1) */
const INNER_RADIUS = 0.45
const SPOKE_END = 1.32
/** Speed of the pulse under the cursor (radians per second; about 1.8 s per beat) */
const HOVER_BEAT = 3.5

/** Seconds of the intro: zoom from the globe down to the region, then the territories fade up, then the targets fly in */
export const MAP_TIMES = { zoom: 3.2, overlay: 1.0, target: 0.7 }

const COLOURS = {
  gdi: 'rgba(232, 200, 140, 0.55)',
  gdiEdge: 'rgba(255, 236, 180, 0.9)',
  nod: 'rgba(214, 30, 14, 0.62)',
  nodEdge: 'rgba(255, 90, 60, 0.9)',
  border: 'rgba(250, 230, 150, 0.55)',
  stateBorder: 'rgba(250, 230, 150, 0.3)',
  coast: 'rgba(200, 245, 255, 0.75)',
  target: '#3cff3c',
}

export function toVector(lon: number, lat: number, target = new THREE.Vector3()) {
  const l = THREE.MathUtils.degToRad(lon)
  const p = THREE.MathUtils.degToRad(lat)
  return target.set(Math.cos(p) * Math.sin(l), Math.sin(p), Math.cos(p) * Math.cos(l))
}

function toLonLat(v: THREE.Vector3): [number, number] {
  return [THREE.MathUtils.radToDeg(Math.atan2(v.x, v.z)), THREE.MathUtils.radToDeg(Math.asin(THREE.MathUtils.clamp(v.y, -1, 1)))]
}

function withBounds(raw: { id: string, name: string, rings: number[][] }): Region {
  const centre = new THREE.Vector3()
  const v = new THREE.Vector3()
  let count = 0
  for (const ring of raw.rings) {
    for (let i = 0; i < ring.length; i += 2) {
      centre.add(toVector(ring[i]!, ring[i + 1]!, v))
      count++
    }
  }
  centre.divideScalar(count).normalize()
  let radius = 0
  for (const ring of raw.rings) {
    for (let i = 0; i < ring.length; i += 2) radius = Math.max(radius, centre.angleTo(toVector(ring[i]!, ring[i + 1]!, v)))
  }
  return { ...raw, centre, radius, label: centroid(raw.rings) }
}

/** The area centroid of the largest ring (in plain lon/lat, fine for a state or country) */
function centroid(rings: number[][]) {
  let best = { area: 0, lon: 0, lat: 0 }
  for (const ring of rings) {
    let area = 0
    let lon = 0
    let lat = 0
    for (let i = 0, j = ring.length - 2; i < ring.length; j = i, i += 2) {
      const cross = ring[j]! * ring[i + 1]! - ring[i]! * ring[j + 1]!
      area += cross
      lon += (ring[j]! + ring[i]!) * cross
      lat += (ring[j + 1]! + ring[i + 1]!) * cross
    }
    if (Math.abs(area) > Math.abs(best.area)) best = { area, lon: lon / (3 * area), lat: lat / (3 * area) }
  }
  return toVector(best.lon, best.lat)
}

/** Whether (lon, lat) lies in a ring (even-odd, in plain lon/lat) */
function inRing(ring: number[], lon: number, lat: number) {
  let inside = false
  for (let i = 0, j = ring.length - 2; i < ring.length; j = i, i += 2) {
    const xi = ring[i]!
    const yi = ring[i + 1]!
    const xj = ring[j]!
    const yj = ring[j + 1]!
    if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}

/** Land mask of the whole world (equirectangular): R = land, G = land blurred (the glow along the coasts) */
function landMask(land: number[][], width: number) {
  const height = width / 2
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')!
  const path = new Path2D()
  for (const ring of land) {
    for (let i = 0; i < ring.length; i += 2) {
      const x = ((ring[i]! + 180) / 360) * width
      const y = ((90 - ring[i + 1]!) / 180) * height
      if (i) path.lineTo(x, y)
      else path.moveTo(x, y)
    }
    path.closePath()
  }
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, width, height)
  ctx.globalCompositeOperation = 'lighter'
  ctx.filter = `blur(${width / 400}px)`
  ctx.fillStyle = '#00ff00'
  ctx.fill(path)
  ctx.filter = 'none'
  ctx.fillStyle = '#ff0000'
  ctx.fill(path)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.NoColorSpace
  texture.generateMipmaps = false
  texture.minFilter = THREE.LinearFilter
  return texture
}

const TerrainShader = {
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = vec4(position.xy, 0.0, 1.0);
    }`,
  fragmentShader: /* glsl */ `
    uniform mat4 uInvViewProj;
    uniform vec3 uCamera;
    uniform sampler2D tRelief;
    uniform sampler2D tMask;
    varying vec2 vUv;

    const float PI = 3.14159265;

    // distance (in degrees) to the nearest line of a grid every 'step' degrees
    float gridLine(float degrees, float step) {
      float d = abs(fract(degrees / step + 0.5) - 0.5) * step;
      return 1.0 - smoothstep(0.0, fwidth(degrees) * 1.2, d);
    }

    void main() {
      vec2 ndc = vUv * 2.0 - 1.0;
      vec4 far = uInvViewProj * vec4(ndc, 1.0, 1.0);
      vec3 dir = normalize(far.xyz / far.w - uCamera);
      // the ray onto the unit sphere
      float b = dot(uCamera, dir);
      float c = dot(uCamera, uCamera) - 1.0;
      float h = b * b - c;
      if (h < 0.0) {
        gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0); // space
        return;
      }
      vec3 p = uCamera + dir * (-b - sqrt(h));
      float lon = atan(p.x, p.z);
      float lat = asin(clamp(p.y, -1.0, 1.0));
      vec2 uv = vec2(lon / (2.0 * PI) + 0.5, lat / PI + 0.5);
      float relief = texture2D(tRelief, uv).r;
      vec2 mask = texture2D(tMask, uv).rg;

      // land: brownish-pink rock, the relief's light and shadow on it
      float shade = (relief - 0.82) * 3.2;
      vec3 land = vec3(0.5, 0.33, 0.26) * (0.85 + shade) + vec3(0.2, 0.12, 0.08) * max(shade, 0.0);
      // sea: deep dark blue, glowing pale cyan along the coasts
      float glow = smoothstep(0.0, 1.0, mask.g);
      vec3 sea = mix(vec3(0.02, 0.035, 0.07), vec3(0.08, 0.13, 0.22), glow);
      sea += vec3(0.45, 0.8, 0.9) * pow(glow, 2.2) * 0.7;
      vec3 colour = mix(sea, land, smoothstep(0.35, 0.65, mask.r));

      // lines of latitude and longitude every 15 degrees
      float grid = max(gridLine(degrees(lon), 15.0), gridLine(degrees(lat), 15.0));
      colour = mix(colour, vec3(0.55, 0.85, 0.95), grid * 0.55);

      // darker towards the rim of the globe
      float facing = dot(normalize(p), -dir);
      colour *= mix(0.35, 1.0, smoothstep(0.0, 0.5, facing));
      gl_FragColor = vec4(colour, 1.0);
    }`,
}

export class WorldMap {
  readonly scene = new THREE.Scene()
  readonly camera = new THREE.PerspectiveCamera(30, 16 / 10, 0.01, 20)
  private readonly terrain: THREE.ShaderMaterial
  /** The vectors, drawn on a canvas of the screen's size and laid over the terrain */
  private readonly overlay = document.createElement('canvas')
  private readonly overlayTexture: THREE.CanvasTexture
  private readonly overlayScene = new THREE.Scene()
  private readonly disposables: { dispose: () => void }[] = []
  private readonly targets: { region: Region, mission?: string, at: THREE.Vector3 }[]
  /** The 3D crosshairs over the targets, in screen pixels (y up from the top, so negative) */
  private readonly targetScene = new THREE.Scene()
  private readonly targetCamera = new THREE.OrthographicCamera(0, 1, 0, -1, -1000, 1000)
  private readonly crosshairs: ReturnType<WorldMap['buildCrosshairs']>
  /** Seconds since the intro began */
  private time = 0
  /** The target under the cursor */
  hovered: number | undefined

  static async load(map: MissionMap) {
    const [data, relief] = await Promise.all([
      fetch('/geo/regions.json').then(r => r.json()) as Promise<{ land: number[][], countries: { id: string, name: string, rings: number[][] }[], states: { id: string, name: string, rings: number[][] }[] }>,
      new THREE.TextureLoader().loadAsync('/geo/relief.jpg'),
    ])
    const geo: GeoData = { land: data.land, countries: data.countries.map(withBounds), states: data.states.map(withBounds) }
    return new WorldMap(map, geo, relief)
  }

  private constructor(private readonly map: MissionMap, private readonly geo: GeoData, relief: THREE.Texture) {
    relief.colorSpace = THREE.NoColorSpace
    relief.generateMipmaps = false // no seam where the texture wraps round
    relief.minFilter = THREE.LinearFilter
    const mask = landMask(geo.land, 4096)
    this.terrain = new THREE.ShaderMaterial({
      vertexShader: TerrainShader.vertexShader,
      fragmentShader: TerrainShader.fragmentShader,
      uniforms: {
        uInvViewProj: { value: new THREE.Matrix4() },
        uCamera: { value: new THREE.Vector3() },
        tRelief: { value: relief },
        tMask: { value: mask },
      },
      depthTest: false,
      depthWrite: false,
    })
    const quad = new THREE.PlaneGeometry(2, 2)
    this.scene.add(new THREE.Mesh(quad, this.terrain))
    this.overlayTexture = new THREE.CanvasTexture(this.overlay)
    this.overlayTexture.colorSpace = THREE.NoColorSpace // drawn as it is, like the shaders' colours
    this.overlayTexture.generateMipmaps = false
    this.overlayTexture.minFilter = THREE.LinearFilter
    const overlayMaterial = new THREE.ShaderMaterial({
      vertexShader: TerrainShader.vertexShader,
      fragmentShader: /* glsl */ `
        uniform sampler2D tOverlay;
        varying vec2 vUv;
        void main() {
          gl_FragColor = texture2D(tOverlay, vUv);
        }`,
      uniforms: { tOverlay: { value: this.overlayTexture } },
      transparent: true,
      depthTest: false,
      depthWrite: false,
    })
    this.overlayScene.add(new THREE.Mesh(quad, overlayMaterial))
    this.disposables.push(quad, this.terrain, relief, mask, this.overlayTexture, overlayMaterial)

    const byId = new Map([...geo.countries, ...geo.states].map(region => [region.id, region]))
    this.targets = map.targets.flatMap(({ region, mission }) => {
      const found = byId.get(region)
      return found ? [{ region: found, mission, at: found.label.clone() }] : []
    })
    this.crosshairs = this.buildCrosshairs()
  }

  /** Where the view of the region shifts the middle to: the open part of the screen above the plate (in -1…1) */
  private static readonly SHIFT = new THREE.Vector2(-0.18, 0.4)

  /** Places the camera for the time of the intro: from the globe down onto the region */
  private placeCamera() {
    const [lon, lat] = this.map.center
    // distance for the span: half the span over the half of the horizontal field of view
    const halfWidth = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2)) * this.camera.aspect
    const near = 1 + THREE.MathUtils.degToRad(this.map.span / 2) / halfWidth
    const far = 4.4
    const t = THREE.MathUtils.clamp(this.time / MAP_TIMES.zoom, 0, 1)
    const ease = t * t * (3 - 2 * t)
    const distance = far * (near / far) ** ease
    // it comes round from the east and from the equator
    const from = toVector(lon + 70 * (1 - ease), lat * ease)
    this.camera.position.copy(from).multiplyScalar(distance)
    this.camera.up.set(0, 1, 0)
    this.camera.lookAt(0, 0, 0)
    this.camera.updateProjectionMatrix()
    // the region sits in the open part of the screen, not under the plate
    const shift = WorldMap.SHIFT.clone().multiplyScalar(ease)
    this.camera.projectionMatrix.elements[8] = -shift.x
    this.camera.projectionMatrix.elements[9] = -shift.y
    this.camera.projectionMatrixInverse.copy(this.camera.projectionMatrix).invert()
    this.camera.updateMatrixWorld()
  }

  /** Jumps to the end of the intro */
  skip() {
    this.time = Math.max(this.time, MAP_TIMES.zoom + MAP_TIMES.overlay + MAP_TIMES.target)
  }

  /** The intro is over (the crosshairs have flown in): the targets can be pointed at and clicked */
  get settled() {
    return this.time >= MAP_TIMES.zoom + MAP_TIMES.overlay + MAP_TIMES.target
  }

  /** The territories are up and the crosshairs begin to fly in */
  get targetsStarted() {
    return this.time >= MAP_TIMES.zoom + MAP_TIMES.overlay
  }

  /** The territories have come up (for the briefing text to start) */
  get overlayStarted() {
    return this.time >= MAP_TIMES.zoom
  }

  /** The target at a point of the screen (0…1 from the top left), if any */
  targetAt(x: number, y: number) {
    if (!this.settled) return undefined
    const ndc = new THREE.Vector3(x * 2 - 1, 1 - y * 2, 1).unproject(this.camera)
    const dir = ndc.sub(this.camera.position).normalize()
    const b = this.camera.position.dot(dir)
    const h = b * b - (this.camera.position.lengthSq() - 1)
    if (h < 0) return undefined
    const p = this.camera.position.clone().addScaledVector(dir, -b - Math.sqrt(h))
    const [lon, lat] = toLonLat(p)
    const index = this.targets.findIndex(t => t.region.rings.some(ring => inRing(ring, lon, lat)))
    return index >= 0 ? index : undefined
  }

  /** The mission (id) and name of a target */
  target(index: number) {
    const target = this.targets[index]!
    return { mission: target.mission, name: target.region.name }
  }

  get targetCount() {
    return this.targets.length
  }

  /** Advances the intro and draws the terrain and the overlay (size in device pixels) */
  render(renderer: THREE.WebGLRenderer, seconds: number, width: number, height: number) {
    this.time += seconds
    this.camera.aspect = width / height
    this.placeCamera()
    this.terrain.uniforms.uInvViewProj!.value.multiplyMatrices(this.camera.matrixWorld, this.camera.projectionMatrixInverse)
    this.terrain.uniforms.uCamera!.value.copy(this.camera.position)
    renderer.render(this.scene, this.camera)
    this.drawOverlay(width, height)
    renderer.render(this.overlayScene, this.camera)
    this.placeCrosshairs(width, height, width / 640)
    renderer.clearDepth()
    renderer.render(this.targetScene, this.targetCamera)
  }

  private drawOverlay(width: number, height: number) {
    const canvas = this.overlay
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width
      canvas.height = height
    }
    const ctx = canvas.getContext('2d')!
    ctx.clearRect(0, 0, width, height)
    const fade = THREE.MathUtils.clamp((this.time - MAP_TIMES.zoom) / MAP_TIMES.overlay, 0, 1)
    // the lines appear with the end of the zoom, the territories fade up after it
    const lines = THREE.MathUtils.clamp((this.time - MAP_TIMES.zoom * 0.6) / (MAP_TIMES.zoom * 0.4), 0, 1)
    if (lines <= 0) {
      this.overlayTexture.needsUpdate = true
      return
    }
    const unit = width / 640 // lines are as thick as in the original's 640 × 400
    const view = this.camera.position.clone().normalize()
    const horizon = Math.acos(1 / this.camera.position.length())
    const visible = (region: Region) => view.angleTo(region.centre) < horizon + region.radius
    const v = new THREE.Vector3()
    const camera = this.camera.position
    /** Areas to fill (only regions in sight, see `visible`) */
    const pathOf = (rings: number[][]) => {
      const path = new Path2D()
      for (const ring of rings) {
        for (let i = 0; i < ring.length; i += 2) {
          toVector(ring[i]!, ring[i + 1]!, v).project(this.camera)
          const x = (v.x + 1) / 2 * width
          const y = (1 - v.y) / 2 * height
          if (i) path.lineTo(x, y)
          else path.moveTo(x, y)
        }
        path.closePath()
      }
      return path
    }
    /** Lines (borders, coasts): broken off where they go behind the horizon, so the far side of the earth does not show through */
    const linesOf = (rings: number[][]) => {
      const path = new Path2D()
      for (const ring of rings) {
        let drawing = false
        for (let i = 0; i <= ring.length; i += 2) {
          const k = i % ring.length // back to the first point: the ring closes
          toVector(ring[k]!, ring[k + 1]!, v)
          if (v.dot(camera) <= 1) { // beyond the horizon
            drawing = false
            continue
          }
          v.project(this.camera)
          const x = (v.x + 1) / 2 * width
          const y = (1 - v.y) / 2 * height
          if (drawing) path.lineTo(x, y)
          else path.moveTo(x, y)
          drawing = true
        }
      }
      return path
    }
    const owned = (regions: Region[]) => regions.filter(r => this.map.regions[r.id] && visible(r))

    // territories: countries first, their states over them
    ctx.globalAlpha = fade
    for (const region of [...owned(this.geo.countries), ...owned(this.geo.states)]) {
      const owner = this.map.regions[region.id]!
      ctx.fillStyle = owner === 'gdi' ? COLOURS.gdi : COLOURS.nod
      ctx.fill(pathOf(region.rings))
    }
    // the targets: hatched, with a glowing green edge
    const hatch = this.hatch(unit)
    this.targets.forEach((target, index) => {
      const path = pathOf(target.region.rings)
      ctx.fillStyle = hatch
      ctx.fill(path)
      ctx.save()
      ctx.shadowColor = COLOURS.target
      ctx.shadowBlur = 6 * unit
      ctx.strokeStyle = COLOURS.target
      ctx.lineWidth = (this.hovered === index ? 2.2 : 1.4) * unit
      ctx.stroke(path)
      ctx.restore()
    })

    // borders and coasts
    ctx.globalAlpha = lines
    ctx.lineJoin = 'round'
    ctx.strokeStyle = COLOURS.stateBorder
    ctx.lineWidth = 0.5 * unit
    ctx.stroke(linesOf(this.geo.states.filter(visible).flatMap(r => r.rings)))
    ctx.strokeStyle = COLOURS.border
    ctx.lineWidth = 0.7 * unit
    ctx.stroke(linesOf(this.geo.countries.filter(visible).flatMap(r => r.rings)))
    ctx.strokeStyle = COLOURS.coast
    ctx.lineWidth = 0.8 * unit
    ctx.stroke(linesOf(this.geo.land))
    ctx.globalAlpha = 1

    this.overlayTexture.needsUpdate = true
  }

  private hatchPattern?: CanvasPattern
  private hatchUnit = 0
  /** Diagonal stripes of bright and dark green for the target regions */
  private hatch(unit: number) {
    if (this.hatchPattern && this.hatchUnit === unit) return this.hatchPattern
    const size = Math.max(4, Math.round(6 * unit))
    const tile = document.createElement('canvas')
    tile.width = tile.height = size
    const ctx = tile.getContext('2d')!
    ctx.fillStyle = 'rgba(4, 40, 6, 0.72)'
    ctx.fillRect(0, 0, size, size)
    ctx.strokeStyle = 'rgba(60, 210, 60, 0.5)'
    ctx.lineWidth = size / 3
    ctx.beginPath()
    for (const o of [-size, 0, size]) {
      ctx.moveTo(o, size)
      ctx.lineTo(o + size, 0)
    }
    ctx.stroke()
    this.hatchPattern = this.overlay.getContext('2d')!.createPattern(tile, 'repeat')!
    this.hatchUnit = unit
    return this.hatchPattern
  }

  /**
   * The crosshairs in 3D, laid over the map in screen pixels: two green rings joined by
   * four spokes (from the inner ring out past the outer one) fly in large and tumbling and
   * settle over the target. Then the crosshair turns back and forth (clockwise and
   * anticlockwise); under the cursor it pulses instead.
   */
  private buildCrosshairs() {
    const ring = new THREE.TorusGeometry(1, 0.11, 16, 64)
    /** A spoke, 1 long from its inner end: it is stretched from the inner ring out past the outer ring (1.0) */
    const bar = new THREE.BoxGeometry(1, 0.16, 0.16)
    bar.translate(0.5, 0, 0)
    const material = new THREE.MeshStandardMaterial({ color: 0x46ff46, emissive: 0x053a05, metalness: 0.4, roughness: 0.28, transparent: true })
    const hoverMaterial = material.clone()
    hoverMaterial.emissive.set(0x1c9a1c)
    this.disposables.push(ring, bar, material, hoverMaterial)
    const sun = new THREE.DirectionalLight(0xffffff, 3)
    sun.position.set(-0.6, 0.9, 0.7)
    this.targetScene.add(sun, new THREE.AmbientLight(0xffffff, 0.25))
    return this.targets.map(() => {
      const group = new THREE.Group()
      const outer = new THREE.Mesh(ring, material)
      const inner = new THREE.Mesh(ring, material)
      const bars = [0, 1, 2, 3].map((i) => {
        const mesh = new THREE.Mesh(bar, material)
        mesh.rotation.z = (i * Math.PI) / 2
        return mesh
      })
      group.add(outer, inner, ...bars)
      group.visible = false
      this.targetScene.add(group)
      /** 0 … 1: how far it has gone over from turning to pulsing (under the cursor) */
      return { group, outer, inner, bars, material, hoverMaterial, hover: 0, last: 0, hoverSince: 0 }
    })
  }

  private placeCrosshairs(width: number, height: number, unit: number) {
    const since = this.time - MAP_TIMES.zoom - MAP_TIMES.overlay
    const fly = THREE.MathUtils.clamp(since / MAP_TIMES.target, 0, 1)
    const ease = 1 - (1 - fly) ** 3
    const rest = 1 - ease
    this.targetCamera.right = width
    this.targetCamera.bottom = -height
    this.targetCamera.updateProjectionMatrix()
    const v = new THREE.Vector3()
    this.crosshairs.forEach((cross, index) => {
      cross.group.visible = since >= 0
      if (since < 0) return
      v.copy(this.targets[index]!.at).project(this.camera)
      cross.group.position.set((v.x + 1) / 2 * width, -(1 - v.y) / 2 * height, 0)
      const hovered = this.hovered === index
      const settled = Math.max(0, since - MAP_TIMES.target)
      // under the cursor it pulses; otherwise it turns back and forth (blended smoothly)
      // the pulse starts with shrinking: from full size down and back up again
      if (hovered && cross.hover < 0.01) cross.hoverSince = this.time
      cross.hover += ((hovered ? 1 : 0) - cross.hover) * (1 - Math.exp(-(this.time - cross.last) * 10))
      cross.last = this.time
      const beat = (1 - Math.cos((this.time - cross.hoverSince) * HOVER_BEAT)) / 2
      const pulse = 1 - cross.hover * 0.12 * beat
      // the inner ring closes almost to a point, the spokes follow it in
      const innerRadius = INNER_RADIUS - cross.hover * (INNER_RADIUS - 0.06) * beat
      cross.inner.scale.setScalar(innerRadius)
      cross.bars.forEach((mesh, i) => {
        const angle = (i * Math.PI) / 2
        mesh.position.set(Math.cos(angle) * innerRadius, Math.sin(angle) * innerRadius, 0)
        mesh.scale.x = SPOKE_END - innerRadius
      })
      const turn = Math.sin(settled * 1.6) * 0.5 * ease * (1 - cross.hover)
      cross.group.scale.setScalar(12 * unit * pulse * (1 + 4 * rest))
      // it comes tumbling in, much larger, and settles flat
      cross.group.rotation.set(rest * Math.PI * 1.5, rest * Math.PI, turn)
      for (const mesh of [cross.outer, cross.inner, ...cross.bars]) mesh.material = hovered ? cross.hoverMaterial : cross.material
      cross.material.opacity = Math.min(1, fly * 2)
    })
  }

  dispose() {
    for (const item of this.disposables) item.dispose()
  }
}
