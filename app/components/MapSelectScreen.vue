<script setup lang="ts">
import { findMission, type Mission } from '~/lib/game/campaigns'
import { MapScreenScene, SCREEN_HEIGHT, SCREEN_WIDTH } from '~/lib/menu/map-screen'
import { pointer } from '~/lib/input/mouse-capture'

/**
 * The map selection before a mission, rebuilt after the original: the map of the region
 * above (zooming down from the globe, then the territories of GDI and Nod and the
 * targets), the metal plate with the brass rail below, the turning GDI coin and globe,
 * and the briefing typed out next to the coin. Clicking a target starts its mission;
 * a click elsewhere (or Space) skips ahead, Enter starts the only target, Esc goes back
 * to the main menu.
 */
const props = defineProps<{ mission: Mission }>()
const emit = defineEmits<{ start: [mission: Mission], leave: [] }>()

const sounds = useUiSounds()
const stage = ref<HTMLDivElement>()
const textBox = ref<HTMLDivElement>()
const ready = ref(false)
let scene: MapScreenScene | undefined
let observer: ResizeObserver | undefined
let frame = 0

/** Where the text is typed (x, y, width, height in screen units): between coin and globe, six lines, in the middle of the plate */
const TEXT_RECT = [122, 262, 390, 117] as const
const CHARS_PER_SECOND = 32

/** One flowing text like in the original, the objectives after it */
const briefing = computed(() => [
  props.mission.briefing.join(' '),
  ...props.mission.objectives.map(o => `▸ ${o}`),
].join('\n'))
/** What is being typed: the briefing, or the target under the cursor */
const text = ref('')
const typed = ref(0)
let typeClock = 0
const hovered = ref<number>()
let leaving = false
/** Which sounds of the intro have played: the territories fading up, the crosshairs flying in */
const played = { overlay: false, target: false }

/** The mission a target leads to */
function missionOf(index: number) {
  const id = scene?.world?.target(index).mission
  return (id && findMission(id)?.mission) || props.mission
}

onMounted(async () => {
  scene = await MapScreenScene.create(stage.value!, props.mission.map)
  observer = new ResizeObserver(() => scene?.resize())
  observer.observe(stage.value!)
  ready.value = true
  window.addEventListener('keydown', onKey, { capture: true })
  frame = requestAnimationFrame(tick)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  observer?.disconnect()
  scene?.dispose()
  window.removeEventListener('keydown', onKey, { capture: true })
})

function tick(now: number) {
  frame = requestAnimationFrame(tick)
  const world = scene?.world
  // the briefing begins once the zoom has reached the region
  // the original's sounds: a sweep as the territories come up, then the crosshairs fly in
  if (world?.overlayStarted && !played.overlay) {
    played.overlay = true
    if (!world.settled) sounds.play('mapOverlay', 0.6)
  }
  if (world?.settled && !played.target) {
    played.target = true
    sounds.play('mapTarget', 0.75)
  }
  if (!text.value && (!world || world.overlayStarted)) {
    text.value = briefing.value
    typeClock = now
  }
  // typing
  if (typed.value < text.value.length) {
    const chars = Math.floor((now - typeClock) / 1000 * CHARS_PER_SECOND)
    if (chars > 0) {
      typeClock += chars / CHARS_PER_SECOND * 1000
      typed.value = Math.min(text.value.length, typed.value + chars)
      nextTick(() => {
        if (textBox.value) textBox.value.scrollTop = textBox.value.scrollHeight
      })
    }
  }
  else {
    typeClock = now
  }
  // the target under the cursor: highlighted, its name typed instead of the briefing
  const target = leaving ? undefined : targetAtPointer()
  if (target !== hovered.value) {
    hovered.value = target
    if (world) world.hovered = target
    if (target !== undefined && world) {
      sounds.play('mapEnter', 0.4)
      text.value = `Einsatz: ${world.target(target).name} – ${missionOf(target).title}`
      typed.value = 0
    }
    else if (text.value) {
      text.value = briefing.value
      typed.value = text.value.length
    }
  }
}

function targetAtPointer() {
  const at = pointer()
  const rect = stage.value?.getBoundingClientRect()
  if (!at.inside || !rect || !scene?.world) return undefined
  return scene.world.targetAt((at.x - rect.left) / rect.width, (at.y - rect.top) / rect.height)
}

/** Skips the zoom and the typing */
function skip() {
  scene?.world?.skip()
  if (!text.value) text.value = briefing.value
  typed.value = text.value.length
}

function start(mission: Mission) {
  if (leaving) return
  leaving = true
  sounds.play(scene?.world ? 'mapClick' : 'click', 0.7)
  emit('start', mission)
}

function onClick(event: MouseEvent) {
  if (event.button !== 0) return
  const target = scene?.world?.targetAt(...stagePoint(event))
  if (target !== undefined) start(missionOf(target))
  else if (!scene?.world) start(props.mission) // no map: a click goes on
  else skip()
}

function stagePoint(event: MouseEvent): [number, number] {
  const rect = stage.value!.getBoundingClientRect()
  return [(event.clientX - rect.left) / rect.width, (event.clientY - rect.top) / rect.height]
}

function onKey(event: KeyboardEvent) {
  if (event.code !== 'Escape' && event.code !== 'Enter' && event.code !== 'Space') return
  event.preventDefault()
  event.stopImmediatePropagation()
  if (event.code === 'Escape') return emit('leave')
  const world = scene?.world
  const settled = !world || world.settled
  if (event.code === 'Enter' && settled && (!world || world.targetCount === 1)) start(world ? missionOf(0) : props.mission)
  else skip()
}

const textStyle = {
  left: `${TEXT_RECT[0] / SCREEN_WIDTH * 100}%`,
  top: `${TEXT_RECT[1] / SCREEN_HEIGHT * 100}%`,
  width: `${TEXT_RECT[2] / SCREEN_WIDTH * 100}%`,
  height: `${TEXT_RECT[3] / SCREEN_HEIGHT * 100}%`,
}
</script>

<template>
  <div class="map-select" @click="onClick">
    <div ref="stage" class="stage" :class="{ ready }">
      <div ref="textBox" class="text" :style="textStyle">
        {{ text.slice(0, typed) }}<span v-if="text" class="caret">▮</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.map-select {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: #000;
}
.stage {
  position: absolute;
  left: 50%;
  top: 50%;
  width: min(100vw, 160vh);
  aspect-ratio: 16 / 10;
  transform: translate(-50%, -50%);
  container-type: size;
  opacity: 0;
  transition: opacity 0.3s;
}
.stage.ready {
  opacity: 1;
}
.stage :deep(canvas) {
  position: absolute;
  inset: 0;
  display: block;
}
.text {
  position: absolute;
  z-index: 1;
  overflow: hidden;
  white-space: pre-line;
  /* exactly six lines fit (the box is 29.25 % of the height) */
  font: 600 3.2cqh / 4.875cqh var(--body);
  color: #3cdc5a;
  text-shadow: 0 0 0.4em rgba(60, 220, 90, 0.35);
  pointer-events: none;
}
.caret {
  animation: blink 0.8s steps(2) infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}
</style>
