import type { Order, OrderResult } from '../orders'
import type { Owner } from '../players'
import { mulberry32 } from '../terrain'
import { type AiLevel, type AiProfile, type AiRules, DEFAULT_AI_RULES, type LevelRules, PROFILES } from './levels'
import type { BuildChoice, Observation, PlayerView, SeenStructure, SeenUnit, WorldQuery } from './view'

/** What a computer player needs of the game: what it sees, and someone to carry out its orders */
export interface World {
  observe: (owner: Owner) => Observation | undefined
  order: (owner: Owner, order: Order) => OrderResult
}

interface Point { x: number, z: number }

/**
 * Units it does not build to fight with, though armed: they fire only dug in or set up
 * (the artillery, the Juggernaut, the limpet drone) or only when aimed (the mobile EMP)
 */
const NOT_FOR_BATTLE = new Set(['ART2', 'JUGG', 'LIMPET', 'MOBILEMP'])
/** The harvester, the MCV */
const HARVESTER = 'HARV'
const MCV = 'MCV'
const YARD = 'GACNST'
/** How far (cells) round the base an enemy counts as an attack on it */
const BASE_ALERT = 5
/** How far (cells) round its harvesters an enemy is driven off */
const HARVESTER_ALERT = 5
/** Cells round a place it looks for room for a building */
const PLACE_SEARCH = 14
/** Seconds it leaves a building alone that found no room */
const NO_ROOM_SECONDS = 60
/** Seconds a team waits at its gathering point for the stragglers */
const REGROUP_SECONDS = 45
/** Seconds after which a team that got nowhere looks for another target */
const STUCK_SECONDS = 150
/** Credits from which it grows its base though its army is not yet big enough for the next attack */
const SPARE_CREDITS = 3000

/** The team it sends against an enemy */
interface Team {
  members: number[]
  enemy: Owner
  /** Gathering halfway, or on its way to the target */
  stage: 'regroup' | 'attack'
  goal: Point
  /** Game seconds when it set out for the goal */
  since: number
  /** Units it set out with */
  size: number
}

const distance = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.z - b.z)
const middle = (points: Point[]): Point => ({
  x: points.reduce((s, p) => s + p.x, 0) / points.length,
  z: points.reduce((s, p) => s + p.z, 0) / points.length,
})

/**
 * A computer player of the skirmish, at one of three levels (Leicht, Mittel, Schwer). It
 * plays by the rules of the human player: it starts with an MCV, builds its base by
 * the original's [AI] of RULES.INI (power first, refineries, barracks, war factory,
 * radar, then defences and more of each by their …Ratio=), keeps its harvesters
 * going, builds an army, defends its base and its harvesters and sends ever bigger
 * teams against the nearest enemy, the first after AttackDelay=, then every TeamDelays=.
 *
 * It only looks at the battlefield through a PlayerView and acts only through orders
 * (see World), like a player over the network would.
 */
export class ComputerPlayer {
  private readonly profile: AiProfile
  private readonly random: () => number
  /** Game seconds since it started */
  private clock = 0
  private wait = 0
  private buildWait = 0
  private repairWait = 0
  private nextAttack: number
  /** Teams sent so far */
  private sent = 0
  private team?: Team
  /** The enemy it goes for, while it is there */
  private enemy?: Owner
  /** Structures that found no room, until when it leaves them alone */
  private readonly noRoom = new Map<string, number>()
  /** Where its new units gather, and the factories already sending them there */
  private rally?: Point
  private readonly rallied = new Map<number, Point>()

  constructor(readonly id: Owner, readonly level: AiLevel, private readonly rules: AiRules = DEFAULT_AI_RULES, seed = 1) {
    this.profile = PROFILES[level]
    this.random = mulberry32(seed)
    this.nextAttack = rules.attackDelay * 60 * this.profile.firstAttack
  }

  /** Its level's rules: handicap, delays */
  get levelRules(): LevelRules {
    return this.rules.levels[this.level]
  }

