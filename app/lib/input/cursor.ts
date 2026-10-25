import { MixArchive } from '../formats/mix'
import { decodePalette, decodeShp, frameToRgba, type Shp } from '../formats/shp'
import type { AssetStore } from '../storage/asset-store'

export interface CursorImage {
  /** Image cropped to the drawn pixels and scaled */
  canvas: HTMLCanvasElement
  /** The same as data URL, for the CSS cursor */
  url: string
  /** Hot spot in pixels of `canvas` */
  hotX: number
  hotY: number
  /** Further frames of an animated cursor, shown one after the other (with this one first) */
  frames?: CursorImage[]
}

/** Frames per second of animated cursors */
export const CURSOR_FPS = 12

/** Screen directions of the scroll cursors, clockwise from up; [dx, dy] with y pointing down. */
export const SCROLL_DIRECTIONS = {
  up: [0, -1],
  upRight: [1, -1],
  right: [1, 0],
  downRight: [1, 1],
  down: [0, 1],
  downLeft: [-1, 1],
  left: [-1, 0],
  upLeft: [-1, -1],
} as const
export type ScrollDirection = keyof typeof SCROLL_DIRECTIONS

export type CursorKind = 'default' | 'hidden' | 'select' | 'move' | 'attack' | 'rally' | 'deploy' | 'deploy-blocked' | `scroll-${ScrollDirection}` | `blocked-${ScrollDirection}`

/** Animated cursors: first frame and number of frames in MOUSE.SHP */
const ANIMATED: Partial<Record<CursorKind, [first: number, count: number]>> = {
  /** Over something of one's own that can be selected: green brackets closing in on it */
  select: [18, 13],
  /** Units are selected: click on the ground to send them there */
  move: [31, 10],
  /** Own units selected, over an enemy: attack (red ellipse) */
  attack: [53, 5],
  /** A factory is selected: click on the ground to set its rally point (a beacon flag) */
  rally: [191, 10],
  /** Over the selected MCV: click to unfold it into a construction yard (arrows spreading out) */
  'deploy': [110, 9],
  /** … but there is no room for it here (crossed out) */
  'deploy-blocked': [119, 1],
}

/**
 * Frames of MOUSE.SHP (TIBSUN.MIX → CONQUER.MIX): the arrow, the green scroll
 * arrows from frame 2 and the crossed-out ones (map edge reached) from frame 10,
 * both clockwise from up.
 */
function cursorFrames() {
  const frames = { default: 0 } as Record<CursorKind, number>
  Object.keys(SCROLL_DIRECTIONS).forEach((direction, i) => {
    frames[`scroll-${direction as ScrollDirection}`] = 2 + i
    frames[`blocked-${direction as ScrollDirection}`] = 10 + i
  })
  return frames
}

/** Pixel-doubled on large screens, the original was made for 640×480. */
export const cursorScale = () => (window.innerHeight >= 900 ? 2 : 1)

/**
 * Hot spot: the tip of the arrow for the normal cursor; for scroll cursors the side
 * the arrow points to, so it sits fully on screen at the edge it points at.
 */
function hotSpot(kind: CursorKind, width: number, height: number) {
  if (kind === 'default') return [0, 0]
  if (ANIMATED[kind]) return [Math.floor(width / 2), Math.floor(height / 2)] // centred on the target
  const [dx, dy] = SCROLL_DIRECTIONS[kind.slice(kind.indexOf('-') + 1) as ScrollDirection]
  return [Math.round((dx + 1) / 2 * (width - 1)), Math.round((dy + 1) / 2 * (height - 1))]
}

function finish(kind: CursorKind, source: HTMLCanvasElement): CursorImage {
  const scale = cursorScale()
  const canvas = document.createElement('canvas')
  canvas.width = source.width * scale
  canvas.height = source.height * scale
  const ctx = canvas.getContext('2d')!
  ctx.imageSmoothingEnabled = false
  ctx.drawImage(source, 0, 0, canvas.width, canvas.height)
  const [hotX, hotY] = hotSpot(kind, canvas.width, canvas.height)
  return { canvas, url: canvas.toDataURL(), hotX: hotX!, hotY: hotY! }
}

