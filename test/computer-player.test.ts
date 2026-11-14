import { describe, expect, it } from 'vitest'
import { ComputerPlayer, type World } from '../app/lib/game/ai/computer-player'
import { type AiLevel, DEFAULT_AI_RULES, parseAiRules } from '../app/lib/game/ai/levels'
import type { BuildChoice, PlayerView, SeenStructure, SeenUnit, WorldQuery } from '../app/lib/game/ai/view'
import type { Order } from '../app/lib/game/orders'

const option = (id: string, more: Partial<BuildChoice> = {}): BuildChoice => ({
  id, structure: true, category: 'structure', cost: 500, power: -10, foundation: [2, 2], adjacent: 2,
  armed: false, antiAir: false, antiGround: false, wall: false, ...more,
})
const unitOption = (id: string, category: 'infantry' | 'vehicle', more: Partial<BuildChoice> = {}) =>
  option(id, { structure: false, category, power: 0, foundation: [1, 1], armed: true, antiGround: true, ...more })

/** GDI's options at the start of a base */
const GDI = [
  option('GAPOWR', { power: 100, cost: 300 }), option('PROC', { power: -30, cost: 2000, foundation: [4, 3] }),
  option('GAPILE', { cost: 300 }), option('GAWEAP', { cost: 2000, foundation: [4, 3] }), option('GARADR', { cost: 1000 }),
  option('GACTWR', { cost: 200, foundation: [1, 1] }), option('GAVULC', { cost: 150, armed: true, antiGround: true, powersUp: 'GACTWR', foundation: [1, 1] }),
  unitOption('E1', 'infantry', { cost: 120 }), unitOption('SMECH', 'vehicle', { cost: 500 }), unitOption('MMCH', 'vehicle', { cost: 800 }),
  unitOption('HARV', 'vehicle', { cost: 1400, armed: false, antiGround: false }), unitOption('MCV', 'vehicle', { cost: 2500, armed: false, antiGround: false }),
]

let nextId = 100
const building = (type: string, x: number, z: number, more: Partial<SeenStructure> = {}): SeenStructure => ({
  id: nextId++, type, owner: 'ai1', x: x + 1, z: z + 1, health: 1, cells: { x, z, w: 2, h: 2 },
  repairing: false, wall: false, armed: false, freeSlot: false, ...more,
})
const unit = (type: string, x: number, z: number, more: Partial<SeenUnit> = {}): SeenUnit => ({
  id: nextId++, type, owner: 'ai1', x, z, health: 1, category: 'vehicle', harvester: false, moving: false, fighting: false, ...more,
})

function view(more: Partial<PlayerView> = {}): PlayerView {
  return {
    me: 'ai1', credits: 10000, power: { output: 0, drain: 0 }, buildings: [], production: { units: [] },
    options: GDI, towers: ['GACTWR'], units: [], structures: [], enemies: { units: [], structures: [] }, tiberium: [],
    starts: [{ owner: 'ai1', x: 20, z: 20 }, { owner: 'player', x: 100, z: 100 }], centre: { x: 60, z: 60 },
    ...more,
  }
}

/** Room everywhere, except where its buildings stand */
const query = (structures: SeenStructure[] = []): WorldQuery => ({
  canPlace: (x, z, w, h, _adjacent, spacing = 0) => !structures.some(s => x - spacing < s.cells.x + s.cells.w && s.cells.x < x + w + spacing
    && z - spacing < s.cells.z + s.cells.h && s.cells.z < z + h + spacing),
  canDeploy: () => true,
  openSpot: (x, z) => ({ x, z }),
})

const yard = () => building('GACNST', 19, 19, { cells: { x: 19, z: 19, w: 3, h: 3 }, x: 20.5, z: 20.5 })
const of = (orders: Order[], type: Order['type']) => orders.filter(o => o.type === type)

