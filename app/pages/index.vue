<script setup lang="ts">
import { capture, release } from '~/lib/input/mouse-capture'

useHead({ title: 'Command & Conquer: Tiberian Fallout' })

const settings = useSettings()
const isDev = import.meta.dev
const { files, persistent, loaded, hasMusic, importing, isComplete: hasGame, refresh, clear } = useGameAssets()
const { supported: deviceSupported } = useDeviceSupport()
const totalSize = computed(() => files.value.reduce((sum, f) => sum + f.size, 0))

function formatSize(bytes: number) {
  if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024).toFixed(0)} KB`
}

async function onClear() {
  if (confirm('Alle importierten Spieldaten aus dem Browser löschen?')) await clear()
}

onMounted(() => {
  refresh()
  release() // back from the game: no full screen and lock on the start page
})
</script>

<template>
  <div class="page">
    <header class="hero">
      <p class="eyebrow">
        Fan-Remake · Three.js
      </p>
      <h1>Command &amp; Conquer<br><span>Tiberian Fallout</span></h1>
      <p class="lead">
        Für Musik, Grafiken und Sounds werden die Original-Spieldaten von <em>Tiberian Sun</em> und <em>Firestorm</em> benötigt.
        Sie werden einmalig geladen und bleiben in deinem Browser gespeichert.
      </p>
      <p v-if="hasGame && !deviceSupported" class="device-hint">
        Zum Spielen werden Maus, Tastatur und ein größerer Bildschirm benötigt – z. B. ein Computer,
        ein Tablet mit Maus und Tastatur oder ein Handy im Desktop-Modus an einem Monitor.
        Die Spieldaten kannst du trotzdem schon laden.
      </p>
      <div class="actions">
        <NuxtLink v-if="hasGame && deviceSupported" class="btn btn-play" to="/menu" @click="capture($event, { lock: settings.mouseCapture })">
          Spiel starten
        </NuxtLink>
        <PwaInstall />
        <details v-if="isDev" class="dev-menu">
          <summary class="btn btn-play btn-secondary">
            Dev-Menü
          </summary>
          <nav>
            <NuxtLink to="/dev/catalog">Katalog: alle Einheiten und Gebäude</NuxtLink>
            <NuxtLink to="/dev/videos">Katalog: alle Videos</NuxtLink>
            <NuxtLink to="/dev/speech">Katalog: alle EVA/CABAL-Ansagen</NuxtLink>
          </nav>
        </details>
      </div>
    </header>

    <main class="grid">
      <section class="panel wide">
        <h2>Spieldaten laden</h2>
        <p>
          EA hat <em>Tiberian Sun</em> und <em>Firestorm</em> 2010 als Freeware freigegeben.
          Die benötigten Dateien werden direkt in deinen Browser geladen – auf jedem Betriebssystem, auch auf macOS.
        </p>
        <GameDataDownloader />

        <details class="alt">
          <summary>Eigene Spieldateien verwenden</summary>
          <p class="hint">
            Du hast das Spiel bereits? Importiere den Spielordner, einzelne <code>.mix</code>-Dateien oder die CD-Images (<code>.iso</code>).
          </p>
          <AssetImporter />
        </details>
      </section>

      <section v-if="loaded && files.length" class="panel wide">
        <div class="panel-head">
          <h2>Gespeicherte Dateien</h2>
          <button class="btn btn-secondary btn-small" :disabled="importing" @click="onClear">
            Löschen
          </button>
        </div>
        <p class="hint">
          {{ files.length }} Dateien · {{ formatSize(totalSize) }} ·
          {{ persistent ? 'dauerhaft im Browser gespeichert' : 'nur für diese Sitzung gespeichert (OPFS nicht verfügbar)' }}
        </p>
        <ul class="files">
          <li v-for="file in files" :key="file.name">
            <code>{{ file.name }}</code>
            <span>{{ formatSize(file.size) }}</span>
          </li>
        </ul>
        <p v-if="!hasMusic" class="warn">
          <code>SCORES.MIX</code> fehlt – ohne diese Datei gibt es keinen Soundtrack.
        </p>
      </section>

      <section v-if="hasMusic" class="panel wide">
        <h2>Original-Soundtrack</h2>
        <MusicPlayer />
      </section>
    </main>

    <BrowserNotice v-if="deviceSupported" :has-game="hasGame" />

    <footer class="footer">
      Inoffizielles Fanprojekt. Command &amp; Conquer ist eine Marke von Electronic Arts.
      Es werden keine Spieldateien mitgeliefert.
    </footer>
  </div>
</template>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 48px 16px 32px;
}
.hero {
  text-align: center;
  margin-bottom: 40px;
}
.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.3em;
  font-size: 0.8rem;
  color: var(--accent);
  margin: 0 0 12px;
}
h1 {
  font-family: var(--display);
  font-size: clamp(2rem, 6vw, 3.6rem);
  line-height: 1.05;
  margin: 0;
  text-shadow: 0 0 30px rgba(61, 255, 110, 0.25);
}
h1 span {
  color: var(--tib);
}
.lead {
  max-width: 620px;
  margin: 18px auto 0;
  color: var(--muted);
  font-size: 1.1rem;
}
.device-hint {
  max-width: 620px;
  margin: 24px auto 0;
  padding: 12px 16px;
  border: 1px solid var(--accent);
  border-radius: 6px;
  color: var(--accent);
}
.actions {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
}
.dev-menu {
  position: relative;
}
.dev-menu summary {
  list-style: none;
  cursor: pointer;
}
.dev-menu summary::-webkit-details-marker {
  display: none;
}
.dev-menu nav {
  position: absolute;
  top: calc(100% + 6px);
  left: 50%;
  z-index: 10;
  display: flex;
  flex-direction: column;
  min-width: 280px;
  transform: translateX(-50%);
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--panel);
  text-align: left;
  overflow: hidden;
}
.dev-menu nav a {
  padding: 10px 14px;
  color: var(--text);
  text-decoration: none;
}
.dev-menu nav a:hover {
  background: var(--line);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr));
  gap: 20px;
}
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 24px;
}
.panel.wide {
  grid-column: 1 / -1;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
h2 {
  font-family: var(--display);
  font-size: 1.15rem;
  margin: 0 0 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.alt {
  margin-top: 20px;
  border-top: 1px solid var(--line);
  padding-top: 16px;
}
.alt summary {
  cursor: pointer;
  color: var(--muted);
  font-weight: 600;
}
.alt summary:hover {
  color: var(--text);
}
.hint {
  font-size: 0.9rem;
  color: var(--muted);
}
.warn {
  color: var(--accent);
}
.files {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 6px 20px;
}
.files li {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding: 4px 0;
}
.files span {
  color: var(--muted);
}
.footer {
  margin-top: 40px;
  text-align: center;
  font-size: 0.8rem;
  color: var(--muted);
}
</style>
