<script setup lang="ts">
import { attach, capture, detach, mouseCapture, needsResume, stayWindowed } from '~/lib/input/mouse-capture'

/**
 * Game pages: draws the game cursor, captures the mouse on the first click (if the
 * start page has not done so already) and offers to resume after Esc or Alt+Tab.
 * Pages with their own pause menu turn the prompt off and resume from there.
 */
const props = withDefaults(defineProps<{ prompt?: boolean }>(), { prompt: true })
const settings = useSettings()

/** First click on the page (e.g. when it was opened directly) starts the capture. */
function onFirstClick(event: PointerEvent) {
  if (!mouseCapture.wanted && event.isTrusted) capture(event, { lock: settings.mouseCapture })
}

onMounted(() => {
  attach()
  window.addEventListener('pointerdown', onFirstClick, { capture: true, once: true })
})

onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', onFirstClick, { capture: true })
  detach()
})
</script>

<template>
  <div v-if="props.prompt && needsResume()" class="overlay">
    <div class="box">
      <p>Vollbild und Maus wurden freigegeben.</p>
      <button class="resume" @click.stop="capture($event, { lock: settings.mouseCapture })">
        Weiter &amp; Vollbild
      </button>
      <button class="windowed" @click.stop="stayWindowed()">
        Im Fenster weiterspielen
      </button>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.6);
}
.box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 32px;
  background: rgba(10, 30, 20, 0.92);
  border: 1px solid var(--tib, #3dff6e);
  color: #cfe;
  font-family: var(--display, sans-serif);
  text-align: center;
}
.box p {
  margin: 0;
}
.resume {
  padding: 10px 28px;
  border: 1px solid var(--tib, #3dff6e);
  background: var(--tib, #3dff6e);
  color: #04110a;
  font: inherit;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.resume[data-hover] {
  filter: brightness(1.12);
}
.windowed {
  border: 0;
  background: none;
  color: #8ab;
  font: inherit;
  font-size: 0.85em;
  text-decoration: underline;
}
.windowed[data-hover] {
  color: #cfe;
}
</style>
