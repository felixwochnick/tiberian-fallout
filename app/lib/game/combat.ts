import * as THREE from 'three'
import { Battlefield } from './battlefield'
import { LEVEL_HEIGHT } from './terrain'
import type { BuildInfo, Weapon } from './cameos'
import type { Death, Unit } from './unit'

/**
 * Fighting, with the values of the game's RULES.INI: a unit walks up to its target
 * until it is within its weapon's Range=, turns towards it and fires every ROF=
 * frames. Each shot does Damage= times the warhead's Verses= factor for the target's
 * Armor= until its Strength= is used up. Targets are units and buildings; the range
 * to a building counts to the edge of its foundation.
 *
 * Idle units (standing, no order) attack the nearest enemy unit or building within
 * their Sight= on their own, walking up to it if needed, so attacked units fight back
 * and a base defends itself. Neutral objects (owner 'neutral') are never attacked.
 *
 * Bullets hit at once. Visible projectiles (the weapon's Projectile=) fly from the
 * muzzle at their Speed=: shells straight, rockets after their target (ROT=), grenades
 * in an arc to where the target stood (Arcing=, they can miss). A warhead with
 * CellSpread= explodes: everything within the radius takes damage, falling off to
 * PercentAtMax= at the edge – own units too, like in the original.
 *
 * The terrain counts: shots hit the ground and the cliffs in their way (a bullet whose
 * line is blocked, a projectile that comes down on rock before it gets there). From
 * higher ground a weapon reaches farther, rockets most (RANGE_UP per level), from
 * below a little less far (RANGE_DOWN). A unit whose line of fire (or a projectile's
 * flight) is blocked does not shoot into the rock: it looks along the ways it can walk
 * for the nearest place within range with a clear shot and goes there (FiringSpot);
 * where there is none, it gives up a target it picked itself for a while
 * (GIVE_UP_SECONDS) and takes another, or walks up to one it was ordered to attack.
 * Idle units pick targets they can hit first.
 *
 * The artillery and the Juggernaut fire only set up (DeployToFire=): folded they pick
 * no targets of their own; ordered to attack, they go into range and set up there, on
 * flat ground with a clear shot (set up, for one out of range they fold up and go).
 * Set up, the Juggernaut turns its head with the guns towards the target; the Nod
 * artillery, on its spades, only tips its barrel: it turns towards the target before
 * it sets up and fires at what lies before it (FIXED_ARC) – for an ordered target
 * elsewhere it folds up, turns and sets up again.
 *
 * Crushers (Crusher=: the Titan, the harvester, the MCV) drive over the sandbags of
 * their enemies, which burst, and run enemy infantry down (Crushable=); their own
 * sandbags they drive round.
 */

/** Cells within which a unit sees a cloaked enemy right next to it */
const DETECT_REACH = 1.5
/** Game seconds a cloaked thing stays visible after its shot */
const UNCLOAK_SECONDS = 2
/** Game seconds between the shots of a burst (Burst=) */
const BURST_GAP = 0.15
/** The game logic runs 15 frames a second at game speed factor 1 (see SPEED_FACTORS) */
const FRAMES_PER_SECOND = 15
/** How often a unit walking after its target looks where the target is now */
const CHASE_INTERVAL = 0.5
/** How far (cells) a target may move before a unit walking up to it heads for where it is now */
const FOLLOW_SLACK = 1
/** Seconds a destroyed unit lies on the ground before it disappears */
const CORPSE_SECONDS = 3
/** Seconds the burning wreck of a vehicle stays before it sinks away */
const WRECK_SECONDS = 6
/** How many of a collapsing building's explosions are heard (every other one of the first) */
const BLAST_SOUNDS = 5
/** How much colour a wreck keeps: burnt black */
const CHARRED = 0.22
/** Infantry lying on the ground takes this share of the damage */
const PRONE_DAMAGE = 0.5
/** Seconds a destroyed building takes to collapse */
const COLLAPSE_SECONDS = 1.6
/** From this Damage= on a gun is heavy: a bigger muzzle flash */
const HEAVY_DAMAGE = 50
/** Armor= index of light armour (vehicles; infantry has none): bullets spark off it, it explodes when destroyed */
const ARMOR_LIGHT = 2
/**
 * A gun on its own node ("Cannon", the Titan's): it tips up or down towards what it fires
 * at, this fast (radians per second) and this far, and fires once it points nearly there.
 * Without a target it goes back level.
 */
const BARREL_SPEED = THREE.MathUtils.degToRad(70)
const BARREL_UP = THREE.MathUtils.degToRad(35)
const BARREL_DOWN = THREE.MathUtils.degToRad(30)
const BARREL_READY = THREE.MathUtils.degToRad(4)

/** Where shots aim at: the middle of a unit or a building's wall, above the ground */
const AIM_HEIGHT = 0.2
/** A grenade landing this close to a target without an explosion still hits it (cells) */
const DIRECT_HIT = 0.35
/** Share of a crusher's frame radius under which it runs a soldier down (at least MIN_CRUSH cells) */
const CRUSH_REACH = 0.55
const MIN_CRUSH = 0.25
/** How far before the middle of a sandbag's cell a crusher bursts it (cells) */
const WALL_CRUSH_MARGIN = 0.15
/** Seconds a crushed sandbag takes to flatten and disappear */
const FLATTEN_SECONDS = 0.6
/** A rocket flies in a flat arc: its height at the middle of the way, in cells (plus per cell of the way) */
const ROCKET_ARC = { base: 0.05, perCell: 0.07 }
/** Extra range (cells) for each level a shooter stands above its target: rockets, grenades, the others */
const RANGE_UP = { rocket: 1.5, grenade: 1, other: 0.5 }
/** Range lost (cells) for each level a shooter stands below its target */
const RANGE_DOWN = 0.5
/** How fast a dug-in unit turns its turret (radians per second) */
const TURRET_SPEED = 2.5
/**
 * A gun without a turret set up (the Nod artillery, on its spades) fires only at what
 * lies this far either side of where it faces; it turns to within SET_UP_AIM of its
 * target before it sets up
 */
const FIXED_ARC = THREE.MathUtils.degToRad(15)
const SET_UP_AIM = THREE.MathUtils.degToRad(1)
/** A weapon keeps at least this share of its range however low it stands */
const MIN_RANGE_SHARE = 0.6
/** How finely (cells) a bullet's line is checked for ground in the way */
const LINE_STEP = 0.15
/** Ground this close to the target (cells) does not block a bullet: it is what the target stands on */
const TARGET_CLEARANCE = 0.45
/** How many cells (along the ways a unit can walk) it looks through for a place with a clear shot */
const SPOT_SEARCH_CELLS = 300
/** Seconds a unit leaves alone a target it picked itself and found no clear shot at */
const GIVE_UP_SECONDS = 6
/** Seconds before a blocked unit looks again whether its line is clear */
const BLOCKED_RETRY = 0.5
/** Extra distance (cells) counted for a target that cannot be hit from where the unit stands */
const BLOCKED_PENALTY = 4
/** Height of a soldier's muzzle above the ground (cells), for working out shots from elsewhere */
const MUZZLE_HEIGHT = 0.32
/** A target no farther than this beyond its range (cells) is approached by looking for a firing place, not straight */
const SPOT_SEARCH_REACH = 8

