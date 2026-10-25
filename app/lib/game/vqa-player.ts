import { toAudioBuffer } from '../formats/aud'
import { decodeVqaAudio } from '../formats/vqa'
import { VqaVideo } from '../formats/vqa-video'

/**
 * Plays a VQA video into a canvas, with its sound: the picture follows the audio clock,
 * so both stay in step (frames are skipped if decoding falls behind).
 */
export class VqaPlayback {
  private readonly video: VqaVideo
  private source?: AudioBufferSourceNode
  private started = 0
  private shown = -1
  private running = false
  private finish?: () => void
  readonly done: Promise<void>

  constructor(
    bytes: Uint8Array,
    private readonly canvas: HTMLCanvasElement,
    private readonly ctx: AudioContext,
    private readonly output: AudioNode,
  ) {
    this.video = new VqaVideo(bytes)
    canvas.width = this.video.header.width
    canvas.height = this.video.header.height
    let sound: AudioBuffer | undefined
    try {
      sound = this.video.header.channels ? toAudioBuffer(ctx, decodeVqaAudio(bytes)) : undefined
    }
    catch {}
    this.done = new Promise((resolve) => {
      this.finish = resolve
    })
    if (sound) {
      this.source = ctx.createBufferSource()
      this.source.buffer = sound
      this.source.connect(output)
    }
  }

  get width() {
    return this.video.header.width
  }

  get height() {
    return this.video.header.height
  }

  /** Seconds the video lasts */
  get duration() {
    return this.video.frameCount / (this.video.header.fps || 15)
  }

  start() {
    this.ctx.resume().catch(() => {})
    this.started = this.ctx.currentTime
    this.source?.start()
    this.running = true
    requestAnimationFrame(this.frame)
  }

  stop() {
    if (!this.running) return
    this.running = false
    try {
      this.source?.stop()
    }
    catch {}
    this.finish?.()
  }

  private readonly frame = () => {
    if (!this.running) return
    const elapsed = this.ctx.state === 'running' ? this.ctx.currentTime - this.started : 0
    const want = Math.min(this.video.frameCount - 1, Math.floor(elapsed * (this.video.header.fps || 15)))
    if (want > this.shown) {
      // catch up to the frame the sound is at
      while (this.shown < want && this.video.decodeNext()) this.shown++
      const ctx2d = this.canvas.getContext('2d')!
      ctx2d.putImageData(new ImageData(this.video.rgba, this.width, this.height), 0, 0)
    }
    if (elapsed >= this.duration) {
      this.stop()
      return
    }
    requestAnimationFrame(this.frame)
  }
}
