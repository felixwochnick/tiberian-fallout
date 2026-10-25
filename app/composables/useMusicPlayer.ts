import { decodeAud, toAudioBuffer } from '~/lib/formats/aud'
import { loadSoundtrack, type Track } from '~/lib/game/soundtrack'
import { getAssetStore } from '~/lib/storage/asset-store'

let ctx: AudioContext | undefined
let gain: GainNode | undefined
let source: AudioBufferSourceNode | undefined
const bufferCache = new Map<string, AudioBuffer>()

export function useMusicPlayer() {
  const tracks = useState<Track[]>('music:tracks', () => [])
  const current = useState<string | null>('music:current', () => null)
  const playing = useState('music:playing', () => false)
  const loading = useState('music:loading', () => false)
  const volume = useState('music:volume', () => 0.7)
  const error = useState<string | null>('music:error', () => null)
  /** Pick the next track at random (in-game) instead of in list order */
  const shuffle = useState('music:shuffle', () => false)

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

  async function play(track: Track) {
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
      gain.gain.value = volume.value
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
      source.onended = () => next()
      source.start()
      playing.value = true
    }
    catch (e) {
      error.value = `„${track.title}“ konnte nicht abgespielt werden: ${e instanceof Error ? e.message : e}`
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

  /** Any track but the current one. */
  function playRandom() {
    const others = tracks.value.filter(t => t.id !== current.value)
    const pick = others[Math.floor(Math.random() * others.length)] ?? tracks.value[0]
    if (pick) return play(pick)
  }

  watch(volume, (v) => {
    if (gain) gain.gain.value = v
  })

  return { tracks, current, playing, loading, volume, error, shuffle, loadTracks, play, stop, next, playRandom }
}
