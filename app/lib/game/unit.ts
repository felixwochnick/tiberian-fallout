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
 * standing: Idle / Walk; diving: GoProne; prone: Prone / Crawl; rising: GoProne backwards;
 * dead: a death clip, held on its last frame. Units do not move while diving or rising.
 */
type Stance = 'standing' | 'diving' | 'prone' | 'rising' | 'dead'

/** How a soldier dies (its clips): shot, blown up by an explosion; lying down it always goes limp (DieProne) */
export type Death = 'Die1' | 'Die2'
/** The fall into the death clip is quicker than the other cross-fades */
const DEATH_FADE = 0.08

/**
 * An infantry unit on the battlefield: a skinned model with the looped clips "Idle"
 * (standing) and "Walk" (in place). It walks in a straight line to a target on the
 * ground, turned towards it, and stands again when it arrives.
 *
 * Like in the original, infantry under fire throws itself down (clip "GoProne"),
 * lies ("Prone") and crawls ("Crawl") at half speed when it moves, and gets up again
 * a few seconds after the last shot at it. Models without these clips stay standing.
 *
 * Killed, it plays a death clip once and lies still (die()): "Die1" shot, "Die2"
 * blown up, "DieProne" when it was lying down.
 *
 * Models with a clip "Fire" (the walkers: spinning barrels, recoil, their own muzzle
 * flashes) play it once per shot, standing, and go back to Idle after it.
 *
 * Other clips of a model (the harvester's Harvest and Unload) are played on demand
 * with perform(); drive() plays the Walk clip, also backwards, while something else
 * moves the unit (the harvester backing into its refinery).
 *
 * Some vehicles take up a posture (the Tick Tank dug in, "Deployed"; the subterranean
 * APC under the ground, "Underground"): change() plays the clip into it once (Deploy,
 * Burrow …), the unit does not move meanwhile; then the clip named like the posture is
 * its idle loop and "Fire<Posture>" its shot, until change() leads out of it again.
 */
export class Unit {
  private readonly mixer: THREE.AnimationMixer
  private readonly idle?: THREE.AnimationAction
  private readonly walk?: THREE.AnimationAction
  private readonly goProne?: THREE.AnimationAction
  private readonly lying?: THREE.AnimationAction
  private readonly crawl?: THREE.AnimationAction
  private readonly shoot?: THREE.AnimationAction
  /** The Fire clip playing now (the posture's own, or Fire) */
  private shot?: THREE.AnimationAction
  /** The looped animation playing now */
  private current?: THREE.AnimationAction
  private target?: THREE.Vector3
  /** Waypoints still to walk after the current target (from pathfinding) */
  private route: THREE.Vector3[] = []
  private stance: Stance = 'standing'
  /** Seconds left lying down before it stands up */
  private proneTime = 0
  /** The posture it has taken up (its own idle and fire clips), if any */
  private postureName?: string
  /** The clip into or out of a posture playing now, and what follows it */
  private changing?: { action: THREE.AnimationAction, posture?: string, done: () => void, finished: Promise<void> }
  /** Ground speed in cells per second; the model's own (feet don't slide) unless given */
  readonly speed: number