  /** Game seconds pass; every so often it looks at the battlefield and gives its orders. */
  update(seconds: number, world: World) {
    this.clock += seconds
    this.buildWait -= seconds
    this.repairWait -= seconds
    this.wait -= seconds
    if (this.wait > 0) return
    this.wait = this.profile.think
    const seen = world.observe(this.id)
    if (!seen) return
    for (const order of this.think(seen.view, seen.query)) world.order(this.id, order)
  }

  /** What it does about what it sees now */
  think(view: PlayerView, query: WorldQuery): Order[] {
    const orders: Order[] = []
    this.deploy(view, query, orders)
    if (view.structures.some(s => s.type === YARD)) this.construct(view, query, orders)
    this.produce(view, orders)
    this.command(view, query, orders)
    this.repair(view, orders)
    return orders
  }

  /** How many of its buildings are of these kinds */
  private count(view: PlayerView, ids: string[]) {
    return view.structures.filter(s => ids.includes(s.type)).length
  }

  /** The middle of its base: the construction yard, else its buildings, else its MCV or where it started */
  private home(view: PlayerView): Point | undefined {
    const yard = view.structures.find(s => s.type === YARD)
    if (yard) return yard
    const base = view.structures.filter(s => !s.wall)
    if (base.length) return middle(base)
    return view.units.find(u => u.type === MCV) ?? view.starts.find(s => s.owner === view.me)
  }

  /** How far its base reaches from its middle */
  private reach(view: PlayerView, home: Point) {
    return Math.max(6, ...view.structures.filter(s => !s.wall).map(s => distance(s, home) + Math.max(s.cells.w, s.cells.h) / 2))
  }

  /** The way towards the enemy (the nearest one's start, else the middle of the map), as a unit vector */
  private front(view: PlayerView, home: Point): Point {
    const starts = view.starts.filter(s => s.owner !== view.me && this.alive(view, s.owner))
    const towards = starts.sort((a, b) => distance(a, home) - distance(b, home))[0] ?? view.centre
    const length = distance(towards, home)
    return length > 0.5 ? { x: (towards.x - home.x) / length, z: (towards.z - home.z) / length } : { x: 1, z: 0 }
  }

  /** Whether a player still has anything on the map */
  private alive(view: PlayerView, owner: Owner) {
    return view.enemies.structures.some(s => s.owner === owner && !s.wall) || view.enemies.units.some(u => u.owner === owner)
  }

  /** Unfolds its MCV where it stands, or drives it to the nearest place with room first */
  private deploy(view: PlayerView, query: WorldQuery, orders: Order[]) {
    for (const mcv of view.units.filter(u => u.type === MCV && !u.moving)) {
      if (query.canDeploy(mcv.id)) {
        orders.push({ type: 'deploy', unit: mcv.id })
        continue
      }
      // a new MCV goes back to where the base was
      const near = view.structures.some(s => s.type === YARD) ? mcv : this.home(view) ?? mcv
      const spot = this.findSpot(query, near, 3, 3, Infinity, 0, 1)
      if (spot) orders.push({ type: 'move', units: [mcv.id], x: spot.x + 1.5, z: spot.z + 1.5 })
    }
  }

  /** Builds its base: places what is ready, starts the next building */
  private construct(view: PlayerView, query: WorldQuery, orders: Order[]) {
    const job = view.production.structure
    if (job?.ready) {
      const choice = view.options.find(o => o.id === job.id)
      const spot = choice && this.place(choice, view, query)
      if (spot) orders.push({ type: 'place', id: job.id, ...spot })
      else {
        orders.push({ type: 'cancel', id: job.id })
        this.noRoom.set(job.id, this.clock + NO_ROOM_SECONDS)
      }
      return
    }
    if (job || this.buildWait > 0) return
    const next = this.nextStructure(view)
    if (!next) return
    orders.push({ type: 'build', id: next.id })
    this.buildWait = this.levelRules.buildDelay
  }

