/**
 * Look of the in-game HUD, rebuilt as vector graphics after Tiberian Sun's sidebar
 * art (TABS.SHP), so it stays sharp at any resolution instead of pixel-doubled bitmaps.
 *
 * The materials are SVG filters: noise gives the stone its camouflage patches, and
 * a height map from noise, lit by SVG lighting (diffuse + specular, light from the
 * top left like the original), gives it real relief. Scratches, grime towards the
 * edges and soft bevels make it look worn; brass and steel get brushed streaks.
 * Sizes are in units of the original art (a tab is 168 × 16), see `hudScale`.
 */

/** Screen pixels per original pixel: the original HUD at 1024 × 768, stepless. */
export const hudScale = () => Math.max(1, window.innerHeight / 768)

/** Size of a tab (and the height of the top bar) in original pixels; a bit higher than TABS.SHP (16) */
export const TAB = { width: 168, height: 20 }

const svgUrl = (svg: string) => `url("data:image/svg+xml,${encodeURIComponent(svg.replace(/\s+/g, ' '))}")`

const svg = (w: number, h: number, body: string) => svgUrl(`
  <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 ${w} ${h}' preserveAspectRatio='none'>${body}</svg>`)

/** A filter over the whole picture (filters in user space, so they keep their scale) */
const filter = (id: string, w: number, h: number, body: string) => `
  <filter id='${id}' x='0' y='0' width='${w}' height='${h}' filterUnits='userSpaceOnUse' color-interpolation-filters='sRGB'>${body}</filter>`

/** Noise coloured in one colour, its alpha from the noise: `alpha` = "scale offset" */
const colouredNoise = (id: string, w: number, h: number, type: string, frequency: string, octaves: number, seed: number, [r, g, b]: number[], alpha: string) =>
  filter(id, w, h, `
    <feTurbulence type='${type}' baseFrequency='${frequency}' numOctaves='${octaves}' seed='${seed}' stitchTiles='stitch'/>
    <feColorMatrix type='matrix' values='0 0 0 0 ${r} 0 0 0 0 ${g} 0 0 0 0 ${b} 0 0 0 ${alpha}'/>`)

/**
 * Lights the graphic with a relief from noise: `frequency` sets the size of the bumps,
 * `depth` how deep they are; multiplied in (diffuse) plus a soft sheen (specular).
 */
const relief = (id: string, w: number, h: number, frequency: string, depth: number, seed: number, shine = 0.35) =>
  filter(id, w, h, `
    <feTurbulence type='fractalNoise' baseFrequency='${frequency}' numOctaves='5' seed='${seed}' stitchTiles='stitch' result='noise'/>
    <feColorMatrix in='noise' type='luminanceToAlpha' result='height'/>
    <feDiffuseLighting in='height' surfaceScale='${depth}' diffuseConstant='1' lighting-color='#ffffff' result='diffuse'>
      <feDistantLight azimuth='225' elevation='40'/>
    </feDiffuseLighting>
    <!-- flat ground comes out at about sin(40°); lift it back to full brightness -->
    <feComponentTransfer in='diffuse' result='shade'>
      <feFuncR type='linear' slope='1.55'/><feFuncG type='linear' slope='1.55'/><feFuncB type='linear' slope='1.55'/>
    </feComponentTransfer>
    <feBlend in='SourceGraphic' in2='shade' mode='multiply' result='lit'/>
    <feSpecularLighting in='height' surfaceScale='${depth}' specularConstant='0.8' specularExponent='22' lighting-color='#fff4dc' result='spec'>
      <feDistantLight azimuth='225' elevation='50'/>
    </feSpecularLighting>
    <feComposite in='spec' in2='SourceAlpha' operator='in' result='sheen'/>
    <feComposite in='lit' in2='sheen' operator='arithmetic' k1='0' k2='1' k3='${shine}' k4='0'/>`)

/** Darker towards the edges and corners, like dirt settling there */
const grime = (id: string, w: number, h: number) => `
  <radialGradient id='${id}' cx='0.5' cy='0.45' r='0.75'>
    <stop offset='0.55' stop-color='#000' stop-opacity='0'/>
    <stop offset='1' stop-color='#000' stop-opacity='0.45'/>
  </radialGradient>
  <rect width='${w}' height='${h}' fill='url(#${id})'/>`

