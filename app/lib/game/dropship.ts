import * as THREE from 'three'

/** Cruising speed (cells per second) */
const SPEED = 2.6
/** Distance (cells) over which it slows down before landing */
const BRAKE = 3
/** Seconds it stays on the ground after unloading */
const WAIT = 1.2
/** Seconds the wreck burns before it is taken away */
const WRECK_SECONDS = 8
/** How fast it turns towards where it flies (radians per second) */
const TURN_SPEED = 1.8
/** Seconds into the Crash clip when the ship hits the ground (frame 62 at 30 fps) */
const IMPACT = 62 / 30

type State = 'arriving' | 'landing' | 'unloading' | 'waiting' | 'takingOff' | 'leaving' | 'crashing' | 'gone'

/** Moments that have a sound: it starts to land or to take off, its wreck hits the ground */
export type DropshipSound = 'land' | 'takeOff' | 'impact'

export interface DropshipFlight {
  /** Where it lands (world, on the ground) */
  to: THREE.Vector3
  /** Where it flies off to after unloading, usually beyond the map edge */
  leave: THREE.Vector3
  /** Called once it has landed, with the point at the end of its ramp; it takes off
   *  when the returned promise has settled */
  unload: (exit: THREE.Vector3) => Promise<unknown> | void
}

/**
 * The GDI dropship (model DSHP.glb): flies in at its cruising height, lands, lets the
 * cargo out over its ramp, takes off and flies away. The model's clips carry the
 * height and the engines (Fly, Land, Landed, TakeOff, Crash, and Lights all the time);
 * this moves it over the ground and plays them in turn.
 */
export class Dropship {
  private readonly mixer: THREE.AnimationMixer
  private readonly actions = new Map<string, THREE.AnimationAction>()
  private current?: THREE.AnimationAction
  private state: State = 'arriving'
  private timer = 0
  /** Called when the ship has left the map or its wreck has burnt out */
  onGone?: () => void
  /** Called when something happens that makes a sound */
  onSound?: (sound: DropshipSound) => void

  constructor(readonly object: THREE.Object3D, clips: THREE.AnimationClip[], private readonly flight: DropshipFlight) {
    this.mixer = new THREE.AnimationMixer(object)
    for (const clip of clips) {
      const action = this.mixer.clipAction(clip)
      if (clip.name !== 'Fly' && clip.name !== 'Landed' && clip.name !== 'Lights') {
        action.setLoop(THREE.LoopOnce, 1)
        action.clampWhenFinished = true
      }
      this.actions.set(clip.name, action)
    }
    this.actions.get('Lights')?.play()
    this.mixer.addEventListener('finished', event => this.finished(event.action))
    this.play('Fly')
    this.face(flight.to, Infinity)
    this.mixer.update(0)
  }

  get flying() {
    return this.state !== 'gone' && this.state !== 'crashing'
  }

  /** Shot down: it spirals to the ground and burns out. */
  crash() {
    if (!this.flying) return
    this.state = 'crashing'
    this.play('Crash')
  }

  update(seconds: number) {
    const position = this.object.position
    switch (this.state) {
      case 'arriving': {
        const way = this.flight.to.clone().sub(position).setY(0)
        const distance = way.length()
        // full speed, slowing down over the last cells
        const speed = SPEED * Math.min(1, Math.max(0.2, distance / BRAKE))
        if (distance <= speed * seconds) {
          position.copy(this.flight.to)
          this.state = 'landing'
          this.play('Land')
        }
        else {
          position.addScaledVector(way, (speed * seconds) / distance)
          this.face(this.flight.to, seconds)
        }
        break
      }
      case 'waiting':
        this.timer -= seconds
        if (this.timer <= 0) {
          this.state = 'takingOff'
          this.play('TakeOff')
        }
        break
      case 'leaving': {
        const way = this.flight.leave.clone().sub(position).setY(0)
        const distance = way.length()
        this.timer += seconds
        const speed = SPEED * Math.min(1, 0.2 + this.timer / 2) // picks up speed
        if (distance <= speed * seconds) this.gone()
        else {
          position.addScaledVector(way, (speed * seconds) / distance)
          this.face(this.flight.leave, seconds)
        }
        break
      }
      case 'crashing':
        // the clip spins it down and lets it slide; the wreck burns a while
        if (this.timer < IMPACT && this.timer + seconds >= IMPACT) this.onSound?.('impact')
        this.timer += seconds
        if (this.timer > WRECK_SECONDS) this.gone()
        break
    }
    this.mixer.update(seconds)
  }

  private finished(action: THREE.AnimationAction) {
    const name = action.getClip().name
    if (name === 'Land' && this.state === 'landing') {
      this.state = 'unloading'
      this.play('Landed')
      const exit = new THREE.Vector3()
      ;(this.object.getObjectByName('CargoExit') ?? this.object).getWorldPosition(exit)
      exit.y = 0
      Promise.resolve(this.flight.unload(exit)).catch(() => {}).finally(() => {
        if (this.state !== 'unloading') return
        this.state = 'waiting'
        this.timer = WAIT
      })
    }
    else if (name === 'TakeOff' && this.state === 'takingOff') {
      this.state = 'leaving'
      this.timer = 0
      this.play('Fly')
    }
  }

  private play(name: string) {
    const action = this.actions.get(name)
    if (!action) return
    // the clips start where the one before ends, so they simply take over
    this.current?.stop()
    action.reset().play()
    this.current = action
    if (name === 'Crash') this.timer = 0
    else if (name === 'Land') this.onSound?.('land')
    else if (name === 'TakeOff') this.onSound?.('takeOff')
  }

  /** Turns the nose (+Z) towards a point. */
  private face(point: THREE.Vector3, seconds: number) {
    const way = point.clone().sub(this.object.position)
    if (way.lengthSq() < 1e-6) return
    const heading = Math.atan2(way.x, way.z)
    const turn = THREE.MathUtils.euclideanModulo(heading - this.object.rotation.y + Math.PI, 2 * Math.PI) - Math.PI
    this.object.rotation.y += THREE.MathUtils.clamp(turn, -TURN_SPEED * seconds, TURN_SPEED * seconds)
  }

  private gone() {
    this.state = 'gone'
    this.mixer.stopAllAction()
    this.onGone?.()
  }

  dispose() {
    this.mixer.stopAllAction()
    this.mixer.uncacheRoot(this.object)
  }
}
