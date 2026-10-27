<script setup lang="ts">
import { findMission, type Mission } from '~/lib/game/campaigns'

/**
 * The briefing before a mission on its own page: the map selection, rebuilt after the
 * original (`?mission=demo-1`). The missions that can be started from it lead on to
 * the battlefield; Esc goes back to the main menu.
 */
const found = findMission(String(useRoute().query.mission ?? ''))
const mission = found?.mission
if (!mission) navigateTo('/menu', { replace: true })
useHead({ title: mission ? `Tiberian Fallout – Briefing: ${mission.title}` : 'Tiberian Fallout – Briefing' })

const music = useMusicPlayer()

function start(chosen: Mission) {
  navigateTo({ path: '/mission', query: { mission: chosen.id } })
}

function leave() {
  useState('westwood-logo-seen').value = true
  useState('menu-assembled').value = true
  navigateTo('/menu')
}

// the map selection has its own music ("Map Selection", MAPS in THEME.INI), over and over
let left = false
onMounted(async () => {
  music.volume.value = volumeOf('music')
  if (!music.tracks.value.length) await music.loadTracks()
  if (left) return
  if (!music.playTheme('MAPS', true) && !music.playing.value) music.playRandom()
})
// the battlefield and the menu bring their own music
onBeforeUnmount(() => {
  left = true
  music.stop()
})
</script>

<template>
  <DeviceGate>
    <MapSelectScreen v-if="mission" :mission="mission" @start="start" @leave="leave()" />
    <CaptureOverlay :prompt="false" />
  </DeviceGate>
</template>
