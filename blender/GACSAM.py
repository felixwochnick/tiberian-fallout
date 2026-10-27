"""
Tiberian Fallout – GDI SAM launcher (GACSAM), the anti-aircraft weapon the game mounts on
a component tower (GACTWR), after Tiberian Sun (the original's GACTWR_D).

A box launcher in the desert camouflage, its front top bevelled, eight tubes in two
rows in its front face with the missiles' noses in the house colour, a hatch in the
house colour on its roof, a grille across its back and a small radar dish behind the
hatch. It rides on two dark trunnion drums between the arms of a low yoke on a
turntable. Foot, pegs and origin as for the Vulcan cannon (see GAVULC.py): the origin
is the middle of the foot, which the game puts onto the tower's node TowerSlot1.

Nodes the game drives
    Turret   turns about the vertical towards the target (everything above the foot)
    Cannon   the launcher, inside Turret, tilts (about its x axis) on the drums; the
             tubes point along -Y; it clears the yoke from 30° down to 35° up
    Flash    inside Cannon, in front of the upper tubes: where the missiles leave; the
             launch fire mesh (LaunchFire) is its child, hidden at rest and keyed by
             Fire only

Animations (glTF clips, merged from the NLA tracks of the same name; no channel is
shared between them)
    Build    one-shot, 0.6 s: the foot locks in, the launcher comes up out of the tower
    Idle     loop, 2 s: the radar dish turns, the lamp blinks
    Fire     one-shot, 0.3 s: a missile leaves an upper tube with a flash, the launcher
             recoils, the next missile slides into the tube

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GACSAM.py [-- --preview <dir>]

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
import GAVULC as vulcan  # noqa: E402 – foot, camouflage, materials and main of the Vulcan cannon
import gdibuilding as gb  # noqa: E402 – prisms

kit.COLLECTION = 'GDISAM'  # after the imports, which set their own
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GACSAM.glb')
BLEND = os.path.join(HERE, 'GACSAM.blend')

FOOT = vulcan.FOOT
GUN_Z = FOOT + 0.17     # the trunnion's height above the origin
HALF_W = 0.14           # the launcher box: half its width,
FRONT, BACK = -0.13, 0.13   # its front and back face (relative to the trunnion),
LOW, HIGH = -0.075, 0.075   # its bottom and top,
BEVEL_Y, BEVEL_Z = -0.07, 0.025  # where the bevel of its front top starts on the roof and the face
DRUM_R = 0.07           # the trunnion drums
ARM_X = 0.2             # the yoke's arms
FIRE_END = vulcan.FIRE_END
SIZE = 1.4              # scale of the whole weapon (root node), to fit the tower's plate

box, cylinder, sphere, beam, srgb = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb
ALONG = (math.pi / 2, 0, 0)     # a cylinder along y
ACROSS = (0, math.pi / 2, 0)    # a cylinder along x


def launcher(m, root):
    """The box launcher about the trunnion at (0, 0, GUN_Z): (camouflaged box, fittings,
    the missiles' noses, the upper row first)."""
    c = Vector((0, 0, GUN_Z))
    profile = [(FRONT, LOW), (BACK, LOW), (BACK, HIGH), (BEVEL_Y, HIGH), (FRONT, BEVEL_Z)]
    shell = gb.prism('LauncherBox', m['sand'], [(y, z) for y, z in profile], -HALF_W, HALF_W, 'X', bevel=0.012)
    shell.location = c
    shell = vulcan.camo(shell, root)
    bevel = math.atan2(HIGH - BEVEL_Z, BEVEL_Y - FRONT)   # slope of the front top
    roof = c + Vector((0, 0, HIGH))
    fittings = [
        # the face with the tubes, its frame in the house colour
        box('TubeFace', m['steel'], (2 * HALF_W - 0.03, 0.008, BEVEL_Z - LOW - 0.02), c + Vector((0, FRONT - 0.003, (LOW + BEVEL_Z) / 2)), bevel=0.002),
        box('FrameTop', m['remap'], (2 * HALF_W - 0.01, 0.012, 0.014), c + Vector((0, FRONT - 0.004, BEVEL_Z - 0.006)), bevel=0.002),
        # the hatch on the roof with its sight, the grille at the back
        box('Hatch', m['remap'], (0.13, 0.1, 0.012), roof + Vector((-0.02, 0.02, 0.005)), bevel=0.003),
        box('HatchSeam', m['remap_dark'], (0.135, 0.006, 0.013), roof + Vector((-0.02, 0.0, 0.006)), bevel=0),
        box('Sight', m['steel'], (0.05, 0.035, 0.03), roof + Vector((-0.045, 0.0, 0.026)), bevel=0.004),
        box('SightGlass', m['window'], (0.04, 0.004, 0.014), roof + Vector((-0.045, -0.019, 0.028)), bevel=0),
        box('Grille', m['steel'], (2 * HALF_W - 0.05, 0.01, 0.1), c + Vector((0, BACK + 0.003, -0.005)), bevel=0.003),
        *[box(f'GrilleSlat{k}', m['dark'], (2 * HALF_W - 0.06, 0.006, 0.006), c + Vector((0, BACK + 0.008, -0.04 + k * 0.023)), bevel=0) for k in range(4)],
        # the bevel's plate and a stripe in the house colour along the sides
        box('BevelPlate', m['steel_light'], (2 * HALF_W - 0.05, 0.05, 0.006),
            c + Vector((0, (FRONT + BEVEL_Y) / 2 + 0.003, (HIGH + BEVEL_Z) / 2 + 0.003)), bevel=0.002, rotation=(bevel, 0, 0)),
        *[box(f'SideStripe{s}', m['remap'], (0.004, 0.2, 0.018), c + Vector((s * (HALF_W + 0.002), 0.0, 0.045)), bevel=0) for s in (-1, 1)],
    ]
    noses = []
    for row, z in enumerate((-0.005, -0.05)):
        for col in range(4):
            p = c + Vector(((col - 1.5) * 0.06, FRONT - 0.008, z))
            fittings.append(cylinder(f'TubeRim{row}{col}', m['steel_light'], 0.024, 0.006, p, rotation=ALONG, segments=14, bevel=0))
            fittings.append(cylinder(f'Tube{row}{col}', m['dark'], 0.019, 0.004, p + Vector((0, -0.002, 0)), rotation=ALONG, segments=14, bevel=0))
            nose = cylinder(f'Nose{row}{col}', m['remap'], 0.016, 0.03, p + Vector((0, -0.008, 0)), rotation=ALONG, segments=12, bevel=0, radius2=0.003)
            noses.append(kit.merge(f'Missile{row}{col}', [nose], p))
    # the trunnion drums on the sides (round: they look the same at any tilt)
    for s in (-1, 1):
        x = s * (HALF_W + 0.018)
        fittings += [
            cylinder(f'Drum{s}', m['pod_dark'], DRUM_R, 0.036, c + Vector((x, 0, 0)), rotation=ACROSS, segments=24, bevel=0.006),
            cylinder(f'DrumHub{s}', m['steel'], 0.03, 0.044, c + Vector((x, 0, 0)), rotation=ACROSS, segments=14, bevel=0.003),
        ]
    return shell, kit.merge('LauncherFittings', fittings, c), noses


def yoke(m):
    """Turntable, crossbar and the two arms up to the drums."""
    z0 = FOOT
    parts = [
        cylinder('TurretRing', m['steel'], 0.18, 0.02, (0, 0, z0 + 0.01), segments=32, bevel=0.003),
        cylinder('Turntable', m['pod_dark'], 0.15, 0.025, (0, 0, z0 + 0.032), segments=32, bevel=0.004),
        box('Crossbar', m['steel'], (2 * ARM_X + 0.03, 0.12, 0.03), (0, 0, z0 + 0.05), bevel=0.006),
        cylinder('Pedestal', m['steel_light'], 0.045, 0.04, (0, 0, z0 + 0.08), segments=16, bevel=0.003),
    ]
    for s in (-1, 1):
        x = s * ARM_X
        parts += [
            kit.hexahedron(f'Arm{s}', m['steel'], [
                (x - 0.012, -0.06, z0 + 0.04), (x + 0.012, -0.06, z0 + 0.04), (x + 0.012, 0.06, z0 + 0.04), (x - 0.012, 0.06, z0 + 0.04),
                (x - 0.012, -0.035, GUN_Z + 0.02), (x + 0.012, -0.035, GUN_Z + 0.02), (x + 0.012, 0.035, GUN_Z + 0.02), (x - 0.012, 0.035, GUN_Z + 0.02),
            ], 0.005),
            cylinder(f'Bearing{s}', m['steel_light'], 0.03, 0.03, (x, 0, GUN_Z), rotation=ACROSS, segments=14, bevel=0.003),
            box(f'ArmStripe{s}', m['remap'], (0.004, 0.07, 0.02), (x + s * 0.013, 0, FOOT + 0.1), bevel=0),
        ]
    return kit.merge('Yoke', parts, (0, 0, z0))


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
    base = vulcan.foot(m, root, SIZE)

    # ---- the turret: the yoke on its turntable
    turret = kit.parent(kit.empty('Turret', (0, 0, FOOT)), root)
    kit.parent(yoke(m), turret)

    # ---- the launcher tilts on its drums; its box recoils inside the Cannon node
    cannon = kit.parent(kit.empty('Cannon', (0, 0, GUN_Z)), turret)
    pod = kit.parent(kit.empty('Launcher', (0, 0, GUN_Z)), cannon)
    shell, fittings, noses = launcher(m, root)
    for obj in (shell, fittings, *noses):
        kit.parent(obj, pod)

    # where the missiles leave, with the launch fire in front of the upper tubes
    tip = Vector((0, FRONT - 0.05, GUN_Z - 0.005))
    flash = kit.parent(kit.empty('Flash', tip), cannon)
    flash.empty_display_size = 0.05
    puffs = [sphere(f'LaunchFire{k}', m['flash'], 0.05 - 0.012 * k, tip + Vector((0.01 * k, -0.04 * k, 0.005 * k)), 10) for k in range(3)]
    smoke = [sphere(f'LaunchSmoke{k}', m['glow_amber'], 0.04, tip + Vector((s * 0.05, 0.02, -0.01)), 8) for k, s in enumerate((-1, 1))]
    fire = kit.parent(kit.merge('LaunchFire', puffs + smoke, tip), flash)

    # ---- the radar dish on a short mast behind the hatch
    mast_foot = Vector((0.07, 0.07, GUN_Z + HIGH))
    mast = kit.parent(kit.merge('RadarMast', [cylinder('Mast', m['steel'], 0.008, 0.07, mast_foot + Vector((0, 0, 0.035)), segments=8, bevel=0),
                                               cylinder('MastFoot', m['steel_light'], 0.02, 0.016, mast_foot + Vector((0, 0, 0.008)), segments=10, bevel=0.002)],
                                    mast_foot), pod)
    head = mast_foot + Vector((0, 0, 0.07))
    radar = kit.parent(kit.empty('Radar', head), mast)
    dish = [
        cylinder('Dish', m['steel_light'], 0.05, 0.02, head + Vector((0, -0.01, 0.022)), rotation=(math.radians(-70), 0, 0), segments=20, radius2=0.018),
        beam('DishArm', m['steel'], head, head + Vector((0, -0.015, 0.022)), 0.01),
        beam('DishFeed', m['steel'], head + Vector((0, -0.015, 0.022)), head + Vector((0, -0.055, 0.035)), 0.004),
    ]
    kit.parent(kit.merge('RadarDish', dish, head), radar)

    # a lamp on the launcher's roof, at its back left
    p = Vector((-0.1, 0.1, GUN_Z + HIGH))
    housing, light = kit.beacon('Lamp', m, p, 'red')
    housing = kit.parent(kit.merge('Lamp', [housing], p), pod)
    kit.parent(light, housing)

    # ---- Build
    # (nothing above the turret is scaled: see vulcan.rise)
    kit.pop(base, 0, 5)
    vulcan.rise(turret, 2, 14)
    for obj in (base, turret):
        kit.to_track(obj, 'Build')

    # ---- Idle
    kit.blink(light, kit.flashes((0, 10), (30, 10)))
    kit.to_track(light, 'Idle')
    keys(radar, 'rotation_euler', {f: Vector((0, 0, 2 * math.pi * f / kit.IDLE_END)) for f in range(0, kit.IDLE_END + 1, 3)}, 'LINEAR')
    kit.to_track(radar, 'Idle')

    # ---- Fire: the flash, the recoil, an upper missile gone and slid back in;
    # the fire is hidden on the clip's first and last frame (its pose at rest)
    keys(pod, 'location', {0: Vector(pod.location), 1: Vector(pod.location) + Vector((0, 0.03, 0)), FIRE_END: Vector(pod.location)})
    kit.to_track(pod, 'Fire')
    keys(fire, 'scale', {f: Vector((1, 1, 1)) * ((0.7 + 0.3 * f) if 0 < f < 6 else kit.HIDDEN) for f in range(FIRE_END + 1)}, 'CONSTANT')
    kit.to_track(fire, 'Fire')
    missile = noses[1]
    home = Vector(missile.location)
    keys(missile, 'location', {0: home, 1: home + Vector((0, 0.05, 0)), 5: home + Vector((0, 0.05, 0)), FIRE_END: home})
    kit.to_track(missile, 'Fire')
    fire.scale = (kit.HIDDEN,) * 3
    root.scale = (SIZE,) * 3  # sized to the tower's plate (all above is modelled at 1)
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    vulcan.main(build, OUT, BLEND)
