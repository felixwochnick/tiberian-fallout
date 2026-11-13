import * as THREE from 'three'
import { expect, it } from 'vitest'
import { Unit } from '../app/lib/game/unit'

/** A one-second clip that moves the node from x 0 to 1 */
function clip(name: string) {
  return new THREE.AnimationClip(name, 1, [new THREE.NumberKeyframeTrack('.position[x]', [0, 1], [0, 1])])
}

/** At four times the game speed it walks four times as far, but its idle loop keeps its pace */
it('runs its idle loop at the ambient pace and walks at the game speed', () => {
  const object = new THREE.Object3D()
  const unit = new Unit(object, [clip('Idle'), clip('Walk')], 1)
  const idle = unit['idle']!
  // 0.1 real seconds at four times the speed: 0.4 game seconds, the idle loop scaled back to 0.1
  unit.update(0.4, 0.25)
  expect(idle.time).toBeCloseTo(0.1)

  unit.walkTo(new THREE.Vector3(0, 0, 10))
  unit.update(0.4, 0.25)
  expect(object.position.z).toBeCloseTo(0.4)
  expect(unit['walk']!.timeScale).toBe(1)
})
