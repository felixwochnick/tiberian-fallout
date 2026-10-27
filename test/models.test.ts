import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * The clips of a building play at the same time: Build holds its last frame, Idle loops
 * over it, Fire/Open/Deliver run once in between. A channel (node + property) driven by
 * two of them is averaged by three.js – lamps end up at half their size, parts halfway
 * between two places. So every channel belongs to one clip only.
 */
const MODELS = join(__dirname, '..', 'public', 'models')

interface Gltf {
  nodes: { name?: string }[]
  animations?: { name: string, channels: { sampler: number, target: { node: number, path: string } }[], samplers: { output: number }[] }[]
  accessors: { bufferView: number, byteOffset?: number, count: number, type: string }[]
  bufferViews: { byteOffset?: number }[]
  /** The binary chunk */
  bin: Buffer
}

function gltf(file: string): Gltf {
  const bytes = readFileSync(join(MODELS, file))
  const length = bytes.readUInt32LE(12)
  return { ...JSON.parse(bytes.subarray(20, 20 + length).toString()), bin: bytes.subarray(20 + length + 8) }
}

/** The float values of an accessor */
function floats(model: Gltf, index: number) {
  const accessor = model.accessors[index]!
  const offset = (model.bufferViews[accessor.bufferView]!.byteOffset ?? 0) + (accessor.byteOffset ?? 0)
  const size = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 }[accessor.type] ?? 1
  return Array.from({ length: accessor.count * size }, (_, i) => model.bin.readFloatLE(offset + i * 4))
}

/** No part is ever scaled up this much: a sign of the exporter making up for a parent scaled down to nothing */
const MAX_SCALE = 20

/** Clips that play together on a building (units switch between their clips instead) */
const LAYERED = ['Build', 'Idle', 'Fire', 'Open', 'Deliver']

const buildings = readdirSync(MODELS).filter(file => file.endsWith('.glb')).filter((file) => {
  const names = (gltf(file).animations ?? []).map(a => a.name)
  return names.includes('Build')
})

describe('all models', () => {
  const all = readdirSync(MODELS).filter(file => file.endsWith('.glb'))
  it.each(all)('%s: no clip blows a part up', (file) => {
    const model = gltf(file)
    const blown: string[] = []
    for (const clip of model.animations ?? []) {
      for (const channel of clip.channels) {
        if (channel.target.path !== 'scale') continue
        const largest = Math.max(...floats(model, clip.samplers[channel.sampler]!.output).map(Math.abs))
        if (largest > MAX_SCALE) blown.push(`${clip.name} ${model.nodes[channel.target.node]?.name}: ${largest}`)
      }
    }
    expect(blown).toEqual([])
  })
})

describe('building models', () => {
  it.each(buildings)('%s: no channel is driven by two clips that play together', (file) => {
    const model = gltf(file)
    const owner = new Map<string, string>()
    const shared: string[] = []
    for (const clip of model.animations ?? []) {
      if (!LAYERED.includes(clip.name)) continue
      for (const { target } of clip.channels) {
        const key = `${model.nodes[target.node]?.name ?? target.node}:${target.path}`
        const first = owner.get(key)
        if (first && first !== clip.name) shared.push(`${key} (${first}, ${clip.name})`)
        else owner.set(key, clip.name)
      }
    }
    expect(shared).toEqual([])
  })
})
