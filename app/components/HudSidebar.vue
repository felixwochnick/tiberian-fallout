<script setup lang="ts">
import type { Battlefield } from '~/lib/game/battlefield'
import type { BaseMode } from '~/composables/useSkirmish'
import { type BuildInfo, canBuild, GDI_BUILD_OPTIONS, loadCameos, type BuildOption } from '~/lib/game/cameos'
import { blackSteelCorner, brassFrameImage, type Corner, hudScale, PILLAR, pillarImage, plateImage, steelImage } from '~/lib/game/hud'
import { getAssetStore } from '~/lib/storage/asset-store'

/**
 * GDI sidebar like in Tiberian Sun: radar on top, the row of repair / sell / power /
 * waypoint buttons, the power bar and the two build columns (structures, units)
 * with their scroll buttons at the bottom. Frame and buttons are vector graphics
 * (see hud.ts); only the cameos are the original pictures, smoothly scaled.
 */
const props = defineProps<{
  radar: boolean
  battlefield?: Battlefield
  /** Power output and drain of the base */
  power: { output: number, drain: number }
  /** Buildings the player owns (RULES.INI ids): only what they allow is offered */
  owned: string[]
  /** Highest tech level that may be built */
  techLevel?: number
  /** A transmission (VQA) to show in the radar */
  movie?: Uint8Array
}>()
const emit = defineEmits<{ radarBusy: [busy: boolean], movieEnd: [] }>()

/** Sizes in original pixels (the sidebar is 168 wide like TABS.SHP) */
const SIZE = { width: 168, radar: 134, buttons: 30, scroll: 20, power: 12, frame: 6, gap: 2 }
const COLUMN = (SIZE.width - 2 * SIZE.frame - SIZE.power - 3 * SIZE.gap) / 2
const SLOT = { width: COLUMN, height: (COLUMN * 48) / 64 }

const scale = ref(1)
const rows = ref(0)
const lower = ref<HTMLDivElement>()
/** At least this much stone (original pixels) below the scroll buttons */
const FOOT_MIN = 5
const cameos = ref(new Map<string, string>())
const scroll = reactive({ structures: 0, units: 0 })

/** Production, money and the game's rules of the running game */
const skirmish = useSkirmish()
const rules = computed(() => skirmish?.rules)

/** Info (price, time, …) of an option; undefined while the game's rules are not loaded */
const infoOf = (option: BuildOption) => rules.value?.info.get(option.id)
const jobOf = (option: BuildOption) => skirmish?.production.jobFor(option.id)
const queued = (option: BuildOption) => skirmish?.production.queued(option.id) ?? 0
const placingId = computed(() => skirmish?.placing?.id)
/** While a structure is being built, the other structures wait (they are shown dimmed) */
const isBlocked = (option: BuildOption) => {
  const job = skirmish?.production.structure
  return !!job && job.info.id !== option.id && !!infoOf(option)?.structure
}

const sounds = useUiSounds()

/**
 * Left click on a cameo: a finished structure goes to placing (or back), otherwise
 * building starts or goes on after a hold; units are queued.
 */
function build(option: BuildOption) {
  const info = infoOf(option)
  if (!skirmish || !info) return
  const job = jobOf(option)
  sounds.play('click')
  if (job?.state === 'ready') {
    skirmish.placing = skirmish.placing ? undefined : info
    return
  }
  const resuming = job?.state === 'paused'
  if (!skirmish.production.start(info)) {
    if (info.structure) sounds.speak('evaBuildingInProgress')
    return
  }
  if (!resuming) sounds.speak(info.structure ? 'evaBuilding' : 'evaTraining')
}

/** Right click on a cameo: hold, or cancel when on hold (the money comes back). */
function hold(option: BuildOption) {
  if (!skirmish) return
  if (skirmish.placing?.id === option.id) skirmish.placing = undefined
  const job = jobOf(option)
  if (!job) return
  const wasRunning = job.state === 'building' && job.progress > 0
  skirmish.credits.value += skirmish.production.hold(option.id)
  sounds.play('click')
  sounds.speak(wasRunning ? 'evaOnHold' : 'evaCancelled')
}

