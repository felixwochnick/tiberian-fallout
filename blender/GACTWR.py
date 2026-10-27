"""
Tiberian Fallout – GDI component tower (GACTWR), after Tiberian Sun.

The empty tower on one cell: an octagonal block with upright walls in the desert
camouflage on a dark footing, with four grey buttresses on its diagonal faces (the one
at the front carries a lamp). On top a thick rim in the house colour round a grey
mounting plate with four holes. The plate's top is the empty node TowerSlot1, where
the game mounts a weapon (GAVULC, GACSAM: their origin is the middle of their foot, see
GAVULC.py).

Like the wall (GAWALL.py) the tower shows wall stubs towards neighbouring walls and
gates (Battlefield.connectWalls): ArmXP, ArmXN, ArmZP, ArmZN (glTF axes), each a block
of the concrete wall from the tower's face to the joint at the cell's edge.

Materials as for the barracks (see GAPILE.py): Camo_* is the baked desert camouflage,
Remap the house colour, Lamp* emissive, Glow* additive halos.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 1.6 s: the footing spreads, the tower rises out of the ground
             with the wall stubs, the buttresses come out, rim and plate come up, the
             lamp's housing pops up
    Idle     loop, 2 s: the lamp on the front buttress blinks

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
import GAWALL as wall  # noqa: E402 – the wall stubs

kit.COLLECTION = 'GDIComponentTower'  # after importing GAPOWR, which sets its own
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GACTWR.glb')
BLEND = os.path.join(HERE, 'GACTWR.blend')

BUILD_END = 48
FOOTING = 0.03
BODY_TOP = 0.56         # top of the camouflaged block
SLOT_TOP = 0.65         # top of the mounting plate: TowerSlot1
# the block's octagonal profile: (radius to the corners, height)
BODY = ((0.47, 0.0), (0.47, 0.03), (0.46, 0.06), (0.46, BODY_TOP))
ARM_START = 0.415       # the wall stubs start just inside the tower's flat faces
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
    """A groove round the block under its top edge and a seam above its foot."""
    parts = []
    flat = math.cos(OCT)  # corner radius to face distance
    for k in range(8):
        a = 2 * math.pi * k / 8
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-d.y, d.x, 0))
        for name, h in (('Groove', BODY_TOP - 0.05), ('Seam', 0.1)):
            z = FOOTING + h
            r = body_radius(h) * flat + 0.002
            width = 2 * r * math.tan(OCT) + 0.004
            parts.append(beam(f'{name}{k}', m['concrete_dark'], d * r + side * width / 2 + Vector((0, 0, z)),
                              d * r - side * width / 2 + Vector((0, 0, z)), 0.012, 0.01))
    return kit.merge('Trim', parts)


def buttress(m, k):
    """A grey buttress leaning against one of the diagonal faces, with a dark recess
    down its middle; origin at its foot. It stays clear of the wall stubs on the flat
    faces next to it."""
    a = math.pi / 4 + math.pi / 2 * k
    d = Vector((math.cos(a), math.sin(a), 0))
    side = Vector((-d.y, d.x, 0))
    flat = math.cos(OCT)
    height = 0.42
    inner0 = body_radius(0.06) * flat - 0.01        # against the face, at the bottom …
    inner1 = body_radius(height) * flat - 0.01      # … and at the top
    corners = []
    for z, r_in, r_out, w in ((0, inner0, inner0 + 0.105, 0.09), (height, inner1, inner1 + 0.035, 0.06)):
        for r, s in ((r_in, -1), (r_out, -1), (r_out, 1), (r_in, 1)):
            corners.append(tuple(d * r + side * w * s + Vector((0, 0, FOOTING + z))))
    shell = kit.hexahedron(f'Buttress{k}', m['steel_light'], corners, 0.008)
    # the dark recess: a narrow strip on the sloped face
    slope = Vector((0.105 - 0.035, 0, height))
    normal = Vector((slope.z, 0, -slope.x)).normalized()  # (outward, up) of the sloped face
    out = Vector((d.x * normal.x, d.y * normal.x, -normal.z))
    p0 = d * (inner0 + 0.105) + Vector((0, 0, FOOTING + 0.03))
    p1 = d * (inner1 + 0.035) + Vector((0, 0, FOOTING + height - 0.03))
    recess = beam(f'ButtressRecess{k}', m['dark'], p0 + out * 0.002 - d * 0.004, p1 + out * 0.002 - d * 0.004, 0.045, 0.006)
    foot = d * (inner0 + 0.05) + Vector((0, 0, FOOTING))
    return kit.merge(f'Buttress{k}', [shell, recess], foot)


def crown(m):
    """A thick rim in the house colour round the grey plate with four holes."""
    z = FOOTING + BODY_TOP
    parts = [
        octagon('Collar', m['steel'], ((0.445, 0), (0.445, 0.015), (0.41, 0.025)), z, 0.003),
        plant.lathe('Rim', m['remap'], ((0.37, 0), (0.39, 0.02), (0.385, SLOT_TOP + 0.02 - z), (0.355, SLOT_TOP + 0.032 - z),
                                       (0.325, SLOT_TOP + 0.022 - z), (0.32, SLOT_TOP - 0.02 - z)), (0, 0, z), 32, 0.004),
        cylinder('Plate', m['plate'], 0.325, SLOT_TOP - z, (0, 0, (z + SLOT_TOP) / 2), segments=32, bevel=0.004),
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
    wm = wall.materials()
    root = kit.empty('GDIComponentTower')
    keys = kit.keys

    # ---- the footing spreads
    feet = [octagon('Footing', m['concrete_dark'], ((0.52, 0), (0.52, FOOTING * 0.6), (0.5, FOOTING)), 0, 0.004)]
    feet.append(octagon('FootingEdge', m['steel'], ((0.525, 0), (0.525, 0.012)), 0, 0))
    footing = kit.parent(kit.merge('Footing', feet), root)
    keys(footing, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 10: Vector((1.03, 1.03, 1)), 13: Vector((1, 1, 1))})

    # ---- the wall stubs towards neighbouring walls and gates grow up (glTF +z = Blender -y)
    for name, direction in (('ArmXP', (1, 0, 0)), ('ArmXN', (-1, 0, 0)), ('ArmZN', (0, 1, 0)), ('ArmZP', (0, -1, 0))):
        stub = kit.parent(wall.arm(name, wm, direction, ARM_START), root)
        keys(stub, 'scale', {0: Vector((1, 1, kit.HIDDEN)), 8: Vector((1, 1, kit.HIDDEN)), 22: Vector((1, 1, 1.05)), 26: Vector((1, 1, 1))})

    # ---- the tower rises out of the ground
    tower = kit.parent(kit.empty('TowerGroup'), root)
    for obj in (block(m, root), trim(m)):
        kit.parent(obj, tower)
    keys(tower, 'location', {0: Vector((0, 0, -0.66)), 6: Vector((0, 0, -0.66)), 26: Vector((0, 0, 0.01)), 29: Vector((0, 0, 0))})

    # ---- the buttresses swing out against it
    buttresses = []
    for k in range(4):
        b = kit.parent(buttress(m, k), tower)
        kit.pop(b, 24 + k * 2, 6)
        buttresses.append(b)

    # ---- rim and plate; the weapon's place on top
    top = kit.parent(crown(m), tower)
    slot = kit.empty('TowerSlot1', (0, 0, SLOT_TOP))
    slot.empty_display_size = 0.15
    kit.parent(slot, top)
    keys(top, 'scale', {0: Vector((1, 1, 1)) * kit.HIDDEN, 28: Vector((1, 1, 1)) * kit.HIDDEN, 36: Vector((1.08, 1.08, 1.08)), 40: Vector((1, 1, 1))})

    # ---- a lamp on top of the front buttress (towards the viewer, glTF +x +z); its
    # light hangs from the tower group (not from the popping housing: a parent scaled
    # to nothing in Build spoils the light's keys in Idle)
    a = -math.pi / 4
    d = Vector((math.cos(a), math.sin(a), 0))
    flat = math.cos(OCT)
    p = d * (body_radius(0.42) * flat + 0.005) + Vector((0, 0, FOOTING + 0.42))
    housing, light = kit.beacon('Lamp', m, p, 'amber')
    housing = kit.parent(kit.merge('Lamp', [housing], p), tower)
    kit.parent(light, tower)
    kit.pop(housing, 38, 5)
    lights = [(light, kit.flashes((0, 12), (30, 12)))]

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
