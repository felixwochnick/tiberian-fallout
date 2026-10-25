<script setup lang="ts">
import { loadMenuMusic, loadStartupSound, loadUiSounds, type UiSound } from '~/lib/menu/audio'
import { CAMPAIGNS } from '~/lib/game/campaigns'
import { Emblem, type EmblemKind } from '~/lib/menu/emblem'
import { StartupScene, TIMELINE } from '~/lib/menu/startup-scene'
import { getAssetStore } from '~/lib/storage/asset-store'

const stage = ref<HTMLDivElement>()
const gdiEmblem = ref<HTMLDivElement>()
const nodEmblem = ref<HTMLDivElement>()
const time = ref(0)
const needsClick = ref(false)
const missingSound = ref(false)

let scene: StartupScene | undefined
const emblemViews: Emblem[] = []
let ctx: AudioContext | undefined
let startupSound: AudioBuffer | undefined
let menuMusic: AudioBuffer | undefined
let startupSource: AudioBufferSourceNode | undefined
let musicSource: AudioBufferSourceNode | undefined
let uiSounds: Partial<Record<UiSound, AudioBuffer>> = {}
let musicGain: GainNode | undefined
let effectsGain: GainNode | undefined
let startedAt = 0
let running = false
let musicStarted = false
let unmounted = false

/** Set when leaving a game (Kapitulieren): show the menu without the startup animation */
const menuAssembled = useState('menu-assembled', () => false)
let startAssembled = menuAssembled.value
menuAssembled.value = false

/** Dev only: `/menu?t=2.5` freezes the animation at that time (for comparing with the original). */
const frozenAt = import.meta.dev ? Number(useRoute().query.t) : Number.NaN

const clamp01 = (x: number) => Math.min(1, Math.max(0, x))
const fade = ([a, b]: readonly [number, number]) => clamp01((time.value - a) / (b - a))
const logo = computed(() => fade(TIMELINE.logo))
/** The logo flies in from far in front of the camera, heavily blurred. */
const logoStyle = computed(() => {
  // Stays huge for a moment, then shrinks quickly into place (like the original)
  const p = logo.value
  const eased = p ** 2.2
  return {
    opacity: p > 0 ? Math.min(1, p * 6) : 0,
    top: `${4 - 1 * eased}%`,
    transform: `translateX(-50%) scale(${5 - 4 * eased})`,
    filter: `blur(${(1 - eased) * 0.6}px) drop-shadow(0 0.3cqw 0.4cqw rgba(0, 0, 0, 0.8))`,
  }
})
const emblemStyle = computed(() => ({
  opacity: emblems.value,
  filter: `blur(${(1 - emblems.value) * 8}px)`,
}))
const emblems = computed(() => fade(TIMELINE.emblems))
const hologram = computed(() => fade(TIMELINE.hologram))
const showMenu = computed(() => time.value >= TIMELINE.end)

type Dialog = 'campaign' | 'skirmish' | 'options' | 'keys' | undefined
const dialog = ref<Dialog>()

// Settings of the dialogs (stored per browser, shared with the in-game menu)
const settings = useSettings()
watch(settings, () => {
  if (musicGain) musicGain.gain.value = settings.music / 100
  if (effectsGain) effectsGain.gain.value = settings.effects / 100
})
const aiLevels = AI_LEVELS
const speeds = SPEEDS

function sound(name: UiSound) {
  play(uiSounds[name], 0, false, effectsGain)
}

function openDialog(name: Exclude<Dialog, undefined>) {
  sound('click')
  sound('open')
  dialog.value = name
}

function closeDialog() {
  if (!dialog.value) return
  sound('open')
  dialog.value = undefined
}

const menuItems: { label: string, disabled?: boolean, action: () => void }[] = [
  { label: 'Neue Kampagne', action: () => openDialog('campaign') },
  // skirmishes are only offered while developing
  ...(import.meta.dev ? [{ label: 'Gefecht', action: () => openDialog('skirmish') }] : []),
  { label: 'Optionen', action: () => openDialog('options') },
  { label: 'Beenden', action: () => { sound('click'); navigateTo('/') } },
]

