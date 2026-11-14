<script setup lang="ts">
import { createSkirmish } from '~/composables/useSkirmish'
import type { Field } from '~/lib/game/field'
import { MODELS } from '~/lib/game/models'
import type * as THREE from 'three'
import { type FlatZone, mulberry32 } from '~/lib/game/terrain'
import { tiberiumField } from '~/lib/game/tiberium'
import { type MapSpot, skirmishLayout, unfairness } from '~/lib/game/skirmish-map'
import { LOCAL_PLAYER, MISSION_ENEMY } from '~/lib/game/players'

/**
 * Gefecht: a free game against the computer players of the skirmish dialog. Every
 * player starts with nothing but an MCV, at a start as good as any other (see
 * skirmish-map.ts); the base has to be built from there.
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

/** Cells kept flat round each start */
const START_FLAT = 6
/** … and round the middle of the map */
const MIDDLE_FLAT = 4

/** A fresh map: the starts, the Tiberium, one MCV for each player, then battle control */
function start(fresh: Field) {
  const { battlefield, addUnit } = fresh
  const layout = skirmishLayout(settings.players.length, battlefield.mapSize)
  const point = ({ u, v }: MapSpot) => battlefield.mapPoint(u, v)
  const cell = (at: THREE.Vector3): [number, number] => [Math.floor(at.x), Math.floor(at.z)]
  const starts = layout.starts.map(spot => point(spot).round())
  const fields = layout.fields.map(f => ({ ...f, at: point(f) }))
  const centre = battlefield.centre
  // a new landscape every game, alike round the middle; flat round every start and every field
  const around = (at: THREE.Vector3, r: number): FlatZone => ({ x: Math.floor(at.x) - r, z: Math.floor(at.z) - r, w: 2 * r + 1, h: 2 * r + 1 })
  const theater = settings.theater === 'random' ? (Math.random() < 0.5 ? 'temperate' : 'snow') : settings.theater
  // each start's way to the middle, to its own fields and to the next start is about as long as the others'
  const goals = starts.map((_, i) => [
    cell(centre),
    ...fields.filter(f => f.start === i).map(f => cell(f.at)),
    cell(starts[(i + 1) % starts.length]!),
  ])
  battlefield.shapeTerrain({
    seed: Math.floor(Math.random() * 2 ** 31),
    theater,
    flat: [around(centre, MIDDLE_FLAT), ...starts.map(at => around(at, START_FLAT)),
      ...fields.map(f => around(f.at, Math.ceil(f.radius) + 1))],
    ways: layout.ways.map(spot => around(point(spot), 0)),
    symmetry: { x: centre.x, z: centre.z, order: starts.length, angle: Math.atan2(starts[0]!.z - centre.z, starts[0]!.x - centre.x) },
    judge: (terrain, onMap) => unfairness(terrain, starts.map(cell), goals, onMap),
  })
  // every start's fields look the same: the same crystals for each
  const crystals = Math.floor(Math.random() * 2 ** 31)
  battlefield.addTiberium(MODELS.TIB!, fields.flatMap(f => tiberiumField(...cell(f.at), f.radius, f.kind, mulberry32(crystals + f.radius * 10))
    .map(c => f.young ? { ...c, stage: 1 } : c)))
    .catch(error => console.error('Tiberium konnte nicht geladen werden', error))
  // the green fields grow round their Tiberium trees, like the original's
  battlefield.addTiberiumTrees(MODELS.TIBTRE!, fields.filter(f => f.tree).map(f => cell(f.at)))
    .catch(error => console.error('Tiberium-Bäume konnten nicht geladen werden', error))
  // the players get the starts at random
  const order = starts.map((_, i) => i).sort(() => Math.random() - 0.5)
  settings.players.forEach((player, i) => {
    const at = starts[order[i]!]!
    const colour = houseColour(player)
    if (player === human.value) {
      fresh.setStart(at)
      battlefield.lookAt(at)
      addUnit('MCV', at, colour, LOCAL_PLAYER, player.side)
        .catch(error => console.error('MCV konnte nicht geladen werden', error))
      return
    }
    addUnit('MCV', at, colour, MISSION_ENEMY, player.side)
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
