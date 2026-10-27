import * as THREE from 'three'
import type { MissionMap } from '../menu/world-map'

/**
 * Campaigns and their missions. A mission sets up the map around the player's base
 * and decides each frame whether it is won or lost.
 */

/** What a mission can do on the battlefield */
export interface MissionContext {
  /** Middle of the player's base (world) */
  base: THREE.Vector3
  /** Puts an enemy soldier (Nod) on the map, `at` in cells from the base */
  spawnEnemy: (id: string, dx: number, dz: number) => Promise<THREE.Object3D>
  /** A unit that can dig in (the Tick Tank) does so where it stands, if the ground lets it */
  digIn: (object: THREE.Object3D) => void
  /** Sends enemies towards a point (cells from the base), fighting on the way */
  attackMove: (objects: THREE.Object3D[], dx: number, dz: number) => void
  /** EVA */
  speak: (message: 'evaBaseAttack') => void
  /** Units on the map: the player's and the enemy's, not counting the fallen */
  units: () => { own: THREE.Object3D[], enemy: THREE.Object3D[] }
  /** Whether the player can still get new soldiers (in production, a barracks and the money for one, or a construction yard) */
  canReinforce: () => boolean
  /** Whether the player has a structure (RULES.INI id) standing */
  owns: (id: string) => boolean
  /** A hint under the top bar, with the incoming message sound */
  hint: (text: string, seconds?: number) => void
  /** Starts the countdown in the top bar ("Timer started"); `onEnd` runs when it reaches 0 */
  startTimer: (seconds: number, onEnd?: () => void) => void
  /** Stops the countdown and takes it away ("Timer stopped") */
  stopTimer: () => void
  /** Plays one of the game's videos (e.g. 'GDI01_SB.VQA') in the radar; resolves when it has ended */
  playRadar: (name: string) => Promise<void>
}

export type MissionResult = 'won' | 'lost' | undefined

export interface Mission {
  id: string
  title: string
  /** Briefing, paragraph by paragraph */
  briefing: string[]
  /** Objectives shown in the briefing and the Esc menu */
  objectives: string[]
  /** Starting money */
  credits: number
  /** Highest tech level that can be built (default 10) */
  techLevel?: number
  /** The radar works without a radar building */
  radar?: boolean
  /** The briefing is shown on the map of the region (its own page, /briefing): who holds what, and the targets to click */
  map?: MissionMap
  /** The player's base at the start: structures (RULES.INI id) and their corner in cells from the middle of the map */
  base: [id: string, dx: number, dz: number][]
  /**
   * Dropships that bring units in after the briefing, one after the other: what each
   * carries and where it lands (cells from the middle of the base); battle control comes
   * once all are out
   */
  reinforcements?: { units: string[], at: [number, number] }[]
  /** The dropships fly in together, side by side, instead of one after the other */
  dropshipsTogether?: boolean
  /** Tiberium fields at the start: middle (cells from the middle of the base) and size (cells from the middle to the edge) */
  tiberium?: { at: [number, number], radius: number }[]
  /** Builds the mission's map; returns the per-frame check */
  start: (context: MissionContext) => (seconds: number) => MissionResult
}

export interface Campaign {
  id: string
  title: string
  description: string
  missions: Mission[]
}

/**
 * A wave of Nod soldiers (and vehicles, RULES.INI ids): appears at `at` (cells from
 * the base), waits `delay` seconds, then attacks the base
 */
interface Wave {
  delay: number
  at: [number, number]
  soldiers: number
  vehicles?: string[]
}

/** Nod soldiers (and vehicles) that stand about on the map (cells from the base) until they are found */
type Garrison = [dx: number, dz: number, soldiers: number, vehicles?: string[]]

interface NodForces {
  garrisons: Garrison[]
  waves: Wave[]
  /** Once the mission runs (after the briefing): hints, transmissions … */
  begin?: (context: MissionContext) => void
  /** Hints at a given second of the mission */
  hints?: [seconds: number, text: string][]
  /** What else has to be done to win (besides wiping out Nod) */
  done?: (context: MissionContext) => boolean
}

/** Every third soldier of a squad carries a rocket launcher (E3), the others rifles (E1) */
const ROCKET_EVERY = 3

/** Cells between the vehicles of a squad */
const VEHICLE_SPACING = 1.2

