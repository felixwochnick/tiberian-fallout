<script setup lang="ts">
import type { Battlefield } from '~/lib/game/battlefield'
import { radarCoverImage, RADAR_EMBLEM, RADAR_OVERFLOW } from '~/lib/game/hud'
import { VqaPlayback } from '~/lib/game/vqa-player'
import { Emblem } from '~/lib/menu/emblem'

/**
 * Radar screen of the sidebar. Without a radar it is closed by a cover like in the
 * original (stone behind black steel struts) with the GDI emblem (without its glow)
 * in the ring at its centre. When the radar comes online, the transmission opens it
 * like in the original: the cover parts along a cut below the emblem with static
 * behind it, first sliding sideways, then the upper part (with the emblem) slides off
 * to the top left and the lower one to the bottom right, the screen is full of
 * static and goes dark, then the map appears: the whole scrollable area with a frame
 * around the visible part. A click there scrolls. Going offline closes the cover again.
 */
const props = defineProps<{
  online: boolean
  battlefield?: Battlefield
  /** A video (VQA) to show in the radar, like the original's transmissions */
  movie?: Uint8Array
}>()
const emit = defineEmits<{ busy: [busy: boolean], movieEnd: [] }>()
/** The cover is open: the radar works, or a transmission comes in */
const open = computed(() => props.online || !!props.movie)

const screen = ref<HTMLDivElement>()
const logo = ref<HTMLDivElement>()
const noise = ref<HTMLCanvasElement>()
const minimap = ref<string>()
/** Map picture inside the screen, letterboxed to the area's aspect */
const mapBox = ref({ left: 0, top: 0, width: 0, height: 0 })
const viewStyle = ref<Record<string, string>>({})

const covers = { top: radarCoverImage('top'), bottom: radarCoverImage('bottom') }
/** The emblem's dome fills 78 % of its canvas; size the canvas so the dome fits the ring */
/** The covers are wider than the screen (RADAR_OVERFLOW on each side) */
const overflow = `${-RADAR_OVERFLOW * 100}%`
const logoStyle = {
  left: `${((RADAR_OVERFLOW + RADAR_EMBLEM.x) / (1 + 2 * RADAR_OVERFLOW)) * 100}%`,
  top: `${RADAR_EMBLEM.y * 100}%`,
  height: `${(RADAR_EMBLEM.size / 0.78) * 100}%`,
}

/** Opening in seconds (closing runs `split` backwards) */
const OPENING = {
  gap: [0, 0.5],
  split: [0.45, 1.15],
  static: [0.1, 2.5],
  dark: [2.2, 2.7],
  map: [2.6, 3.1],
} as const
const clamp01 = (x: number) => Math.min(1, Math.max(0, x))
const phase = ([a, b]: readonly [number, number], t: number) => clamp01((t - a) / (b - a))

/** State of the transmission: 0 = closed … OPENING end = map */
const opening = ref(open.value ? OPENING.map[1] : 0)
/** A transmission is running (the cover opening or closing) */
const busy = computed(() => opening.value > 0 && opening.value < OPENING.map[1])
watch(busy, value => emit('busy', value))
const halves = computed(() => {
  const t = opening.value
  // like in the original: for the first quarter the parts only slide sideways (the upper
  // one left, the lower one right), then off to the top left and the bottom right
  const p = phase([OPENING.gap[0], OPENING.split[1]], t)
  const SIDEWAYS = 0.4
  const side = 3 // % of the screen, each way
  const q = clamp01((p - SIDEWAYS) / (1 - SIDEWAYS)) ** 2
  const x = Math.min(1, p / SIDEWAYS) * side + q * 90
  const y = q * 110
  return {
    top: { transform: `translate(${-x}%, ${-y}%)` },
    bottom: { transform: `translate(${x}%, ${y}%)` },
  }
})
const staticOpacity = computed(() => {
  const t = opening.value
  return t >= OPENING.static[1] ? 0 : t > OPENING.static[0] ? 1 - phase(OPENING.dark, t) : 0
})
const mapOpacity = computed(() => phase(OPENING.map, opening.value))