interface Shot {
  object: THREE.Object3D
  attacker: THREE.Object3D
  target: THREE.Object3D
  weapon: Weapon
  from: THREE.Vector3
  /** Where it comes down: a rocket follows its target, a shell or grenade flies to the point aimed at */
  to: THREE.Vector3
  /** 0 … 1 along the way */
  progress: number
}


interface Fighter {
  target?: THREE.Object3D
  /** Attack-move: walking there, but fighting every enemy met on the way */
  attackMove?: THREE.Vector3
  /** The target was ordered by the player (otherwise picked by the unit itself) */
  ordered: boolean
  cooldown: number
  chase: number
  /** Where it walks to get a clear shot at its target */
  spot?: THREE.Vector3
  /** The spot is the target itself (no place with a clear shot found): it follows the target */
  toTarget?: boolean
  /** Targets it found no clear shot at, until when it leaves them alone (seconds of game time) */
  ignore?: Map<THREE.Object3D, number>
  /** Shots of the current burst (Burst=) still to come */
  burst?: number
}

export interface CombatEffects {
  /** A shot is fired (sound) */
  fire: (attacker: THREE.Object3D, info: BuildInfo) => void
  /** A unit was destroyed (death cry) */
  die: (victim: THREE.Object3D, info: BuildInfo, crushed?: boolean) => void
  /** A building was destroyed */
  destroyed?: (building: THREE.Object3D) => void
  /** Something cloaked or uncloaked (sound) */
  cloak?: (object: THREE.Object3D, cloaked: boolean) => void
  /** A projectile exploded (sound) */
  impact?: (weapon: Weapon, point: THREE.Vector3) => void
  /** One of the explosions of a building blowing up, `delay` seconds from now (sound) */
  blast?: (building: THREE.Object3D, info: BuildInfo, delay: number) => void
  /** An object took damage */
  hit?: (target: THREE.Object3D) => void
}

export class Combat {
  private readonly fighters = new Map<Unit, Fighter>()
  /**
   * Destroyed units: playing their death clip (unit), falling over (fall ±1) or lying
   * (0), crushed flat, or a vehicle's burning wreck (hop, tilt)
   */
  private readonly dying: {
    object: THREE.Object3D, time: number, fall: number, crushed: boolean, unit?: Unit
    wreck?: { size: number, tilt: THREE.Vector2 }
    /** Height of the ground where it fell */
    ground: number
  }[] = []
  private readonly collapsing: { object: THREE.Object3D, time: number, crushed: boolean, ground: number }[] = []
  private readonly shots: Shot[] = []
  private readonly shellGeometry = new THREE.SphereGeometry(0.03, 8, 6)
  private readonly shellMaterial = new THREE.MeshBasicMaterial({ color: 0xffd27a, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })
  private readonly rocketGeometry = new THREE.CylinderGeometry(0.016, 0.016, 0.11, 6).rotateX(Math.PI / 2)
  private readonly rocketMaterial = new THREE.MeshStandardMaterial({ color: 0x6b6d5c, roughness: 0.6 })
  private readonly grenadeGeometry = new THREE.SphereGeometry(0.025, 8, 6)
  private readonly grenadeMaterial = new THREE.MeshStandardMaterial({ color: 0x3a3c32, roughness: 0.7 })

  constructor(
    private readonly battlefield: Battlefield,
    private readonly infoOf: (object: THREE.Object3D) => BuildInfo | undefined,
    private readonly effects: CombatEffects,
  ) {
    // crushers find their way over enemy sandbags
    battlefield.crusher = object => !!infoOf(object)?.crusher
    // units move at their Speed=
    battlefield.speedOf = object => infoOf(object)?.speed || undefined
  }

  /** Hit points left of an object, starting at its Strength= */
  private hp(object: THREE.Object3D) {
    const info = this.infoOf(object)
    object.userData.hp ??= info?.strength ?? 100
    return object.userData.hp as number
  }

  /** Whether `a` and `b` are on opposite sides */
  static hostile(a: THREE.Object3D, b: THREE.Object3D) {
    if (a.userData.owner === 'neutral' || b.userData.owner === 'neutral') return false
    // under the ground (the subterranean APC on its way) nothing can hit it
    if (b.userData.underground) return false
    return Battlefield.own(a) !== Battlefield.own(b)
  }

  /**
   * Whether `object`'s weapon may go for `other`: an enemy it can hit (in the air only
   * with AA=, on the ground only with AG=); a healer's (negative Damage=) a wounded
   * soldier of its own side
   */
  private targetable(object: THREE.Object3D, weapon: Weapon, other: THREE.Object3D, force = false) {
    if (other === object || other.userData.dead || other.userData.underground) return false
    // cloaked and not seen by a sensor nor a unit close by: it cannot be fired at
    if (other.userData.cloaked && !other.userData.detected && Combat.hostile(object, other)) return false
    const unit = other.userData.unit as Unit | undefined
    if (weapon.damage < 0) {
      // healing (the medic: Organic warhead, soldiers only) or repairing (the repair
      // vehicle: Mechanical, vehicles only), as the warhead's Verses= says
      const info = this.infoOf(other)
      return !Combat.hostile(object, other) && !!other.userData.unit && (weapon.verses[info?.armor ?? 0] ?? 0) > 0
        && this.hp(other) < (info?.strength ?? 100)
    }
    if (!force && !Combat.hostile(object, other)) return false
    const air = !!unit && this.battlefield.flight.airborne(unit)
    return air ? weapon.aa : weapon.ag
  }

  /**
   * Whether the selected units could attack an object (it is an enemy, they have weapons).
   * `force` (Ctrl, like the original): anything but themselves, also walls and their own side.
   */
  canAttack(selection: THREE.Object3D[], target: THREE.Object3D, force = false) {
    if (!force && Battlefield.isWall(target)) return false
    return selection.some((object) => {
      const weapon = this.infoOf(object)?.weapon
      return !!object.userData.unit && Battlefield.own(object) && !!weapon && this.targetable(object, weapon, target, force)
    })
  }

  /** Orders units to attack a target; `force`: also one that is not an enemy (see canAttack). */
  attack(attackers: THREE.Object3D[], target: THREE.Object3D, force = false) {
    for (const object of attackers) {
      const unit = object.userData.unit as Unit | undefined
      const weapon = this.infoOf(object)?.weapon
      if (!unit || !weapon || !this.targetable(object, weapon, target, force)) continue
      this.fighters.set(unit, { target, ordered: true, cooldown: this.fighters.get(unit)?.cooldown ?? 0, chase: 0 })
    }
  }

  /** A move order stops attacking. */
  stop(objects: THREE.Object3D[]) {
    for (const object of objects) {
      const fighter = this.fighters.get(object.userData.unit)
      if (fighter) {
        fighter.target = undefined
        fighter.attackMove = undefined
        fighter.spot = undefined
      }
    }
  }

  /** Attack-move: the units walk to `point` and fight whatever enemy comes in range on the way. */
  attackMove(objects: THREE.Object3D[], point: THREE.Vector3) {
    for (const object of objects) {
      const unit = object.userData.unit as Unit | undefined
      if (!unit) continue
      const fighter = this.fighters.get(unit) ?? { ordered: false, cooldown: 0, chase: 0 }
      fighter.attackMove = point.clone()
      fighter.target = undefined
      this.fighters.set(unit, fighter)
      this.battlefield.walk(unit, point)
    }
  }

  /** Game time (seconds), for how long units leave targets alone */
  private clock = 0

