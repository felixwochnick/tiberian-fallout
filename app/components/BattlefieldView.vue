<script setup lang="ts">
import * as THREE from 'three'
import { Battlefield } from '~/lib/game/battlefield'
import { Combat } from '~/lib/game/combat'
import { MODELS, UNIT_FALLBACK } from '~/lib/game/models'
import type { BuildInfo, UnitVoice } from '~/lib/game/cameos'
import type { Unit } from '~/lib/game/unit'
import type { Field } from '~/lib/game/field'
import type { DropshipSound } from '~/lib/game/dropship'
import type { CursorKind } from '~/lib/input/cursor'
import { needsResume, pointer, setCursor } from '~/lib/input/mouse-capture'

/**
 * The battlefield: plain ground, scrolled by pushing the cursor against the screen edges.
 * It knows nothing about the game mode: what stands on the map at the start and what
 * happens on it is up to the skirmish or the mission, which get the `Field` on `start`.
 */

const props = withDefaults(defineProps<{
  paused?: boolean
  /** No cursor: battle control is not established yet */
  cursorHidden?: boolean
  /** House colour of the human player */
  colour?: number
}>(), { colour: 0xd8b43a }) // GDI gold
const skirmish = useSkirmish()
/**
 * `ready` hands the battlefield to the HUD (radar), `start` the field to the game mode;
 * `tick` gives the game seconds of each frame the game runs.
 */
const emit = defineEmits<{ ready: [battlefield: Battlefield], start: [field: Field], tick: [seconds: number] }>()
const settings = useSettings()
/** Edge scroll speed for each step of the setting (Sehr langsam … Maximal) */
const SCROLL_FACTORS = [0.35, 0.5, 0.7, 1, 1.3, 1.7, 2.2]

const stage = ref<HTMLDivElement>()
let battlefield: Battlefield | undefined
let running = false
let last = 0

function frame(now: number) {
  if (!running || !battlefield) return
  const seconds = Math.min(0.1, (now - last) / 1000) // no jump after a stall
  last = now
  const active = !props.paused && !needsResume()
  if (active) combat?.update(seconds, SPEED_FACTORS[settings.speed] ?? 1)
  if (active && skirmish) tickMissionDisplay(skirmish, seconds * (SPEED_FACTORS[settings.speed] ?? 1))
  if (active) emit('tick', seconds * (SPEED_FACTORS[settings.speed] ?? 1))
  if (active && skirmish) {
    skirmish.production.tick(seconds, (SPEED_FACTORS[settings.speed] ?? 1) * powerFactor(skirmish), skirmish.credits)
    // out of money: EVA says so, at most every few seconds
    if (skirmish.production.starved) {
      skirmish.production.starved = false
      if (now - lastFundsWarning > 8000) {
        lastFundsWarning = now
        sounds.speak('evaInsufficientFunds')
      }
    }
    for (const info of skirmish.arrivals.splice(0)) deliver(info)
  }
  syncPlacement()
  updatePowerLabel()
  if (skirmish?.placing) battlefield.updatePlacement(pointer().x, pointer().y)
  let cursor: CursorKind = 'default'
  if (active) {
    const at = pointer()
    cursor = battlefield.edgeScroll(at, seconds * (SCROLL_FACTORS[settings.scrollSpeed] ?? 1))
    // on the battlefield (not over the HUD): over a building or unit the select cursor;
    // with a factory selected, over the ground the rally point cursor
    if (cursor === 'default' && at.inside && !skirmish?.placing && document.elementFromPoint(at.x, at.y)?.closest('.battlefield')) {
      // the cursor shows what the order button would do on the ground
      const hovered = battlefield.objectAt(at.x, at.y)
      // over the selected MCV: unfold it here (or not, if there is no room)
      if (hovered && isDeployable(hovered)) cursor = battlefield.deployCell(hovered.userData.unit as Unit) ? 'deploy' : 'deploy-blocked'
      else if (hovered) cursor = combat?.canAttack(battlefield.selection, hovered) ? 'attack' : 'select'
      else if (battlefield.groundAt(at.x, at.y)) cursor = battlefield.canMove ? 'move' : battlefield.canSetRallyPoint ? 'rally' : 'default'
    }
  }
  // no cursor until battle control is established
  setCursor(props.cursorHidden ? 'hidden' : cursor)
  battlefield.render()
  requestAnimationFrame(frame)
}