/** Soft bevel: lit top and left edge, shaded bottom and right */
const bevel = (w: number, h: number, size: number, pressed = false) => `
  <linearGradient id='bevel-top' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='#fff8e0' stop-opacity='${pressed ? 0.05 : 0.45}'/><stop offset='1' stop-color='#fff8e0' stop-opacity='0'/></linearGradient>
  <linearGradient id='bevel-bottom' x1='0' y1='1' x2='0' y2='0'><stop offset='0' stop-color='#000' stop-opacity='0.8'/><stop offset='1' stop-color='#000' stop-opacity='0'/></linearGradient>
  <linearGradient id='bevel-left' x1='0' y1='0' x2='1' y2='0'><stop offset='0' stop-color='#fff8e0' stop-opacity='${pressed ? 0.03 : 0.25}'/><stop offset='1' stop-color='#fff8e0' stop-opacity='0'/></linearGradient>
  <linearGradient id='bevel-right' x1='1' y1='0' x2='0' y2='0'><stop offset='0' stop-color='#000' stop-opacity='0.7'/><stop offset='1' stop-color='#000' stop-opacity='0'/></linearGradient>
  <rect width='${w}' height='${size}' fill='url(#bevel-top)'/>
  <rect y='${h - size}' width='${w}' height='${size}' fill='url(#bevel-bottom)'/>
  <rect width='${size}' height='${h}' fill='url(#bevel-left)'/>
  <rect x='${w - size}' width='${size}' height='${h}' fill='url(#bevel-right)'/>
  <rect x='0.15' y='0.15' width='${w - 0.3}' height='${h - 0.3}' fill='none' stroke='#0b0907' stroke-width='0.3'/>`

const chromeGradient = `
  <radialGradient id='chrome' cx='0.34' cy='0.28' r='0.85'>
    <stop offset='0' stop-color='#ffffff'/>
    <stop offset='0.12' stop-color='#e4e5e2'/>
    <stop offset='0.4' stop-color='#8d9090'/>
    <stop offset='0.75' stop-color='#3a3c3d'/>
    <stop offset='1' stop-color='#141515'/>
  </radialGradient>
  <radialGradient id='rust' cx='0.5' cy='0.5' r='0.5'>
    <stop offset='0.6' stop-color='#5a2f12' stop-opacity='0.55'/>
    <stop offset='1' stop-color='#5a2f12' stop-opacity='0'/>
  </radialGradient>`

/** Rivet sunk into the plate: rust stain, dark recess, chrome dome with a highlight */
function rivet(x: number, y: number, r = 3.3) {
  return `
    <circle cx='${x + 0.4}' cy='${y + 0.9}' r='${r * 1.7}' fill='url(#rust)'/>
    <circle cx='${x}' cy='${y}' r='${r + 0.75}' fill='#0c0a08' opacity='0.85'/>
    <circle cx='${x + 0.35}' cy='${y + 0.45}' r='${r}' fill='#000' opacity='0.6'/>
    <circle cx='${x}' cy='${y}' r='${r}' fill='url(#chrome)'/>
    <circle cx='${x}' cy='${y}' r='${r}' fill='none' stroke='#0d0e0e' stroke-width='0.3'/>
    <ellipse cx='${x - r * 0.35}' cy='${y - r * 0.4}' rx='${r * 0.32}' ry='${r * 0.2}' fill='#fff' opacity='0.85' transform='rotate(-35 ${x - r * 0.35} ${y - r * 0.4})'/>`
}

/**
 * A worn stone plate of any size (in original pixels): camouflage patches of light
 * and dark stone, lit relief, scratches, grime and bevelled edges, with optional
 * rivets; `pressed` sinks it in. Used for the tabs and the sidebar frame.
 */
export function plateImage(w: number, h: number, { rivets = [] as [number, number][], pressed = false } = {}) {
  const stone = stoneLayers(w, h, pressed)
  return svg(w, h, `
    <defs>
      ${chromeGradient}
      ${stone.defs}
    </defs>
    ${stone.body}
    ${bevel(w, h, Math.min(2.2, h / 6), pressed)}
    ${pressed ? `<rect width='${w}' height='1.8' fill='#000' opacity='0.4'/>` : ''}
    ${rivets.map(([x, y]) => rivet(x, y)).join('')}`)
}

