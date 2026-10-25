<script setup lang="ts">
/**
 * Mission hints like in Tiberian Sun: a line of text right under the top bar, light
 * on the map with a dark outline, that fades after a few seconds.
 */
defineProps<{ hints: Hint[] }>()
</script>

<template>
  <TransitionGroup tag="div" name="hint" class="hints">
    <p v-for="hint in hints" :key="hint.id" class="hint">
      {{ hint.text }}
    </p>
  </TransitionGroup>
</template>

<style scoped>
.hints {
  position: fixed;
  top: calc(var(--hud-top, 0px) + 2px);
  left: 6px;
  right: calc(var(--hud-right, 0px) + 6px);
  z-index: 9;
  display: flex;
  flex-direction: column;
  gap: 2px;
  pointer-events: none;
}
.hint {
  margin: 0;
  font: 400 clamp(12px, 1.25vh, 18px) / 1.25 Arial, Helvetica, sans-serif;
  letter-spacing: 0.14em;
  color: #e9e3b8;
  text-shadow:
    1px 0 0 #000, -1px 0 0 #000, 0 1px 0 #000, 0 -1px 0 #000,
    1px 1px 1px rgba(0, 0, 0, 0.9);
}
.hint-enter-from,
.hint-leave-to {
  opacity: 0;
}
.hint-enter-active,
.hint-leave-active {
  transition: opacity 0.6s;
}
</style>