/**
 * Selection box: pressing the left button on the battlefield and dragging draws a
 * rubber band; on release all units inside are selected (not buildings or harvesters).
 * A press without dragging stays a normal click.
 */
const DRAG = 5
let drag: { x0: number, y0: number, active: boolean } | undefined
let suppressClick = false

function onMouseDown(event: MouseEvent) {
  if (event.button !== 0 || props.paused || skirmish?.placing) return
  drag = { x0: event.clientX, y0: event.clientY, active: false }
}

function onMouseMove(event: MouseEvent) {
  if (!drag || !battlefield) return
  if (!drag.active && Math.hypot(event.clientX - drag.x0, event.clientY - drag.y0) < DRAG) return
  drag.active = true
  battlefield.setBand({ x0: drag.x0, y0: drag.y0, x1: event.clientX, y1: event.clientY })
}

function onMouseUp(event: MouseEvent) {
  if (!drag || !battlefield) return
  if (drag.active) {
    battlefield.setBand(undefined)
    if (battlefield.selectInBox(drag.x0, drag.y0, event.clientX, event.clientY)) respond('select')
    suppressClick = true // the click that follows the release
  }
  drag = undefined
}

/**
 * An order on the ground at a point of the screen: selected units walk there, a
 * selected factory gets its rally point there. Returns false if there was nothing to order.
 */
function order(clientX: number, clientY: number) {
  const ground = battlefield?.groundAt(clientX, clientY)
  if (!battlefield || !ground) return false
  if (battlefield.canMove) {
    combat?.stop(battlefield.selection)
    battlefield.orderMove(ground)
    respond('move')
  }
  else if (battlefield.canSetRallyPoint) battlefield.setRallyPoint(ground)
  else return false
  sounds.play('click')
  return true
}

/**
 * Left click. Always selects the building or unit under the cursor. On the ground:
 * classic controls give the order there, modern controls clear the selection.
 */
function onClick(event: MouseEvent) {
  // some browsers (Firefox) also send "click" for the right and middle button
  if (event.button !== 0) return
  if (suppressClick) {
    suppressClick = false
    return
  }
  if (props.paused || !battlefield) return
  // placing a structure: a left click puts it down (with both control schemes)
  if (skirmish?.placing) {
    place()
    return
  }
  const object = battlefield.objectAt(event.clientX, event.clientY)
  // classic controls: a left click on an enemy attacks it
  if (object && settings.controls === 'classic' && attack(object)) return
  // a second click on the selected MCV deploys it into a construction yard
  if (object && isDeployable(object)) {
    deployMcv(object)
    return
  }
  if (object) {
    battlefield.select(object)
    respond('select')
  }
  else if (settings.controls === 'modern' || !order(event.clientX, event.clientY)) battlefield.select(undefined)
}

/**
 * Right click anywhere (the browser menu never opens in the game). Classic controls:
 * clears the selection, whatever is selected. Modern controls: gives the order on the
 * ground (move, rally point).
 */
function onRightClick(event: MouseEvent) {
  event.preventDefault()
  if (props.paused || !battlefield) return
  // placing a structure: a right click stops placing (it stays ready in the sidebar)
  if (skirmish?.placing) {
    skirmish.placing = undefined
    return
  }
  if (settings.controls === 'modern') {
    const onMap = (event.target as Element | null)?.closest?.('.battlefield')
    const object = onMap && battlefield.objectAt(event.clientX, event.clientY)
    if (object) attack(object)
    else if (onMap) order(event.clientX, event.clientY)
  }
  else battlefield.select(undefined)
}

const sounds = useUiSounds()

