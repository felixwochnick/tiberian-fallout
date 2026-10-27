"""
Tiberian Fallout – GDI Vulcan cannon (GAVULC), the gun the game mounts on a component
tower (GACTWR), after Tiberian Sun.

A squat armoured turret in the desert camouflage with house-colour stripes, an
ammunition box at its back and a mantlet at its front carrying two six-barrelled
gatling guns side by side. Its foot ring locks into the tower's plate with four pegs;
the origin is the middle of the foot, which the game puts onto the tower's node
TowerSlot1 (see GACTWR.py).

Nodes the game drives
    Turret   turns about the vertical towards the target (everything above the foot)
    Cannon   inside Turret, tilts (about its x axis); the barrels point along -Y
    Flash    inside Cannon, between the muzzles: where the shots leave; the muzzle
             fire meshes (MuzzleL/R) are its children, hidden outside Fire

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 0.6 s: the foot locks in, the turret grows up, the guns come out
    Idle     loop, 2 s: the lamp on the turret's back blinks
    Fire     one-shot, 0.3 s: the barrels spin a third of a turn, the guns recoil and
             run out again, the muzzles flash in turn

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAVULC.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z).
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

kit.COLLECTION = 'GDIVulcan'  # after the imports, which set their own
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAVULC.glb')
BLEND = os.path.join(HERE, 'GAVULC.blend')

BUILD_END = 18
FIRE_END = 9
FOOT = 0.025            # top of the foot ring: the turret's floor
GUN_Z = 0.135           # height of the guns' axis above the origin
TRUNNION_Y = -0.1       # where the guns tilt
MUZZLE_Y = -0.46        # the barrels' ends

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = plant.materials()
    m['flash'] = material('GlowFlash', (0, 0, 0), 1.0, emission=srgb('#ffd27a'), strength=6, alpha=0.7)
    m['gun'] = material('GunMetal', srgb('#2e3135'), 0.4, 0.9)
    return m


def camo(obj, root):
    """Gives a one-material object the baked desert camouflage."""
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def foot(m, root):
    """The ring the weapon stands on, with four pegs down into the tower's plate."""
    parts = [cylinder('FootRing', m['pod_dark'], 0.2, FOOT, (0, 0, FOOT / 2), segments=32, bevel=0.004),
             cylinder('FootBearing', m['steel'], 0.17, 0.012, (0, 0, FOOT + 0.006), segments=32, bevel=0.002)]
    for k in range(4):
        a = math.pi / 4 + math.pi / 2 * k
        p = Vector((math.cos(a), math.sin(a), 0)) * plant.HOLE_RADIUS
        parts.append(cylinder(f'Peg{k}', m['steel_light'], 0.022, 0.03, p, segments=12, bevel=0.002))
    return kit.parent(kit.merge('Foot', parts), root)


