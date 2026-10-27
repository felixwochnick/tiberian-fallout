"""
Tiberian Fallout – GDI Vulcan cannon (GAVULC), the gun the game mounts on a component
tower (GACTWR), after Tiberian Sun.

A rounded armoured turret in the desert camouflage with a grille across its back and
an ammunition drum in the house colour on either side; on top, on a pedestal, two
six-barrelled gatling guns side by side, clamped together by a bridge (like the
original's GACTWR_B). Its foot ring locks into the tower's plate with four pegs;
the origin is the middle of the foot, which the game puts onto the tower's node
TowerSlot1 (see GACTWR.py).

Nodes the game drives
    Turret   turns about the vertical towards the target (everything above the foot)
    Cannon   inside Turret, tilts (about its x axis) on the pedestal; the barrels point
             along -Y and clear the body from about 20° down to 15° up
    Flash    inside Cannon, between the muzzles: where the shots leave; the muzzle
             fire meshes (MuzzleL/R) are its children, hidden at rest and keyed by
             Fire only (no channel is shared between the clips)

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 0.6 s: the foot locks in, the turret comes up out of the tower,
             the guns run out
    Idle     loop, 2 s: the lamp on the turret's back blinks
    Fire     one-shot, 0.3 s: the barrels spin a third of a turn, the guns recoil and
             run out again, the muzzles flash in turn

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAVULC.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The parts are
modelled at a smaller size, the root node scales the whole weapon by SIZE to fit the
tower's plate.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import GAPOWR as plant  # noqa: E402 – HOLE_RADIUS (the plate's holes) and materials
import GACTWR as tower  # noqa: E402 – the preview with a closer camera
import housecamo  # noqa: E402

kit.COLLECTION = 'GDIVulcan'  # after the imports, which set their own
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAVULC.glb')
BLEND = os.path.join(HERE, 'GAVULC.blend')

BUILD_END = 18
FIRE_END = 9
FOOT = 0.025            # top of the foot ring: the turret's floor
BODY_TOP = FOOT + 0.16  # top of the rounded body
GUN_Z = 0.262           # height of the guns' axis above the origin
TRUNNION_Y = 0.02       # where the guns tilt
GUN_X = 0.09            # the guns' distance from the middle
GUN_BACK = 0.1          # the guns' back ends (breeches)
MUZZLE_Y = -0.34        # the barrels' ends
DRUM_R = 0.062          # the ammunition drums on the sides
SIZE = 1.3              # scale of the whole weapon (root node), to fit the tower's plate

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = plant.materials()
    m['flash'] = material('GlowFlash', (0, 0, 0), 1.0, emission=srgb('#ffd27a'), strength=6, alpha=0.7)
    m['gun'] = material('GunMetal', srgb('#2e3135'), 0.4, 0.9)
    m['remap_dark'] = housecamo.shade('RemapDark', 0.6, 1.0, 0.6)
    return m


def camo(obj, root):
    """Gives a one-material object the baked desert camouflage."""
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def foot(m, root, size=1.0):
    """The ring the weapon stands on, with four pegs down into the tower's plate (at the
    plate's holes also when the whole weapon is scaled by `size`)."""
    parts = [cylinder('FootRing', m['pod_dark'], 0.2, FOOT, (0, 0, FOOT / 2), segments=32, bevel=0.004),
             cylinder('FootBearing', m['steel'], 0.17, 0.012, (0, 0, FOOT + 0.006), segments=32, bevel=0.002)]
    for k in range(4):
        a = math.pi / 4 + math.pi / 2 * k
        p = Vector((math.cos(a), math.sin(a), 0)) * plant.HOLE_RADIUS / size
        parts.append(cylinder(f'Peg{k}', m['steel_light'], 0.022, 0.03, p, segments=12, bevel=0.002))
    return kit.parent(kit.merge('Foot', parts), root)


def housing_shell(name, root, half_x, y_front, y_back, top, slope, bevel=0.012, segments=2):
    """A camouflaged turret body: a box whose front top is chamfered by `slope`."""
    z0 = FOOT + 0.005
    verts = (
        (-half_x, y_front, z0), (half_x, y_front, z0), (half_x, y_back, z0), (-half_x, y_back, z0),
        (-half_x + 0.02, y_front + slope, top), (half_x - 0.02, y_front + slope, top),
        (half_x - 0.02, y_back - 0.015, top), (-half_x + 0.02, y_back - 0.015, top),
    )
    obj = kit.hexahedron(name, kit.materials()['sand'], verts, bevel)
    obj.modifiers['Bevel'].segments = segments
    return camo(obj, root)


