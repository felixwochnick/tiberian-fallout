import * as THREE from 'three'

/**
 * Rebuild of the Westwood Studios logo (WWLOGO.VQA) that plays before the startup
 * animation: a blue plasma globe full of lightning, a yellow crescent swoosh and the
 * green 3D "W" in front of it, two glowing rings orbiting it. The camera starts above
 * the globe in its pillar of light while crescent and W drop in, swings to the front,
 * holds and finally rushes at the W (white flash, then black).
 */

/** Timeline in seconds, matched to WWLOGO.VQA (8.7 s, its sound peaks from the rush on). */
export const WESTWOOD_TIMELINE = {
  /** camera comes down from above the globe and its pillar of light to the front */
  reveal: [0, 1.5],
  pillarOut: [0.7, 1.5],
  /** crescent and W drop in from above, one after the other */
  crescentIn: [0.2, 1.0],
  letterIn: [0.45, 1.25],
  rings: [1.2, 1.8],
  texts: [1.5, 1.9],
  textsOut: [4.2, 4.4],
  /** camera rushes towards the W until it fills the screen */
  rush: [4.4, 4.85],
  /** short white flash, then black at once */
  flash: [4.8, 4.9],
  fadeOut: [5.05, 5.2],
  /** the sound fades out instead of playing to its very end */
  soundOut: [6.3, 7.0],
  end: 7.0,
} as const

/** Radius of the blue globe; rings and crescent are placed around it. */
const GLOBE_RADIUS = 1.0

const clamp01 = (x: number) => Math.min(1, Math.max(0, x))
const progress = ([a, b]: readonly [number, number], t: number) => clamp01((t - a) / (b - a))
const easeOut = (x: number) => 1 - (1 - x) ** 3
const easeIn = (x: number) => x ** 3

const NOISE = /* glsl */ `
  float hash3(vec3 p) {
    return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453);
  }
  float noise3(vec3 p) {
    vec3 i = floor(p), f = fract(p);
    vec3 u = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(mix(hash3(i), hash3(i + vec3(1, 0, 0)), u.x), mix(hash3(i + vec3(0, 1, 0)), hash3(i + vec3(1, 1, 0)), u.x), u.y),
      mix(mix(hash3(i + vec3(0, 0, 1)), hash3(i + vec3(1, 0, 1)), u.x), mix(hash3(i + vec3(0, 1, 1)), hash3(i + vec3(1, 1, 1)), u.x), u.y),
      u.z);
  }
  float fbm3(vec3 p) {
    return noise3(p) * 0.55 + noise3(p * 2.03) * 0.3 + noise3(p * 4.1) * 0.15;
  }`

/** Plasma globe: deep blue with crawling white lightning veins and a dark rim. */
const GlobeShader = {
  uniforms: {
    uTime: { value: 0 },
  },
  vertexShader: /* glsl */ `
    varying vec3 vPos;
    varying vec3 vNormal;
    varying vec3 vView;
    void main() {
      vPos = position;
      vec4 world = modelMatrix * vec4(position, 1.0);
      vNormal = normalize(mat3(modelMatrix) * normal);
      vView = normalize(cameraPosition - world.xyz);
      gl_Position = projectionMatrix * viewMatrix * world;
    }`,
  fragmentShader: /* glsl */ `
    uniform float uTime;
    varying vec3 vPos;
    varying vec3 vNormal;
    varying vec3 vView;
    ${NOISE}

    // thin bright lines where the (warped) noise crosses 0.5
    float veins(vec3 p, float sharpness) {
      float n = fbm3(p);
      return pow(1.0 - abs(n * 2.0 - 1.0), sharpness);
    }

    void main() {
      vec3 p = normalize(vPos);
      float t = uTime;
      vec3 warp = vec3(fbm3(p * 2.0 + t * 0.25), fbm3(p * 2.0 + 5.2 - t * 0.2), fbm3(p * 2.0 + 9.7 + t * 0.15));
      vec3 q = p * 1.3 + warp * 1.2;
      float bolts = veins(q + vec3(0.0, t * 0.35, 0.0), 14.0);
      float fine = veins(q * 1.9 + 3.0 - vec3(t * 0.3, 0.0, 0.0), 26.0) * 0.35;
      // the bolts flare up and die down in patches
      float patches = smoothstep(0.35, 0.7, fbm3(p * 1.5 + vec3(t * 0.4)));
      float light = clamp((bolts + fine) * (0.35 + 0.9 * patches), 0.0, 1.0);

      vec3 base = mix(vec3(0.03, 0.08, 0.5), vec3(0.12, 0.26, 0.9), fbm3(p * 2.5 - t * 0.1));
      vec3 colour = base + vec3(0.75, 0.82, 1.0) * light;
      // soft blue haze around the bolts
      colour += vec3(0.15, 0.3, 0.9) * pow(1.0 - abs(fbm3(q + vec3(0.0, t * 0.35, 0.0)) * 2.0 - 1.0), 5.0) * 0.4 * patches;

      // dark rim before the halo starts
      float facing = clamp(dot(normalize(vNormal), normalize(vView)), 0.0, 1.0);
      colour *= smoothstep(0.12, 0.55, facing);
      gl_FragColor = vec4(colour, 1.0);
    }`,
}