/** The worn stone itself (camouflage, relief, scratches, grime), without edges and rivets */
function stoneLayers(w: number, h: number, pressed = false) {
  return {
    defs: `
      <linearGradient id='base' x1='0' y1='0' x2='0' y2='1'>
        <stop offset='0' stop-color='${pressed ? '#55493a' : '#86755a'}'/>
        <stop offset='0.55' stop-color='${pressed ? '#41372c' : '#665741'}'/>
        <stop offset='1' stop-color='${pressed ? '#2f281f' : '#42382b'}'/>
      </linearGradient>
      ${colouredNoise('light', w, h, 'fractalNoise', '0.04 0.09', 4, 3, [0.8, 0.7, 0.53], '4 -1.9')}
      ${colouredNoise('dark', w, h, 'fractalNoise', '0.05 0.12', 4, 11, [0.16, 0.12, 0.08], '3.6 -1.75')}
      ${colouredNoise('moss', w, h, 'fractalNoise', '0.08 0.18', 3, 17, [0.3, 0.3, 0.2], '3 -1.8')}
      ${colouredNoise('pores', w, h, 'fractalNoise', '1.1', 2, 5, [0.06, 0.05, 0.03], '1.8 -0.9')}
      ${colouredNoise('scratches', w, h, 'turbulence', '0.02 0.45', 2, 23, [0.05, 0.04, 0.03], '-12 2.75')}
      ${colouredNoise('nicks', w, h, 'turbulence', '0.03 0.35', 2, 41, [0.93, 0.87, 0.74], '-14 2.7')}
      ${relief('stone', w, h, '0.16 0.24', 2.8, 7, 0.45)}`,
    body: `
      <g filter='url(#stone)'>
        <rect width='${w}' height='${h}' fill='url(#base)'/>
        <rect width='${w}' height='${h}' filter='url(#light)'/>
        <rect width='${w}' height='${h}' filter='url(#moss)'/>
        <rect width='${w}' height='${h}' filter='url(#dark)'/>
        <rect width='${w}' height='${h}' filter='url(#pores)'/>
      </g>
      <rect width='${w}' height='${h}' filter='url(#scratches)' opacity='0.5'/>
      <rect width='${w}' height='${h}' filter='url(#nicks)' opacity='0.35'/>
      ${grime('grime', w, h)}`,
  }
}

/** The stone tab with two rivets ("Optionen", credits). */
export const tabImage = (pressed = false) =>
  plateImage(TAB.width, TAB.height, { rivets: [[8.5, TAB.height / 2], [TAB.width - 8.5, TAB.height / 2]], pressed })

/** Brushed metal streaks along x (`along` = 'x') or y */
const brushed = (id: string, w: number, h: number, along: 'x' | 'y', seed: number) => filter(id, w, h, `
  <feTurbulence type='fractalNoise' baseFrequency='${along === 'x' ? '0.004 0.9' : '0.9 0.004'}' numOctaves='3' seed='${seed}' stitchTiles='stitch'/>
  <feColorMatrix type='matrix' values='0 0 0 0 1 0 0 0 0 0.95 0 0 0 0 0.85 0 0 0 1.6 -0.75'/>`)

