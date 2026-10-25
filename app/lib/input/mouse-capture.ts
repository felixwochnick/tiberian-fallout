import { reactive } from 'vue'
import { getAssetStore } from '../storage/asset-store'
import { CURSOR_FPS, fallbackCursors, loadCursors, type CursorImage, type CursorKind } from './cursor'

/**
 * Keeps the mouse inside the game like a real RTS: full screen plus pointer lock,
 * and in Chrome also keyboard lock, so Esc reaches the game (holding Esc leaves).
 *
 * While the pointer is locked the browser hides the system cursor and only reports
 * movement, so the game draws the cursor itself and forwards clicks, hover, wheel
 * and slider drags to the element under it. Hover is shown through a `data-hover`
 * attribute (and `data-active` while pressed) instead of :hover, which a locked
 * pointer cannot trigger; the attributes are kept up to date without the lock too.
 *
 * Esc in Firefox and Safari always leaves full screen and the lock; `needsResume`
 * then asks the page to offer "Weiter & Vollbild", which captures again.
 *
 * Moving between game pages keeps the capture; the start page calls `release`.
 */

interface KeyboardLock {
  lock?: (keys?: string[]) => Promise<void>
  unlock?: () => void
}
const keyboard = () => (navigator as Navigator & { keyboard?: KeyboardLock }).keyboard

export const mouseCapture = reactive({
  /** The player started the game, so full screen (and the lock, see `lockWanted`) should be on */
  wanted: false,
  /** Keep the mouse inside the game; off = full screen only */
  lockWanted: true,
  fullscreen: false,
  locked: false,
  /** A capture is under way (the browser has not answered yet) */
  capturing: false,
})

/** Full screen or lock was lost (Esc, Alt+Tab) and has to be resumed by a click. */
export const needsResume = () => mouseCapture.wanted && !mouseCapture.capturing
  && !(mouseCapture.fullscreen && (mouseCapture.locked || !mouseCapture.lockWanted))

let x = 0
let y = 0
/** The pointer is over the page (always when locked) */
let inside = false
/** Pages that use the game cursor (counted, as the next page may mount before the last one unmounts) */
let users = 0
let attached = false
let cursors: Partial<Record<CursorKind, CursorImage>> = {}
let cursorKind: CursorKind = 'default'
let cursor: CursorImage | undefined
let cursorElement: HTMLCanvasElement | undefined
let cursorStyle: HTMLStyleElement | undefined
let hovered: Element[] = []
let pressed: Element[] = []
let slider: HTMLInputElement | undefined

/**
 * Turns full screen and the locks on; must run inside a click or key handler.
 * With `lock: false` only full screen, the mouse stays free.
 */
export async function capture(at?: { clientX: number, clientY: number }, { lock = true } = {}) {
  if (at) {
    x = at.clientX
    y = at.clientY
  }
  mouseCapture.wanted = true
  mouseCapture.lockWanted = lock
  mouseCapture.capturing = true
  const root = document.documentElement
  // both requested right away: full screen uses up the click, waiting for it would get the lock refused
  const requests: unknown[] = []
  try {
    if (!document.fullscreenElement) requests.push(root.requestFullscreen?.({ navigationUI: 'hide' }))
    if (lock && document.pointerLockElement !== root) requests.push(root.requestPointerLock?.())
    if (!lock && document.pointerLockElement) document.exitPointerLock()
  }
  catch {}
  await Promise.allSettled(requests)
  // Esc only reaches the page in full screen
  await keyboard()?.lock?.(['Escape']).catch(() => {})
  mouseCapture.capturing = false
  sync()
}

/** Back to a normal window, e.g. when leaving the game. */
export function release() {
  mouseCapture.wanted = false
  keyboard()?.unlock?.()
  if (document.pointerLockElement) document.exitPointerLock()
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {})
}

/** Where the game cursor is, in CSS pixels of the viewport. */
export const pointer = () => ({ x, y, inside: inside || mouseCapture.locked })

/** Switches the game cursor, e.g. to a scroll arrow. */
export function setCursor(kind: CursorKind) {
  if (kind === cursorKind) return
  cursorKind = kind
  showCursor()
}

/** Goes on in the window without capturing again. */
export function stayWindowed() {
  mouseCapture.wanted = false
}

function sync() {
  mouseCapture.fullscreen = !!document.fullscreenElement
  mouseCapture.locked = !!document.pointerLockElement
  if (cursorElement) cursorElement.style.display = mouseCapture.locked && cursorKind !== 'hidden' ? 'block' : 'none'
  moveCursor()
}

/** Clicks and keys while captured can leave text selected; it shows once the lock is gone. */
const clearSelection = () => window.getSelection()?.removeAllRanges()