/** The tooltip at the hovered cameo, left of the sidebar */
const tip = ref<{ info: BuildInfo, top: number }>()
function showTip(option: BuildOption, event: MouseEvent) {
  const info = infoOf(option)
  const target = event.currentTarget as HTMLElement | null
  if (!info || !target) return
  tip.value = { info, top: target.getBoundingClientRect().top }
}

/** Only what can be built now (all of it while the game's rules are not available) */
const available = (options: BuildOption[], structure: boolean) =>
  rules.value
    ? options.filter(o => canBuild(rules.value!, o.id, props.owned, structure)
      && (rules.value!.info.get(o.id)?.techLevel ?? 0) <= (props.techLevel ?? 10))
    : options
const columns = computed(() => ({
  structures: available(GDI_BUILD_OPTIONS.structures, true),
  units: available(GDI_BUILD_OPTIONS.units, false),
}))
// fewer options: keep the scroll position within the list
watch(columns, () => {
  scrollColumn('structures', 0)
  scrollColumn('units', 0)
})

/**
 * EVA says "New construction options" when something can be built that could not
 * before (a building that unlocks it, the MCV unfolding); not when the rules first load.
 */
let known: Set<string> | undefined
watch(columns, (now) => {
  const ids = [...now.structures, ...now.units].map(o => o.id)
  if (!rules.value) return
  if (known && ids.some(id => !known!.has(id))) sounds.speak('evaNewOptions')
  known = new Set(ids)
}, { immediate: true })

/** The options of a column visible at its scroll position, padded with empty slots */
function slots(column: 'structures' | 'units') {
  const list: (BuildOption | undefined)[] = columns.value[column].slice(scroll[column], scroll[column] + rows.value)
  while (list.length < rows.value) list.push(undefined)
  return list
}

function scrollColumn(column: 'structures' | 'units', by: number) {
  const max = Math.max(0, columns.value[column].length - rows.value)
  scroll[column] = Math.min(max, Math.max(0, scroll[column] + by))
}

/**
 * Black steel brackets over the corners of the radar frame: each covers the frame
 * there completely (arms as wide as the frame on that side) and reaches a little over
 * the screen. The frame is RADAR_FRAME wide, see the padding of .radar-box.
 */
const RADAR_FRAME = { top: 7, side: 9, bottom: 6 }
const BRACKET = { width: 36, height: 30, overlap: 1.6 }
const corners: Corner[] = ['top-left', 'top-right', 'bottom-left', 'bottom-right']
/** Light brass frame along the inner edge of the stone frame, around the screen */
const BRASS = 5
const brassFrame = brassFrameImage(SIZE.width - 2 * RADAR_FRAME.side, SIZE.radar - RADAR_FRAME.top - RADAR_FRAME.bottom, BRASS)
const cornerImages = Object.fromEntries(corners.map(c => [c, blackSteelCorner(c, {
  width: BRACKET.width,
  height: BRACKET.height,
  side: RADAR_FRAME.side + BRACKET.overlap,
  cap: (c.startsWith('top') ? RADAR_FRAME.top : RADAR_FRAME.bottom) + BRACKET.overlap,
})]))

const buttons = [
  { id: 'repair', title: 'Reparieren' },
  { id: 'sell', title: 'Verkaufen' },
  { id: 'power', title: 'Strom an/aus' },
  { id: 'waypoint', title: 'Wegpunkte' },
] as const

/** A button switches its mode on (and the others off), a second click switches it off */
function toggle(id: BaseMode) {
  if (!skirmish) return
  sounds.play('click')
  skirmish.mode = skirmish.mode === id ? undefined : id
}

