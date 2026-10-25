<script setup lang="ts">
import type { Battlefield } from '~/lib/game/battlefield'
import { createSkirmish } from '~/composables/useSkirmish'
import { loadBuildRules } from '~/lib/game/cameos'
import { findMission } from '~/lib/game/campaigns'
import { hudScale, TAB } from '~/lib/game/hud'
import { getAssetStore } from '~/lib/storage/asset-store'

/** `?mission=demo-1` plays a campaign mission, otherwise it is a skirmish */
const found = findMission(String(useRoute().query.mission ?? ''))
const mission = found?.mission
// skirmishes (no mission) only while developing: otherwise back to the main menu
if (!mission && !import.meta.dev) navigateTo('/menu', { replace: true })
useHead({ title: mission ? `Tiberian Fallout – ${mission.title}` : 'Tiberian Fallout – Gefecht' })

const paused = ref(false)
/** A mission with the map selection has its briefing on its own page (/briefing) */
const briefingHere = !!mission && !mission.map
/** Mission: briefing first (unless it had its own page), the result at the end; the game waits meanwhile */
const screen = ref<'briefing' | 'won' | 'lost' | undefined>(briefingHere ? 'briefing' : undefined)
const halted = computed(() => paused.value || !!screen.value || !skirmish.control)
/**
 * "Battle control online": until EVA has said it, the game waits and the player has
 * no cursor and cannot scroll or click anything (Esc still opens the menu).
 */
const sounds = useUiSounds()
let controlRound = 0
async function establishControl() {
  const mine = ++controlRound
  skirmish.control = false
  await sounds.speakNow('evaStartGame')
  if (mine === controlRound) skirmish.control = true
}

/** A mission's reinforcements are flying in (after the briefing, before battle control) */
const landing = ref(false)
/** The mission begins (on the fresh battlefield): first the reinforcements, then battle control */
function beginMission() {
  skirmish.control = false
  landing.value = false
  nextTick(() => {
    if (mission?.reinforcements?.length) landing.value = true
    else establishControl()
  })
}
async function landed() {
  await establishControl()
  landing.value = false
}

/** The transmission in the radar has ended */
function endRadarMovie() {
  const movie = skirmish.radarMovie
  skirmish.radarMovie = undefined
  movie?.done()
}

function onResult(result: 'won' | 'lost') {
  screen.value = result
}
function retry() {
  round.value++
  if (briefingHere) {
    screen.value = 'briefing'
  }
  else {
    screen.value = undefined
    beginMission()
  }
}
function leave() {
  useState('westwood-logo-seen').value = true
  useState('menu-assembled').value = true
  navigateTo('/menu')
}
/** "Neu starten" builds the battlefield anew */
const round = ref(0)
const escMenu = ref<{ open: () => void }>()

// Soundtrack: every round starts with a random track, then goes on at random
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

/** Money, buildings and production of this game (shared with battlefield and sidebar) */
const startCredits = mission?.credits ?? settings.credits
const skirmish = createSkirmish(startCredits)
getAssetStore().then(loadBuildRules).then((rules) => {
  skirmish.rules = rules
}).catch(() => {})
const power = computed(() => basePower(skirmish))
const owned = computed(() => skirmish.buildings)
/** Whole credits for the top bar, counting along like in the original */
const credits = computed(() => Math.floor(skirmish.credits.value))
// "Neu starten": a fresh base and the starting money again
watch(round, () => {
  skirmish.credits.value = startCredits
  skirmish.buildings.splice(0)
  skirmish.production.structure = undefined
  skirmish.production.units.splice(0)
  skirmish.placing = undefined
  skirmish.arrivals.splice(0)
  skirmish.hints = []
  skirmish.timer = undefined
  skirmish.radarMovie = undefined
})

/** Match settings: skirmish dialog, or the mission's own */
const techLevel = mission ? (mission.techLevel ?? 10) : settings.techLevel
const radarAlways = mission ? !!mission.radar : settings.radarAlways

/**
 * The radar works with a radar building (GDI or Nod) on enough power, or always if
 * the match is set up that way. R opens and closes it, but not while a transmission
 * is still running; without power it shuts down by itself.
 */
const RADAR_BUILDINGS = ['GARADR', 'NARADR']
const radar = ref(false)
const radarBusy = ref(false)
const radarAvailable = computed(() => radarAlways
  || (skirmish.buildings.some(id => RADAR_BUILDINGS.includes(id)) && power.value.output >= power.value.drain))
watch(radarAvailable, (available) => {
  if (!available) radar.value = false
})
const keys = useKeys()
function onKey(event: KeyboardEvent) {
  if (!keys.matches(event, 'radar') || halted.value || radarBusy.value) return
  if (radar.value || radarAvailable.value) radar.value = !radar.value
}
watch(round, () => {
  radar.value = false
})

async function startMusic() {
  if (!music.tracks.value.length) await music.loadTracks()
  music.playRandom()
}

watch(() => settings.music, (value) => {
  music.volume.value = value / 100
}, { immediate: true })
watch(round, startMusic)
// a skirmish starts at once, a mission after its briefing
watch(round, () => {
  if (!mission) establishControl()
})
watch(screen, (now, before) => {
  if (before === 'briefing' && !now) beginMission()
  if (now === 'briefing') {
    skirmish.control = false
    landing.value = false
  }
})

// only once the game can be played (see DeviceGate)
const { supported } = useDeviceSupport()
onMounted(() => {
  onResize()
  window.addEventListener('resize', onResize)
  window.addEventListener('keydown', onKey)
  music.shuffle.value = true
  if (supported.value) startMusic()
  if (!mission) establishControl()
  else if (!briefingHere) beginMission()
})
watch(supported, (ok) => {
  if (ok && !music.current.value) startMusic()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onKey)
  music.stop()
  music.shuffle.value = false
})
</script>

<template>
  <DeviceGate>
    <div :style="hudStyle">
      <BattlefieldView :key="round" :paused="halted" :cursor-hidden="!skirmish.control && !screen" :mission="mission" :landing="landing" @landed="landed()" @ready="battlefield = $event" @result="onResult" />
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
    <div v-if="!skirmish.control && !screen" class="no-control" @contextmenu.prevent />
    <EscMenu ref="escMenu" v-model:paused="paused" @restart="mission ? retry() : round++" />
    <MissionScreen
      v-if="mission && screen"
      :key="`${screen}-${round}`"
      :mission="mission"
      :result="screen === 'briefing' ? undefined : screen"
      @start="screen = undefined"
      @retry="retry()"
      @leave="leave()"
    />
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
