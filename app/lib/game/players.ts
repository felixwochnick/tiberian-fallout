/**
 * The players of a match. Everything on the map belongs to one of them (userData.owner):
 * its id is a short string that stays the same for the whole match, so orders and the
 * state of the map can name it the same way on every machine – the computer players
 * here, and later the players of a network match (Colyseus), who would each have their
 * own id instead of LOCAL_PLAYER.
 */

/** Who owns a unit or building: a player's id */
export type Owner = string

/** The human player at this screen ('player', also what an object without owner belongs to) */
export const LOCAL_PLAYER: Owner = 'player'
/** The enemy of the campaign missions */
export const MISSION_ENEMY: Owner = 'enemy'
/** Objects nobody fights over (civilian buildings …): never attacked */
export const NEUTRAL: Owner = 'neutral'

/** The owner of an object on the map (one without belongs to the human player) */
export function ownerOf(object: { userData: Record<string, unknown> }): Owner {
  return (object.userData.owner as Owner | undefined) ?? LOCAL_PLAYER
}

/**
 * Whether two players fight on the same side. Every player for themselves for now; teams
 * (2 against 2 …) would be decided here.
 */
export function allied(a: Owner, b: Owner) {
  return a === b
}

/**
 * The handicap a player plays with, like the original's [Easy], [Normal] and [Difficult]
 * of RULES.INI: factors on the damage their units and buildings withstand (Armor=, the
 * damage they take is divided by it), on the pause between their shots (ROF=) and on how
 * long their production takes (BuildTime=)
 */
export interface Handicap {
  armor: number
  rof: number
  buildTime: number
}

export const NO_HANDICAP: Handicap = { armor: 1, rof: 1, buildTime: 1 }