  update(seconds: number, speed: number) {
    const dt = seconds * speed
    this.clock += dt
    // electromagnetic pulses wear off
    for (const object of [...this.battlefield.units.map(u => u.object), ...this.battlefield.structureObjects]) {
      if (object.userData.empSeconds > 0) object.userData.empSeconds = Math.max(0, object.userData.empSeconds - dt)
    }
    /** Units whose gun was pointed at a target this frame (the others level theirs) */
    const aiming = new Set<THREE.Object3D>()
    for (const unit of [...this.battlefield.units]) {
      const object = unit.object
      if (object.userData.dead) continue
      const info = this.infoOf(object)
      const weapon = info?.weapon
      if (!weapon) continue
      const fighter = this.fighters.get(unit) ?? { ordered: false, cooldown: 0, chase: 0 }
      this.fighters.set(unit, fighter)
      fighter.cooldown = Math.max(0, fighter.cooldown - dt)
      // lamed by an electromagnetic pulse: it does nothing until it wears off
      if (object.userData.empSeconds > 0) continue
      // digging in or out: no shot meanwhile
      if (unit.changingPosture) continue
      /** Dug in (the Tick Tank): it turns its turret, but does not go after anything */
      const fixed = !!unit.posture
      /** It fires only set up (DeployToFire=) and is not: it sets up only for a target it was ordered to attack */
      const folded = info!.deployToFire && !fixed

      if (fighter.target?.userData.dead || (fighter.target && !fighter.target.parent) || fighter.target?.userData.underground
        || (folded && !fighter.ordered)) {
        fighter.target = undefined
        fighter.spot = undefined
      }
      // an aircraft without shots left does not fight: it flies to a helipad to reload
      if (!this.battlefield.flight.canFire(unit)) {
        fighter.target = undefined
        fighter.attackMove = undefined
        fighter.spot = undefined
        this.battlefield.flight.done(unit)
        continue
      }
      // attack-move: stop for every enemy in range, go on when it is down
      if (fighter.attackMove && !fighter.target) {
        const enemy = folded ? undefined : this.nearestEnemy(object, weapon, fighter, other => this.range(object.position, weapon, other))
        if (enemy) {
          fighter.target = enemy
          fighter.ordered = false
        }
        else if (!unit.walking && !this.battlefield.flight.travelling(unit)) {
          // there: across the ground (aircraft are up in the air)
          const way = Math.hypot(object.position.x - fighter.attackMove.x, object.position.z - fighter.attackMove.z)
          if (fixed || way < 0.6) fighter.attackMove = undefined
          else this.battlefield.walk(unit, fighter.attackMove)
        }
      }
      // standing idle: guard, attack the nearest enemy within sight
      const sight = Math.max(weapon.range, info!.sight)
      if (!fighter.target && !folded && !unit.walking && !this.battlefield.flight.grounded(unit)) {
        fighter.target = this.nearestEnemy(object, weapon, fighter, other => Math.max(sight, this.range(object.position, weapon, other)))
        fighter.ordered = false
      }
      const target = fighter.target
      if (!target) {
        // an aircraft whose work is done lands where it is (out of shots: on a helipad)
        this.battlefield.flight.done(unit)
        continue
      }
      // on its way to a place with a clear shot: let it get there
      // (while the target stays where it can be hit from there; once it moves away, a new place)
      if (fighter.spot) {
        if (unit.walking) {
          fighter.chase -= dt
          if (fighter.chase > 0) continue
          fighter.chase = CHASE_INTERVAL
          if (fighter.toTarget ? Battlefield.reach(fighter.spot, target) < FOLLOW_SLACK : this.spotHolds(fighter.spot, weapon, target)) continue
          fighter.chase = 0
        }
        fighter.spot = undefined
      }

      const distance = Battlefield.reach(object.position, target)
      const range = this.range(object.position, weapon, target)
      if (distance > range) {
        // a target it picked itself is let go once out of sight; an ordered one is chased
        // (dug in, it lets go of all it cannot reach; set up to fire, it folds up for an ordered one)
        if (fixed && info!.deployToFire && fighter.ordered) {
          this.battlefield.toggleDigIn(unit)
          continue
        }
        if (fixed || (!fighter.ordered && distance > sight + 1)) {
          fighter.target = undefined
          continue
        }
        fighter.chase -= dt
        if (!unit.walking || fighter.chase <= 0) {
          fighter.chase = CHASE_INTERVAL
          // near enough: to the nearest place it can hit it from (round cliffs, up ramps; not in the air)
          if (distance <= range + SPOT_SEARCH_REACH && !this.battlefield.flight.has(unit)) {
            this.takePosition(unit, fighter, weapon, target, MUZZLE_HEIGHT)
            continue
          }
          // up to the target, on the way round buildings, until it is in range
          const aim = Battlefield.closestPoint(object.position, target)
          const way = aim.clone().sub(object.position).setY(0)
          const length = way.length()
          const stopAt = length > 0 ? object.position.clone().addScaledVector(way, Math.max(0, 1 - (range * 0.85) / length)) : aim
          this.battlefield.walk(unit, stopAt)
        }
        continue
      }
      if (unit.walking) unit.stop()
      const point = Battlefield.closestPoint(object.position, target)
      if (folded) {
        this.setUp(unit, fighter, weapon, target, point, dt)
        continue
      }
      // dug in, the Tick Tank turns its turret (the Juggernaut its head with the guns); set
      // up without one (the Nod artillery, on its spades) it only tips its barrel
      let faced: boolean
      if (!fixed) faced = unit.face(point, dt)
      else if (this.part(object, 'Turret')) faced = this.traverse(object, point, dt)
      else if (this.bears(object, point)) faced = true
      else {
        // elsewhere: for an ordered target it folds up to turn and set up again, one it picked itself it leaves
        if (fighter.ordered) this.battlefield.toggleDigIn(unit)
        else this.giveUp(fighter, target)
        continue
      }
      aiming.add(object)
      const elevated = this.elevate(object, target, dt)
      if (faced && elevated && fighter.cooldown <= 0) {
        const muzzle = this.muzzle(object, true)
        if (!this.battlefield.flight.airborne(unit) && this.flightBlocked(weapon, muzzle, this.aimPoint(muzzle, target))) {
          // not into the rock: somewhere with a clear shot, or another target (dug in: only that)
          fighter.cooldown = BLOCKED_RETRY
          if (fixed) {
            this.giveUp(fighter, target)
            continue
          }
          this.takePosition(unit, fighter, weapon, target, muzzle.y - object.position.y)
          continue
        }
        // a burst: its shots one after another, then the weapon's pause
        fighter.burst = (fighter.burst || weapon.burst) - 1
        fighter.cooldown = fighter.burst > 0 ? BURST_GAP : weapon.rof / FRAMES_PER_SECOND
        this.fire(object, target, info!)
        if (!fighter.burst) this.battlefield.flight.fired(unit)
      }
    }
    this.updateTowers(dt)
    this.cloak(dt)
    for (const unit of this.battlefield.units) {
      if (aiming.has(unit.object) || unit.object.userData.dead) continue
      this.elevate(unit.object, undefined, dt)
      this.centreTurret(unit.object, dt)
    }
    this.crush()
    this.fly(dt)
    this.animate(dt)
  }

