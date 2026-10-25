<script setup lang="ts">
import { previewModel } from '~/lib/game/model-preview'

/** A 3D model turning slowly, seen from the game's angle. */
const props = defineProps<{ url: string }>()
const canvas = ref<HTMLCanvasElement>()
const failed = ref(false)
let stop: (() => void) | undefined

onMounted(async () => {
  try {
    stop = await previewModel(canvas.value!, props.url)
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
  <canvas v-else ref="canvas" class="preview" />
</template>

<style scoped>
.preview {
  display: block;
  width: 120px;
  height: 120px;
}
.failed {
  color: var(--danger);
}
</style>
