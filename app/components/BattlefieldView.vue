<script setup lang="ts">
import * as THREE from 'three'
import { Battlefield } from '~/lib/game/battlefield'
import { Combat } from '~/lib/game/combat'
import { Harvesting } from '~/lib/game/harvesting'
import { Repairs } from '~/lib/game/repairs'
import { applyHouseColour, MODELS, UNIT_FALLBACK, type Side } from '~/lib/game/models'
import { type BuildInfo, DEFAULT_SURVIVORS, DEFAULT_UPKEEP, type UnitVoice } from '~/lib/game/cameos'
import type { Unit } from '~/lib/game/unit'
import { type SuperWeaponCharge, SuperWeapons } from '~/lib/game/superweapons'
import type { Field } from '~/lib/game/field'
import type { Dropship, DropshipSound } from '~/lib/game/dropship'
import { cursorScale, type CursorKind } from '~/lib/input/cursor'
import { loadSigns } from '~/lib/game/signs'
import { getAssetStore } from '~/lib/storage/asset-store'
import type { BaseMode } from '~/composables/useSkirmish'
import { needsResume, pointer, setCursor } from '~/lib/input/mouse-capture'
import { agentCommands } from '~/lib/agent/commands'
import { linkAgent } from '~/lib/agent/link'

/**
 * The battlefield: plain ground, scrolled by pushing the cursor against the screen edges.
 * It knows nothing about the game mode: what stands on the map at the start and what
 * happens on it is up to the skirmish or the mission, which get the `Field` on `start`.
 */

const props = withDefaults(defineProps<{
  paused?: boolean
  /** The whole game is paused (Esc menu): units, aircraft and animations stand still too */
  frozen?: boolean
  /** No cursor: battle control is not established yet */
  cursorHidden?: boolean
  /** House colour of the human player */
  colour?: number
  /** The human player's side: GDI's units wear camouflage, Nod's dark armour */
  side?: Side
  /** Highest tech level that can be built (for the agent, the sidebar has its own) */
  techLevel?: number
}>(), { colour: 0xd8b43a, side: 'gdi', techLevel: 10 }) // GDI gold
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
/** Game seconds the battlefield has run */
let clock = 0

function frame(now: number) {
  if (!running || !battlefield) return
  const seconds = Math.min(0.1, (now - last) / 1000) // no jump after a stall
  last = now
  const active = !props.paused && !needsResume()
  // the game speed: everything in the game runs on game seconds (the edge scroll does not)
  const speed = SPEED_FACTORS[settings.speed] ?? 1
  const gameSeconds = seconds * speed
  if (active) combat?.update(seconds, speed)
  if (active) harvesting?.update(gameSeconds)
  if (active) repairs?.update(gameSeconds)
  if (active && skirmish) tickMissionDisplay(skirmish, gameSeconds)
  if (active) emit('tick', gameSeconds)
  if (active) clock += gameSeconds
  if (active && skirmish) {
    skirmish.production.tick(seconds, speed * powerFactor(skirmish), skirmish.credits)
    // out of money: EVA says so, at most every few seconds
    if (skirmish.production.starved) {
      skirmish.production.starved = false
      if (now - lastFundsWarning > 8000) {
        lastFundsWarning = now
        sounds.speak('evaInsufficientFunds')
      }
    }
    for (const info of skirmish.arrivals.splice(0)) deliver(info)
    tickSpecials(gameSeconds)
    tickDepots(gameSeconds)
    tickTakers()
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
      // a special weapon waits for its target
      if (skirmish?.targeting) cursor = 'attack'
      // a button of the sidebar is on: its cursor, crossed out where it cannot be used
      else if (skirmish?.mode) cursor = modeCursor(skirmish.mode, hovered, at.x, at.y)
      // Ctrl: fire at whatever is under the cursor; Alt: move there, whatever is there
      else if (modifiers.ctrl && hovered && combat?.canAttack(battlefield.selection, hovered, true)) cursor = 'attack'
      else if (modifiers.alt && battlefield.canMove && battlefield.groundAt(at.x, at.y)) cursor = 'move'
      // over the selected MCV: unfold it here (or not, if there is no room)
      else if (hovered && isDeployable(hovered)) cursor = canDeploy(hovered) ? 'deploy' : 'deploy-blocked'
      // a harvester over its refinery: drive in and unload
      else if (hovered) cursor = canUnloadAt(hovered) || canEnter(hovered) ? 'enter' : combat?.canAttack(battlefield.selection, hovered) ? 'attack' : 'select'
      // a harvester over Tiberium: harvest it (the attack cursor, like in the original)
      else if (harvestTarget(at.x, at.y)) cursor = 'attack'
      else if (battlefield.groundAt(at.x, at.y)) cursor = battlefield.canMove ? 'move' : battlefield.canSetRallyPoint ? 'rally' : 'default'
    }
  }
  // no cursor until battle control is established
  setCursor(props.cursorHidden ? 'hidden' : cursor)
  // the camera stays on the dropship that is on its way in, until it is down
  const arriving = escorted.find(ship => ship.arriving)
  if (arriving) battlefield.lookAt(arriving.object.position)
  escorted.splice(0, escorted.length, ...escorted.filter(ship => ship.arriving))
  battlefield.render(props.frozen, SPEED_FACTORS[settings.speed] ?? 1)
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
  trackModifiers(event)
  if (!drag || !battlefield) return
  if (!drag.active && Math.hypot(event.clientX - drag.x0, event.clientY - drag.y0) < DRAG) return
  drag.active = true
  battlefield.setBand({ x0: drag.x0, y0: drag.y0, x1: event.clientX, y1: event.clientY })
}

function onMouseUp(event: MouseEvent) {
  if (!drag || !battlefield) return
  if (drag.active) {
    battlefield.setBand(undefined)
    if (battlefield.selectInBox(drag.x0, drag.y0, event.clientX, event.clientY, event.shiftKey)) respond('select')
    suppressClick = true // the click that follows the release
  }
  drag = undefined
}

/**
 * An order on the ground at a point of the screen: selected units walk there (selected
 * harvesters harvest there, if it is Tiberium), a selected factory gets its rally point
 * there. Returns false if there was nothing to order.
 */