/** Highlighted like the selection of the original until the mouse is over the menu */
const defaultItem = menuItems.find(item => !item.disabled)

/** Player list of the skirmish dialog */
function addPlayer() {
  if (settings.players.length >= MAX_PLAYERS) return
  sound('click')
  const used = new Set(settings.players.map(p => p.colour))
  const colour = HOUSE_COLOURS.findIndex((_, i) => !used.has(i))
  const number = Math.max(0, ...settings.players.map(p => Number(/^Computer (\d+)$/.exec(p.name)?.[1] ?? 0))) + 1
  settings.players.push({ name: `Computer ${number}`, side: 'nod', colour: Math.max(0, colour), ai: 1 })
}

function removePlayer(index: number) {
  sound('click')
  settings.players.splice(index, 1)
}

function toggleSide(player: SkirmishPlayer) {
  sound('click')
  player.side = player.side === 'gdi' ? 'nod' : 'gdi'
}

/** The next colour no other player has */
function nextColour(player: SkirmishPlayer) {
  sound('click')
  const used = new Set(settings.players.filter(p => p !== player).map(p => p.colour))
  for (let step = 1; step <= HOUSE_COLOURS.length; step++) {
    const colour = (player.colour + step) % HOUSE_COLOURS.length
    if (!used.has(colour)) {
      player.colour = colour
      return
    }
  }
}

function nextLevel(player: SkirmishPlayer) {
  sound('click')
  player.ai = ((player.ai ?? 0) + 1) % AI_LEVELS.length
}

const chosenCampaign = ref(CAMPAIGNS[0]!.id)

/** Starts the chosen campaign with its first mission: briefing first (on the map selection page, if it has one) */
function startCampaign() {
  const campaign = CAMPAIGNS.find(c => c.id === chosenCampaign.value)
  const first = campaign?.missions[0]
  if (!first) return
  sound('click')
  navigateTo({ path: first.map ? '/briefing' : '/mission', query: { mission: first.id } })
}

function startSkirmish() {
  sound('click')
  navigateTo('/skirmish')
}

function replayIntro() {
  sound('click')
  dialog.value = undefined
  begin()
}

/** Audio clock when available, so picture and sound stay in sync. */
const now = () => (ctx && ctx.state === 'running' ? ctx.currentTime : performance.now() / 1000)

function play(buffer: AudioBuffer | undefined, offset = 0, loop = false, output?: AudioNode) {
  if (!ctx || !buffer) return undefined
  const source = ctx.createBufferSource()
  source.buffer = buffer
  source.loop = loop
  source.connect(output ?? ctx.destination)
  source.start(0, offset)
  return source
}

function startMusic() {
  if (musicStarted) return
  musicStarted = true
  musicSource = play(menuMusic, 0, true, musicGain)
}

function frame() {
  if (!running || !scene) return
  time.value = Number.isFinite(frozenAt) ? frozenAt : Math.min(now() - startedAt, TIMELINE.end + 600)
  if (time.value >= TIMELINE.end) startMusic()
  scene.render(Math.min(time.value, TIMELINE.end))
  requestAnimationFrame(frame)
}

async function begin() {
  needsClick.value = false
  await ctx?.resume().catch(() => {})
  startupSource?.stop()
  musicSource?.stop()
  musicStarted = false
  if (startAssembled) {
    // back from a game: the machine is already assembled, straight to the menu
    startAssembled = false
    startedAt = now() - TIMELINE.end
  }
  else {
    startedAt = now()
    startupSource = play(startupSound)
  }
  if (!running) {
    running = true
    requestAnimationFrame(frame)
  }
}

function skip() {
  if (time.value >= TIMELINE.end) return
  startupSource?.stop()
  startedAt = now() - TIMELINE.end
}

