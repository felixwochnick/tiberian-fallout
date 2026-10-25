<script setup lang="ts">
import type { Track } from '~/lib/game/soundtrack'
import { capture, mouseCapture, needsResume } from '~/lib/input/mouse-capture'
import { loadUiSounds, type UiSound } from '~/lib/menu/audio'
import { getAssetStore } from '~/lib/storage/asset-store'

/**
 * In-game menu (Esc), in the look of the main menu: the scroll unrolls between its
 * pillars with the same sounds. Also opens when the browser left full screen on its
 * own (Esc in Firefox and Safari), so "Weiter" can capture again.
 */

const emit = defineEmits<{ restart: [] }>()
const music = useMusicPlayer()
/** The game waits while the menu is open */
const paused = defineModel<boolean>('paused', { default: false })

type Dialog = 'main' | 'options' | 'keys' | undefined
const dialog = ref<Dialog>()
const settings = useSettings()
const logoSeen = useState('westwood-logo-seen', () => false)
const menuAssembled = useState('menu-assembled', () => false)

let ctx: AudioContext | undefined
let effectsGain: GainNode | undefined
let uiSounds: Partial<Record<UiSound, AudioBuffer>> = {}

function sound(name: UiSound) {
  const buffer = uiSounds[name]
  if (!ctx || !buffer || !effectsGain) return
  ctx.resume().catch(() => {})
  const source = ctx.createBufferSource()
  source.buffer = buffer
  source.connect(effectsGain)
  source.start()
}

/** Like the main menu: the sheet unrolls with the mechanical slide. */
function show(next: Dialog) {
  if (next === dialog.value) return
  if (next) sound('open')
  dialog.value = next
  paused.value = !!next
}

function open() {
  show('main')
}

function openOptions() {
  sound('click')
  show('options')
}

function back() {
  sound('click')
  show(dialog.value === 'keys' ? 'options' : 'main')
}

function openKeys() {
  sound('click')
  show('keys')
}

/** Closes the menu; from a click it also brings full screen and the lock back. */
function resume(event?: MouseEvent) {
  if (event) sound('click')
  sound('open')
  dialog.value = undefined
  paused.value = false
  if (event && (needsResume() || !mouseCapture.wanted)) capture(event, { lock: settings.mouseCapture })
}

/** Back to the main menu, without the Westwood logo and the startup animation; full screen and the lock stay on. */
function surrender() {
  sound('click')
  logoSeen.value = true
  menuAssembled.value = true
  navigateTo('/menu')
}

function restart(event: MouseEvent) {
  emit('restart')
  resume(event)
}

function playTrack(track: Track) {
  sound('click')
  music.play(track)
}

function toggleControls() {
  sound('click')
  settings.controls = settings.controls === 'modern' ? 'classic' : 'modern'
}

function toggleMouseCapture(event: MouseEvent) {
  sound('click')
  settings.mouseCapture = !settings.mouseCapture
  capture(event, { lock: settings.mouseCapture })
}

/** The HUD's "Optionen" tab opens the menu as well. */
defineExpose({
  open() {
    sound('click')
    open()
  },
})

function onKey(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  event.preventDefault()
  if (!dialog.value) open()
  else if (dialog.value === 'options' || dialog.value === 'keys') back()
  else resume()
}

// Esc in Firefox and Safari never reaches the page, it only leaves full screen
watch(needsResume, (lost) => {
  if (lost && !dialog.value) open()
})

watch(() => settings.effects, (value) => {
  if (effectsGain) effectsGain.gain.value = value / 100
})

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  ctx = new AudioContext()
  effectsGain = ctx.createGain()
  effectsGain.gain.value = settings.effects / 100
  effectsGain.connect(ctx.destination)
  uiSounds = await loadUiSounds(ctx, await getAssetStore()).catch(() => ({}))
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  ctx?.close()
})
</script>

