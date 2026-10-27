"""
Tiberian Fallout – GDI SAM launcher (GACSAM), the anti-aircraft weapon the game mounts on
a component tower (GACTWR), after Tiberian Sun.

A low camouflaged turret with a yoke carrying a box launcher: nine tubes in three rows,
the missiles' noses in the house colour peeking out, a house-colour frame round the
front; a radar dish on a mast at the turret's back. Foot, pegs and origin as for the
Vulcan cannon (see GAVULC.py): the origin is the middle of the foot, which the game
puts onto the tower's node TowerSlot1.

Nodes the game drives
    Turret   turns about the vertical towards the target (everything above the foot)
    Cannon   the launcher, inside Turret, tilts (about its x axis); the tubes point along -Y
    Flash    inside Cannon, in front of the tubes: where the missiles leave; the
             launch fire mesh (LaunchFire) is its child, hidden outside Fire

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 0.6 s: the foot locks in, the turret grows up, the launcher and
             the radar come up
    Idle     loop, 2 s: the radar dish turns, the lamp blinks
    Fire     one-shot, 0.3 s: a missile leaves the top tube with a flash, the launcher
             recoils, the next missile slides into the tube

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GACSAM.py [-- --preview <dir>]

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
import GAVULC as vulcan  # noqa: E402 – foot, turret body, clips and main of the Vulcan cannon

kit.COLLECTION = 'GDISAM'  # after the imports, which set their own
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GACSAM.glb')
BLEND = os.path.join(HERE, 'GACSAM.blend')

FOOT = vulcan.FOOT
GUN_Z = 0.235            # the launcher's trunnion height above the origin
FRONT = -0.15           # the launcher's front face (relative to the trunnion)
TUBE = 0.058            # spacing of the tubes
FIRE_END = vulcan.FIRE_END

box, cylinder, sphere, beam, srgb = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb


def launcher(m, root):
    """The box launcher about the trunnion at (0, 0, GUN_Z): (camouflaged box, fittings,
    the noses of the missiles as a list of objects, the top one first)."""
    c = Vector((0, 0, GUN_Z))
    box_obj = vulcan.camo(kit.box('LauncherBox', m['sand'], (0.27, 0.24, 0.2), c + Vector((0, FRONT + 0.12, 0.0)), bevel=0.014), root)
    fittings = [
        # the house-colour frame round the front, and the tube faces
        box('FrameTop', m['remap'], (0.28, 0.02, 0.022), c + Vector((0, FRONT - 0.004, 0.092)), bevel=0.003),
        box('FrameBottom', m['remap'], (0.28, 0.02, 0.022), c + Vector((0, FRONT - 0.004, -0.092)), bevel=0.003),
        *[box(f'FrameSide{s}', m['remap'], (0.022, 0.02, 0.2), c + Vector((0.13 * s, FRONT - 0.004, 0)), bevel=0.003) for s in (-1, 1)],
        box('TubeFace', m['steel'], (0.24, 0.012, 0.17), c + Vector((0, FRONT - 0.002, 0)), bevel=0.003),
        # side plates with stiffeners, the cable to the turret
        *[box(f'Stiffener{s}{k}', m['sand_light'], (0.012, 0.2, 0.02), c + Vector((0.14 * s, FRONT + 0.12, z)), bevel=0.003)
          for s in (-1, 1) for k, z in enumerate((-0.05, 0.05))],
        box('Cap', m['steel_light'], (0.2, 0.12, 0.016), c + Vector((0, FRONT + 0.16, 0.105)), bevel=0.004),
    ]
    noses = []
    for row in range(3):
        for col in range(3):
            p = c + Vector(((col - 1) * TUBE, FRONT - 0.009, (1 - row) * TUBE))
            fittings.append(cylinder(f'Tube{row}{col}', m['dark'], 0.024, 0.006, p, rotation=(math.pi / 2, 0, 0), segments=14, bevel=0))
            fittings.append(cylinder(f'TubeRim{row}{col}', m['steel_light'], 0.027, 0.004, p + Vector((0, 0.002, 0)),
                                     rotation=(math.pi / 2, 0, 0), segments=14, bevel=0))
            nose = cylinder(f'Nose{row}{col}', m['remap'], 0.02, 0.04, p + Vector((0, -0.012, 0)), rotation=(math.pi / 2, 0, 0),
                            segments=12, bevel=0, radius2=0.004)
            noses.append(kit.merge(f'Missile{row}{col}', [nose], p))
    return box_obj, kit.merge('LauncherFittings', fittings, c), noses


def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = kit.IDLE_END
    scene.frame_current = vulcan.BUILD_END

    m = vulcan.materials()
    root = kit.empty('GDISAM')
    keys = kit.keys
    base = vulcan.foot(m, root)

    # ---- the turret: a low body with a yoke
    turret = kit.parent(kit.empty('Turret', (0, 0, FOOT)), root)
    top = FOOT + 0.1
    kit.parent(vulcan.housing_shell('Housing', root, 0.14, -0.13, 0.15, top, 0.04), turret)
    trim = [
        kit.cylinder('TurretRing', m['steel'], 0.18, 0.02, (0, 0, FOOT + 0.01), segments=32, bevel=0.003),
        *[box(f'Stripe{s}', m['remap'], (0.006, 0.18, 0.02), (0.142 * s, 0.01, FOOT + 0.065), bevel=0) for s in (-1, 1)],
        # the yoke's arms up to the trunnion
        *[kit.hexahedron(f'Yoke{s}', m['steel'], [
            (0.16 * s + dx, y, z) for z, ys in ((top - 0.01, (-0.07, 0.07)), (GUN_Z + 0.03, (-0.035, 0.035)))
            for y, dx in ((ys[0], -0.014), (ys[0], 0.014), (ys[1], 0.014), (ys[1], -0.014))], 0.005)
          for s in (-1, 1)],
        box('ControlBox', m['olive'], (0.1, 0.06, 0.06), (-0.06, 0.12, top + 0.03), bevel=0.006),
    ]
    kit.parent(kit.merge('TurretTrim', trim, (0, 0, FOOT)), turret)

    # ---- the launcher tilts; its box recoils inside the Cannon node
    cannon = kit.parent(kit.empty('Cannon', (0, 0, GUN_Z)), turret)
    kit.parent(kit.merge('Trunnion', [cylinder('TrunnionPin', m['steel_light'], 0.025, 0.36, (0, 0, GUN_Z),
                                               rotation=(0, math.pi / 2, 0), segments=12, bevel=0.003)], (0, 0, GUN_Z)), cannon)
    pod = kit.parent(kit.empty('Launcher', (0, 0, GUN_Z)), cannon)
    box_obj, fittings, noses = launcher(m, root)
    for obj in (box_obj, fittings, *noses):
        kit.parent(obj, pod)

    # where the missiles leave, with the launch fire in front of the top tube
    flash = kit.parent(kit.empty('Flash', (0, FRONT - 0.04, GUN_Z + TUBE)), cannon)
    flash.empty_display_size = 0.05
    tip = Vector((0, FRONT - 0.04, GUN_Z + TUBE))
    puffs = [sphere(f'LaunchFire{k}', m['flash'], 0.05 - 0.012 * k, tip + Vector((0.01 * k, -0.04 * k, 0.005 * k)), 10) for k in range(3)]
    smoke = [sphere(f'LaunchSmoke{k}', m['glow_amber'], 0.04, tip + Vector((s * 0.05, 0.02, -0.01)), 8) for k, s in enumerate((-1, 1))]
    fire = kit.parent(kit.merge('LaunchFire', puffs + smoke, tip), flash)

    # ---- radar dish on a mast at the back
    mast_foot = Vector((0.08, 0.11, top))
    mast = kit.parent(kit.merge('RadarMast', [cylinder('Mast', m['steel'], 0.01, 0.16, mast_foot + Vector((0, 0, 0.08)), segments=8, bevel=0),
                                               cylinder('MastFoot', m['steel_light'], 0.022, 0.02, mast_foot + Vector((0, 0, 0.01)), segments=10, bevel=0.002)],
                                    mast_foot), turret)
    head = mast_foot + Vector((0, 0, 0.16))
    radar = kit.parent(kit.empty('Radar', head), mast)
    dish = [
        cylinder('Dish', m['steel_light'], 0.075, 0.03, head + Vector((0, -0.012, 0.03)), rotation=(math.radians(-70), 0, 0), segments=20, radius2=0.025),
        beam('DishArm', m['steel'], head, head + Vector((0, -0.02, 0.03)), 0.012),
        beam('DishFeed', m['steel'], head + Vector((0, -0.02, 0.03)), head + Vector((0, -0.08, 0.05)), 0.005),
    ]
    kit.parent(kit.merge('RadarDish', dish, head), radar)

    # a lamp on the turret's back
    p = Vector((-0.1, 0.1, top))
    housing, light = kit.beacon('Lamp', m, p, 'red')
    housing = kit.parent(kit.merge('Lamp', [housing], p), turret)
    kit.parent(light, housing)

    # ---- clips
    vulcan.kit.pop(base, 0, 5)
    keys(turret, 'scale', {0: Vector((1, 1, 1)) * kit.HIDDEN, 2: Vector((1, 1, 1)) * kit.HIDDEN,
                           9: Vector((1.06, 1.06, 1.1)), 12: Vector((1, 1, 1))})
    kit.pop(pod, 8, 7)
    kit.grow(mast, 10, 6, 2)
    kit.pop(housing, 12, 5)
    vulcan.hide([fire], vulcan.BUILD_END)
    for obj in (base, turret, pod, mast, housing, fire):
        kit.to_track(obj, 'Build')

    kit.blink(light, kit.flashes((0, 10), (30, 10)))
    kit.to_track(light, 'Idle')
    keys(radar, 'rotation_euler', {f: Vector((0, 0, 2 * math.pi * f / kit.IDLE_END)) for f in range(0, kit.IDLE_END + 1, 3)}, 'LINEAR')
    kit.to_track(radar, 'Idle')
    vulcan.hide([fire], kit.IDLE_END)
    kit.to_track(fire, 'Idle')

    # Fire: the flash, the recoil, the top middle missile gone and slid back in
    keys(pod, 'location', {0: Vector(pod.location), 1: Vector(pod.location) + Vector((0, 0.035, 0)), FIRE_END: Vector(pod.location)})
    kit.to_track(pod, 'Fire')
    keys(fire, 'scale', {f: Vector((1, 1, 1)) * ((1.0 + 0.3 * f) if f < 5 else kit.HIDDEN) for f in range(FIRE_END + 1)}, 'CONSTANT')
    kit.to_track(fire, 'Fire')
    missile = noses[1]
    home = Vector(missile.location)
    keys(missile, 'location', {0: home, 1: home + Vector((0, 0.06, 0)), 5: home + Vector((0, 0.06, 0)), FIRE_END: home})
    kit.to_track(missile, 'Fire')
    fire.scale = (kit.HIDDEN,) * 3
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    vulcan.main(build, OUT, BLEND)
