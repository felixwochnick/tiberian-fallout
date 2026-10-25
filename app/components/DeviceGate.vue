<script setup lang="ts">
/**
 * Game pages: shows the game only with mouse and a big enough screen. Once the game
 * is running it stays mounted; losing the mouse (unplugged) only covers it.
 */
const { pointer, screen, supported } = useDeviceSupport()
const started = ref(supported.value)
watch(supported, (ok) => {
  if (ok) started.value = true
})
</script>

<template>
  <slot v-if="started" />
  <div v-if="!supported" class="gate">
    <div class="box">
      <h2>Maus und Tastatur benötigt</h2>
      <p>
        Tiberian Fallout ist ein Echtzeit-Strategiespiel und wird mit Maus und Tastatur gespielt.
      </p>
      <ul>
        <li :class="{ ok: pointer }">
          {{ pointer ? 'Maus erkannt' : 'Keine Maus erkannt – schließe eine Maus oder ein Trackpad an.' }}
        </li>
        <li :class="{ ok: screen }">
          {{ screen ? 'Bildschirm groß genug' : `Der Bildschirm ist zu klein (mindestens ${MIN_SCREEN.long} × ${MIN_SCREEN.short} Pixel).` }}
        </li>
      </ul>
      <p class="hint">
        Tablets mit Maus und Tastatur funktionieren, ebenso Handys im Desktop- bzw. Docking-Modus an einem Monitor.
        Das Spiel geht von selbst weiter, sobald alles da ist.
      </p>
      <NuxtLink to="/">
        Zur Startseite
      </NuxtLink>
    </div>
  </div>
</template>

<style scoped>
.gate {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: grid;
  place-items: center;
  padding: 16px;
  background: #000;
  overflow: auto;
}
.box {
  max-width: 520px;
  padding: 24px;
  background: var(--panel);
  border: 1px solid var(--tib-dim);
  border-radius: 8px;
}
h2 {
  margin: 0 0 12px;
  font-family: var(--display);
  font-size: 1.15rem;
  color: var(--tib);
}
p {
  margin: 0 0 10px;
}
ul {
  margin: 0 0 12px;
  padding-left: 1.2em;
}
li {
  color: var(--danger);
}
li.ok {
  color: var(--tib);
}
.hint {
  color: var(--muted);
}
</style>
