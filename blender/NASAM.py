"""
Tiberian Fallout – Nod SAM site (NASAM), after Tiberian Sun.

A low, flat pyramid of dark concrete on one cell standing on a red (house colour)
skirt, its slopes painted with rows of yellow and black hazard stripes; in the middle
of its top a grey dome, and on the dome – always up, as in the original (TurretAnim
NASAM_A) – the turning launcher: a turntable with a yoke, in it a dark box with two rows
of four tubes in its face (red missile tips), round trunnion drums on its sides, a red
band over its top and a sensor with a lamp at its back.

Nodes the game uses (see nodstructure.py):
    Turret           the turntable with the yoke, turning about the vertical
    Cannon           the launcher's trunnion, tipped up and down; the tubes look along -Y
    FlashL, FlashR   the glows at the left and the right tubes (shots alternate)
Other nodes
    Mount            above Turret: brings the launcher down onto the dome (Build)
    Recoil           inside Cannon, carries the box: kicks back at each shot (Fire)
Animations (glTF clips)
    Build    one-shot, 2.2 s: skirt and pyramid grow, the stripes, the dome pops up,
             the launcher is lowered onto it
    Idle     loop, 2 s: a lamp on the bunker and one on the sensor blink
    Fire     one-shot, 1 s: left, then right – flash and kick

Run headless:

    blender -b --factory-startup --python blender/NASAM.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). Origin in the
middle of the cell on the ground.
"""
import math
import os
import sys

from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodstructure as nb  # noqa: E402

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam
HIDDEN = kit.HIDDEN

SKIRT = 0.05                              # the red skirt's height
BOTTOM, TOP, HEIGHT = 0.8, 0.38, 0.16    # the pyramid (HEIGHT: its top)
DOME = 0.15                               # the dome's radius
TABLE = Vector((0, 0, HEIGHT + 0.085))    # the turntable on the dome
GUN = Vector((0, 0, 0.4))                 # the trunnion
BOX = (0.32, 0.3, 0.17)                   # the launcher box (width, depth, height)
FRONT = GUN.y - BOX[1] / 2
FIRE_FRAMES = 30
BUILD_END = 66


def bunker(m, root):
    """The pyramid (concrete) and its skirt, stripes, dome; returns (shell, details, dome)."""
    shell = nb.concrete('Bunker', [
        kit.frustum('BunkerBody', m['steel'], (BOTTOM, BOTTOM), (TOP, TOP), HEIGHT - SKIRT, (0, 0, SKIRT), bevel=0.012),
    ], root, 'dark')
    parts = [
        kit.frustum('Skirt', m['remap'], (BOTTOM + 0.08, BOTTOM + 0.08), (BOTTOM + 0.02, BOTTOM + 0.02), SKIRT, (0, 0, 0), bevel=0.006),
        kit.frustum('TopPlate', m['nplate'], (TOP - 0.01, TOP - 0.01), (TOP - 0.04, TOP - 0.04), 0.014, (0, 0, HEIGHT - 0.002), bevel=0.004),
    ]
    run = (BOTTOM - TOP) / 2
    slope = math.atan2(HEIGHT - SKIRT, run)
    slant = math.hypot(HEIGHT - SKIRT, run)
    normal = Vector((0, -math.sin(slope), math.cos(slope)))
    for k in range(4):
        turn = Matrix.Rotation(k * math.pi / 2, 4, 'Z')
        # two rows of hazard stripes up each slope, cut to the face's width
        for row, t in enumerate((0.2, 0.5, 0.8)):
            width = 0.075 * slant / 0.27
            top_edge = t + 0.5 * width / slant
            length = BOTTOM - (BOTTOM - TOP) * top_edge - 0.05
            band = nb.stripes(f'Slope{k}{row}', m, (0, 0, 0), (length, width, 0.008), 'X', max(4, round(length / 0.05)))
            at = Vector((0, -BOTTOM / 2 + run * t, SKIRT + (HEIGHT - SKIRT) * t)) + normal * 0.004
            band.matrix_world = turn @ Matrix.Translation(at) @ Matrix.Rotation(slope, 4, 'X')
            parts.append(band)
        # a red line along the top edge
        a, b = turn @ Vector((-TOP / 2 + 0.01, -TOP / 2 + 0.006, HEIGHT + 0.004)), turn @ Vector((TOP / 2 - 0.01, -TOP / 2 + 0.006, HEIGHT + 0.004))
        parts.append(beam(f'TopRim{k}', m['remap'], a, b, 0.016, 0.012))
    for x in (-1, 1):
        for y in (-1, 1):
            parts.append(cylinder(f'Bolt{x}{y}', m['steel'], 0.014, 0.012, (x * (TOP / 2 - 0.045), y * (TOP / 2 - 0.045), HEIGHT + 0.016), segments=8, bevel=0))
    details = kit.merge('BunkerDetails', parts)

    dome_parts = [
        cylinder('DomeRing', m['steel'], DOME + 0.012, 0.02, (0, 0, HEIGHT + 0.02), segments=28),
        sphere('Dome', m['nsteel_light'], DOME, (0, 0, HEIGHT + 0.025), 24),
    ]
    dome_parts[1].scale = (1, 1, 0.5)
    dome = kit.merge('Dome', dome_parts, (0, 0, HEIGHT + 0.012))
    return shell, details, dome