function order(clientX: number, clientY: number) {
  const ground = battlefield?.groundAt(clientX, clientY)
  if (!battlefield || !ground) return false
  if (battlefield.canMove) {
    const tiberium = harvestTarget(clientX, clientY)
    combat?.stop(battlefield.selection)
    harvesting?.order(battlefield.selection)
    battlefield.orderMove(ground)
    if (tiberium) harvesting?.harvest(battlefield.selection, tiberium)
    respond(tiberium ? 'attack' : 'move')
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
  // a special weapon waits for its target: there it goes
  if (skirmish?.targeting) {
    const ground = battlefield.groundAt(event.clientX, event.clientY)
    const charge = superWeapons?.charges.find(c => c.type.id === skirmish!.targeting)
    skirmish.targeting = undefined
    if (ground && charge?.ready) fireSpecial(charge, ground)
    return
  }
  // placing a structure: a left click puts it down (with both control schemes)
  if (skirmish?.placing) {
    place()
    return
  }
  // a button of the sidebar is on: the click repairs, sells, switches or sets a waypoint
  if (skirmish?.mode) {
    useMode(skirmish.mode, event.clientX, event.clientY)
    return
  }
  const object = battlefield.objectAt(event.clientX, event.clientY)
  // Shift: a unit is added to the selection (or taken out of it)
  if (object && event.shiftKey) {
    if (battlefield.toggleSelect(object)) respond('select')
    return
  }
  // classic controls: Ctrl and Alt give their orders with the left button (with modern ones the right button does)
  if (settings.controls === 'classic' && forcedOrder(event, object)) return
  // classic controls: a left click on an enemy attacks it, on an own refinery sends the harvesters in
  if (object && settings.controls === 'classic' && (unloadAt(object) || enter(object) || attack(object))) return
  // a second click on the selected MCV deploys it into a construction yard, on a Tick Tank digs it in (or out),
  // on a transport lets its soldiers out
  if (object && isDeployable(object)) {
    deployObject(object)
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
  // a right click puts a special weapon back (it stays ready)
  if (skirmish?.targeting) {
    skirmish.targeting = undefined
    return
  }
  // placing a structure: a right click stops placing (it stays ready in the sidebar)
  if (skirmish?.placing) {
    skirmish.placing = undefined
    return
  }
  // a button of the sidebar is on: a right click switches it off (with both control schemes)
  if (skirmish?.mode) {
    skirmish.mode = undefined
    return
  }
  if (settings.controls === 'modern') {
    const onMap = (event.target as Element | null)?.closest?.('.battlefield')
    const object = onMap && battlefield.objectAt(event.clientX, event.clientY)
    if (onMap && forcedOrder(event, object || undefined)) return
    if (object) {
      if (!unloadAt(object) && !enter(object)) attack(object)
    }
    else if (onMap) order(event.clientX, event.clientY)
  }
  else battlefield.select(undefined)
}

const sounds = useUiSounds()

/** Keyboard shortcuts of the battlefield (see "Tastenbelegung" in the options) */
const keys = useKeys()
function onKeyDown(event: KeyboardEvent) {
  trackModifiers(event)
  // Alt alone would open the browser's menu (Firefox)
  if (event.key === 'Alt') event.preventDefault()
  if (props.paused || !battlefield) return
  if (keys.matches(event, 'stop')) {
    const own = battlefield.selection.filter(Battlefield.own)
    combat?.stop(own)
    harvesting?.order(own)
    battlefield.clearWaypoints(own)
    for (const object of own) (object.userData.unit as { stop?: () => void } | undefined)?.stop?.()
  }
  else if (keys.matches(event, 'selectAll')) {
    if (battlefield.selectAllUnits()) respond('select')
  }
  else if (keys.matches(event, 'selectType')) {
    if (battlefield.selectSameType()) respond('select')
  }
  else if (keys.matches(event, 'deploy')) {
    const object = battlefield.selected
    if (object && isDeployable(object)) deployObject(object)
  }
  else if (keys.matches(event, 'scatter')) {
    for (const object of battlefield.selection.filter(Battlefield.own)) {
      const unit = object.userData.unit as Unit | undefined
      if (!unit || object.userData.harvester) continue
      const angle = Math.random() * Math.PI * 2
      combat?.stop([object])
      battlefield.walk(unit, battlefield.openSpot(object.position.clone().add(new THREE.Vector3(Math.cos(angle), 0, Math.sin(angle)).multiplyScalar(1.2))))
    }
  }
  else if (/^Digit\d$/.test(event.code)) team(Number(event.code.slice(5)), event)
  else if (keys.matches(event, 'home')) {
    // the construction yard (or barracks), else the MCV that is still to deploy
    const yard = battlefield.structuresOf('GACNST').find(Battlefield.own) ?? battlefield.structuresOf('GAPILE').find(Battlefield.own)
      ?? battlefield.structuresOf('NAHAND').find(Battlefield.own)
      ?? battlefield.units.map(u => u.object).find(o => o.userData.id === 'MCV' && Battlefield.own(o) && !o.userData.dead)
    if (yard) battlefield.lookAt(yard.position)
  }
}

/** Unfolds the MCV, digs the Tick Tank in or out, lets a transport's soldiers out (click on it or D) */
function deployObject(object: THREE.Object3D) {
  if (Battlefield.capacity(object)) unloadTransport(object)
  else if (Battlefield.digsIn(object)) digIn(object)
  else deployMcv(object)
}

/** Ctrl, Shift and Alt as held now (for the cursor) */
const modifiers = { ctrl: false, shift: false, alt: false }
function trackModifiers(event: KeyboardEvent | MouseEvent) {
  modifiers.ctrl = event.ctrlKey
  modifiers.shift = event.shiftKey
  modifiers.alt = event.altKey
}

/**
 * Teams like in the original: Ctrl+digit makes the selected units team 1 … 9 (0 is the
 * tenth), the digit selects it again, Shift+digit adds it to the selection; pressed
 * twice quickly the view jumps to the team.
 */
const teams = new Map<number, THREE.Object3D[]>()
let lastTeam = { number: -1, time: 0 }
/** Two presses of the same digit within this many milliseconds centre the view on the team */
const DOUBLE_PRESS = 400
function team(number: number, event: KeyboardEvent) {
  if (!battlefield) return
  event.preventDefault()
  if (event.ctrlKey) {
    const units = battlefield.selection.filter(Battlefield.multiSelectable)
    if (!units.length) return
    // a unit is in one team at a time
    for (const [n, members] of teams) teams.set(n, members.filter(object => !units.includes(object)))
    teams.set(number, units)
    return
  }
  const members = (teams.get(number) ?? []).filter(object => !object.userData.dead && object.parent)
  teams.set(number, members)
  if (!members.length) return
  const now = performance.now()
  const twice = lastTeam.number === number && now - lastTeam.time < DOUBLE_PRESS
  lastTeam = { number, time: now }
  if (event.shiftKey) battlefield.selectAll([...new Set([...battlefield.selection.filter(Battlefield.multiSelectable), ...members])])
  else battlefield.selectAll(members)
  respond('select')
  if (twice) {
    const centre = members.reduce((sum, object) => sum.add(object.position), new THREE.Vector3()).divideScalar(members.length)
    battlefield.lookAt(centre)
  }
}

function onWheel(event: WheelEvent) {
  event.preventDefault()
  if (!props.paused) battlefield?.zoomBy(-Math.sign(event.deltaY))
}

/**
 * The canvas follows the size of the battlefield, also when only the HUD around it
 * changes (its bars get their size after the battlefield is set up)
 */
const resizeObserver = new ResizeObserver(() => battlefield?.resize())

/** Foundations until the game's rules are loaded */
const FOUNDATIONS: Record<string, [number, number]> = { GACNST: [3, 3], GAPOWR: [2, 2], PROC: [4, 3], GAPILE: [2, 2], GASAND: [1, 1] }
/** Units without their own model yet use the light infantry's */
const UNIT_MODEL = UNIT_FALLBACK
/** The factories of each kind of unit: soldiers leave the barracks, vehicles the war factory, aircraft rise from the helipad */
const FACTORIES: Record<BuildInfo['category'], string[]> = {
  infantry: ['GAPILE', 'NAHAND'],
  vehicle: ['GAWEAP', 'NAWEAP'],
  aircraft: ['GAHPAD', 'NAHPAD'],
  structure: [],
}

/** Puts a structure of the player's base on the map. */
async function buildStructure(id: string, x: number, z: number, built = true) {
  if (!battlefield) return
  const [w, h] = skirmish?.rules?.info.get(id)?.foundation ?? FOUNDATIONS[id] ?? [2, 2]
  skirmish?.buildings.push(id)
  try {
    const object = await battlefield.addStructure(id, x, z, w, h, MODELS[id], props.colour, 'player', props.side)
    // factories can send what they produce to a rally point
    if (FACTORY_IDS.has(id)) object.userData.abilities = ['rally']
    if (id === 'GAPOWR') await addTurbine(object, props.colour)
    if (built) buildSound()
    if (id === 'PROC') addHarvester(object, built)
    return object
  }
  catch (error) {
    console.error(`${id} konnte nicht gebaut werden`, error)
  }
}
const FACTORY_IDS = new Set(Object.values(FACTORIES).flat())
/** Until the rules are loaded: bales a harvester carries and credits a bale is worth (Tiberian Sun) */
const HARVESTER_STORAGE = 28
const TIBERIUM_VALUE = 25
const BLUE_TIBERIUM_VALUE = 50
/** Seconds the refinery takes to build up (its Build clip, see blender/PROC.py) */
const REFINERY_BUILD_SECONDS = 3.4

/**
 * A refinery comes with its harvester, like in the original: it stands in the dock at
 * the back and drives out to work once the refinery has built up.
 */
async function addHarvester(refinery: THREE.Object3D, built: boolean) {
  if (!battlefield || !harvesting) return
  const { at, forward } = Harvesting.dock(refinery)
  const unit = await battlefield.addUnit(MODELS.HARV!, at, props.colour, 'player', props.side)
  unit.object.userData.id = 'HARV'
  unit.object.rotation.y = Math.atan2(forward.x, forward.z)
  harvesting.add(unit, refinery, built ? REFINERY_BUILD_SECONDS : 0.5)
}
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

/**
 * Selected units attack an enemy; false if they cannot (not an enemy, no weapons).
 * `force` (Ctrl): also their own side's units and buildings, and walls.
 */
function attack(target: THREE.Object3D, force = false) {
  if (!battlefield || !combat?.canAttack(battlefield.selection, target, force)) return false
  battlefield.clearWaypoints(battlefield.selection)
  harvesting?.order(battlefield.selection)
  combat.attack(battlefield.selection, target, force)
  respond('attack')
  return true
}

/**
 * The orders with a key held, like in the original: Ctrl fires at what is under the
 * cursor (force fire), Alt moves there whatever is there (force move). Returns whether
 * one was given.
 */
function forcedOrder(event: MouseEvent, object: THREE.Object3D | undefined) {
  if (event.ctrlKey && object) return attack(object, true)
  if (event.altKey && battlefield?.canMove) return order(event.clientX, event.clientY)
  return false
}

/** Own harvesters are selected */
function harvestersSelected() {
  return !!battlefield?.selection.some(object => object.userData.harvester && Battlefield.own(object))
}

/** An own refinery the selected harvesters can drive into to unload */
function canUnloadAt(object: THREE.Object3D) {
  return object.userData.id === 'PROC' && Battlefield.own(object) && !object.userData.dead && harvestersSelected()
}

/** The Tiberium under a point of the screen, if selected harvesters can be sent to harvest it */
function harvestTarget(clientX: number, clientY: number) {
  const ground = harvestersSelected() && battlefield?.groundAt(clientX, clientY)
  return ground ? battlefield!.tiberiumAt(ground) : undefined
}

/** Sends the selected harvesters into a refinery to unload; returns false if it is none they can use. */
function unloadAt(refinery: THREE.Object3D) {
  if (!battlefield || !canUnloadAt(refinery)) return false
  harvesting?.unloadAt(battlefield.selection, refinery)
  respond('move')
  sounds.play('click')
  return true
}

/** The first selected unit answers (select: "Reporting", move: "Moving out" …), like in the original */
function respond(voice: UnitVoice) {
  const id = battlefield?.selection.find(object => object.userData.unit && Battlefield.own(object))?.userData.id as string | undefined
  const files = id ? skirmish?.rules?.info.get(id)?.voices[voice] : undefined
  if (files?.length) sounds.respond(files)
}

let delivered = 0

/**
 * The selected MCV, Tick Tank or loaded transport of the player: a click on it unfolds
 * it (digs it in or out, lets the soldiers out)
 */
function isDeployable(object: THREE.Object3D) {
  const transport = Battlefield.capacity(object) > 0 && Battlefield.passengers(object).length > 0
  return object === battlefield?.selected && (!!DEPLOYS_INTO[object.userData.id] || Battlefield.digsIn(object) || transport)
    && Battlefield.own(object) && !!object.userData.unit
}

/** The selected soldiers of the player that could get into a transport */
function boarders(transport: THREE.Object3D) {
  return battlefield!.selection
    .map(object => object.userData.unit as Unit | undefined)
    .filter((unit): unit is Unit => !!unit && Battlefield.own(unit.object) && battlefield!.canBoard(unit, transport))
}

/** Whether the selected soldiers can get into this (an own transport with room): the enter cursor */
function canEnter(object: THREE.Object3D) {
  if (depotVehicles(object).length || hijackers(object).length || carryalls(object).length) return true
  return !!battlefield && Battlefield.capacity(object) > 0 && Battlefield.own(object) && boarders(object).length > 0
}

/** The selected mutant hijackers that could take this enemy vehicle over */
function hijackers(object: THREE.Object3D) {
  if (!battlefield || Battlefield.own(object) || object.userData.dead || infoOf(object)?.category !== 'vehicle' || object.userData.flyer) return []
  return battlefield.selection.filter(o => o.userData.id === 'MHIJACK' && Battlefield.own(o) && !o.userData.dead)
}

/** The selected carryalls that could pick this own vehicle up */
function carryalls(object: THREE.Object3D) {
  if (!battlefield || !Battlefield.own(object) || object.userData.dead || infoOf(object)?.category !== 'vehicle' || object.userData.flyer) return []
  return battlefield.selection.filter(o => o.userData.id === 'TRNSPORT' && Battlefield.own(o) && !o.userData.dead && !o.userData.carrying)
}

/** A hijacker this near (cells) to the vehicle gets into it */
const HIJACK_REACH = 1
/** How far below the carryall the vehicle it carries hangs (its Hook, see blender/TRNSPORT.py) */
const CARRY_DROP = 0.35

/**
 * Hijackers and carryalls at work: a hijacker that reaches the enemy vehicle it went for
 * takes it over (it becomes the player's, the mutant is gone into it); a carryall that
 * reaches the vehicle it was sent for picks it up and carries it under itself, and sets
 * it down where it comes to a stop.
 */
function tickTakers() {
  if (!battlefield) return
  for (const unit of battlefield.units) {
    const object = unit.object
    if (object.userData.dead) continue
    const prize = object.userData.hijack as THREE.Object3D | undefined
    if (prize) {
      if (prize.userData.dead || Battlefield.own(prize)) object.userData.hijack = undefined
      else if (Math.hypot(object.position.x - prize.position.x, object.position.z - prize.position.z) < HIJACK_REACH) {
        object.userData.hijack = undefined
        prize.userData.owner = 'player'
        prize.traverse((node) => {
          const mesh = node as THREE.Mesh
          for (const mat of mesh.isMesh ? [mesh.material].flat() as THREE.MeshStandardMaterial[] : []) applyHouseColour(mat, props.colour, props.side)
        })
        combat?.stop([prize])
        ;(prize.userData.unit as Unit).stop()
        battlefield.remove(object)
        sounds.speak('evaUnitReady')
      }
      else if (!unit.walking) battlefield.walk(unit, prize.position)
    }
    const load = object.userData.lift as THREE.Object3D | undefined
    if (load && !load.userData.dead && Math.hypot(object.position.x - load.position.x, object.position.z - load.position.z) < 0.25) {
      // hooked on: it hangs under the carryall from now on
      object.userData.lift = undefined
      object.userData.carrying = load
      object.userData.carryMoved = false
      object.userData.carryFrom = object.position.clone()
      load.userData.offGround = true
      load.userData.carried = true
      ;(load.userData.unit as Unit).stop()
    }
    const carried = object.userData.carrying as THREE.Object3D | undefined
    if (carried) {
      // it sets the vehicle down only at the end of the next flight the player sends it on
      const from = object.userData.carryFrom as THREE.Vector3 | undefined
      if (battlefield.flight.travelling(unit) && (!from || Math.hypot(object.position.x - from.x, object.position.z - from.z) > 0.5)) object.userData.carryMoved = true
      if (carried.userData.dead) object.userData.carrying = undefined
      else if (!battlefield.flight.travelling(unit) && object.userData.carryMoved) {
        object.userData.carryMoved = false
        // at its destination: set down there
        object.userData.carrying = undefined
        carried.userData.offGround = false
        carried.userData.carried = false
        carried.position.copy(battlefield.openSpot(object.position.clone()))
      }
      else carried.position.copy(object.position).setY(object.position.y - CARRY_DROP)
    }
  }
}

/** Buildings vehicles drive onto to be repaired (the service depot) */
const DEPOTS = new Set(['GADEPT'])

/** The selected own vehicles that could drive onto this service depot */
function depotVehicles(object: THREE.Object3D) {
  if (!battlefield || !DEPOTS.has(object.userData.id) || !Battlefield.own(object) || object.userData.dead) return []
  return battlefield.selection.filter(o => Battlefield.own(o) && infoOf(o)?.category === 'vehicle' && !o.userData.harvester)
}

/** Where a vehicle stands on a depot (its Pad node) */
function depotPad(depot: THREE.Object3D) {
  depot.updateMatrixWorld(true)
  return depot.getObjectByName('Pad')?.getWorldPosition(new THREE.Vector3()) ?? depot.position.clone()
}

/** Seconds of repair a credit buys … see Repairs; here: the share of strength a vehicle gets back each game second on the pad */
const DEPOT_RATE = 0.06

/**
 * Service depots repair the player's vehicles standing on their pad, as long as there is
 * money (RepairPercent= of the cost for a full repair), and their robot arms work meanwhile
 */
function tickDepots(seconds: number) {
  if (!battlefield || !skirmish) return
  for (const depot of battlefield.structureObjects) {
    if (!DEPOTS.has(depot.userData.id) || !Battlefield.own(depot) || depot.userData.dead || depot.userData.poweredOff) continue
    const pad = depotPad(depot)
    const vehicle = battlefield.units.map(u => u.object).find((o) => {
      const info = infoOf(o)
      return Battlefield.own(o) && !o.userData.dead && info?.category === 'vehicle' && Math.hypot(o.position.x - pad.x, o.position.z - pad.z) < 0.6
        && (o.userData.hp ?? info.strength) < info.strength
    })
    const working = !!vehicle
    if (working !== !!depot.userData.repairing) {
      depot.userData.repairing = working
      battlefield.playClip(depot, 'Fire', working ? { hold: true } : { reverse: true })
    }
    if (!vehicle) continue
    const info = infoOf(vehicle)!
    const step = info.strength * DEPOT_RATE * seconds
    const price = (step / info.strength) * info.cost * (skirmish.rules?.upkeep ?? DEFAULT_UPKEEP).repairCost
    if (skirmish.credits.value < price) continue
    skirmish.credits.value -= price
    vehicle.userData.hp = Math.min(info.strength, (vehicle.userData.hp ?? info.strength) + step)
    vehicle.userData.health = vehicle.userData.hp / info.strength
  }
}

/** Sends the selected soldiers into a transport (vehicles onto a service depot); returns false if it is none they can get into */
function enter(transport: THREE.Object3D) {
  // mutant hijackers go for an enemy vehicle, a carryall for an own one
  const thieves = hijackers(transport)
  const lifters = carryalls(transport)
  if (battlefield && (thieves.length || lifters.length)) {
    for (const object of thieves) {
      combat?.stop([object])
      object.userData.hijack = transport
      battlefield.walk(object.userData.unit as Unit, transport.position)
    }
    for (const object of lifters) {
      object.userData.lift = transport
      object.userData.carrying = undefined
      battlefield.flight.flyTo(object.userData.unit as Unit, transport.position)
    }
    respond('move')
    sounds.play('click')
    return true
  }
  const vehicles = depotVehicles(transport)
  if (battlefield && vehicles.length) {
    // one after the other onto the pad: the first drives on, the others wait next to it
    const pad = depotPad(transport)
    vehicles.forEach((object, i) => {
      combat?.stop([object])
      battlefield!.walk(object.userData.unit as Unit, i === 0 ? pad : battlefield!.openSpot(pad.clone().add(new THREE.Vector3(i, 0, 2))))
    })
    respond('move')
    sounds.play('click')
    return true
  }
  if (!battlefield || !canEnter(transport)) return false
  const units = boarders(transport)
  combat?.stop(units.map(unit => unit.object))
  battlefield.board(units, transport)
  respond('move')
  sounds.play('click')
  return true
}

/** Lets a transport's soldiers out round it; not under the ground or while it digs */
function unloadTransport(object: THREE.Object3D) {
  if (!battlefield!.unload(object).length) {
    sounds.play('evaCannotPlace')
    return
  }
  sounds.play('click')
}

/** Whether it can deploy where it stands: the MCV on 3 × 3 free flat cells, the Tick Tank on flat ground (or it is dug in) */
function canDeploy(object: THREE.Object3D) {
  const unit = object.userData.unit as Unit
  if (Battlefield.capacity(object)) return battlefield!.canUnload(object)
  if (Battlefield.digsIn(object)) return !!unit.posture || battlefield!.canDig(object.position)
  const into = DEPLOYS_INTO[object.userData.id]
  return !!into && !!battlefield!.deployCell(unit, into.w, into.h)
}

/** Digs a Tick Tank in where it stands, or out again; not on a slope or a ramp */
function digIn(object: THREE.Object3D) {
  if (!battlefield!.toggleDigIn(object.userData.unit as Unit)) {
    sounds.play('evaCannotPlace')
    return
  }
  sounds.play('click')
}

/** Unfolds the MCV into a construction yard where it stands, if the 3 × 3 cells are free. */
/** What vehicles unfold into (DeploysInto=): the MCV into the construction yard, Firestorm's mobile war factories into a war factory */
const DEPLOYS_INTO: Record<string, { id: string, w: number, h: number }> = {
  MCV: { id: 'GACNST', w: 3, h: 3 },
  MOBWARG: { id: 'GAWEAP', w: 4, h: 3 },
  MOBWARN: { id: 'NAWEAP', w: 4, h: 3 },
}

function deployMcv(object: THREE.Object3D) {
  const unit = object.userData.unit as Unit | undefined
  const into = DEPLOYS_INTO[object.userData.id]
  if (!battlefield || !unit || !into) return
  if (!battlefield.deployCell(unit, into.w, into.h)) {
    sounds.play('evaCannotPlace')
    return
  }
  sounds.play('click')
  battlefield.deploy(unit, MODELS[into.id]!, props.colour, into.id, into.w, into.h)
    .then((building) => {
      if (!building) return
      skirmish?.buildings.push(into.id)
      if (FACTORY_IDS.has(into.id)) building.userData.abilities = ['rally']
      buildSound() // it unfolds now
    })
    .catch(error => console.error(`${into.id} konnte nicht aufgebaut werden`, error))
}

/** Dropships on their way in: the camera follows them until they are down */
const escorted: Dropship[] = []
/** Where dropships come from and fly off to (world, on the ground): from the top edge of the screen, away to the right */
const DROPSHIP_IN = new THREE.Vector3(-1, 0, -1)
const DROPSHIP_OUT = new THREE.Vector3(1, 0, -1)

/**
 * Reinforcements by dropship, like at the start of the original's missions: it flies
 * in from the edge of the map, lands at `at`, the units come out over its ramp, and it
 * flies off over the map edge again. Settles once the last unit is out.
 */
async function dropship(ids: string[], at: THREE.Vector3, landed?: () => void) {
  if (!battlefield) return
  const colour = props.colour
  const from = battlefield.edgePoint(at, DROPSHIP_IN)
  const leave = battlefield.edgePoint(at, DROPSHIP_OUT)
  let unloaded!: () => void
  const out = new Promise<void>((resolve) => {
    unloaded = resolve
  })
  const ship = await battlefield.addDropship(MODELS.DSHP!, from, {
    to: at,
    leave,
    unload: (exit) => {
      landed?.()
      return unloadSoldiers(exit).finally(unloaded)
    },
  }, colour)
  ship.onSound = sound => sounds.effect(DROPSHIP_SOUNDS[sound])
  escorted.push(ship)
  battlefield.lookAt(from)
  return out

  async function unloadSoldiers(exit: THREE.Vector3) {
    const away = exit.clone().sub(at).setY(0).normalize()
    const side = new THREE.Vector3(-away.z, 0, away.x)
    for (const [i, id] of ids.entries()) {
      if (!battlefield) return
      const unit = await battlefield.addUnit(MODELS[id] ?? UNIT_MODEL, exit, colour, 'player', props.side)
      unit.object.userData.id = id
      battlefield.walk(unit, exit.clone().addScaledVector(away, id === 'MCV' ? 2 : 1.2).addScaledVector(side, (i - (ids.length - 1) / 2) * 0.7))
      await new Promise(resolve => setTimeout(resolve, 600 / (SPEED_FACTORS[settings.speed] ?? 1)))
    }
  }
}

let lastFundsWarning = -Infinity
/** Seconds between two "Our base is under attack" (or "Harvester under attack") */
const ATTACK_WARNING_INTERVAL = 30
let lastBaseAttack = -Infinity
/** Seconds between two hit feedbacks (VoiceFeedback=) */
const FEEDBACK_INTERVAL = 4
let lastFeedback = -Infinity
let lastHarvesterAttack = -Infinity
let superWeapons: SuperWeapons | undefined
/** Every so often the lamed things crackle */
let empSparkTime = 0

/**
 * The player's special weapons charge (with enough power, if they need it) and show in
 * the sidebar; EVA says when one is ready. One the player clicked in the sidebar that
 * needs no target (the firestorm, the hunter seeker) goes off at once.
 */
function tickSpecials(seconds: number) {
  const rules = skirmish?.rules
  if (!skirmish || !rules || !battlefield) return
  superWeapons ??= new SuperWeapons(rules.superWeapons)
  superWeapons.sync(onlineBuildings(skirmish))
  for (const charge of superWeapons.tick(seconds, powerFactor(skirmish) >= 1)) sounds.effect(charge.type.readyVoice, 'voices')
  const charges = superWeapons.charges
  if (skirmish.specials.length !== charges.length || skirmish.specials.some((s, i) => s.id !== charges[i]!.type.id)) {
    skirmish.specials = charges.map(c => ({ id: c.type.id, name: c.type.name, cameo: c.type.cameo, progress: 0, ready: false, active: false }))
  }
  charges.forEach((charge, i) => {
    const special = skirmish.specials[i]!
    special.progress = Math.round(charge.progress * 100) / 100
    special.ready = charge.ready
    special.active = charge.active
  })
  const waiting = charges.find(c => c.type.id === skirmish.targeting)
  if (waiting && !waiting.type.targeted) {
    skirmish.targeting = undefined
    if (waiting.ready || waiting.active) fireSpecial(waiting)
  }
  const firestorm = charges.some(c => c.type.kind === 'Firestorm' && c.active)
  battlefield.setFirestorm('player', firestorm)
  // the firestorm burns what tries to pass it
  if (firestorm) {
    for (const unit of battlefield.units) {
      if (!Battlefield.own(unit.object) && !unit.object.userData.dead && battlefield.inFirestorm(unit.object.position, 'enemy')) {
        combat?.blast(unit.object.position, 1000, 0.3)
      }
    }
  }
  // things lamed by a pulse crackle
  empSparkTime -= seconds
  if (empSparkTime <= 0) {
    empSparkTime = 0.15
    for (const object of [...battlefield.units.map(u => u.object), ...battlefield.structureObjects]) {
      if (object.userData.empSeconds > 0 && !object.userData.dead) battlefield.effects.empSparks(object.position)
    }
  }
}

/** The player's building that gives a special weapon (the nearest to `point`, if given) */
function specialSource(charge: SuperWeaponCharge, point?: THREE.Vector3) {
  const own = battlefield!.structureObjects.filter(o => charge.type.buildings.includes(o.userData.id) && Battlefield.own(o) && !o.userData.dead)
  if (!point) return own[0]
  return own.sort((a, b) => a.position.distanceTo(point) - b.position.distanceTo(point))[0]
}

/** Game seconds to milliseconds of real time at the game speed */
const later = (seconds: number, then: () => void) => setTimeout(then, (seconds * 1000) / (SPEED_FACTORS[settings.speed] ?? 1))

/** Cells round the target the ion cannon hurts, the pulse lames, the gas poisons */
const ION_RADIUS = 2
const EMP_RADIUS = 4
const GAS_RADIUS = 2.5
/** Game seconds a pulse lames (Damage= of EMPulseWeapon is in frames) */
const EMP_FRAMES = 1200
/** Damage of the hunter seeker (it destroys what it reaches) and of the chemical missile's blast and gas */
const SEEKER_DAMAGE = 2000
const CHEM_DAMAGE = 100
const GAS_DAMAGE = 15

/**
 * Fires a special weapon, as in the original: the ion cannon strikes from the sky, the
 * EMP cannon fires a pulse that lames vehicles and buildings, the missile silo sends the
 * chemical missile (blast and poison gas), the hunter seeker flies to an enemy building
 * and destroys it, drop pods bring soldiers down, the firestorm is switched on or off.
 */
function fireSpecial(charge: SuperWeaponCharge, point?: THREE.Vector3) {
  if (!battlefield || !combat || !skirmish?.rules) return
  const source = specialSource(charge, point)
  superWeapons!.use(charge)
  const rules = skirmish.rules
  switch (charge.type.kind) {
    case 'IonCannon': {
      if (!point) return
      // the uplink lines up its dish
      const uplink = battlefield.structuresOf('GAPLUG').find(Battlefield.own)
      for (const node of uplink ? [uplink] : []) {
        node.traverse(child => child.userData.mixer && child !== node && battlefield!.playClip(child, 'Fire'))
      }
      sounds.effect(['ION1'], 'shots')
      later(0.8, () => {
        battlefield?.effects.ionStrike(point, ION_RADIUS)
        later(0.5, () => combat?.blast(point, rules.specials.ionDamage, ION_RADIUS))
      })
      return
    }
    case 'EMPulse': {
      if (!point || !source) return
      battlefield.playClip(source, 'Fire')
      sounds.effect(['PLSECAN2'], 'shots')
      // the pulse flies over in an arc (Lobber=)
      const flight = Math.max(0.6, source.position.distanceTo(point) / 8)
      later(flight, () => {
        battlefield?.effects.empBurst(point, EMP_RADIUS)
        combat?.pulse(point, EMP_RADIUS, EMP_FRAMES / 15)
      })
      return
    }
    case 'ChemMissile': {
      if (!point || !source) return
      battlefield.playClip(source, 'Open', { hold: true })
      sounds.effect(['ICBM1'], 'shots')
      later(1.5, () => battlefield?.playClip(source, 'Open', { reverse: true }))
      later(1.2 + source.position.distanceTo(point) / 10, () => {
        battlefield?.effects.explosion(point, 1.6)
        battlefield?.effects.gasCloud(point, GAS_RADIUS)
        combat?.blast(point, CHEM_DAMAGE, GAS_RADIUS)
        // the gas lingers and poisons who stays in it
        for (let i = 1; i <= 6; i++) later(i, () => combat?.blast(point, GAS_DAMAGE, GAS_RADIUS, { wall: false }))
      })
      return
    }
    case 'HunterSeeker': {
      // it picks an enemy building (else a unit) and flies to it
      const targets = battlefield.structureObjects.filter(o => !Battlefield.own(o) && !o.userData.dead && o.userData.owner !== 'neutral' && !Battlefield.isWall(o))
      const units = battlefield.units.map(u => u.object).filter(o => !Battlefield.own(o) && !o.userData.dead)
      const target = targets[Math.floor(Math.random() * targets.length)] ?? units[0]
      if (!target || !source) return
      later(1 + source.position.distanceTo(target.position) / 6, () => {
        if (target.userData.dead) return
        battlefield?.effects.explosion(target.position.clone().setY(target.position.y + 0.3), 1.4)
        combat?.blast(target.position, SEEKER_DAMAGE, 1)
      })
      return
    }
    case 'DropPod': {
      if (!point) return
      const [min, max] = rules.specials.dropPods
      const count = min + Math.floor(Math.random() * (max - min + 1))
      for (let i = 0; i < count; i++) {
        const at = battlefield.openSpot(point.clone().add(new THREE.Vector3((Math.random() - 0.5) * 2.4, 0, (Math.random() - 0.5) * 2.4)))
        later(0.3 + i * 0.25, () => {
          if (!battlefield) return
          battlefield.effects.explosion(at, 0.4)
          sounds.effect(rules.audio.get('DROPPOD') ?? [], 'shots')
          const id = i % 3 === 2 ? 'E2' : 'E1'
          battlefield.addUnit(MODELS[id] ?? UNIT_MODEL, at, props.colour, 'player', props.side)
            .then((unit) => { unit.object.userData.id = id })
            .catch(error => console.error('Landekapsel', error))
        })
      }
      return
    }
    case 'Firestorm':
      sounds.effect(charge.active ? ['FIRSTRM1'] : [], 'shots')
  }
}

/** Seconds a war factory's door stays open after a vehicle has come out */
const DOOR_OPEN_SECONDS = 2

/**
 * A finished unit comes out of its factory (the newest of its kind the player has): at
 * the factory's Exit node, through the war factory's opening door, and walks to the
 * rally point or a bit out. Aircraft rise from their helipad (see Aircraft).
 */
async function deliver(info: BuildInfo) {
  if (!battlefield) return
  const factory = battlefield.structureObjects.filter(o => FACTORIES[info.category].includes(o.userData.id) && Battlefield.own(o) && !o.userData.dead).at(-1)
  if (!factory) return
  factory.updateMatrixWorld(true)
  const exit = factory.getObjectByName('Exit')
  const door = exit ? exit.getWorldPosition(new THREE.Vector3()) : factory.position.clone().add(new THREE.Vector3(0.46, 0, 1.0))
  const out = exit ? exit.getWorldDirection(new THREE.Vector3()).setY(0).normalize() : new THREE.Vector3(0.3, 0, 1).normalize()
  const opens = battlefield.playClip(factory, 'Open', { hold: true })
  if (opens) {
    clearTimeout(factory.userData.doorTimer)
    factory.userData.doorTimer = setTimeout(() => battlefield?.playClip(factory, 'Open', { reverse: true }), (opens + DOOR_OPEN_SECONDS) * 1000 / (SPEED_FACTORS[settings.speed] ?? 1))
  }
  // the vehicle appears once the door is open (else it would poke through the closed door)
  if (opens) await new Promise(resolve => later(opens, () => resolve(undefined)))
  if (!battlefield || factory.userData.dead) return
  const unit = await battlefield.addUnit(MODELS[info.id] ?? UNIT_MODEL, door, props.colour, 'player', props.side)
  unit.object.userData.id = info.id
  unit.object.rotation.y = Math.atan2(out.x, out.z)
  // an aircraft stands on its helipad, ready to take off; a jumpjet soldier flies where it is sent
  if (info.category === 'aircraft') {
    battlefield.flight.addAircraft(unit, factory, info.ammo)
    return
  }
  if (info.jumpjet) battlefield.flight.addJumpjet(unit)
  const rally = factory.userData.rallyPoint as THREE.Vector3 | undefined
  // each one stands a bit apart from the last, round the rally point
  delivered++
  const angle = delivered * 2.4
  const radius = 0.35 + 0.18 * Math.sqrt(delivered % 12)
  const spread = new THREE.Vector3(Math.cos(angle) * radius, 0, Math.sin(angle) * radius)
  // to a free spot: in front of the door may be another building; a harvester goes to work
  const onwards = () => info.id === 'HARV'
    ? harvesting?.add(unit)
    : battlefield?.walk(unit, battlefield.openSpot((rally ?? door.clone().addScaledVector(out, 2.2)).clone().add(spread)))
  // first straight out through the door and off the factory's foundation (inside it no
  // way can be found: all its cells are taken), then on round anything in the way
  const leave = () => {
    if (!battlefield || unit.object.userData.dead) return
    const outside = clearOf(factory, door, out)
    unit.walkTo(outside)
    const wait = setInterval(() => {
      if (unit.walking && !unit.object.userData.dead) return
      clearInterval(wait)
      if (!unit.object.userData.dead) onwards()
    }, 100)
  }
  leave()
}

/** The first point from `door` along `out` that is off the building's foundation (half a cell beyond its edge) */
function clearOf(building: THREE.Object3D, door: THREE.Vector3, out: THREE.Vector3) {
  const f = building.userData.footprint as { x: number, z: number, w: number, h: number } | undefined
  const point = door.clone()
  if (!f) return point.addScaledVector(out, 1)
  const inside = (p: THREE.Vector3) => p.x >= f.x - 0.5 && p.x < f.x + f.w + 0.5 && p.z >= f.z - 0.5 && p.z < f.z + f.h + 0.5
  for (let step = 0; step < 40 && inside(point); step++) point.addScaledVector(out, 0.1)
  return point
}

/** Shows or hides the placement preview when the sidebar starts or stops placing. */
let placingId: string | undefined
function syncPlacement() {
  if (!battlefield || placingId === skirmish?.placing?.id) return
  placingId = skirmish?.placing?.id
  const info = skirmish?.placing
  // a gun for the component tower: a square that is white on top of a tower it fits, red elsewhere
  if (info?.powersUp) battlefield.startPlacement(1, 1, 0, (x, z) => towerTop(info, x, z))
  // pavement is laid on the free cells of its 4 × 4, the others are left out
  else if (info && PAVING.has(info.id)) battlefield.startPlacement(info.foundation[0], info.foundation[1], info.adjacent, undefined, true)
  else if (info) battlefield.startPlacement(info.foundation[0], info.foundation[1], info.adjacent)
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
  placeAt(info, cell)
}

/** Puts a finished structure down with its lower corner on `cell` */
function placeAt(info: BuildInfo, cell: [number, number]) {
  if (!skirmish) return
  skirmish.placing = undefined
  skirmish.production.placed()
  syncPlacement()
  if (PAVING.has(info.id)) {
    battlefield!.pave(battlefield!.paveCells(cell[0], cell[1], info.foundation[0], info.foundation[1], info.adjacent))
    buildSound()
    return
  }
  if (info.powersUp) {
    const building = upgradeTarget(info, cell[0], cell[1])
    if (building) mountGun(building, info.id)
    return
  }
  buildStructure(info.id, cell[0], cell[1])
  // the construction yard's crane lets a crate down into its hatch
  const yard = battlefield!.structuresOf('GACNST').filter(Battlefield.own).at(-1)
  if (yard) battlefield!.playClip(yard, 'Deliver')
}

/** Structures that are laid on the ground instead of standing on it (ToTile= in ART.INI: pavement) */
const PAVING = new Set(['GAPAVE'])

/** Whether a gun (the Vulcan, the SAM) can go onto this building: an own component tower without one */
function towerFor(info: BuildInfo, object: THREE.Object3D) {
  return object.userData.id === info.powersUp && Battlefield.own(object) && !object.userData.dead
    && !object.userData.gun && !!battlefield?.freeSlot(object)
}

/** The building on a cell an upgrade fits on (with a free place), if any */
function upgradeTarget(info: BuildInfo, x: number, z: number) {
  const building = battlefield?.buildingOn(x, z)
  return building && towerFor(info, building) ? building : undefined
}

/** The height of the free place on the building on the cell the upgrade fits on, undefined if there is none */
function towerTop(info: BuildInfo, x: number, z: number) {
  const building = upgradeTarget(info, x, z)
  if (!building) return undefined
  building.updateMatrixWorld(true)
  const slot = battlefield!.freeSlot(building)
  return (slot ? slot.getWorldPosition(new THREE.Vector3()).y : new THREE.Box3().setFromObject(building).max.y) - building.position.y
}

/**
 * Mounts an upgrade on its building's next free place: a gun on the component tower
 * (the tower fires with it from now on, see Combat), a turbine on the power plant, the
 * uplink and the others on the upgrade center
 */
async function mountGun(building: THREE.Object3D, id: string) {
  const armed = !!skirmish?.rules?.info.get(id)?.weapon
  if (armed) building.userData.gun = true // taken while the model loads
  skirmish?.buildings.push(id)
  buildSound()
  const upgrade = await battlefield?.addUpgrade(building, MODELS[id]!, props.colour)
    .catch(error => console.error(`${id} konnte nicht montiert werden`, error))
  if (!upgrade) return
  upgrade.userData.id = id
  upgrade.userData.owner = building.userData.owner
  if (armed) building.userData.gun = upgrade
}

let combat: Combat | undefined
let harvesting: Harvesting | undefined
let repairs: Repairs | undefined

/** What RULES.INI says about an object */
const infoOf = (object: THREE.Object3D) => skirmish?.rules?.info.get(object.userData.id)

/** An own building that still stands */
function ownBuilding(object: THREE.Object3D | undefined) {
  return object?.userData.footprint && Battlefield.own(object) && !object.userData.dead ? object : undefined
}

const canSell = (object?: THREE.Object3D) => !!ownBuilding(object) && (infoOf(object!)?.sellable ?? true)
/** Damaged and repairable, or being repaired (a click stops it) */
const canRepair = (object?: THREE.Object3D) => !!ownBuilding(object) && (infoOf(object!)?.repairable ?? true)
  && (!!object!.userData.repairing || !!repairs?.damaged(object!))
/** Only buildings that use power can be switched off */
const canSwitch = (object?: THREE.Object3D) => !!ownBuilding(object) && (infoOf(object!)?.power ?? 0) < 0

/** The cursor of a sidebar button's mode over what is under it */
function modeCursor(mode: BaseMode, hovered: THREE.Object3D | undefined, clientX: number, clientY: number): CursorKind {
  switch (mode) {
    case 'sell': return canSell(hovered) ? 'sell' : 'sell-blocked'
    case 'repair': return canRepair(hovered) ? 'repair' : 'repair-blocked'
    case 'power': return canSwitch(hovered) ? 'power' : 'power-blocked'
    // units can still be picked while setting waypoints
    case 'waypoint': return hovered ? 'select' : battlefield?.canSetWaypoints && battlefield.groundAt(clientX, clientY) ? 'waypoint' : 'default'
  }
}

/** A left click while a sidebar button is on; the mode stays on until switched off */
function useMode(mode: BaseMode, clientX: number, clientY: number) {
  if (!battlefield) return
  const object = battlefield.objectAt(clientX, clientY)
  if (mode === 'waypoint') {
    const ground = battlefield.groundAt(clientX, clientY)
    if (object) {
      battlefield.select(object)
      respond('select')
    }
    else if (ground && battlefield.canSetWaypoints) {
      combat?.stop(battlefield.selection)
      battlefield.addWaypoint(ground)
      respond('move')
      sounds.play('click')
    }
    return
  }
  if (mode === 'sell' && canSell(object)) sell(object!)
  else if (mode === 'repair' && canRepair(object)) repair(object!)
  else if (mode === 'power' && canSwitch(object)) switchPower(object!)
}

/**
 * Sells a building: RefundPercent= of its cost comes back (less for a damaged one), it
 * folds up and is gone (SellSound=CASHTURN, EVA: "Structure sold").
 */
function sell(building: THREE.Object3D) {
  if (!battlefield) return
  const cost = infoOf(building)?.cost ?? 0
  const refund = Math.round(cost * (skirmish?.rules?.upkeep ?? DEFAULT_UPKEEP).refund * (building.userData.health ?? 1))
  battlefield.unbuild(building)
  forget(building)
  releaseCrew(building)
  if (skirmish) skirmish.credits.value += refund
  sounds.effect(['CASHTURN'])
  sounds.speak('evaStructureSold')
}

/** Starts or stops repairing a building (EVA: "Repairing") */
function repair(building: THREE.Object3D) {
  sounds.play('click')
  if (repairs?.toggle(building)) sounds.speak('evaRepairing')
}

/**
 * Switches a building off or on again: switched off it uses no power and does not work
 * (its Idle clip stands still; EVA: "Building offline" / "Building online").
 */
function switchPower(building: THREE.Object3D) {
  if (!skirmish) return
  const off = !building.userData.poweredOff
  building.userData.poweredOff = off || undefined
  const id = building.userData.id as string
  if (off) skirmish.offline.push(id)
  else skirmish.offline.splice(skirmish.offline.indexOf(id), 1)
  const idle = (building.userData.clips as THREE.AnimationClip[] | undefined)?.find(c => c.name === 'Idle')
  const action = idle && (building.userData.mixer as THREE.AnimationMixer | undefined)?.existingAction(idle)
  if (action) action.paused = off
  // a laser fence post switched off drops its fences
  if (id === 'NAPOST') battlefield?.updateFences()
  sounds.play('click')
  sounds.speak(off ? 'evaBuildingOffline' : 'evaBuildingOnline')
}

/** Most soldiers that come out of one building */
const MAX_SURVIVORS = 5

/**
 * Soldiers come out of a building of the player that is sold or destroyed, like in the
 * original: Crewed= buildings let SurvivorRate= of their cost / SurvivorDivisor= of them
 * (Crew=, light infantry) out round their foundation.
 */
function releaseCrew(building: THREE.Object3D) {
  const info = infoOf(building)
  const footprint = building.userData.footprint as { x: number, z: number, w: number, h: number } | undefined
  if (!battlefield || !info?.crewed || !footprint || !Battlefield.own(building)) return
  const survivors = skirmish?.rules?.survivors ?? DEFAULT_SURVIVORS
  const count = Math.min(MAX_SURVIVORS, Math.floor((info.cost * survivors.rate) / survivors.divisor))
  const centre = new THREE.Vector3(footprint.x + footprint.w / 2, 0, footprint.z + footprint.h / 2)
  for (let i = 0; i < count; i++) {
    const angle = (i / Math.max(1, count)) * Math.PI * 2
    const at = centre.clone().add(new THREE.Vector3(Math.cos(angle) * 0.3, 0, Math.sin(angle) * 0.3))
    battlefield.addUnit(MODELS[survivors.crew] ?? UNIT_MODEL, at, props.colour, 'player', props.side).then((unit) => {
      unit.object.userData.id = survivors.crew
      // out of the ruin, to the nearest free spot beside it
      const out = centre.clone().add(new THREE.Vector3(Math.cos(angle), 0, Math.sin(angle)).multiplyScalar(Math.max(footprint.w, footprint.h) / 2 + 0.8))
      battlefield?.walk(unit, battlefield.openSpot(out))
    }).catch(error => console.error('Überlebende konnten nicht erscheinen', error))
  }
}

/** A building of the player is gone (destroyed, sold): it no longer counts for power and what can be built */
function forget(building: THREE.Object3D) {
  if (!Battlefield.own(building) || !skirmish) return
  const id = building.userData.id as string
  const i = skirmish.buildings.indexOf(id)
  if (i >= 0) skirmish.buildings.splice(i, 1)
  const off = building.userData.poweredOff ? skirmish.offline.indexOf(id) : -1
  if (off >= 0) skirmish.offline.splice(off, 1)
  // the gun on a component tower goes with it
  const gun = building.userData.gun as THREE.Object3D | true | undefined
  const g = gun && gun !== true ? skirmish.buildings.indexOf(gun.userData.id) : -1
  if (g >= 0) skirmish.buildings.splice(g, 1)
}

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
  // the original signs over buildings (repair wrench, switched off)
  getAssetStore()
    .then(store => loadSigns(store))
    .then(frames => frames && battlefield?.setSigns(frames, cursorScale()))
    .catch(error => console.error('Gebäude-Symbole konnten nicht geladen werden', error))
  // fighting with the values of RULES.INI; shots and death cries from SOUNDS.MIX
  // aircraft taking off and landing (AuxSound1=, AuxSound2=)
  battlefield.flight.sound = (unit, event) => {
    const info = skirmish?.rules?.info.get(unit.object.userData.id)
    sounds.effect((event === 'takeOff' ? info?.takeOffSound : info?.landSound) ?? [])
  }
  // the battlefield's own sounds ([AudioVisual] of RULES.INI: gates, digging …)
  battlefield.sound = (key) => {
    const files = skirmish?.rules?.audio.get(key)
    if (files?.length) sounds.effect(files)
  }
  combat = markRaw(new Combat(
    battlefield,
    object => skirmish?.rules?.info.get(object.userData.id),
    {
      fire: (_, info) => sounds.effect(info.weapon?.reports ?? [], 'shots'),
      impact: weapon => sounds.effect(weapon.impactReports, 'shots'),
      // CloakSound= of [AudioVisual], for the player's own (the enemy is not heard cloaking)
      cloak: (object) => {
        if (Battlefield.own(object)) sounds.effect(skirmish?.rules?.audio.get('CLOAKSOUND') ?? [], 'shots')
      },
      blast: (_, info, delay) => setTimeout(() => sounds.effect(info.explosionReports, 'shots'), delay * 1000 / (SPEED_FACTORS[settings.speed] ?? 1)),
      die(victim, info, crushed) {
        // run down: the squelch (CrushSound=) instead of the death cry
        if (crushed && info.crushSound.length) sounds.effect(info.crushSound, 'shots')
        else sounds.effect(info.voices.die, 'voices')
        // a vehicle blows up (Explosion=)
        sounds.effect(info.explosionReports, 'shots')
        if (Battlefield.own(victim)) sounds.speak('evaUnitLost')
      },
      // EVA warns when a building or a harvester of the player is attacked, not again for every shot
      hit(target) {
        if (!Battlefield.own(target)) return
        // a unit that says something when hit (VoiceFeedback=: the limpet drone …)
        const feedback = infoOf(target)?.voices.feedback
        if (feedback?.length && performance.now() - lastFeedback > FEEDBACK_INTERVAL * 1000) {
          lastFeedback = performance.now()
          sounds.effect(feedback, 'voices')
        }
        const harvester = !!target.userData.harvester
        if (!harvester && (!target.userData.footprint || Battlefield.isWall(target))) return
        const now = performance.now()
        const last = harvester ? lastHarvesterAttack : lastBaseAttack
        if (now - last < ATTACK_WARNING_INTERVAL * 1000) return
        if (harvester) lastHarvesterAttack = now
        else lastBaseAttack = now
        sounds.speak(harvester ? 'evaHarvesterAttack' : 'evaBaseAttack')
      },
      // a lost building of the player no longer counts for power and what can be built;
      // its crew gets out
      destroyed(building) {
        forget(building)
        releaseCrew(building)
      },
    },
  ))
  // repairs with the sidebar's button: RepairPercent=, RepairRate=, RepairStep= from RULES.INI
  repairs = markRaw(new Repairs(battlefield, () => ({
    upkeep: skirmish?.rules?.upkeep ?? DEFAULT_UPKEEP,
    info: object => infoOf(object),
    pay(credits) {
      if (!skirmish || skirmish.credits.value < credits) return false
      skirmish.credits.value -= credits
      return true
    },
    broke: () => sounds.speak('evaInsufficientFunds'),
  })))
  // the harvesters at work: Storage= and the Tiberium's Value= from RULES.INI
  harvesting = markRaw(new Harvesting(battlefield, () => ({
    capacity: unit => skirmish?.rules?.info.get(unit.object.userData.id)?.storage || HARVESTER_STORAGE,
    value: kind => kind === 'blue'
      ? skirmish?.rules?.blueTiberiumValue ?? BLUE_TIBERIUM_VALUE
      : skirmish?.rules?.tiberiumValue ?? TIBERIUM_VALUE,
    earn(owner, credits) {
      if (owner === 'player' && skirmish) skirmish.credits.value += credits
    },
  })))
  emit('ready', battlefield)
  // dev only: an agent outside the browser can play (scripts/agent.mjs)
  if (import.meta.dev && skirmish) {
    unlinkAgent = linkAgent(agentCommands({
      battlefield,
      skirmish,
      combat: combat!,
      harvesting: harvesting!,
      techLevel: () => props.techLevel,
      paused: () => props.paused || needsResume(),
      clock: () => clock,
      place: placeAt,
      deploy(object) {
        if (!canDeploy(object)) return false
        if (Battlefield.capacity(object)) unloadTransport(object)
        else if (Battlefield.digsIn(object)) digIn(object)
        else if (DEPLOYS_INTO[object.userData.id]) deployMcv(object)
        else return false
        return true
      },
      sell: object => canSell(object) && (sell(object), true),
      // dev tests: put a unit or a finished structure down at once, charge the special weapons
      async spawn(id, at, owner) {
        const unit = await battlefield!.addUnit(MODELS[id] ?? UNIT_MODEL, at, owner === 'player' ? props.colour : 0xb3241a, owner,
          owner === 'player' ? props.side : props.side === 'gdi' ? 'nod' : 'gdi')
        unit.object.userData.id = id
        const info = skirmish?.rules?.info.get(id)
        if (info?.category === 'aircraft') battlefield!.flight.addAircraft(unit, undefined, info.ammo)
        else if (info?.jumpjet) battlefield!.flight.addJumpjet(unit)
        return unit.object
      },
      async instant(info, cell) {
        if (info.powersUp || PAVING.has(info.id)) placeAt(info, cell)
        else await buildStructure(info.id, cell[0], cell[1])
      },
      charge() {
        for (const charge of superWeapons?.charges ?? []) charge.progress = 0.999
      },
      repair: object => canRepair(object) && (repair(object), true),
      switchPower: object => canSwitch(object) && (switchPower(object), true),
    }))
  }
  emit('start', markRaw({
    battlefield,
    combat: combat!,
    colour: props.colour,
    buildStructure,
    async addUnit(id, at, colour = props.colour, owner = 'player', side = props.side) {
      const unit = await battlefield!.addUnit(MODELS[id] ?? UNIT_MODEL, at, colour, owner, side)
      unit.object.userData.id = id
      return unit.object
    },
    async dropship(ids, at, landed) {
      await dropship(ids, at, landed)
    },
  }))
  resizeObserver.observe(stage.value!)
  window.addEventListener('contextmenu', onRightClick)
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', trackModifiers)
  // moving and releasing may happen over the HUD as well
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
  running = true
  last = performance.now()
  requestAnimationFrame(frame)
})

let unlinkAgent: (() => void) | undefined

onBeforeUnmount(() => {
  running = false
  unlinkAgent?.()
  resizeObserver.disconnect()
  window.removeEventListener('contextmenu', onRightClick)
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', trackModifiers)
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
  setCursor('default')
  combat?.dispose()
  harvesting?.dispose()
  repairs?.dispose()
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
