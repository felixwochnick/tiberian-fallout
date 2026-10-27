"""
Tiberian Fallout – GDI component tower (GACTWR), after Tiberian Sun.

The empty tower on one cell: an octagonal, slightly tapering block in the desert
camouflage on a dark footing, with four grey buttresses on its diagonal faces and an
armoured hatch at the front. On top a steel collar, a ring in the house colour and a
round mounting plate with four holes. The plate's top is the empty node TowerSlot1,
where the game mounts a weapon (GAVULC, GACSAM: their origin is the middle of their
foot, see GAVULC.py).

Materials as for the barracks (see GAPILE.py): Camo_* is the baked desert camouflage,
Remap the house colour, Lamp* emissive, Glow* additive halos.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 1.6 s: the footing spreads, the tower rises out of the ground,
             the buttresses come out, the collar, ring and plate come up, the lamp
             comes on
    Idle     loop, 2 s: the lamps above the hatch blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GACTWR.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). Origin in the
middle of the cell on the ground.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import GAPOWR as plant  # noqa: E402 – lathe() and the plate materials of the turbine places

kit.COLLECTION = 'GDIComponentTower'  # after importing GAPOWR, which sets its own
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GACTWR.glb')
BLEND = os.path.join(HERE, 'GACTWR.blend')

BUILD_END = 48
FOOTING = 0.03
BODY_TOP = 0.40         # top of the camouflaged block
SLOT_TOP = 0.53         # top of the mounting plate: TowerSlot1
# the block's octagonal profile: (radius to the corners, height)
BODY = ((0.34, 0.0), (0.34, 0.04), (0.29, BODY_TOP))
OCT = math.pi / 8       # turns the octagon so that its flat faces look along the axes

box, cylinder, sphere, beam, srgb = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb


def body_radius(z):
    """Radius (to the corners) of the block at height z above the footing."""
    for (r0, z0), (r1, z1) in zip(BODY, BODY[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return BODY[-1][0]


def octagon(name, mat, profile, z, bevel=0.0):
    obj = plant.lathe(name, mat, profile, (0, 0, z), 8, bevel)
    obj.rotation_euler = (0, 0, OCT)
    return obj


def block(m, root):
    """The camouflaged octagonal block (one material, so it can be baked)."""
    obj = octagon('Block', m['sand'], BODY, FOOTING, 0.008)
    obj = kit.merge('Block', [obj])
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material('Camo_Block', root))
    return obj


def trim(m):
    """Plating on the block: a band in the house colour, seams, the hatch."""
    parts = []
    flat = math.cos(OCT)  # corner radius to face distance
    # the armoured hatch on the front face, with a frame and a handle
    face = body_radius(0.14) * flat
    slope = math.atan2(BODY[1][0] - BODY[2][0], BODY[2][1] - BODY[1][1])
    parts += [
        box('HatchFrame', m['steel'], (0.17, 0.03, 0.21), (0, -face + 0.004, FOOTING + 0.14), bevel=0.006, rotation=(-slope, 0, 0)),
        box('Hatch', m['dark'], (0.13, 0.03, 0.17), (0, -face - 0.004, FOOTING + 0.135), bevel=0.004, rotation=(-slope, 0, 0)),
        box('HatchBar', m['steel_light'], (0.1, 0.02, 0.016), (0, -face - 0.012, FOOTING + 0.15), bevel=0.003, rotation=(-slope, 0, 0)),
        box('HatchStep', m['concrete_dark'], (0.2, 0.08, 0.025), (0, -face - 0.05, FOOTING + 0.0125), bevel=0.004),
    ]
    # a groove round the block under its top edge
    for k in range(8):
        a = 2 * math.pi * k / 8
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-d.y, d.x, 0))
        z = FOOTING + BODY_TOP - 0.045
        r = body_radius(BODY_TOP - 0.045) * flat + 0.002
        width = 2 * r * math.tan(OCT) + 0.004
        parts.append(beam(f'Groove{k}', m['concrete_dark'], d * r + side * width / 2 + Vector((0, 0, z)),
                          d * r - side * width / 2 + Vector((0, 0, z)), 0.012, 0.01))
    return kit.merge('Trim', parts)


def buttress(m, k):
    """A grey buttress leaning against one of the diagonal faces; origin at its foot."""
    a = math.pi / 4 + math.pi / 2 * k
    d = Vector((math.cos(a), math.sin(a), 0))
    side = Vector((-d.y, d.x, 0))
    flat = math.cos(OCT)
    height = 0.27
    inner0 = body_radius(0) * flat - 0.01           # against the face, at the bottom …
    inner1 = body_radius(height) * flat - 0.01      # … and at the top
    corners = []
    for z, r_in, r_out, w in ((0, inner0, inner0 + 0.13, 0.075), (height, inner1, inner1 + 0.035, 0.04)):
        for r, s in ((r_in, -1), (r_out, -1), (r_out, 1), (r_in, 1)):
            corners.append(tuple(d * r + side * w * s + Vector((0, 0, FOOTING + z))))
    shell = kit.hexahedron(f'Buttress{k}', m['steel_light'], corners, 0.01)
    mid = d * (inner0 + inner1 + 0.08) / 2 + Vector((0, 0, FOOTING + height / 2))
    normal = Vector((0.13 - 0.035, 0, height)).normalized()  # (outward, up) of the sloped face
    bolt = cylinder(f'ButtressBolt{k}', m['steel'], 0.018, 0.012, mid + d * 0.01, segments=8, bevel=0)
    bolt.rotation_mode = 'QUATERNION'
    bolt.rotation_quaternion = (d * normal.z + Vector((0, 0, normal.x))).to_track_quat('Z', 'Y')
    foot = d * (inner0 + 0.06) + Vector((0, 0, FOOTING))
    return kit.merge(f'Buttress{k}', [shell, bolt], foot)


def crown(m):
    """Collar, house-colour ring and the mounting plate with four holes."""
    z = FOOTING + BODY_TOP
    parts = [
        octagon('Collar', m['steel'], ((0.3, 0), (0.3, 0.02)), z, 0.004),
        octagon('Ring', m['remap'], ((0.275, 0), (0.29, 0.01), (0.29, 0.022), (0.27, 0.03)), z + 0.02, 0),
        cylinder('PlateFoot', m['steel'], 0.2, 0.02, (0, 0, z + 0.06), segments=32, bevel=0.003),
        cylinder('Plate', m['plate'], 0.22, 0.03, (0, 0, SLOT_TOP - 0.015), segments=32, bevel=0.005),
        cylinder('PlateDeck', m['pod_dark'], 0.07, 0.004, (0, 0, SLOT_TOP + 0.001), segments=32, bevel=0),
    ]
    for k in range(4):
        a = math.pi / 4 + math.pi / 2 * k
        p = Vector((math.cos(a), math.sin(a), 0)) * plant.HOLE_RADIUS + Vector((0, 0, SLOT_TOP))
        parts += [
            cylinder(f'HoleRim{k}', m['steel'], 0.04, 0.01, p + Vector((0, 0, 0.002)), segments=16, bevel=0.002),
            cylinder(f'Hole{k}', m['dark'], 0.028, 0.004, p + Vector((0, 0, 0.0065)), segments=16, bevel=0),
        ]
    return kit.merge('Crown', parts, (0, 0, z))


def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = BUILD_END + 12
    scene.frame_current = BUILD_END

    m = plant.materials()
    m['plate'] = kit.material('TowerPlate', srgb('#8e8aa6'), 0.5, 0.4)
    root = kit.empty('GDIComponentTower')
    keys = kit.keys

    # ---- the footing spreads
    feet = [octagon('Footing', m['concrete_dark'], ((0.43, 0), (0.43, FOOTING * 0.6), (0.41, FOOTING)), 0, 0.004)]
    feet.append(octagon('FootingEdge', m['steel'], ((0.44, 0), (0.44, 0.012)), 0, 0))
    footing = kit.parent(kit.merge('Footing', feet), root)
    keys(footing, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 10: Vector((1.03, 1.03, 1)), 13: Vector((1, 1, 1))})

    # ---- the tower rises out of the ground
    tower = kit.parent(kit.empty('TowerGroup'), root)
    for obj in (block(m, root), trim(m)):
        kit.parent(obj, tower)
    keys(tower, 'location', {0: Vector((0, 0, -0.42)), 6: Vector((0, 0, -0.42)), 26: Vector((0, 0, 0.01)), 29: Vector((0, 0, 0))})

    # ---- the buttresses swing out against it
    for k in range(4):
        b = kit.parent(buttress(m, k), tower)
        kit.pop(b, 24 + k * 2, 6)

    # ---- collar, ring and plate; the weapon's place on top
    top = kit.parent(crown(m), tower)
    slot = kit.empty('TowerSlot1', (0, 0, SLOT_TOP))
    slot.empty_display_size = 0.15
    kit.parent(slot, top)
    keys(top, 'scale', {0: Vector((1, 1, 1)) * kit.HIDDEN, 28: Vector((1, 1, 1)) * kit.HIDDEN, 36: Vector((1.08, 1.08, 1.08)), 40: Vector((1, 1, 1))})

    # ---- two lamps above the hatch, blinking in turn
    lights = []
    flat = math.cos(OCT)
    for i, x in enumerate((-0.06, 0.06)):
        z = FOOTING + 0.3
        p = Vector((x, -body_radius(0.3) * flat - 0.012, z))
        housing, light = kit.beacon(f'Lamp{i}', m, p, 'amber')
        housing = kit.parent(kit.merge(f'Lamp{i}', [housing], p), tower)
        kit.parent(light, housing)
        kit.pop(housing, 38 + i * 3, 5)
        lights.append((light, kit.flashes((i * 30, 12))))

    # ---- clips
    for obj in kit.collection().objects:
        if obj.animation_data and obj.animation_data.action:
            kit.to_track(obj, 'Build')
    for light, pattern in lights:
        kit.blink(light, pattern)
        kit.to_track(light, 'Idle')
    return len(kit.collection().objects)


def preview(frames, out_dir, ortho=1.7, target=(0, 0, 0.25)):
    """kit.render_preview with the camera closer in (small buildings)."""
    kit.render_preview([], out_dir)
    cam = bpy.data.objects['PreviewCamera']
    cam.data.ortho_scale = ortho
    direction = cam.rotation_euler.to_quaternion() @ Vector((0, 0, 1))
    cam.location = Vector(target) + direction * 10
    kit.render_preview(frames, out_dir)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    kit.bake_camo(512)
    bpy.context.scene.frame_set(BUILD_END)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2])


if __name__ == '__main__' and bpy.app.background:
    main()