/** LEDs of the power bar in original pixels: margin at the ends, height of one, distance from one to the next */
const LED = { inset: 1.5, height: 2.4, pitch: 3.2 }
/** Power per LED at the start; when the bar is more than 3/4 full it goes up in steps */
const POWER_UNIT = { start: 10, step: 5, full: 0.75 }
const LED_RED: [number, number, number] = [216, 36, 28]
const LED_ORANGE: [number, number, number] = [240, 138, 28]
const LED_GREEN: [number, number, number] = [63, 210, 58]

/**
 * Power bar: one LED for every `unit` of power (only whole ones, rounded down). What
 * the base uses is red, the rest above it goes from orange to green.
 */
const powerBar = computed(() => {
  // the bar is as high as the build area
  const height = rows.value * (SLOT.height + SIZE.gap) + SIZE.gap
  const capacity = Math.max(1, Math.floor((height - 2 * LED.inset + LED.pitch - LED.height) / LED.pitch))
  const { output, drain } = props.power
  let unit = POWER_UNIT.start
  while (Math.floor(Math.max(output, drain) / unit) > capacity * POWER_UNIT.full) unit += POWER_UNIT.step
  const lit = Math.min(capacity, Math.floor(output / unit))
  const used = Math.min(capacity, Math.floor(drain / unit))
  const red = Math.min(lit, used)
  const spare = lit - red
  const leds = Array.from({ length: capacity }, (_, i) => {
    if (i >= lit) return undefined
    if (i < red) return `rgb(${LED_RED})`
    const t = spare > 1 ? (i - red) / (spare - 1) : 0
    return `rgb(${LED_ORANGE.map((c, k) => Math.round(c + (LED_GREEN[k]! - c) * t))})`
  })
  return { unit, leds }
})
const lowPower = computed(() => props.power.drain > props.power.output)
// EVA says so when the base starts to use more power than it produces
watch(lowPower, (low) => {
  if (low) sounds.speak('evaLowPower')
})

const style = computed(() => ({
  '--u': `${scale.value}px`,
  // the black steel corners take the place of rivets
  '--plate-radar': plateImage(SIZE.width, SIZE.radar),
  '--plate-buttons': plateImage(SIZE.width, SIZE.buttons),
  '--plate-scroll': plateImage(SIZE.width, SIZE.scroll),
  '--plate-foot': plateImage(SIZE.width, 24),
  '--pillar': pillarImage(),
  '--bracket-w': `${BRACKET.width * scale.value}px`,
  '--bracket-h': `${BRACKET.height * scale.value}px`,
  '--pillar-h': `${PILLAR.height * scale.value}px`,
  '--steel': steelImage(34, 25),
  '--steel-pressed': steelImage(34, 25, true),
  '--steel-arrow': steelImage(30, 15),
  '--steel-arrow-pressed': steelImage(30, 15, true),
  '--slot-h': `${SLOT.height * scale.value}px`,
}))

/**
 * As many full rows as fit; the build area is then exactly that high, so there is no
 * gap below the last row, and the rest goes to the stone below the scroll buttons.
 */
const buildHeight = computed(() => `${(rows.value * (SLOT.height + SIZE.gap) - SIZE.gap + 2 * SIZE.gap) * scale.value}px`)
function measure() {
  scale.value = hudScale()
  const u = scale.value
  const available = (lower.value?.clientHeight ?? 0) - (SIZE.scroll + FOOT_MIN + 2 * SIZE.gap) * u
  const slot = (SLOT.height + SIZE.gap) * u
  rows.value = Math.max(1, Math.floor((available + SIZE.gap * u) / slot))
  scrollColumn('structures', 0)
  scrollColumn('units', 0)
}

