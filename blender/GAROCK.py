"""
Tiberian Fallout – GDI RPG launcher (GAROCK), the anti-ground rocket weapon the game
mounts on a component tower (GACTWR), after Tiberian Sun (the original's GACTWR_C).

A squat launcher in the desert camouflage with two big rocket tubes side by side
whose round mouths stand out of its rounded front, a block in the house colour on its
back with a grille, a sight on its roof. It rides on two dark trunnion drums between
the arms of the SAM launcher's yoke (see GACSAM.py). Foot, pegs and origin as for the
Vulcan cannon (see GAVULC.py): the origin is the middle of the foot, which the game
puts onto the tower's node TowerSlot1.

Nodes the game drives
    Turret   turns about the vertical towards the target (everything above the foot)
    Cannon   the launcher, inside Turret, tilts (about its x axis) on the drums; the
             tubes point along -Y
    Flash    inside Cannon, between the tubes' mouths: where the rockets leave; the
             launch fire mesh (LaunchFire) is its child, hidden at rest and keyed by
             Fire only

Animations (glTF clips, merged from the NLA tracks of the same name; no channel is
shared between them)
    Build    one-shot, 0.6 s: the foot locks in, the launcher comes up out of the tower
    Idle     loop, 2 s: the lamp on the back blinks
    Fire     one-shot, 0.3 s: a rocket leaves the left tube with a flash and a puff of
             smoke, the launcher recoils, the next rocket slides into the tube

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAROCK.py [-- --preview <dir>]

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
import GACSAM as sam  # noqa: E402 – the yoke
import gdibuilding as gb  # noqa: E402 – prisms

kit.COLLECTION = 'GDIRPG'  # after the imports, which set their own
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAROCK.glb')
BLEND = os.path.join(HERE, 'GAROCK.blend')

FOOT = vulcan.FOOT
GUN_Z = sam.GUN_Z
HALF_W = sam.HALF_W
FRONT, BACK = -0.12, 0.1     # the camouflaged body (relative to the trunnion)
LOW, HIGH = -0.08, 0.08
TUBE_X = 0.068               # the tubes' distance from the middle
TUBE_R = 0.058
TUBE_Z = -0.005
MOUTH_Y = -0.2               # the tubes' mouths
FIRE_END = vulcan.FIRE_END
SIZE = 1.4

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam
ALONG = (math.pi / 2, 0, 0)
ACROSS = (0, math.pi / 2, 0)


def launcher(m, root):
    """The launcher about the trunnion at (0, 0, GUN_Z): (camouflaged body, fittings,
    the rockets in the tubes, left first)."""
    c = Vector((0, 0, GUN_Z))
    r = 0.05   # rounded corners at the front
    profile = [(FRONT + r, LOW), (BACK, LOW), (BACK, HIGH), (FRONT + r, HIGH), (FRONT + 0.012, HIGH - 0.03),
               (FRONT, 0.0), (FRONT + 0.012, LOW + 0.03)]
    shell = gb.prism('LauncherBody', m['sand'], profile, -HALF_W, HALF_W, 'X', bevel=0.016)
    shell.location = c
    shell = vulcan.camo(shell, root)
    fittings = []
    rockets = []
    for k, s in enumerate((-1, 1)):
        p = c + Vector((s * TUBE_X, 0, TUBE_Z))
        length = BACK - MOUTH_Y - 0.03
        fittings += [
            cylinder(f'Tube{k}', m['steel'], TUBE_R, length, p + Vector((0, MOUTH_Y + length / 2, 0)), rotation=ALONG, segments=24, bevel=0.004),
            cylinder(f'Mouth{k}', m['steel_light'], TUBE_R + 0.008, 0.02, p + Vector((0, MOUTH_Y + 0.01, 0)), rotation=ALONG, segments=24, bevel=0.003),
            cylinder(f'Bore{k}', m['dark'], TUBE_R - 0.012, 0.004, p + Vector((0, MOUTH_Y - 0.001, 0)), rotation=ALONG, segments=20, bevel=0),
            cylinder(f'TubeBand{k}', m['remap'], TUBE_R + 0.004, 0.016, p + Vector((0, MOUTH_Y + 0.05, 0)), rotation=ALONG, segments=24, bevel=0),
        ]
        nose_at = p + Vector((0, MOUTH_Y + 0.012, 0))
        nose = cylinder(f'Warhead{k}', m['olive'], 0.032, 0.05, nose_at + Vector((0, 0.0, 0)), rotation=ALONG, segments=14, bevel=0, radius2=0.008)
        rockets.append(kit.merge(f'Rocket{k}', [nose], nose_at))
    roof = c + Vector((0, 0, HIGH))
    fittings += [
        # the block in the house colour on the back with its grille
        box('BackBlock', m['remap'], (2 * HALF_W - 0.03, 0.07, HIGH - LOW - 0.03), c + Vector((0, BACK + 0.03, 0)), bevel=0.01),
        *[box(f'Grille{k}', m['dark'], (2 * HALF_W - 0.08, 0.006, 0.008), c + Vector((0, BACK + 0.066, -0.04 + k * 0.022)), bevel=0) for k in range(4)],
        box('BackSeam', m['remap_dark'], (2 * HALF_W - 0.02, 0.006, HIGH - LOW - 0.02), c + Vector((0, BACK + 0.0, 0)), bevel=0),
        # the sight on the roof, a stripe in the house colour along the sides
        box('Sight', m['steel'], (0.05, 0.06, 0.03), roof + Vector((0.07, -0.02, 0.014)), bevel=0.005),
        box('SightGlass', m['window'], (0.04, 0.004, 0.016), roof + Vector((0.07, -0.051, 0.016)), bevel=0),
        box('RoofPlate', m['steel_light'], (0.12, 0.08, 0.006), roof + Vector((-0.05, 0.01, 0.002)), bevel=0.002),
        *[box(f'SideStripe{s}', m['remap'], (0.004, 0.16, 0.016), c + Vector((s * (HALF_W + 0.002), -0.01, 0.045)), bevel=0) for s in (-1, 1)],
    ]
    for s in (-1, 1):  # the trunnion drums
        x = s * (HALF_W + 0.018)
        fittings += [
            cylinder(f'Drum{s}', m['pod_dark'], sam.DRUM_R, 0.036, c + Vector((x, 0, 0)), rotation=ACROSS, segments=24, bevel=0.006),
            cylinder(f'DrumHub{s}', m['steel'], 0.03, 0.044, c + Vector((x, 0, 0)), rotation=ACROSS, segments=14, bevel=0.003),
        ]
    return shell, kit.merge('LauncherFittings', fittings, c), rockets


def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = kit.IDLE_END
    scene.frame_current = vulcan.BUILD_END

    m = vulcan.materials()
    root = kit.empty('GDIRPG')
    keys = kit.keys
    base = vulcan.foot(m, root, SIZE)

    turret = kit.parent(kit.empty('Turret', (0, 0, FOOT)), root)
    kit.parent(sam.yoke(m), turret)

    cannon = kit.parent(kit.empty('Cannon', (0, 0, GUN_Z)), turret)
    pod = kit.parent(kit.empty('Launcher', (0, 0, GUN_Z)), cannon)
    shell, fittings, rockets = launcher(m, root)
    for obj in (shell, fittings, *rockets):
        kit.parent(obj, pod)

    # where the rockets leave, the launch fire in front of the left tube
    tip = Vector((0, MOUTH_Y - 0.04, GUN_Z + TUBE_Z))
    flash = kit.parent(kit.empty('Flash', tip), cannon)
    flash.empty_display_size = 0.05
    left = tip + Vector((-TUBE_X, 0, 0))
    puffs = [sphere(f'LaunchFire{k}', m['flash'], 0.06 - 0.014 * k, left + Vector((0, -0.045 * k, 0)), 10) for k in range(3)]
    smoke = [sphere(f'LaunchSmoke{k}', m['glow_amber'], 0.045, left + Vector((s * 0.06, 0.03, -0.01)), 8) for k, s in enumerate((-1, 1))]
    # the back blast behind the tube
    blast = [sphere(f'BackBlast{k}', m['flash'], 0.04 - 0.01 * k, Vector((-TUBE_X, BACK + 0.11 + 0.04 * k, GUN_Z + TUBE_Z)), 8) for k in range(2)]
    fire = kit.parent(kit.merge('LaunchFire', puffs + smoke + blast, tip), flash)

    # a lamp on the back block
    p = Vector((-0.09, BACK + 0.03, GUN_Z + HIGH - 0.015))
    housing, light = kit.beacon('Lamp', m, p, 'red')
    housing = kit.parent(kit.merge('Lamp', [housing], p), pod)
    kit.parent(light, housing)

    # ---- Build (nothing above the turret is scaled: see vulcan.rise)
    kit.pop(base, 0, 5)
    vulcan.rise(turret, 2, 14)
    for obj in (base, turret):
        kit.to_track(obj, 'Build')

    # ---- Idle
    kit.blink(light, kit.flashes((0, 10), (30, 10)))
    kit.to_track(light, 'Idle')

    # ---- Fire: flash and back blast, recoil, the left rocket gone and slid back in
    keys(pod, 'location', {0: Vector(pod.location), 1: Vector(pod.location) + Vector((0, 0.035, 0)), FIRE_END: Vector(pod.location)})
    kit.to_track(pod, 'Fire')
    keys(fire, 'scale', {f: Vector((1, 1, 1)) * ((0.7 + 0.3 * f) if 0 < f < 6 else kit.HIDDEN) for f in range(FIRE_END + 1)}, 'CONSTANT')
    kit.to_track(fire, 'Fire')
    rocket = rockets[0]
    home = Vector(rocket.location)
    keys(rocket, 'location', {0: home, 1: home + Vector((0, 0.08, 0)), 5: home + Vector((0, 0.08, 0)), FIRE_END: home})
    kit.to_track(rocket, 'Fire')
    fire.scale = (kit.HIDDEN,) * 3
    root.scale = (SIZE,) * 3
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    vulcan.main(build, OUT, BLEND)