/** Keyboard shortcuts of the battlefield (see "Tastenbelegung" in the options) */
const keys = useKeys()
function onKeyDown(event: KeyboardEvent) {
  if (props.paused || !battlefield) return
  if (keys.matches(event, 'stop')) {
    const own = battlefield.selection.filter(Battlefield.own)
    combat?.stop(own)
    for (const object of own) (object.userData.unit as { stop?: () => void } | undefined)?.stop?.()
  }
  else if (keys.matches(event, 'selectAll')) {
    if (battlefield.selectAllUnits()) respond('select')
  }
  else if (keys.matches(event, 'home')) {
    // the construction yard (or barracks), else the MCV that is still to deploy
    const yard = battlefield.structuresOf('GACNST').find(Battlefield.own) ?? battlefield.structuresOf('GAPILE').find(Battlefield.own)
      ?? battlefield.units.map(u => u.object).find(o => o.userData.id === 'MCV' && Battlefield.own(o) && !o.userData.dead)
    if (yard) battlefield.lookAt(yard.position)
  }
}

function onWheel(event: WheelEvent) {
  event.preventDefault()
  if (!props.paused) battlefield?.zoomBy(-Math.sign(event.deltaY))
}

const onResize = () => battlefield?.resize()

/** Foundations until the game's rules are loaded */
const FOUNDATIONS: Record<string, [number, number]> = { GACNST: [3, 3], GAPOWR: [2, 2], PROC: [4, 3], GAPILE: [2, 2] }
/** Units without their own model yet use the light infantry's */
const UNIT_MODEL = UNIT_FALLBACK
const FACTORY: Record<string, string> = { E1: 'GAPILE', E2: 'GAPILE', ENGINEER: 'GAPILE' }

/** Puts a structure of the player's base on the map. */
async function buildStructure(id: string, x: number, z: number, built = true) {
  if (!battlefield) return
  const [w, h] = skirmish?.rules?.info.get(id)?.foundation ?? FOUNDATIONS[id] ?? [2, 2]
  skirmish?.buildings.push(id)
  try {
    const object = await battlefield.addStructure(id, x, z, w, h, MODELS[id], props.colour)
    // factories can send what they produce to a rally point
    if (FACTORY_IDS.has(id)) object.userData.abilities = ['rally']
    if (id === 'GAPOWR') await addTurbine(object, props.colour)
    if (built) buildSound()
    return object
  }
  catch (error) {
    console.error(`${id} konnte nicht gebaut werden`, error)
  }
}
const FACTORY_IDS = new Set(Object.values(FACTORY))
/** A structure set down on the map, also the MCV unfolding (SOUNDS.MIX; BuildSounds and TransformSounds in OpenRA's Tiberian Sun) */
const PLACE_SOUND = ['PLACE2']

/** A structure starts to build up where it was placed */
function buildSound() {
  sounds.effect(PLACE_SOUND)
}
/** The dropship's sounds (SOUNDS.MIX), as in OpenRA's Tiberian Sun: landing, taking off, and its wreck exploding */
const DROPSHIP_SOUNDS: Record<DropshipSound, string[]> = {
  land: ['DROPDWN1'],
  takeOff: ['DROPUP1'],
  impact: ['EXPNEW09', 'EXPNEW10', 'EXPNEW12'],
}

/**
 * A power plant comes with its first turbine, on its right place (TurbineSlot1), like in
 * the original; it rises together with the plant.
 */
async function addTurbine(plant: THREE.Object3D, colour: number) {
  await battlefield?.addUpgrade(plant, MODELS.GAPOWRUP!, colour)
    .catch(error => console.error('GAPOWRUP konnte nicht montiert werden', error))
}

/** Selected units attack an enemy; false if they cannot (not an enemy, no weapons). */
function attack(target: THREE.Object3D) {
  if (!battlefield || !combat?.canAttack(battlefield.selection, target)) return false
  combat.attack(battlefield.selection, target)
  respond('attack')
  return true
}

/** The first selected unit answers (select: "Reporting", move: "Moving out" …), like in the original */
function respond(voice: UnitVoice) {
  const id = battlefield?.selection.find(object => object.userData.unit && Battlefield.own(object))?.userData.id as string | undefined
  const files = id ? skirmish?.rules?.info.get(id)?.voices[voice] : undefined
  if (files?.length) sounds.respond(files)
}

let delivered = 0

/** The selected MCV of the player: a click on it unfolds it */
function isDeployable(object: THREE.Object3D) {
  return object === battlefield?.selected && object.userData.id === 'MCV' && Battlefield.own(object) && !!object.userData.unit
}