function onKey(event: KeyboardEvent) {
  if (dialog.value) {
    if (event.key === 'Escape') {
      // from the key bindings back to the options
      if (dialog.value === 'keys') {
        sound('open')
        dialog.value = 'options'
      }
      else closeDialog()
    }
    return
  }
  if (event.key === 'Escape' || event.key === ' ' || event.key === 'Enter') skip()
}

const onResize = () => {
  scene?.resize()
  for (const emblem of emblemViews) emblem.resize()
}

onMounted(async () => {
  for (const [kind, el] of [['gdi', gdiEmblem.value!], ['nod', nodEmblem.value!]] as [EmblemKind, HTMLElement][]) {
    Emblem.create(el, kind)
      .then((emblem) => {
        if (unmounted) emblem.dispose()
        else emblemViews.push(emblem)
      })
      .catch(error => console.error(`Emblem ${kind} konnte nicht geladen werden`, error))
  }
  try {
    scene = await StartupScene.create(stage.value!)
    if (unmounted) {
      scene.dispose()
      return
    }
  }
  catch (error) {
    console.error('Startanimation konnte nicht geladen werden', error)
    return
  }
  window.addEventListener('resize', onResize)
  window.addEventListener('keydown', onKey)

  const store = await getAssetStore()
  ctx = new AudioContext()
  musicGain = ctx.createGain()
  musicGain.gain.value = settings.music / 100
  musicGain.connect(ctx.destination)
  effectsGain = ctx.createGain()
  effectsGain.gain.value = settings.effects / 100
  effectsGain.connect(ctx.destination)
  ;[startupSound, menuMusic, uiSounds] = await Promise.all([
    loadStartupSound(ctx, store).catch(() => undefined),
    loadMenuMusic(ctx, store).catch(() => undefined),
    loadUiSounds(ctx, store).catch(() => ({})),
  ])
  missingSound.value = !startupSound

  // Browsers only allow sound after a user gesture
  await ctx.resume().catch(() => {})
  if (ctx.state === 'running' || Number.isFinite(frozenAt)) await begin()
  else needsClick.value = true
})

onBeforeUnmount(() => {
  unmounted = true
  running = false
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onKey)
  startupSource?.stop()
  musicSource?.stop()
  ctx?.close()
  scene?.dispose()
  for (const emblem of emblemViews) emblem.dispose()
})
</script>