let emblem: Emblem | undefined
let running = false
let unmounted = false

function layout() {
  const box = screen.value
  if (!box || !props.battlefield) return
  const aspect = props.battlefield.areaAspect
  let width = box.clientWidth
  let height = width / aspect
  if (height > box.clientHeight) {
    height = box.clientHeight
    width = height * aspect
  }
  mapBox.value = { left: (box.clientWidth - width) / 2, top: (box.clientHeight - height) / 2, width, height }
}

function drawMap() {
  if (!props.online || !props.battlefield) return
  layout()
  const { width, height } = mapBox.value
  if (width < 2 || height < 2) return
  const dpr = Math.min(window.devicePixelRatio, 2)
  minimap.value = props.battlefield.renderMinimap(Math.round(width * dpr), Math.round(height * dpr)).toDataURL()
}

let last = performance.now()
/** Steps the opening or closing and the static; follows the camera with the white frame. */
function frame(now: number) {
  if (!running) return
  // the game is paused: the cover and the transmission wait
  const dt = sounds.held.value ? 0 : Math.min(0.1, (now - last) / 1000)
  last = now
  const end = OPENING.map[1]
  if (open.value && opening.value < end) opening.value = Math.min(end, opening.value + dt)
  // the transmission starts once the static has gone dark
  if (props.movie && !playback && !sounds.held.value && opening.value >= OPENING.map[0]) startMovie(props.movie)
  // closing: the halves slide back together, faster
  if (!open.value && opening.value > 0) opening.value = opening.value > OPENING.split[1] ? OPENING.split[1] : Math.max(0, opening.value - dt * 1.4)
  if (staticOpacity.value > 0) drawStatic(now)
  const view = props.battlefield?.viewRect()
  if (view) {
    const { left, top, width, height } = mapBox.value
    viewStyle.value = {
      left: `${left + view.x * width}px`,
      top: `${top + view.y * height}px`,
      width: `${view.width * width}px`,
      height: `${view.height * height}px`,
    }
  }
  requestAnimationFrame(frame)
}

/**
 * TV static like in the original: grey speckles, now and then torn into vertical or
 * horizontal streaks. Drawn small and scaled up smoothly.
 */
let staticMode = 0
let staticModeUntil = 0
function drawStatic(now: number) {
  const canvas = noise.value
  if (!canvas) return
  const w = 96
  const h = 78
  if (canvas.width !== w) {
    canvas.width = w
    canvas.height = h
  }
  if (now > staticModeUntil) {
    const r = Math.random()
    staticMode = r < 0.6 ? 0 : r < 0.8 ? 1 : 2
    staticModeUntil = now + (staticMode ? 90 : 220) + Math.random() * 150
  }
  const ctx = canvas.getContext('2d')!
  const image = ctx.createImageData(w, h)
  const columns = Array.from({ length: w }, () => Math.random())
  const rows = Array.from({ length: h }, () => Math.random())
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const v = staticMode === 1 ? columns[x]! * 0.8 + Math.random() * 0.2 : staticMode === 2 ? rows[y]! * 0.8 + Math.random() * 0.2 : Math.random()
      const grey = v < 0.45 ? v * 120 : 90 + v * 165
      const i = (y * w + x) * 4
      image.data[i] = image.data[i + 1] = image.data[i + 2] = grey
      image.data[i + 3] = 255
    }
  }
  ctx.putImageData(image, 0, 0)
}

function onClick(event: MouseEvent) {
  if (mapOpacity.value < 1 || !props.battlefield || !screen.value) return
  const rect = screen.value.getBoundingClientRect()
  const { left, top, width, height } = mapBox.value
  props.battlefield.centerOn((event.clientX - rect.left - left) / width, (event.clientY - rect.top - top) / height)
}

