export type Ini = Map<string, Map<string, string>>

/** Parses Westwood-style INI files (case-insensitive sections, `;` comments). */
export function parseIni(text: string): Ini {
  const ini: Ini = new Map()
  let section: Map<string, string> | undefined
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.replace(/;.*$/, '').trim()
    if (!line) continue
    const header = /^\[(.+)]$/.exec(line)
    if (header) {
      const name = header[1]!.trim().toUpperCase()
      section = ini.get(name) ?? new Map()
      ini.set(name, section)
      continue
    }
    const eq = line.indexOf('=')
    if (eq > 0 && section) section.set(line.slice(0, eq).trim().toUpperCase(), line.slice(eq + 1).trim())
  }
  return ini
}