/** The rail between the tabs: a dark groove above a worn, brushed brass strip. */
export function railImage() {
  const { width: w, height: h } = TAB
  return svg(w, h, `
    <defs>
      <linearGradient id='bands' x1='0' y1='0' x2='0' y2='1'>
        <stop offset='0' stop-color='#0c0906'/>
        <stop offset='0.15' stop-color='#241c13'/>
        <stop offset='0.19' stop-color='#d2bd8a'/>
        <stop offset='0.24' stop-color='#8a764f'/>
        <stop offset='0.42' stop-color='#a48e62'/>
        <stop offset='0.6' stop-color='#6b5a3d'/>
        <stop offset='0.69' stop-color='#3a2f21'/>
        <stop offset='0.73' stop-color='#090705'/>
        <stop offset='0.78' stop-color='#b9a376'/>
        <stop offset='0.84' stop-color='#5a4b34'/>
        <stop offset='1' stop-color='#0a0806'/>
      </linearGradient>
      <clipPath id='strip'><rect y='${h * 0.18}' width='${w}' height='${h * 0.54}'/></clipPath>
      ${brushed('brush', w, h, 'x', 13)}
      ${colouredNoise('wear', w, h, 'fractalNoise', '0.04 0.3', 4, 29, [0.12, 0.09, 0.05], '3 -1.5')}
      ${colouredNoise('scratches', w, h, 'turbulence', '0.015 0.5', 2, 31, [0.04, 0.03, 0.02], '-12 2.75')}
      ${relief('dents', w, h, '0.06 0.4', 0.9, 19, 0.5)}
    </defs>
    <g filter='url(#dents)'>
      <rect width='${w}' height='${h}' fill='url(#bands)'/>
      <g clip-path='url(#strip)'>
        <rect width='${w}' height='${h}' filter='url(#brush)' opacity='0.16'/>
        <rect width='${w}' height='${h}' filter='url(#wear)'/>
        <rect width='${w}' height='${h}' filter='url(#scratches)' opacity='0.4'/>
      </g>
    </g>`)
}

/**
 * Brass pillar along the sides of the sidebar: a round, brushed brass rod in a
 * dark groove with a bolt; one tile is `PILLAR.width` × `PILLAR.height`, repeated down.
 */
export const PILLAR = { width: 6, height: 48 }
export function pillarImage() {
  const { width: w, height: h } = PILLAR
  return svg(w, h, `
    <defs>
      <linearGradient id='rod' x1='0' y1='0' x2='1' y2='0'>
        <stop offset='0' stop-color='#120d07'/>
        <stop offset='0.12' stop-color='#5e4b2c'/>
        <stop offset='0.32' stop-color='#e2cb92'/>
        <stop offset='0.42' stop-color='#fff0c4'/>
        <stop offset='0.55' stop-color='#b29a64'/>
        <stop offset='0.8' stop-color='#5c4a2c'/>
        <stop offset='1' stop-color='#140f08'/>
      </linearGradient>
      ${chromeGradient}
      ${brushed('brush', w, h, 'y', 37)}
      ${colouredNoise('tarnish', w, h, 'fractalNoise', '0.3 0.05', 4, 43, [0.2, 0.17, 0.08], '3 -1.55')}
    </defs>
    <rect width='${w}' height='${h}' fill='url(#rod)'/>
    <rect width='${w}' height='${h}' filter='url(#brush)' opacity='0.3'/>
    <rect width='${w}' height='${h}' filter='url(#tarnish)'/>
    <!-- collar with a bolt at the end of each segment -->
    <rect y='${h - 3.2}' width='${w}' height='3.2' fill='#000' opacity='0.35'/>
    <rect y='${h - 3.4}' width='${w}' height='0.35' fill='#fff2c8' opacity='0.45'/>
    ${rivet(w / 2, h - 1.6, 1.45)}`)
}

/**
 * Blue-grey steel of the sidebar buttons like in the original: slightly mottled,
 * with rounded corners and a lit top-left edge. `pressed` sinks the button in:
 * darker, with the edges turned round (shadow top left, light bottom right).
 * Stretched over a button, so `w` × `h` should match its proportions.
 */
