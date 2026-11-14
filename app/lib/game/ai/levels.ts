import type { Handicap } from '../players'

/** The computer player's levels of the skirmish dialog: 0 Leicht, 1 Mittel, 2 Schwer */
export type AiLevel = 0 | 1 | 2

/**
 * What a computer player plays with at a level, from RULES.INI like in the original:
 * the handicap of [Easy], [Normal] or [Difficult] – the other way round, as the original
 * hands them to the computer: the hard computer player gets [Easy]'s (sturdier units,
 * faster fire and production), the easy one [Difficult]'s –, how long it waits between
 * two buildings and two repairs (BuildDelay=, RepairDelay=), between two attack teams
 * (TeamDelays= of [General]) and how many units it keeps at home
 * (MinimumAIDefensiveTeams=).
 */
export interface LevelRules extends Handicap {
  /** Seconds between two buildings it starts */
  buildDelay: number
  /** Seconds between two repairs it starts */
  repairDelay: number
  /** Seconds between two attack teams */
  teamDelay: number
  /** Units it keeps at home when it attacks */
  guards: number
}

/** How much of the base a kind of building should be (…Ratio=), and how many at most (…Limit=) */
export interface Share { ratio: number, limit: number }

/** The computer player's rules: [AI] of RULES.INI and the levels */
export interface AiRules {
  /** Which buildings are of each kind (BuildPower=, BuildRefinery= …) */
  power: string[]
  refinery: string[]
  barracks: string[]
  factory: string[]
  radar: string[]
  tech: string[]
  /** Power it keeps in hand over what its base uses (PowerSurplus=) */
  powerSurplus: number
  /** Credits it keeps (CreditReserve=) */
  creditReserve: number
  /** Minutes before the first attack (AttackDelay=) */
  attackDelay: number
  /** Cells it keeps free between its buildings (AIBaseSpacing=) */
  baseSpacing: number
  refineries: Share
  barracksShare: Share
  factories: Share
  defenses: Share
  antiAir: Share
  /** Leicht, Mittel, Schwer */
  levels: [LevelRules, LevelRules, LevelRules]
}

/** The game logic's frames a second (TeamDelays= is in frames) */
const FRAMES_PER_SECOND = 15

/** The values of Tiberian Sun's RULES.INI (with Firestorm), for when it is not loaded */
export const DEFAULT_AI_RULES: AiRules = {
  power: ['NAPOWR', 'GAPOWR', 'NAAPWR'],
  refinery: ['PROC'],
  barracks: ['NAHAND', 'GAPILE'],
  factory: ['GAWEAP', 'NAWEAP'],
  radar: ['GARADR', 'NARADR'],
  tech: ['NATECH', 'GATECH'],
  powerSurplus: 50,
  creditReserve: 100,
  attackDelay: 5,
  baseSpacing: 1,
  refineries: { ratio: 0.16, limit: 4 },
  barracksShare: { ratio: 0.16, limit: 2 },
  factories: { ratio: 0.1, limit: 2 },
  defenses: { ratio: 0.4, limit: 40 },
  antiAir: { ratio: 0.14, limit: 10 },
  levels: [
    // [Difficult]
    { armor: 0.8, rof: 1.2, buildTime: 1, buildDelay: 6, repairDelay: 3, teamDelay: 3600 / FRAMES_PER_SECOND, guards: 2 },
    // [Normal]
    { armor: 1, rof: 1, buildTime: 1, buildDelay: 1.8, repairDelay: 1.2, teamDelay: 2700 / FRAMES_PER_SECOND, guards: 3 },
    // [Easy]
    { armor: 1.2, rof: 0.8, buildTime: 0.8, buildDelay: 1.8, repairDelay: 1.2, teamDelay: 2250 / FRAMES_PER_SECOND, guards: 4 },
  ],
}

type Ini = ReadonlyMap<string, ReadonlyMap<string, string>>

