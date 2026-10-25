import * as THREE from 'three'
import { Battlefield } from './battlefield'
import type { BuildInfo } from './cameos'
import type { Unit } from './unit'

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
 */

/** The game runs 15 frames a second at normal speed */
const FRAMES_PER_SECOND = 15
/** How often a unit walking after its target looks where the target is now */
const CHASE_INTERVAL = 0.5
/** Seconds a destroyed unit lies on the ground before it disappears */
const CORPSE_SECONDS = 3
/** Infantry lying on the ground takes this share of the damage */
const PRONE_DAMAGE = 0.5
/** Seconds a destroyed building takes to collapse */
const COLLAPSE_SECONDS = 1.6

interface Fighter {
  target?: THREE.Object3D
  /** Attack-move: walking there, but fighting every enemy met on the way */
  attackMove?: THREE.Vector3
  /** The target was ordered by the player (otherwise picked by the unit itself) */
  ordered: boolean
  cooldown: number
  chase: number
}

export interface CombatEffects {
  /** A shot is fired (sound) */
  fire: (attacker: THREE.Object3D, info: BuildInfo) => void
  /** A unit was destroyed (death cry) */
  die: (victim: THREE.Object3D, info: BuildInfo) => void
  /** A building was destroyed */
  destroyed?: (building: THREE.Object3D) => void
}

export class Combat {
  private readonly fighters = new Map<Unit, Fighter>()
  private readonly dying: { object: THREE.Object3D, time: number, fall: number }[] = []
  private readonly collapsing: { object: THREE.Object3D, time: number }[] = []
  private readonly flashes: { object: THREE.Object3D, time: number }[] = []
  private readonly flashGeometry = new THREE.SphereGeometry(0.05, 8, 6)
  private readonly flashMaterial = new THREE.MeshBasicMaterial({ color: 0xffe28a, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })
  private readonly puffMaterial = new THREE.MeshBasicMaterial({ color: 0xcfc4a8, transparent: true, opacity: 0.7, depthWrite: false })

  constructor(
    private readonly battlefield: Battlefield,
    private readonly infoOf: (object: THREE.Object3D) => BuildInfo | undefined,
    private readonly effects: CombatEffects,
  ) {}

  /** Hit points left of an object, starting at its Strength= */
  private hp(object: THREE.Object3D) {
    const info = this.infoOf(object)
    object.userData.hp ??= info?.strength ?? 100
    return object.userData.hp as number
  }

  /** Whether `a` and `b` are on opposite sides */
  static hostile(a: THREE.Object3D, b: THREE.Object3D) {
    if (a.userData.owner === 'neutral' || b.userData.owner === 'neutral') return false
    return Battlefield.own(a) !== Battlefield.own(b)
  }

  /** Whether the selected units could attack an object (it is an enemy, they have weapons) */
  canAttack(selection: THREE.Object3D[], target: THREE.Object3D) {
    return selection.some(object => object.userData.unit && Battlefield.own(object) && Combat.hostile(object, target)
      && this.infoOf(object)?.weapon)
  }

