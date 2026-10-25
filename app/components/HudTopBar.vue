<script setup lang="ts">
import { hudScale, railImage, TAB, tabImage } from '~/lib/game/hud'

/**
 * Top bar of the in-game HUD like in Tiberian Sun: the "Optionen" tab on the left
 * (opens the Esc menu), the credits tab on the right above the sidebar and the rail
 * between them. Drawn as vector graphics (see hud.ts), sharp at any resolution.
 */
const props = defineProps<{
  credits: number
  /** Mission countdown in seconds, shown in a tab next to the credits */
  timer?: number
}>()
const time = computed(() => props.timer === undefined ? '' : formatTime(Math.ceil(props.timer)).padStart(5, '0'))
const emit = defineEmits<{ options: [] }>()

const scale = ref(1)
const onResize = () => {
  scale.value = hudScale()
}

const style = computed(() => ({
  '--px': `${scale.value}px`,
  '--tab-w': `${TAB.width * scale.value}px`,
  '--bar-h': `${TAB.height * scale.value}px`,
  '--tab': tabImage(),
  '--tab-pressed': tabImage(true),
  '--rail': railImage(),
}))

onMounted(() => {
  onResize()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
</script>

<template>
  <header class="top-bar" :style="style">
    <button class="tab options" @click="emit('options')">
      Optionen
    </button>
    <div class="rail" />
    <div v-if="timer !== undefined" class="tab timer" aria-label="Zeit">
      Zeit:{{ time }}
    </div>
    <div class="tab credits" aria-label="Guthaben">
      {{ credits }}
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  height: var(--bar-h);
  user-select: none;
}
.tab {
  flex: 0 0 var(--tab-w);
  display: grid;
  place-items: center;
  padding: 0 0 calc(var(--px) * 0.6);
  border: 0;
  background: var(--tab) 0 0 / 100% 100%;
  /* bold, light and widely spaced, outlined so it reads on the busy stone */
  font: 700 calc(var(--px) * 11) Arial, Helvetica, sans-serif;
  letter-spacing: 0.18em;
  color: #fbeeb4;
  text-shadow:
    calc(var(--px) * 0.6) 0 0 #1a1208, calc(var(--px) * -0.6) 0 0 #1a1208,
    0 calc(var(--px) * 0.6) 0 #1a1208, 0 calc(var(--px) * -0.6) 0 #1a1208,
    calc(var(--px) * 0.9) calc(var(--px) * 1.1) calc(var(--px) * 1.2) rgba(0, 0, 0, 0.8);
  line-height: 1;
}
.options {
  cursor: pointer;
}
.options[data-hover] {
  color: #ffffff;
}
.options[data-active] {
  background-image: var(--tab-pressed);
  padding-top: calc(var(--px) * 1.2);
}
.credits,
.timer {
  letter-spacing: 0.45em;
  padding-left: 0.45em;
}
.timer {
  letter-spacing: 0.25em;
}
/* the rail tiles every tab width, its noise is seamless */
.rail {
  flex: 1;
  background: var(--rail) 0 0 / var(--tab-w) 100% repeat-x;
}
</style>