/** The computer player's rules from RULES.INI (sections and keys in capitals), the defaults for what is missing */
export function parseAiRules(rules: Ini): AiRules {
  const d = DEFAULT_AI_RULES
  const ai = rules.get('AI')
  const general = rules.get('GENERAL')
  const number = (value: string | undefined, fallback: number) => {
    const n = Number.parseFloat(value ?? '')
    return Number.isFinite(n) ? n / (value!.trim().endsWith('%') ? 100 : 1) : fallback
  }
  const list = (value: string | undefined, fallback: string[]) => {
    const ids = (value ?? '').split(',').map(s => s.trim().toUpperCase()).filter(Boolean)
    return ids.length ? ids : fallback
  }
  const share = (name: string, fallback: Share): Share => ({
    ratio: number(ai?.get(`${name}RATIO`), fallback.ratio),
    limit: number(ai?.get(`${name}LIMIT`), fallback.limit),
  })
  /** A value of [General] for each level: listed Hard, Normal, Easy there, Leicht first here */
  const perLevel = (key: string, level: number, fallback: number) =>
    number(general?.get(key)?.split(',')[2 - level], fallback)
  // the hard computer player gets [Easy]'s handicap, the easy one [Difficult]'s
  const sections = ['DIFFICULT', 'NORMAL', 'EASY']
  const levels = d.levels.map((fallback, level): LevelRules => {
    const section = rules.get(sections[level]!)
    return {
      armor: number(section?.get('ARMOR'), fallback.armor),
      rof: number(section?.get('ROF'), fallback.rof),
      buildTime: number(section?.get('BUILDTIME'), fallback.buildTime),
      // minutes
      buildDelay: number(section?.get('BUILDDELAY'), fallback.buildDelay / 60) * 60,
      repairDelay: number(section?.get('REPAIRDELAY'), fallback.repairDelay / 60) * 60,
      teamDelay: perLevel('TEAMDELAYS', level, fallback.teamDelay * FRAMES_PER_SECOND) / FRAMES_PER_SECOND,
      guards: perLevel('MINIMUMAIDEFENSIVETEAMS', level, fallback.guards),
    }
  }) as AiRules['levels']
  return {
    power: list(ai?.get('BUILDPOWER'), d.power),
    refinery: list(ai?.get('BUILDREFINERY'), d.refinery),
    barracks: list(ai?.get('BUILDBARRACKS'), d.barracks),
    factory: list(ai?.get('BUILDWEAPONS'), d.factory),
    radar: list(ai?.get('BUILDRADAR'), d.radar),
    tech: list(ai?.get('BUILDTECH'), d.tech),
    powerSurplus: number(ai?.get('POWERSURPLUS'), d.powerSurplus),
    creditReserve: number(ai?.get('CREDITRESERVE'), d.creditReserve),
    attackDelay: number(ai?.get('ATTACKDELAY'), d.attackDelay),
    baseSpacing: number(ai?.get('AIBASESPACING'), d.baseSpacing),
    refineries: share('REFINERY', d.refineries),
    barracksShare: share('BARRACKS', d.barracksShare),
    factories: share('WAR', d.factories),
    defenses: share('DEFENSE', d.defenses),
    antiAir: share('AA', d.antiAir),
    levels,
  }
}

/**
 * How a computer player plays at a level, beyond the rules: how quickly it reacts, how
 * big its base and army grow, how it attacks. Our own choice; the original's skirmish
 * computer gets this from AI.INI's teams and triggers.
 */
export interface AiProfile {
  /** Seconds between two looks at the battlefield */
  think: number
  /** Most refineries, harvesters per refinery (beyond the one each brings: only with money to spare), base defences */
  refineries: number
  harvesters: number
  defenses: number
  /** Most buildings of the base (walls not counted) */
  buildings: number
  /** Most fighting units at once */
  army: number
  /** The first attack comes after AttackDelay= times this */
  firstAttack: number
  /** Units of the first attack team, and how many more each later one has */
  team: number
  teamGrowth: number
  /** The team gathers halfway and goes in together */
  regroup: boolean
  /** The team falls back once this share of it is left (0: it fights to the last) */
  retreat: number
  /** Buildings below this health are repaired (0: never) */
  repairBelow: number
  /** A lost construction yard is replaced by a new MCV */
  rebuildYard: boolean
  /** How much it prefers strong (costly) units: 0 any, 1 the strongest it can build */
  strength: number
  /** Share of soldiers among its units once it has a war factory */
  infantry: number
  /** It goes for the enemy's refineries and factories first */
  economyFirst: boolean
}

export const PROFILES: Record<AiLevel, AiProfile> = {
  0: {
    think: 2.5, refineries: 1, harvesters: 1, defenses: 1, buildings: 10, army: 12, firstAttack: 1.6, team: 4, teamGrowth: 1,
    regroup: false, retreat: 0, repairBelow: 0.35, rebuildYard: false, strength: 0, infantry: 0.5, economyFirst: false,
  },
  1: {
    think: 1.25, refineries: 2, harvesters: 1, defenses: 4, buildings: 18, army: 22, firstAttack: 1, team: 5, teamGrowth: 2,
    regroup: true, retreat: 0.25, repairBelow: 0.6, rebuildYard: true, strength: 0.35, infantry: 0.35, economyFirst: false,
  },
  2: {
    think: 0.6, refineries: 3, harvesters: 2, defenses: 8, buildings: 26, army: 32, firstAttack: 0.6, team: 6, teamGrowth: 3,
    regroup: true, retreat: 0.3, repairBelow: 0.8, rebuildYard: true, strength: 0.7, infantry: 0.25, economyFirst: true,
  },
}
