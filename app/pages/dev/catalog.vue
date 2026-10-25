<script setup lang="ts">
import { type Category, type CatalogEntry, loadCatalog } from '~/lib/game/catalog'
import { MODELS } from '~/lib/game/models'
import { getAssetStore } from '~/lib/storage/asset-store'

/**
 * Dev only: every building and unit of RULES.INI with its cameo from the game and,
 * where there is one already, the new 3D model.
 */
if (!import.meta.dev) navigateTo('/', { replace: true })
useHead({ title: 'Tiberian Fallout – Katalog (Dev)' })

const CATEGORIES: [Category | 'all', string][] = [
  ['all', 'Alle'], ['building', 'Gebäude'], ['infantry', 'Infanterie'], ['vehicle', 'Fahrzeuge'], ['aircraft', 'Luft'],
]

const entries = shallowRef<CatalogEntry[]>([])
const loading = ref(true)
const category = ref<Category | 'all'>('all')
const search = ref('')
/** Only what can be built (TechLevel ≥ 0), not civilian and mission-only objects */
const buildableOnly = ref(false)
const withModelOnly = ref(false)

const shown = computed(() => {
  const q = search.value.trim().toLowerCase()
  return entries.value.filter(e =>
    (category.value === 'all' || e.category === category.value)
    && (!buildableOnly.value || e.techLevel >= 0)
    && (!withModelOnly.value || MODELS[e.id])
    && (!q || e.id.toLowerCase().includes(q) || e.name.toLowerCase().includes(q)))
})
const modelCount = computed(() => entries.value.filter(e => MODELS[e.id]).length)

onMounted(async () => {
  entries.value = await getAssetStore().then(loadCatalog).catch(() => [])
  loading.value = false
})
</script>

<template>
  <div class="page">
    <header>
      <h1>Katalog <small>Dev</small></h1>
      <p class="hint">
        Alle Gebäude und Einheiten aus der <code>RULES.INI</code> mit ihrem Bild aus dem Spiel und – wo es schon eins gibt – dem neuen 3D-Modell.
        {{ entries.length }} Einträge, {{ modelCount }} mit 3D-Modell.
      </p>
      <div class="filters">
        <button
          v-for="[id, label] in CATEGORIES"
          :key="id"
          class="btn btn-small"
          :class="{ 'btn-secondary': category !== id }"
          @click="category = id"
        >
          {{ label }}
        </button>
        <input v-model="search" type="search" placeholder="Suchen (ID oder Name)">
        <label><input v-model="buildableOnly" type="checkbox"> nur baubare</label>
        <label><input v-model="withModelOnly" type="checkbox"> nur mit 3D-Modell</label>
      </div>
    </header>

    <p v-if="loading">
      Lade Spieldaten …
    </p>
    <p v-else-if="!entries.length" class="hint">
      Keine Spieldaten gefunden – zuerst auf der <NuxtLink to="/">Startseite</NuxtLink> laden.
    </p>
    <table v-else>
      <thead>
        <tr>
          <th>Bild</th>
          <th>3D-Modell</th>
          <th>ID</th>
          <th>Name</th>
          <th>Art</th>
          <th>Seite</th>
          <th>Kosten</th>
          <th>Leben</th>
          <th>Tech</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="entry in shown" :key="entry.id">
          <td>
            <img v-if="entry.cameo" :src="entry.cameo" :alt="entry.name" class="cameo">
            <span v-else class="none" :title="entry.cameoName">–</span>
          </td>
          <td>
            <ModelPreview v-if="MODELS[entry.id]" :url="MODELS[entry.id]!" />
            <span v-else class="none">–</span>
          </td>
          <td><code>{{ entry.id }}</code></td>
          <td>{{ entry.name }}</td>
          <td>{{ CATEGORIES.find(([id]) => id === entry.category)?.[1] }}</td>
          <td>{{ entry.owner || '–' }}</td>
          <td>{{ entry.cost || '–' }}</td>
          <td>{{ entry.strength || '–' }}</td>
          <td>{{ entry.techLevel }}</td>
        </tr>
      </tbody>
    </table>
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
.hint {
  color: var(--muted);
}
.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 16px 0;
}
.filters input[type='search'] {
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: var(--panel);
  color: var(--text);
  font: inherit;
}
.filters label {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--muted);
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  padding: 6px 10px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: middle;
}
th {
  position: sticky;
  top: 0;
  background: var(--bg);
  color: var(--muted);
  font-weight: 600;
}
.cameo {
  display: block;
  width: 96px;
  image-rendering: pixelated;
}
.none {
  color: var(--muted);
}
</style>