def gatling(m, name, centre):
    """A six-barrelled gun along -Y from `centre` (its back end at the mantlet)."""
    c = Vector(centre)
    length = c.y - MUZZLE_Y
    along = (math.pi / 2, 0, 0)
    parts = [
        cylinder(f'{name}Breech', m['gun'], 0.055, 0.09, c + Vector((0, -0.045, 0)), rotation=along, segments=16, bevel=0.004),
        cylinder(f'{name}Clamp', m['steel_light'], 0.044, 0.014, c + Vector((0, -length * 0.55, 0)), rotation=along, segments=16, bevel=0.002),
        cylinder(f'{name}Muzzle', m['gun'], 0.042, 0.02, c + Vector((0, -length + 0.012, 0)), rotation=along, segments=16, bevel=0.002),
        cylinder(f'{name}Spindle', m['steel'], 0.01, length - 0.04, c + Vector((0, -length / 2, 0)), rotation=along, segments=8, bevel=0),
    ]
    for k in range(6):
        a = math.pi / 3 * k
        off = Vector((math.cos(a) * 0.027, 0, math.sin(a) * 0.027))
        parts.append(cylinder(f'{name}Barrel{k}', m['steel'], 0.011, length - 0.07, c + off + Vector((0, -0.07 - (length - 0.07) / 2, 0)),
                              rotation=along, segments=8, bevel=0))
        parts.append(cylinder(f'{name}Bore{k}', m['dark'], 0.007, 0.004, c + off + Vector((0, -length - 0.001, 0)),
                              rotation=along, segments=6, bevel=0))
    return kit.merge(name, parts, c)


def drum(m, name, x, y, z):
    """An ammunition drum in the house colour on the turret's side (axis along x)."""
    s = 1 if x > 0 else -1
    across = (0, math.pi / 2, 0)
    parts = [
        cylinder(f'{name}', m['remap'], DRUM_R, 0.075, (x, y, z), rotation=across, segments=20, bevel=0.008),
        cylinder(f'{name}Cap', m['steel'], DRUM_R * 0.62, 0.012, (x + s * 0.04, y, z), rotation=across, segments=16, bevel=0.002),
        cylinder(f'{name}Hub', m['steel_light'], 0.018, 0.012, (x + s * 0.048, y, z), rotation=across, segments=10, bevel=0.002),
    ]
    for k in (-1, 1):  # grooves round the drum
        parts.append(cylinder(f'{name}Groove{k}', m['remap_dark'], DRUM_R + 0.002, 0.008, (x + k * 0.02, y, z), rotation=across, segments=20, bevel=0))
    return kit.merge(name, parts, (x, y, z))


def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = kit.IDLE_END
    scene.frame_current = BUILD_END

    m = materials()
    root = kit.empty('GDIVulcan')
    base = foot(m, root, SIZE)

    # ---- the turret: everything above the foot turns
    turret = kit.parent(kit.empty('Turret', (0, 0, FOOT)), root)
    shell = housing_shell('Housing', root, 0.165, -0.17, 0.165, BODY_TOP, 0.1, bevel=0.045, segments=4)
    kit.parent(shell, turret)
    top = BODY_TOP
    trim = [
        cylinder('TurretRing', m['steel'], 0.185, 0.02, (0, 0, FOOT + 0.01), segments=32, bevel=0.003),
        # the grille across the back, the vision slits at the front
        box('Grille', m['steel'], (0.2, 0.012, 0.045), (0, 0.168, FOOT + 0.06), bevel=0.003),
        *[box(f'GrilleSlat{k}', m['dark'], (0.19, 0.006, 0.005), (0, 0.175, FOOT + 0.045 + k * 0.012), bevel=0) for k in range(3)],
        box('Band', m['remap'], (0.2, 0.08, 0.008), (0, 0.06, top + 0.002), bevel=0.002),
        # the pedestal the guns pivot on
        box('Pedestal', m['steel'], (0.05, 0.07, GUN_Z - 0.045 - top + 0.01), (0, TRUNNION_Y, (GUN_Z - 0.045 + top - 0.01) / 2), bevel=0.006),
        *[box(f'Fork{s}', m['steel'], (0.012, 0.05, 0.07), (0.037 * s, TRUNNION_Y, GUN_Z - 0.02), bevel=0.003) for s in (-1, 1)],
    ]
    kit.parent(kit.merge('TurretTrim', trim, (0, 0, FOOT)), turret)
    for s in (-1, 1):
        kit.parent(drum(m, f'Drum{"L" if s < 0 else "R"}', s * 0.2, 0.04, FOOT + 0.085), turret)

    # ---- the guns: the mantlet tilts with them
    cannon = kit.parent(kit.empty('Cannon', (0, TRUNNION_Y, GUN_Z)), turret)
    mantlet = [
        cylinder('Mantlet', m['steel_light'], 0.038, 0.06, (0, TRUNNION_Y, GUN_Z), rotation=(0, math.pi / 2, 0), segments=16, bevel=0.004),
        cylinder('Trunnion', m['steel'], 0.014, 0.09, (0, TRUNNION_Y, GUN_Z), rotation=(0, math.pi / 2, 0), segments=10, bevel=0.002),
        # the bridge that clamps both guns
        box('Bridge', m['steel'], (2 * GUN_X, 0.05, 0.024), (0, TRUNNION_Y - 0.03, GUN_Z + 0.045), bevel=0.004),
        box('BridgeBand', m['remap'], (2 * GUN_X - 0.02, 0.03, 0.006), (0, TRUNNION_Y - 0.03, GUN_Z + 0.058), bevel=0),
    ]
    kit.parent(kit.merge('Mantlet', mantlet, (0, TRUNNION_Y, GUN_Z)), cannon)
    barrels = []
    for side, x in (('L', -GUN_X), ('R', GUN_X)):
        centre = Vector((x, GUN_BACK, GUN_Z))
        group = kit.parent(kit.empty(f'Barrels{side}', centre), cannon)
        kit.parent(gatling(m, f'Gatling{side}', centre), group)
        barrels.append(group)

    # where the shots leave, with the muzzle fire at each gun
    flash = kit.parent(kit.empty('Flash', (0, MUZZLE_Y - 0.02, GUN_Z)), cannon)
    flash.empty_display_size = 0.05
    fires = []
    for side, x in (('L', -GUN_X), ('R', GUN_X)):
        tip = Vector((x, MUZZLE_Y - 0.02, GUN_Z))
        balls = [sphere(f'Muzzle{side}{k}', m['flash'], 0.045 - 0.011 * k, tip + Vector((0, -0.035 * k, 0)), 10) for k in range(3)]
        star = [beam(f'Muzzle{side}Spike{k}', m['flash'], tip + Vector((math.cos(a) * 0.07, 0.01, math.sin(a) * 0.07)),
                     tip - Vector((math.cos(a) * 0.07, -0.01, math.sin(a) * 0.07)), 0.012, 0.004)
                for k, a in enumerate((0.4, 0.4 + math.pi / 2))]
        fire = kit.parent(kit.merge(f'Muzzle{side}', balls + star, tip), flash)
        fires.append(fire)

    # a lamp on the turret's back
    p = Vector((0, 0.13, top - 0.004))  # between the guns' breeches
    housing, light = kit.beacon('Lamp', m, p, 'red')
    housing = kit.parent(kit.merge('Lamp', [housing], p), turret)
    kit.parent(light, housing)

    build_clip(base, turret, barrels)
    idle_clip(light)
    fire_clip(barrels, fires)
    for fire in fires:  # hidden at rest: only Fire shows them
        fire.scale = (kit.HIDDEN,) * 3
    root.scale = (SIZE,) * 3  # sized to the tower's plate (all above is modelled at 1)
    return len(kit.collection().objects)