<template>
  <div class="viewport" @click="needsClick ? begin() : skip()">
    <div ref="stage" class="canvas" />
    <div class="vignette" />

    <!-- 16:10 frame aligned with the machine; holds the 2D layers of the original screen -->
    <div class="frame">
      <div class="logo" :style="logoStyle">
        <span class="logo-small">Command</span>
        <span class="logo-amp">&amp;</span>
        <span class="logo-small">Conquer</span>
        <span class="logo-big">Tiberian</span>
        <span class="logo-sub">Fallout</span>
        <svg class="logo-chevron" viewBox="0 0 100 24" aria-hidden="true">
          <path d="M2 2 L50 22 L98 2 L84 2 L50 14 L16 2 Z" fill="#8d8a80" stroke="#2a2620" stroke-width="1.5" />
        </svg>
      </div>

      <div ref="gdiEmblem" class="emblem gdi" :style="emblemStyle" aria-label="GDI" />

      <!-- red glass in CSS, the black parts of the logo as metal (WebGL) on top -->
      <div ref="nodEmblem" class="emblem nod" :style="emblemStyle" aria-label="Nod">
        <div class="nod-glass" />
      </div>

      <span class="corner tr" :style="{ opacity: hologram }">)))</span>
      <span class="corner bl" :style="{ opacity: hologram }">(((</span>

      <Transition name="menu">
        <nav v-if="showMenu && !dialog" class="menu" @click.stop>
          <button
            v-for="item in menuItems"
            :key="item.label"
            class="menu-item"
            :class="{ default: item === defaultItem }"
            :disabled="item.disabled"
            :title="item.disabled ? 'Die Kampagnen folgen später' : undefined"
            @click="item.action()"
          >
            {{ item.label }}
          </button>
        </nav>
      </Transition>

      <MenuScroll :open="dialog === 'keys'">
        <h2 class="dialog-title">
          Tastenbelegung
        </h2>
        <KeyBindings @click="sound('click')">
          <button class="metal-btn" @click="sound('click'); sound('open'); dialog = 'options'">
            Zurück
          </button>
        </KeyBindings>
      </MenuScroll>

      <MenuScroll :open="dialog === 'campaign'">
        <h2 class="dialog-title">
          Neue Kampagne
        </h2>
        <ul class="dialog-list">
          <li
            v-for="campaign in CAMPAIGNS"
            :key="campaign.id"
            :class="{ selected: campaign.id === chosenCampaign }"
            @click="sound('click'); chosenCampaign = campaign.id"
          >
            {{ campaign.title }}
          </li>
        </ul>
        <p class="campaign-description">
          {{ CAMPAIGNS.find(c => c.id === chosenCampaign)?.description }}
        </p>
        <div class="dialog-buttons">
          <button class="metal-btn" @click="startCampaign()">
            Starten
          </button>
          <button class="metal-btn" @click="sound('click'); closeDialog()">
            Abbrechen
          </button>
        </div>
      </MenuScroll>

      <MenuScroll :open="dialog === 'skirmish'" class="skirmish">
        <h2 class="dialog-title">
          Gefecht
        </h2>
        <!-- the players: side, colour and level are switched by clicking them -->
        <ul class="dialog-list players">
          <li class="head">
            <span>Spieler</span><span>Seite</span><span>Farbe</span><span>Stärke</span><span />
          </li>
          <li v-for="(player, i) in settings.players" :key="i">
            <span class="player-name">{{ player.name }}</span>
            <button class="cell" title="Seite wechseln" @click="toggleSide(player)">
              {{ player.side === 'gdi' ? 'GDI' : 'Nod' }}
            </button>
            <button class="cell" :title="HOUSE_COLOURS[player.colour]![0]" @click="nextColour(player)">
              <i class="swatch" :style="{ background: `#${HOUSE_COLOURS[player.colour]![1].toString(16).padStart(6, '0')}` }" />
            </button>
            <button v-if="player.ai !== null" class="cell" title="Stärke wechseln" @click="nextLevel(player)">
              {{ aiLevels[player.ai] }}
            </button>
            <span v-else class="cell">Mensch</span>
            <button v-if="player.ai !== null" class="cell remove" title="Spieler entfernen" @click="removePlayer(i)">
              ✕
            </button>
            <span v-else />
          </li>
        </ul>
        <div class="dialog-buttons">
          <button class="metal-btn" :disabled="settings.players.length >= MAX_PLAYERS" @click="addPlayer()">
            Spieler hinzufügen
          </button>
        </div>
        <div class="slider-row">
          <MetalSlider v-model="settings.credits" label="Startkapital" :min="2500" :max="10000" :step="500" @change="sound('click')" />
          <MetalSlider v-model="settings.speed" label="Spieltempo" :min="0" :max="6" :display="speeds[settings.speed]" @change="sound('click')" />
        </div>
        <div class="slider-row">
          <MetalSlider v-model="settings.techLevel" label="Techstufe" :min="1" :max="10" @change="sound('click')" />
          <div class="toggle">
            <span title="Immer an: das Radar funktioniert von Anfang an. Sonst erst mit Radargebäude und genug Energie.">Radar</span>
            <button class="metal-btn" @click="sound('click'); settings.radarAlways = !settings.radarAlways">
              {{ settings.radarAlways ? 'Immer an' : 'Mit Gebäude' }}
            </button>
          </div>
        </div>
        <div class="dialog-buttons">
          <button class="metal-btn" @click="startSkirmish()">
            Starten
          </button>
          <button class="metal-btn" @click="sound('click'); closeDialog()">
            Abbrechen
          </button>
        </div>
      </MenuScroll>

      <MenuScroll :open="dialog === 'options'">
        <h2 class="dialog-title">
          Optionen
        </h2>
        <MetalSlider v-model="settings.music" label="Musik" :display="`${settings.music} %`" />
        <MetalSlider v-model="settings.effects" label="Effekte" :display="`${settings.effects} %`" @change="sound('click')" />
        <div class="toggle">
          <span title="Klassisch: Linksklick wählt aus und gibt Befehle, Rechtsklick wählt ab. Modern: Linksklick wählt aus, Rechtsklick gibt Befehle.">Steuerung</span>
          <button class="metal-btn" @click="sound('click'); settings.controls = settings.controls === 'modern' ? 'classic' : 'modern'">
            {{ settings.controls === 'modern' ? 'Modern' : 'Klassisch' }}
          </button>
        </div>
        <ul class="dialog-list">
          <li>
            <NuxtLink to="/" @click="sound('click')">
              Spieldaten &amp; Soundtrack
            </NuxtLink>
          </li>
          <li @click="replayIntro()">
            Intro wiederholen
          </li>
        </ul>
        <div class="dialog-buttons">
          <button class="metal-btn" @click="sound('click'); sound('open'); dialog = 'keys'">
            Tastenbelegung
          </button>
          <button class="metal-btn" @click="sound('click'); closeDialog()">
            Zurück
          </button>
        </div>
      </MenuScroll>
    </div>

    <button v-if="needsClick" class="start-hint">
      Klicken zum Starten
    </button>
    <span v-else-if="!showMenu" class="skip-hint">Klick oder Esc zum Überspringen</span>
    <span v-if="missingSound && showMenu" class="sound-hint">
      Ohne Startsound – auf der Startseite „Fehlende Dateien laden“.
    </span>
  </div>
</template>

<style scoped>
.viewport {
  position: fixed;
  inset: 0;
  overflow: hidden;
  background: #000;
  cursor: pointer;
  user-select: none;
}
/* Same box as the 16:10 camera frame (see StartupScene.resize) */
.frame {
  position: absolute;
  left: 50%;
  top: 50%;
  width: min(100vw, 160vh);
  aspect-ratio: 16 / 10;
  transform: translate(-50%, -50%);
  container-type: size;
  pointer-events: none;
}
.frame > * {
  pointer-events: auto;
}
.canvas,
.canvas :deep(canvas) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.vignette {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(ellipse min(60vw, 96vh) min(70vh, 43.75vw) at 50% 50%, transparent 40%, rgba(0, 0, 0, 0.88) 100%);
}
.logo {
  position: absolute;
  top: 3%;
  left: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 0.9;
  pointer-events: none;
  transform-origin: 50% 0;
}
.logo-small,
.logo-amp,
.logo-big,
.logo-sub {
  font-family: var(--display);
  font-weight: 800;
  text-transform: uppercase;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.logo-small {
  font-size: 2.3cqw;
  letter-spacing: 0.04em;
  background-image: linear-gradient(#fff4d8, #f0b040 60%, #a85a10);
  -webkit-text-stroke: 1px #3a1c04;
}
.logo-amp {
  font-size: 1.4cqw;
  color: #f0c060;
  -webkit-text-stroke: 0;
}
.logo-big {
  font-size: 6.2cqw;
  background-image: linear-gradient(#ffe27a, #ff9a22 50%, #c2440a);
  -webkit-text-stroke: 1px #4a1a04;
}
.logo-sub {
  font-size: 4cqw;
  background-image: linear-gradient(#ffd060, #ff8418 55%, #a83806);
  -webkit-text-stroke: 1px #4a1a04;
}
.logo-chevron {
  width: 18%;
  min-width: 40px;
  margin-top: 0.2em;
}
.emblem {
  position: absolute;
  width: 13%;
  pointer-events: none;
}
.gdi {
  top: 2%;
  left: 2%;
  width: 16%;
  aspect-ratio: 1;
}
.emblem :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
}
.nod {
  /*
   * The hexagon covers the middle 70 % (NOD_SCALE in emblem.ts), the rest is for the glow.
   * The hexagon (83 % as high as wide) is as high as the GDI dome is wide (78 % of 16 %),
   * placed mirrored to it in the bottom right corner.
   */
  right: -0.7%;
  bottom: -4.3%;
  width: 21.4%;
  aspect-ratio: 1;
}
.nod-glass {
  position: absolute;
  inset: 15%;
  /*
   * Nod red behind the black logo, lit from behind: a hot red core, twelve soft
   * light beams fanning out from it that fade into dark red towards the edge.
   * Cut to the middle of the metal ring, so no red shows outside of it.
   */
  background:
    radial-gradient(circle at 50% 52%, #ff2a10 0%, #f01a08 10%, rgba(240, 26, 8, 0) 26%),
    radial-gradient(circle at 50% 52%, rgba(60, 0, 0, 0) 15%, rgba(60, 0, 0, 0.55) 45%, rgba(40, 0, 0, 0.95) 72%),
    repeating-conic-gradient(from -7.5deg at 50% 52%,
      rgba(255, 42, 16, 0) 0deg, rgba(255, 42, 16, 0.85) 7.5deg, rgba(255, 42, 16, 0) 15deg, rgba(255, 42, 16, 0) 30deg),
    radial-gradient(circle at 50% 52%, #ff3a1a 0%, #d10000 30%, #6e0000 60%, #2a0000 75%);
  clip-path: polygon(61.83% 11.40%, 96.33% 68.60%, 83.01% 88.64%, 16.99% 88.64%, 3.67% 68.60%, 38.17% 11.40%);
}
.nod :deep(canvas) {
  position: relative;
}
.corner {
  position: absolute;
  color: #3dff7a;
  font: 700 1.6cqw var(--display);
  text-shadow: 0 0 8px #3dff7a;
  letter-spacing: -0.05em;
  pointer-events: none;
}
.tr {
  top: 4%;
  right: 8%;
}
.bl {
  bottom: 5%;
  left: 8%;
}
.menu {
  position: absolute;
  left: 50%;
  top: 44%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  animation: menu-in 0.5s ease-out;
}
.menu-leave-active {
  transition: opacity 0.2s;
}
.menu-leave-to {
  opacity: 0;
}
.campaign-description {
  margin: 0;
  font: 600 2.4cqh / 1.4 var(--body);
  color: #d8f0c0;
}
/* the skirmish dialog needs more room for its player list: a little taller */
.frame .skirmish {
  top: 31%;
  height: 65%;
}
.slider-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6%;
}
/* player list of the skirmish dialog: name, side, colour, level, remove */
.players {
  flex: 1 1 auto;
  min-height: 0;
  font-size: 2.3cqh;
}
.players li {
  display: grid;
  grid-template-columns: 1fr 4em 3.8em 5em 1.6em;
  align-items: center;
  gap: 0.4em;
  cursor: default;
}
.players li[data-hover] {
  background: none;
}
.players .head {
  font-size: 0.8em;
  color: #9fd0dc;
  text-transform: uppercase;
}
.player-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.players .cell {
  padding: 0.05em 0.2em;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-align: center;
  cursor: pointer;
}
.players .cell[data-hover] {
  color: #fff;
  background: rgba(130, 200, 220, 0.35);
}
.players span.cell {
  cursor: default;
  color: #9fd0dc;
}
.swatch {
  display: inline-block;
  width: 1.4em;
  height: 0.8em;
  vertical-align: middle;
  border: 1px solid rgba(0, 0, 0, 0.8);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.35);
}
.players .remove {
  color: #ff8a70;
}
.start-hint {
  position: absolute;
  inset: 0;
  margin: auto;
  width: max-content;
  height: max-content;
  font: 600 1.2rem var(--display);
  color: #3dff7a;
  background: rgba(0, 0, 0, 0.7);
  border: 1px solid #3dff7a;
  padding: 0.8em 1.6em;
  cursor: pointer;
}
.skip-hint,
.sound-hint {
  position: absolute;
  bottom: 1.5%;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.35);
  pointer-events: none;
  white-space: nowrap;
}
@keyframes menu-in {
  from {
    opacity: 0;
  }
}

</style>
