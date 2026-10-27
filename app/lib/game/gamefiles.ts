import { type Ini, parseIni } from '../formats/ini'
import { MixArchive } from '../formats/mix'
import type { AssetStore } from '../storage/asset-store'

/**
 * The game's own files with Firestorm on top, like the original with its expansion:
 * FIRESTRM.INI changes RULES.INI, ARTFS.INI changes ART.INI (both in EXPAND01.MIX).
 * Without the Firestorm disc the plain Tiberian Sun files are used.
 */

/** The expansion's file for each of the game's INI files */
const EXPANSION: Record<string, string> = { 'RULES.INI': 'FIRESTRM.INI', 'ART.INI': 'ARTFS.INI' }

const decode = (bytes: Uint8Array) => new TextDecoder('latin1').decode(bytes)

/**
 * Puts an expansion's INI over the base one: its values replace those of the same key;
 * numbered lists (BuildingTypes, VehicleTypes …: every key a number) are appended to,
 * because the expansion numbers its entries from 1 again.
 */
export function mergeIni(base: Ini, patch: Ini) {
  for (const [name, section] of patch) {
    const target = base.get(name)
    if (!target) {
      base.set(name, new Map(section))
      continue
    }
    const list = [...section.keys()].every(key => /^\d+$/.test(key)) && [...target.keys()].every(key => /^\d+$/.test(key))
    if (!list) {
      for (const [key, value] of section) target.set(key, value)
      continue
    }
    const values = new Set([...target.values()].map(v => v.toUpperCase()))
    let next = Math.max(0, ...[...target.keys()].map(Number)) + 1
    for (const value of section.values()) {
      if (values.has(value.toUpperCase())) continue
      values.add(value.toUpperCase())
      target.set(String(next++), value)
    }
  }
  return base
}

/** Firestorm's archive (EXPAND01.MIX), if it was imported */
export async function expansionArchive(store: AssetStore) {
  const blob = await store.get('EXPAND01.MIX')
  return blob ? MixArchive.open(blob, 'EXPAND01.MIX') : undefined
}

/** RULES.INI or ART.INI from LOCAL.MIX, with Firestorm's changes if there are any */
export async function gameIni(store: AssetStore, name: 'RULES.INI' | 'ART.INI'): Promise<Ini | undefined> {
  const tibsun = await store.get('TIBSUN.MIX')
  if (!tibsun) return undefined
  const local = await (await MixArchive.open(tibsun, 'TIBSUN.MIX')).openNested('LOCAL.MIX')
  const bytes = await local?.read(name)
  if (!bytes) return undefined
  const ini = parseIni(decode(bytes))
  const patch = await (await expansionArchive(store))?.read(EXPANSION[name]!)
  return patch ? mergeIni(ini, parseIni(decode(patch))) : ini
}
