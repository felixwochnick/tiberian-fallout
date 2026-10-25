import * as THREE from 'three'

/**
 * Faction emblems of the main menu, drawn from the colourless logo SVGs.
 *
 * GDI: the logo seen through a
 * glowing golden glass dome that shines light out onto the wall (like the
 * GDI button of the original).
 *
 * Everything is done in one fragment shader on a square quad: the dome bends
 * the logo (slightly magnified in the middle, squeezed at the edge), is lit
 * from the top left and darkens towards its rim.
 */
const DomeShader = {
  uniforms: {
    tLogo: { value: null as THREE.Texture | null },
    /** 1 = light shining out onto the wall around the emblem, 0 = none */
    uGlow: { value: 1 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = vec4(position.xy, 0.0, 1.0);
    }`,
  fragmentShader: /* glsl */ `
    uniform sampler2D tLogo;
    uniform float uGlow;
    varying vec2 vUv;

    const float PI = 3.14159265;
    const float DOME = 0.78;
    const vec3 LIGHT = vec3(-0.45, 0.6, 0.66);

    float hash(vec2 p) {
      return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
    }
    float noise(vec2 p) {
      vec2 i = floor(p), f = fract(p);
      vec2 u = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
    }

    void main() {
      vec2 p = vUv * 2.0 - 1.0;
      float r = length(p);
      float aa = fwidth(r) * 1.2;
      vec3 light = normalize(LIGHT);
      vec3 view = vec3(0.0, 0.0, 1.0);

      // ---- glass dome with the logo underneath
      vec2 q = p / DOME;
      float q2 = min(dot(q, q), 1.0);
      float h = sqrt(1.0 - q2);
      vec3 n = normalize(vec3(q * 0.75, h));
      // magnifies the middle a little and squeezes the edge
      vec2 s = q * mix(0.8, 1.0, q2);
      float ink = texture2D(tLogo, s * 0.5 + 0.5, 1.5).a;
      float inkSoft = texture2D(tLogo, s * 0.5 + 0.5, 4.0).a;
      ink = mix(ink, inkSoft, 0.5); // seen through blurry glass

      // hot, almost white-yellow spot right of the centre, deeper gold outside
      // lit from inside: lemon yellow, hottest right of the centre
      float hot = 1.0 - smoothstep(0.0, 1.3, length(q - vec2(0.3, -0.05)));
      vec3 gold = mix(vec3(1.0, 0.9, 0.36), vec3(1.0, 1.0, 0.74), hot);
      // the eagle: a deeper, darker gold than the glass around it
      vec3 inkColour = mix(vec3(0.24, 0.17, 0.035), vec3(0.38, 0.28, 0.07), hot);
      vec3 dome = mix(gold, inkColour, ink * 0.95);

      dome *= 0.9 + 0.1 * dot(n, light);
      dome *= mix(0.8, 1.0, smoothstep(0.0, 0.3, h)); // darker towards the rim
      // light glowing out of the glass
      dome += vec3(0.25, 0.2, 0.02) * hot * hot;
      float spec = pow(max(dot(n, normalize(light + view)), 0.0), 18.0);
      dome += vec3(1.0, 0.97, 0.85) * spec * 0.2;
      // cloudy reflection of the stone wall on the left of the glass
      float cloud = smoothstep(0.75, 0.0, length((q - vec2(-0.62, 0.12)) * vec2(1.6, 0.8)));
      cloud *= 0.55 + 0.45 * noise(q * 6.0 + 3.0);
      dome = mix(dome, vec3(0.8, 0.78, 0.68), cloud * 0.6);

      // ---- compose: the glowing glass shines yellow light out onto the wall
      float inside = 1.0 - smoothstep(DOME - aa, DOME, r);
      float edge = smoothstep(DOME - 0.035, DOME, r) * inside; // thin dark seam of the glass
      dome *= 1.0 - edge * 0.55;
      float fall = clamp(1.0 - (r - DOME) / (1.0 - DOME), 0.0, 1.0);
      float glow = 0.55 * fall * fall * fall;
      vec4 shine = vec4(vec3(1.0, 0.84, 0.34) * glow, glow * 0.7) * uGlow; // partly additive on the dark wall
      gl_FragColor = vec4(dome * inside, inside) + shine * (1.0 - inside);
    }`,
}

/**
 * Nod: only the black parts of the logo (hexagon ring and scorpion tail) as
 * dark, worn metal with bevelled edges, plus the red glow shining out onto the
 * wall; the red glass behind it is CSS. tShapes holds R = metal mask (sharp),
 * G = the same mask blurred (height for the bevel) and B = whole hexagon (for the glow).
 * The glass also gets sharp edged, pale glare facets coming in from its three short sides.
 */
const NodShader = {
  uniforms: {
    tShapes: { value: null as THREE.Texture | null },
    /** 1 = red light shining out onto the wall around the emblem, 0 = none */
    uGlow: { value: 1 },
    /** Corners of the outer hexagon in -1..1 space; edges 1, 3 and 5 are the short sides */
    uHex: { value: [] as THREE.Vector2[] },
  },
  vertexShader: DomeShader.vertexShader,
  fragmentShader: /* glsl */ `
    uniform sampler2D tShapes;
    uniform float uGlow;
    uniform vec2 uHex[6];
    varying vec2 vUv;

    float cross2(vec2 a, vec2 b) {
      return a.x * b.y - a.y * b.x;
    }
    // pale facet between the centre c and the side a-b: sharp sides, brightest at the side, fading out towards c
    float facet(vec2 p, vec2 c, vec2 a, vec2 b) {
      // the corners run clockwise, so inside means p lies clockwise of c-a and anticlockwise of c-b
      float s1 = cross2(p - c, a - c) / length(a - c);
      float s2 = cross2(b - c, p - c) / length(b - c);
      float aa = fwidth(s1) * 0.8;
      float inside = smoothstep(-aa, aa, s1) * smoothstep(-aa, aa, s2);
      vec2 n = vec2(b.y - a.y, a.x - b.x);
      float t = dot(n, p - c) / dot(n, a - c); // 0 at the centre, 1 at the side
      return inside * smoothstep(0.1, 0.9, t);
    }

    const vec3 LIGHT = vec3(-0.45, 0.6, 0.66);

    float hash(vec2 p) {
      return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
    }
    float noise(vec2 p) {
      vec2 i = floor(p), f = fract(p);
      vec2 u = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
    }
    float fbm(vec2 p) {
      return noise(p) * 0.5 + noise(p * 2.1) * 0.3 + noise(p * 4.3) * 0.2;
    }

    void main() {
      vec2 p = vUv * 2.0 - 1.0;
      float mask = texture2D(tShapes, vUv).r;

      // bevel: normal from the blurred mask, the metal falls off towards its edges
      vec2 e = vec2(2.0 / 1024.0, 0.0);
      float dx = texture2D(tShapes, vUv + e.xy).g - texture2D(tShapes, vUv - e.xy).g;
      float dy = texture2D(tShapes, vUv + e.yx).g - texture2D(tShapes, vUv - e.yx).g;
      vec3 n = normalize(vec3(-dx * 7.0, -dy * 7.0, 1.0));
      vec3 light = normalize(LIGHT);
      vec3 half_ = normalize(light + vec3(0.0, 0.0, 1.0));

      // very dark grey, slightly worn and pitted
      float grain = fbm(p * 18.0);
      float pits = smoothstep(0.62, 0.75, fbm(p * 55.0 + 7.0));
      vec3 colour = vec3(0.07, 0.068, 0.068) + vec3(0.07) * grain;
      colour *= 1.0 - pits * 0.5;
      colour *= 0.45 + 1.1 * max(dot(n, light), 0.0);
      // grey highlights on the bevels facing the light
      float spec = pow(max(dot(n, half_), 0.0), 36.0);
      colour += vec3(0.62, 0.6, 0.6) * spec * (0.5 + 0.5 * grain);
      // red light of the glass catching the edges, strongest close to the core
      float core = exp(-length(p - vec2(0.0, -0.04)) * 2.2);
      colour += vec3(0.85, 0.07, 0.03) * (1.0 - n.z) * (0.25 + 1.3 * core);

      // ---- pale glare facets from the three short sides, lying on top of glass and metal
      vec2 c = vec2(0.0, -0.028); // centre of the light, same as the CSS glass
      float glare = facet(p, c, uHex[1], uHex[2]) + facet(p, c, uHex[3], uHex[4]) + facet(p, c, uHex[5], uHex[0]);
      float hex = texture2D(tShapes, vUv).b;
      glare *= 0.3 * hex * (1.0 - 0.4 * mask); // only on the emblem, a bit weaker on the metal
      vec4 glass = vec4(vec3(1.0, 0.86, 0.84) * glare, glare);

      // ---- red light shining out of the hexagon onto the wall
      float wide = texture2D(tShapes, vUv, 5.0).b;
      float tight = texture2D(tShapes, vUv, 3.0).b;
      float window = 1.0 - smoothstep(0.8, 0.99, max(abs(p.x), abs(p.y))); // fades out before the canvas edge
      float glow = (tight + wide * 0.45) * window * (1.0 - hex);
      vec4 shine = vec4(vec3(1.0, 0.1, 0.05) * glow, glow * 0.7) * uGlow; // partly additive on the dark wall
      vec4 emblem = vec4(colour * mask, mask) + shine * (1.0 - mask);
      gl_FragColor = glass + emblem * (1.0 - glare);
    }`,
}

export type EmblemKind = 'gdi' | 'nod'

function mipmapped(canvas: HTMLCanvasElement) {
  const texture = new THREE.CanvasTexture(canvas)
  texture.generateMipmaps = true
  texture.minFilter = THREE.LinearMipmapLinearFilter
  texture.anisotropy = 4
  return texture
}

/** GDI: the logo as alpha mask. */
async function gdiTexture(url: string, size: number) {
  const image = new Image()
  image.src = url
  await image.decode()
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  canvas.getContext('2d')!.drawImage(image, 0, 0, size, size)
  return mipmapped(canvas)
}

/** Texture scale: the hexagon covers 70 % of the emblem, the rest is for the glow (keep in sync with .nod-glass in StartupMenu.vue). */
const NOD_SCALE = 0.7

/** Nod: metal mask (R), its blurred copy (G) and the whole hexagon (B); the SVG has the paths "frame" (even-odd ring) and "scorpion". */
async function nodTexture(url: string, size: number) {
  const svg = new DOMParser().parseFromString(await (await fetch(url)).text(), 'image/svg+xml')
  const d = (id: string) => svg.getElementById(id)!.getAttribute('d')!
  const frame = new Path2D(d('frame'))
  const scorpion = new Path2D(d('scorpion'))
  const [outer] = d('frame').split('M').filter(Boolean).map(ring =>
    [...ring.matchAll(/(-?[\d.]+),(-?[\d.]+)/g)].map(m => new THREE.Vector2(Number(m[1]), -Number(m[2])).multiplyScalar(NOD_SCALE / 500))) // SVG y points down

  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, size, size)
  ctx.globalCompositeOperation = 'lighter'
  // the SVG is 1000 units wide and centred on 0,0
  const draw = (colour: string, filter: string, rule: CanvasFillRule, withScorpion: boolean) => {
    ctx.save()
    ctx.filter = filter
    ctx.translate(size / 2, size / 2)
    ctx.scale((size / 1000) * NOD_SCALE, (size / 1000) * NOD_SCALE)
    ctx.fillStyle = colour
    ctx.fill(frame, rule)
    if (withScorpion) ctx.fill(scorpion)
    ctx.restore()
  }
  draw('#ff0000', 'none', 'evenodd', true)
  draw('#00ff00', `blur(${(size * NOD_SCALE) / 160}px)`, 'evenodd', true)
  draw('#0000ff', 'none', 'nonzero', false)
  const texture = mipmapped(canvas)
  texture.colorSpace = THREE.NoColorSpace
  return { texture, uniforms: { uHex: outer! } }
}

const KINDS = {
  gdi: { shader: DomeShader, texture: async (url: string, size: number) => ({ texture: await gdiTexture(url, size), uniforms: {} }), uniform: 'tLogo', url: '/logos/gdi.svg' },
  nod: { shader: NodShader, texture: nodTexture, uniform: 'tShapes', url: '/logos/nod.svg' },
} as const

export class Emblem {
  private readonly renderer: THREE.WebGLRenderer
  private readonly scene = new THREE.Scene()
  private readonly camera = new THREE.Camera()
  private readonly material: THREE.ShaderMaterial
  private readonly geometry = new THREE.PlaneGeometry(2, 2)

  /** `glow: false` leaves out the light shining around the emblem (e.g. in the radar). */
  static async create(container: HTMLElement, kind: EmblemKind, { glow = true } = {}) {
    const { texture, url } = KINDS[kind]
    const loaded = await texture(url, 1024)
    return new Emblem(container, kind, loaded.texture, { ...loaded.uniforms, uGlow: glow ? 1 : 0 })
  }

  private constructor(
    private readonly container: HTMLElement,
    kind: EmblemKind,
    private readonly logo: THREE.Texture,
    extraUniforms: Record<string, unknown>,
  ) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, premultipliedAlpha: true })
    this.renderer.outputColorSpace = THREE.LinearSRGBColorSpace // the shaders write display colours
    this.renderer.setClearColor(0x000000, 0)
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    container.appendChild(this.renderer.domElement)
    const { shader, uniform } = KINDS[kind]
    this.material = new THREE.ShaderMaterial({
      vertexShader: shader.vertexShader,
      fragmentShader: shader.fragmentShader,
      uniforms: {
        ...THREE.UniformsUtils.clone(shader.uniforms),
        [uniform]: { value: logo },
        ...Object.fromEntries(Object.entries(extraUniforms).map(([key, value]) => [key, { value }])),
      },
      transparent: true,
      premultipliedAlpha: true,
    })
    this.scene.add(new THREE.Mesh(this.geometry, this.material))
    this.resize()
  }

  /** Static picture, so it only renders on resize. */
  resize() {
    const size = this.container.clientWidth
    if (!size) return
    this.renderer.setSize(size, size)
    this.renderer.render(this.scene, this.camera)
  }

  dispose() {
    this.geometry.dispose()
    this.material.dispose()
    this.logo.dispose()
    this.renderer.dispose()
    this.renderer.domElement.remove()
  }
}
