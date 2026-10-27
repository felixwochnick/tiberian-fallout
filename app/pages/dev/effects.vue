<script setup lang="ts">
import * as THREE from 'three'
import { Battlefield } from '~/lib/game/battlefield'
import type { BuildInfo, Weapon } from '~/lib/game/cameos'
import { Combat } from '~/lib/game/combat'
import { Harvesting } from '~/lib/game/harvesting'
import { MODELS, type Side } from '~/lib/game/models'
import { tiberiumField } from '~/lib/game/tiberium'

/**
 * Dev only: the battlefield's effects without the game data, over and over – a
 * refinery with its harvester at work in a Tiberium field, soldiers and walkers of both
 * sides shooting at each other (made-up weapons: rifle, grenades, rockets, gatlings,
 * cannon), a dropship landing and taking off, explosions.
 */
if (!import.meta.dev) navigateTo('/', { replace: true })
useHead({ title: 'Tiberian Fallout – Effekte (Dev)' })

const stage = ref<HTMLDivElement>()
const credits = ref(0)
let battlefield: Battlefield | undefined
let combat: Combat | undefined
let harvesting: Harvesting | undefined
let running = false

const weapon = (name: string, damage: number, rof: number, range: number, extra: Partial<Weapon> = {}): Weapon =>
  ({ name, damage, rof, range, verses: [1, 1, 1, 1, 1], reports: [], impactReports: [], wall: false, speed: 5, spread: 0, percentAtMax: 1, ...extra })
/** Made-up values, the game data are not needed here; they hardly hurt, so the show goes on */
const WEAPONS: Record<string, Weapon> = {
  E1: weapon('Rifle', 0.5, 12, 4),
  E2: weapon('Grenade', 1, 40, 4, { projectile: { arcing: true, homing: false }, speed: 4, spread: 0.4, percentAtMax: 0.5 }),
  E3: weapon('Rocket', 1, 45, 5, { projectile: { arcing: false, homing: true }, speed: 4, spread: 0.3 }),
  SMECH: weapon('Gatling', 0.5, 4, 4),
  MMCH: weapon('Cannon', 60, 50, 6, { projectile: { arcing: false, homing: false }, speed: 9, spread: 0.5 }),
  BGGY: weapon('MachineGun', 0.5, 8, 4),
  BIKE: weapon('BikeRocket', 1, 45, 5, { projectile: { arcing: false, homing: true }, speed: 4, spread: 0.3 }),
  TTNK: weapon('TickCannon', 2, 50, 5, { projectile: { arcing: false, homing: false }, speed: 9, spread: 0.4 }),
}
const info = (object: THREE.Object3D): BuildInfo | undefined => {
  const id = object.userData.id as string
  return {
    id, name: id, structure: !!object.userData.footprint, cost: 0, seconds: 0, power: 0, foundation: [1, 1], adjacent: 2,
    voices: { select: [], move: [], attack: [], die: [] }, techLevel: 1, sight: 6, strength: 100000, repairable: true, sellable: true, storage: 10,
    armor: ['E1', 'E2', 'E3', 'ENGINEER'].includes(id) ? 0 : 2, weapon: WEAPONS[id],
    crusher: ['MMCH', 'HARV'].includes(id), crushable: ['E1', 'E2', 'E3', 'ENGINEER', 'GASAND'].includes(id), explosionReports: [],
  }
}

onMounted(async () => {
  const field = markRaw(new Battlefield(stage.value!, 128, 128))
  battlefield = field
  // reachable from the browser console (and automated screenshots)
  Object.assign(window, { battlefield: field, THREE })
  const centre = field.centre.clone().floor()
  field.lookAt(centre.clone().add(new THREE.Vector3(1, 0, 1)))
  combat = markRaw(new Combat(field, info, { fire() {}, die() {} }))
  Object.assign(window, { combat })
  harvesting = markRaw(new Harvesting(field, () => ({ capacity: () => 28, value: kind => kind === 'blue' ? 50 : 25, earn: (_, c) => credits.value += c })))
  running = true
  let last = performance.now()
  const frame = (now: number) => {
    if (!running) return
    const seconds = Math.min(0.1, (now - last) / 1000)
    last = now
    combat?.update(seconds, 1)
    harvesting?.update(seconds)
    field.render()
    requestAnimationFrame(frame)
  }
  requestAnimationFrame(frame)

  // the refinery with its harvester, a field beside it
  await field.addTiberium(MODELS.TIB!, tiberiumField(centre.x + 6, centre.z - 1, 2.5))
  await field.addTiberium(MODELS.TIB!, tiberiumField(centre.x + 4, centre.z - 6, 1.6, 'blue'))
  const refinery = await field.addStructure('PROC', centre.x - 2, centre.z - 2, 4, 3, MODELS.PROC)
  const { at, forward } = Harvesting.dock(refinery)
  const harvester = await field.addUnit(MODELS.HARV!, at)
  harvester.object.userData.id = 'HARV'
  harvester.object.rotation.y = Math.atan2(forward.x, forward.z)
  harvesting.add(harvester, refinery, 3.4)

  // two small squads facing each other in front of the refinery
  const squad = async (ids: string[], x: number, z: number, owner: 'player' | 'enemy', colour: number, side: Side = 'gdi') => {
    for (const [i, id] of ids.entries()) {
      const unit = await field.addUnit(MODELS[id] ?? MODELS.E1!, new THREE.Vector3(centre.x + x + (i % 3) * 0.6, 0, centre.z + z + Math.floor(i / 3) * 0.6), colour, owner, side)
      unit.object.userData.id = id
    }
  }
  await squad(['E1', 'E2', 'E3', 'ENGINEER', 'SMECH'], -3, 4.5, 'player', 0xd8b43a)
  await squad(['E1', 'E2', 'E3', 'ENGINEER', 'MMCH'], 1.5, 6.5, 'enemy', 0xc0302a, 'nod')
  // Nod's vehicles, a cell and more apart (squad() packs soldiers closer)
  for (const [i, id] of ['BGGY', 'BIKE', 'SAPC', 'TTNK'].entries()) await squad([id], 4 + (i % 2) * 1.3, 2.5 + Math.floor(i / 2) * 1.3, 'enemy', 0xc0302a, 'nod')

  // a dropship lands now and then
  const fly = async () => {
    if (!running) return
    const to = centre.clone().add(new THREE.Vector3(-4, 0, -4))
    const ship = await field.addDropship(MODELS.DSHP!, field.edgePoint(to, new THREE.Vector3(-1, 0, -1)), {
      to, leave: field.edgePoint(to, new THREE.Vector3(1, 0, -1)), unload: () => new Promise(resolve => setTimeout(resolve, 1500)),
    })
    const gone = ship.onGone
    ship.onGone = () => {
      gone?.()
      setTimeout(fly, 1000)
    }
  }
  fly()
})

onBeforeUnmount(() => {
  running = false
  combat?.dispose()
  harvesting?.dispose()
  battlefield?.dispose()
})
</script>

<template>
  <div ref="stage" class="stage" />
  <div class="credits">
    Credits aus der Ernte: {{ credits }}
  </div>
</template>

<style scoped>
.stage {
  position: fixed;
  inset: 0;
  background: #000;
}
.credits {
  position: fixed;
  left: 12px;
  top: 12px;
  color: #e9e3b8;
  font: 14px Arial, sans-serif;
  text-shadow: 0 1px 2px #000;
}
</style>