  /**
   * Cloaking, like in the original: what is Cloakable= (the stealth tank; the limpet drone
   * dug in) and what stands within CloakRadiusInCells= of its side's cloak generator (the
   * stealth generator; the mobile one set up) is cloaked, but for a moment after each of
   * its shots. Cloaked enemies are seen by Sensors= buildings within their sight and by
   * units right next to them – only then can they be fired at.
   */
  private cloak(dt: number) {
    const all = [...this.battlefield.units.map(u => u.object), ...this.battlefield.structureObjects].filter(o => !o.userData.dead)
    const generators = all.filter((o) => {
      const info = this.infoOf(o)
      if (!info?.cloakRadius || o.userData.poweredOff || o.userData.empSeconds > 0) return false
      return !info.cloakRadiusDeployed || !!(o.userData.unit as Unit | undefined)?.posture
    })
    for (const object of all) {
      object.userData.uncloak = Math.max(0, (object.userData.uncloak ?? 0) - dt)
      const info = this.infoOf(object)
      const unit = object.userData.unit as Unit | undefined
      const self = !!info?.cloakable && (!info.cloakDeployed || !!unit?.posture)
      const covered = generators.some(g => g !== object && g.userData.owner === object.userData.owner
        && Battlefield.reach(g.position, object) <= this.infoOf(g)!.cloakRadius)
      const cloaked = (self || covered) && !(object.userData.uncloak > 0) && !object.userData.flyer
      if (cloaked !== !!object.userData.cloaked) {
        object.userData.cloaked = cloaked
        this.effects.cloak?.(object, cloaked)
      }
      object.userData.detected = cloaked && all.some((other) => {
        if (!Combat.hostile(other, object)) return false
        const sight = this.infoOf(other)
        const range = sight?.sensors ? sight.sight : DETECT_REACH
        return Battlefield.reach(other.position, object) <= range
      })
      this.battlefield.showCloaked(object, cloaked, !!object.userData.detected)
    }
  }

  /** The base defences and their targets (each keeps its own, like a unit) */
  private readonly towers = new Map<THREE.Object3D, Fighter>()

  /**
   * What a building fires with: its own Primary= (the laser, the SAM site) or that of
   * the gun mounted on it (the component tower's Vulcan or SAM, userData.gun)
   */
  private armament(object: THREE.Object3D) {
    const own = this.infoOf(object)
    // the EMP cannon fires only when the player aims its pulse
    if (own?.manualOnly) return undefined
    if (own?.weapon) return own
    // (true while its model is still loading)
    const gun = object.userData.gun as THREE.Object3D | true | undefined
    return gun && gun !== true ? this.infoOf(gun) : undefined
  }

  /**
   * Base defences fire at enemies within range of their own accord, turning their
   * turret ("Turret", tipping "Cannon") towards them; switched off with the power
   * button (userData.poweredOff) they are silent.
   */
  private updateTowers(dt: number) {
    for (const object of this.battlefield.structureObjects) {
      const info = object.userData.dead || object.userData.poweredOff || object.userData.empSeconds > 0 ? undefined : this.armament(object)
      const weapon = info?.weapon
      if (!info || !weapon) continue
      const fighter = this.towers.get(object) ?? { ordered: false, cooldown: 0, chase: 0 }
      this.towers.set(object, fighter)
      fighter.cooldown = Math.max(0, fighter.cooldown - dt)
      const target = fighter.target
      if (!target || !this.targetable(object, weapon, target) || Battlefield.reach(object.position, target) > weapon.range) {
        fighter.target = this.nearestEnemy(object, weapon, fighter, () => weapon.range)
      }
      if (!fighter.target) continue
      const aim = Battlefield.closestPoint(object.position, fighter.target)
      const faced = this.traverse(object, aim, dt) || !this.part(object, 'Turret')
      const elevated = this.elevate(object, fighter.target, dt)
      if (!faced || !elevated || fighter.cooldown > 0) continue
      fighter.burst = (fighter.burst || weapon.burst) - 1
      fighter.cooldown = fighter.burst > 0 ? BURST_GAP : weapon.rof / FRAMES_PER_SECOND
      this.fire(object, fighter.target, info)
    }
    for (const object of this.towers.keys()) if (object.userData.dead) this.towers.delete(object)
  }

  /**
   * Tips a gun on its own node up or down towards the target (level without one).
   * Returns whether it points there; units without such a gun always do.
   */
  private elevate(object: THREE.Object3D, target: THREE.Object3D | undefined, seconds: number) {
    const cannon = this.part(object, 'Cannon')
    if (!cannon) return true
    let pitch = 0
    if (target) {
      const pivot = cannon.getWorldPosition(new THREE.Vector3())
      const aim = this.aimPoint(pivot, target)
      pitch = THREE.MathUtils.clamp(Math.atan2(aim.y - pivot.y, Math.hypot(aim.x - pivot.x, aim.z - pivot.z)), -BARREL_DOWN, BARREL_UP)
    }
    // the barrel points along +z: tipping it up turns it round x the other way
    const wanted = -pitch
    const step = BARREL_SPEED * seconds
    const now = cannon.rotation.x
    cannon.rotation.x = now + THREE.MathUtils.clamp(wanted - now, -step, step)
    return Math.abs(wanted - cannon.rotation.x) <= BARREL_READY
  }

  /**
   * A node of a unit's gun by its name (Cannon, Turret): in a posture its own
   * (DeployedCannon …) if the model has one, else the same as without; found once
   */
  private part(object: THREE.Object3D, name: string) {
    const posture = (object.userData.unit as Unit | undefined)?.posture ?? ''
    const parts = (object.userData.parts ??= new Map<string, THREE.Object3D | null>()) as Map<string, THREE.Object3D | null>
    const key = posture + name
    if (!parts.has(key)) parts.set(key, object.getObjectByName(key) ?? object.getObjectByName(name) ?? null)
    return parts.get(key)
  }

  /**
   * Turns a turret that was aimed while dug in back to the front (it drives with the gun
   * forward), already while it digs out
   */
  private centreTurret(object: THREE.Object3D, seconds: number) {
    const unit = object.userData.unit as Unit | undefined
    if (unit?.posture && !unit.changingPosture) return
    const turret = this.part(object, 'Turret')
    if (!turret || turret.rotation.y === 0) return
    const turn = THREE.MathUtils.euclideanModulo(turret.rotation.y + Math.PI, 2 * Math.PI) - Math.PI
    const step = TURRET_SPEED * seconds
    turret.rotation.y = Math.abs(turn) <= step ? 0 : turret.rotation.y - Math.sign(turn) * step
  }

  /**
   * Turns a dug-in unit's turret (node "<Posture>Turret", turning about the vertical)
   * towards a point; returns whether it points there. Without such a turret it cannot aim.
   */
  private traverse(object: THREE.Object3D, point: THREE.Vector3, seconds: number) {
    const turret = this.part(object, 'Turret')
    if (!turret) return false
    const way = point.clone().sub(object.position)
    const heading = Math.atan2(way.x, way.z) - object.rotation.y
    const turn = THREE.MathUtils.euclideanModulo(heading - turret.rotation.y + Math.PI, 2 * Math.PI) - Math.PI
    const step = TURRET_SPEED * seconds
    turret.rotation.y += THREE.MathUtils.clamp(turn, -step, step)
    return Math.abs(turn) < 0.1
  }

