<script setup lang="ts">
import * as THREE from 'three'
import { Battlefield } from '~/lib/game/battlefield'
import { findMission, type Mission, type MissionResult } from '~/lib/game/campaigns'
import { createSkirmish } from '~/composables/useSkirmish'
import type { Field } from '~/lib/game/field'
import { MODELS } from '~/lib/game/models'
import { readMovie } from '~/lib/game/movies'
import { tiberiumField } from '~/lib/game/tiberium'
import type { FlatZone } from '~/lib/game/terrain'
import type { Unit } from '~/lib/game/unit'
import { getAssetStore } from '~/lib/storage/asset-store'

/**
 * A campaign mission (`?mission=demo-1`): briefing (here, or on its own page /briefing
 * for a mission with the map selection), the mission's base and reinforcements, its
 * objectives, and the result at the end.
 */
const found = findMission(String(useRoute().query.mission ?? ''))
const mission = found?.mission
if (!mission) navigateTo('/menu', { replace: true })
useHead({ title: mission ? `Tiberian Fallout – ${mission.title}` : 'Tiberian Fallout – Mission' })

const skirmish = createSkirmish(mission?.credits ?? 0)
const control = useBattleControl(skirmish)
const sounds = useUiSounds()
const session = ref<{ restart: () => void }>()

/** A mission with the map selection has its briefing on its own page (/briefing) */
const briefingHere = !!mission && !mission.map
/** Briefing first (unless it had its own page), the result at the end; the game waits meanwhile */
const screen = ref<'briefing' | 'won' | 'lost' | undefined>(briefingHere ? 'briefing' : undefined)

/** The battlefield of this round */
let field: Field | undefined
/** The running mission's check (won, lost or still going) */
let checkMission: ((seconds: number) => MissionResult) | undefined
let finished = false

/** A fresh map: the mission's base and its enemies; it begins after the briefing */
function start(fresh: Field) {
  if (!mission) return
  field = fresh
  const [cx, cz] = [Math.round(fresh.battlefield.centre.x), Math.round(fresh.battlefield.centre.z)]
  fresh.battlefield.shapeTerrain({ seed: seedOf(mission.id), flat: flatZones(mission, cx, cz) })
  for (const [id, dx, dz] of mission.base) fresh.buildStructure(id, cx + dx, cz + dz, false)
  for (const { at: [dx, dz], radius } of mission.tiberium ?? []) {
    fresh.battlefield.addTiberium(MODELS.TIB!, tiberiumField(cx + dx, cz + dz, radius))
      .catch(error => console.error('Tiberium konnte nicht geladen werden', error))
  }
  finished = false
  checkMission = mission.start(missionContext(fresh))
  if (screen.value !== 'briefing') begin()
}

/** The same map every time for a mission: its terrain's seed from its id */
function seedOf(id: string) {
  let seed = 7
  for (const char of id) seed = (seed * 31 + char.charCodeAt(0)) >>> 0
  return seed
}

/**
 * Where the ground stays level (cells): the base with room round it (or, without one,
 * room for the construction yard), the Tiberium fields and where the dropships land
 */
function flatZones(mission: Mission, cx: number, cz: number): FlatZone[] {
  const base = mission.base.length ? mission.base : [['', -2, -2] as const, ['', 2, 2] as const]
  const xs = base.map(([, dx]) => cx + dx)
  const zs = base.map(([, , dz]) => cz + dz)
  const zones: FlatZone[] = [{ x: Math.min(...xs) - 2, z: Math.min(...zs) - 2, w: Math.max(...xs) - Math.min(...xs) + 7, h: Math.max(...zs) - Math.min(...zs) + 7 }]
  for (const { at: [dx, dz], radius } of mission.tiberium ?? []) {
    const r = Math.ceil(radius) + 1
    zones.push({ x: cx + dx - r, z: cz + dz - r, w: 2 * r + 1, h: 2 * r + 1 })
  }
  for (const { at: [dx, dz] } of mission.reinforcements ?? []) zones.push({ x: Math.floor(cx + dx) - 2, z: Math.floor(cz + dz) - 2, w: 5, h: 5 })
  return zones
}

/** Where a dropship lands: `at` (cells) from the middle of the base */
const landingSpot = (on: Field, [dx, dz]: [number, number]) => on.battlefield.centre.clone().round().add(new THREE.Vector3(dx, 0, dz))

/**
 * The mission begins: first the reinforcements fly in, one dropship after the other
 * (the next sets off when the one before is down) or all together, then battle control
 */
async function begin() {
  const mine = field
  // EVA says at once that battle control is being handed over; it comes after the landing
  control.drop(true)
  if (mine) {
    const flights: Promise<void>[] = []
    for (const { units, at } of mission?.reinforcements ?? []) {
      let landed!: () => void
      const down = new Promise<void>((resolve) => {
        landed = resolve
      })
      const flight = mine.dropship(units, landingSpot(mine, at), landed)
        .catch(error => console.error('Dropship konnte nicht geladen werden', error))
      flights.push(flight)
      if (!mission?.dropshipsTogether) await Promise.race([down, flight])
      if (mine !== field) return
    }
    await Promise.all(flights)
  }
  // not if the round was restarted meanwhile
  if (mine === field && !screen.value) control.establish()
}

