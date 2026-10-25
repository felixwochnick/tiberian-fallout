"""
Tiberian Fallout – GDI power plant (GAPOWR), after Tiberian Sun.

The plant itself: a tall ribbed cooling tower standing in a crown of fins with the
entrance at its foot, and three empty turbine places on the other cells of the
foundation (2 × 2 cells). A place is a round platform with four holes that a power
turbine (GAPOWRUP, see GAPOWRUP.py) locks into when it is mounted later. The places
are the empty nodes TurbineSlot1 … TurbineSlot3 (in the order the game fills them:
right, front, left), at the top of their platform. Lights sit all round the tower on
four levels; each level flashes as one, the levels one after another from the bottom
up, white, the top one red. No concrete slab: the tower and the places stand on their
own dark footings, like in the original.

Materials as for the barracks (see GAPILE.py): Camo_* is the baked desert camouflage,
Remap the house colour, Lamp* emissive, Glow* additive halos.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.4 s: the footings spread, the crown rises out of the ground
             and puts up its fins, the tower rises, the turbine places come up, the
             lights come on
    Idle     loop, 2 s: the light levels flash from the bottom up (twice), the door
             lamp blinks

Run headless (builds, bakes, saves the .blend, exports the GLB):

    Blender -b --factory-startup --python blender/GAPOWR.py

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells of the
foundation are centred at (±0.5, ±0.5); seen in the game, (-0.5, 0.5) is the top one.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script

kit.COLLECTION = 'GDIPowerPlant'
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAPOWR.glb')
BLEND = os.path.join(HERE, 'GAPOWR.blend')

FOOTING = 0.03          # height of the dark footings
SLOT_TOP = 0.09         # top of a turbine place (where a turbine stands)
BUILD_END = 72
IDLE_END = kit.IDLE_END

TOWER = Vector((-0.28, 0.28, 0))
SLOT_RADIUS = 0.26
HOLE_RADIUS = 0.15      # the four holes the turbine's pegs lock into, at 45°
# right, front, left: the order the game mounts turbines in
SLOTS = (Vector((0.5, 0.5, 0)), Vector((0.5, -0.5, 0)), Vector((-0.5, -0.5, 0)))
DOOR = Vector((1, -1, 0)).normalized()   # the entrance faces the front of the screen

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'plate': material('SlotPlate', srgb('#8f9aa6'), 0.45, 0.7),
        'pod_dark': material('PodDark', srgb('#2b3036'), 0.6, 0.6),
        'glow_white': material('GlowWhite', (0, 0, 0), 1.0, emission=srgb('#fff2c8'), strength=3, alpha=0.25),
    })
    return m


def lathe(name, mat, profile, location, segments=32, bevel=0.0):
    """Surface of revolution from (radius, height) points, bottom to top, capped."""
    def build(bm):
        rings = []
        for r, z in profile:
            rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z))
                          for a in (2 * math.pi * i / segments for i in range(segments))])
        for lower, upper in zip(rings, rings[1:]):
            for i in range(segments):
                j = (i + 1) % segments
                bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
        bm.faces.new(rings[0])
        bm.faces.new(rings[-1])

    obj = kit.mesh_object(name, build)
    obj.location = location
    return kit.finish(obj, mat, bevel)


# --------------------------------------------------------------------------- parts

def footings(m):
    """Dark footings under the tower and the places, joined by walkways."""
    parts = [cylinder('TowerFooting', m['concrete_dark'], 0.47, FOOTING, TOWER + Vector((0, 0, FOOTING / 2)), segments=40, bevel=0.006)]
    for i, slot in enumerate(SLOTS):
        parts.append(cylinder(f'SlotFooting{i}', m['concrete_dark'], SLOT_RADIUS + 0.04, FOOTING, slot + Vector((0, 0, FOOTING / 2)),
                              segments=40, bevel=0.006))
        # walkway from the tower's foot to the place, with a power conduit
        way = slot - TOWER
        a = math.atan2(way.y, way.x)
        mid = TOWER + way / 2
        parts.append(box(f'Walkway{i}', m['concrete_dark'], (way.length - 0.5, 0.16, FOOTING), mid + Vector((0, 0, FOOTING / 2)),
                         bevel=0.004, rotation=(0, 0, a)))
        parts.append(box(f'Conduit{i}', m['steel'], (way.length - 0.55, 0.035, 0.03), mid + Vector((0, 0, FOOTING + 0.015)),
                         bevel=0.004, rotation=(0, 0, a)))
    return kit.merge('Footings', parts)


TOWER_BASE = 0.12       # the tower's shell starts inside the crown
TOWER_PROFILE = ((0.29, 0.0), (0.29, 0.1), (0.27, 0.45), (0.245, 0.85), (0.25, 1.05), (0.27, 1.12))


def tower_radius(height):
    """Radius of the tower shell at a height above TOWER_BASE."""
    for (r0, z0), (r1, z1) in zip(TOWER_PROFILE, TOWER_PROFILE[1:]):
        if z0 <= height <= z1:
            return r0 + (r1 - r0) * (height - z0) / (z1 - z0)
    return TOWER_PROFILE[-1][0]


def tower(m, root):
    """Cooling tower: camouflaged shell, sand ribs, house-colour bands, a dark rim."""
    base = TOWER + Vector((0, 0, TOWER_BASE))
    shell = lathe('TowerShell', m['sand'], TOWER_PROFILE, base, 32)
    shell.data.materials.clear()
    shell.data.materials.append(kit.camo_material('Camo_Tower', root))

    parts = []
    for k in range(20):
        a = 2 * math.pi * k / 20
        d = Vector((math.cos(a), math.sin(a), 0))
        for i, ((r0, z0), (r1, z1)) in enumerate(zip(TOWER_PROFILE[1:], TOWER_PROFILE[2:])):
            parts.append(beam(f'TowerRib{k}_{i}', m['sand_light'], base + d * (r0 + 0.006) + Vector((0, 0, z0)),
                              base + d * (r1 + 0.006) + Vector((0, 0, z1)), 0.02, 0.014))
    for i, z in enumerate((0.3, 0.88)):
        parts.append(cylinder(f'TowerBand{i}', m['remap'], tower_radius(z) + 0.02, 0.035, base + Vector((0, 0, z)), segments=32, bevel=0))
    parts.append(cylinder('TowerRim', m['steel'], 0.285, 0.04, base + Vector((0, 0, 1.12)), segments=32, bevel=0.006))
    parts.append(cylinder('TowerOpening', m['dark'], 0.245, 0.01, base + Vector((0, 0, 1.141)), segments=32, bevel=0))
    for i in range(4):  # grille over the opening
        a = math.pi / 4 * i
        d = Vector((math.cos(a), math.sin(a), 0)) * 0.245
        parts.append(beam(f'TowerGrille{i}', m['steel'], base + Vector((0, 0, 1.15)) - d, base + Vector((0, 0, 1.15)) + d, 0.012))
    # maintenance ladder beside the entrance
    out = DOOR.lerp(Vector((-DOOR.y, DOOR.x, 0)), 0.5).normalized()
    side = Vector((-out.y, out.x, 0))
    for s in (-1, 1):
        low = base + out * (tower_radius(0.2) + 0.03) + side * 0.03 * s + Vector((0, 0, 0.2))
        high = base + out * (tower_radius(1.05) + 0.03) + side * 0.03 * s + Vector((0, 0, 1.05))
        parts.append(beam(f'LadderRail{s}', m['steel_light'], low, high, 0.008))
    for i in range(12):
        z = 0.25 + i * 0.07
        p = base + out * (tower_radius(z) + 0.03) + Vector((0, 0, z))
        parts.append(beam(f'LadderRung{i}', m['steel_light'], p - side * 0.03, p + side * 0.03, 0.006))
    return shell, kit.merge('Tower', parts)


def crown(m):
    """The tower's foot: a dark drum in a crown of fins, the entrance towards the front."""
    door_angle = math.atan2(DOOR.y, DOOR.x)
    door = TOWER + DOOR * 0.36
    parts = [
        cylinder('CrownDrum', m['pod_dark'], 0.36, 0.2, TOWER + Vector((0, 0, FOOTING + 0.1)), segments=32, bevel=0.008),
        cylinder('CrownBand', m['remap'], 0.365, 0.025, TOWER + Vector((0, 0, FOOTING + 0.17)), segments=32, bevel=0),
        box('DoorFrame', m['steel'], (0.06, 0.17, 0.17), door + Vector((0, 0, FOOTING + 0.085)), bevel=0.006, rotation=(0, 0, door_angle)),
        box('DoorLeaf', m['dark'], (0.03, 0.12, 0.13), door + DOOR * 0.02 + Vector((0, 0, FOOTING + 0.07)), bevel=0.003, rotation=(0, 0, door_angle)),
        box('DoorHood', m['steel_light'], (0.08, 0.22, 0.016), door + DOOR * 0.02 + Vector((0, 0, FOOTING + 0.18)), bevel=0.004, rotation=(0, 0, door_angle)),
    ]
    drum = kit.merge('Crown', parts)

    fins = []
    for i in range(12):
        a = 2 * math.pi * (i + 0.5) / 12
        if abs(math.remainder(a - door_angle, 2 * math.pi)) < 0.35:
            continue  # leave the entrance free
        d = Vector((math.cos(a), math.sin(a), 0))
        foot = TOWER + d * 0.37 + Vector((0, 0, FOOTING))
        fin = box(f'Fin{i}', m['steel'], (0.03, 0.09, 0.3), foot + d * 0.03 + Vector((0, 0, 0.15)), bevel=0.004)
        fin.rotation_euler = (0, math.radians(12), a)  # leaning outwards
        fins.append(kit.merge(f'Fin{i}', [fin], foot))
    return drum, fins


