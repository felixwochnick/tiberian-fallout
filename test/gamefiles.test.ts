import { describe, expect, it } from 'vitest'
import { parseIni } from '../app/lib/formats/ini'
import { mergeIni } from '../app/lib/game/gamefiles'

describe('Firestorm over Tiberian Sun', () => {
  it('replaces values and appends to numbered lists', () => {
    const rules = parseIni('[VehicleTypes]\n1=HARV\n2=MMCH\n[MMCH]\nCost=800\nSpeed=4\n')
    mergeIni(rules, parseIni('[VehicleTypes]\n1=REAPER\n2=MMCH\n[MMCH]\nCost=1000\n[REAPER]\nCost=1100\n'))
    expect([...rules.get('VEHICLETYPES')!.values()]).toEqual(['HARV', 'MMCH', 'REAPER'])
    expect(rules.get('MMCH')!.get('COST')).toBe('1000')
    expect(rules.get('MMCH')!.get('SPEED')).toBe('4')
    expect(rules.get('REAPER')!.get('COST')).toBe('1100')
  })
})
