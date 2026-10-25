<script setup lang="ts">
import { readMovie } from '~/lib/game/movies'
import { VqaPlayback } from '~/lib/game/vqa-player'
import { getAssetStore } from '~/lib/storage/asset-store'

/** Plays one of the game's videos (VQA) with its sound; for the dev catalog. */
const props = defineProps<{ name: string }>()
const emit = defineEmits<{ ended: [] }>()
const canvas = ref<HTMLCanvasElement>()
const info = ref('')
let playback: VqaPlayback | undefined
let ctx: AudioContext | undefined

onMounted(async () => {
  const bytes = await getAssetStore().then(store => readMovie(store, props.name))
  if (!bytes || !canvas.value) {
    info.value = 'Video nicht gefunden'
    return
  }
  ctx = new AudioContext()
  playback = new VqaPlayback(bytes, canvas.value, ctx, ctx.destination)
  info.value = `${playback.width} × ${playback.height}, ${playback.duration.toFixed(1)} s`
  playback.done.then(() => emit('ended'))
  playback.start()
})
onBeforeUnmount(() => {
  playback?.stop()
  ctx?.close()
})
</script>

<template>
  <div class="player">
    <canvas ref="canvas" />
    <p>{{ name }} · {{ info }}</p>
  </div>
</template>

<style scoped>
.player canvas {
  display: block;
  max-width: 100%;
  background: #000;
  image-rendering: pixelated;
}
.player p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.85rem;
}
</style>