let observer: ResizeObserver | undefined
onMounted(async () => {
  measure()
  observer = new ResizeObserver(measure)
  observer.observe(lower.value!)
  window.addEventListener('resize', measure)
  const ids = [...GDI_BUILD_OPTIONS.structures, ...GDI_BUILD_OPTIONS.units].map(o => o.id)
  cameos.value = await getAssetStore().then(store => loadCameos(store, ids)).catch(() => new Map())
})
onBeforeUnmount(() => {
  observer?.disconnect()
  window.removeEventListener('resize', measure)
})
</script>

<template>
  <aside class="sidebar" :style="style">
    <section class="radar-box">
      <div class="screen">
        <HudRadar :online="radar" :battlefield="battlefield" :movie="movie" @busy="emit('radarBusy', $event)" @movie-end="emit('movieEnd')" />
        <i class="brass" :style="{ backgroundImage: brassFrame }" />
      </div>
      <i v-for="corner in corners" :key="corner" class="corner" :class="corner" :style="{ backgroundImage: cornerImages[corner] }" />
    </section>

    <section class="buttons">
      <button
        v-for="button in buttons"
        :key="button.id"
        class="tool"
        :class="{ on: skirmish?.mode === button.id }"
        :title="button.title"
        @click="toggle(button.id)"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <defs>
            <linearGradient :id="`gold-${button.id}`" x1="0" y1="0" x2="0.4" y2="1">
              <stop offset="0" stop-color="#fff4b8" />
              <stop offset="0.4" stop-color="#e8bd45" />
              <stop offset="1" stop-color="#8c5c0e" />
            </linearGradient>
            <linearGradient :id="`silver-${button.id}`" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#ffffff" />
              <stop offset="0.45" stop-color="#d9d4cc" />
              <stop offset="0.75" stop-color="#b08463" />
              <stop offset="1" stop-color="#6e4a33" />
            </linearGradient>
          </defs>
          <g stroke="#2a1c06" stroke-width="0.6" stroke-linejoin="round">
            <!-- wrench: silver with a copper tinge -->
            <path v-if="button.id === 'repair'" :fill="`url(#silver-${button.id})`" d="M17.5 2.5a5 5 0 0 0-4.8 6.4L3.3 18.3a2 2 0 0 0 2.8 2.8l9.4-9.4a5 5 0 0 0 6.4-4.8l-3 1.6-2.4-.8-.8-2.4 1.8-2.8z" />
            <!-- dollar -->
            <path v-else-if="button.id === 'sell'" :fill="`url(#gold-${button.id})`" d="M13 2h-2v2.1C8.2 4.5 6.5 6.3 6.5 8.6c0 2.7 2.2 3.7 4.5 4.3v4.3c-1.4-.3-2.4-1.1-2.8-2.4l-2 .7c.6 2 2.4 3.4 4.8 3.7V22h2v-2.8c2.9-.4 4.6-2.2 4.6-4.6 0-2.8-2.3-3.8-4.6-4.4V6.2c1.1.3 1.9 1 2.3 2l2-.7c-.6-1.8-2.2-3-4.3-3.4zm-2 4.2v3.9c-1.4-.5-2.3-1.1-2.3-2.2 0-.9.9-1.6 2.3-1.7zm2 7.4c1.5.5 2.4 1.1 2.4 2.2 0 1.1-.9 1.8-2.4 2z" />
            <!-- lightning -->
            <path v-else-if="button.id === 'power'" :fill="`url(#gold-${button.id})`" d="M15.5 1.5 6 13.5h6l-3 9 9.5-12.5h-6.2z" />
            <!-- waypoint: a golden beacon with a green ring at its tip -->
            <template v-else>
              <ellipse cx="12" cy="20" rx="3.6" ry="1.5" fill="none" stroke="#3fe05a" stroke-width="1.3" />
              <path :fill="`url(#gold-${button.id})`" d="M5 2.5h14l-5.6 8.2-1.4 9.3-1.4-9.3z" />
            </template>
          </g>
        </svg>
      </button>
    </section>

    <div ref="lower" class="lower">
    <section class="build" :style="{ flexBasis: buildHeight }">
      <div class="power" :class="{ low: lowPower }" :title="`Energie: ${power.output} / Verbrauch: ${power.drain} (${powerBar.unit} pro Strich)`">
        <div class="leds">
          <i v-for="(colour, i) in powerBar.leds" :key="i" :class="{ lit: colour }" :style="colour ? { background: colour } : undefined" />
        </div>
      </div>
      <div class="columns">
        <div v-for="column in (['structures', 'units'] as const)" :key="column" class="column">
          <button
            v-for="(option, i) in slots(column)"
            :key="option?.id ?? `empty-${i}`"
            class="slot"
            :class="{ empty: !option, blocked: option && isBlocked(option) }"
            :disabled="!option"
            @click="option && build(option)"
            @contextmenu.prevent.stop="option && hold(option)"
            @mouseenter="option && showTip(option, $event)"
            @mouseleave="tip = undefined"
          >
            <template v-if="option">
              <img v-if="cameos.get(option.id)" :src="cameos.get(option.id)" alt="">
              <!-- the clock: the part still to build is darkened, it shrinks clockwise -->
              <span
                v-if="jobOf(option) && jobOf(option)!.state !== 'ready'"
                class="clock"
                :style="{ '--done': `${jobOf(option)!.progress * 360}deg` }"
              />
              <span v-if="queued(option) > 1" class="count">{{ queued(option) }}</span>
              <span v-if="jobOf(option)?.state === 'ready'" class="status ready">{{ placingId === option.id ? 'Platzieren' : 'Bereit' }}</span>
              <span v-else-if="jobOf(option)?.state === 'paused'" class="status">Angehalten</span>
              <span class="name">{{ option.name }}</span>
            </template>
          </button>
        </div>
      </div>
    </section>

    <!-- price and regular build time of the cameo under the cursor -->
    <div v-if="tip" class="tip" :style="{ top: `${tip.top}px` }">
      <strong>{{ tip.info.name }}</strong>
      <span>{{ tip.info.cost }} Credits</span>
      <span>Bauzeit {{ formatTime(tip.info.seconds) }}</span>
    </div>

    <section class="scroll">
      <button class="arrow up" title="Gebäude hoch" @click="scrollColumn('structures', -1)" />
      <button class="arrow down" title="Gebäude runter" @click="scrollColumn('structures', 1)" />
      <button class="arrow up" title="Einheiten hoch" @click="scrollColumn('units', -1)" />
      <button class="arrow down" title="Einheiten runter" @click="scrollColumn('units', 1)" />
    </section>
    <!-- what is left below the last full row: stone under the scroll buttons -->
    <div class="foot" />
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  top: var(--hud-top, 0);
  right: 0;
  bottom: 0;
  z-index: 10;
  width: calc(var(--u) * 168);
  display: flex;
  flex-direction: column;
  user-select: none;
  /* brass pillars along both sides */
  background:
    var(--pillar) 0 0 / calc(var(--u) * 6) var(--pillar-h) repeat-y,
    var(--pillar) 100% 0 / calc(var(--u) * 6) var(--pillar-h) repeat-y,
    #0d0f0d;
}
button {
  font: inherit;
  padding: 0;
  border: 0;
  cursor: pointer;
}

