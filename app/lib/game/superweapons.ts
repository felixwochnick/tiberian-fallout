import type { Ini } from '../formats/ini'

/**
 * The special weapons of Tiberian Sun and Firestorm ([SuperWeaponTypes] of RULES.INI):
 * a building (SuperWeapon=, SuperWeapon2=) gives its owner the weapon; it charges for
 * RechargeTime= minutes (only with enough power if IsPowered=), then EVA says it is
 * ready (RechargeVoice=) and it can be fired once – most at a point of the map the
 * player picks (Action=), the firestorm is switched on instead and drains its charge.
 */

export type SuperWeaponKind = 'IonCannon' | 'EMPulse' | 'Firestorm' | 'HunterSeeker' | 'DropPod' | 'ChemMissile'

export interface SuperWeaponType {
  /** Section in RULES.INI, e.g. IONCANNONSPECIAL */
  id: string
  /** German name, for the sidebar */
  name: string
  kind: SuperWeaponKind
  /** Game seconds to charge (RechargeTime= is in minutes of 15 frames a second) */
  seconds: number
  /** Charges only while the base has enough power (IsPowered=) */
  powered: boolean
  /** Its cameo in the sidebar (SidebarImage=, a SHP without extension) */
  cameo: string
  /** EVA when it is ready (RechargeVoice=) */
  readyVoice: string[]
  /** The buildings that give it */
  buildings: string[]
  /** A building that is needed as well (AuxBuilding=: the waste facility for the chemical missile) */
  aux?: string
  /** The player picks where it goes (Action=): all but the firestorm and the hunter seeker */
  targeted: boolean
}

const NAMES: Record<SuperWeaponKind, string> = {
  IonCannon: 'Ionenkanone',
  EMPulse: 'EM-Puls',
  Firestorm: 'Feuersturm-Abwehr',
  HunterSeeker: 'Hunter-Seeker',
  DropPod: 'Landekapseln',
  ChemMissile: 'Chemische Rakete',
}

const list = (value?: string) => (value ?? '').split(',').map(s => s.trim().toUpperCase()).filter(Boolean)

/** The special weapons the rules know, with the buildings that give them */
export function superWeaponTypes(rules: Ini): SuperWeaponType[] {
  const types: SuperWeaponType[] = []
  for (const id of [...(rules.get('SUPERWEAPONTYPES')?.values() ?? [])].map(v => v.toUpperCase())) {
    const section = rules.get(id)
    const kind = section?.get('TYPE') as SuperWeaponKind | undefined
    if (!section || !kind || !(kind in NAMES)) continue
    const buildings = [...(rules.get('BUILDINGTYPES')?.values() ?? [])].map(v => v.toUpperCase()).filter((building) => {
      const b = rules.get(building)
      return b?.get('SUPERWEAPON')?.toUpperCase() === id || b?.get('SUPERWEAPON2')?.toUpperCase() === id
    })
    if (!buildings.length) continue
    types.push({
      id,
      name: NAMES[kind],
      kind,
      seconds: Number(section.get('RECHARGETIME') ?? 5) * 60,
      powered: /^(yes|true|1)$/i.test(section.get('ISPOWERED') ?? 'yes'),
      cameo: (section.get('SIDEBARIMAGE') ?? '').toUpperCase(),
      readyVoice: list(section.get('RECHARGEVOICE')),
      buildings,
      aux: section.get('AUXBUILDING')?.toUpperCase(),
      targeted: kind !== 'Firestorm' && kind !== 'HunterSeeker',
    })
  }
  return types
}

export interface SuperWeaponCharge {
  type: SuperWeaponType
  /** 0 … 1 */
  progress: number
  ready: boolean
  /** The firestorm is switched on (it uses up its charge meanwhile) */
  active: boolean
}

/** The special weapons of one player: they come with their buildings and charge */
export class SuperWeapons {
  readonly charges: SuperWeaponCharge[] = []

  constructor(private readonly types: SuperWeaponType[]) {}

  /** Takes on the weapons the buildings now give (`owned`: ids of the buildings, online ones) and drops the others */
  sync(owned: string[]) {
    for (const type of this.types) {
      const has = type.buildings.some(b => owned.includes(b)) && (!type.aux || owned.includes(type.aux))
      const i = this.charges.findIndex(c => c.type === type)
      if (has && i < 0) this.charges.push({ type, progress: 0, ready: false, active: false })
      if (!has && i >= 0) this.charges.splice(i, 1)
    }
  }

  /**
   * Charges them by `seconds` (game); `powered`: the base has enough power. Returns the
   * ones that have just become ready. A firestorm switched on drains its charge again
   * and goes off when it is empty.
   */
  tick(seconds: number, powered: boolean) {
    const ready: SuperWeaponCharge[] = []
    for (const charge of this.charges) {
      if (charge.active) {
        charge.progress = Math.max(0, charge.progress - (seconds * FIRESTORM_DRAIN) / charge.type.seconds)
        if (charge.progress <= 0) charge.active = false
        continue
      }
      if (charge.ready || (charge.type.powered && !powered)) continue
      charge.progress = Math.min(1, charge.progress + seconds / charge.type.seconds)
      if (charge.progress >= 1) {
        charge.ready = true
        ready.push(charge)
      }
    }
    return ready
  }

  /** Fires it (or switches the firestorm on/off): it starts charging again */
  use(charge: SuperWeaponCharge) {
    if (charge.type.kind === 'Firestorm') {
      // on while charged, off again whenever the player likes
      charge.active = !charge.active && charge.progress > 0
      charge.ready = false
      return
    }
    charge.ready = false
    charge.progress = 0
  }
}

/** The firestorm burns its charge this many times faster than it builds up */
const FIRESTORM_DRAIN = 4