def launcher(m, mount):
    """Turntable and yoke (Turret), the box (Cannon → Recoil); returns (recoil, flashes, light)."""
    turret = kit.parent(kit.empty('Turret', TABLE), mount)
    arm_x = BOX[0] / 2 + 0.06
    yoke = [
        cylinder('Turntable', m['armour_dark'], 0.08, 0.03, TABLE + Vector((0, 0, 0.0)), segments=20),
        cylinder('Pivot', m['steel'], 0.05, 0.03, TABLE + Vector((0, 0, 0.025)), segments=14),
        box('YokeBase', m['armour'], (2 * arm_x + 0.03, 0.08, 0.025), TABLE + Vector((0, 0, 0.045)), bevel=0.005),
    ]
    for s in (-1, 1):
        x = s * arm_x
        yoke += [
            box(f'Arm{s}', m['armour'], (0.03, 0.08, GUN.z - TABLE.z - 0.03), Vector((x, 0, (TABLE.z + 0.045 + GUN.z) / 2)), bevel=0.006),
            cylinder(f'ArmHub{s}', m['steel'], 0.03, 0.012, Vector((x + s * 0.016, 0, GUN.z)), rotation=(0, math.pi / 2, 0), segments=12, bevel=0.002),
        ]
    kit.parent(kit.merge('Yoke', yoke, TABLE), turret)

    cannon = kit.parent(kit.empty('Cannon', GUN), turret)
    recoil = kit.parent(kit.empty('Recoil', GUN), cannon)
    w, d, h = BOX
    along = (math.pi / 2, 0, 0)
    side = (0, math.pi / 2, 0)
    pod = [
        box('Box', m['armour'], BOX, GUN, bevel=0.014),
        box('FacePlate', m['armour_dark'], (w - 0.03, 0.012, h - 0.03), Vector((0, FRONT - 0.002, GUN.z)), bevel=0.003),
        box('Band', m['remap'], (w + 0.004, 0.09, 0.012), GUN + Vector((0, -0.04, h / 2 - 0.004)), bevel=0.003),
        box('BackPlate', m['armour_dark'], (w - 0.06, 0.02, h - 0.06), GUN + Vector((0, d / 2 + 0.008, 0)), bevel=0.004),
        # the sensor at the back: a red block and a grey drum
        box('SensorBase', m['remap'], (0.07, 0.07, 0.04), GUN + Vector((0.09, 0.08, h / 2 + 0.018)), bevel=0.005),
        cylinder('Sensor', m['steel_light'], 0.032, 0.05, GUN + Vector((0.09, 0.08, h / 2 + 0.06)), rotation=side, segments=14, bevel=0.003),
        *detail.rivets('RivetL', m['steel'], GUN + Vector((-w / 2 - 0.002, -0.12, h / 2 - 0.025)), GUN + Vector((-w / 2 - 0.002, 0.12, h / 2 - 0.025)), 5, 0.005, 'X'),
        *detail.rivets('RivetR', m['steel'], GUN + Vector((w / 2 + 0.002, -0.12, h / 2 - 0.025)), GUN + Vector((w / 2 + 0.002, 0.12, h / 2 - 0.025)), 5, 0.005, 'X'),
    ]
    for s in (-1, 1):   # the trunnion drums on the sides
        x = s * (w / 2 + 0.02)
        pod += [cylinder(f'Drum{s}', m['armour_dark'], 0.062, 0.04, Vector((x, 0, GUN.z)), rotation=side, segments=20, bevel=0.004),
                cylinder(f'DrumCap{s}', m['steel'], 0.035, 0.044, Vector((x, 0, GUN.z)), rotation=side, segments=16, bevel=0.002)]
    columns = (-0.111, -0.037, 0.037, 0.111)
    for i, x in enumerate(columns):
        for j, z in enumerate((-0.037, 0.037)):
            c = Vector((x, FRONT - 0.008, GUN.z + z))
            pod += [
                cylinder(f'TubeRim{i}{j}', m['steel'], 0.028, 0.012, c, rotation=along, segments=14, bevel=0.002),
                cylinder(f'Tube{i}{j}', m['dark'], 0.021, 0.006, c - Vector((0, 0.004, 0)), rotation=along, segments=14, bevel=0),
                cylinder(f'Missile{i}{j}', m['remap'], 0.015, 0.02, c + Vector((0, -0.006, 0)), rotation=along, segments=12, radius2=0.004, bevel=0),
            ]
    kit.parent(kit.merge('Launcher', pod, GUN), recoil)
    light = nb.lamp(m, cannon, 'SensorLamp', GUN + Vector((0.09, 0.08, h / 2 + 0.09)), 'red', 54)
    flashes = []
    for name, x in (('FlashL', -0.074), ('FlashR', 0.074)):
        flashes.append(kit.parent(nb.glow(m, name, Vector((x, FRONT - 0.04, GUN.z)), 0.05, 'flash'), cannon))
    return recoil, flashes, light


