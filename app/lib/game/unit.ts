import * as THREE from 'three'

/** How fast a unit turns towards where it walks (radians per second) */
const TURN_SPEED = 9
/** Cross-fade between the animations (seconds) */
const FADE = 0.2
/** Seconds infantry stays down after the last shot at it, then stands up again */
const PRONE_SECONDS = 4
/** Crawling is slower than walking */
const CRAWL_FACTOR = 0.5

/**
 * standing: Idle / Walk; diving: GoProne; prone: Prone / Crawl; rising: GoProne backwards.
 * Units do not move while diving or rising.
 */
type Stance = 'standing' | 'diving' | 'prone' | 'rising'

/**
 * An infantry unit on the battlefield: a skinned model with the looped clips "Idle"
 * (standing) and "Walk" (in place). It walks in a straight line to a target on the
 * ground, turned towards it, and stands again when it arrives.
 *
 * Like in the original, infantry under fire throws itself down (clip "GoProne"),
 * lies ("Prone") and crawls ("Crawl") at half speed when it moves, and gets up again
 * a few seconds after the last shot at it. Models without these clips stay standing.
 */
export class Unit {
  private readonly mixer: THREE.AnimationMixer
  private readonly idle?: THREE.AnimationAction
  private readonly walk?: THREE.AnimationAction
  private readonly goProne?: THREE.AnimationAction
  private readonly lying?: THREE.AnimationAction
  private readonly crawl?: THREE.AnimationAction
  /** The looped animation playing now */
  private current?: THREE.AnimationAction
  private target?: THREE.Vector3
  /** Waypoints still to walk after the current target (from pathfinding) */
  private route: THREE.Vector3[] = []
  private stance: Stance = 'standing'
  /** Seconds left lying down before it stands up */
  private proneTime = 0
  /** Ground speed in cells per second; the model's own (feet don't slide) unless given */
  readonly speed: number

  constructor(readonly object: THREE.Object3D, clips: THREE.AnimationClip[], speed?: number) {
    this.mixer = new THREE.AnimationMixer(object)
    const action = (name: string) => {
      const clip = clips.find(c => c.name === name)
      return clip && this.mixer.clipAction(clip)
    }
    this.idle = action('Idle')
    this.walk = action('Walk')
    this.lying = action('Prone')
    this.crawl = action('Crawl')
    this.goProne = action('GoProne')
    this.goProne?.setLoop(THREE.LoopOnce, 1)
    if (this.goProne) this.goProne.clampWhenFinished = true
    this.mixer.addEventListener('finished', (event) => {
      if (event.action !== this.goProne) return
      this.stance = this.stance === 'diving' ? 'prone' : 'standing'
      this.play(this.loop)
    })
    this.current = this.idle
    this.idle?.play()
    // the model tells at which speed its walk cycle matches the ground
    let modelSpeed: number | undefined
    object.traverse((node) => {
      modelSpeed ??= node.userData.walkSpeed
    })
    this.speed = speed ?? modelSpeed ?? 0.25
    // the walk cycle runs faster or slower with the speed, so the feet stay on the ground
    if (this.walk && modelSpeed) this.walk.timeScale = this.speed / modelSpeed
  }

  get walking() {
    return !!this.target
  }

  /** Lying on the ground (or throwing itself down): harder to hit */
  get prone() {
    return this.stance === 'prone' || this.stance === 'diving'
  }

  /** Where it is walking to in the end, if anywhere */
  get destination() {
    return this.route.at(-1) ?? this.target
  }

  /** Walks (or crawls) straight to a point on the ground (world coordinates). */
  walkTo(target: THREE.Vector3) {
    this.followPath([target])
  }

  /** Walks along waypoints (from pathfinding), one after the other. */
  followPath(points: THREE.Vector3[]) {
    const [first, ...rest] = points
    if (!first) {
      this.stop()
      return
    }
    this.target = first.clone().setY(this.object.position.y)
    this.route = rest.map(p => p.clone().setY(this.object.position.y))
    this.play(this.loop)
  }

  /** Turns towards a point while standing (aiming); `seconds` limits how far it turns this frame. */
  face(point: THREE.Vector3, seconds: number) {
    const way = point.clone().sub(this.object.position)
    const heading = Math.atan2(way.x, way.z)
    const turn = THREE.MathUtils.euclideanModulo(heading - this.object.rotation.y + Math.PI, 2 * Math.PI) - Math.PI
    this.object.rotation.y += THREE.MathUtils.clamp(turn, -TURN_SPEED * seconds, TURN_SPEED * seconds)
    return Math.abs(turn) < 0.25
  }

  /** Stops where it is. */
  stop() {
    this.target = undefined
    this.route = []
    this.play(this.loop)
  }

  /** It is being shot at: down on the ground, and it stays down a while longer. */
  takeFire() {
    const dive = this.goProne
    if (!dive || !this.lying) return
    this.proneTime = PRONE_SECONDS
    if (this.stance === 'standing') {
      this.stance = 'diving'
      dive.reset()
      dive.timeScale = 1
      this.fadeTo(dive)
    }
    else if (this.stance === 'rising') {
      // back down from where getting up has got to
      this.stance = 'diving'
      dive.timeScale = 1
    }
  }

  update(seconds: number) {
    if (this.stance === 'prone') {
      this.proneTime -= seconds
      if (this.proneTime <= 0) this.rise()
    }
    const moving = this.stance === 'standing' || this.stance === 'prone'
    if (this.target && moving) {
      const position = this.object.position
      const way = this.target.clone().sub(position)
      const distance = way.length()
      const step = this.speed * (this.stance === 'prone' ? CRAWL_FACTOR : 1) * seconds
      if (distance <= step) {
        position.copy(this.target)
        // on to the next waypoint, or arrived
        const next = this.route.shift()
        if (next) this.target = next
        else this.stop()
      }
      else {
        position.addScaledVector(way, step / distance)
        // the model looks along +Z: turn the short way round towards the target
        this.face(this.target, seconds)
      }
    }
    this.mixer.update(seconds)
  }

  /** Gets up: the dive played backwards. */
  private rise() {
    const dive = this.goProne!
    this.stance = 'rising'
    dive.reset()
    dive.timeScale = -1
    dive.time = dive.getClip().duration
    this.fadeTo(dive)
  }

  /** The looped animation for the stance and whether it moves */
  private get loop() {
    if (this.stance === 'prone') return this.target ? this.crawl : this.lying
    if (this.stance === 'standing') return this.target ? this.walk : this.idle
    return undefined // diving / rising: the transition plays on, the loop follows when it ends
  }

  private play(action?: THREE.AnimationAction) {
    if (!action || action === this.current) return
    action.reset()
    this.fadeTo(action)
  }

  private fadeTo(action: THREE.AnimationAction) {
    action.play()
    if (this.current && this.current !== action) action.crossFadeFrom(this.current, FADE, false)
    this.current = action
  }

  dispose() {
    this.mixer.stopAllAction()
    this.mixer.uncacheRoot(this.object)
  }
}