describe('computer player', () => {
  it('unfolds its MCV first', () => {
    const ai = new ComputerPlayer('ai1', 1)
    const mcv = unit('MCV', 20, 20)
    expect(of(ai.think(view({ units: [mcv] }), query()), 'deploy')).toEqual([{ type: 'deploy', unit: mcv.id }])
  })

  it('drives its MCV to a place with room when it cannot unfold where it stands', () => {
    const ai = new ComputerPlayer('ai1', 1)
    const mcv = unit('MCV', 20, 20)
    const orders = ai.think(view({ units: [mcv] }), { ...query(), canDeploy: () => false })
    expect(of(orders, 'move')).toHaveLength(1)
  })

  it('builds its base in the order of the original: power, refinery, barracks, war factory, radar', () => {
    const ai = new ComputerPlayer('ai1', 2)
    const structures = [yard()]
    const built: string[] = []
    let power = { output: 0, drain: 0 }
    for (let step = 0; step < 6; step++) {
      // a while later, so it may start the next one (BuildDelay=)
      ai.update(10, { observe: () => undefined, order: () => ({ ok: true }) })
      const orders = ai.think(view({ structures: [...structures], power }), query(structures))
      const build = of(orders, 'build').find(o => o.type === 'build' && GDI.find(g => g.id === o.id)?.structure)
      if (build?.type !== 'build') break
      built.push(build.id)
      const choice = GDI.find(g => g.id === build.id)!
      power = choice.power > 0 ? { ...power, output: power.output + choice.power } : { ...power, drain: power.drain - choice.power }
      structures.push(building(build.id, 30 + step * 5, 30))
    }
    expect(built.slice(0, 5)).toEqual(['GAPOWR', 'PROC', 'GAPILE', 'GAWEAP', 'PROC'])
  })

  it('places what is ready on free ground, a cell away from its other buildings', () => {
    const ai = new ComputerPlayer('ai1', 1)
    const structures = [yard()]
    const orders = ai.think(view({ structures, power: { output: 100, drain: 0 }, production: { structure: { id: 'GAPOWR', ready: true }, units: [] } }), query(structures))
    const place = of(orders, 'place')[0]
    expect(place).toMatchObject({ type: 'place', id: 'GAPOWR' })
    if (place?.type !== 'place') return
    expect(query(structures).canPlace(place.x, place.z, 2, 2, 2, 1)).toBe(true)
  })

  it('cancels a building it finds no room for and leaves it alone for a while', () => {
    const ai = new ComputerPlayer('ai1', 1)
    const full = { ...query(), canPlace: () => false }
    const orders = ai.think(view({ structures: [yard()], production: { structure: { id: 'GARADR', ready: true }, units: [] } }), full)
    expect(of(orders, 'cancel')).toEqual([{ type: 'cancel', id: 'GARADR' }])
  })

  it('builds component towers as defences (GDI), though their guns come only once a tower stands', () => {
    const ai = new ComputerPlayer('ai1', 0)
    const base = [yard(), building('PROC', 25, 19), building('GAPILE', 19, 25), building('GAWEAP', 25, 25), building('GARADR', 30, 30)]
    const withoutGuns = GDI.filter(o => !o.powersUp)
    ai.update(10, { observe: () => undefined, order: () => ({ ok: true }) })
    const orders = ai.think(view({ structures: base, options: withoutGuns, power: { output: 500, drain: 0 } }), query(base))
    expect(of(orders, 'build')).toContainEqual({ type: 'build', id: 'GACTWR' })
  })

  it('puts a gun onto a component tower that has none', () => {
    const ai = new ComputerPlayer('ai1', 1)
    const tower = building('GACTWR', 30, 30, { cells: { x: 30, z: 30, w: 1, h: 1 }, freeSlot: true })
    ai.update(10, { observe: () => undefined, order: () => ({ ok: true }) })
    const orders = ai.think(view({ structures: [yard(), tower], power: { output: 500, drain: 0 } }), query())
    expect(of(orders, 'build')).toContainEqual({ type: 'build', id: 'GAVULC' })
    const place = ai.think(view({ structures: [yard(), tower], power: { output: 500, drain: 0 }, production: { structure: { id: 'GAVULC', ready: true }, units: [] } }), query())
    expect(of(place, 'place')).toEqual([{ type: 'place', id: 'GAVULC', x: 30, z: 30 }])
  })

  it('replaces lost harvesters and builds an army once it has factories', () => {
    const ai = new ComputerPlayer('ai1', 1)
    const base = [yard(), building('PROC', 25, 19), building('GAPILE', 19, 25), building('GAWEAP', 25, 25)]
    expect(of(ai.think(view({ structures: base, power: { output: 500, drain: 0 } }), query(base)), 'build')).toContainEqual({ type: 'build', id: 'HARV' })
    const harvester = unit('HARV', 30, 30, { harvester: true })
    const orders = of(ai.think(view({ structures: base, units: [harvester], power: { output: 500, drain: 0 } }), query(base)), 'build')
    expect(orders.some(o => o.type === 'build' && ['E1', 'SMECH', 'MMCH'].includes(o.id))).toBe(true)
  })

  it('sends its factories\' units to a gathering point in front of the base', () => {
    const ai = new ComputerPlayer('ai1', 1)
    const factory = building('GAWEAP', 25, 25)
    const rally = of(ai.think(view({ structures: [yard(), factory] }), query()), 'rally')
    expect(rally).toHaveLength(1)
    // towards the enemy (down the map from (20, 20) to (100, 100))
    const order = rally[0]!
    if (order.type === 'rally') expect(order.x + order.z).toBeGreaterThan(41)
  })

  it('defends its base: the units at home go for enemies that come near', () => {
    const ai = new ComputerPlayer('ai1', 1)
    const guards = [unit('E1', 30, 30, { category: 'infantry' }), unit('SMECH', 31, 30)]
    const intruder = { ...unit('BGGY', 24, 24), owner: 'player' }
    const orders = ai.think(view({ structures: [yard()], units: guards, enemies: { units: [intruder], structures: [] } }), query())
    expect(of(orders, 'attackMove')).toContainEqual({ type: 'attackMove', units: guards.map(g => g.id), x: 24, z: 24 })
  })

  for (const [level, minutes] of [[0, 8], [1, 5], [2, 3]] as const) {
    it(`level ${level}: attacks with a team after about ${minutes} minutes (AttackDelay=), keeping guards at home`, () => {
      const ai = new ComputerPlayer('ai1', level as AiLevel)
      const army = Array.from({ length: 16 }, (_, i) => unit('SMECH', 30 + (i % 4), 30 + Math.floor(i / 4)))
      const enemyBase = { ...building('GAPOWR', 99, 99), owner: 'player' }
      const look = () => view({ structures: [yard()], units: army, enemies: { units: [], structures: [enemyBase] } })
      const attacks = () => of(ai.think(look(), query()), 'attackMove')
      ai.update(minutes * 60 - 20, { observe: () => undefined, order: () => ({ ok: true }) })
      expect(attacks()).toEqual([])
      ai.update(30, { observe: () => undefined, order: () => ({ ok: true }) })
      const sent = attacks()
      expect(sent).toHaveLength(1)
      const team = sent[0]!.type === 'attackMove' ? sent[0]!.units : []
      expect(team.length).toBe(16 - DEFAULT_AI_RULES.levels[level]!.guards)
    })
  }

  it('gives its orders through the world, as plain data', () => {
    const ai = new ComputerPlayer('ai1', 2)
    const given: Order[] = []
    const world: World = {
      observe: () => ({ view: view({ units: [unit('MCV', 20, 20)] }), query: query() }),
      order: (owner, order) => {
        expect(owner).toBe('ai1')
        given.push(order)
        return { ok: true }
      },
    }
    ai.update(1, world)
    expect(given.length).toBeGreaterThan(0)
    expect(JSON.parse(JSON.stringify(given))).toEqual(given)
  })
})

