"""
Tiberian Fallout – Tiberium (Riparius), the green crystals of Tiberian Sun, on one cell.

After help/tiberium/: many small, flat, star-shaped sprigs of bright neon-green
crystal shards (lighter, glowing tips) spread over the whole cell in loose clumps, so
the cells of a field grow together; between them lie greyish-white seeds, the round
lumps a sprig grows out of next. The stained, green-lit ground round a field is not
part of the model: the game draws it into the ground (Battlefield.addTiberium).

Three growth stages, each in three variants (so a field does not look tiled; the game
also turns each cell by a multiple of 90°):

    Stage1A … Stage1C   young: a few small sprigs, many seeds
    Stage2A … Stage2C   growing: the sprigs bigger, new ones where the seeds were
    Stage3A … Stage3C   ripe: sprigs over the whole cell, the last seeds

The stages of one variant grow out of each other: every place on the cell has the stage
its sprig appears in; one stage before, a seed lies there, and from then on the sprig
gets bigger with every stage. The game shows one of the nine nodes per cell and hides
the others.

Run headless:

    Blender -b --factory-startup --python blender/TIB.py

Units: 1 = one map cell. Blender Z is up; origin in the middle of the cell on the ground.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script

kit.COLLECTION = 'Tiberium'
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'TIB.glb')
BLEND = os.path.join(HERE, 'TIB.blend')

STAGES = (1, 2, 3)
VARIANTS = 'ABC'
SITES = 4                       # places on a jittered SITES × SITES grid over the cell
BORN = [1] * 4 + [2] * 5 + [3] * 5 + [4] * 2  # stage each place's sprig appears in (4: only ever a seed)
SPRIG = 0.18                    # length of a full grown sprig's longest shard
GROWTH = (0.5, 0.8, 1.0)        # share of the full size one, two and three stages on

srgb, material = kit.srgb, kit.material
MATERIALS = ('crystal', 'deep', 'tip')


def materials():
    return {
        'crystal': material('TiberiumCrystal', srgb('#2ee63a'), 0.15, 0.05, emission=srgb('#22e030'), strength=1.6),
        'deep': material('TiberiumDeep', srgb('#14a028'), 0.2, 0.05, emission=srgb('#10b024'), strength=1.0),
        'tip': material('TiberiumTip', srgb('#78ff64'), 0.1, 0.0, emission=srgb('#6cff58'), strength=2.4),
        'seed': material('TiberiumSeed', srgb('#c9cdc0'), 0.55),
        'seed_dark': material('TiberiumSeedDark', srgb('#5e6656'), 0.8),
    }


# --------------------------------------------------------------------------- geometry

def add_shard(bm, base, direction, length, radius, twist, body, sides=5):
    """A thin shard from `base` along `direction`: the shaft in material `body` (index),
    the pointed tip glowing ('tip'). It starts a little under the ground."""
    d = direction.normalized()
    side = d.cross(Vector((0, 0, 1)))
    if side.length < 1e-4:
        side = Vector((1, 0, 0))
    side.normalize()
    up = side.cross(d)
    start = base - d * 0.015
    shaft = length * 0.8

    def ring(centre, r):
        return [bm.verts.new(centre + (side * math.cos(a) + up * math.sin(a)) * r)
                for a in (twist + 2 * math.pi * k / sides for k in range(sides))]

    bottom = ring(start, radius * 0.6)
    top = ring(start + d * shaft, radius)
    tip = bm.verts.new(start + d * (length + 0.015))
    tip_index = MATERIALS.index('tip')
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((bottom[k], bottom[j], top[j], top[k])).material_index = body
        bm.faces.new((top[k], top[j], tip)).material_index = tip_index
    bm.faces.new(list(reversed(bottom))).material_index = body


def add_seed(bm, centre, radius, rng):
    """A round, flattened lump, a little uneven."""
    result = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=radius)
    for v in result['verts']:
        v.co.z *= 0.55
        v.co *= 1 + rng.uniform(-0.12, 0.12)
        v.co += centre + Vector((0, 0, radius * 0.25))


# --------------------------------------------------------------------------- layout

def layout(seed):
    """The places of one variant on a jittered grid over the whole cell: (stage its
    sprig appears in, centre, size, shards, seed radius); a shard is (direction, share
    of the sprig's size, thickness, twist, material index)."""
    rng = random.Random(seed)
    places = []
    step = 1 / SITES
    for i in range(SITES):
        for j in range(SITES):
            places.append(Vector((-0.5 + (i + 0.5 + rng.uniform(-0.35, 0.35)) * step,
                                  -0.5 + (j + 0.5 + rng.uniform(-0.35, 0.35)) * step, 0)))
    # the first sprigs nearer the middle, so a young cell is a small clump
    places.sort(key=lambda p: p.length + rng.uniform(0, 0.4))
    sprigs = []
    for born, centre in zip(BORN, places):
        shards = []
        count = rng.randint(5, 7)
        for k in range(count):
            # a star: shards spread wide and low, one short one standing up in the middle
            a = 2 * math.pi * k / count + rng.uniform(-0.35, 0.35)
            spread = 0.2 if k == 0 else rng.uniform(1.0, 1.9)
            direction = Vector((math.cos(a) * spread, math.sin(a) * spread, 1)).normalized()
            share = 0.6 if k == 0 else rng.uniform(0.65, 1.0)
            shards.append((direction, share, rng.uniform(0.16, 0.22), rng.uniform(0, 1), rng.choice((0, 0, 1))))
        sprigs.append((born, centre, SPRIG * rng.uniform(0.75, 1.2), shards, rng.uniform(0.035, 0.05)))
    return sprigs


def stage_node(m, root, stage, variant, sprigs):
    """The node StageNV: the sprigs at their size in this stage, seeds where the next
    ones will grow."""
    name = f'Stage{stage}{variant}'
    node = kit.parent(kit.empty(name), root)

    def crystals(bm):
        for born, centre, size, shards, _ in sprigs:
            if born > stage:
                continue
            length = size * GROWTH[stage - born]
            for direction, share, thickness, twist, body in shards:
                base = centre + Vector((direction.x, direction.y, 0)) * 0.01
                add_shard(bm, base, direction, length * share, length * share * thickness, twist, body)

    obj = kit.mesh_object(f'{name}Crystals', crystals)
    for key in MATERIALS:
        obj.data.materials.append(m[key])
    for poly in obj.data.polygons:
        poly.use_smooth = False  # cut facets
    kit.parent(obj, node)

    seeds = [(centre, radius) for born, centre, _, _, radius in sprigs if born == stage + 1]
    if seeds:
        rng = random.Random(f'{name}Seeds')

        def lumps(bm):
            for centre, radius in seeds:
                add_seed(bm, centre, radius, rng)

        obj = kit.mesh_object(f'{name}Seeds', lumps)
        obj.data.materials.append(m['seed'])
        obj.data.materials.append(m['seed_dark'])
        for poly in obj.data.polygons:
            poly.material_index = 1 if poly.center.z < 0.012 else 0  # darker underneath
        kit.parent(obj, node)


def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    m = materials()
    root = kit.empty('Tiberium')
    for i, variant in enumerate(VARIANTS):
        sprigs = layout(17 + 31 * i)
        for stage in STAGES:
            stage_node(m, root, stage, variant, sprigs)
    return len(kit.collection().objects)


def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    bpy.context.scene.frame_set(0)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)


if __name__ == '__main__' and bpy.app.background:
    main()
