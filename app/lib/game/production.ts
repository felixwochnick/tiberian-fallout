import type { BuildInfo } from './cameos'

/**
 * Production of the sidebar like in Tiberian Sun: one structure at a time and a queue
 * of units. The price is paid bit by bit while the clock runs; without money the
 * clock stops. A finished structure waits ("Bereit") until it is placed, a finished
 * unit leaves its factory at once. Jobs can be put on hold and cancelled (the money
 * spent so far comes back).
 */

export type JobState = 'building' | 'paused' | 'ready'

export interface Job {
  info: BuildInfo
  /** 0 … 1 */
  progress: number
  /** Credits paid so far */
  paid: number
  state: JobState
}

/** Most units waiting in the queue */
export const MAX_QUEUE = 15

export class Production {
  structure?: Job = undefined
  /** Units in order; the first one is being built */
  units: Job[] = []

  /** Set when a running job stopped for lack of money (for "Insufficient funds") */
  starved = false

  constructor(
    private readonly onUnitDone: (info: BuildInfo) => void,
    private readonly onStructureDone: (info: BuildInfo) => void = () => {},
  ) {}

  /** The job shown on a cameo: the structure or the first unit of that kind */
  jobFor(id: string) {
    if (this.structure?.info.id === id) return this.structure
    return this.units.find(job => job.info.id === id)
  }

  /** How many units of that kind are queued (including the one being built) */
  queued(id: string) {
    return this.units.filter(job => job.info.id === id).length
  }

  /**
   * Left click on a cameo: starts building, or continues a job on hold. Returns false
   * if nothing could be started (another structure is being built, queue full).
   */
  start(info: BuildInfo) {
    const job = this.jobFor(info.id)
    if (job?.state === 'paused') {
      job.state = 'building'
      return true
    }
    if (info.structure) {
      if (this.structure) return false
      this.structure = { info, progress: 0, paid: 0, state: 'building' }
      return true
    }
    if (this.units.length >= MAX_QUEUE) return false
    this.units.push({ info, progress: 0, paid: 0, state: 'building' })
    return true
  }

  /**
   * Right click on a cameo: puts a running job on hold; a job on hold or a finished
   * structure is cancelled. Returns the credits to give back.
   */
  hold(id: string) {
    const job = this.jobFor(id)
    if (!job) return 0
    if (job.state === 'building' && job.progress > 0) {
      job.state = 'paused'
      return 0
    }
    return this.cancel(job)
  }

  /** Removes a job (for units the last queued one of its kind) and returns its payment. */
  cancel(job: Job) {
    if (job === this.structure) {
      this.structure = undefined
      return job.paid
    }
    // queued units of that kind go first, the one in work last
    const index = this.units.map(j => j.info.id).lastIndexOf(job.info.id)
    const [removed] = this.units.splice(index, 1)
    return removed?.paid ?? 0
  }

  /** The finished structure was placed. */
  placed() {
    if (this.structure?.state === 'ready') this.structure = undefined
  }

  /**
   * Advances the running jobs by `seconds` at `speed` (game speed × power) and pays for
   * them from `credits`.
   */
  tick(seconds: number, speed: number, credits: { value: number }) {
    const advance = (job: Job) => {
      if (job.state !== 'building') return false
      let step = (seconds * speed) / Math.max(job.info.seconds, 0.1)
      step = Math.min(step, 1 - job.progress)
      const price = step * job.info.cost
      if (price > credits.value) {
        step = job.info.cost ? credits.value / job.info.cost : step
        this.starved = true
      }
      const paid = step * job.info.cost
      credits.value -= paid
      job.paid += paid
      job.progress += step
      return job.progress >= 1 - 1e-6
    }
    if (this.structure && advance(this.structure)) {
      this.structure.progress = 1
      this.structure.state = 'ready'
      this.onStructureDone(this.structure.info)
    }
    const unit = this.units[0]
    if (unit && advance(unit)) {
      this.units.shift()
      this.onUnitDone(unit.info)
    }
  }
}