/** A few soldiers close together, in rows of three, and the vehicles in a row behind them */
function squad(context: MissionContext, [x, z]: [number, number], soldiers: number, vehicles: string[] = []) {
  const behind = z + Math.ceil(soldiers / 3) * 0.7 + 0.6
  return Promise.all([
    ...Array.from({ length: soldiers }, (_, i) =>
      context.spawnEnemy(i % ROCKET_EVERY === ROCKET_EVERY - 1 ? 'E3' : 'E1', x + (i % 3) * 0.7, z + Math.floor(i / 3) * 0.7)),
    ...vehicles.map((id, i) => context.spawnEnemy(id, x + i * VEHICLE_SPACING, behind)),
  ])
}

/**
 * Nod in a demo mission: soldiers standing about on the map and small groups that
 * attack the base now and then. Won when all of them are gone (and `done`), lost when
 * the player has no units left and cannot get new ones.
 */
function fightNod(context: MissionContext, { garrisons, waves, begin, hints = [], done }: NodForces) {
  let time = 0
  let next = 0
  let arrived = 0
  // the garrisons' Tick Tanks dig in where they stand
  for (const [x, z, soldiers, vehicles] of garrisons) void squad(context, [x, z], soldiers, vehicles).then(units => units.forEach(context.digIn))
  // the waves appear in the distance a little before they set off
  const pending = waves.map(wave => squad(context, wave.at, wave.soldiers, wave.vehicles).finally(() => arrived++))

  return (seconds: number): MissionResult => {
    if (time === 0) {
      begin?.(context)
      if (waves[0]) context.startTimer(waves[0].delay)
    }
    const before = time
    time += seconds
    for (const [at, text] of hints) {
      if (before < at && time >= at) context.hint(text)
    }
    while (next < waves.length && time >= waves[next]!.delay) {
      const index = next++
      pending[index]!.then((soldiers) => {
        context.attackMove(soldiers, 1, 1)
      })
      const coming = waves[next]
      if (coming) {
        context.hint(`Nod greift an (${index + 1} von ${waves.length})! Weitere Truppen sind im Anmarsch.`)
        context.startTimer(coming.delay - time)
      }
      else {
        context.hint('Die letzten Angreifer rücken an. Suchen und vernichten Sie danach die übrigen Nod-Truppen!')
        context.stopTimer()
      }
    }
    const { own, enemy } = context.units()
    if (next >= waves.length && arrived === waves.length && !enemy.length && (done?.(context) ?? true)) return 'won'
    if (!own.length && !context.canReinforce()) return 'lost'
    return undefined
  }
}

/** Sandbags (GASAND) all round a rectangle of cells, leaving out `gaps` */
function sandbagRing(x0: number, z0: number, x1: number, z1: number, gaps: [number, number][]): Mission['base'] {
  const cells: [number, number][] = []
  for (let x = x0; x <= x1; x++) cells.push([x, z0], [x, z1])
  for (let z = z0 + 1; z < z1; z++) cells.push([x0, z], [x1, z])
  return cells
    .filter(([x, z]) => !gaps.some(([gx, gz]) => gx === x && gz === z))
    .map(([x, z]) => ['GASAND', x, z])
}

/**
 * The map selection of the demo: the south-west of the USA. GDI holds the country, Nod
 * has taken the south-west and Mexico; Nevada and Utah are the targets.
 */
const DEMO_MAP: MissionMap = {
  center: [-113, 36],
  span: 36,
  regions: { 'USA': 'gdi', 'CAN': 'gdi', 'MEX': 'nod', 'US-AZ': 'nod', 'US-NM': 'nod', 'US-UT': 'nod' },
  targets: [{ region: 'US-NV', mission: 'demo-1' }, { region: 'US-UT', mission: 'demo-2' }],
}

