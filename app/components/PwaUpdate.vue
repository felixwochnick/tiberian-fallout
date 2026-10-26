<script setup lang="ts">
/**
 * A new version of the game was loaded by the service worker: it is used after a
 * reload, which the player starts here (shown on the start page only, never mid-game).
 */
const { $pwa } = useNuxtApp()
const needRefresh = computed(() => !!$pwa?.needRefresh)
</script>

<template>
  <div v-if="needRefresh" class="update" role="status">
    <span>Eine neue Version des Spiels ist verfügbar.</span>
    <button class="btn btn-small" @click="$pwa?.updateServiceWorker()">
      Neu laden
    </button>
  </div>
</template>

<style scoped>
.update {
  position: fixed;
  left: 50%;
  bottom: 16px;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 14px;
  max-width: calc(100vw - 32px);
  padding: 10px 14px;
  transform: translateX(-50%);
  border: 1px solid var(--tib);
  border-radius: 6px;
  background: var(--panel);
  box-shadow: 0 0 24px rgba(61, 255, 110, 0.15);
}
</style>
