"""
Tiberian Fallout – Nod SAM site (NASAM), after Tiberian Sun.

A low, sloped bunker of dark concrete on one cell, its slopes painted with yellow and
black hazard stripes, a red (house colour) rim round its foot and round the hatch on
top. In the hatch sits the launcher: a turntable with an arm carrying a box of four
missiles with red tips. At rest the launcher is down in the bunker; to fire it rises
out, shoots and sinks back.

Nodes the game uses (see nodbuilding.py):
    Turret           the turntable, turning about the vertical
    Lift             under the turret: raises the launcher out of the hatch (Fire)
    Cannon           the launcher's trunnion, tipped up and down; the tubes look along -Y
    FlashL, FlashR   the glows at the left and the right pair of tubes (shots alternate)
Animations (glTF clips)
    Build    one-shot, 2.2 s: the bunker rises, the stripes and rims appear, the
             launcher pops up once and sinks into its hatch
    Idle     loop, 2 s: down in the bunker, a lamp blinks
    Fire     one-shot, 1 s: the launcher rises, fires left and right, sinks back

Run headless:

    blender -b --factory-startup --python blender/NASAM.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). Origin in the
middle of the cell on the ground.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodbuilding as nb  # noqa: E402

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam
HIDDEN = kit.HIDDEN

BOTTOM, TOP, HEIGHT = 0.9, 0.5, 0.17
HATCH = 0.4
TABLE = Vector((0, 0, HEIGHT - 0.1))      # the turntable, down in the hatch
RAISED = 0.2                              # how far the lift raises the launcher
GUN = Vector((0, 0.02, HEIGHT + 0.04))    # the trunnion when down
FIRE_FRAMES = 30


def bunker(m, root):
    """The sloped concrete bunker with its hatch; returns (shell, details)."""
    shell = nb.concrete('Bunker', [
        kit.hexahedron('BunkerBody', m['steel'], (
            (-BOTTOM / 2, -BOTTOM / 2, 0), (BOTTOM / 2, -BOTTOM / 2, 0), (BOTTOM / 2, BOTTOM / 2, 0), (-BOTTOM / 2, BOTTOM / 2, 0),
            (-TOP / 2, -TOP / 2, HEIGHT), (TOP / 2, -TOP / 2, HEIGHT), (TOP / 2, TOP / 2, HEIGHT), (-TOP / 2, TOP / 2, HEIGHT)), bevel=0.015),
    ], root)
    parts = [
        # the hatch: a dark well with a steel collar
        box('Well', m['dark'], (HATCH, HATCH, 0.012), (0, 0, HEIGHT + 0.001), bevel=0),
        cylinder('TableRing', m['steel'], 0.17, 0.02, (0, 0, HEIGHT + 0.004), segments=24, bevel=0.002),
    ]
    for k in range(4):
        a = k * math.pi / 2

        def turn(v):
            v = Vector(v)
            v.rotate(kit.Matrix.Rotation(a, 3, 'Z'))
            return v
        # the hazard stripes on the slope, the red rims at the foot and round the hatch
        slope = math.atan2(HEIGHT, (BOTTOM - TOP) / 2)
        band = nb.stripes(f'Slope{k}', m, (0, 0, 0), (0.52, 0.19, 0.008), 'X', 8)
        normal = Vector((0, -math.sin(slope), math.cos(slope)))
        at = Vector((0, -(BOTTOM + TOP) / 4, HEIGHT / 2)) + normal * 0.005
        band.matrix_world = kit.Matrix.Rotation(a, 4, 'Z') @ kit.Matrix.Translation(at) @ kit.Matrix.Rotation(slope, 4, 'X')
        parts.append(band)
        parts.append(beam(f'FootRim{k}', m['remap'], turn((-BOTTOM / 2 - 0.004, -BOTTOM / 2 - 0.004, 0.012)), turn((BOTTOM / 2 + 0.004, -BOTTOM / 2 - 0.004, 0.012)), 0.025, 0.022))
        parts.append(beam(f'TopRim{k}', m['remap'], turn((-TOP / 2, -TOP / 2 + 0.012, HEIGHT + 0.004)), turn((TOP / 2, -TOP / 2 + 0.012, HEIGHT + 0.004)), 0.024, 0.012))
    parts += [box('Hinge', m['steel'], (0.18, 0.03, 0.03), (0, TOP / 2 - 0.02, HEIGHT + 0.012), bevel=0.004)]
    housing, light = nb.lamp('Lamp', m, (TOP / 2 - 0.03, TOP / 2 - 0.03, HEIGHT))
    return shell, kit.merge('BunkerDetails', parts), housing, light


def launcher(m, mount):
    """Turntable (Turret), Lift, launcher (Cannon) with two flashes; returns (lift, flashes)."""
    turret = kit.parent(kit.empty('Turret', TABLE), mount)
    kit.parent(kit.merge('Table', [
        cylinder('Turntable', m['armour_dark'], 0.15, 0.03, TABLE + Vector((0, 0, 0.015)), segments=24),
        cylinder('Column', m['steel'], 0.05, 0.08, TABLE + Vector((0, 0, 0.04)), segments=14),
    ], TABLE), turret)
    lift = kit.parent(kit.empty('Lift', TABLE), turret)
    # the arm the launcher hangs in, rising with the lift
    kit.parent(kit.merge('Arm', [
        box('ArmPost', m['steel'], (0.05, 0.06, GUN.z - TABLE.z), (0, GUN.y, (TABLE.z + GUN.z) / 2), bevel=0.006),
        *[box(f'Yoke{s}', m['armour'], (0.02, 0.07, 0.07), (s * 0.14, GUN.y, GUN.z), bevel=0.006) for s in (-1, 1)],
        beam('YokeBar', m['steel'], (-0.14, GUN.y, GUN.z - 0.04), (0.14, GUN.y, GUN.z - 0.04), 0.03, 0.02),
    ], TABLE), lift)
    cannon = kit.parent(kit.empty('Cannon', GUN), lift)
    pod = [
        box('Pod', m['armour'], (0.25, 0.3, 0.13), GUN + Vector((0, -0.03, 0.0)), bevel=0.012),
        box('PodTop', m['remap'], (0.252, 0.12, 0.02), GUN + Vector((0, 0.04, 0.06)), bevel=0.004),
        box('PodBack', m['armour_dark'], (0.2, 0.04, 0.1), GUN + Vector((0, 0.13, 0)), bevel=0.008),
        *detail.rivets('PodRivet', m['steel'], GUN + Vector((0.126, -0.15, 0.04)), GUN + Vector((0.126, 0.08, 0.04)), 5, 0.006, 'X'),
        *detail.rivets('PodRivetL', m['steel'], GUN + Vector((-0.126, -0.15, 0.04)), GUN + Vector((-0.126, 0.08, 0.04)), 5, 0.006, 'X'),
    ]
    along = (math.pi / 2, 0, 0)
    front = GUN.y - 0.18
    for i, x in enumerate((-0.06, 0.06)):
        for j, z in enumerate((-0.03, 0.03)):
            c = Vector((x, front, GUN.z + z))
            pod += [
                cylinder(f'Tube{i}{j}', m['dark'], 0.026, 0.02, c, rotation=along, segments=14, bevel=0),
                cylinder(f'TubeRim{i}{j}', m['steel'], 0.03, 0.016, c + Vector((0, 0.004, 0)), rotation=along, segments=14, bevel=0.002),
                cylinder(f'Missile{i}{j}', m['remap'], 0.018, 0.04, c + Vector((0, 0.002, 0)), rotation=along, segments=12, radius2=0.004, bevel=0),
            ]
    kit.parent(kit.merge('Launcher', pod, GUN), cannon)
    flashes = []
    for name, x in (('FlashL', -0.06), ('FlashR', 0.06)):
        flashes.append(kit.parent(nb.glow(m, name, Vector((x, front - 0.05, GUN.z)), 0.05, 'flash'), cannon))
    return lift, flashes


def build():
    root = nb.start('NodSAM', 'NodSAMSite')
    m = nb.materials()
    shell, details, housing, light = bunker(m, root)
    for obj in (shell, details, housing):
        kit.parent(obj, root)
    kit.parent(light, housing)
    mount = kit.parent(kit.empty('Mount', TABLE), root)
    lift, flashes = launcher(m, mount)

    # Build: the bunker rises, the details, the launcher pops up and sinks
    nb.rise(shell, 0, 18, HEIGHT + 0.02)
    nb.rise(details, 4, 18, HEIGHT + 0.04)
    nb.show_at(housing, 26)
    nb.show_at(mount, 24)
    down, up = Vector((0, 0, 0)), Vector((0, 0, RAISED))
    kit.keys(lift, 'location', {0: down, 24: down, 36: up, 52: up, 64: down})
    nb.all_to_build()

    # Idle: down, the lamp blinks
    nb.blinking([(light, kit.flashes((0, 6), (12, 6)))])

    # Fire: up, left, right, down
    kit.keys(lift, 'location', {0: down, 7: up, 22: up, FIRE_FRAMES: down})
    kit.to_track(lift, 'Fire')
    for flash, at in zip(flashes, (8, 13)):
        nb.flash_keys(flash, FIRE_FRAMES, at, at + 4)
        kit.to_track(flash, 'Fire')

    shell.location = details.location = (0, 0, 0)
    lift.location = down
    for flash in flashes:
        flash.scale = (HIDDEN,) * 3
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NASAM', {'Build': [12, 30, 48, 66], 'Idle': [0], 'Fire': [10]}, scale=1.3, target=(0, 0, 0.15))
