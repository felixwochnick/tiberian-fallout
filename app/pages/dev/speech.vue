<script setup lang="ts">
import { decodeAud, toAudioBuffer } from '~/lib/formats/aud'
import { loadSpeech, type SpeechFile } from '~/lib/game/speech'
import { getAssetStore } from '~/lib/storage/asset-store'

/** Dev only: every message of the computer voices EVA (GDI) and CABAL (Nod), to listen to. */
if (!import.meta.dev) navigateTo('/', { replace: true })
useHead({ title: 'Tiberian Fallout – EVA/CABAL (Dev)' })

const VOICES: [SpeechFile['voice'], string][] = [['EVA', 'EVA (GDI)'], ['CABAL', 'CABAL (Nod)']]
const KINDS: [string, string][] = [['I', 'Ansagen'], ['N', 'Missionen'], ['#', 'Ohne Dateinamen']]
const ARCHIVE_TITLES: Record<string, string> = {
  'SPEECH01.MIX': 'Tiberian Sun',
  'SPEECH02.MIX': 'Tiberian Sun',
  'E01VOX01.MIX': 'Firestorm',
  'E01VOX02.MIX': 'Firestorm',
}

const files = shallowRef<SpeechFile[]>([])
const loading = ref(true)
const search = ref('')
const playing = shallowRef<SpeechFile>()
/** Length in seconds, known once a file has been played */
const durations = reactive(new Map<SpeechFile, number>())

let ctx: AudioContext | undefined
let source: AudioBufferSourceNode | undefined

onMounted(async () => {
  files.value = await getAssetStore().then(loadSpeech).catch(() => [])
  loading.value = false
})
onBeforeUnmount(() => ctx?.close())

function kindOf(file: SpeechFile) {
  return file.name.startsWith('#') ? '#' : file.name.charAt(3)
}

const filtered = computed(() => {
  const query = search.value.trim().toLowerCase()
  if (!query) return files.value
  return files.value.filter(f => `${f.name} ${f.title ?? ''} ${f.archive}`.toLowerCase().includes(query))
})

function group(voice: SpeechFile['voice'], archive: string, kind: string) {
  return filtered.value.filter(f => f.voice === voice && f.archive === archive && kindOf(f) === kind)
}
function archivesOf(voice: SpeechFile['voice']) {
  return [...new Set(files.value.filter(f => f.voice === voice).map(f => f.archive))]
}

async function play(file: SpeechFile) {
  source?.stop()
  source = undefined
  if (playing.value === file) {
    playing.value = undefined
    return
  }
  playing.value = file
  ctx ??= new AudioContext()
  await ctx.resume().catch(() => {})
  const bytes = await file.mix.read(file.entry)
  if (!bytes || playing.value !== file) return
  let buffer: AudioBuffer
  try {
    buffer = toAudioBuffer(ctx, decodeAud(bytes))
  }
  catch (error) {
    console.warn(`${file.name}: ${(error as Error).message}`)
    playing.value = undefined
    return
  }
  durations.set(file, buffer.duration)
  const gain = ctx.createGain()
  gain.gain.value = volumeOf('voices')
  const node = ctx.createBufferSource()
  node.buffer = buffer
  node.connect(gain).connect(ctx.destination)
  node.onended = () => {
    if (source === node) {
      source = undefined
      playing.value = undefined
    }
  }
  node.start()
  source = node
}
</script>

<template>
  <div class="page">
    <header>
      <h1>EVA &amp; CABAL <small>Dev</small></h1>
      <p class="hint">
        Alle Sprachdateien der Computerstimmen aus <code>SPEECH01/02.MIX</code> (Tiberian Sun) und <code>E01VOX01/02.MIX</code> (Firestorm).
        {{ files.length }} gefunden. Die Titel sind nur für die Ansagen bekannt, die das Spiel schon nutzt.
      </p>
    </header>

    <p v-if="loading">
      Lade Spieldaten …
    </p>
    <p v-else-if="!files.length" class="hint">
      Keine Sprachdateien gefunden – <code>TIBSUN.MIX</code> wird mit der GDI-CD geladen (auf der <NuxtLink to="/">Startseite</NuxtLink> „Fehlende Dateien laden“).
    </p>
    <template v-else>
      <div class="filters">
        <input v-model="search" type="search" placeholder="Suchen (Datei, Titel) …">
      </div>
      <section v-for="[voice, voiceLabel] in VOICES" :key="voice">
        <h2>{{ voiceLabel }}</h2>
        <template v-for="archive in archivesOf(voice)" :key="archive">
          <template v-for="[kind, kindLabel] in KINDS" :key="kind">
            <template v-if="group(voice, archive, kind).length">
              <h3>{{ kindLabel }} <small>{{ ARCHIVE_TITLES[archive] }} · <code>{{ archive }}</code> · {{ group(voice, archive, kind).length }}</small></h3>
              <div class="list">
                <button
                  v-for="file in group(voice, archive, kind)"
                  :key="file.name"
                  class="btn btn-small"
                  :class="{ 'btn-secondary': playing !== file }"
                  :title="`${archive} / ${file.name}`"
                  @click="play(file)"
                >
                  <span v-if="file.title">{{ file.title }}</span>
                  <code>{{ file.name.replace(/\.AUD$/, '') }}</code>
                  <small v-if="durations.has(file)">{{ durations.get(file)!.toFixed(1) }} s</small>
                </button>
              </div>
            </template>
          </template>
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
  margin: 28px 0 4px;
  font-family: var(--display);
  font-size: 1.3rem;
}
h3 {
  margin: 16px 0 8px;
  font-size: 1rem;
}
h3 small {
  color: var(--muted);
  font-weight: normal;
}
.hint {
  color: var(--muted);
}
.filters {
  margin: 16px 0;
}
.filters input {
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: var(--panel);
  color: var(--text);
  font: inherit;
}
.list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.list button {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
}
.list button small {
  opacity: 0.7;
}
</style>