function fullFrame(shp: Shp, frame: number, palette: Uint8Array) {
  const canvas = document.createElement('canvas')
  canvas.width = shp.width
  canvas.height = shp.height
  canvas.getContext('2d')!.putImageData(new ImageData(frameToRgba(shp, shp.frames[frame]!, palette), shp.width, shp.height), 0, 0)
  return canvas
}

/** A frame cropped to its drawn pixels. */
function cropFrame(shp: Shp, frame: number, palette: Uint8Array) {
  const pixels = shp.frames[frame]?.pixels
  if (!pixels) return undefined
  let left = shp.width
  let top = shp.height
  let right = -1
  let bottom = -1
  pixels.forEach((index, i) => {
    if (!index) return
    const x = i % shp.width
    const y = Math.floor(i / shp.width)
    left = Math.min(left, x)
    top = Math.min(top, y)
    right = Math.max(right, x)
    bottom = Math.max(bottom, y)
  })
  if (right < 0) return undefined
  const full = document.createElement('canvas')
  full.width = shp.width
  full.height = shp.height
  full.getContext('2d')!.putImageData(new ImageData(frameToRgba(shp, shp.frames[frame]!, palette), shp.width, shp.height), 0, 0)
  const cropped = document.createElement('canvas')
  cropped.width = right - left + 1
  cropped.height = bottom - top + 1
  cropped.getContext('2d')!.drawImage(full, -left, -top)
  return cropped
}

/** The original cursors (MOUSE.SHP with MOUSEPAL.PAL from CACHE.MIX). */
export async function loadCursors(store: AssetStore): Promise<Partial<Record<CursorKind, CursorImage>> | undefined> {
  const tibsun = await store.get('TIBSUN.MIX')
  if (!tibsun) return undefined
  const archive = await MixArchive.open(tibsun, 'TIBSUN.MIX')
  const shpBytes = await (await archive.openNested('CONQUER.MIX'))?.read('MOUSE.SHP')
  const palBytes = await (await archive.openNested('CACHE.MIX'))?.read('MOUSEPAL.PAL')
  if (!shpBytes || !palBytes) return undefined
  const shp = decodeShp(shpBytes)
  const palette = decodePalette(palBytes)
  const cursors: Partial<Record<CursorKind, CursorImage>> = {}
  for (const [kind, frame] of Object.entries(cursorFrames()) as [CursorKind, number][]) {
    const canvas = cropFrame(shp, frame, palette)
    if (canvas) cursors[kind] = finish(kind, canvas)
  }
  // animated ones keep the full frame, so they stay centred while they change size
  for (const [kind, [first, count]] of Object.entries(ANIMATED) as [CursorKind, [number, number]][]) {
    const frames = Array.from({ length: count }, (_, i) => finish(kind, fullFrame(shp, first + i, palette)))
    cursors[kind] = { ...frames[0]!, frames }
  }
  return cursors
}

