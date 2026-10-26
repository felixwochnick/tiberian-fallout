import * as THREE from 'three'
import { Battlefield } from './battlefield'
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
 * Crushers (Crusher=: the Titan, the harvester, the MCV) drive over the sandbags of
 * their enemies, which burst, and run enemy infantry down (Crushable=); their own
 * sandbags they drive round.
 */

/** The game runs 15 frames a second at normal speed */
const FRAMES_PER_SECOND = 15
/** How often a unit walking after its target looks where the target is now */
const CHASE_INTERVAL = 0.5
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
}

export interface CombatEffects {
  /** A shot is fired (sound) */
  fire: (attacker: THREE.Object3D, info: BuildInfo) => void
  /** A unit was destroyed (death cry) */
  die: (victim: THREE.Object3D, info: BuildInfo) => void
  /** A building was destroyed */
  destroyed?: (building: THREE.Object3D) => void
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
  }[] = []
  private readonly collapsing: { object: THREE.Object3D, time: number, crushed: boolean }[] = []
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
    return Battlefield.own(a) !== Battlefield.own(b)
  }

  /** Whether the selected units could attack an object (it is an enemy, they have weapons) */
  canAttack(selection: THREE.Object3D[], target: THREE.Object3D) {
    if (Battlefield.isWall(target)) return false
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
    this.crush()
    this.fly(dt)
    this.animate(seconds)
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

  /** The nearest enemy unit or building within `range` (units first when about as near) */
  private nearestEnemy(object: THREE.Object3D, range: number) {
    let best: THREE.Object3D | undefined
    let bestDistance = range
    const candidates = [...this.battlefield.units.map(u => u.object), ...this.battlefield.structureObjects]
    for (const other of candidates) {
      // walls are never picked as a target
      if (other.userData.dead || !Combat.hostile(object, other) || Battlefield.isWall(other)) continue
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
    // the walkers fire with their own clip (barrels, recoil, muzzle flashes at the
    // guns); for the others a muzzle flash in front of the soldier
    const shooter = attacker.userData.unit as Unit | undefined
    const muzzle = this.muzzle(attacker)
    const aim = Combat.aimPoint(muzzle, target)
    shooter?.fire()
    // the flash and a wisp of smoke at the muzzle (heavy guns: more of both)
    this.battlefield.effects.muzzleFlash(muzzle, aim.clone().sub(muzzle), weapon.damage >= HEAVY_DAMAGE)
    if (!weapon.projectile) {
      this.impact(attacker, target, weapon, aim, true)
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
  private muzzle(attacker: THREE.Object3D) {
    let muzzles = attacker.userData.muzzles as THREE.Object3D[] | undefined
    if (!muzzles) {
      muzzles = []
      attacker.traverse((node) => {
        if (node.name.startsWith('Flash') && !node.parent?.name.startsWith('Flash')) muzzles!.push(node)
      })
      attacker.userData.muzzles = muzzles
    }
    if (muzzles.length) {
      const shot = attacker.userData.shotCount = ((attacker.userData.shotCount as number | undefined) ?? -1) + 1
      return muzzles[shot % muzzles.length]!.getWorldPosition(new THREE.Vector3())
    }
    const forward = new THREE.Vector3(Math.sin(attacker.rotation.y), 0, Math.cos(attacker.rotation.y))
    const lying = (attacker.userData.unit as Unit | undefined)?.prone
    return attacker.position.clone().addScaledVector(forward, lying ? 0.3 : 0.18).setY(lying ? 0.08 : 0.32)
  }

  /** The point a shot from `from` goes for: the unit, or the nearest wall of a building */
  private static aimPoint(from: THREE.Vector3, target: THREE.Object3D) {
    return Battlefield.closestPoint(from, target).setY(AIM_HEIGHT)
  }

  /** Moves the projectiles on; at the end of their way they hit. */
  private fly(dt: number) {
    for (const shot of [...this.shots]) {
      const { weapon, object } = shot
      // a rocket steers after its target while that is still there
      if (weapon.projectile!.homing && !shot.target.userData.dead) shot.to = Combat.aimPoint(object.position, shot.target)
      const length = Math.max(0.05, shot.from.distanceTo(shot.to))
      shot.progress = Math.min(1, shot.progress + (weapon.speed * dt) / length)
      const position = Combat.along(shot, shot.progress)
      const back = object.position.clone().sub(position)
      if (back.lengthSq() > 1e-8) object.lookAt(position)
      object.position.copy(position)
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

  /** Damage times the warhead's Verses= factor for the victim's Armor=, times `share` (of an explosion). */
  private damage(target: THREE.Object3D, weapon: Weapon, share: number) {
    const targetInfo = this.infoOf(target)
    // walls only take damage from explosives (Wall= of the warhead), not from rifles
    const verses = Battlefield.isWall(target) && !weapon.wall ? 0 : weapon.verses[targetInfo?.armor ?? 0] ?? 1
    // infantry under fire throws itself down, and is harder to hurt there
    const victim = target.userData.unit as Unit | undefined
    const cover = victim?.prone ? PRONE_DAMAGE : 1
    victim?.takeFire()
    const hp = this.hp(target) - weapon.damage * verses * cover * share
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
      this.battlefield.effects.crush(new THREE.Vector3(footprint.x + footprint.w / 2, 0, footprint.z + footprint.h / 2), true)
      this.battlefield.removeStructure(object)
      this.effects.destroyed?.(object)
      this.collapsing.push({ object, time: 0, crushed })
      return
    }
    // a building collapses in explosions, the first few heard one after the other
    if (footprint) {
      const info = this.infoOf(object)
      for (let i = 0; i < 3 + footprint.w * footprint.h / 2; i++) {
        const at = new THREE.Vector3(footprint.x + Math.random() * footprint.w, 0.1 + Math.random() * 0.4, footprint.z + Math.random() * footprint.h)
        this.battlefield.effects.explosion(at, 0.6 + Math.random() * 0.5, i * 0.18)
        if (info && i < BLAST_SOUNDS && i % 2 === 0) this.effects.blast?.(object, info, i * 0.18)
      }
      this.battlefield.removeStructure(object)
      this.effects.destroyed?.(object)
      this.collapsing.push({ object, time: 0, crushed })
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
      this.dying.push({ object, time: 0, fall: 0, crushed, wreck: { size, tilt: new THREE.Vector2(Math.random() - 0.5, Math.random() - 0.5).multiplyScalar(0.35) } })
      return
    }
    if (crushed) this.battlefield.effects.crush(object.position, false)
    if (info) this.effects.die(object, info)
    // no longer a target or selectable
    this.battlefield.remove(object)
    this.battlefield.addEffect(object)
    // soldiers play their death clip (shot: they slump, blown up: thrown back); models
    // without one fall over stiffly, lying ones are already down
    const prone = unit?.prone
    const animated = !crushed && !!unit?.die(death)
    this.dying.push({ object, time: 0, fall: animated || prone || crushed ? 0 : Math.random() < 0.5 ? 1 : -1, crushed, unit: animated ? unit : undefined })
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
        item.object.position.y = 0.12 * size * 4 * hop * (1 - hop)
        item.object.rotation.x = tilt.x * Math.min(1, item.time / 0.3)
        item.object.rotation.z = tilt.y * Math.min(1, item.time / 0.3)
        const burning = 1 - item.time / WRECK_SECONDS
        if (item.time > 0.2 && Math.random() < burning + 0.2) {
          this.battlefield.effects.burn(item.object.position.clone().setY(0.15 * size)
            .add(new THREE.Vector3((Math.random() - 0.5) * size * 0.5, 0, (Math.random() - 0.5) * size * 0.5)), 0.25 + 0.35 * size * Math.max(0.3, burning))
        }
        if (item.time > WRECK_SECONDS - 0.8) item.object.position.y = -(item.time - (WRECK_SECONDS - 0.8)) * 0.3
        continue
      }
      // no longer updated by the battlefield: the death clip runs on here
      item.unit?.update(seconds)
      const fall = Math.min(1, item.time / 0.45)
      item.object.rotation.x = item.fall * (Math.PI / 2) * fall * fall
      // run down: pressed flat at once
      if (item.crushed) item.object.scale.y = Math.max(0.12, 1 - item.time / 0.12)
      // after lying a while it sinks into the ground
      if (item.time > CORPSE_SECONDS - 0.6) item.object.position.y = -(item.time - (CORPSE_SECONDS - 0.6)) * 0.4
    }
    // a destroyed building sinks together and disappears
    for (const item of this.collapsing) {
      item.time += seconds
      // a crushed sandbag is pressed flat and sinks, without fire
      if (item.crushed) {
        const t = Math.min(1, item.time / FLATTEN_SECONDS)
        item.object.scale.y = Math.max(0.05, 1 - Math.sqrt(t))
        item.object.position.y = -0.05 * t
        continue
      }
      const t = Math.min(1, item.time / COLLAPSE_SECONDS)
      item.object.scale.y = Math.max(0.05, 1 - t * t)
      item.object.position.y = -0.1 * t
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