const outpostMission: Mission = {
  id: 'demo-1',
  title: 'Demo 1: Der Außenposten',
  briefing: [
    'Kommandant, unser Außenposten in Nevada besteht nur noch aus einem Kraftwerk und einer Kaserne hinter Sandsäcken. Einen Bauhof gibt es nicht.',
    'Zwei Dropships bringen Ihnen je einen Wolverine und vier Infanteristen. Nod-Soldaten streifen durch das Gebiet und werden den Posten in kleinen Gruppen angreifen.',
    'Bilden Sie in der Kaserne Verstärkung aus und vernichten Sie alle Nod-Truppen. Für die GDI!',
  ],
  objectives: [
    'Alle Nod-Truppen im Gebiet vernichten',
    'Mindestens eine Einheit muss überleben',
  ],
  credits: 1000,
  techLevel: 1,
  // a power plant and a barracks behind sandbags, open in front of the barracks door
  base: [
    ['GAPOWR', -3, 0],
    ['GAPILE', 0, 0],
    ...sandbagRing(-5, -2, 3, 3, [[0, 3], [1, 3]]),
  ],
  // side by side on the screen, so they come in from the map edge together
  reinforcements: [
    { units: ['SMECH', 'E1', 'E1', 'E1', 'E1'], at: [7.5, 6.5] },
    { units: ['SMECH', 'E1', 'E1', 'E1', 'E1'], at: [3.5, 10.5] },
  ],
  dropshipsTogether: true,
  map: DEMO_MAP,
  start: context => fightNod(context, {
    garrisons: [[13, -10, 3], [-15, -9, 2], [-11, 14, 3], [16, 10, 2], [24, -2, 3]],
    waves: [
      { delay: 45, at: [17, 13], soldiers: 2 },
      { delay: 100, at: [-15, 15], soldiers: 3 },
      { delay: 155, at: [18, -12], soldiers: 2 },
      { delay: 210, at: [-16, -13], soldiers: 3 },
    ],
    begin(context) {
      context.hint('Wenn Sie Truppen ausbilden wollen, klicken Sie auf die entsprechenden Symbole im Seitenmenü.')
      // an incoming transmission in the radar, like in the original's first mission
      context.playRadar('GDI01_SB.VQA')
    },
    hints: [[8, 'Wählen Sie Einheiten mit einem Klick oder per Rahmen aus und schicken Sie sie mit einem Klick auf den Boden los.']],
  }),
}

const bridgeheadMission: Mission = {
  id: 'demo-2',
  title: 'Demo 2: Der Brückenkopf',
  briefing: [
    'Kommandant, wir errichten einen Brückenkopf in Utah, mitten im Gebiet der Bruderschaft.',
    'Ein Dropship bringt Ihnen ein MCV, ein zweites zwei Wolverines und zwei Titans. Errichten Sie mit dem MCV einen Bauhof und bauen Sie die Basis aus.',
    'Nod wird nicht lange auf sich warten lassen. Unsere Aufklärung meldet neben Infanterie auch Buggys, Angriffsmotorräder, Tick Tanks und einen Untergrund-Truppentransporter. Vernichten Sie alle Nod-Truppen im Gebiet.',
  ],
  objectives: [
    'Mit dem MCV einen Bauhof errichten',
    'Alle Nod-Truppen im Gebiet vernichten',
  ],
  credits: 5000,
  base: [],
  // side by side on the screen, so they come in from the map edge together
  reinforcements: [
    { units: ['MCV'], at: [0.5, 0.5] },
    { units: ['SMECH', 'SMECH', 'MMCH', 'MMCH'], at: [-3.5, 4.5] },
  ],
  dropshipsTogether: true,
  // a field to the lower right of the base, for the refinery
  tiberium: [{ at: [10, -2], radius: 4 }],
  map: DEMO_MAP,
  start: context => fightNod(context, {
    garrisons: [[14, -11, 3, ['BGGY']], [-16, -8, 3, ['SAPC']], [-12, 15, 2, ['BIKE']], [22, 3, 3, ['TTNK']]],
    waves: [
      { delay: 90, at: [18, 14], soldiers: 3, vehicles: ['BIKE', 'BIKE'] },
      { delay: 170, at: [-17, 15], soldiers: 4, vehicles: ['BGGY', 'TTNK'] },
      { delay: 250, at: [19, -13], soldiers: 4, vehicles: ['TTNK', 'BGGY', 'BIKE'] },
    ],
    begin(context) {
      context.hint('Wählen Sie das MCV aus und klicken Sie es noch einmal an, um den Bauhof zu errichten.')
    },
    done: context => context.owns('GACNST'),
  }),
}

export const CAMPAIGNS: Campaign[] = [
  {
    id: 'demo',
    title: 'Demo',
    description: 'Zwei kurze Missionen zum Ausprobieren: Halten Sie einen Außenposten oder errichten Sie einen Brückenkopf im Gebiet von Nod.',
    missions: [outpostMission, bridgeheadMission],
  },
]

export function findMission(id: string) {
  for (const campaign of CAMPAIGNS) {
    const mission = campaign.missions.find(m => m.id === id)
    if (mission) return { campaign, mission }
  }
  return undefined
}
