<script setup lang="ts">
import { loadWestwoodSound } from '~/lib/menu/audio'
import { WESTWOOD_TIMELINE, WestwoodIntro } from '~/lib/menu/westwood-intro'
import { getAssetStore } from '~/lib/storage/asset-store'

const emit = defineEmits<{ done: [] }>()

const stage = ref<HTMLDivElement>()
const time = ref(0)
const needsClick = ref(false)

let intro: WestwoodIntro | undefined
let ctx: AudioContext | undefined
let gain: GainNode | undefined
let source: AudioBufferSourceNode | undefined
let startedAt = 0
let running = false
let soundStarted = false
let unmounted = false

/** Dev only: `/menu?intro=4` freezes the logo at that time. */
const frozenAt = import.meta.dev ? Number(useRoute().query.intro) : Number.NaN

const clamp01 = (x: number) => Math.min(1, Math.max(0, x))
const fade = ([a, b]: readonly [number, number]) => clamp01((time.value - a) / (b - a))
const flash = computed(() => fade(WESTWOOD_TIMELINE.flash) * (1 - fade(WESTWOOD_TIMELINE.fadeOut)))
const blackout = computed(() => fade(WESTWOOD_TIMELINE.fadeOut))
/** The texts are there while the logo is in full view. */
const texts = computed(() => fade(WESTWOOD_TIMELINE.texts) * (1 - fade(WESTWOOD_TIMELINE.textsOut)))

/** Audio clock when available, so picture and sound stay in sync. */
const now = () => (ctx && ctx.state === 'running' ? ctx.currentTime : performance.now() / 1000)

function frame() {
  if (!running || !intro) return
  time.value = Number.isFinite(frozenAt) ? frozenAt : now() - startedAt
  if (gain) gain.gain.value = (1 - fade(WESTWOOD_TIMELINE.soundOut)) * volumeOf('effects')
  if (blackout.value < 1) intro.render(time.value) // black after the flash, only the sound goes on
  if (time.value >= WESTWOOD_TIMELINE.end) finish()
  else requestAnimationFrame(frame)
}

async function begin() {
  needsClick.value = false
  await ctx?.resume().catch(() => {})
  startedAt = now()
  source?.start()
  soundStarted = !!source
  running = true
  requestAnimationFrame(frame)
}

function finish() {
  if (unmounted || (!running && !needsClick.value)) return
  running = false
  needsClick.value = false
  if (soundStarted) source?.stop()
  emit('done')
}

/** A click starts the logo when the browser still blocks sound, otherwise it skips it. */
function onClick() {
  if (needsClick.value) begin()
  else finish()
}

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape' || event.key === ' ' || event.key === 'Enter') finish()
}
const onResize = () => intro?.resize()

onMounted(async () => {
  try {
    intro = new WestwoodIntro(stage.value!)
  }
  catch (error) {
    console.error('Westwood-Logo konnte nicht geladen werden', error)
    emit('done')
    return
  }
  window.addEventListener('resize', onResize)
  window.addEventListener('keydown', onKey)

  ctx = new AudioContext()
  const sound = await loadWestwoodSound(ctx, await getAssetStore()).catch(() => undefined)
  if (unmounted) return
  if (sound) {
    gain = ctx.createGain()
    gain.connect(ctx.destination)
    source = ctx.createBufferSource()
    source.buffer = sound
    source.connect(gain)
  }

  // Browsers only allow sound after a user gesture
  await ctx.resume().catch(() => {})
  if (unmounted) return
  if (!sound || ctx.state === 'running' || Number.isFinite(frozenAt)) begin()
  else needsClick.value = true
})

onBeforeUnmount(() => {
  unmounted = true
  running = false
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onKey)
  ctx?.close() // also stops the sound
  intro?.dispose()
})
</script>

<template>
  <div class="intro" @click="onClick">
    <div ref="stage" class="stage" />
    <div class="flash" :style="{ opacity: flash }" />
    <div class="blackout" :style="{ opacity: blackout }" />
    <div class="texts" :style="{ opacity: texts }">
      <p class="company">
        Westwood Studios is an Electronic Arts<sup>™</sup> Company
      </p>
      <p class="disclaimer">
        Command &amp; Conquer, Tiberian Sun und Westwood sind Marken von Electronic Arts. Alle Rechte liegen bei
        Westwood Studios / Electronic Arts. Tiberian Fallout ist ein inoffizielles, nicht-kommerzielles Fanprojekt
        und steht in keiner Verbindung zu Electronic Arts.
      </p>
    </div>
    <p v-if="needsClick" class="hint">
      Klicken zum Starten
    </p>
  </div>
</template>

<style scoped>
.intro {
  position: fixed;
  inset: 0;
  background: #000;
  cursor: pointer;
  overflow: hidden;
}
.stage,
.flash,
.blackout {
  position: absolute;
  inset: 0;
}
.stage :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
}
.flash {
  background: radial-gradient(ellipse, #fff 35%, #c8d6ff 75%, #8fa6f0 100%);
  pointer-events: none;
}
.blackout {
  background: #000;
  pointer-events: none;
}
.texts {
  position: absolute;
  right: 2.5vw;
  bottom: 2.5vh;
  left: 2.5vw;
  text-align: right;
  pointer-events: none;
  font-family: Arial, Helvetica, sans-serif;
}
.company {
  margin: 0;
  color: #1f9a2a;
  font-size: clamp(12px, 1.6vw, 26px);
  font-weight: 700;
}
.company sup {
  font-size: 0.5em;
}
.hint {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  margin: 0;
  text-align: center;
  color: #9fb8ff;
  font: 600 clamp(14px, 1.4vw, 22px) Arial, Helvetica, sans-serif;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.disclaimer {
  max-width: 60em;
  margin: 0.6em 0 0 auto;
  color: rgba(120, 190, 120, 0.75);
  font-size: clamp(10px, 0.85vw, 14px);
  line-height: 1.4;
}
</style>
