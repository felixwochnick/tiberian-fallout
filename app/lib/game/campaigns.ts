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
  /** Sends enemies towards a point (cells from the base), fighting on the way */
  attackMove: (objects: THREE.Object3D[], dx: number, dz: number) => void
  /** EVA */
  speak: (message: 'evaBaseAttack') => void
  /** Units on the map: the player's and the enemy's, not counting the fallen */
  units: () => { own: THREE.Object3D[], enemy: THREE.Object3D[] }
  /** Whether the player can still get new soldiers (in production, or the money for one) */
  canReinforce: () => boolean
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
  /** Units a dropship brings in after the briefing; battle control comes once they are out */
  reinforcements?: string[]
  /** Builds the mission's map; returns the per-frame check */
  start: (context: MissionContext) => (seconds: number) => MissionResult
}

export interface Campaign {
  id: string
  title: string
  description: string
  missions: Mission[]
}

/** A wave of Nod soldiers: appears at `at`, waits `delay` seconds, then attacks the base */
interface Wave {
  delay: number
  at: [number, number]
  soldiers: number
}

const DEMO_WAVES: Wave[] = [
  { delay: 40, at: [16, 13], soldiers: 3 },
  { delay: 110, at: [-14, 15], soldiers: 4 },
  { delay: 180, at: [17, -12], soldiers: 5 },
]

const demoMission: Mission = {
  id: 'demo-1',
  title: 'Demo: Die Stellung halten',
  briefing: [
    'Kommandant, eine Nod-Einheit hat sich in diesem Sektor festgesetzt. Unsere vorgeschobene Basis ist das einzige, was zwischen ihnen und den Tiberiumfeldern steht.',
    'Die Aufklärung meldet mehrere Angriffswellen der Bruderschaft. Bilden Sie in der Kaserne Infanterie aus und schlagen Sie jeden Angriff zurück.',
    'Halten Sie die Stellung. Für die GDI!',
  ],
  objectives: [
    'Alle drei Angriffswellen von Nod abwehren',
    'Mindestens eine Einheit muss überleben',
  ],
  credits: 5000,
  // construction yard, power plant, refinery and barracks
  base: [['GACNST', -3, -3], ['GAPOWR', 0, -3], ['PROC', -5, 0], ['GAPILE', 0, 0]],
  reinforcements: ['E1', 'E1', 'E1'],
  // the south-west of the USA: GDI holds the country, Nod has taken the south-west and
  // Mexico; the target is Nevada
  map: {
    center: [-113, 36],
    span: 36,
    regions: { 'USA': 'gdi', 'CAN': 'gdi', 'MEX': 'nod', 'US-AZ': 'nod', 'US-NM': 'nod', 'US-UT': 'nod' },
    targets: [{ region: 'US-NV' }],
  },
  start(context) {
    let time = 0
    let next = 0
    const waves: THREE.Object3D[][] = []

    // the waves appear in the distance a little before they set off
    const spawnWave = async (wave: Wave) => {
      const soldiers = await Promise.all(Array.from({ length: wave.soldiers }, (_, i) =>
        context.spawnEnemy('E1', wave.at[0] + (i % 3) * 0.7, wave.at[1] + Math.floor(i / 3) * 0.7)))
      waves.push(soldiers)
      return soldiers
    }
    const pending: Promise<THREE.Object3D[]>[] = DEMO_WAVES.map(spawnWave)

    return (seconds) => {
      // once the mission runs (after the briefing): hints on how to play and the
      // countdown to the first attack
      if (time === 0) {
        context.hint('Wenn Sie ein Gebäude errichten oder Truppen ausbilden wollen, klicken Sie auf die entsprechenden Symbole im Seitenmenü.')
        context.startTimer(DEMO_WAVES[0]!.delay)
        // an incoming transmission in the radar, like in the original's first mission
        context.playRadar('GDI01_SB.VQA')
      }
      const before = time
      time += seconds
      if (before < 8 && time >= 8) context.hint('Wählen Sie Einheiten mit einem Klick oder per Rahmen aus und schicken Sie sie mit einem Klick auf den Boden los.')
      while (next < DEMO_WAVES.length && time >= DEMO_WAVES[next]!.delay) {
        const index = next++
        pending[index]!.then((soldiers) => {
          context.attackMove(soldiers, 1, 1)
          context.speak('evaBaseAttack')
        })
        const coming = DEMO_WAVES[next]
        if (coming) {
          context.hint(`Angriffswelle ${index + 1} von ${DEMO_WAVES.length}! Die nächste Welle folgt in Kürze.`)
          context.startTimer(coming.delay - time)
        }
        else {
          context.hint('Die letzte Angriffswelle rückt an. Halten Sie durch!')
          context.stopTimer()
        }
      }
      const { own, enemy } = context.units()
      if (next >= DEMO_WAVES.length && waves.length === DEMO_WAVES.length && !enemy.length) return 'won'
      if (!own.length && !context.canReinforce()) return 'lost'
      return undefined
    }
  },
}

export const CAMPAIGNS: Campaign[] = [
  {
    id: 'demo',
    title: 'Demo',
    description: 'Eine kurze Mission zum Ausprobieren: Verteidigen Sie Ihre Basis gegen drei Angriffswellen von Nod.',
    missions: [demoMission],
  },
]

export function findMission(id: string) {
  for (const campaign of CAMPAIGNS) {
    const mission = campaign.missions.find(m => m.id === id)
    if (mission) return { campaign, mission }
  }
  return undefined
}