  constructor(readonly object: THREE.Object3D, private readonly clips: THREE.AnimationClip[], speed?: number) {
    this.mixer = new THREE.AnimationMixer(object)
    const action = (name: string) => this.action(name)
    this.idle = action('Idle')
    this.walk = action('Walk')
    this.lying = action('Prone')
    this.crawl = action('Crawl')
    this.goProne = action('GoProne')
    this.shoot = action('Fire')
    this.shoot?.setLoop(THREE.LoopOnce, 1)
    this.goProne?.setLoop(THREE.LoopOnce, 1)
    if (this.goProne) this.goProne.clampWhenFinished = true
    this.mixer.addEventListener('finished', (event) => {
      if (this.stance === 'dead') return
      const changing = this.changing
      if (changing && event.action === changing.action) {
        this.changing = undefined
        this.postureName = changing.posture
        this.current = undefined
        this.fadeFrom(changing.action, this.loop)
        changing.done()
        return
      }
      if (event.action === this.shot) {
        if (this.current === this.shot) {
          this.current = undefined
          this.fadeFrom(this.shot, this.loop)
        }
        return
      }
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

  /** The posture it has taken up (Deployed, Underground …), if any */
  get posture() {
    return this.postureName
  }

  /** Whether it is changing its posture now (it cannot move or fire meanwhile) */
  get changingPosture() {
    return !!this.changing
  }

  /**
   * Plays the model's clip `clip` once (Deploy, Undeploy, Burrow, Surface …) and then
   * takes up `posture` (undefined: none, back to Idle). It stops where it is and does
   * not move meanwhile. Resolves when it is done; at once if the model has no such clip
   * (it just takes up the posture). The same change asked again waits for the one on.
   */
  change(clip: string, posture: string | undefined): Promise<void> {
    if (this.changing) return this.changing.finished.then(() => this.postureName === posture ? undefined : this.change(clip, posture))
    const action = this.action(clip)
    this.target = undefined
    this.route = []
    if (!action || this.stance === 'dead') {
      this.postureName = posture
      this.play(this.loop)
      return Promise.resolve()
    }
    let done!: () => void
    const finished = new Promise<void>((resolve) => {
      done = resolve
    })
    this.changing = { action, posture, done, finished }
    action.reset()
    action.setLoop(THREE.LoopOnce, 1)
    action.clampWhenFinished = true
    this.fadeTo(action)
    return finished
  }

  private action(name: string) {
    const clip = this.clips.find(c => c.name === name)
    return clip && this.mixer.clipAction(clip)
  }

  /**
   * Plays one of the model's clips instead of Idle (looped, or once and then holding
   * its last pose); it lasts until the unit walks or rest() is called. Returns the
   * clip's length in seconds, undefined if the model has no such clip.
   */
  perform(name: string, loop = true) {
    const action = this.action(name)
    if (!action) return undefined
    if (action !== this.current) {
      action.reset()
      action.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, Infinity)
      action.clampWhenFinished = !loop
      this.fadeTo(action)
    }
    return action.getClip().duration
  }

  /** Back to Idle (or what fits the stance) after perform() or drive(). */
  rest() {
    if (this.walk) this.walk.timeScale = Math.abs(this.walk.timeScale)
    this.play(this.loop)
  }

  /** Plays the Walk clip, forwards or backwards, while the unit is moved from outside. */
  drive(reverse = false) {
    if (!this.walk) return
    this.walk.timeScale = Math.abs(this.walk.timeScale) * (reverse ? -1 : 1)
    this.play(this.walk)
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
    // dug in or changing its posture: it does not drive (see Battlefield.walk)
    if (this.changing || this.postureName) return
    if (!first) {
      this.stop()
      return
    }
    if (this.walk) this.walk.timeScale = Math.abs(this.walk.timeScale)
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

  /**
   * A shot: plays the model's Fire clip from the start, when it has one and stands.
   * Returns whether it did (the model then shows its own muzzle flash).
   */
  fire() {
    const shoot = this.postureName ? this.action(`Fire${this.postureName}`) : this.shoot
    if (!shoot || this.stance !== 'standing' || this.target || this.changing) return false
    shoot.setLoop(THREE.LoopOnce, 1)
    // it holds its last frame while the loop fades in after it: else for a moment
    // nothing would pose the model (a dug-in Tick Tank would fall back flat)
    shoot.clampWhenFinished = true
    this.shot = shoot
    // straight in, no cross-fade: the flash is on the first frames
    if (this.current && this.current !== shoot) this.current.stop()
    shoot.reset().play()
    this.current = shoot
    return true
  }

  /**
   * Killed: plays its death clip once (lying down: DieProne) and holds the last frame.
   * Returns false if the model has no death clips (the caller tips it over instead).
   */
  die(death: Death) {
    const action = (this.prone ? this.action('DieProne') : undefined) ?? this.action(death) ?? this.action('Die1')
    if (!action) return false
    this.target = undefined
    this.route = []
    this.stance = 'dead'
    action.reset()
    action.setLoop(THREE.LoopOnce, 1)
    action.clampWhenFinished = true
    action.play()
    if (this.current && this.current !== action) action.crossFadeFrom(this.current, DEATH_FADE, false)
    this.current = action
    return true
  }

  /** It is being shot at: down on the ground, and it stays down a while longer. */
  takeFire() {
    const dive = this.goProne
    if (!dive || !this.lying || this.stance === 'dead') return
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
    if (this.stance === 'dead') {
      this.mixer.update(seconds)
      return
    }
    if (this.stance === 'prone') {
      this.proneTime -= seconds
      if (this.proneTime <= 0) this.rise()
    }
    const moving = this.stance === 'standing' || this.stance === 'prone'
    if (this.target && moving) {
      const position = this.object.position
      // along the ground (the battlefield sets the height)
      const way = this.target.clone().sub(position).setY(0)
      const distance = way.length()
      const step = this.speed * (this.stance === 'prone' ? CRAWL_FACTOR : 1) * seconds
      if (distance <= step) {
        position.x = this.target.x
        position.z = this.target.z
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
    if (this.changing) return undefined // the change plays on, the loop follows when it ends
    if (this.postureName) return this.action(this.postureName) ?? this.idle
    if (this.stance === 'prone') return this.target ? this.crawl : this.lying
    if (this.stance === 'standing') return this.target ? this.walk : this.idle
    return undefined // diving / rising: the transition plays on, the loop follows when it ends
  }

  private play(action?: THREE.AnimationAction) {
    if (!action || action === this.current) return
    action.reset()
    this.fadeTo(action)
  }

  /** Fades from a finished one-off clip into `action` (the loop). */
  private fadeFrom(from: THREE.AnimationAction, action?: THREE.AnimationAction) {
    if (!action) return
    action.reset().play()
    action.crossFadeFrom(from, FADE, false)
    this.current = action
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