def build():
    root = nb.start('NodSAM', 'NodSAMSite', BUILD_END)
    m = nb.materials()
    shell, details, dome = bunker(m, root)
    for obj in (shell, details, dome):
        kit.parent(obj, root)
    base_light = nb.lamp(m, root, 'Lamp', (TOP / 2 - 0.035, TOP / 2 - 0.035, HEIGHT + 0.012), 'red', 30)
    mount = kit.parent(kit.empty('Mount', TABLE), root)
    recoil, flashes, sensor_light = launcher(m, mount)

    # Build: the bunker grows, the dome pops up, the launcher is lowered onto it
    nb.grow_z(shell, 0, 16)
    nb.grow_z(details, 4, 16)
    kit.pop(dome, 22, 8)
    kit.keys(mount, 'location', {0: TABLE - Vector((0, 0, 1.5)), 33: TABLE - Vector((0, 0, 1.5))}, 'CONSTANT')
    kit.keys(mount, 'location', {34: TABLE + Vector((0, 0, 0.45)), 50: TABLE - Vector((0, 0, 0.004)), 54: TABLE})
    nb.all_to_build()

    # Idle: the lamps blink
    nb.blinking([(base_light, kit.flashes((0, 6), (12, 6))), (sensor_light, kit.flashes((30, 10)))])

    # Fire: left, then right – each a flash and a kick
    rest = recoil.location.copy()
    back = Vector((0, 0.018, 0))
    kit.keys(recoil, 'location', {0: rest, 4: rest, 5: rest + back, 11: rest, 15: rest, 16: rest + back, 23: rest, FIRE_FRAMES: rest})
    kit.to_track(recoil, 'Fire')
    for flash, at in zip(flashes, (4, 15)):
        nb.flash_keys(flash, FIRE_FRAMES, at, at + 5)
        kit.to_track(flash, 'Fire')

    mount.location = TABLE
    recoil.location = rest
    for flash in flashes:
        flash.scale = (HIDDEN,) * 3
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NASAM', {'Build': [12, 30, 44, 66], 'Idle': [0], 'Fire': [6, 17, FIRE_FRAMES]}, ortho=1.3, target=(0, 0, 0.18))