export function steelImage(w: number, h: number, pressed = false) {
  const r = Math.min(w, h) * 0.12
  const edge = Math.min(w, h) * 0.14
  const [lit, shade] = pressed ? ['#000', '#e8f0f8'] : ['#eef4fa', '#000']
  return svg(w, h, `
    <defs>
      <linearGradient id='steel' x1='0' y1='0' x2='0.35' y2='1'>
        <stop offset='0' stop-color='${pressed ? '#56677a' : '#b2c2d2'}'/>
        <stop offset='0.5' stop-color='${pressed ? '#64768a' : '#8a9db2'}'/>
        <stop offset='1' stop-color='${pressed ? '#73869b' : '#687b91'}'/>
      </linearGradient>
      <linearGradient id='edge-top' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='${lit}' stop-opacity='${pressed ? 0.45 : 0.6}'/><stop offset='1' stop-color='${lit}' stop-opacity='0'/></linearGradient>
      <linearGradient id='edge-left' x1='0' y1='0' x2='1' y2='0'><stop offset='0' stop-color='${lit}' stop-opacity='${pressed ? 0.35 : 0.4}'/><stop offset='1' stop-color='${lit}' stop-opacity='0'/></linearGradient>
      <linearGradient id='edge-bottom' x1='0' y1='1' x2='0' y2='0'><stop offset='0' stop-color='${shade}' stop-opacity='${pressed ? 0.25 : 0.6}'/><stop offset='1' stop-color='${shade}' stop-opacity='0'/></linearGradient>
      <linearGradient id='edge-right' x1='1' y1='0' x2='0' y2='0'><stop offset='0' stop-color='${shade}' stop-opacity='${pressed ? 0.2 : 0.5}'/><stop offset='1' stop-color='${shade}' stop-opacity='0'/></linearGradient>
      <clipPath id='round'><rect width='${w}' height='${h}' rx='${r}'/></clipPath>
      ${colouredNoise('light', w, h, 'fractalNoise', '0.14 0.18', 4, 53, [0.86, 0.91, 0.97], '2.6 -1.35')}
      ${colouredNoise('dark', w, h, 'fractalNoise', '0.18 0.22', 4, 59, [0.18, 0.23, 0.3], '2.6 -1.4')}
      ${colouredNoise('scratches', w, h, 'turbulence', '0.03 0.5', 2, 67, [0.2, 0.25, 0.32], '-12 2.75')}
      ${relief('dents', w, h, '0.2 0.25', 0.5, 61, 0.5)}
    </defs>
    <g clip-path='url(#round)'>
      <g filter='url(#dents)'>
        <rect width='${w}' height='${h}' fill='url(#steel)'/>
        <rect width='${w}' height='${h}' filter='url(#light)'/>
        <rect width='${w}' height='${h}' filter='url(#dark)'/>
        <rect width='${w}' height='${h}' filter='url(#scratches)' opacity='0.4'/>
      </g>
      <rect width='${w}' height='${edge}' fill='url(#edge-top)'/>
      <rect width='${edge}' height='${h}' fill='url(#edge-left)'/>
      <rect y='${h - edge}' width='${w}' height='${edge}' fill='url(#edge-bottom)'/>
      <rect x='${w - edge}' width='${edge}' height='${h}' fill='url(#edge-right)'/>
    </g>
    <rect x='0.3' y='0.3' width='${w - 0.6}' height='${h - 0.6}' rx='${r}' fill='none' stroke='#141a21' stroke-width='0.6'/>`)
}

export type Corner = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'

/**
 * Black steel bracket around a corner of the radar, in the look of the metal of the
 * Nod emblem: very dark, finely grained and pitted, with rounded bevels catching
 * grey highlights from the top left. Each corner is drawn on its own (not mirrored),
 * so the light comes from the same side on all four.
 *
 * `width` × `height` is the bracket's box (original pixels), `side` the width of its
 * upright arm and `cap` that of its level arm, so it can cover a frame exactly.
 */
export function blackSteelCorner(corner: Corner, { width, height, side, cap }: { width: number, height: number, side: number, cap: number }) {
  const flipX = corner.endsWith('right')
  const flipY = corner.startsWith('bottom')
  const p = (x: number, y: number) => `${flipX ? width - x : x},${flipY ? height - y : y}`
  // an L with a rounded outer and inner corner
  const m = 0.4
  const path = `M${p(m, height)} L${p(m, 6)} Q${p(m, m)} ${p(6, m)} L${p(width, m)} L${p(width, cap)} L${p(side + 4, cap)} Q${p(side, cap)} ${p(side, cap + 4)} L${p(side, height)} Z`
  const bolt = flipX ? width - side / 2 : side / 2
  const boltY = flipY ? height - cap / 2 : cap / 2
  const s = Math.max(width, height)
  const steel = blackSteelLayers(path, s, s)
  return svg(width, height, `
    <defs>
      ${chromeGradient}
      ${steel.defs}
    </defs>
    ${steel.body}
    <circle cx='${bolt + 0.3}' cy='${boltY + 0.4}' r='2.3' fill='#000' opacity='0.75'/>
    <circle cx='${bolt}' cy='${boltY}' r='2.1' fill='url(#chrome)' opacity='0.7'/>
    <circle cx='${bolt}' cy='${boltY}' r='2.1' fill='none' stroke='#050505' stroke-width='0.35'/>`)
}