<template>
  <div class="pause" :class="{ active: dialog }">
    <!-- 16:10 frame like the main menu, so the scroll has the same size -->
    <div class="frame">
      <MenuScroll :open="dialog === 'main'" class="esc">
        <h2 class="dialog-title">
          Menü
        </h2>
        <nav class="entries">
          <button class="metal-btn" disabled title="Speichern folgt später">
            Speichern
          </button>
          <button class="metal-btn" disabled title="Laden folgt später">
            Laden
          </button>
          <button class="metal-btn" @click="surrender()">
            Kapitulieren
          </button>
          <button class="metal-btn" @click="restart($event)">
            Neu starten
          </button>
          <button class="metal-btn" @click="openOptions()">
            Optionen
          </button>
          <button class="metal-btn" @click="resume($event)">
            Weiter
          </button>
        </nav>
      </MenuScroll>

      <MenuScroll :open="dialog === 'options'" class="esc tall">
        <h2 class="dialog-title">
          Optionen
        </h2>
        <MetalSlider v-model="settings.music" label="Musik" :display="`${settings.music} %`" />
        <ul class="dialog-list tracks">
          <li v-if="!music.tracks.value.length">
            Kein Soundtrack geladen
          </li>
          <li
            v-for="track in music.tracks.value"
            :key="track.id"
            :class="{ selected: track.id === music.current.value }"
            @click="playTrack(track)"
          >
            {{ track.title }}
          </li>
        </ul>
        <MetalSlider v-model="settings.effects" label="Effekte" :display="`${settings.effects} %`" @change="sound('click')" />
        <MetalSlider v-model="settings.speed" label="Spieltempo" :min="0" :max="6" :display="SPEEDS[settings.speed]" @change="sound('click')" />
        <MetalSlider v-model="settings.scrollSpeed" label="Scrolltempo" :min="0" :max="6" :display="SPEEDS[settings.scrollSpeed]" @change="sound('click')" />
        <div class="toggle">
          <span title="Vollbild, die Maus bleibt im Spiel">Mausfang</span>
          <button class="metal-btn" @click="toggleMouseCapture($event)">
            {{ settings.mouseCapture ? 'An' : 'Aus' }}
          </button>
        </div>
        <div class="toggle">
          <span title="Klassisch: Linksklick wählt aus und gibt Befehle, Rechtsklick wählt ab. Modern: Linksklick wählt aus, Rechtsklick gibt Befehle.">Steuerung</span>
          <button class="metal-btn" @click="toggleControls()">
            {{ settings.controls === 'modern' ? 'Modern' : 'Klassisch' }}
          </button>
        </div>
        <div class="dialog-buttons">
          <button class="metal-btn" @click="openKeys()">
            Tastenbelegung
          </button>
          <button class="metal-btn" @click="back()">
            Zurück
          </button>
        </div>
      </MenuScroll>

      <MenuScroll :open="dialog === 'keys'" class="esc">
        <h2 class="dialog-title">
          Tastenbelegung
        </h2>
        <KeyBindings @click="sound('click')">
          <button class="metal-btn" @click="back()">
            Zurück
          </button>
        </KeyBindings>
      </MenuScroll>
    </div>
  </div>
</template>

<style scoped>
.pause {
  position: fixed;
  inset: 0;
  z-index: 100;
  pointer-events: none;
  transition: background 0.3s;
}
.pause.active {
  pointer-events: auto;
  background: rgba(0, 0, 0, 0.45);
}
.frame {
  position: absolute;
  left: 50%;
  top: 50%;
  width: min(100vw, 160vh);
  aspect-ratio: 16 / 10;
  transform: translate(-50%, -50%);
  container-type: size;
}
/* higher than in the main menu, there is no logo above it */
.frame .esc {
  top: 12%;
  height: 76%;
}
.frame .esc.tall {
  top: 5%;
  height: 90%;
}
.entries {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.6cqh;
}
.entries .metal-btn {
  width: 55%;
}
.tracks {
  flex: 1.4;
  font-size: 2.4cqh;
}
</style>
