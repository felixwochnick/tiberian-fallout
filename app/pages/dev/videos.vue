<script setup lang="ts">
import { availableMovies, type MovieInfo } from '~/lib/game/movies'
import { getAssetStore } from '~/lib/storage/asset-store'

/** Dev only: every video (VQA) of the movie archives, to watch with its sound. */
if (!import.meta.dev) navigateTo('/', { replace: true })
useHead({ title: 'Tiberian Fallout – Videos (Dev)' })

const KINDS: [MovieInfo['kind'], string][] = [
  ['radar', 'Radar'], ['mission', 'Ingame'], ['briefing', 'Briefing'], ['other', 'Sonstige'],
]

const movies = shallowRef<MovieInfo[]>([])
const loading = ref(true)
const playing = ref<string>()

onMounted(async () => {
  movies.value = await getAssetStore().then(availableMovies).catch(() => [])
  loading.value = false
})
</script>

<template>
  <div class="page">
    <header>
      <h1>Videos <small>Dev</small></h1>
      <p class="hint">
        Alle Videos aus den <code>MOVIES*.MIX</code>-Archiven. {{ movies.length }} gefunden.
      </p>
    </header>

    <p v-if="loading">
      Lade Spieldaten …
    </p>
    <p v-else-if="!movies.length" class="hint">
      Keine Videos gefunden – <code>MOVIES01.MIX</code> wird mit der GDI-CD geladen (auf der <NuxtLink to="/">Startseite</NuxtLink> „Fehlende Dateien laden“).
    </p>
    <template v-else>
      <MoviePlayer v-if="playing" :key="playing" class="player" :name="playing" @ended="playing = undefined" />
      <section v-for="[kind, label] in KINDS" :key="kind">
        <template v-if="movies.some(m => m.kind === kind)">
          <h2>{{ label }}</h2>
          <div class="list">
            <button
              v-for="movie in movies.filter(m => m.kind === kind)"
              :key="movie.name"
              class="btn btn-small"
              :class="{ 'btn-secondary': playing !== movie.name }"
              :title="movie.name"
              @click="playing = playing === movie.name ? undefined : movie.name"
            >
              {{ movie.title }}
            </button>
          </div>
        </template>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 16px;
}
h1 {
  margin: 0 0 8px;
  font-family: var(--display);
}
h1 small {
  font-size: 0.5em;
  color: var(--accent);
}
h2 {
  margin: 20px 0 8px;
  font-family: var(--display);
  font-size: 1.1rem;
}
.hint {
  color: var(--muted);
}
.player {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 12px 0;
  background: var(--bg, #000);
}
.list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