/**
 * Black steel (like the metal of the Nod emblem) in the shape of `path`: very dark,
 * grained and pitted, its rounded edges lit with grey highlights from the top left,
 * with a soft drop shadow. `round` sets how round the edges are.
 */
function blackSteelLayers(path: string | string[], w: number, h: number, round = 1.1, hole?: string, part?: string) {
  // each part is its own path, so overlapping parts add up; a hole is cut out of all of
  // them, and `part` (a region) keeps only what lies inside it. Both happen before the
  // edges are lit, so the metal ends there with a finished, rounded edge, not a cut.
  const shapes = (fill: string) => [path].flat().map(d => `<path d='${d}' fill='${fill}'/>`).join('')
  const masked = (content: string) => {
    const inPart = part ? `<g clip-path='url(#steel-part)'>${content}</g>` : content
    return hole ? `<g mask='url(#hole)'>${inPart}</g>` : inPart
  }
  return {
    defs: `
      ${part ? `<clipPath id='steel-part'><path d='${part}'/></clipPath>` : ''}
      ${hole ? `<mask id='hole' maskUnits='userSpaceOnUse' x='0' y='0' width='${w}' height='${h}'><rect width='${w}' height='${h}' fill='#fff'/><path d='${hole}' fill='#000'/></mask>` : ''}
      <linearGradient id='steel-base' x1='0' y1='0' x2='1' y2='1'>
        <stop offset='0' stop-color='#3a3a3b'/>
        <stop offset='0.5' stop-color='#1e1e1f'/>
        <stop offset='1' stop-color='#111112'/>
      </linearGradient>
      <clipPath id='shape'>${shapes('#000')}</clipPath>
      ${colouredNoise('grain', w, h, 'fractalNoise', '0.6', 3, 71, [0.36, 0.36, 0.37], '2 -0.9')}
      ${colouredNoise('pits', w, h, 'fractalNoise', '1.4', 2, 73, [0, 0, 0], '4 -2.4')}
      <filter id='bevel' x='0' y='0' width='${w}' height='${h}' filterUnits='userSpaceOnUse' color-interpolation-filters='sRGB'>
        <!-- height: the blurred outline (rounded edges) plus a little grain -->
        <feGaussianBlur in='SourceAlpha' stdDeviation='${round}' result='blur'/>
        <feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' seed='79' result='noise'/>
        <feColorMatrix in='noise' type='luminanceToAlpha' result='grainHeight'/>
        <feComposite in='blur' in2='grainHeight' operator='arithmetic' k2='1' k3='0.12' result='height'/>
        <feDiffuseLighting in='height' surfaceScale='4' diffuseConstant='1' lighting-color='#ffffff' result='diffuse'>
          <feDistantLight azimuth='225' elevation='45'/>
        </feDiffuseLighting>
        <feComposite in='SourceGraphic' in2='diffuse' operator='arithmetic' k1='1.5' result='lit'/>
        <feSpecularLighting in='height' surfaceScale='4' specularConstant='1.1' specularExponent='28' lighting-color='#c8c8cc' result='spec'>
          <feDistantLight azimuth='225' elevation='35'/>
        </feSpecularLighting>
        <feComposite in='lit' in2='spec' operator='arithmetic' k2='1' k3='0.7' result='shiny'/>
        <feComposite in='shiny' in2='SourceAlpha' operator='in'/>
      </filter>
      <filter id='shadow' x='0' y='0' width='${w}' height='${h}' filterUnits='userSpaceOnUse'>
        <feGaussianBlur in='SourceAlpha' stdDeviation='${round}'/>
        <feOffset dx='0.8' dy='1.1'/>
      </filter>`,
    body: `
      <g filter='url(#shadow)' opacity='0.8'>${masked(shapes('#000'))}</g>
      <g filter='url(#bevel)'>
        ${masked(`
          ${shapes('url(#steel-base)')}
          <g clip-path='url(#shape)'>
            <rect width='${w}' height='${h}' filter='url(#grain)'/>
            <rect width='${w}' height='${h}' filter='url(#pits)' opacity='0.8'/>
          </g>`)}
      </g>`,
  }
}

