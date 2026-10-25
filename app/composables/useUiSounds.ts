import { decodeAud, toAudioBuffer } from '~/lib/formats/aud'
import { MixArchive } from '~/lib/formats/mix'
import { type EvaSound, loadUiSounds, type UiSound } from '~/lib/menu/audio'
import { getAssetStore } from '~/lib/storage/asset-store'

/**
 * Interface sounds of the game (clicks, radar …) on one shared audio context,
 * at the volume of the "Effekte" setting. Loaded once on first use.
 */
let ctx: AudioContext | undefined
let gain: GainNode | undefined
let sounds: Partial<Record<UiSound, AudioBuffer>> = {}
let loading: Promise<void> | undefined
let speaking: EvaSound | undefined
const evaQueue: EvaSound[] = []
/** Unit responses from SOUNDS.MIX, decoded on first use */
let soundsMix: Promise<MixArchive | undefined> | undefined
const voiceCache = new Map<string, Promise<AudioBuffer | undefined>>()
let talking: AudioBufferSourceNode | undefined

export function useUiSounds() {
  const settings = useSettings()
  if (!loading) {
    ctx = new AudioContext()
    gain = ctx.createGain()
    gain.connect(ctx.destination)
    watch(() => settings.effects, (value) => {
      if (gain) gain.gain.value = value / 100
    }, { immediate: true })
    loading = getAssetStore()
      .then(store => loadUiSounds(ctx!, store))
      .then((loaded) => {
        sounds = loaded
      })
      .catch(() => {})
  }

  /** Plays an interface sound, at `volume` (0 … 1) of the effects volume */
  function play(name: UiSound, volume = 1) {
    const buffer = sounds[name]
    if (!ctx || !gain || !buffer) return undefined
    ctx.resume().catch(() => {})
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
    const source = play(name)
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
    const source = play(name)
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

  function start(buffer: AudioBuffer) {
    ctx!.resume().catch(() => {})
    const source = ctx!.createBufferSource()
    source.buffer = buffer
    source.connect(gain!)
    source.start()
    return source
  }

  /**
   * A unit's spoken response (one of `files`, picked at random). Like in the original
   * only one unit talks at a time: a new response cuts off the last one.
   */
  async function respond(files: string[]) {
    const buffer = await soundFile(files)
    if (!buffer || !gain) return
    talking?.stop()
    talking = start(buffer)
  }

  /** A sound effect from SOUNDS.MIX (shots, death cries); several may play at once */
  async function effect(files: string[]) {
    const buffer = await soundFile(files)
    if (buffer && gain) start(buffer)
  }

  /** The shared audio context and the effects volume, e.g. for the sound of videos */
  function output() {
    return ctx && gain ? { ctx, gain } : undefined
  }

  return { play, speak, speakNow, respond, effect, output }
}