/** Unfolds the MCV into a construction yard where it stands, if the 3 × 3 cells are free. */
function deployMcv(object: THREE.Object3D) {
  const unit = object.userData.unit as Unit | undefined
  if (!battlefield || !unit) return
  if (!battlefield.deployCell(unit)) {
    sounds.play('evaCannotPlace')
    return
  }
  sounds.play('click')
  battlefield.deploy(unit, MODELS.GACNST!, props.colour)
    .then((yard) => {
      if (!yard) return
      skirmish?.buildings.push('GACNST')
      buildSound() // it unfolds now
    })
    .catch(error => console.error('Bauhof konnte nicht aufgebaut werden', error))
}

/**
 * Reinforcements by dropship, like at the start of the original's missions: it flies
 * in over the map, lands at `at`, the soldiers come out over its ramp, and it leaves.
 * Settles once the last soldier is out.
 */
async function dropship(ids: string[], at: THREE.Vector3) {
  if (!battlefield) return
  const colour = props.colour
  const from = at.clone().add(new THREE.Vector3(-10, 0, -10))
  const leave = at.clone().add(new THREE.Vector3(12, 0, -12))
  let unloaded!: () => void
  const out = new Promise<void>((resolve) => {
    unloaded = resolve
  })
  const ship = await battlefield.addDropship(MODELS.DSHP!, from, {
    to: at,
    leave,
    unload: exit => unloadSoldiers(exit).finally(unloaded),
  }, colour)
  ship.onSound = sound => sounds.effect(DROPSHIP_SOUNDS[sound])
  return out

  async function unloadSoldiers(exit: THREE.Vector3) {
    const away = exit.clone().sub(at).setY(0).normalize()
    const side = new THREE.Vector3(-away.z, 0, away.x)
    for (const [i, id] of ids.entries()) {
      if (!battlefield) return
      const unit = await battlefield.addUnit(UNIT_MODEL, exit, colour)
      unit.object.userData.id = id
      battlefield.walk(unit, exit.clone().addScaledVector(away, 1.2).addScaledVector(side, (i - (ids.length - 1) / 2) * 0.7))
      await new Promise(resolve => setTimeout(resolve, 600))
    }
  }
}

let lastFundsWarning = -Infinity
/** A finished unit comes out of its factory and walks to the rally point (or a bit out). */
async function deliver(info: BuildInfo) {
  if (!battlefield) return
  const factory = battlefield.structuresOf(FACTORY[info.id] ?? '').filter(Battlefield.own).at(-1)
  if (!factory) return
  const door = factory.position.clone().add(new THREE.Vector3(0.46, 0, 1.0))
  const unit = await battlefield.addUnit(UNIT_MODEL, door, props.colour)
  unit.object.userData.id = info.id
  const rally = factory.userData.rallyPoint as THREE.Vector3 | undefined
  // each one stands a bit apart from the last, round the rally point
  delivered++
  const angle = delivered * 2.4
  const radius = 0.35 + 0.18 * Math.sqrt(delivered % 12)
  const spread = new THREE.Vector3(Math.cos(angle) * radius, 0, Math.sin(angle) * radius)
  battlefield.walk(unit, (rally ?? door.clone().add(new THREE.Vector3(0.8, 0, 2.6))).clone().add(spread))
}

/** Shows or hides the placement preview when the sidebar starts or stops placing. */
let placingId: string | undefined
function syncPlacement() {
  if (!battlefield || placingId === skirmish?.placing?.id) return
  placingId = skirmish?.placing?.id
  const info = skirmish?.placing
  if (info) battlefield.startPlacement(info.foundation[0], info.foundation[1], info.adjacent)
  else battlefield.cancelPlacement()
}

/** Puts the finished structure down where the preview is, if it may go there. */
function place() {
  const info = skirmish?.placing
  const cell = battlefield?.placementCell
  if (!skirmish || !info) return
  if (!cell) {
    sounds.speak('evaCannotPlace')
    return
  }
  skirmish.placing = undefined
  skirmish.production.placed()
  syncPlacement()
  buildStructure(info.id, cell[0], cell[1])
  // the construction yard's crane lets a crate down into its hatch
  const yard = battlefield!.structuresOf('GACNST').filter(Battlefield.own).at(-1)
  if (yard) battlefield!.playClip(yard, 'Deliver')
}

