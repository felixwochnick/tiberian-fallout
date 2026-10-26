<script setup lang="ts">
/**
 * "Spiel installieren": installs the game as an app (PWA) with the browser's own
 * dialog. Firefox and Safari have none: there it explains the way through the browser
 * menu instead. Hidden once the game runs as an installed app.
 */
const { $pwa } = useNuxtApp()

const installed = computed(() => !!$pwa?.isPWAInstalled)
const help = ref<HTMLDialogElement>()
const platform = ref<'ios' | 'safari' | 'firefox-android' | 'firefox' | 'other'>('other')

onMounted(() => {
  const agent = navigator.userAgent
  if (/iphone|ipad|ipod/i.test(agent) || (/macintosh/i.test(agent) && navigator.maxTouchPoints > 1)) platform.value = 'ios'
  else if (/firefox|fxios/i.test(agent)) platform.value = /android/i.test(agent) ? 'firefox-android' : 'firefox'
  else if (/safari/i.test(agent) && !/chrome|chromium|android/i.test(agent)) platform.value = 'safari'
})

async function install() {
  if ($pwa?.showInstallPrompt) await $pwa.install()
  else help.value?.showModal()
}
</script>

<template>
  <button v-if="!installed" class="btn btn-play btn-secondary" title="Als App installieren: startet im Vollbild und läuft auch offline" @click="install">
    Spiel installieren
  </button>

  <dialog ref="help" class="install-help" @click.self="help?.close()">
    <h2>Als App installieren</h2>
    <ol>
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
    <p class="hint">
      Als App startet das Spiel im Vollbild und läuft auch offline. Die geladenen Spieldaten bleiben erhalten.
    </p>
    <form method="dialog">
      <button class="btn">
        Verstanden
      </button>
    </form>
  </dialog>
</template>

<style scoped>
.install-help {
  max-width: min(440px, calc(100vw - 32px));
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--text);
  text-align: left;
}
.install-help::backdrop {
  background: rgba(0, 0, 0, 0.7);
}
h2 {
  font-family: var(--display);
  font-size: 1.15rem;
  margin: 0 0 14px;
}
ol {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 20px;
}
.hint {
  font-size: 0.9rem;
  color: var(--muted);
}
form {
  display: flex;
  justify-content: flex-end;
}
</style>