def rise(turret, start=2, end=12):
    """Build: the turret comes up out of the tower (hidden in its block at first). It
    is never scaled to almost nothing: the glTF exporter would then write wobbling
    translations into the Idle and Fire keys of everything under it."""
    home = Vector(turret.location)
    low = home + Vector((0, 0, -0.24))
    kit.keys(turret, 'location', {0: low, start: low, end - 2: home + Vector((0, 0, 0.012)), end: home})
    kit.keys(turret, 'scale', {0: Vector((0.4, 0.4, 0.4)), start: Vector((0.4, 0.4, 0.4)), end - 3: Vector((1.05, 1.05, 1.08)), end: Vector((1, 1, 1))})


def build_clip(base, turret, barrels):
    kit.pop(base, 0, 5)
    rise(turret)
    for k, group in enumerate(barrels):
        s = Vector(group.scale)
        # the guns run out of the mantlet
        kit.keys(group, 'scale', {0: Vector((1, kit.HIDDEN, 1)), 8 + k * 2: Vector((1, kit.HIDDEN, 1)),
                                  13 + k * 2: Vector((1, 1.08, 1)), 16 + k * 2: s})
    for obj in [base, turret, *barrels]:
        kit.to_track(obj, 'Build')


def idle_clip(light):
    kit.blink(light, kit.flashes((0, 10), (30, 10)))
    kit.to_track(light, 'Idle')


def fire_clip(barrels, fires, spin=2 * math.pi / 3):
    """The barrels spin (a third of a turn: they look the same after it) and recoil, the
    muzzles flash in turn (the only clip that keys them; hidden on its first and last
    frame, which is also their pose at rest)."""
    for k, group in enumerate(barrels):
        home = Vector(group.location)
        kit.keys(group, 'rotation_euler', {0: Vector((0, 0, 0)), FIRE_END: Vector((0, spin * (1 if k else -1), 0))}, 'LINEAR')
        kit.keys(group, 'location', {0: home, 1: home + Vector((0, 0.03, 0)), FIRE_END: home})
        kit.to_track(group, 'Fire')
    for k, fire in enumerate(fires):
        frames = {f: Vector((1, 1, 1)) * (1.0 if 0 < f < FIRE_END - 1 and (f - 1 + k * 2) % 4 < 2 else kit.HIDDEN) for f in range(FIRE_END + 1)}
        kit.keys(fire, 'scale', frames, 'CONSTANT')
        kit.to_track(fire, 'Fire')


def main(build_fn=build, out=OUT, blend=BLEND, bake=512):
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build_fn(), flush=True)
    kit.bake_camo(bake)
    bpy.context.scene.frame_set(BUILD_END)
    print('export', kit.export_glb(out), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    if '--preview' in args:
        tower.preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2],
                      ortho=1.2, target=(0, -0.1, 0.12))


if __name__ == '__main__' and bpy.app.background:
    main()