/* ---- radar ---- */
.radar-box {
  position: relative;
  flex: 0 0 calc(var(--u) * 134);
  /* the frame, see RADAR_FRAME */
  padding: calc(var(--u) * 7) calc(var(--u) * 9) calc(var(--u) * 6);
  background: var(--plate-radar) 0 0 / 100% 100%;
}
.corner {
  position: absolute;
  width: var(--bracket-w);
  height: var(--bracket-h);
  background: 0 0 / 100% 100% no-repeat;
  pointer-events: none;
}
/* flush with the outer edge of the frame */
.corner.top-left {
  left: 0;
  top: 0;
}
.corner.top-right {
  right: 0;
  top: 0;
}
.corner.bottom-left {
  left: 0;
  bottom: 0;
}
.corner.bottom-right {
  right: 0;
  bottom: 0;
}
.screen {
  position: relative;
  width: 100%;
  height: 100%;
  /* room for the brass frame (BRASS) */
  padding: calc(var(--u) * 5);
}
.screen > :first-child {
  box-shadow: inset 0 0 calc(var(--u) * 6) #000;
}
.brass {
  position: absolute;
  inset: 0;
  background: 0 0 / 100% 100% no-repeat;
  pointer-events: none;
  filter: drop-shadow(calc(var(--u) * 0.5) calc(var(--u) * 0.7) calc(var(--u) * 0.6) rgba(0, 0, 0, 0.8));
}