function onResize() {
  emblem?.resize()
  drawMap()
}

watch(() => [props.online, props.battlefield], drawMap)

// the original's sounds: the transmission coming in, and the cover closing
const sounds = useUiSounds()
let radarSound: AudioBufferSourceNode | undefined
watch(open, (online) => {
  radarSound?.stop()
  radarSound = sounds.play(online ? 'radarOn' : 'radarOff')
})

/** The transmission: the video in the radar screen, with its sound */
const movieCanvas = ref<HTMLCanvasElement>()
let playback: VqaPlayback | undefined
function startMovie(bytes: Uint8Array) {
  // a spoken message: at the volume of the voices
  const out = sounds.output('voices')
  if (!movieCanvas.value || !out) return
  try {
    playback = new VqaPlayback(bytes, movieCanvas.value, out.ctx, out.gain)
  }
  catch (error) {
    console.error('Video konnte nicht abgespielt werden', error)
    emit('movieEnd')
    return
  }
  const current = playback
  current.done.then(() => {
    if (playback === current) emit('movieEnd')
  })
  current.start()
}
watch(() => props.movie, (movie) => {
  if (movie) return
  playback?.stop()
  playback = undefined
})

onMounted(async () => {
  window.addEventListener('resize', onResize)
  running = true
  requestAnimationFrame(frame)
  drawMap()
  emblem = await Emblem.create(logo.value!, 'gdi', { glow: false }).catch(() => undefined)
  if (unmounted) emblem?.dispose()
})

onBeforeUnmount(() => {
  unmounted = true
  running = false
  window.removeEventListener('resize', onResize)
  emblem?.dispose()
})
</script>

<template>
  <div ref="screen" class="radar" :class="{ online: mapOpacity >= 1 }" @click="onClick">
    <img
      v-if="minimap"
      class="map"
      :src="minimap"
      alt=""
      :style="{ left: `${mapBox.left}px`, top: `${mapBox.top}px`, width: `${mapBox.width}px`, height: `${mapBox.height}px`, opacity: movie ? 0 : mapOpacity }"
    >
    <div class="view" :style="{ ...viewStyle, opacity: movie ? 0 : mapOpacity }" />
    <canvas v-show="movie" ref="movieCanvas" class="movie" :style="{ opacity: mapOpacity }" />
    <canvas ref="noise" class="static" :style="{ opacity: staticOpacity }" />
    <div class="half bottom" :style="[{ backgroundImage: covers.bottom }, halves.bottom]" />
    <div class="half top" :style="[{ backgroundImage: covers.top }, halves.top]">
      <div ref="logo" class="logo" :style="logoStyle" />
    </div>
  </div>
</template>

<style scoped>
.radar {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #050605;
}
.half {
  position: absolute;
  top: 0;
  bottom: 0;
  left: v-bind(overflow);
  right: v-bind(overflow);
  background: 0 0 / 100% 100% no-repeat;
  will-change: transform;
}
/* the halves throw a shadow into the gap */
.half.top {
  filter: drop-shadow(calc(var(--u, 1px) * 1) calc(var(--u, 1px) * 1.2) calc(var(--u, 1px) * 1.2) rgba(0, 0, 0, 0.85));
}
.half.bottom {
  filter: drop-shadow(calc(var(--u, 1px) * -1) calc(var(--u, 1px) * -1.2) calc(var(--u, 1px) * 1.2) rgba(0, 0, 0, 0.85));
}
.logo {
  position: absolute;
  aspect-ratio: 1;
  transform: translate(-50%, -50%);
}
.logo :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
}
.movie {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}
.static {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.map,
.view {
  position: absolute;
}
.view {
  border: max(1px, calc(var(--u, 1px) * 0.8)) solid #f2f2f2;
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.8);
  pointer-events: none;
}
.online {
  cursor: pointer;
}
</style>
