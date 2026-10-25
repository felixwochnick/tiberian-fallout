<script setup lang="ts">
import type { GameDisc } from '#shared/game-discs'

const { discs, files, importing, progress, downloadError: error, isDiscLoaded, downloadDiscs, cancel } = useGameAssets()

/** Disc was imported by an older version that did not extract everything yet */
const isPartial = (disc: GameDisc) => !isDiscLoaded(disc) && files.value.some(f => f.name === disc.marker)

const selected = ref<string[]>(discs.filter(d => !d.optional).map(d => d.id))

const pending = computed(() => discs.filter(d => selected.value.includes(d.id) && !isDiscLoaded(d)))
const downloadSize = computed(() => pending.value.reduce((sum, d) => sum + d.size, 0))
const downloading = computed(() => importing.value && !!progress.value?.disc)
const percent = computed(() =>
  progress.value?.total ? Math.floor((progress.value.done / progress.value.total) * 100) : 0,
)

function formatMB(bytes: number) {
  return `${Math.round(bytes / 1024 / 1024)} MB`
}
</script>

<template>
  <div>
    <ul class="discs">
      <li v-for="disc in discs" :key="disc.id">
        <label class="disc" :class="{ done: isDiscLoaded(disc) }">
          <input
            v-model="selected"
            type="checkbox"
            :value="disc.id"
            :disabled="!disc.optional || isDiscLoaded(disc) || importing"
          >
          <span class="disc-text">
            <strong>{{ disc.title }}</strong>
            <span>{{ disc.description }}</span>
          </span>
          <span class="disc-size">
            {{ isDiscLoaded(disc) ? 'geladen ✓' : isPartial(disc) ? 'Update verfügbar' : formatMB(disc.size) }}
          </span>
        </label>
      </li>
    </ul>

    <div v-if="downloading && progress" class="progress">
      <div class="progress-head">
        <span>{{ progress.disc }} · {{ progress.file }}</span>
        <span>{{ percent }} %</span>
      </div>
      <div class="bar" role="progressbar" :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100">
        <div class="bar-fill" :style="{ width: `${percent}%` }" />
      </div>
      <div class="progress-foot">
        <span class="hint">{{ formatMB(progress.done) }} / {{ formatMB(progress.total) }}</span>
        <button class="btn btn-secondary btn-small" @click="cancel()">
          Abbrechen
        </button>
      </div>
    </div>

    <div v-else class="start">
      <button class="btn" :disabled="importing || !pending.length" @click="downloadDiscs(pending)">
        {{ !pending.length
          ? 'Ausgewählte Spieldaten geladen'
          : pending.every(isPartial) ? 'Fehlende Dateien laden' : `Spieldaten laden (${formatMB(downloadSize)})` }}
      </button>
    </div>

    <p v-if="error && !importing" class="error" role="alert">
      {{ error }}
    </p>
    <p class="hint">
      Die Original-CDs werden von <a href="https://cnc-comm.com/tiberian-sun" target="_blank" rel="noopener">cnc-comm.com</a>
      geladen und noch während des Downloads entpackt. Gespeichert werden nur die Spielarchive
      (ohne Videosequenzen), ungefähr ein Viertel der Downloadgröße. Eine Installation ist nicht nötig.
    </p>
  </div>
</template>

<style scoped>
.discs {
  list-style: none;
  margin: 0 0 18px;
  padding: 0;
  display: grid;
  gap: 8px;
}
.disc {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 4px;
  cursor: pointer;
}
.disc.done {
  border-color: var(--tib-dim);
}
.disc input {
  accent-color: var(--tib);
  width: 18px;
  height: 18px;
}
.disc-text {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}
.disc-text span {
  font-size: 0.9rem;
  color: var(--muted);
}
.disc-size {
  font-size: 0.9rem;
  color: var(--muted);
  white-space: nowrap;
}
.disc.done .disc-size {
  color: var(--tib);
}
.progress-head,
.progress-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.progress-head {
  margin-bottom: 8px;
  font-weight: 600;
}
.progress-foot {
  margin-top: 8px;
}
.bar {
  height: 10px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 5px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--tib-dim), var(--tib));
  transition: width 0.2s;
}
.hint {
  font-size: 0.9rem;
  color: var(--muted);
}
.progress-foot .hint {
  margin: 0;
}
.error {
  color: var(--danger);
}
</style>