/* ---- repair / sell / power / waypoint ---- */
.buttons {
  flex: 0 0 calc(var(--u) * 30);
  display: flex;
  justify-content: center;
  align-items: center;
  gap: calc(var(--u) * 2);
  background: var(--plate-buttons) 0 0 / 100% 100%;
}
.tool {
  width: calc(var(--u) * 34);
  height: calc(var(--u) * 25);
  display: grid;
  place-items: center;
  background: var(--steel) 0 0 / 100% 100%;
  box-shadow: 0 0 0 calc(var(--u) * 0.6) #0c0e10, 0 calc(var(--u) * 0.8) calc(var(--u) * 1.2) rgba(0, 0, 0, 0.6);
}
.tool svg {
  width: 82%;
  height: 92%;
  filter: drop-shadow(0 calc(var(--u) * 0.6) calc(var(--u) * 0.4) rgba(0, 0, 0, 0.6));
}
.tool[data-hover] {
  filter: brightness(1.12);
}
/* switched on (repair, sell …) or being clicked: pressed into the plate */
.tool.on,
.tool[data-active] {
  background-image: var(--steel-pressed);
  box-shadow: 0 0 0 calc(var(--u) * 0.6) #0c0e10, inset 0 calc(var(--u) * 1) calc(var(--u) * 1.6) rgba(0, 0, 0, 0.55);
}
.tool.on svg,
.tool[data-active] svg {
  transform: translate(calc(var(--u) * 0.4), calc(var(--u) * 0.7)) scale(0.94);
  filter: drop-shadow(0 calc(var(--u) * 0.3) calc(var(--u) * 0.3) rgba(0, 0, 0, 0.7)) brightness(0.92);
}

