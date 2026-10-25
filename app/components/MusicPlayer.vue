<script setup lang="ts">
const { files } = useGameAssets()
const { tracks, current, playing, loading, volume, error, loadTracks, play, stop, next } = useMusicPlayer()

const scanning = ref(true)
const currentTrack = computed(() => tracks.value.find(t => t.id === current.value))

watch(files, async () => {
  scanning.value = true
  stop()
  await loadTracks()
  scanning.value = false
}, { immediate: true })

onBeforeUnmount(stop)
</script>

<template>
  <div class="player">
    <div class="now">
      <div>
        <div class="label">
          {{ playing ? 'Läuft gerade' : 'Bereit' }}
        </div>
        <div class="title">
          {{ loading ? 'Dekodiere …' : currentTrack?.title ?? 'Kein Track gewählt' }}
        </div>
      </div>
      <div class="controls">
        <button class="btn btn-secondary" :disabled="!playing" @click="stop()">
          Stopp
        </button>
        <button class="btn" :disabled="!tracks.length" @click="currentTrack ? next() : play(tracks[0]!)">
          {{ currentTrack ? 'Weiter' : 'Abspielen' }}
        </button>
        <label class="volume">
          <span>Lautstärke</span>
          <input v-model.number="volume" type="range" min="0" max="1" step="0.01">
        </label>
      </div>
    </div>

    <p v-if="error" class="error" role="alert">
      {{ error }}
    </p>
    <p v-if="scanning" class="muted">
      Durchsuche SCORES.MIX …
    </p>
    <p v-else-if="!tracks.length" class="muted">
      In SCORES.MIX wurden keine Musikstücke gefunden.
    </p>

    <ol v-else class="tracks">
      <li v-for="track in tracks" :key="track.id">
        <button class="track" :class="{ active: track.id === current }" @click="play(track)">
          <span class="track-title">{{ track.title }}</span>
          <span class="track-meta">{{ track.filename ?? 'ohne Dateinamen' }} · {{ (track.entry.length / 1024 / 1024).toFixed(1) }} MB</span>
        </button>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.now {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}
.label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--muted);
}
.title {
  font-family: var(--display);
  font-size: 1.3rem;
  color: var(--tib);
}
.controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.volume {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 0.85rem;
  color: var(--muted);
}
.volume input {
  accent-color: var(--tib);
}
.tracks {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
}
.track {
  width: 100%;
  text-align: left;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--line);
  border-radius: 4px;
  color: var(--text);
  padding: 10px 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font: inherit;
}
.track:hover {
  border-color: var(--tib-dim);
}
.track.active {
  border-color: var(--tib);
  background: rgba(61, 255, 110, 0.08);
}
.track-title {
  font-weight: 600;
}
.track-meta {
  font-size: 0.8rem;
  color: var(--muted);
}
.muted {
  color: var(--muted);
}
.error {
  color: var(--danger);
}
</style>
