<script setup lang="ts">
useHead({ title: 'Tiberian Fallout – Hauptmenü' })

/**
 * The Westwood logo plays once per visit, not again when coming back from a game;
 * dev links that freeze the startup animation (`?t=`) go straight to it.
 */
const logoSeen = useState('westwood-logo-seen', () => false)
const showIntro = ref(!logoSeen.value && !(import.meta.dev && useRoute().query.t !== undefined))
/** Before the Westwood logo: what the game is made with, and the project link */
const showSplash = ref(showIntro.value)

function introDone() {
  logoSeen.value = true
  showIntro.value = false
}
</script>

<template>
  <DeviceGate>
    <SplashScreen v-if="showSplash" @done="showSplash = false" />
    <WestwoodIntro v-else-if="showIntro" @done="introDone" />
    <StartupMenu v-else />
    <CaptureOverlay />
  </DeviceGate>
</template>
