<script setup lang="ts">
import { previewModel } from '~/lib/game/model-preview'

/** A 3D model turning slowly, seen from the game's angle; `size` in CSS pixels (default 120). */
const props = withDefaults(defineProps<{ url: string, size?: number }>(), { size: 120 })
const canvas = ref<HTMLCanvasElement>()
const failed = ref(false)
let stop: (() => void) | undefined

onMounted(async () => {
  try {
    // sharp on high-density screens
    const pixels = Math.round(props.size * Math.min(window.devicePixelRatio, 2))
    stop = await previewModel(canvas.value!, props.url, undefined, pixels)
  }
  catch (error) {
    console.error('Modell konnte nicht geladen werden', props.url, error)
    failed.value = true
  }
})
onBeforeUnmount(() => stop?.())
</script>

<template>
  <span v-if="failed" class="failed">Fehler</span>
  <canvas v-else ref="canvas" class="preview" :style="{ width: `${size}px`, height: `${size}px` }" />
</template>

<style scoped>
.preview {
  display: block;
}
.failed {
  color: var(--danger);
}
</style>