def turbine_place(m, i, centre):
    """A round platform with four holes for the turbine's pegs; returns (platform, slot node)."""
    c = centre + Vector((0, 0, FOOTING))
    height = SLOT_TOP - FOOTING
    parts = [
        cylinder(f'Plate{i}', m['plate'], SLOT_RADIUS, height, c + Vector((0, 0, height / 2)), segments=40, bevel=0.008),
        cylinder(f'PlateTrim{i}', m['remap'], SLOT_RADIUS + 0.006, 0.018, c + Vector((0, 0, height - 0.025)), segments=40, bevel=0),
        cylinder(f'PlateDeck{i}', m['pod_dark'], SLOT_RADIUS - 0.04, 0.006, c + Vector((0, 0, height + 0.003)), segments=40, bevel=0),
    ]
    for k in range(4):
        a = math.pi / 4 + math.pi / 2 * k
        p = centre + Vector((math.cos(a), math.sin(a), 0)) * HOLE_RADIUS + Vector((0, 0, SLOT_TOP))
        parts += [
            cylinder(f'HoleRim{i}_{k}', m['steel'], 0.042, 0.012, p + Vector((0, 0, 0.004)), segments=16, bevel=0.002),
            cylinder(f'Hole{i}_{k}', m['dark'], 0.03, 0.004, p + Vector((0, 0, 0.0085)), segments=16, bevel=0),
        ]
    platform = kit.merge(f'Place{i}', parts, c)
    slot = kit.empty(f'TurbineSlot{i + 1}', centre + Vector((0, 0, SLOT_TOP)))
    slot.empty_display_size = 0.15
    return platform, slot