function onFullscreenChange() {
  clearSelection()
  // leaving full screen (Esc) gives up the lock as well
  if (!document.fullscreenElement) {
    keyboard()?.unlock?.()
    if (document.pointerLockElement) document.exitPointerLock()
  }
  sync()
}

function onPointerLockChange() {
  clearSelection()
  if (!document.pointerLockElement) setHovered(undefined)
  sync()
}

function moveCursor() {
  if (!cursorElement || !cursor) return
  cursorElement.style.transform = `translate(${x - cursor.hotX}px, ${y - cursor.hotY}px)`
}

const chain = (element: Element | null | undefined) => {
  const list: Element[] = []
  for (let e = element; e; e = e.parentElement) list.push(e)
  return list
}

const mouseInit = (event: MouseEvent, extra: MouseEventInit = {}): MouseEventInit => ({
  bubbles: true,
  cancelable: true,
  composed: true,
  clientX: x,
  clientY: y,
  screenX: event.screenX,
  screenY: event.screenY,
  button: event.button,
  buttons: event.buttons,
  ctrlKey: event.ctrlKey,
  shiftKey: event.shiftKey,
  altKey: event.altKey,
  metaKey: event.metaKey,
  ...extra,
})

/** Moves `data-hover` to the element under the cursor and its ancestors, with enter/leave events. */
function setHovered(target: Element | undefined, event?: MouseEvent) {
  const next = chain(target)
  const left = hovered.filter(e => !next.includes(e))
  const entered = next.filter(e => !hovered.includes(e))
  for (const e of left) e.removeAttribute('data-hover')
  for (const e of entered) e.setAttribute('data-hover', '')
  // synthetic enter/leave only where no real ones happen
  if (event && mouseCapture.locked) {
    if (left.length) hovered[0]?.dispatchEvent(new MouseEvent('mouseout', mouseInit(event, { relatedTarget: target ?? null })))
    for (const e of left) e.dispatchEvent(new MouseEvent('mouseleave', mouseInit(event, { bubbles: false })))
    if (entered.length) target?.dispatchEvent(new MouseEvent('mouseover', mouseInit(event, { relatedTarget: hovered[0] ?? null })))
    for (const e of entered.reverse()) e.dispatchEvent(new MouseEvent('mouseenter', mouseInit(event, { bubbles: false })))
  }
  hovered = next
}

function setPressed(target: Element | undefined) {
  for (const e of pressed) e.removeAttribute('data-active')
  pressed = chain(target)
  for (const e of pressed) e.setAttribute('data-active', '')
}

const under = () => document.elementFromPoint(x, y) ?? document.body

/** Native range inputs cannot be dragged by synthetic events, so set their value directly. */
function dragSlider(input: HTMLInputElement) {
  const box = input.getBoundingClientRect()
  const min = Number(input.min || 0)
  const max = Number(input.max || 100)
  const step = Number(input.step || 1)
  const ratio = Math.min(1, Math.max(0, (x - box.left) / box.width))
  const value = String(Math.round((min + ratio * (max - min)) / step) * step)
  if (input.value !== value) {
    input.value = value
    input.dispatchEvent(new Event('input', { bubbles: true }))
  }
}

function scrollableParent(element: Element | null) {
  for (let e = element; e; e = e.parentElement) {
    const style = getComputedStyle(e)
    if (/(auto|scroll)/.test(style.overflowY) && e.scrollHeight > e.clientHeight) return e
  }
  return undefined
}

/** Real mouse events: tracked when free, replaced by events at the virtual cursor when locked. */
function onMouse(event: Event) {
  if (!event.isTrusted) return
  const mouse = event as MouseEvent
  if (!mouseCapture.locked) {
    if (event.type === 'mousemove') {
      x = mouse.clientX
      y = mouse.clientY
      inside = true
      setHovered(event.target as Element)
    }
    if (event.type === 'mouseout' && !mouse.relatedTarget) inside = false // left the window
    if (event.type === 'mousedown') setPressed(event.target as Element)
    if (event.type === 'mouseup') setPressed(undefined)
    return
  }

  event.stopImmediatePropagation()
  if (event.type === 'contextmenu' || event.type === 'wheel') event.preventDefault()
  if (event.type.startsWith('pointer') || event.type === 'mouseout') return // the mouse events below stand for them

  if (event.type === 'mousemove') {
    x = Math.min(window.innerWidth - 1, Math.max(0, x + mouse.movementX))
    y = Math.min(window.innerHeight - 1, Math.max(0, y + mouse.movementY))
    moveCursor()
  }
  const target = under()
  if (event.type === 'mousemove') {
    setHovered(target, mouse)
    if (slider) dragSlider(slider)
  }
  if (event.type === 'mousedown') {
    setPressed(target)
    ;(target.closest('button, input, select, textarea, a, [tabindex]') as HTMLElement | null)?.focus?.()
    const input = target.closest('input[type=range]') as HTMLInputElement | null
    if (input && !input.disabled) {
      slider = input
      dragSlider(input)
    }
  }
  if (event.type === 'wheel') {
    const wheel = event as WheelEvent
    const synthetic = new WheelEvent('wheel', { ...mouseInit(mouse), deltaX: wheel.deltaX, deltaY: wheel.deltaY, deltaZ: wheel.deltaZ, deltaMode: wheel.deltaMode })
    // scroll lists like the browser would, unless the page handles the wheel itself (zoom)
    if (target.dispatchEvent(synthetic)) scrollableParent(target)?.scrollBy({ left: wheel.deltaX, top: wheel.deltaY })
    return
  }

  const init = mouseInit(mouse, { movementX: mouse.movementX, movementY: mouse.movementY })
  // only the primary button clicks; Firefox also reports "click" for the others
  const type = event.type === 'click' && mouse.button !== 0 ? 'auxclick' : event.type
  target.dispatchEvent(new MouseEvent(type, init))

  if (event.type === 'mouseup') {
    setPressed(undefined)
    if (slider) {
      slider.dispatchEvent(new Event('change', { bubbles: true }))
      slider = undefined
    }
  }
}