watch(screen, (now, before) => {
  if (before === 'briefing' && !now) begin()
  if (now === 'briefing') control.drop()
})

function onTick(seconds: number) {
  if (!checkMission || finished) return
  const result = checkMission(seconds)
  if (result) {
    finished = true
    screen.value = result
  }
}

/** Again from the start: briefing first, if it is shown here */
function retry() {
  screen.value = briefingHere ? 'briefing' : undefined
  session.value?.restart()
}

function leave() {
  useState('westwood-logo-seen').value = true
  useState('menu-assembled').value = true
  navigateTo('/menu')
}

const NOD_RED = HOUSE_COLOURS[1][1]

/** What the mission can do on the battlefield */
function missionContext({ battlefield, combat, addUnit }: Field): Parameters<Mission['start']>[0] {
  const base = battlefield.centre.clone()
  const alive = (object: THREE.Object3D) => !object.userData.dead
  return {
    base,
    async spawnEnemy(id, dx, dz) {
      // not on a cliff or under a building: the vehicles need room as well
      const at = battlefield.openSpot(base.clone().add(new THREE.Vector3(dx, 0, dz)))
      const object = await addUnit(id, at, NOD_RED, 'enemy', 'nod')
      const towards = base.clone().sub(at)
      object.rotation.y = Math.atan2(towards.x, towards.z)
      return object
    },
    digIn(object) {
      const unit = object.userData.unit as Unit | undefined
      if (unit && Battlefield.digsIn(object)) battlefield.toggleDigIn(unit)
    },
    load(transport, soldiers) {
      battlefield.load(transport, soldiers.map(object => object.userData.unit as Unit).filter(Boolean))
    },
    burrow(transport) {
      const unit = transport.userData.unit as Unit | undefined
      if (unit) battlefield.startUnderground(unit)
    },
    tunnelIn(transport, [dx, dz], [ax, az]) {
      const unit = transport.userData.unit as Unit | undefined
      if (!unit || !alive(transport)) return
      const target = base.clone().add(new THREE.Vector3(ax, 0, az))
      battlefield.deliver(transport, (soldiers) => {
        combat.attackMove(soldiers.map(soldier => soldier.object), target)
        // and off again under the ground
        battlefield.vanish(unit)
      })
      battlefield.walk(unit, base.clone().add(new THREE.Vector3(dx, 0, dz)))
    },
    attackMove(objects, dx, dz) {
      const to = base.clone().add(new THREE.Vector3(dx, 0, dz))
      // those in a transport ride along (they are off the map meanwhile)
      const out = objects.filter(object => alive(object) && object.parent)
      combat.attackMove(out, to)
      // a transport lets its soldiers out where it gets to, and they attack on
      for (const transport of out.filter(object => Battlefield.passengers(object).length)) {
        battlefield.deliver(transport, (soldiers) => {
          combat.attackMove(soldiers.map(unit => unit.object), to)
          // and off again under the ground
          battlefield.vanish(transport.userData.unit as Unit)
        })
      }
    },
    speak: message => sounds.speak(message),
    units() {
      const all = battlefield.units.map(u => u.object).filter(alive)
      return { own: all.filter(Battlefield.own), enemy: all.filter(o => !Battlefield.own(o)) }
    },
    hint(text, seconds) {
      showHint(skirmish, text, seconds)
      sounds.play('message')
    },
    startTimer(seconds, onEnd) {
      skirmish.timer = { remaining: seconds, running: true, onEnd }
    },
    async playRadar(name) {
      const bytes = await getAssetStore().then(store => readMovie(store, name)).catch(() => undefined)
      if (!bytes) return
      // one transmission at a time: a new one waits for the last
      while (skirmish.radarMovie) await new Promise(resolve => setTimeout(resolve, 250))
      await sounds.speakNow('evaIncomingTransmission')
      await new Promise<void>((resolve) => {
        skirmish.radarMovie = markRaw({ bytes, done: resolve })
      })
    },
    stopTimer() {
      if (!skirmish.timer) return
      skirmish.timer = undefined
      sounds.speak('evaTimerStopped')
    },
    canReinforce() {
      // a construction yard can still put up a barracks
      if (skirmish.buildings.includes('GACNST')) return true
      const cheapest = Math.min(...['E1', 'E2'].map(id => skirmish.rules?.info.get(id)?.cost ?? 120))
      return skirmish.production.units.length > 0 || skirmish.arrivals.length > 0
        || (skirmish.buildings.includes('GAPILE') && skirmish.credits.value >= cheapest)
    },
    owns: id => skirmish.buildings.includes(id),
  }
}
</script>

<template>
  <GameSession
    v-if="mission"
    ref="session"
    :start-credits="mission.credits"
    :tech-level="mission.techLevel ?? 10"
    :radar-always="!!mission.radar"
    :blocked="!!screen"
    :theme="screen === 'briefing' ? 'MAPS' : undefined"
    @start="start"
    @tick="onTick"
    @restart="retry()"
  >
    <MissionScreen
      v-if="screen"
      :key="screen"
      :mission="mission"
      :result="screen === 'briefing' ? undefined : screen"
      @start="screen = undefined"
      @retry="retry()"
      @leave="leave()"
    />
  </GameSession>
</template>
