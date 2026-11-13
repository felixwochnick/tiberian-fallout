<script setup lang="ts">
import { createSkirmish } from '~/composables/useSkirmish'
import type { Field } from '~/lib/game/field'
import { MODELS } from '~/lib/game/models'
import type * as THREE from 'three'
import type { FlatZone } from '~/lib/game/terrain'
import { tiberiumField } from '~/lib/game/tiberium'

/**
 * Gefecht: a free game against the computer players of the skirmish dialog. Every
 * player starts with nothing but an MCV; the base has to be built from there.
 */
// skirmishes only while developing: otherwise back to the main menu
if (!import.meta.dev) navigateTo('/menu', { replace: true })
useHead({ title: 'Tiberian Fallout – Gefecht' })

const settings = useSettings()
const skirmish = createSkirmish(settings.credits, (settings.players.find(p => p.ai === null) ?? settings.players[0])?.side)
const control = useBattleControl(skirmish)
const session = ref<{ restart: () => void }>()

/** The players of the skirmish dialog: the human player and the computer players */
const human = computed(() => settings.players.find(p => p.ai === null) ?? settings.players[0])
const houseColour = (player?: SkirmishPlayer) => HOUSE_COLOURS[player?.colour ?? 0]?.[1] ?? 0xd8b43a

/**
 * Where the computer players start, as fractions of the map along the screen axes:
 * the corners first, then the middles of the edges (the player is in the middle).
 */
const START_SPOTS: [number, number][] = [
  [0.2, 0.2], [0.8, 0.8], [0.8, 0.2], [0.2, 0.8], [0.5, 0.15], [0.5, 0.85], [0.15, 0.5],
]

/** Where the Tiberium field lies: a few cells to the lower right of the player's start (screen axes) */
const TIBERIUM_OFFSET: [number, number] = [6, 5]
/** Its size: cells from the middle to the edge */
const TIBERIUM_RADIUS = 4
/** A smaller field of blue Tiberium a little farther, on the other side (screen axes) */
const BLUE_TIBERIUM_OFFSET: [number, number] = [-7, 8]
const BLUE_TIBERIUM_RADIUS = 2.5
/**
 * Small, young fields elsewhere, each round a Tiberium tree that makes it grow (as
 * fractions of the map along the screen axes, away from the starts)
 */
const TREE_FIELDS: [number, number][] = [[0.33, 0.64], [0.67, 0.36]]
const TREE_FIELD_RADIUS = 1.5

/** A fresh map: a Tiberium field near the player, one MCV for each player, then battle control */
function start({ battlefield, addUnit }: Field) {
  const [mapW, mapH] = battlefield.mapSize
  const field = battlefield.mapPoint(mapW / 2 + TIBERIUM_OFFSET[0], mapH / 2 + TIBERIUM_OFFSET[1])
  const blueField = battlefield.mapPoint(mapW / 2 + BLUE_TIBERIUM_OFFSET[0], mapH / 2 + BLUE_TIBERIUM_OFFSET[1])
  const spots = settings.players.filter(p => p.ai !== null).map((_, i) => {
    const [fu, fv] = START_SPOTS[i % START_SPOTS.length]!
    return battlefield.mapPoint(fu * mapW, fv * mapH).round()
  })
  const treeFields = TREE_FIELDS.map(([fu, fv]) => battlefield.mapPoint(fu * mapW, fv * mapH))
  // a new landscape every game; level round every start and the Tiberium fields
  const around = (at: THREE.Vector3, r: number): FlatZone => ({ x: Math.floor(at.x) - r, z: Math.floor(at.z) - r, w: 2 * r + 1, h: 2 * r + 1 })
  const theater = settings.theater === 'random' ? (Math.random() < 0.5 ? 'temperate' : 'snow') : settings.theater
  battlefield.shapeTerrain({
    seed: Math.floor(Math.random() * 2 ** 31),
    theater,
    flat: [around(battlefield.centre, 6), ...spots.map(spot => around(spot, 6)),
      around(field, TIBERIUM_RADIUS + 1), around(blueField, Math.ceil(BLUE_TIBERIUM_RADIUS) + 1),
      ...treeFields.map(at => around(at, Math.ceil(TREE_FIELD_RADIUS) + 1))],
  })
  const cell = (at: THREE.Vector3): [number, number] => [Math.floor(at.x), Math.floor(at.z)]
  battlefield.addTiberium(MODELS.TIB!, [
    ...tiberiumField(...cell(field), TIBERIUM_RADIUS),
    ...tiberiumField(...cell(blueField), BLUE_TIBERIUM_RADIUS, 'blue'),
    ...treeFields.flatMap(at => tiberiumField(...cell(at), TREE_FIELD_RADIUS).map(c => ({ ...c, stage: 1 }))),
  ]).catch(error => console.error('Tiberium konnte nicht geladen werden', error))
  // the green fields grow round their Tiberium trees, like the original's (the blue one has none)
  battlefield.addTiberiumTrees(MODELS.TIBTRE!, [cell(field), ...treeFields.map(cell)])
    .catch(error => console.error('Tiberium-Bäume konnten nicht geladen werden', error))
  addUnit('MCV', battlefield.centre.clone().round(), houseColour(human.value), 'player', human.value?.side)
    .catch(error => console.error('MCV konnte nicht geladen werden', error))
  settings.players.filter(p => p.ai !== null).forEach((player, i) => {
    const spot = spots[i]!
    addUnit('MCV', spot, houseColour(player), 'enemy', player.side)
      .then((mcv) => { mcv.userData.player = player.name })
      .catch(error => console.error('MCV konnte nicht geladen werden', error))
  })
  control.establish()
}
</script>

<template>
  <GameSession
    ref="session"
    :start-credits="settings.credits"
    :tech-level="settings.techLevel"
    :radar-always="settings.radarAlways"
    :colour="houseColour(human)"
    :side="human?.side"
    @start="start"
    @restart="session?.restart()"
  />
</template>