def housing_shell(name, root, half_x, y_front, y_back, top, slope):
    """A camouflaged turret body: a box whose front top is chamfered by `slope`."""
    z0 = FOOT + 0.005
    verts = (
        (-half_x, y_front, z0), (half_x, y_front, z0), (half_x, y_back, z0), (-half_x, y_back, z0),
        (-half_x + 0.02, y_front + slope, top), (half_x - 0.02, y_front + slope, top),
        (half_x - 0.02, y_back - 0.015, top), (-half_x + 0.02, y_back - 0.015, top),
    )
    return camo(kit.hexahedron(name, kit.materials()['sand'], verts, 0.012), root)


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
    keys = kit.keys
    base = foot(m, root)

    # ---- the turret: everything above the foot turns
    turret = kit.parent(kit.empty('Turret', (0, 0, FOOT)), root)
    shell = housing_shell('Housing', root, 0.165, -0.15, 0.16, FOOT + 0.17, 0.06)
    kit.parent(shell, turret)
    top = FOOT + 0.17
    trim = [
        cylinder('TurretRing', m['steel'], 0.185, 0.02, (0, 0, FOOT + 0.01), segments=32, bevel=0.003),
        # armour cheeks on the sides, with house-colour stripes
        *[box(f'Cheek{s}', m['sand_light'], (0.02, 0.24, 0.1), (0.172 * s, 0.0, FOOT + 0.085), bevel=0.006) for s in (-1, 1)],
        *[box(f'Stripe{s}', m['remap'], (0.006, 0.2, 0.022), (0.184 * s, 0.0, FOOT + 0.11), bevel=0) for s in (-1, 1)],
        # roof: hatch, vision block, a stub antenna
        cylinder('RoofHatch', m['steel'], 0.045, 0.014, (0.06, 0.06, top + 0.007), segments=16, bevel=0.003),
        box('VisionBlock', m['steel_light'], (0.07, 0.04, 0.03), (-0.06, -0.03, top + 0.015), bevel=0.005),
        box('VisionGlass', m['window'], (0.055, 0.006, 0.014), (-0.06, -0.051, top + 0.016), bevel=0),
        beam('Antenna', m['steel'], (-0.11, 0.12, top), (-0.11, 0.12, top + 0.13), 0.006),
        # the ammunition box at the back with a feed chute to the guns
        box('AmmoBox', m['olive'], (0.24, 0.08, 0.11), (0, 0.2, FOOT + 0.08), bevel=0.008),
        box('AmmoLid', m['steel'], (0.25, 0.085, 0.012), (0, 0.2, FOOT + 0.14), bevel=0.003),
        *[box(f'AmmoRib{k}', m['steel'], (0.008, 0.085, 0.1), (x, 0.2, FOOT + 0.08), bevel=0) for k, x in enumerate((-0.06, 0.06))],
    ]
    kit.parent(kit.merge('TurretTrim', trim, (0, 0, FOOT)), turret)

    # ---- the guns: the mantlet tilts with them
    cannon = kit.parent(kit.empty('Cannon', (0, TRUNNION_Y, GUN_Z)), turret)
    mantlet = [
        box('Mantlet', m['steel'], (0.31, 0.07, 0.13), (0, TRUNNION_Y - 0.03, GUN_Z), bevel=0.012),
        cylinder('Trunnion', m['steel_light'], 0.03, 0.35, (0, TRUNNION_Y, GUN_Z), rotation=(0, math.pi / 2, 0), segments=12, bevel=0.003),
        box('MantletBand', m['remap'], (0.312, 0.01, 0.02), (0, TRUNNION_Y - 0.066, GUN_Z + 0.035), bevel=0),
    ]
    kit.parent(kit.merge('Mantlet', mantlet, (0, TRUNNION_Y, GUN_Z)), cannon)
    barrels = []
    for side, x in (('L', -0.09), ('R', 0.09)):
        centre = Vector((x, TRUNNION_Y - 0.065, GUN_Z))
        group = kit.parent(kit.empty(f'Barrels{side}', centre), cannon)
        kit.parent(gatling(m, f'Gatling{side}', centre), group)
        barrels.append(group)

    # where the shots leave, with the muzzle fire at each gun
    flash = kit.parent(kit.empty('Flash', (0, MUZZLE_Y - 0.02, GUN_Z)), cannon)
    flash.empty_display_size = 0.05
    fires = []
    for side, x in (('L', -0.09), ('R', 0.09)):
        tip = Vector((x, MUZZLE_Y - 0.02, GUN_Z))
        balls = [sphere(f'Muzzle{side}{k}', m['flash'], 0.045 - 0.011 * k, tip + Vector((0, -0.035 * k, 0)), 10) for k in range(3)]
        star = [beam(f'Muzzle{side}Spike{k}', m['flash'], tip + Vector((math.cos(a) * 0.07, 0.01, math.sin(a) * 0.07)),
                     tip - Vector((math.cos(a) * 0.07, -0.01, math.sin(a) * 0.07)), 0.012, 0.004)
                for k, a in enumerate((0.4, 0.4 + math.pi / 2))]
        fire = kit.parent(kit.merge(f'Muzzle{side}', balls + star, tip), flash)
        fires.append(fire)

    # a lamp on the turret's back
    p = Vector((0.11, 0.13, top))
    housing, light = kit.beacon('Lamp', m, p, 'red')
    housing = kit.parent(kit.merge('Lamp', [housing], p), turret)
    kit.parent(light, housing)

    build_clip(base, turret, barrels, housing, fires)
    idle_clip(light, fires)
    fire_clip(barrels, fires)
    for fire in fires:
        fire.scale = (kit.HIDDEN,) * 3
    return len(kit.collection().objects)


def hide(objects, frames):
    """Keys `objects` hidden over a clip (the muzzle fire outside Fire)."""
    for obj in objects:
        kit.keys(obj, 'scale', {0: Vector((kit.HIDDEN,) * 3), frames: Vector((kit.HIDDEN,) * 3)}, 'CONSTANT')


def build_clip(base, turret, barrels, lamp, fires):
    kit.pop(base, 0, 5)
    kit.keys(turret, 'scale', {0: Vector((1, 1, 1)) * kit.HIDDEN, 2: Vector((1, 1, 1)) * kit.HIDDEN,
                               9: Vector((1.06, 1.06, 1.1)), 12: Vector((1, 1, 1))})
    for k, group in enumerate(barrels):
        s = Vector(group.scale)
        # the guns run out of the mantlet
        kit.keys(group, 'scale', {0: Vector((1, kit.HIDDEN, 1)), 8 + k * 2: Vector((1, kit.HIDDEN, 1)),
                                  13 + k * 2: Vector((1, 1.08, 1)), 16 + k * 2: s})
    kit.pop(lamp, 12, 5)
    hide(fires, BUILD_END)
    for obj in [base, turret, *barrels, lamp, *fires]:
        kit.to_track(obj, 'Build')


def idle_clip(light, fires):
    kit.blink(light, kit.flashes((0, 10), (30, 10)))
    kit.to_track(light, 'Idle')
    hide(fires, kit.IDLE_END)
    for fire in fires:
        kit.to_track(fire, 'Idle')


def fire_clip(barrels, fires, spin=2 * math.pi / 3):
    """The barrels spin (a third of a turn: they look the same after it) and recoil, the
    muzzles flash in turn."""
    for k, group in enumerate(barrels):
        home = Vector(group.location)
        kit.keys(group, 'rotation_euler', {0: Vector((0, 0, 0)), FIRE_END: Vector((0, spin * (1 if k else -1), 0))}, 'LINEAR')
        kit.keys(group, 'location', {0: home, 1: home + Vector((0, 0.03, 0)), FIRE_END: home})
        kit.to_track(group, 'Fire')
    for k, fire in enumerate(fires):
        frames = {f: Vector((1, 1, 1)) * (1.0 if f < FIRE_END - 2 and (f + k * 2) % 4 < 2 else kit.HIDDEN) for f in range(FIRE_END + 1)}
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