  /**
   * What to build next, like the original's computer: enough power first, then the
   * buildings a base needs, then more refineries, factories and defences as the base
   * grows (RefineryRatio= … of all its buildings, up to the …Limit= and its level's most)
   */
  private nextStructure(view: PlayerView): BuildChoice | undefined {
    const { rules, profile } = this
    const options = view.options.filter(o => o.structure && !o.wall && !((this.noRoom.get(o.id) ?? 0) > this.clock))
    const of = (ids: string[]) => options.filter(o => ids.includes(o.id))
    const surplus = view.power.output - view.power.drain
    const plant = of(rules.power).sort((a, b) => b.power - a.power)[0]
    // a gun for a component tower that has none yet
    const upgrade = this.towerGun(view, options)
    if (upgrade) return upgrade
    if (surplus < rules.powerSurplus && plant) return plant
    const base = view.structures.filter(s => !s.wall)
    if (base.length >= profile.buildings) return undefined
    // what a base needs, in this order: the money comes first
    const needs: [string[], number][] = [[rules.refinery, 1], [rules.barracks, 1], [rules.factory, 1], [rules.refinery, Math.min(2, profile.refineries)]]
    for (const [ids, wanted] of needs) {
      const choice = of(ids)[0]
      if (choice && this.count(view, ids) < wanted) return choice
    }
    // the rest of the base once there is an army for the next attack (or money to spare),
    // but for the harder levels a defence or two before that
    const defences = this.defences(view).length
    if (this.fighters(view).length < this.nextTeam() + this.levelRules.guards && view.credits < SPARE_CREDITS) {
      return defences < this.level ? this.defence(view, options, false) : undefined
    }
    const radar = of(rules.radar)[0]
    if (radar && this.count(view, rules.radar) < 1) return radar
    // then by their share of the base
    const wanted = (share: { ratio: number, limit: number }, most: number) =>
      Math.min(most, share.limit, Math.max(1, Math.ceil(share.ratio * base.length)))
    const antiAir = view.structures.filter(s => this.isAntiAir(view, s.type)).length
    const enemyAircraft = view.enemies.units.some(u => u.category === 'aircraft')
    const candidates: [BuildChoice | undefined, number][] = [
      [of(rules.refinery)[0], wanted(rules.refineries, profile.refineries) - this.count(view, rules.refinery)],
      [of(rules.factory)[0], wanted(rules.factories, this.level === 0 ? 1 : 2) - this.count(view, rules.factory)],
      [this.defence(view, options, false), wanted(rules.defenses, profile.defenses) - defences],
      [enemyAircraft ? this.defence(view, options, true) : undefined, wanted(rules.antiAir, 1 + this.level) - antiAir],
      [of(rules.barracks)[0], wanted(rules.barracksShare, this.level === 0 ? 1 : 2) - this.count(view, rules.barracks)],
      [this.level > 0 ? of(rules.tech)[0] : undefined, 1 - this.count(view, rules.tech)],
    ]
    const best = candidates.filter(([choice, missing]) => choice && missing > 0).sort((a, b) => b[1] - a[1])[0]
    if (best) return best[0]
    // power ahead of what is still to come
    return surplus < 2 * rules.powerSurplus ? plant : undefined
  }

  /** Its buildings that defend the base: armed ones, and towers waiting for their gun */
  private defences(view: PlayerView) {
    const factories = [...this.rules.factory, ...this.rules.barracks]
    return view.structures.filter(s => !factories.includes(s.type) && (s.armed || this.isTower(view, s.type)))
  }

  /** A building upgrades with guns go onto (the component tower) */
  private isTower(view: PlayerView, type: string) {
    return view.towers.includes(type)
  }

  /** Whether a building of its own fires only at aircraft */
  private isAntiAir(view: PlayerView, type: string) {
    const option = view.options.find(o => o.id === type)
    return !!option && option.armed && option.antiAir && !option.antiGround
  }