/** Plain green arrows while the game data is missing. */
export function fallbackCursors(): Record<CursorKind, CursorImage> {
  const draw = (width: number, height: number, paint: (ctx: CanvasRenderingContext2D) => void) => {
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = '#9cff6a'
    ctx.strokeStyle = '#0b2a05'
    paint(ctx)
    return canvas
  }
  const cursors = {
    default: finish('default', draw(12, 19, (ctx) => {
      ctx.beginPath()
      ctx.moveTo(0.5, 0.5)
      ctx.lineTo(0.5, 16)
      ctx.lineTo(4.5, 12)
      ctx.lineTo(7.5, 18.5)
      ctx.lineTo(10, 17.5)
      ctx.lineTo(7, 11.5)
      ctx.lineTo(11.5, 11.5)
      ctx.closePath()
      ctx.fill()
      ctx.stroke()
    })),
  } as Record<CursorKind, CursorImage>
  for (const [direction, [dx, dy]] of Object.entries(SCROLL_DIRECTIONS) as [ScrollDirection, readonly [number, number]][]) {
    for (const blocked of [false, true]) {
      const kind: CursorKind = `${blocked ? 'blocked' : 'scroll'}-${direction}`
      cursors[kind] = finish(kind, draw(20, 20, (ctx) => {
        // arrow pointing in the scroll direction, red when the map edge is reached
        ctx.translate(10, 10)
        ctx.rotate(Math.atan2(dy, dx))
        ctx.beginPath()
        ctx.moveTo(9, 0)
        ctx.lineTo(-1, -8)
        ctx.lineTo(-1, -3)
        ctx.lineTo(-9, -3)
        ctx.lineTo(-9, 3)
        ctx.lineTo(-1, 3)
        ctx.lineTo(-1, 8)
        ctx.closePath()
        if (blocked) ctx.fillStyle = '#ff5a3c'
        ctx.fill()
        ctx.stroke()
      }))
    }
  }
  // select: green corner brackets closing in
  const frames = Array.from({ length: 6 }, (_, i) => finish('select', draw(40, 30, (ctx) => {
    const inset = 3 + i * 2.5
    ctx.strokeStyle = '#7cff4a'
    ctx.lineWidth = 2
    const [x0, y0, x1, y1] = [inset, inset * 0.75, 40 - inset, 30 - inset * 0.75]
    const l = 5
    ctx.beginPath()
    for (const [x, y, dx, dy] of [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]] as const) {
      ctx.moveTo(x + dx * l, y)
      ctx.lineTo(x, y)
      ctx.lineTo(x, y + dy * l)
    }
    ctx.stroke()
  })))
  cursors.select = { ...frames[0]!, frames }
  // attack: a red ring
  cursors.attack = finish('attack', draw(24, 16, (ctx) => {
    ctx.strokeStyle = '#ff3a1a'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.ellipse(12, 8, 10, 6, 0, 0, Math.PI * 2)
    ctx.stroke()
  }))
  // move: a small green target ring
  cursors.move = finish('move', draw(20, 14, (ctx) => {
    ctx.strokeStyle = '#7cff4a'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.ellipse(10, 7, 8, 5, 0, 0, Math.PI * 2)
    ctx.stroke()
  }))
  cursors.rally = finish('rally', draw(24, 28, (ctx) => {
    ctx.fillStyle = '#ffd21a'
    ctx.beginPath()
    ctx.moveTo(12, 3)
    ctx.lineTo(22, 7)
    ctx.lineTo(12, 11)
    ctx.closePath()
    ctx.fill()
    ctx.fillRect(11, 3, 2, 20)
    ctx.strokeStyle = '#3fff4a'
    ctx.beginPath()
    ctx.ellipse(12, 23, 8, 3.5, 0, 0, Math.PI * 2)
    ctx.stroke()
  }))
  // deploy: four arrows pointing outwards, red and crossed out where it cannot
  for (const kind of ['deploy', 'deploy-blocked'] as const) {
    cursors[kind] = finish(kind, draw(24, 24, (ctx) => {
      ctx.strokeStyle = kind === 'deploy' ? '#7cff4a' : '#ff5a3c'
      ctx.lineWidth = 2
      ctx.beginPath()
      for (const [dx, dy] of [[1, 1], [-1, 1], [1, -1], [-1, -1]]) {
        ctx.moveTo(12 + dx! * 3, 12 + dy! * 3)
        ctx.lineTo(12 + dx! * 10, 12 + dy! * 10)
        ctx.moveTo(12 + dx! * 10, 12 + dy! * 5)
        ctx.lineTo(12 + dx! * 10, 12 + dy! * 10)
        ctx.lineTo(12 + dx! * 5, 12 + dy! * 10)
      }
      if (kind === 'deploy-blocked') {
        ctx.moveTo(4, 20)
        ctx.lineTo(20, 4)
      }
      ctx.stroke()
    }))
  }
  return cursors
}