/** Where the emblem sits on the radar cover, as fractions of the screen (centre, dome diameter / height) */
export const RADAR_EMBLEM = { x: 0.5, y: 0.45, size: 0.62 }

/**
 * Where the cover splits open, after the original. It never runs through stone, only
 * between metal and metal or the emblem and metal: straight in from the left edge
 * along a bar to the bottom of the emblem, round the emblem's edge up to 2/5 of its
 * height, then straight out to the right along a higher bar.
 */
export const RADAR_CUT = { rise: 0.4 }

/** How far the radar cover reaches past the screen on each side (fraction of its width) */
export const RADAR_OVERFLOW = 0.6

/** Size of the radar screen (inside its frame) in original pixels */
export const RADAR_SCREEN = { width: 142, height: 115 }

/**
 * The cover of the radar while it is off, after the original: stone behind a frame of
 * black steel struts, two diagonals from the corners and a double bar across, all
 * meeting a thick ring that holds the emblem (drawn on top, see HudRadar).
 */
export function radarCoverImage(part: 'top' | 'bottom' | 'whole' = 'whole') {
  const { width: w, height: h } = RADAR_SCREEN
  // the cover reaches past the screen on both sides, so nothing shows while it slides sideways
  const m = w * RADAR_OVERFLOW
  const W = w + 2 * m
  const cx = m + w * RADAR_EMBLEM.x
  const cy = h * RADAR_EMBLEM.y
  /** All metal is this wide; along the cut twice as wide (a piece on each side) */
  const metal = 13
  const ring = { inner: h * (RADAR_EMBLEM.size / 2), outer: h * (RADAR_EMBLEM.size / 2) + metal }
  // diagonals: from the centre out to the four sides, all at the same angle (an X);
  // steep enough that the lower ones come out to the side of the corner brackets
  const STRUT_ANGLE = (40 * Math.PI) / 180
  const strut = (sx: -1 | 1, sy: -1 | 1, t: number) => {
    const reach = Math.hypot(W, h)
    const x = cx + sx * Math.cos(STRUT_ANGLE) * reach
    const y = cy + sy * Math.sin(STRUT_ANGLE) * reach
    const nx = -sy * Math.sin(STRUT_ANGLE) * t
    const ny = sx * Math.cos(STRUT_ANGLE) * t
    return `M${x + nx},${y + ny} L${cx + nx},${cy + ny} L${cx - nx},${cy - ny} L${x - nx},${y - ny} Z`
  }
  const circle = (r: number) => `M${cx - r},${cy} a${r},${r} 0 1,0 ${2 * r},0 a${r},${r} 0 1,0 ${-2 * r},0 Z`
  // the cut: low on the left (bottom of the emblem), high on the right (2/5 up the emblem)
  const r = ring.inner
  const low = cy + r
  const high = cy + r - RADAR_CUT.rise * 2 * r
  const arcEnd = cx + Math.sqrt(r * r - (high - cy) ** 2)
  const cut = `M0,${low} L${cx},${low} A${r},${r} 0 0,0 ${arcEnd},${high} L${W},${high}`
  // the bars carry the cut: the left ones low, the right ones high, like in the original
  const halfBar = (x0: number, x1: number, y: number, t: number) => `M${x0},${y - t} L${x1},${y - t} L${x1},${y + t} L${x0},${y + t} Z`
  const half = metal / 2
  /** The diagonals are a bit sturdier than the rest */
  const strutHalf = half * 1.4
  const struts = [
    strut(-1, -1, strutHalf), strut(1, -1, strutHalf), strut(-1, 1, strutHalf), strut(1, 1, strutHalf),
    // the bars along the cut are double width, so each half keeps a full-width bar
    halfBar(0, cx, low, metal),
    halfBar(cx, W, high, metal),
    circle(ring.outer),
  ]
  // the halves: above and below the cut line
  const regions = {
    top: `${cut} L${W},0 L0,0 Z`,
    bottom: `${cut} L${W},${h} L0,${h} Z`,
    whole: undefined,
  }
  const stone = stoneLayers(W, h)
  const steel = blackSteelLayers(struts, W, h, 1.6, circle(ring.inner), regions[part])
  return svg(W, h, `
    <defs>
      ${stone.defs}
      ${steel.defs}
      ${part === 'whole' ? '' : `<clipPath id='half'><path d='${regions[part]}'/></clipPath>`}
    </defs>
    <g ${part === 'whole' ? '' : `clip-path='url(#half)'`}>
      ${stone.body}
      <rect width='${W}' height='${h}' fill='#000' opacity='0.22'/>
      <!-- dark well behind the emblem -->
      <circle cx='${cx}' cy='${cy}' r='${ring.inner}' fill='#070605'/>
    </g>
    ${steel.body}`)
}

