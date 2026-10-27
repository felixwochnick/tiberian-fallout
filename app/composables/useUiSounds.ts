import { decodeAud, toAudioBuffer } from '~/lib/formats/aud'
import { MixArchive } from '~/lib/formats/mix'
import { type EvaSound, loadUiSounds, type UiSound } from '~/lib/menu/audio'
import { getAssetStore } from '~/lib/storage/asset-store'

/**
 * Sounds of the game on one shared audio context, each at the volume of its kind:
 * "Schüsse" (shots, impacts, explosions), "Effekte" (clicks, radar, building …) and
 * "Stimmen" (EVA, the units), all times the overall volume. Loaded once on first use.
 */
type Bus = Exclude<VolumeKind, 'music'>
let ctx: AudioContext | undefined
let buses: Record<Bus, GainNode> | undefined
let sounds: Partial<Record<UiSound, AudioBuffer>> = {}
let loading: Promise<void> | undefined
let speaking: EvaSound | undefined
const evaQueue: EvaSound[] = []
/** Unit responses from SOUNDS.MIX, decoded on first use */
let soundsMix: Promise<MixArchive | undefined> | undefined
const voiceCache = new Map<string, Promise<AudioBuffer | undefined>>()
let talking: AudioBufferSourceNode | undefined
/** The game is paused: EVA, the effects and the radar transmission hold where they are */
const held = ref(false)

export function useUiSounds() {
  const settings = useSettings()
  if (!loading) {
    ctx = new AudioContext()
    // detached: the volumes keep following the settings after the component that first
    // played a sound is gone
    const scope = effectScope(true)
    const bus = (kind: Bus) => {
      const node = ctx!.createGain()
      node.connect(ctx!.destination)
      scope.run(() => watch(() => volumeOf(kind), (value) => {
        node.gain.value = value
      }, { immediate: true }))
      return node
    }
    buses = { shots: bus('shots'), effects: bus('effects'), voices: bus('voices') }
    loading = getAssetStore()
      .then(store => loadUiSounds(ctx!, store))
      .then((loaded) => {
        sounds = loaded
      })
      .catch(() => {})
  }

  /** Plays an interface sound (or an EVA message), at `volume` (0 … 1) of the volume of its kind */
  function play(name: UiSound, volume = 1, kind: Bus = 'effects') {
    const buffer = sounds[name]
    if (!ctx || !buses || !buffer) return undefined
    const gain = buses[kind]
    if (!held.value) ctx.resume().catch(() => {})
    const source = ctx.createBufferSource()
    source.buffer = buffer
    if (volume === 1) {
      source.connect(gain)
    }
    else {
      const level = ctx.createGain()
      level.gain.value = volume
      source.connect(level).connect(gain)
    }
    source.start()
    return source
  }

  /**
   * EVA speaks one message at a time like in the original: a new one waits until the
   * current one has ended; the same message is not queued twice.
   */
  function speak(name: EvaSound) {
    if (speaking === name || evaQueue.includes(name)) return
    if (speaking) {
      evaQueue.push(name)
      return
    }
    const source = play(name, 1, 'voices')
    if (!source) return
    speaking = name
    source.onended = () => {
      speaking = undefined
      const next = evaQueue.shift()
      if (next) speak(next)
    }
  }

  /**
   * Says a message now (cutting off what EVA says) and resolves when it has been said;
   * without the sound after `fallback` seconds, so the game never waits forever.
   */
  async function speakNow(name: EvaSound, fallback = 3) {
    await loading
    evaQueue.length = 0
    const source = play(name, 1, 'voices')
    if (!source) {
      await new Promise(resolve => setTimeout(resolve, fallback * 1000))
      return
    }
    speaking = name
    await new Promise<void>((resolve) => {
      source.onended = () => {
        speaking = undefined
        resolve()
      }
    })
  }

  /** One of `files` from SOUNDS.MIX (picked at random), decoded on first use */
  async function soundFile(files: string[]) {
    const file = files[Math.floor(Math.random() * files.length)]
    if (!file || !ctx) return undefined
    soundsMix ??= getAssetStore()
      .then(store => store.get('TIBSUN.MIX'))
      .then(blob => blob && MixArchive.open(blob, 'TIBSUN.MIX'))
      .then(archive => archive?.openNested('SOUNDS.MIX'))
    const name = `${file.toUpperCase()}.AUD`
    if (!voiceCache.has(name)) {
      voiceCache.set(name, soundsMix.then(mix => mix?.read(name)).then(bytes => bytes && toAudioBuffer(ctx!, decodeAud(bytes))).catch(() => undefined))
    }
    return voiceCache.get(name)
  }

  function start(buffer: AudioBuffer, kind: Bus) {
    if (!held.value) ctx!.resume().catch(() => {})
    const source = ctx!.createBufferSource()
    source.buffer = buffer
    source.connect(buses![kind])
    source.start()
    return source
  }

  /**
   * A unit's spoken response (one of `files`, picked at random). Like in the original
   * only one unit talks at a time: a new response cuts off the last one.
   */
  async function respond(files: string[]) {
    const buffer = await soundFile(files)
    if (!buffer || !buses) return
    talking?.stop()
    talking = start(buffer, 'voices')
  }

  /** A sound from SOUNDS.MIX at the volume of its kind (shots, death cries …); several may play at once */
  async function effect(files: string[], kind: Bus = 'effects') {
    const buffer = await soundFile(files)
    if (buffer && buses) start(buffer, kind)
  }

  /** The shared audio context and the volume of a kind of sound, e.g. for the sound of videos */
  function output(kind: Bus = 'effects') {
    return ctx && buses ? { ctx, gain: buses[kind] } : undefined
  }

  /** Pauses (or resumes) all sounds of the game on this context */
  function hold(on: boolean) {
    held.value = on
    if (on) ctx?.suspend().catch(() => {})
    else ctx?.resume().catch(() => {})
  }

  return { play, speak, speakNow, respond, effect, output, held, hold }
}