  /**
   * Whether a unit's gun can be brought to bear on `point` from where it stands: set up
   * without a turret (the Nod artillery, on its spades) only on what lies before it
   */
  private bears(object: THREE.Object3D, point: THREE.Vector3) {
    if (!(object.userData.unit as Unit | undefined)?.posture || this.part(object, 'Turret')) return true
    return Combat.offAxis(object, point) <= FIXED_ARC
  }

  /** How far (radians, either way) `point` lies off the way the object faces */
  private static offAxis(object: THREE.Object3D, point: THREE.Vector3) {
    const heading = Math.atan2(point.x - object.position.x, point.z - object.position.z)
    return Math.abs(THREE.MathUtils.euclideanModulo(heading - object.rotation.y + Math.PI, 2 * Math.PI) - Math.PI)
  }

  /**
   * A unit that fires only set up (DeployToFire=), folded in range of the target it was
   * ordered to attack: it sets up where it stands if the ground lets it (flat) and the
   * shot from there is clear, else it goes to the nearest place where both are so; without
   * a turret it turns towards the target first
   */
  private setUp(unit: Unit, fighter: Fighter, weapon: Weapon, target: THREE.Object3D, point: THREE.Vector3, seconds: number) {
    const object = unit.object
    const muzzle = object.position.clone().setY(object.position.y + MUZZLE_HEIGHT)
    if (!this.battlefield.canDig(object.position) || this.flightBlocked(weapon, muzzle, this.aimPoint(muzzle, target))) {
      this.takePosition(unit, fighter, weapon, target, MUZZLE_HEIGHT, true)
      return
    }
    if (!this.part(object, 'Turret')) {
      unit.face(point, seconds)
      if (Combat.offAxis(object, point) > SET_UP_AIM) return
    }
    this.battlefield.toggleDigIn(unit)
  }

  /** Leaves a target alone for a while (GIVE_UP_SECONDS) */
  private giveUp(fighter: Fighter, target: THREE.Object3D) {
    ;(fighter.ignore ??= new Map()).set(target, this.clock + GIVE_UP_SECONDS)
    fighter.target = undefined
  }

  /** Moving crushers burst the enemy sandbags and run down the enemy soldiers they drive over. */
  private crush() {
    const walls = this.battlefield.structureObjects.filter(Battlefield.isWall)
    for (const unit of this.battlefield.units) {
      const object = unit.object
      if (object.userData.dead || !unit.walking || !this.infoOf(object)?.crusher) continue
      const at = object.position
      for (const wall of walls) {
        if (wall.userData.dead || !Combat.hostile(object, wall) || this.infoOf(wall)?.crushable === false) continue
        const f = wall.userData.footprint as { x: number, z: number, w: number, h: number }
        const m = WALL_CRUSH_MARGIN
        if (at.x > f.x - m && at.x < f.x + f.w + m && at.z > f.z - m && at.z < f.z + f.h + m) this.kill(wall, true)
      }
      const reach = Math.max(MIN_CRUSH, ((object.userData.frameSize?.radius as number | undefined) ?? 0) * CRUSH_REACH)
      for (const other of [...this.battlefield.units]) {
        const victim = other.object
        if (other === unit || victim.userData.dead || !Combat.hostile(object, victim) || !this.infoOf(victim)?.crushable) continue
        if (Math.hypot(victim.position.x - at.x, victim.position.z - at.z) < reach) this.kill(victim, true)
      }
    }
  }

  /**
   * How far a weapon reaches from `attacker` to `target`: its Range=, longer from
   * above (rockets most), a little shorter from below
   */
  private range(from: THREE.Vector3, weapon: Weapon, target: THREE.Object3D) {
    const point = Battlefield.closestPoint(from, target)
    const levels = (this.battlefield.heightAt(from.x, from.z) - this.battlefield.heightAt(point.x, point.z)) / LEVEL_HEIGHT
    if (levels >= 0) {
      const kind = weapon.projectile?.homing ? 'rocket' : weapon.projectile?.arcing ? 'grenade' : 'other'
      return weapon.range + levels * RANGE_UP[kind]
    }
    return Math.max(weapon.range * MIN_RANGE_SHARE, weapon.range + levels * RANGE_DOWN)
  }

  /**
   * The nearest enemy unit or building within its `range` (units first when about as
   * near; the ones it can hit from where it stands first; none it has given up on)
   */
  private nearestEnemy(object: THREE.Object3D, weapon: Weapon, fighter: Fighter, range: (other: THREE.Object3D) => number) {
    let best: THREE.Object3D | undefined
    let bestDistance = Infinity
    const candidates = [...this.battlefield.units.map(u => u.object), ...this.battlefield.structureObjects]
    for (const other of candidates) {
      // walls are never picked as a target
      if (!this.targetable(object, weapon, other) || Battlefield.isWall(other)) continue
      // buildings count a little farther, so soldiers deal with soldiers first
      if ((fighter.ignore?.get(other) ?? 0) > this.clock) continue
      if (!this.bears(object, Battlefield.closestPoint(object.position, other))) continue
      const distance = Battlefield.reach(object.position, other)
      if (distance > range(other) || distance - BLOCKED_PENALTY > bestDistance) continue
      const muzzle = object.position.clone().setY(object.position.y + MUZZLE_HEIGHT)
      const clear = !this.flightBlocked(weapon, muzzle, this.aimPoint(muzzle, other))
      const d = distance + (other.userData.footprint ? 0.5 : 0) + (clear ? 0 : BLOCKED_PENALTY)
      if (d <= bestDistance) {
        best = other
        bestDistance = d
      }
    }
    return best
  }

  private fire(attacker: THREE.Object3D, target: THREE.Object3D, info: BuildInfo) {
    const weapon = info.weapon!
    // a shot gives it away
    attacker.userData.uncloak = UNCLOAK_SECONDS
    this.effects.fire(attacker, info)
    // the walkers fire with their own clip (barrels, recoil, muzzle flashes at the
    // guns); for the others a muzzle flash in front of the soldier
    const shooter = attacker.userData.unit as Unit | undefined
    const muzzle = this.muzzle(attacker)
    const aim = this.aimPoint(muzzle, target)
    shooter?.fire()
    // a base defence plays its own Fire clip (its gun's, if one is mounted)
    const gun = attacker.userData.gun as THREE.Object3D | true | undefined
    if (!shooter) this.battlefield.playClip(gun && gun !== true ? gun : attacker, 'Fire')
    // the flash and a wisp of smoke at the muzzle (heavy guns: more of both)
    this.battlefield.effects.muzzleFlash(muzzle, aim.clone().sub(muzzle), weapon.damage >= HEAVY_DAMAGE)
    if (weapon.laser !== undefined) this.battlefield.effects.beam(muzzle, aim, weapon.laser)
    if (!weapon.projectile) {
      // a bullet: into the ground or the rock if that is in the way
      const blocked = this.blocked(muzzle, aim)
      if (blocked) this.impact(attacker, target, weapon, blocked, false)
      else this.impact(attacker, target, weapon, aim, true)
      return
    }
    // a projectile on its way: a rocket (its exhaust trails behind, see fly), a grenade, a glowing shell
    let object: THREE.Object3D
    if (weapon.projectile.homing) object = new THREE.Mesh(this.rocketGeometry, this.rocketMaterial)
    else if (weapon.projectile.arcing) object = new THREE.Mesh(this.grenadeGeometry, this.grenadeMaterial)
    else {
      object = new THREE.Mesh(this.shellGeometry, this.shellMaterial)
      object.scale.set(0.8, 0.8, 2.2)
    }
    const shot: Shot = { object, attacker, target, weapon, from: muzzle, to: aim, progress: 0 }
    // it leaves the muzzle pointing along its way (the start of the arc)
    object.position.copy(muzzle)
    object.lookAt(Combat.along(shot, 0.02))
    this.battlefield.addEffect(object)
    this.shots.push(shot)
  }