describe('computer player rules', () => {
  it('reads [AI] and the levels from RULES.INI: the hard computer gets [Easy]\'s handicap, the easy one [Difficult]\'s', () => {
    const ini = new Map([
      ['AI', new Map([['POWERSURPLUS', '75'], ['ATTACKDELAY', '4'], ['REFINERYRATIO', '.2'], ['REFINERYLIMIT', '3']])],
      ['GENERAL', new Map([['TEAMDELAYS', '1500,3000,4500'], ['MINIMUMAIDEFENSIVETEAMS', '5,3,1']])],
      ['EASY', new Map([['ARMOR', '1.5'], ['ROF', '.5'], ['BUILDTIME', '.7'], ['BUILDDELAY', '.02']])],
      ['DIFFICULT', new Map([['ARMOR', '.6'], ['ROF', '1.4'], ['BUILDDELAY', '.2']])],
    ])
    const rules = parseAiRules(ini)
    expect(rules.powerSurplus).toBe(75)
    expect(rules.attackDelay).toBe(4)
    expect(rules.refineries).toEqual({ ratio: 0.2, limit: 3 })
    const [easy, medium, hard] = rules.levels
    expect(hard).toMatchObject({ armor: 1.5, rof: 0.5, buildTime: 0.7, teamDelay: 100, guards: 5 })
    expect(hard.buildDelay).toBeCloseTo(1.2)
    expect(easy).toMatchObject({ armor: 0.6, rof: 1.4, teamDelay: 300, guards: 1 })
    expect(easy.buildDelay).toBeCloseTo(12)
    // missing values: the original's
    expect(medium).toMatchObject({ armor: 1, rof: 1, teamDelay: 200, guards: 3 })
    expect(rules.factory).toEqual(DEFAULT_AI_RULES.factory)
  })
})