let combat: Combat | undefined

/**
 * A selected power plant of the player shows in its middle how much power the whole
 * base produces and how much it uses.
 */
const powerLabel = ref<{ x: number, y: number, output: number, drain: number }>()
function updatePowerLabel() {
  const plant = battlefield?.selected
  const isPlant = !!plant && !plant.userData.unit && Battlefield.own(plant) && (skirmish?.rules?.info.get(plant.userData.id)?.power ?? 0) > 0
  if (!isPlant || !skirmish) {
    powerLabel.value = undefined
    return
  }
  const { x, y } = battlefield!.frameCentre(plant)
  const { output, drain } = basePower(skirmish)
  const now = powerLabel.value
  if (now?.x !== x || now.y !== y || now.output !== output || now.drain !== drain) powerLabel.value = { x, y, output, drain }
}

onMounted(() => {
  battlefield = markRaw(new Battlefield(stage.value!, 128, 128))
  // dev only: reachable from the browser console (and automated tests)
  if (import.meta.dev) Object.assign(window, { battlefield })
  // fighting with the values of RULES.INI; shots and death cries from SOUNDS.MIX
  combat = markRaw(new Combat(
    battlefield,
    object => skirmish?.rules?.info.get(object.userData.id),
    {
      fire: (_, info) => sounds.effect(info.weapon?.reports ?? []),
      die: (_, info) => sounds.effect(info.voices.die),
      // a lost building of the player no longer counts for power and what can be built
      destroyed(building) {
        if (!Battlefield.own(building) || !skirmish) return
        const i = skirmish.buildings.indexOf(building.userData.id)
        if (i >= 0) skirmish.buildings.splice(i, 1)
      },
    },
  ))
  emit('ready', battlefield)
  emit('start', markRaw({
    battlefield,
    combat: combat!,
    colour: props.colour,
    buildStructure,
    async addUnit(id, at, colour = props.colour, owner = 'player') {
      const unit = await battlefield!.addUnit(MODELS[id] ?? UNIT_MODEL, at, colour, owner)
      unit.object.userData.id = id
      return unit.object
    },
    async dropship(ids, at) {
      await dropship(ids, at)
    },
  }))
  window.addEventListener('resize', onResize)
  window.addEventListener('contextmenu', onRightClick)
  window.addEventListener('keydown', onKeyDown)
  // moving and releasing may happen over the HUD as well
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
  running = true
  last = performance.now()
  requestAnimationFrame(frame)
})

onBeforeUnmount(() => {
  running = false
  window.removeEventListener('resize', onResize)
  window.removeEventListener('contextmenu', onRightClick)
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
  setCursor('default')
  combat?.dispose()
  battlefield?.dispose()
})
</script>

<template>
  <div ref="stage" class="battlefield" @mousedown="onMouseDown" @click="onClick" @wheel="onWheel">
    <div v-if="powerLabel" class="power-label" :class="{ low: powerLabel.drain > powerLabel.output }" :style="{ left: `${powerLabel.x}px`, top: `${powerLabel.y}px` }">
      <span>Erzeugt: {{ powerLabel.output }}</span>
      <span>Verbraucht: {{ powerLabel.drain }}</span>
    </div>
  </div>
</template>

<style scoped>
.battlefield {
  position: fixed;
  inset: 0;
  /* below the HUD's top bar, left of its sidebar */
  top: var(--hud-top, 0);
  right: var(--hud-right, 0);
  overflow: hidden;
  background: #000;
}
/* a selected power plant: power produced and used by the base, in its middle */
.power-label {
  position: absolute;
  z-index: 1;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  white-space: nowrap;
  pointer-events: none;
  font: 400 clamp(12px, 1.25vh, 18px) / 1.25 Arial, Helvetica, sans-serif;
  letter-spacing: 0.14em;
  color: #e9e3b8;
  text-shadow:
    1px 0 0 #000, -1px 0 0 #000, 0 1px 0 #000, 0 -1px 0 #000,
    1px 1px 1px rgba(0, 0, 0, 0.9);
}
/* more used than produced */
.power-label.low span:last-child {
  color: #ff6a4a;
}
.battlefield :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
