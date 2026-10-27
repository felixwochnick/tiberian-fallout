import * as THREE from 'three'
import { Cell, LEVEL_HEIGHT, type Terrain } from './terrain'

/** Shade of the ground at the foot of a cliff (in its shadow) */
const CLIFF_FOOT_SHADE = 0.62

/** Rock at least this high (levels) is a cliff: stony ground and shade round its foot */
const CLIFF_SPAN = 0.75

/** How rocky (the shader's broken rock of a slope) the terraces' slopes and the ramps look, 0 … 1 */
const SLOPE_RAMP = 0.4

/** Pieces a cell near a slope is cut into, along x and z, so the ground can be rounded and rough there */
const DETAIL = 5

/**
 * The ground's mesh: flat cells as two triangles; the cells near a cliff or a ramp cut
 * into DETAIL × DETAIL pieces on Terrain.heightAt, which rounds the folds at the top
 * and the foot of the slopes, lets their lines waver and roughens them. Only the cells
 * `include` lets in. Faceted: every triangle has its own normal (the ground shader
 * lights and colours by it). Per corner, the attribute `shade` darkens the ground at
 * the foot of the cliffs, and `rock` says how much of the ground there is rock: 1 at
 * the corners of rock cells, so the stony ground of a cliff runs out over the flat
 * cells next to it (on top of a plateau and at its foot); `ramp` likewise is SLOPE_RAMP at the
 * corners of the ramps' cells and of the terraces' slopes. Inside a cell they are
 * blended between its corners.
 */
export function terrainGeometry(terrain: Terrain, include: (x: number, z: number) => boolean) {
  const positions: number[] = []
  const shades: number[] = []
  const rocks: number[] = []
  const ramps: number[] = []
  const around = (px: number, pz: number) => [[px - 1, pz - 1], [px, pz - 1], [px - 1, pz], [px, pz]] as const
  /** A cliff: rock at least CLIFF_SPAN high (the low rock beside the foot of a ramp looks like a slope) */
  const cliff = (x: number, z: number) => {
    if (terrain.cell(x, z) !== Cell.Rock) return false
    const levels = terrain.corners(x, z)
    return Math.max(...levels) - Math.min(...levels) >= CLIFF_SPAN
  }
  /** Whether a corner is on a ramp: it stays open ground, though the rock of the ramp's sides touches it */
  const onRamp = (px: number, pz: number) => around(px, pz).some(([x, z]) => terrain.cell(x, z) === Cell.Ramp)
  const cornerShade = (px: number, pz: number) => {
    const here = terrain.corner(px, pz)
    return !onRamp(px, pz) && around(px, pz).some(([x, z]) => cliff(x, z) && Math.max(...terrain.corners(x, z)) > here)
      ? CLIFF_FOOT_SHADE
      : 1
  }
  const cornerRock = (px: number, pz: number) => !onRamp(px, pz) && around(px, pz).some(([x, z]) => cliff(x, z)) ? 1 : 0
  const cornerRamp = (px: number, pz: number) =>
    // the ramps are steps like the terraces' slopes, and look like them; so does the low rock beside them
    around(px, pz).some(([x, z]) => {
      const cell = terrain.cell(x, z)
      return cell === Cell.Ramp || cell === Cell.Slope || (cell === Cell.Rock && !cliff(x, z))
    })
      ? SLOPE_RAMP
      : 0
  /** Whether a cell and its eight neighbours are flat on one level */
  const plain = (x: number, z: number) => {
    const level = terrain.corner(x, z)
    for (let j = z - 1; j <= z + 1; j++) {
      for (let i = x - 1; i <= x + 1; i++) {
        if (terrain.cell(i, j) !== Cell.Flat || terrain.corner(i, j) !== level) return false
      }
    }
    return true
  }
  const { x0, z0, width, depth } = terrain
  for (let z = z0 - 1; z <= z0 + depth; z++) {
    for (let x = x0 - 1; x <= x0 + width; x++) {
      if (!include(x, z)) continue
      const corners = [[x, z], [x + 1, z], [x, z + 1], [x + 1, z + 1]] as const
      const shade = corners.map(([px, pz]) => cornerShade(px, pz))
      const rock = corners.map(([px, pz]) => cornerRock(px, pz))
      const ramp = corners.map(([px, pz]) => cornerRamp(px, pz))
      const blend = (v: number[], fx: number, fz: number) =>
        (v[0]! * (1 - fx) + v[1]! * fx) * (1 - fz) + (v[2]! * (1 - fx) + v[3]! * fx) * fz
      const n = plain(x, z) ? 1 : DETAIL
      const level = terrain.corner(x, z) * LEVEL_HEIGHT
      const point = (i: number, j: number) => {
        const fx = i / n
        const fz = j / n
        return [x + fx, n === 1 ? level : terrain.heightAt(x + fx, z + fz), z + fz, fx, fz] as const
      }
      const grid = Array.from({ length: (n + 1) * (n + 1) }, (_, k) => point(k % (n + 1), Math.floor(k / (n + 1))))
      const at = (i: number, j: number) => grid[j * (n + 1) + i]!
      for (let j = 0; j < n; j++) {
        for (let i = 0; i < n; i++) {
          const p00 = at(i, j)
          const p10 = at(i + 1, j)
          const p01 = at(i, j + 1)
          const p11 = at(i + 1, j + 1)
          // the diagonal along the smaller difference in height, so folds stay folds
          const triangles = Math.abs(p00[1] - p11[1]) < Math.abs(p10[1] - p01[1])
            ? [[p00, p01, p11], [p00, p11, p10]]
            : [[p00, p01, p10], [p10, p01, p11]]
          for (const triangle of triangles) {
            for (const [px, py, pz, fx, fz] of triangle) {
              positions.push(px, py, pz)
              shades.push(blend(shade, fx, fz))
              rocks.push(blend(rock, fx, fz))
              ramps.push(blend(ramp, fx, fz))
            }
          }
        }
      }
    }
  }
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geometry.setAttribute('shade', new THREE.Float32BufferAttribute(shades, 1))
  geometry.setAttribute('rock', new THREE.Float32BufferAttribute(rocks, 1))
  geometry.setAttribute('ramp', new THREE.Float32BufferAttribute(ramps, 1))
  geometry.computeVertexNormals()
  return geometry
}