/**
 * Light brass frame (the material of the sidebar's pillars) of `w` × `h` original
 * pixels and `t` thick: each side is a round, brushed rod lit from the top left,
 * mitred at the corners. Used around the inside of the radar's stone frame.
 */
export function brassFrameImage(w: number, h: number, t: number) {
  const stops = `
    <stop offset='0' stop-color='#3a2c17'/>
    <stop offset='0.1' stop-color='#9a8255'/>
    <stop offset='0.3' stop-color='#e8d39c'/>
    <stop offset='0.42' stop-color='#fff3cc'/>
    <stop offset='0.62' stop-color='#c9b07a'/>
    <stop offset='0.88' stop-color='#7a6440'/>
    <stop offset='1' stop-color='#2a1f10'/>`
  // a side is a trapezoid between the outer and the inner edge (mitred corners)
  const side = (points: [number, number][], gradient: string) =>
    `<polygon points='${points.map(p => p.join(',')).join(' ')}' fill='url(#${gradient})'/>`
  return svg(w, h, `
    <defs>
      <linearGradient id='down' x1='0' y1='0' x2='0' y2='1'>${stops}</linearGradient>
      <linearGradient id='up' x1='0' y1='1' x2='0' y2='0'>${stops}</linearGradient>
      <linearGradient id='right' x1='0' y1='0' x2='1' y2='0'>${stops}</linearGradient>
      <linearGradient id='left' x1='1' y1='0' x2='0' y2='0'>${stops}</linearGradient>
      ${brushed('brush', w, h, 'x', 83)}
      ${colouredNoise('tarnish', w, h, 'fractalNoise', '0.08 0.3', 4, 89, [0.2, 0.17, 0.08], '3 -1.55')}
      <mask id='frame' maskUnits='userSpaceOnUse' x='0' y='0' width='${w}' height='${h}'>
        <rect width='${w}' height='${h}' fill='#fff'/>
        <rect x='${t}' y='${t}' width='${w - 2 * t}' height='${h - 2 * t}' fill='#000'/>
      </mask>
    </defs>
    <!-- lit from the top left: the top and left rods get the bright side outward -->
    ${side([[0, 0], [w, 0], [w - t, t], [t, t]], 'down')}
    ${side([[0, h], [w, h], [w - t, h - t], [t, h - t]], 'down')}
    ${side([[0, 0], [t, t], [t, h - t], [0, h]], 'right')}
    ${side([[w, 0], [w - t, t], [w - t, h - t], [w, h]], 'right')}
    <g mask='url(#frame)'>
      <rect width='${w}' height='${h}' filter='url(#brush)' opacity='0.25'/>
      <rect width='${w}' height='${h}' filter='url(#tarnish)'/>
    </g>
    <rect x='0.2' y='0.2' width='${w - 0.4}' height='${h - 0.4}' fill='none' stroke='#0d0904' stroke-width='0.4'/>
    <rect x='${t - 0.2}' y='${t - 0.2}' width='${w - 2 * t + 0.4}' height='${h - 2 * t + 0.4}' fill='none' stroke='#0d0904' stroke-width='0.4'/>`)
}