/** Pale blue halo around the globe, drawn on a camera-facing quad behind it. */
const HaloShader = {
  uniforms: {
    uTime: { value: 0 },
    uStrength: { value: 1 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }`,
  fragmentShader: /* glsl */ `
    uniform float uTime;
    uniform float uStrength;
    varying vec2 vUv;
    ${NOISE}
    void main() {
      vec2 p = vUv * 2.0 - 1.0;
      float r = length(p) * 3.0 / ${GLOBE_RADIUS.toFixed(3)}; // 1.0 = edge of the globe
      float a = atan(p.y, p.x);
      float flicker = 0.75 + 0.25 * fbm3(vec3(cos(a) * 2.0, sin(a) * 2.0, uTime * 0.8));
      float glow = smoothstep(0.95, 1.06, r) * exp(-max(r - 1.06, 0.0) * 6.0) * flicker * (1.0 - smoothstep(2.4, 3.0, r));
      vec3 colour = vec3(0.45, 0.75, 0.95) * glow * uStrength;
      gl_FragColor = vec4(colour, 1.0); // additive
    }`,
}

/** Pillar of blue light the globe sits in at the start: vertical streaks, brightest at the globe. */
const PillarShader = {
  uniforms: {
    uTime: { value: 0 },
    uStrength: { value: 1 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    varying float vFacing;
    void main() {
      vUv = uv;
      vec4 world = modelMatrix * vec4(position, 1.0);
      vec3 n = normalize(mat3(modelMatrix) * normal);
      vFacing = abs(dot(n, normalize(cameraPosition - world.xyz)));
      gl_Position = projectionMatrix * viewMatrix * world;
    }`,
  fragmentShader: /* glsl */ `
    uniform float uTime;
    uniform float uStrength;
    varying vec2 vUv;
    varying float vFacing;
    ${NOISE}
    void main() {
      float streaks = fbm3(vec3(vUv.x * 40.0, vUv.y * 1.5 - uTime * 0.8, uTime * 0.3));
      float light = (0.35 + 0.9 * streaks) * pow(vUv.y, 1.5); // uv.y = 1 at the top, under the globe
      light *= 1.0 - smoothstep(0.86, 0.97, vUv.y); // soft top edge where it meets the globe
      light *= 0.5 + 0.8 * (1.0 - vFacing); // denser where we look along the wall
      gl_FragColor = vec4(vec3(0.08, 0.25, 1.0) * light * uStrength, 1.0); // additive
    }`,
}

/**
 * Green light flying around a ring: a few streaks with a bright head and a fading
 * tail run along the torus (uv.x goes once around it), over a faint trace of the path.
 */
const RingShader = {
  uniforms: {
    uTime: { value: 0 },
    uOpacity: { value: 1 },
    /** turns per second, the sign gives the direction */
    uSpeed: { value: 0.3 },
    uPhase: { value: 0 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }`,
  fragmentShader: /* glsl */ `
    uniform float uTime;
    uniform float uOpacity;
    uniform float uSpeed;
    uniform float uPhase;
    varying vec2 vUv;
    const float STREAKS = 3.0;
    void main() {
      // rises from 0 just behind a head to 1 at the head; the heads move along the ring
      float p = fract((vUv.x + uPhase - uTime * uSpeed) * STREAKS);
      if (uSpeed < 0.0) p = 1.0 - p; // the heads always lead in the direction of flight
      float streak = pow(p, 5.0) * smoothstep(1.0, 0.96, p);
      float light = 0.12 + streak * 1.6;
      gl_FragColor = vec4(vec3(0.24, 0.82, 0.24) * light * uOpacity, 1.0); // additive
    }`,
}

/**
 * Outline of the "W" (x -1..1, y -0.5..0.5), clockwise from the top left. Only the
 * tops of the outer strokes are flat, the feet and the middle peak are sharp points.
 */
const W_OUTLINE: [number, number][] = [
  [-1, 0.5], [-0.62, 0.5], [-0.213, -0.043], [0, 0.17], [0.213, -0.043], [0.62, 0.5], [1, 0.5],
  [0.25, -0.5], [0, -0.25], [-0.25, -0.5],
]

/** The W is a bit turned, so its left side faces show; the rings turn with it. */
const LETTER_TURN = 0.35
/** How far the rings are moved out of the centre of the globe (radius 1) */
const RING_OFFSET = 0.45

/** How far the rings are turned outwards at the front (radians) */
const RING_SPREAD = THREE.MathUtils.degToRad(10)

/** Radius of the shell the crescent lies on: everywhere the same distance above the globe. */
const CRESCENT_SHELL = 1.25
/** Camera distance while the logo is in full view (see render) */
const VIEW_DISTANCE = 4.4

/**
 * Point on the crescent shell that the camera sees at `screen` (in units of the globe
 * radius, measured on the original frame), so the outline matches the original
 * although the shell bulges towards the camera.
 */
function onShell(screen: THREE.Vector2) {
  const flat = screen.clone()
  let z = 0
  for (let i = 0; i < 6; i++) {
    z = Math.sqrt(Math.max(CRESCENT_SHELL ** 2 - flat.lengthSq(), 0))
    flat.copy(screen).multiplyScalar((VIEW_DISTANCE - z) / VIEW_DISTANCE)
  }
  return new THREE.Vector3(flat.x, flat.y, z)
}

/**
 * Upper half of the yellow bolt: a crescent from the sharp tip at the top right down
 * to a straight, sharp-cornered cut left of the middle. Outer and inner edge as seen
 * on the original frame; the lower half is the same turned by 180°, and a straight
 * bar behind the W joins both.
 */
const BOLT_OUTER = [[0.34, 1.12], [-0.05, 1.0], [-0.42, 0.8], [-0.66, 0.42], [-0.72, -0.08]] as const
const BOLT_INNER = [[0.34, 1.12], [0.06, 0.84], [-0.14, 0.52], [-0.24, 0.2], [-0.25, -0.08]] as const

/** Half the height of the straight bar behind the W that joins both halves (their cuts lie on its edges) */
const BOLT_BAR = 0.08

/** Yellow bolt bent onto a sphere around the globe: both halves and the bar between them in one geometry. */
function boltGeometry() {
  const v = (x: number, y: number) => new THREE.Vector2(x, y)
  const curve = (points: readonly (readonly [number, number])[]) => new THREE.SplineCurve(points.map(([x, y]) => v(x, y)))
  // the bar fills the gap between the inner edges of both halves
  const [left] = BOLT_INNER.at(-1)!
  // each patch is a grid between two edges: [edge, opposite edge, turned by 180°],
  // all wound the same way round
  const patches: [THREE.Curve<THREE.Vector2>, THREE.Curve<THREE.Vector2>, boolean][] = [
    [curve(BOLT_OUTER), curve(BOLT_INNER), false],
    [curve(BOLT_OUTER), curve(BOLT_INNER), true],
    [new THREE.LineCurve(v(left, -BOLT_BAR), v(-left, -BOLT_BAR)), new THREE.LineCurve(v(left, BOLT_BAR), v(-left, BOLT_BAR)), false],
  ]
  const steps = 64
  const columns = 8
  const positions: number[] = []
  const normals: number[] = []
  const index: number[] = []
  for (const [outer, inner, turned] of patches) {
    const start = positions.length / 3
    for (let i = 0; i <= steps; i++) {
      const t = i / steps
      const o = outer.getPoint(t)
      const n = inner.getPoint(t)
      for (let j = 0; j <= columns; j++) {
        const vertex = onShell(o.clone().lerp(n, j / columns).multiplyScalar(turned ? -1 : 1))
        positions.push(vertex.x, vertex.y, vertex.z)
        vertex.normalize()
        normals.push(vertex.x, vertex.y, vertex.z)
        if (i < steps && j < columns) {
          const a = start + i * (columns + 1) + j
          const b = a + columns + 1
          index.push(a, b, a + 1, a + 1, b, b + 1)
        }
      }
    }
  }
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3))
  geometry.setIndex(index)
  return geometry
}

export class WestwoodIntro {
  private readonly renderer: THREE.WebGLRenderer
  private readonly scene = new THREE.Scene()
  private readonly camera = new THREE.PerspectiveCamera(32, 16 / 10, 0.05, 100)
  private readonly globe: THREE.ShaderMaterial
  private readonly halo: THREE.ShaderMaterial
  private readonly haloMesh: THREE.Mesh
  private readonly pillar: THREE.ShaderMaterial
  private crescent!: THREE.Mesh
  private letter!: THREE.Mesh
  /** materials of the rings with their full opacity */
  private readonly rings: [THREE.ShaderMaterial, number][][] = []
  private readonly disposables: { dispose(): void }[] = []

  constructor(private readonly container: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.setClearColor(0x000000)
    this.renderer.outputColorSpace = THREE.SRGBColorSpace
    container.appendChild(this.renderer.domElement)

    this.globe = this.track(new THREE.ShaderMaterial({ ...GlobeShader, uniforms: THREE.UniformsUtils.clone(GlobeShader.uniforms) }))
    this.scene.add(new THREE.Mesh(this.track(new THREE.SphereGeometry(GLOBE_RADIUS, 96, 64)), this.globe))

    this.halo = this.track(new THREE.ShaderMaterial({
      ...HaloShader,
      uniforms: THREE.UniformsUtils.clone(HaloShader.uniforms),
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }))
    this.haloMesh = new THREE.Mesh(this.track(new THREE.PlaneGeometry(6, 6)), this.halo)
    this.haloMesh.renderOrder = -1
    this.scene.add(this.haloMesh)

    this.pillar = this.track(new THREE.ShaderMaterial({
      ...PillarShader,
      uniforms: THREE.UniformsUtils.clone(PillarShader.uniforms),
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
    }))
    const pillar = new THREE.Mesh(this.track(new THREE.CylinderGeometry(1.15 * GLOBE_RADIUS, 1.05 * GLOBE_RADIUS, 7, 64, 1, true)), this.pillar)
    pillar.position.y = -3.3
    this.scene.add(pillar)

    this.buildLogo()
    this.buildRings()

    // lit from the front right, so the extruded sides of the W on the left fall into shade
    const key = new THREE.DirectionalLight(0xffffff, 2.2)
    key.position.set(1.2, 0.8, 3)
    this.scene.add(key, new THREE.AmbientLight(0xffffff, 0.55))

    this.resize()
    this.render(0)
  }

  private track<T extends { dispose(): void }>(resource: T): T {
    this.disposables.push(resource)
    return resource
  }

  private buildLogo() {
    const crescent = new THREE.Mesh(
      this.track(boltGeometry()),
      this.track(new THREE.MeshLambertMaterial({ color: 0xe8dc6a, emissive: 0x403a10, side: THREE.DoubleSide })),
    )
    this.crescent = crescent

    const w = new THREE.Shape(W_OUTLINE.map(([x, y]) => new THREE.Vector2(x, y)))
    const geometry = this.track(new THREE.ExtrudeGeometry(w, { depth: 0.22, bevelEnabled: true, bevelSize: 0.012, bevelThickness: 0.012, bevelSegments: 1 }))
    geometry.translate(0, 0, -0.22)
    const letter = new THREE.Mesh(geometry, this.track(new THREE.MeshLambertMaterial({ color: 0x178a0c, emissive: 0x062004 })))
    // taller than the outline, so it keeps the original's proportions after the 4:3 squash
    letter.scale.set(0.62, 0.62 * 1.22, 0.62)
    letter.position.z = 1.4
    letter.rotation.y = LETTER_TURN
    this.letter = letter
    this.scene.add(crescent, letter)
  }

  /**
   * Four green rings as wide as the globe, standing at right angles to the W like a
   * "#" around it: two upright ones moved left and right of the centre, two lying
   * ones moved up and down, so each runs around the globe instead of through it.
   * The lying ones are turned with the W about the upright axis, so they show as flat
   * ellipses; the upright ones are turned edge-on to the camera, so they show as lines.
   */
  private buildRings() {
    const set = new THREE.Group()
    set.rotation.y = LETTER_TURN
    const ring = (offset: THREE.Vector3, normal: THREE.Vector3, parent: THREE.Object3D) => {
      const pivot = new THREE.Group()
      pivot.position.copy(offset)
      pivot.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal) // torus lies in its xy plane
      const materials: [THREE.ShaderMaterial, number][] = []
      // each ring flies at its own speed and direction
      const index = this.rings.length
      const speed = (0.22 + 0.06 * index) * (index % 2 ? -1 : 1)
      // thin core plus a wide faint copy as glow
      for (const [tube, opacity] of [[0.007, 1], [0.028, 0.27]] as const) {
        const material = this.track(new THREE.ShaderMaterial({
          ...RingShader,
          uniforms: THREE.UniformsUtils.clone(RingShader.uniforms),
          transparent: true,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        }))
        material.uniforms.uSpeed!.value = speed
        material.uniforms.uPhase!.value = index * 0.37
        materials.push([material, opacity])
        pivot.add(new THREE.Mesh(this.track(new THREE.TorusGeometry(1, tube, 8, 160)), material))
      }
      parent.add(pivot)
      this.rings.push(materials)
    }
    const up = new THREE.Vector3(0, 1, 0)
    // lying ones: tipped about the cross axis by RING_SPREAD, so they too stand further
    // apart in front (at the W) than behind the globe
    for (const y of [-RING_OFFSET, RING_OFFSET]) {
      const normal = up.clone().applyAxisAngle(new THREE.Vector3(1, 0, 0), -Math.sign(y) * RING_SPREAD)
      ring(new THREE.Vector3(0, y, 0), normal, set)
    }
    // upright ones: their plane runs through the camera, then each is turned outwards
    // by RING_SPREAD, so they stand further apart in front (at the W) than behind the globe
    for (const x of [-RING_OFFSET, RING_OFFSET]) {
      const toCamera = new THREE.Vector3(-x, 0, VIEW_DISTANCE).normalize()
      toCamera.applyAxisAngle(up, Math.sign(x) * RING_SPREAD)
      ring(new THREE.Vector3(x, 0, 0), new THREE.Vector3().crossVectors(toCamera, up).normalize(), this.scene)
    }
    this.scene.add(set)
  }

  resize() {
    const width = this.container.clientWidth
    const height = this.container.clientHeight
    if (!width || !height) return
    this.renderer.setSize(width, height)
    this.camera.aspect = width / height
    // keep the whole logo visible on narrow screens
    this.camera.fov = width / height < 1.3 ? 32 * (1.3 / (width / height)) : 32
    this.camera.updateProjectionMatrix()
    // the original was rendered for 4:3 and shown at 16:10, so everything looks a bit squashed
    this.camera.projectionMatrix.elements[5]! *= 0.84
    this.camera.projectionMatrixInverse.copy(this.camera.projectionMatrix).invert()
  }

  render(time: number) {
    const reveal = easeOut(progress(WESTWOOD_TIMELINE.reveal, time))
    const rush = easeIn(progress(WESTWOOD_TIMELINE.rush, time))

    // starts above the globe looking down into its pillar of light, swings to the front, then rushes at the W
    const height = THREE.MathUtils.lerp(2.3, 0, reveal)
    const distance = THREE.MathUtils.lerp(1.9, VIEW_DISTANCE, reveal) - rush * 2.2
    this.camera.position.set(0, height, distance)
    this.camera.lookAt(0, THREE.MathUtils.lerp(-0.7, 0, reveal), 0)

    this.pillar.uniforms.uTime!.value = time
    this.pillar.uniforms.uStrength!.value = 1 - progress(WESTWOOD_TIMELINE.pillarOut, time)

    this.globe.uniforms.uTime!.value = time
    this.halo.uniforms.uTime!.value = time
    this.halo.uniforms.uStrength!.value = 1 + 0.6 * (1 - reveal) // brighter while the camera is close
    this.haloMesh.quaternion.copy(this.camera.quaternion)

    // crescent and W drop in from above
    this.crescent.position.y = (1 - easeOut(progress(WESTWOOD_TIMELINE.crescentIn, time))) * 3.5
    this.letter.position.y = -0.04 + (1 - easeOut(progress(WESTWOOD_TIMELINE.letterIn, time))) * 3.5

    const ringsVisible = progress(WESTWOOD_TIMELINE.rings, time)
    for (const materials of this.rings) {
      for (const [material, opacity] of materials) {
        material.uniforms.uOpacity!.value = opacity * ringsVisible
        material.uniforms.uTime!.value = time
      }
    }

    this.renderer.render(this.scene, this.camera)
  }

  dispose() {
    for (const resource of this.disposables) resource.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