const MOUSE_EVENTS = ['mousemove', 'mousedown', 'mouseup', 'mouseout', 'click', 'dblclick', 'auxclick', 'contextmenu', 'wheel', 'pointermove', 'pointerdown', 'pointerup'] as const

/** Draws the game cursor while the page is shown; call `detach` when leaving it. */
export function attach() {
  users++
  if (attached) return
  attached = true
  for (const type of MOUSE_EVENTS) window.addEventListener(type, onMouse, { capture: true, passive: false })
  document.addEventListener('fullscreenchange', onFullscreenChange)
  document.addEventListener('pointerlockchange', onPointerLockChange)
  if (!document.pointerLockElement && !inside) {
    x = window.innerWidth / 2
    y = window.innerHeight / 2
  }

  cursorElement = document.createElement('canvas')
  Object.assign(cursorElement.style, { position: 'fixed', left: '0', top: '0', zIndex: '2147483647', pointerEvents: 'none', display: 'none' })
  document.body.appendChild(cursorElement)
  cursorStyle = document.createElement('style')
  document.head.appendChild(cursorStyle)
  // a game, not a document: nothing to select
  document.documentElement.style.userSelect = 'none'
  cursorKind = 'default'
  if (!cursors.default) cursors = fallbackCursors()
  showCursor()
  getAssetStore()
    .then(store => loadCursors(store))
    .then((loaded) => {
      if (!loaded) return
      cursors = { ...fallbackCursors(), ...loaded }
      if (attached) showCursor()
    })
    .catch(error => console.error('Mauszeiger konnte nicht geladen werden', error))
  sync()
}

let animation: ReturnType<typeof setInterval> | undefined

/** Shows the current cursor; animated ones step through their frames. */
function showCursor() {
  clearInterval(animation)
  animation = undefined
  // no cursor at all (e.g. before battle control is established)
  if (cursorKind === 'hidden') {
    if (cursorElement) cursorElement.style.display = 'none'
    if (cursorStyle) cursorStyle.textContent = 'html, html * { cursor: none !important; }'
    return
  }
  if (cursorElement) cursorElement.style.display = mouseCapture.locked ? 'block' : 'none'
  const image = cursors[cursorKind] ?? cursors.default
  if (image?.frames && image.frames.length > 1) {
    let frame = 0
    const frames = image.frames
    animation = setInterval(() => {
      frame = (frame + 1) % frames.length
      drawCursor(frames[frame]!)
    }, 1000 / CURSOR_FPS)
  }
  if (image) drawCursor(image)
}

function drawCursor(image: CursorImage) {
  cursor = image
  if (!image || !cursorElement || !cursorStyle) return
  cursorElement.width = image.canvas.width
  cursorElement.height = image.canvas.height
  cursorElement.getContext('2d')!.drawImage(image.canvas, 0, 0)
  // the same image as the system cursor while the pointer is free
  cursorStyle.textContent = `html, html * { cursor: url(${image.url}) ${image.hotX} ${image.hotY}, default !important; }`
  moveCursor()
}

export function detach() {
  users = Math.max(0, users - 1)
  if (!attached || users) return
  attached = false
  for (const type of MOUSE_EVENTS) window.removeEventListener(type, onMouse, { capture: true })
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  document.removeEventListener('pointerlockchange', onPointerLockChange)
  setHovered(undefined)
  setPressed(undefined)
  clearInterval(animation)
  animation = undefined
  cursorElement?.remove()
  cursorStyle?.remove()
  document.documentElement.style.userSelect = ''
  cursorElement = undefined
  cursorStyle = undefined
}
