/**
 * The game needs a mouse (or trackpad) and a screen of desktop size: tablets with a
 * mouse and phones in a desktop/docking mode on a monitor are fine, phones on their
 * own are not. A keyboard cannot be detected by the browser, so it is only asked for.
 * Updates live, e.g. when a mouse is plugged in or the phone is docked.
 */

/** Smallest window that still works: shorter and longer side in CSS pixels */
export const MIN_SCREEN = { short: 600, long: 900 }

const FINE_POINTER = '(any-pointer: fine) and (any-hover: hover)'

const state = reactive({ pointer: true, screen: true })
let watching = false

function update() {
  state.pointer = window.matchMedia(FINE_POINTER).matches
  const short = Math.min(window.innerWidth, window.innerHeight)
  const long = Math.max(window.innerWidth, window.innerHeight)
  state.screen = short >= MIN_SCREEN.short && long >= MIN_SCREEN.long
}

export function useDeviceSupport() {
  if (!watching) {
    watching = true
    update()
    window.matchMedia(FINE_POINTER).addEventListener('change', update)
    window.addEventListener('resize', update)
  }
  return {
    /** A mouse or trackpad is there */
    pointer: computed(() => state.pointer),
    /** The window is big enough */
    screen: computed(() => state.screen),
    supported: computed(() => state.pointer && state.screen),
  }
}
