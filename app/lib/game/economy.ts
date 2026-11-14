import type { BuildInfo, BuildRules } from './cameos'
import type { Side } from './models'
import { Production } from './production'

/**
 * What a player's base has to work with, the human player's (the sidebar shows it) and
 * each computer player's alike: money, the buildings on the map (and so power and
 * what can be built) and production.
 */
export interface Economy {
  credits: { value: number }
  /** What the player builds: their side's sidebar */
  side: Side
  rules?: BuildRules
  /** Buildings on the map (RULES.INI ids, one per building) */
  buildings: string[]
  /** Buildings switched off with the power button (one id per building): they use no power and do not work */
  offline: string[]
  production: Production
  /** Units that left their factory, to be put on the map by the battlefield */
  arrivals: BuildInfo[]
}

/** A fresh economy (a computer player's): the money to start with, nothing built yet */
export function createEconomy(credits: number, side: Side, rules?: BuildRules): Economy {
  const economy: Economy = {
    credits: { value: credits },
    side,
    rules,
    buildings: [],
    offline: [],
    production: new Production(info => economy.arrivals.push(info)),
    arrivals: [],
  }
  return economy
}

/** The buildings that work: those on the map, less those switched off */
export function onlineBuildings(economy: Economy) {
  const online = [...economy.buildings]
  for (const id of economy.offline) {
    const i = online.indexOf(id)
    if (i >= 0) online.splice(i, 1)
  }
  return online
}

/** Power output and drain of the buildings (switched off ones use none) */
export function basePower(economy: Economy) {
  let output = 0
  let drain = 0
  for (const id of onlineBuildings(economy)) {
    const power = economy.rules?.info.get(id)?.power ?? 0
    if (power > 0) output += power
    else drain -= power
  }
  return { output, drain }
}

/** Production slows down when the base uses more power than it has */
export function powerFactor(economy: Economy) {
  const { output, drain } = basePower(economy)
  return drain > output ? Math.max(0.3, output / drain) : 1
}

/** A building of the base is gone (destroyed, sold): it no longer counts for power and what can be built */
export function forgetBuilding(economy: Economy, id: string, poweredOff = false) {
  const i = economy.buildings.indexOf(id)
  if (i >= 0) economy.buildings.splice(i, 1)
  const off = poweredOff ? economy.offline.indexOf(id) : -1
  if (off >= 0) economy.offline.splice(off, 1)
}
