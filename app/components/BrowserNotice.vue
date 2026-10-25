<script setup lang="ts">
/**
 * Launcher: in browsers without the Keyboard Lock API (Firefox, Safari) Esc always
 * leaves full screen and frees the mouse, while the game uses Esc for its menu.
 * Recommends Chrome (or another Chromium browser) before the game data is downloaded,
 * as the data is stored per browser.
 */
const props = defineProps<{ hasGame: boolean }>()

const DISMISSED_KEY = 'tiberian-fallout:browser-notice-dismissed'

const keyboardLock = typeof (navigator as Navigator & { keyboard?: { lock?: unknown } }).keyboard?.lock === 'function'

function browserName() {
  const agent = navigator.userAgent
  if (/firefox|fxios/i.test(agent)) return 'Firefox'
  if (/safari/i.test(agent) && !/chrome|chromium|crios|android/i.test(agent)) return 'Safari'
  return 'diesem Browser'
}
const browser = browserName()
const windows = /windows/i.test(navigator.userAgent)
/** Edge (Chromium) is on every Windows and can be started through its URL scheme */
const edgeUrl = `microsoft-edge:${location.href}`

let dismissed = false
try {
  dismissed = localStorage.getItem(DISMISSED_KEY) === '1'
}
catch {}
const open = ref(!keyboardLock && !dismissed)
const copied = ref(false)

/** A web page cannot start another browser, so hand over the link. */
async function openInChrome() {
  try {
    await navigator.clipboard.writeText(location.href)
    copied.value = true
  }
  catch {
    copied.value = false
    prompt('Diesen Link in Chrome öffnen:', location.href)
  }
}

function continueAnyway() {
  try {
    localStorage.setItem(DISMISSED_KEY, '1')
  }
  catch {}
  open.value = false
}
</script>

<template>
  <div v-if="open" class="notice" role="dialog" aria-modal="true" aria-labelledby="browser-notice-title">
    <div class="box">
      <h2 id="browser-notice-title">
        Am besten in Chrome spielen
      </h2>
      <p>
        In {{ browser }} beendet die <kbd>Esc</kbd>-Taste immer den Vollbildmodus und gibt die Maus frei –
        das kann eine Webseite dort nicht verhindern. Im Spiel öffnet <kbd>Esc</kbd> aber das Menü.
      </p>
      <p>
        Chrome und andere Chromium-Browser (Edge, Opera, Brave) geben <kbd>Esc</kbd> im Vollbild an das Spiel
        weiter; den Vollbildmodus verlässt man dort durch langes Drücken von <kbd>Esc</kbd>.
      </p>
      <p class="hint">
        Die Spieldaten werden pro Browser gespeichert. Wechselst du später, musst du sie dort erneut laden.
      </p>

      <div class="actions">
        <button class="btn" @click="openInChrome">
          In Chrome öffnen
        </button>
        <a v-if="windows" class="btn btn-secondary" :href="edgeUrl">
          In Edge öffnen
        </a>
      </div>
      <p v-if="copied" class="copied">
        Link kopiert – öffne Chrome und füge ihn in die Adresszeile ein.
        Noch kein Chrome? <a href="https://www.google.com/chrome/" target="_blank" rel="noopener">Chrome herunterladen</a>
      </p>

      <button class="anyway" @click="continueAnyway">
        Trotzdem in {{ browser }} {{ props.hasGame ? 'starten' : 'herunterladen' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.notice {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.75);
}
.box {
  max-width: 560px;
  padding: 28px;
  background: var(--panel);
  border: 1px solid var(--tib-dim);
  border-radius: 8px;
  box-shadow: 0 0 40px rgba(61, 255, 110, 0.12);
}
h2 {
  margin: 0 0 12px;
  font-family: var(--display);
  font-size: 1.2rem;
  color: var(--tib);
}
p {
  margin: 0 0 10px;
}
kbd {
  padding: 0 5px;
  border: 1px solid var(--line);
  border-radius: 3px;
  font-family: ui-monospace, monospace;
  font-size: 0.85em;
  color: var(--accent);
}
.hint {
  color: var(--muted);
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}
.copied {
  margin-top: 12px;
  color: var(--accent);
}
.anyway {
  margin-top: 18px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--muted);
  font: inherit;
  text-decoration: underline;
  cursor: pointer;
}
.anyway:hover {
  color: var(--text);
}
</style>
