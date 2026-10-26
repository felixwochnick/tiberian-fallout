<script setup lang="ts">
/**
 * "Spiel installieren": a short setup in two steps. First the game data of Tiberian Sun
 * and Firestorm, whole, then the game as an app (PWA) with the browser's own dialog.
 * Firefox and Safari have none: there it explains the way through the browser menu
 * instead. Hidden once the game runs as an installed app with all its data.
 *
 * "Update installieren" instead, when this version of the game needs more of the original
 * data or a new version of the game itself is waiting: it loads what is missing and
 * then reloads into the new version.
 */
const { $pwa } = useNuxtApp()
const { isComplete, needsDataUpdate, importing, downloadDiscs } = useGameAssets()

/** The service worker has loaded a new version of the game */
const appUpdate = computed(() => !!$pwa?.needRefresh)
const updating = ref(false)

const installed = computed(() => !!$pwa?.isPWAInstalled)
const setup = ref<HTMLDialogElement>()
const step = ref<'data' | 'app' | 'update'>('data')
/** The browser's install dialog was accepted */
const accepted = ref(false)
const platform = ref<'ios' | 'safari' | 'firefox-android' | 'firefox' | 'other'>('other')

onMounted(() => {
  const agent = navigator.userAgent
  if (/iphone|ipad|ipod/i.test(agent) || (/macintosh/i.test(agent) && navigator.maxTouchPoints > 1)) platform.value = 'ios'
  else if (/firefox|fxios/i.test(agent)) platform.value = /android/i.test(agent) ? 'firefox-android' : 'firefox'
  else if (/safari/i.test(agent) && !/chrome|chromium|android/i.test(agent)) platform.value = 'safari'
})

// on to the app (or the new version) as soon as the data is complete
watch(isComplete, (complete) => {
  if (!complete || step.value !== 'data') return
  if (updating.value) finishUpdate()
  else step.value = 'app'
})

function open() {
  updating.value = false
  step.value = isComplete.value ? 'app' : 'data'
  setup.value?.showModal()
}

/** Loads the missing data right away, then switches to the new version of the game */
function update() {
  updating.value = true
  setup.value?.showModal()
  if (isComplete.value) return finishUpdate()
  step.value = 'data'
  downloadDiscs()
}

function finishUpdate() {
  step.value = 'update'
  // reloads the page with the new version; without one the update is done here
  if (appUpdate.value) $pwa?.updateServiceWorker()
}

async function install() {
  const choice = await $pwa?.install()
  if (choice?.outcome === 'accepted') accepted.value = true
}
</script>

<template>
  <button v-if="needsDataUpdate || appUpdate" class="btn btn-play" title="Lädt fehlende Spieldaten bzw. die neue Version des Spiels" @click="update">
    Update installieren
  </button>
  <button v-else-if="!installed || !isComplete" class="btn btn-play btn-secondary" title="Spieldaten laden und als App installieren: startet im Vollbild und läuft auch offline" @click="open">
    Spiel installieren
  </button>

  <dialog ref="setup" class="setup" @cancel="importing && $event.preventDefault()">
    <h2>{{ updating ? 'Update installieren' : 'Spiel installieren' }}</h2>
    <ol v-if="!updating" class="steps">
      <li :class="{ active: step === 'data', done: isComplete }">
        <span>1</span> Spieldaten
      </li>
      <li :class="{ active: step === 'app', done: installed || accepted }">
        <span>2</span> App
      </li>
    </ol>

    <section v-if="step === 'data'">
      <p v-if="updating" class="hint">
        Diese Version des Spiels braucht weitere Original-Spieldaten von <em>Tiberian Sun</em> bzw. <em>Firestorm</em>.
        Die CDs werden dafür noch einmal vollständig geladen.
      </p>
      <p v-else class="hint">
        <em>Tiberian Sun</em> und <em>Firestorm</em> werden einmal vollständig geladen und bleiben im Browser gespeichert.
      </p>
      <GameDataDownloader />
    </section>

    <section v-else-if="step === 'update'">
      <p v-if="appUpdate">
        Die neue Version des Spiels wird gestartet …
      </p>
      <p v-else>
        Die Spieldaten sind auf dem neuesten Stand.
      </p>
    </section>

    <section v-else>
      <p v-if="installed || accepted">
        Das Spiel ist als App installiert. Du findest es bei deinen Programmen bzw. auf dem Home-Bildschirm.
      </p>
      <template v-else-if="$pwa?.showInstallPrompt">
        <p>Als App startet das Spiel im Vollbild und läuft auch offline.</p>
        <button class="btn" @click="install">
          Jetzt installieren
        </button>
      </template>
      <template v-else>
        <p>Als App startet das Spiel im Vollbild und läuft auch offline. So installierst du es:</p>
        <ol class="howto">
          <template v-if="platform === 'ios'">
            <li>Tippe unten auf <strong>Teilen</strong>.</li>
            <li>Wähle <strong>Zum Home-Bildschirm</strong>.</li>
          </template>
          <template v-else-if="platform === 'safari'">
            <li>Öffne in der Menüleiste <strong>Ablage</strong>.</li>
            <li>Wähle <strong>Zum Dock hinzufügen …</strong>.</li>
          </template>
          <template v-else-if="platform === 'firefox-android'">
            <li>Öffne das Browsermenü <strong>⋮</strong>.</li>
            <li>Wähle <strong>Installieren</strong> bzw. <strong>Zum Startbildschirm hinzufügen</strong>.</li>
          </template>
          <template v-else-if="platform === 'firefox'">
            <li>Firefox kann Web-Apps auf dem Computer nicht installieren.</li>
            <li>Öffne die Seite in Chrome oder Edge und klicke dort auf <strong>Spiel installieren</strong>.</li>
          </template>
          <template v-else>
            <li>Öffne das Browsermenü.</li>
            <li>Wähle <strong>Installieren</strong> bzw. <strong>App installieren</strong>.</li>
          </template>
        </ol>
      </template>
    </section>

    <div class="buttons">
      <button v-if="step === 'app' && !isComplete" class="btn btn-secondary" @click="step = 'data'">
        Zurück
      </button>
      <button v-if="step === 'data' && isComplete && !updating" class="btn" @click="step = 'app'">
        Weiter
      </button>
      <button class="btn btn-secondary" :disabled="importing" @click="setup?.close()">
        {{ isComplete && (updating || installed || accepted) ? 'Fertig' : 'Schließen' }}
      </button>
    </div>
  </dialog>
</template>

<style scoped>
.setup {
  width: min(560px, calc(100vw - 32px));
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--text);
  text-align: left;
}
.setup::backdrop {
  background: rgba(0, 0, 0, 0.7);
}
h2 {
  font-family: var(--display);
  font-size: 1.15rem;
  margin: 0 0 14px;
}
.steps {
  display: flex;
  gap: 20px;
  margin: 0 0 18px;
  padding: 0 0 14px;
  border-bottom: 1px solid var(--line);
  list-style: none;
  color: var(--muted);
}
.steps li {
  display: flex;
  align-items: center;
  gap: 8px;
}
.steps span {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border: 1px solid var(--line);
  border-radius: 50%;
  font-size: 0.8rem;
}
.steps .active {
  color: var(--text);
}
.steps .active span {
  border-color: var(--tib);
}
.steps .done span {
  border-color: var(--tib);
  background: var(--tib-dim);
}
.howto {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 20px;
}
.hint {
  font-size: 0.9rem;
  color: var(--muted);
}
.buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
</style>