  /** Where a projectile is at `progress` (0 … 1) of its way: grenades and rockets fly in an arc */
  private static along(shot: Shot, progress: number) {
    const { projectile } = shot.weapon
    const length = Math.max(0.05, shot.from.distanceTo(shot.to))
    const position = shot.from.clone().lerp(shot.to, progress)
    // a grenade is thrown high, the farther the higher; a rocket arcs flat
    const height = projectile!.arcing
      ? 0.15 + 0.3 * length
      : projectile!.homing ? ROCKET_ARC.base + ROCKET_ARC.perCell * length : 0
    position.y += 4 * height * progress * (1 - progress)
    return position
  }

  /** Where a shot leaves the attacker: the muzzle of a walker's gun (its flash nodes, in turn), else in front of it */
  private muzzle(attacker: THREE.Object3D, peek = false) {
    // the muzzles of its gun: nodes Flash… (in a posture <Posture>Flash… if there are any), found once
    const posture = (attacker.userData.unit as Unit | undefined)?.posture ?? ''
    const found = (attacker.userData.muzzles ??= new Map<string, THREE.Object3D[]>()) as Map<string, THREE.Object3D[]>
    let muzzles = found.get(posture)
    if (!muzzles) {
      const collect = (prefix: string) => {
        const all: THREE.Object3D[] = []
        attacker.traverse((node) => {
          if (node.name.startsWith(prefix) && !node.parent?.name.startsWith(prefix)) all.push(node)
        })
        return all
      }
      // a posture's own muzzles if the model has them, else the same as without
      muzzles = posture ? collect(`${posture}Flash`) : []
      if (!muzzles.length) muzzles = collect('Flash')
      found.set(posture, muzzles)
    }
    if (muzzles.length) {
      const next = ((attacker.userData.shotCount as number | undefined) ?? -1) + 1
      const shot = peek ? next : (attacker.userData.shotCount = next)
      return muzzles[shot % muzzles.length]!.getWorldPosition(new THREE.Vector3())
    }
    const forward = new THREE.Vector3(Math.sin(attacker.rotation.y), 0, Math.cos(attacker.rotation.y))
    const lying = (attacker.userData.unit as Unit | undefined)?.prone
    return attacker.position.clone().addScaledVector(forward, lying ? 0.3 : 0.18).setY(attacker.position.y + (lying ? 0.08 : 0.32))
  }

  /** The point a shot from `from` goes for: the unit, or the nearest wall of a building */
  private aimPoint(from: THREE.Vector3, target: THREE.Object3D) {
    const point = Battlefield.closestPoint(from, target)
    return point.setY(this.battlefield.heightAt(point.x, point.z) + AIM_HEIGHT)
  }

  /**
   * Whether the ground is in the way of a shot from `from` to `to`: a bullet's or
   * shell's straight line, a rocket's or grenade's arc
   */
  private flightBlocked(weapon: Weapon, from: THREE.Vector3, to: THREE.Vector3) {
    if (!weapon.projectile || (!weapon.projectile.homing && !weapon.projectile.arcing)) return !!this.blocked(from, to)
    const shot = { weapon, from, to } as Shot
    const length = from.distanceTo(to)
    const steps = Math.max(2, Math.ceil(length / LINE_STEP))
    for (let i = 1; i < steps; i++) {
      const point = Combat.along(shot, i / steps)
      if (Math.hypot(point.x - to.x, point.z - to.z) < TARGET_CLEARANCE) break
      if (this.battlefield.heightAt(point.x, point.z) > point.y) return true
    }
    return false
  }

