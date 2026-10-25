/**
 * Keyboard shortcuts of the game, changeable in the options ("Tastenbelegung").
 * Keys are stored as KeyboardEvent.code (the physical key), so they work with any
 * keyboard layout. Esc always opens the menu and cannot be changed.
 */

export type KeyAction = 'radar' | 'stop' | 'selectAll' | 'home'

export const KEY_ACTIONS: { action: KeyAction, label: string }[] = [
  { action: 'radar', label: 'Radar an/aus' },
  { action: 'stop', label: 'Einheiten anhalten' },
  { action: 'selectAll', label: 'Alle Einheiten auswählen' },
  { action: 'home', label: 'Zur Basis springen' },
]

export const DEFAULT_KEYS: Record<KeyAction, string> = {
  radar: 'KeyR',
  stop: 'KeyS',
  selectAll: 'KeyQ',
  home: 'KeyH',
}

/** Keys that cannot be used for shortcuts */
export const RESERVED_KEYS = ['Escape', 'Tab', 'MetaLeft', 'MetaRight', 'OSLeft', 'OSRight']

const NAMES: Record<string, string> = {
  Space: 'Leertaste', Enter: 'Enter', Backspace: 'Rücktaste', ShiftLeft: 'Umschalt links', ShiftRight: 'Umschalt rechts',
  ControlLeft: 'Strg links', ControlRight: 'Strg rechts', AltLeft: 'Alt', AltRight: 'Alt Gr',
  ArrowUp: '↑', ArrowDown: '↓', ArrowLeft: '←', ArrowRight: '→', Home: 'Pos 1', End: 'Ende',
  PageUp: 'Bild ↑', PageDown: 'Bild ↓', Insert: 'Einfg', Delete: 'Entf', CapsLock: 'Feststell',
}

/** "KeyR" → "R", "Digit1" → "1", "Numpad5" → "Num 5", "Space" → "Leertaste" */
export function keyName(code: string) {
  if (NAMES[code]) return NAMES[code]
  if (code.startsWith('Key')) return code.slice(3)
  if (code.startsWith('Digit')) return code.slice(5)
  if (code.startsWith('Numpad')) return `Num ${code.slice(6)}`
  return code
}

export function useKeys() {
  const settings = useSettings()
  /** Whether a key event is the shortcut of an action (without Ctrl, Alt or Cmd held) */
  function matches(event: KeyboardEvent, action: KeyAction) {
    if (event.ctrlKey || event.altKey || event.metaKey || event.repeat) return false
    return event.code === (settings.keys[action] ?? DEFAULT_KEYS[action])
  }
  return { matches, keys: settings.keys }
}