  /** The defence to build: against aircraft or the ground, a stronger one the harder it plays */
  private defence(view: PlayerView, options: BuildChoice[], antiAir: boolean) {
    const guns = options.filter(o => o.armed && !o.powersUp && (antiAir ? o.antiAir : o.antiGround && !(o.antiAir && !o.antiGround)))
    // GDI: the component tower, the guns come onto it afterwards
    const towers = options.filter(o => !o.armed && this.isTower(view, o.id))
    return this.pick([...guns, ...towers])
  }

  /** A gun for a component tower without one: against the ground (against aircraft if they come) */
  private towerGun(view: PlayerView, options: BuildChoice[]) {
    const bare = view.structures.find(s => s.freeSlot && !s.armed && this.isTower(view, s.type))
    if (!bare) return undefined
    const guns = options.filter(o => o.powersUp === bare.type && o.armed)
    const antiAir = view.enemies.units.some(u => u.category === 'aircraft') && this.random() < 0.3
    return this.pick(guns.filter(g => antiAir ? g.antiAir : g.antiGround)) ?? this.pick(guns)
  }

  /** One of the choices at random, the costly (strong) ones the likelier the harder it plays */
  private pick<T extends { cost: number }>(choices: T[]) {
    if (!choices.length) return undefined
    const weights = choices.map(c => Math.max(1, c.cost) ** this.profile.strength)
    let roll = this.random() * weights.reduce((s, w) => s + w, 0)
    for (const [i, choice] of choices.entries()) {
      roll -= weights[i]!
      if (roll <= 0) return choice
    }
    return choices.at(-1)
  }

  /**
   * Where a finished building goes (its lower corner): a refinery towards the Tiberium,
   * defences between the base and the enemy, factories on the front side, power plants
   * and the rest behind; with a cell free round it (AIBaseSpacing=) where there is room
   */
  private place(choice: BuildChoice, view: PlayerView, query: WorldQuery): Point | undefined {
    if (choice.powersUp) {
      const target = view.structures.find(s => s.type === choice.powersUp && s.freeSlot)
      return target && { x: target.cells.x, z: target.cells.z }
    }
    const home = this.home(view)
    if (!home) return undefined
    const front = this.front(view, home)
    const reach = this.reach(view, home)
    const at = (along: number, across = 0): Point => ({ x: home.x + front.x * along - front.z * across, z: home.z + front.z * along + front.x * across })
    let anchor: Point
    if (this.rules.refinery.includes(choice.id)) {
      const fields = [...view.tiberium].sort((a, b) => distance(a, home) - distance(b, home))
      anchor = fields[0] && distance(fields[0], home) < reach + 14 ? fields[0] : at(reach * 0.5, reach * 0.5)
    }
    else if (choice.armed || this.isTower(view, choice.id)) anchor = at(reach + 1, (this.random() - 0.5) * reach * 1.6)
    else if ([...this.rules.factory, ...this.rules.barracks].includes(choice.id)) anchor = at(reach * 0.6, (this.random() - 0.5) * reach)
    else anchor = at(-reach * 0.5, (this.random() - 0.5) * reach)
    const [w, h] = choice.foundation
    return this.findSpot(query, anchor, w, h, choice.adjacent, this.rules.baseSpacing)
      ?? this.findSpot(query, anchor, w, h, choice.adjacent, 0)
  }

  /** The lower corner of the free w × h place nearest to `near` (up to PLACE_SEARCH cells away) */
  private findSpot(query: WorldQuery, near: Point, w: number, h: number, adjacent: number, spacing: number, from = 0) {
    const cx = Math.round(near.x - w / 2)
    const cz = Math.round(near.z - h / 2)
    for (let r = from; r <= PLACE_SEARCH; r++) {
      const ring: [number, number][] = []
      for (let dx = -r; dx <= r; dx++) {
        for (let dz = -r; dz <= r; dz++) if (Math.max(Math.abs(dx), Math.abs(dz)) === r) ring.push([cx + dx, cz + dz])
      }
      ring.sort((a, b) => Math.hypot(a[0] - cx, a[1] - cz) - Math.hypot(b[0] - cx, b[1] - cz))
      const spot = ring.find(([x, z]) => query.canPlace(x, z, w, h, adjacent, spacing))
      if (spot) return { x: spot[0], z: spot[1] }
    }
    return undefined
  }