/* ---- power bar and build columns ---- */
.lower {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.foot {
  flex: 1 0 calc(var(--u) * 5);
  background: var(--plate-foot) 0 0 / 100% 100%;
}
.build {
  flex: 0 0 auto;
  min-height: 0;
  display: flex;
  gap: calc(var(--u) * 2);
  padding: calc(var(--u) * 2) calc(var(--u) * 6);
}
.power {
  position: relative;
  flex: 0 0 calc(var(--u) * 12);
  background: #050605;
  box-shadow: inset 0 0 0 calc(var(--u) * 0.8) #2a2a22;
  overflow: hidden;
}
/* LEDs from the bottom up: red as far as the base uses power, above that orange to green */
.leds {
  position: absolute;
  inset: calc(var(--u) * 1.5) calc(var(--u) * 2.5);
  display: flex;
  flex-direction: column-reverse;
  gap: calc(var(--u) * 0.8);
}
.leds i {
  flex: 0 0 calc(var(--u) * 2.4);
}
.low .leds .lit {
  animation: blink 0.8s steps(2) infinite;
}
@keyframes blink {
  50% {
    opacity: 0.35;
  }
}
.columns {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: calc(var(--u) * 2);
}
.column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: calc(var(--u) * 2);
}
.slot {
  position: relative;
  flex: 0 0 var(--slot-h);
  overflow: hidden;
  background: #070a08;
  box-shadow: 0 0 0 calc(var(--u) * 0.7) #6f7378, inset 0 0 0 calc(var(--u) * 0.7) #000;
  cursor: pointer;
}
.slot.empty {
  cursor: default;
}
.slot.blocked img {
  filter: grayscale(0.7) brightness(0.55);
}
.clock {
  position: absolute;
  inset: 0;
  background: conic-gradient(transparent 0 var(--done), rgba(0, 0, 0, 0.62) var(--done) 360deg);
}
.status {
  position: absolute;
  left: 0;
  right: 0;
  top: 32%;
  text-align: center;
  font: 700 calc(var(--u) * 7.5) / 1 'Arial Narrow', Arial, sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #fff;
  text-shadow: 0 0 calc(var(--u) * 1.5) #000, 0 0 calc(var(--u) * 1) #000;
}
.status.ready {
  color: #ffe85a;
  animation: blink-ready 1s steps(2) infinite;
}
@keyframes blink-ready {
  50% {
    opacity: 0.55;
  }
}
.count {
  position: absolute;
  top: calc(var(--u) * 1.5);
  right: calc(var(--u) * 2.5);
  font: 700 calc(var(--u) * 7.5) Arial, sans-serif;
  color: #fff;
  text-shadow: 0 0 calc(var(--u) * 1.5) #000;
}
.tip {
  position: fixed;
  right: calc(var(--u) * 168 + 6px);
  z-index: 20;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 10px;
  background: rgba(6, 8, 6, 0.92);
  border: 1px solid #6f7378;
  color: #e9e3c4;
  font: 600 13px Arial, sans-serif;
  white-space: nowrap;
  pointer-events: none;
}
.tip strong {
  color: #ffe85a;
  text-transform: uppercase;
  font-size: 12px;
}
.slot img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  image-rendering: auto;
}
.slot[data-hover]:not(.empty) img {
  filter: brightness(1.18);
}
.name {
  position: absolute;
  left: calc(var(--u) * 2);
  right: calc(var(--u) * 2);
  bottom: calc(var(--u) * 1.5);
  font: 700 calc(var(--u) * 6.2) / 1.05 'Arial Narrow', Arial, sans-serif;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  text-align: left;
  color: #fff;
  text-shadow:
    calc(var(--u) * 0.5) 0 0 #000, calc(var(--u) * -0.5) 0 0 #000,
    0 calc(var(--u) * 0.5) 0 #000, 0 calc(var(--u) * -0.5) 0 #000;
}

/* ---- scroll buttons ---- */
.scroll {
  flex: 0 0 calc(var(--u) * 20);
  display: flex;
  justify-content: center;
  align-items: center;
  gap: calc(var(--u) * 2);
  background: var(--plate-scroll) 0 0 / 100% 100%;
}
.arrow {
  position: relative;
  width: calc(var(--u) * 30);
  height: calc(var(--u) * 15);
  background: var(--steel-arrow) 0 0 / 100% 100%;
  box-shadow: 0 0 0 calc(var(--u) * 0.6) #0c0e10;
}
.arrow:nth-child(3) {
  margin-left: calc(var(--u) * 8);
}
.arrow::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  border-left: calc(var(--u) * 6) solid transparent;
  border-right: calc(var(--u) * 6) solid transparent;
  transform: translate(-50%, -50%);
}
.arrow.up::after {
  border-bottom: calc(var(--u) * 7) solid #1d2126;
  filter: drop-shadow(0 calc(var(--u) * 0.6) 0 rgba(255, 255, 255, 0.45));
}
.arrow.down::after {
  border-top: calc(var(--u) * 7) solid #1d2126;
  filter: drop-shadow(0 calc(var(--u) * 0.6) 0 rgba(255, 255, 255, 0.45));
}
.arrow[data-hover] {
  filter: brightness(1.2);
}
.arrow[data-active] {
  background-image: var(--steel-arrow-pressed);
}
</style>
