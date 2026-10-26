<script setup lang="ts">
import type { Battlefield } from '~/lib/game/battlefield'
import type { Field } from '~/lib/game/field'
import type { Side } from '~/lib/game/models'
import { loadBuildRules } from '~/lib/game/cameos'
import { hudScale, TAB } from '~/lib/game/hud'
import { getAssetStore } from '~/lib/storage/asset-store'

/**
 * A running game, whatever its mode: battlefield, HUD, radar, soundtrack and the Esc
 * menu. The skirmish and the campaign mission each have their own page around it and
 * set up the map on `start`; the game state comes from the page (createSkirmish).
 */
const props = defineProps<{
  /** Money at the start (and again after "Neu starten") */
  startCredits: number
  /** Highest tech level that can be built */
  techLevel: number
  /** The radar works without a radar building */
  radarAlways?: boolean
  /** House colour of the human player */
  colour?: number
  /** The human player's side (the look of their units) */
  side?: Side
  /** A screen of the page (briefing, result) is in front: the game waits */
  blocked?: boolean
  /** A theme of its own (THEME.INI id, e.g. 'MAPS') that loops instead of the random soundtrack */
  theme?: string
}>()
const emit = defineEmits<{ start: [field: Field], tick: [seconds: number], restart: [] }>()

const skirmish = useSkirmish()!
const paused = ref(false)
const halted = computed(() => paused.value || props.blocked || !skirmish.control)

/** The transmission in the radar has ended */
function endRadarMovie() {
  const movie = skirmish.radarMovie
  skirmish.radarMovie = undefined
  movie?.done()
}

/** "Neu starten" builds the battlefield anew */
const round = ref(0)
const escMenu = ref<{ open: () => void }>()

/** Starts a fresh round: a new battlefield, a fresh base and the starting money again */
function restart() {
  round.value++
  skirmish.credits.value = props.startCredits
  skirmish.buildings.splice(0)
  skirmish.offline.splice(0)
  skirmish.mode = undefined
  skirmish.production.structure = undefined
  skirmish.production.units.splice(0)
  skirmish.placing = undefined
  skirmish.arrivals.splice(0)
  skirmish.hints = []
  skirmish.timer = undefined
  skirmish.radarMovie = undefined
  radar.value = false
  startMusic()
}
defineExpose({ restart })

// Soundtrack: every round starts with a random track, then goes on at random (unless a theme is set)
const settings = useSettings()
const music = useMusicPlayer()

/** The map starts below the HUD's top bar */
const scale = ref(1)
const onResize = () => {
  scale.value = hudScale()
}
const hudStyle = computed(() => ({
  '--hud-top': `${TAB.height * scale.value}px`,
  // the sidebar is as wide as a tab
  '--hud-right': `${TAB.width * scale.value}px`,
}))

/** Handed over by the battlefield, for the radar */
const battlefield = shallowRef<Battlefield>()

getAssetStore().then(loadBuildRules).then((rules) => {
  skirmish.rules = rules
}).catch(() => {})
const power = computed(() => basePower(skirmish))
const owned = computed(() => skirmish.buildings)
/** Whole credits for the top bar, counting along like in the original */
const credits = computed(() => Math.floor(skirmish.credits.value))

/**
 * The credits counter ticks while money comes in or goes out, like in the original:
 * up and down have their own click (SOUNDS.MIX; CashTickUp/CashTickDown in OpenRA's
 * Tiberian Sun), at most one every CASH_TICK_SECONDS while the money keeps changing.
 */
const CASH_TICK = { up: ['CREDUP1'], down: ['CREDDWN1'] }
const CASH_TICK_SECONDS = 0.12
const cashSounds = useUiSounds()
let lastCashTick = -Infinity
watch(credits, (now, before) => {
  const time = performance.now() / 1000
  if (now === before || time - lastCashTick < CASH_TICK_SECONDS) return
  lastCashTick = time
  cashSounds.effect(now > before ? CASH_TICK.up : CASH_TICK.down)
})

/**
 * The radar works with a radar building (GDI or Nod) on enough power, or always if
 * the match is set up that way. R opens and closes it, but not while a transmission
 * is still running; without power it shuts down by itself.
 */
const RADAR_BUILDINGS = ['GARADR', 'NARADR']
const radar = ref(false)
const radarBusy = ref(false)
const radarAvailable = computed(() => props.radarAlways
  || (onlineBuildings(skirmish).some(id => RADAR_BUILDINGS.includes(id)) && power.value.output >= power.value.drain))
watch(radarAvailable, (available) => {
  if (!available) radar.value = false
})
const keys = useKeys()
function onKey(event: KeyboardEvent) {
  if (!keys.matches(event, 'radar') || halted.value || radarBusy.value) return
  if (radar.value || radarAvailable.value) radar.value = !radar.value
}

async function startMusic() {
  if (!music.tracks.value.length) await music.loadTracks()
  if (!props.theme || !music.playTheme(props.theme, true)) music.playRandom()
}

watch(() => settings.music, (value) => {
  music.volume.value = value / 100
}, { immediate: true })

// only once the game can be played (see DeviceGate)
const { supported } = useDeviceSupport()
onMounted(() => {
  onResize()
  window.addEventListener('resize', onResize)
  window.addEventListener('keydown', onKey)
  music.shuffle.value = true
  if (supported.value) startMusic()
})
watch(supported, (ok) => {
  // the briefing's theme may still be the current track, but it has stopped
  if (ok && !music.playing.value) startMusic()
})
// the briefing has its own theme, the battle goes back to the random soundtrack
watch(() => props.theme, () => {
  if (supported.value) startMusic()
})

// the Esc menu pauses the whole game, its sounds too (the music plays on, like in the original)
watch(paused, on => cashSounds.hold(on))

onBeforeUnmount(() => {
  cashSounds.hold(false)
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onKey)
  music.stop()
  music.shuffle.value = false
})
</script>

<template>
  <DeviceGate>
    <div :style="hudStyle">
      <BattlefieldView
        :key="round"
        :paused="halted"
        :frozen="paused"
        :cursor-hidden="!skirmish.control && !blocked && !paused"
        :colour="colour"
        :side="side"
        @ready="battlefield = $event"
        @start="emit('start', $event)"
        @tick="emit('tick', $event)"
      />
      <HudTopBar :credits="credits" :timer="skirmish.timer?.remaining" @options="escMenu?.open()" />
      <HudHints :hints="skirmish.hints" />
      <HudSidebar
        :radar="radar"
        :battlefield="battlefield"
        :power="power"
        :owned="owned"
        :tech-level="techLevel"
        :movie="skirmish.radarMovie?.bytes"
        @radar-busy="radarBusy = $event"
        @movie-end="endRadarMovie()"
      />
    </div>
    <!-- before battle control is established: no cursor, nothing can be clicked -->
    <div v-if="!skirmish.control && !blocked" class="no-control" @contextmenu.prevent />
    <EscMenu ref="escMenu" v-model:paused="paused" @restart="emit('restart')" />
    <!-- the page's own screens (briefing, result) -->
    <slot />
    <!-- the Esc menu offers "Weiter" when full screen was lost -->
    <CaptureOverlay :prompt="false" />
  </DeviceGate>
</template>

<style scoped>
.no-control {
  position: fixed;
  inset: 0;
  z-index: 50;
  cursor: none;
}
</style>