  /** Its fighting units: all but harvesters, MCVs and aircraft */
  private fighters(view: PlayerView) {
    return view.units.filter(u => !u.harvester && u.type !== MCV && u.category !== 'aircraft')
  }

  /** Keeps its factories busy: harvesters for its refineries, a new MCV for a lost yard, an army */
  private produce(view: PlayerView, orders: Order[]) {
    const { rules, profile } = this
    const queue = view.production.units
    const factory = this.count(view, rules.factory) > 0
    if ((!factory && this.count(view, rules.barracks) === 0) || queue.length >= 2) return
    const option = (id: string) => view.options.find(o => o.id === id)
    const queued = (id: string) => queue.filter(q => q === id).length
    // harvesters: each refinery brings one; lost ones are replaced, and the hard level
    // adds more when it has money to spare (a refinery unloads one at a time)
    const harvesters = view.units.filter(u => u.harvester).length + queued(HARVESTER)
    const perRefinery = view.credits > SPARE_CREDITS / 2 ? profile.harvesters : 1
    if (factory && option(HARVESTER) && harvesters < this.count(view, rules.refinery) * perRefinery) {
      orders.push({ type: 'build', id: HARVESTER })
      return
    }
    // a new construction yard
    const yard = view.structures.some(s => s.type === YARD) || view.units.some(u => u.type === MCV) || queued(MCV) > 0
    if (!yard && profile.rebuildYard && option(MCV)) {
      orders.push({ type: 'build', id: MCV })
      return
    }
    if (view.credits < rules.creditReserve || this.fighters(view).length + queue.length >= profile.army) return
    const unit = this.chooseUnit(view)
    if (unit) orders.push({ type: 'build', id: unit.id })
  }

  /** The next unit for its army: soldiers or vehicles (by its level's share), stronger ones the harder it plays */
  private chooseUnit(view: PlayerView) {
    const choices = view.options.filter(o => !o.structure && o.armed && o.antiGround && o.category !== 'aircraft' && !NOT_FOR_BATTLE.has(o.id))
    const infantry = choices.filter(c => c.category === 'infantry')
    const vehicles = choices.filter(c => c.category === 'vehicle')
    const soldiers = !vehicles.length || (infantry.length > 0 && this.random() < this.profile.infantry)
    return this.pick(soldiers ? infantry : vehicles)
  }

  /** Its army: gathering, defending the base and the harvesters, attacking in teams */
  private command(view: PlayerView, query: WorldQuery, orders: Order[]) {
    const home = this.home(view)
    if (!home) return
    const reach = this.reach(view, home)
    const front = this.front(view, home)
    this.gather(view, query, home, reach, front, orders)
    const fighters = this.fighters(view)
    const byId = new Map(fighters.map(u => [u.id, u]))
    if (this.team) this.team.members = this.team.members.filter(id => byId.has(id))
    const inTeam = new Set(this.team?.members)
    const guards = fighters.filter(u => !inTeam.has(u.id))
    const rally = this.rally!
    const ids = (units: SeenUnit[]) => units.map(u => u.id)

    // enemies at the base or at the harvesters: everyone at home goes for them
    const harvesters = view.units.filter(u => u.harvester)
    const threats = view.enemies.units.filter(e => !e.harvester && e.category !== 'aircraft'
      && (distance(e, home) < reach + BASE_ALERT || harvesters.some(h => distance(h, e) < HARVESTER_ALERT)))
    if (threats.length) {
      const threat = threats.sort((a, b) => distance(a, home) - distance(b, home))[0]!
      const free = guards.filter(u => !u.fighting)
      if (free.length) orders.push({ type: 'attackMove', units: ids(free), x: threat.x, z: threat.z })
      // a big attack on the base calls the team back (not on the easy level)
      const team = this.team
      if (team && this.level > 0 && threats.length >= Math.max(4, team.members.length / 2)) {
        orders.push({ type: 'attackMove', units: team.members, x: threat.x, z: threat.z })
        this.endTeam()
      }
    }
    else {
      // the others wait at the gathering point
      const strays = guards.filter(u => !u.moving && !u.fighting && distance(u, rally) > 5)
      if (strays.length) orders.push({ type: 'move', units: ids(strays), x: rally.x, z: rally.z })
    }

    if (this.team) this.lead(view, byId, orders)
    else if (this.clock >= this.nextAttack) this.attack(view, home, reach, guards, orders)
  }

