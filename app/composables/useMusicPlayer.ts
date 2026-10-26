import { decodeAud, toAudioBuffer } from '~/lib/formats/aud'
import { loadSoundtrack, type Track } from '~/lib/game/soundtrack'
import { getAssetStore } from '~/lib/storage/asset-store'

let ctx: AudioContext | undefined
let gain: GainNode | undefined
let source: AudioBufferSourceNode | undefined
const bufferCache = new Map<string, AudioBuffer>()
/** Themes the original plays quieter than the soundtrack (share of the music volume) */
const THEME_LEVELS: Record<string, number> = { 'MAPS.AUD': 0.2 }
/** Level of the track playing now */
let level = 1

export function useMusicPlayer() {
  const tracks = useState<Track[]>('music:tracks', () => [])
  const current = useState<string | null>('music:current', () => null)
  const playing = useState('music:playing', () => false)
  const loading = useState('music:loading', () => false)
  const volume = useState('music:volume', () => 0.7)
  const error = useState<string | null>('music:error', () => null)
  /** Pick the next track at random (in-game) instead of in list order */
  const shuffle = useState('music:shuffle', () => false)
  /** The in-game play list: without the themes of the menu and the screens (MAPS, SCORE, …) */
  const playlist = computed(() => tracks.value.filter(t => t.normal))

  async function loadTracks() {
    error.value = null
    try {
      tracks.value = (await loadSoundtrack(await getAssetStore())).map(track => markRaw(track))
    }
    catch (e) {
      tracks.value = []
      error.value = e instanceof Error ? e.message : String(e)
    }
  }

  function stop() {
    if (source) {
      source.onended = null
      source.stop()
      source.disconnect()
      source = undefined
    }
    playing.value = false
  }

  /** Plays a track; `loop` repeats it endlessly instead of going on to the next */
  async function play(track: Track, loop = false) {
    stop()
    error.value = null
    loading.value = true
    current.value = track.id
    try {
      ctx ??= new AudioContext()
      if (!gain) {
        gain = ctx.createGain()
        gain.connect(ctx.destination)
      }
      level = THEME_LEVELS[track.filename ?? ''] ?? 1
      gain.gain.value = volume.value * level
      await ctx.resume()

      let buffer = bufferCache.get(track.id)
      if (!buffer) {
        const bytes = await track.archive.read(track.entry)
        buffer = toAudioBuffer(ctx, decodeAud(bytes!))
        bufferCache.set(track.id, buffer)
      }
      if (current.value !== track.id) return

      source = ctx.createBufferSource()
      source.buffer = buffer
      source.connect(gain)
      source.loop = loop
      if (!loop) source.onended = () => next()
      source.start()
      playing.value = true
    }
    catch (e) {
      error.value = `„${track.title}“ konnte nicht abgespielt werden: ${e instanceof Error ? e.message : e}`
      console.warn(error.value, e)
    }
    finally {
      loading.value = false
    }
  }

  function next() {
    const list = tracks.value
    if (!list.length) return
    if (shuffle.value) return playRandom()
    const index = list.findIndex(t => t.id === current.value)
    play(list[(index + 1) % list.length]!)
  }

  /** Any track of the play list but the current one. */
  function playRandom() {
    const others = playlist.value.filter(t => t.id !== current.value)
    const pick = others[Math.floor(Math.random() * others.length)] ?? playlist.value[0]
    if (pick) return play(pick)
  }

  /** Plays one of the game's themes (THEME.INI id, e.g. 'MAPS'); false if it is not there */
  function playTheme(id: string, loop = false) {
    const track = tracks.value.find(t => t.filename === `${id.toUpperCase()}.AUD`)
    if (!track) return false
    if (current.value !== track.id || !playing.value) play(track, loop)
    return true
  }

  watch(volume, (v) => {
    if (gain) gain.gain.value = v * level
  })

  return { tracks, playlist, current, playing, loading, volume, error, shuffle, loadTracks, play, playTheme, stop, next, playRandom }
}