  /** Orders units to attack a target. */
  attack(attackers: THREE.Object3D[], target: THREE.Object3D) {
    for (const object of attackers) {
      const unit = object.userData.unit as Unit | undefined
      if (!unit || !Combat.hostile(object, target) || !this.infoOf(object)?.weapon) continue
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

  update(seconds: number, speed: number) {
    const dt = seconds * speed
    for (const unit of [...this.battlefield.units]) {
      const object = unit.object
      if (object.userData.dead) continue
      const info = this.infoOf(object)
      const weapon = info?.weapon
      if (!weapon) continue
      const fighter = this.fighters.get(unit) ?? { ordered: false, cooldown: 0, chase: 0 }
      this.fighters.set(unit, fighter)
      fighter.cooldown = Math.max(0, fighter.cooldown - dt)

      if (fighter.target?.userData.dead || (fighter.target && !fighter.target.parent)) fighter.target = undefined
      // attack-move: stop for every enemy in range, go on when it is down
      if (fighter.attackMove && !fighter.target) {
        const enemy = this.nearestEnemy(object, weapon.range)
        if (enemy) {
          fighter.target = enemy
          fighter.ordered = false
        }
        else if (!unit.walking) {
          if (object.position.distanceTo(fighter.attackMove) < 0.6) fighter.attackMove = undefined
          else this.battlefield.walk(unit, fighter.attackMove)
        }
      }
      // standing idle: guard, attack the nearest enemy within sight
      const sight = Math.max(weapon.range, info!.sight)
      if (!fighter.target && !unit.walking) {
        fighter.target = this.nearestEnemy(object, sight)
        fighter.ordered = false
      }
      const target = fighter.target
      if (!target) continue

      const distance = Battlefield.reach(object.position, target)
      if (distance > weapon.range) {
        // a target it picked itself is let go once out of sight; an ordered one is chased
        if (!fighter.ordered && distance > sight + 1) {
          fighter.target = undefined
          continue
        }
        fighter.chase -= seconds
        if (!unit.walking || fighter.chase <= 0) {
          fighter.chase = CHASE_INTERVAL
          // up to the target, on the way round buildings, until it is in range
          const aim = Battlefield.closestPoint(object.position, target)
          const way = aim.clone().sub(object.position).setY(0)
          const length = way.length()
          const stopAt = length > 0 ? object.position.clone().addScaledVector(way, Math.max(0, 1 - (weapon.range * 0.85) / length)) : aim
          this.battlefield.walk(unit, stopAt)
        }
        continue
      }
      if (unit.walking) unit.stop()
      const aimed = unit.face(Battlefield.closestPoint(object.position, target), seconds)
      if (aimed && fighter.cooldown <= 0) {
        fighter.cooldown = weapon.rof / FRAMES_PER_SECOND
        this.fire(object, target, info!)
      }
    }
    this.animate(seconds)
  }

  /** The nearest enemy unit or building within `range` (units first when about as near) */
  private nearestEnemy(object: THREE.Object3D, range: number) {
    let best: THREE.Object3D | undefined
    let bestDistance = range
    const candidates = [...this.battlefield.units.map(u => u.object), ...this.battlefield.structureObjects]
    for (const other of candidates) {
      if (other.userData.dead || !Combat.hostile(object, other)) continue
      // buildings count a little farther, so soldiers deal with soldiers first
      const d = Battlefield.reach(object.position, other) + (other.userData.footprint ? 0.5 : 0)
      if (d <= bestDistance) {
        best = other
        bestDistance = d
      }
    }
    return best
  }

  private fire(attacker: THREE.Object3D, target: THREE.Object3D, info: BuildInfo) {
    const weapon = info.weapon!
    this.effects.fire(attacker, info)
    // muzzle flash in front of the soldier, a puff of dust at the target
    const forward = new THREE.Vector3(Math.sin(attacker.rotation.y), 0, Math.cos(attacker.rotation.y))
    const flash = new THREE.Mesh(this.flashGeometry, this.flashMaterial)
    const lying = (attacker.userData.unit as Unit | undefined)?.prone
    flash.position.copy(attacker.position).addScaledVector(forward, lying ? 0.3 : 0.18).setY(lying ? 0.08 : 0.32)
    this.addFlash(flash)
    const puff = new THREE.Mesh(this.flashGeometry, this.puffMaterial)
    const hitPoint = target.userData.footprint ? Battlefield.closestPoint(attacker.position, target).setY(0.2) : target.position
    puff.position.copy(hitPoint).add(new THREE.Vector3((Math.random() - 0.5) * 0.15, 0.12 + Math.random() * 0.2, (Math.random() - 0.5) * 0.15))
    puff.scale.setScalar(1.6)
    this.addFlash(puff)

    const targetInfo = this.infoOf(target)
    const verses = weapon.verses[targetInfo?.armor ?? 0] ?? 1
    // infantry under fire throws itself down, and is harder to hurt there
    const victim = target.userData.unit as Unit | undefined
    const cover = victim?.prone ? PRONE_DAMAGE : 1
    victim?.takeFire()
    const hp = this.hp(target) - weapon.damage * verses * cover
    target.userData.hp = hp
    target.userData.health = Math.max(0, hp / (targetInfo?.strength ?? 100))
    if (hp <= 0) this.kill(target)
  }

  private addFlash(object: THREE.Object3D) {
    this.battlefield.addEffect(object)
    this.flashes.push({ object, time: 0 })
  }

  /** Falls over, lies on the ground for a moment and disappears. */
  private kill(object: THREE.Object3D) {
    if (object.userData.dead) return
    object.userData.dead = true
    // a building collapses
    if (object.userData.footprint) {
      this.battlefield.removeStructure(object)
      this.effects.destroyed?.(object)
      this.collapsing.push({ object, time: 0 })
      return
    }
    const unit = object.userData.unit as Unit | undefined
    unit?.stop()
    const info = this.infoOf(object)
    if (info) this.effects.die(object, info)
    // no longer a target or selectable
    this.battlefield.remove(object)
    this.battlefield.addEffect(object)
    // standing soldiers fall over; lying ones are already down
    this.dying.push({ object, time: 0, fall: unit?.prone ? 0 : Math.random() < 0.5 ? 1 : -1 })
  }

  private animate(seconds: number) {
    for (const item of this.flashes) item.time += seconds
    for (const item of this.flashes.filter(f => f.time > 0.09)) this.battlefield.removeEffect(item.object)
    this.flashes.splice(0, this.flashes.length, ...this.flashes.filter(f => f.time <= 0.09))

    for (const item of this.dying) {
      item.time += seconds
      const fall = Math.min(1, item.time / 0.45)
      item.object.rotation.x = item.fall * (Math.PI / 2) * fall * fall
      // after lying a while it sinks into the ground
      if (item.time > CORPSE_SECONDS - 0.6) item.object.position.y = -(item.time - (CORPSE_SECONDS - 0.6)) * 0.4
    }
    // a destroyed building sinks together and disappears
    for (const item of this.collapsing) {
      item.time += seconds
      const t = Math.min(1, item.time / COLLAPSE_SECONDS)
      item.object.scale.y = Math.max(0.05, 1 - t * t)
      item.object.position.y = -0.1 * t
    }
    for (const item of this.collapsing.filter(c => c.time > COLLAPSE_SECONDS + 0.5)) this.battlefield.removeEffect(item.object)
    this.collapsing.splice(0, this.collapsing.length, ...this.collapsing.filter(c => c.time <= COLLAPSE_SECONDS + 0.5))
    for (const item of this.dying.filter(d => d.time > CORPSE_SECONDS)) this.battlefield.removeEffect(item.object)
    this.dying.splice(0, this.dying.length, ...this.dying.filter(d => d.time <= CORPSE_SECONDS))
  }

  dispose() {
    this.flashGeometry.dispose()
    this.flashMaterial.dispose()
    this.puffMaterial.dispose()
  }
}