  /** Where its new units gather: in front of the base, towards the enemy; its factories send them there */
  private gather(view: PlayerView, query: WorldQuery, home: Point, reach: number, front: Point, orders: Order[]) {
    const wanted = { x: home.x + front.x * (reach + 3), z: home.z + front.z * (reach + 3) }
    if (!this.rally || distance(this.rally, wanted) > 3) this.rally = query.openSpot(wanted.x, wanted.z)
    const factories = [...this.rules.factory, ...this.rules.barracks]
    for (const factory of view.structures.filter(s => factories.includes(s.type))) {
      if (this.rallied.get(factory.id) === this.rally) continue
      this.rallied.set(factory.id, this.rally)
      orders.push({ type: 'rally', factory: factory.id, ...this.rally })
    }
  }

  /** Sends a team out once it has enough units and the time has come */
  private attack(view: PlayerView, home: Point, reach: number, guards: SeenUnit[], orders: Order[]) {
    const ready = guards.filter(u => !u.fighting && distance(u, home) < reach + 15)
      // those nearest the base stay to guard it
      .sort((a, b) => distance(a, home) - distance(b, home))
    const keep = this.levelRules.guards
    if (ready.length < this.nextTeam() + keep) return
    const enemy = this.chooseEnemy(view, home)
    const members = ready.slice(keep)
    const target = enemy && this.chooseTarget(view, enemy, middle(members))
    if (!enemy || !target) return
    const from = middle(members)
    const stage = this.profile.regroup && distance(from, target) > 25 ? 'regroup' : 'attack'
    const goal = stage === 'regroup' ? { x: from.x + (target.x - from.x) * 0.55, z: from.z + (target.z - from.z) * 0.55 } : target
    this.team = { members: members.map(u => u.id), enemy, stage, goal, since: this.clock, size: members.length }
    orders.push({ type: 'attackMove', units: this.team.members, ...goal })
  }

  /** The team on its way: gathers, attacks, goes on to the next target, falls back when too few are left */
  private lead(view: PlayerView, byId: Map<number, SeenUnit>, orders: Order[]) {
    const team = this.team!
    const members = team.members.map(id => byId.get(id)!)
    if (!members.length || members.length < team.size * this.profile.retreat) {
      if (members.length) orders.push({ type: 'move', units: team.members, ...this.rally! })
      this.endTeam()
      return
    }
    const idle = members.filter(u => !u.moving && !u.fighting)
    const there = members.filter(u => distance(u, team.goal) < 6).length
    if (team.stage === 'regroup') {
      if (there >= members.length * 0.7 || this.clock - team.since > REGROUP_SECONDS) this.advance(view, members, orders)
      else {
        const lagging = idle.filter(u => distance(u, team.goal) >= 6)
        if (lagging.length) orders.push({ type: 'attackMove', units: lagging.map(u => u.id), ...team.goal })
      }
      return
    }
    // at the target with nothing left to fight there, or stuck: on to the next
    if ((idle.length === members.length && there >= members.length * 0.5) || this.clock - team.since > STUCK_SECONDS) {
      this.advance(view, members, orders)
      return
    }
    const lagging = idle.filter(u => distance(u, team.goal) >= 4)
    if (lagging.length) orders.push({ type: 'attackMove', units: lagging.map(u => u.id), ...team.goal })
  }