# --------------------------------------------------------------------------- model

def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = BUILD_END + 12
    scene.frame_current = BUILD_END  # parenting reads the evaluated pose: the finished plant

    m = materials()
    root = kit.empty('GDIPowerPlant')
    keys = kit.keys

    # ---- the footings spread from the tower's place
    feet = kit.parent(footings(m), root)
    keys(feet, 'scale', {0: Vector((0.05, 0.05, 1)), 3: Vector((0.05, 0.05, 1)), 14: Vector((1.02, 1.02, 1)), 17: Vector((1, 1, 1))})

    # ---- the crown rises out of the ground and puts up its fins
    crown_group = kit.parent(kit.empty('CrownGroup'), root)
    drum, fins = crown(m)
    kit.parent(drum, crown_group)
    keys(crown_group, 'location', {0: Vector((0, 0, -0.3)), 8: Vector((0, 0, -0.3)), 22: Vector((0, 0, 0.008)), 25: Vector((0, 0, 0))})
    for i, fin in enumerate(fins):
        kit.parent(fin, crown_group)
        kit.pop(fin, 20 + i * 2, 6)

    # ---- the tower rises inside it
    tower_group = kit.parent(kit.empty('TowerGroup'), root)
    for obj in tower(m, root):
        kit.parent(obj, tower_group)
    keys(tower_group, 'location', {0: Vector((0, 0, -1.3)), 16: Vector((0, 0, -1.3)), 44: Vector((0, 0, 0.015)), 48: Vector((0, 0, 0))})

    # lights all round the tower on four levels, the top one red; each level is one
    # object, so it flashes as one
    lights = []
    base = TOWER + Vector((0, 0, TOWER_BASE))
    levels = ((0.22, 'white'), (0.52, 'white'), (0.82, 'white'), (1.115, 'red'))
    for k, (height, colour) in enumerate(levels):
        housings, bulbs = [], []
        r = (tower_radius(height) if height < 1.1 else 0.285) + 0.015
        for j in range(8):
            a = 2 * math.pi * (j + 0.5 * (k % 2)) / 8
            p = base + Vector((math.cos(a) * r, math.sin(a) * r, height - 0.03))
            housing, light = kit.beacon(f'Level{k}Lamp{j}', m, p, colour)
            housings.append(housing)
            bulbs.append(light)
        centre = base + Vector((0, 0, height))
        mount = kit.parent(kit.merge(f'LightLevel{k}', housings, centre), tower_group)
        level = kit.merge(f'LightLevel{k}Glow', bulbs, centre)
        kit.parent(level, mount)
        kit.pop(mount, 48 + k * 3, 5)
        # from the bottom up, twice a loop
        lights.append((level, kit.flashes((k * 6, 4), (30 + k * 6, 4))))

    # door light
    door = TOWER + DOOR * 0.4 + Vector((0, 0, FOOTING + 0.2))
    housing, light = kit.beacon('DoorLamp', m, door, 'amber')
    housing = kit.merge('DoorLamp', [housing], door)
    kit.parent(housing, crown_group)
    kit.pop(housing, 28, 6)
    kit.parent(light, housing)
    lights.append((light, kit.flashes((0, 20), (30, 20))))

    # ---- the turbine places come up
    for i, centre in enumerate(SLOTS):
        platform, slot = turbine_place(m, i, centre)
        group = kit.parent(kit.empty(f'PlaceGroup{i}'), root)
        for obj in (platform, slot):
            kit.parent(obj, group)
        start = 30 + i * 5
        keys(group, 'location', {0: Vector((0, 0, -0.12)), start: Vector((0, 0, -0.12)), start + 10: Vector((0, 0, 0.006)), start + 13: Vector((0, 0, 0))})

    # ---- clips
    for obj in kit.collection().objects:
        if obj.animation_data and obj.animation_data.action:
            kit.to_track(obj, 'Build')
    for light, pattern in lights:
        kit.blink(light, pattern)
        kit.to_track(light, 'Idle')
    return len(kit.collection().objects)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    kit.bake_camo()
    bpy.context.scene.frame_set(BUILD_END)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        kit.render_preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2])


if __name__ == '__main__' and bpy.app.background:
    main()