  /**
   * Looks for the nearest place (along the ways the unit can walk) within range of the
   * target with a clear shot, not taken by another unit (`flat`: on flat ground, to set
   * up on), and sends the unit there; if there is none, a target it picked itself is
   * left alone a while, one it was ordered to attack is walked up to (not to set up:
   * that is left alone as well).
   */
  private takePosition(unit: Unit, fighter: Fighter, weapon: Weapon, target: THREE.Object3D, muzzleHeight: number, flat = false) {
    const object = unit.object
    const nav = this.battlefield.navFor(object)
    const taken = [...this.fighters.values()].flatMap(f => f !== fighter && f.spot ? [f.spot] : [])
    const others = this.battlefield.units.filter(u => u !== unit && !u.object.userData.dead).map(u => u.object.position)
    const start = [Math.floor(object.position.x), Math.floor(object.position.z)] as const
    const seen = new Set([`${start[0]},${start[1]}`])
    const queue: (readonly [number, number])[] = [start]
    for (let i = 0; i < queue.length && i < SPOT_SEARCH_CELLS; i++) {
      const [x, z] = queue[i]!
      const spot = new THREE.Vector3(x + 0.5, this.battlefield.heightAt(x + 0.5, z + 0.5), z + 0.5)
      const free = !taken.some(t => t.distanceTo(spot) < 0.7) && !others.some(o => Math.hypot(o.x - spot.x, o.z - spot.z) < 0.4)
      if (i > 0 && free && (!flat || this.battlefield.canDig(spot)) && Battlefield.reach(spot, target) <= this.range(spot, weapon, target) * 0.95) {
        const muzzle = spot.clone().setY(spot.y + muzzleHeight)
        if (!this.flightBlocked(weapon, muzzle, this.aimPoint(muzzle, target))) {
          fighter.spot = spot
          fighter.toTarget = false
          this.battlefield.walk(unit, spot)
          return
        }
      }
      for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]] as const) {
        const nx = x + dx
        const nz = z + dz
        const key = `${nx},${nz}`
        if (seen.has(key) || !nav.free(nx, nz) || (nav.step && !nav.step(x, z, dx, dz))) continue
        seen.add(key)
        queue.push([nx, nz])
      }
    }
    if (fighter.ordered && !flat) {
      // ordered: up to it, on the way something better may turn up
      fighter.spot = Battlefield.closestPoint(object.position, target)
      fighter.toTarget = true
      this.battlefield.walk(unit, fighter.spot)
      return
    }
    this.giveUp(fighter, target)
  }

  /** The target (where it is now) can still be hit from `spot`, with a clear shot */
  private spotHolds(spot: THREE.Vector3, weapon: Weapon, target: THREE.Object3D) {
    if (Battlefield.reach(spot, target) > this.range(spot, weapon, target)) return false
    const muzzle = spot.clone().setY(spot.y + MUZZLE_HEIGHT)
    return !this.flightBlocked(weapon, muzzle, this.aimPoint(muzzle, target))
  }

  /** The first point on the straight line from `from` to `to` where the ground is in the way, if any */
  private blocked(from: THREE.Vector3, to: THREE.Vector3) {
    const length = from.distanceTo(to)
    const point = new THREE.Vector3()
    for (let d = LINE_STEP; d < length - TARGET_CLEARANCE; d += LINE_STEP) {
      point.lerpVectors(from, to, d / length)
      if (this.battlefield.heightAt(point.x, point.z) > point.y) return point.setY(this.battlefield.heightAt(point.x, point.z))
    }
    return undefined
  }

  /** Moves the projectiles on; they hit the ground or rock in their way, at the end of their way they hit. */
  private fly(dt: number) {
    for (const shot of [...this.shots]) {
      const { weapon, object } = shot
      // a rocket steers after its target while that is still there
      if (weapon.projectile!.homing && !shot.target.userData.dead) shot.to = this.aimPoint(object.position, shot.target)
      const length = Math.max(0.05, shot.from.distanceTo(shot.to))
      shot.progress = Math.min(1, shot.progress + (weapon.speed * dt) / length)
      const position = Combat.along(shot, shot.progress)
      const back = object.position.clone().sub(position)
      if (back.lengthSq() > 1e-8) object.lookAt(position)
      object.position.copy(position)
      // into the ground or a cliff on the way (not the ground the target stands on)
      const ground = this.battlefield.heightAt(position.x, position.z)
      const near = Math.hypot(position.x - shot.to.x, position.z - shot.to.z) < TARGET_CLEARANCE
      if (position.y < ground && !near && shot.progress < 1) {
        this.battlefield.removeEffect(object)
        this.shots.splice(this.shots.indexOf(shot), 1)
        this.impact(shot.attacker, shot.target, weapon, position.setY(ground), false)
        continue
      }
      // the rocket's exhaust out of its tail, the shell's glowing trail
      // puffs along the way flown this frame, so the trail stays whole at any frame rate
      const steps = Math.max(1, Math.round(dt * 60))
      const tail = back.clone().normalize()
      for (let i = 0; i < steps; i++) {
        const along = position.clone().addScaledVector(back, i / steps)
        if (weapon.projectile!.homing) this.battlefield.effects.rocketTrail(along.addScaledVector(tail, 0.06), tail)
        else if (!weapon.projectile!.arcing) this.battlefield.effects.tracer(along)
      }
      if (shot.progress < 1) continue
      this.battlefield.removeEffect(object)
      this.shots.splice(this.shots.indexOf(shot), 1)
      // a grenade comes down where the target was: it may have walked away
      const direct = !weapon.projectile!.arcing || Battlefield.reach(shot.to, shot.target) <= DIRECT_HIT
      this.impact(shot.attacker, shot.target, weapon, shot.to, direct)
    }
  }

  /** A shot arrives at `point`: an explosion (CellSpread=) hurts all round it, else the target if it was hit. */
  private impact(attacker: THREE.Object3D, target: THREE.Object3D, weapon: Weapon, point: THREE.Vector3, direct: boolean) {
    if (weapon.spread > 0 || weapon.projectile) {
      // an explosion as big as its blast, with its sound
      this.battlefield.effects.explosion(point, Math.max(0.35, weapon.spread * 1.5))
      this.effects.impact?.(weapon, point)
    }
    else {
      // a bullet: dust, and sparks off armour and walls
      const at = point.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.15, (Math.random() - 0.4) * 0.2, (Math.random() - 0.5) * 0.15))
      const hard = !!target.userData.footprint || (this.infoOf(target)?.armor ?? 0) >= ARMOR_LIGHT
      this.battlefield.effects.bulletHit(at, direct && hard)
    }
    if (weapon.spread <= 0) {
      if (direct && !target.userData.dead) this.damage(target, weapon, 1)
      return
    }
    const victims = [...this.battlefield.units.map(u => u.object), ...this.battlefield.structureObjects]
    for (const victim of victims) {
      if (victim === attacker || victim.userData.dead || victim.userData.owner === 'neutral') continue
      const distance = Battlefield.reach(point, victim)
      if (distance > weapon.spread) continue
      this.damage(victim, weapon, 1 - (1 - weapon.percentAtMax) * (distance / weapon.spread))
    }
  }

  /**
   * An explosion that is no unit's shot (a superweapon): `damage` at `point`, less
   * towards the edge of `radius` (cells); `wall`: it also breaks walls
   */
  blast(point: THREE.Vector3, damage: number, radius: number, { percentAtMax = 0.5, wall = true, spare }: { percentAtMax?: number, wall?: boolean, spare?: string } = {}) {
    const weapon: Weapon = {
      name: 'Blast', damage, rof: 1, range: 0, verses: [1, 1, 1, 1, 1], reports: [], impactReports: [], wall, speed: 0,
      spread: radius, percentAtMax, aa: true, ag: true, burst: 1,
    }
    for (const victim of [...this.battlefield.units.map(u => u.object), ...this.battlefield.structureObjects]) {
      if (victim.userData.dead || victim.userData.owner === 'neutral' || (spare && victim.userData.owner === spare)) continue
      const distance = Battlefield.reach(point, victim)
      if (distance > radius) continue
      this.damage(victim, weapon, 1 - (1 - percentAtMax) * (distance / radius))
    }
  }

  /**
   * An electromagnetic pulse (EMEffect=): vehicles and buildings within `radius` of
   * `point` are lamed for `seconds` – they neither move nor fire; soldiers are not hit
   */
  pulse(point: THREE.Vector3, radius: number, seconds: number) {
    const hit: THREE.Object3D[] = []
    for (const object of [...this.battlefield.units.map(u => u.object), ...this.battlefield.structureObjects]) {
      if (object.userData.dead || Battlefield.reach(point, object) > radius) continue
      if (this.infoOf(object)?.category === 'infantry') continue
      object.userData.empSeconds = Math.max(object.userData.empSeconds ?? 0, seconds)
      const unit = object.userData.unit as Unit | undefined
      unit?.stop()
      const fighter = unit && this.fighters.get(unit)
      if (fighter) fighter.target = undefined
      hit.push(object)
    }
    return hit
  }

  /** Damage times the warhead's Verses= factor for the victim's Armor=, times `share` (of an explosion). */
  private damage(target: THREE.Object3D, weapon: Weapon, share: number) {
    const targetInfo = this.infoOf(target)
    // walls only take damage from explosives (Wall= of the warhead), not from rifles
    const verses = Battlefield.isWall(target) && !weapon.wall ? 0 : weapon.verses[targetInfo?.armor ?? 0] ?? 1
    // infantry under fire throws itself down, and is harder to hurt there
    const victim = target.userData.unit as Unit | undefined
    const healing = weapon.damage < 0
    const cover = victim?.prone && !healing ? PRONE_DAMAGE : 1
    if (!healing && !targetInfo?.fearless) victim?.takeFire()
    // healed up to its full strength, no more
    const hp = Math.min(targetInfo?.strength ?? Infinity, this.hp(target) - weapon.damage * verses * cover * share)
    target.userData.hp = hp
    target.userData.health = Math.max(0, hp / (targetInfo?.strength ?? 100))
    if (weapon.damage * verses > 0) this.effects.hit?.(target)
    if (hp <= 0) this.kill(target, false, weapon.spread > 0 || weapon.projectile ? 'Die2' : 'Die1')
  }

  /** Falls over (or is `crushed` flat), lies on the ground for a moment and disappears. */
  private kill(object: THREE.Object3D, crushed = false, death: Death = 'Die1') {
    if (object.userData.dead) return
    object.userData.dead = true
    const footprint = object.userData.footprint as { x: number, z: number, w: number, h: number } | undefined
    // a sandbag driven over bursts and is flattened
    if (footprint && crushed) {
      this.battlefield.effects.crush(new THREE.Vector3(footprint.x + footprint.w / 2, object.position.y, footprint.z + footprint.h / 2), true)
      const info = this.infoOf(object)
      if (info) this.effects.die(object, info, true)
      this.battlefield.removeStructure(object)
      this.effects.destroyed?.(object)
      this.collapsing.push({ object, time: 0, crushed, ground: object.position.y })
      return
    }
    // a building collapses in explosions, the first few heard one after the other
    if (footprint) {
      const info = this.infoOf(object)
      for (let i = 0; i < 3 + footprint.w * footprint.h / 2; i++) {
        const at = new THREE.Vector3(footprint.x + Math.random() * footprint.w, object.position.y + 0.1 + Math.random() * 0.4, footprint.z + Math.random() * footprint.h)
        this.battlefield.effects.explosion(at, 0.6 + Math.random() * 0.5, i * 0.18)
        if (info && i < BLAST_SOUNDS && i % 2 === 0) this.effects.blast?.(object, info, i * 0.18)
      }
      this.battlefield.removeStructure(object)
      this.effects.destroyed?.(object)
      this.collapsing.push({ object, time: 0, crushed, ground: object.position.y })
      return
    }
    const unit = object.userData.unit as Unit | undefined
    unit?.stop()
    const info = this.infoOf(object)
    // vehicles and walkers blow up (infantry has no armour) and leave a burning wreck
    if ((info?.armor ?? 0) >= ARMOR_LIGHT && !crushed) {
      const size = this.blowUp(object)
      this.battlefield.remove(object)
      this.battlefield.addEffect(object)
      if (info) this.effects.die(object, info)
      this.dying.push({ object, time: 0, fall: 0, crushed, ground: object.position.y, wreck: { size, tilt: new THREE.Vector2(Math.random() - 0.5, Math.random() - 0.5).multiplyScalar(0.35) } })
      return
    }
    if (crushed) this.battlefield.effects.crush(object.position, false)
    if (info) this.effects.die(object, info, crushed)
    // no longer a target or selectable
    this.battlefield.remove(object)
    this.battlefield.addEffect(object)
    // soldiers play their death clip (shot: they slump, blown up: thrown back); models
    // without one fall over stiffly, lying ones are already down
    const prone = unit?.prone
    const animated = !crushed && !!unit?.die(death)
    this.dying.push({ object, time: 0, ground: object.position.y, fall: animated || prone || crushed ? 0 : Math.random() < 0.5 ? 1 : -1, crushed, unit: animated ? unit : undefined })
  }

  /**
   * A vehicle explodes: a big blast in its middle, smaller ones after it across its
   * body, and it is burnt black. Returns its size (cells across).
   */
  private blowUp(object: THREE.Object3D) {
    const box = new THREE.Box3().setFromObject(object)
    const extent = box.getSize(new THREE.Vector3())
    const size = THREE.MathUtils.clamp(Math.max(extent.x, extent.z), 0.5, 2)
    const middle = box.getCenter(new THREE.Vector3())
    const effects = this.battlefield.effects
    effects.explosion(middle, size * 1.1)
    for (let i = 0; i < 2 + Math.round(size * 2); i++) {
      const at = middle.clone().add(new THREE.Vector3((Math.random() - 0.5) * extent.x, (Math.random() - 0.3) * extent.y, (Math.random() - 0.5) * extent.z))
      effects.explosion(at, size * (0.4 + Math.random() * 0.3), 0.12 + i * 0.16 + Math.random() * 0.1)
    }
    effects.scorch(middle, size * 2)
    object.traverse((node) => {
      const mesh = node as THREE.Mesh
      if (!mesh.isMesh) return
      for (const mat of [mesh.material].flat() as THREE.MeshStandardMaterial[]) {
        mat.color?.multiplyScalar(CHARRED)
        mat.emissive?.setScalar(0)
        if ('roughness' in mat) mat.roughness = 1
      }
    })
    return size
  }

  private animate(seconds: number) {
    for (const item of this.dying) {
      item.time += seconds
      if (item.wreck) {
        // thrown up by the blast, it comes down crooked and burns out
        const { size, tilt } = item.wreck
        const hop = Math.min(1, item.time / 0.45)
        item.object.position.y = item.ground + 0.12 * size * 4 * hop * (1 - hop)
        item.object.rotation.x = tilt.x * Math.min(1, item.time / 0.3)
        item.object.rotation.z = tilt.y * Math.min(1, item.time / 0.3)
        const burning = 1 - item.time / WRECK_SECONDS
        if (item.time > 0.2 && Math.random() < burning + 0.2) {
          this.battlefield.effects.burn(item.object.position.clone().setY(item.ground + 0.15 * size)
            .add(new THREE.Vector3((Math.random() - 0.5) * size * 0.5, 0, (Math.random() - 0.5) * size * 0.5)), 0.25 + 0.35 * size * Math.max(0.3, burning))
        }
        if (item.time > WRECK_SECONDS - 0.8) item.object.position.y = item.ground - (item.time - (WRECK_SECONDS - 0.8)) * 0.3
        continue
      }
      // no longer updated by the battlefield: the death clip runs on here
      item.unit?.update(seconds)
      const fall = Math.min(1, item.time / 0.45)
      item.object.rotation.x = item.fall * (Math.PI / 2) * fall * fall
      // run down: pressed flat at once
      if (item.crushed) item.object.scale.y = Math.max(0.12, 1 - item.time / 0.12)
      // after lying a while it sinks into the ground
      if (item.time > CORPSE_SECONDS - 0.6) item.object.position.y = item.ground - (item.time - (CORPSE_SECONDS - 0.6)) * 0.4
    }
    // a destroyed building sinks together and disappears
    for (const item of this.collapsing) {
      item.time += seconds
      // a crushed sandbag is pressed flat and sinks, without fire
      if (item.crushed) {
        const t = Math.min(1, item.time / FLATTEN_SECONDS)
        item.object.scale.y = Math.max(0.05, 1 - Math.sqrt(t))
        item.object.position.y = item.ground - 0.05 * t
        continue
      }
      const t = Math.min(1, item.time / COLLAPSE_SECONDS)
      item.object.scale.y = Math.max(0.05, 1 - t * t)
      item.object.position.y = item.ground - 0.1 * t
      // fire and smoke out of the ruins
      const f = item.object.userData.footprint as { x: number, z: number, w: number, h: number }
      if (t < 1) this.battlefield.effects.burn(new THREE.Vector3(f.x + Math.random() * f.w, 0.15, f.z + Math.random() * f.h), 0.5)
    }
    for (const item of this.collapsing.filter(c => c.time > COLLAPSE_SECONDS + 0.5)) this.battlefield.removeEffect(item.object)
    this.collapsing.splice(0, this.collapsing.length, ...this.collapsing.filter(c => c.time <= COLLAPSE_SECONDS + 0.5))
    const gone = (d: { time: number, wreck?: unknown }) => d.time > (d.wreck ? WRECK_SECONDS : CORPSE_SECONDS)
    for (const item of this.dying.filter(gone)) this.battlefield.removeEffect(item.object)
    this.dying.splice(0, this.dying.length, ...this.dying.filter(d => !gone(d)))
  }

  dispose() {
    for (const resource of [this.shellGeometry, this.shellMaterial, this.rocketGeometry, this.rocketMaterial,
      this.grenadeGeometry, this.grenadeMaterial]) resource.dispose()
  }
}