  /** The team goes for the next target of its enemy (another enemy once that one is beaten), or home if there is none */
  private advance(view: PlayerView, members: SeenUnit[], orders: Order[]) {
    const team = this.team!
    const from = middle(members)
    if (!this.alive(view, team.enemy)) team.enemy = this.chooseEnemy(view, from) ?? team.enemy
    const target = this.chooseTarget(view, team.enemy, from)
    if (!target) {
      orders.push({ type: 'move', units: team.members, ...this.rally! })
      this.endTeam()
      return
    }
    team.stage = 'attack'
    team.goal = target
    team.since = this.clock
    orders.push({ type: 'attackMove', units: team.members, ...target })
  }

  /** Units of the next attack team */
  private nextTeam() {
    return this.profile.team + this.profile.teamGrowth * this.sent
  }

  /** The team is back or gone: the next one comes after TeamDelays= */
  private endTeam() {
    this.team = undefined
    this.sent++
    this.nextAttack = this.clock + this.levelRules.teamDelay
  }

  /**
   * The enemy it goes for: the nearest one (any one on the easy level), as long as they
   * are still there
   */
  private chooseEnemy(view: PlayerView, from: Point): Owner | undefined {
    if (this.enemy && this.alive(view, this.enemy)) return this.enemy
    const owners = [...new Set([...view.enemies.structures.filter(s => !s.wall), ...view.enemies.units].map(t => t.owner))]
    if (!owners.length) return undefined
    const where = (owner: Owner): Point => view.starts.find(s => s.owner === owner)
      ?? middle([...view.enemies.structures, ...view.enemies.units].filter(t => t.owner === owner))
    this.enemy = this.level === 0
      ? owners[Math.floor(this.random() * owners.length)]
      : owners.sort((a, b) => distance(where(a), from) - distance(where(b), from))[0]
    return this.enemy
  }

  /**
   * Where to attack an enemy: next to their nearest building (on the hard level their
   * refineries and factories first), else at their nearest unit
   */
  private chooseTarget(view: PlayerView, enemy: Owner, from: Point): Point | undefined {
    const economy = [...this.rules.refinery, ...this.rules.factory, ...this.rules.barracks, YARD]
    const weight = (s: SeenStructure) => distance(s, from) * (this.profile.economyFirst && economy.includes(s.type) ? 0.6 : 1)
    const building = view.enemies.structures.filter(s => s.owner === enemy && !s.wall).sort((a, b) => weight(a) - weight(b))[0]
    if (building) return outside(building, from)
    return view.enemies.units.filter(u => u.owner === enemy).sort((a, b) => distance(a, from) - distance(b, from))[0]
  }

  /** Repairs its damaged buildings while there is money (RepairDelay= between two) */
  private repair(view: PlayerView, orders: Order[]) {
    if (this.repairWait > 0 || !this.profile.repairBelow || view.credits < this.rules.creditReserve + 300) return
    const damaged = view.structures.find(s => !s.repairing && !s.wall && s.health < this.profile.repairBelow)
    if (!damaged) return
    orders.push({ type: 'repair', building: damaged.id })
    this.repairWait = this.levelRules.repairDelay
  }
}

/** A point just outside a building's foundation, on the side facing `from` */
function outside(building: SeenStructure, from: Point): Point {
  const { x, z, w, h } = building.cells
  const edge = { x: Math.min(Math.max(from.x, x), x + w), z: Math.min(Math.max(from.z, z), z + h) }
  const away = { x: edge.x - building.x, z: edge.z - building.z }
  const length = Math.hypot(away.x, away.z) || 1
  return { x: edge.x + (away.x / length) * 1.5, z: edge.z + (away.z / length) * 1.5 }
}
