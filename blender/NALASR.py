"""
Tiberian Fallout – Nod laser turret (NALASR), after Tiberian Sun.

A slender tower on one cell, like the original's: a low dark footing and on it a
leaning wedge of armour plate in two stages – steep at the front (-Y) and on the left
(-X), where it wears red (house colour) plates with black diagonal stripes, and sloping
down to the back right (+X, +Y) in black, with vents, a ladder and a cable. On its flat
top turns the laser head: a collar, an angular grey housing with a red stripe and a
visor, and the long barrel with cooling rings, a capacitor along its side and a lens at
the tip.

Nodes the game uses (see nodstructure.py):
    Turret     the head, turning about the vertical
    Cannon     the barrel's trunnion in the head, tipped up and down; looks along -Y
    Flash      the flare at the lens (the beam itself is drawn by the game)
Other nodes
    Mount      above Turret: brings the head down onto the tower (Build)
    Recoil     inside Cannon, carries the barrel: kicks back a little (Fire)
    LensGlow   on Cannon at the lens: glows softly (Idle)
    LensFlare  on Cannon at the lens: flares up (Fire)
Animations (glTF clips)
    Build    one-shot, 2.2 s: the footing spreads, the tower grows, the head is
             lowered onto it
    Idle     loop, 2 s: the lens glows softly, a lamp on the head and one on the
             tower blink
    Fire     one-shot, 0.5 s: the lens flares up, the barrel kicks a little

Run headless:

    blender -b --factory-startup --python blender/NALASR.py [-- --preview <dir>]

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
import nodstructure as nb  # noqa: E402

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam
HIDDEN = kit.HIDDEN

FOOT = 0.035
# the tower's outlines (counter-clockwise from front left) at three heights
BASE = [(-0.2, -0.22), (0.26, -0.22), (0.26, 0.24), (-0.2, 0.24)]
MID_Z = 0.26
MID = [(-0.19, -0.19), (0.1, -0.19), (0.1, 0.17), (-0.19, 0.17)]
TOP_Z = 0.56
TOP = [(-0.18, -0.15), (0.0, -0.15), (0.0, 0.12), (-0.18, 0.12)]
HEAD = Vector((-0.09, -0.015, TOP_Z))          # the turret's pivot on the tower's top
GUN = HEAD + Vector((0, -0.02, 0.115))      # the trunnion
BARREL = 0.44
TIP = GUN - Vector((0, 0.06 + BARREL, 0))   # the lens
FIRE_FRAMES = 15
BUILD_END = 66


def lerp(a, b, t):
    return a + (b - a) * t


def patch(quad, u0, u1, v0, v1, lift, thick, shear=0.0):
    """Corners of a plate on a face given by `quad` (bottom left, bottom right, top
    right, top left): the part u0..u1 across, v0..v1 up, its top edge shifted by
    `shear` across; lifted off the face by `lift`, `thick` thick."""
    bl, br, tr, tl = (Vector(p) for p in quad)
    normal = (br - bl).cross(tl - bl).normalized()

    def at(u, v):
        return lerp(lerp(bl, br, u), lerp(tl, tr, u), v)
    flat = [at(u0, v0), at(u1, v0), at(u1 + shear, v1), at(u0 + shear, v1)]
    return [p + normal * lift for p in flat] + [p + normal * (lift + thick) for p in flat]


def outward(quad, centre):
    """The quad in the order whose normal points away from `centre`."""
    bl, br, tr, tl = (Vector(p) for p in quad)
    if (br - bl).cross(tl - bl).dot((bl + tr) / 2 - Vector(centre)) < 0:
        return [br, bl, tl, tr]
    return [bl, br, tr, tl]


def face(lower, upper, z0, z1, k):
    """Side k (0 front -Y, 1 right +X, 2 back +Y, 3 left -X) between two outlines."""
    j = (k + 1) % 4
    return [Vector((*lower[k], z0)), Vector((*lower[j], z0)), Vector((*upper[j], z1)), Vector((*upper[k], z1))]


def tower(m, root):
    """Footing (concrete), the wedge with its plates (one object), the details."""
    footing = nb.concrete('Footing', [
        kit.frustum('FootSlab', m['steel'], (0.62, 0.62), (0.56, 0.56), FOOT, (0.02, 0.01, 0), bevel=0.01),
    ], root, 'dark')
    foot_parts = []
    for x in (-1, 1):
        for y in (-1, 1):
            foot_parts.append(cylinder(f'Bolt{x}{y}', m['steel'], 0.018, 0.014, (0.02 + x * 0.25, 0.01 + y * 0.25, FOOT + 0.007), segments=8, bevel=0))
    for k, (a, b) in enumerate((((-0.29, -0.3), (0.33, -0.3)), ((0.33, -0.3), (0.33, 0.32)))):
        foot_parts.append(beam(f'FootTrim{k}', m['remap'], (*a, FOOT * 0.5), (*b, FOOT * 0.5), 0.012, FOOT * 0.8))
    foot_details = kit.merge('FootingDetails', foot_parts)

    parts = [
        nb.prism('TowerLow', m['armour_dark'], BASE, MID, FOOT, MID_Z, bevel=0.008),
        nb.prism('TowerHigh', m['armour_dark'], MID, TOP, MID_Z, TOP_Z, bevel=0.008),
        nb.prism('TopCap', m['steel'], [(x * 0.97 - 0.003, y * 0.97 - 0.001) for x, y in TOP], [(x * 0.9 - 0.009, y * 0.9 - 0.002) for x, y in TOP],
                 TOP_Z - 0.002, TOP_Z + 0.012, bevel=0.003),
    ]
    centre = (-0.04, 0, 0.28)
    stages = ((BASE, MID, FOOT, MID_Z), (MID, TOP, MID_Z, TOP_Z))
    for s, (lower, upper, z0, z1) in enumerate(stages):
        for k in (0, 3):           # red plates with black stripes: front and left
            quad = outward(face(lower, upper, z0, z1, k), centre)
            parts.append(kit.hexahedron(f'Plate{s}{k}', m['remap'], patch(quad, 0.04, 0.96, 0.05, 0.95, 0.001, 0.01), bevel=0.003))
            for n in range(2):
                u = 0.2 + 0.36 * n
                parts.append(kit.hexahedron(f'Stripe{s}{k}{n}', m['nplate_dark'],
                                            patch(quad, u, u + 0.07, 0.1, 0.9, 0.009, 0.006, shear=0.14), bevel=0))
        for k in (1, 2):           # black side and back: seams and plates
            quad = outward(face(lower, upper, z0, z1, k), centre)
            parts.append(kit.hexahedron(f'Panel{s}{k}', m['nplate'], patch(quad, 0.08, 0.92, 0.1, 0.9, 0.001, 0.008), bevel=0.003))
    # a vent on the sloping right face, a band of red at the top's edge
    right = outward(face(MID, TOP, MID_Z, TOP_Z, 1), centre)
    parts.append(kit.hexahedron('Vent', m['dark'], patch(right, 0.25, 0.75, 0.3, 0.7, 0.008, 0.006), bevel=0))
    for n in range(4):
        v = 0.33 + 0.1 * n
        parts.append(kit.hexahedron(f'VentSlat{n}', m['steel'], patch(right, 0.24, 0.76, v, v + 0.035, 0.012, 0.008), bevel=0))
    tower_obj = kit.merge('Tower', parts, (0, 0, FOOT))

    details = []
    back = outward(face(BASE, MID, FOOT, MID_Z, 2), centre)
    bl, br = back[0], back[1]
    details += detail.ladder('Ladder', m['steel'], lerp(bl, br, 0.5) + Vector((0, 0.025, 0)), Vector((lerp(bl.x, br.x, 0.5), 0.195, MID_Z)), 0.06, 5)
    details += [box('CableBox', m['steel'], (0.07, 0.04, 0.07), (0.16, 0.27, FOOT + 0.035), bevel=0.006)]
    details += detail.hose('Cable', m['dark'], (0.16, 0.27, FOOT + 0.07), (0.12, 0.22, 0.3), (-0.02, 0.13, TOP_Z - 0.02), 0.01)
    tower_details = kit.merge('TowerDetails', details)
    return footing, foot_details, tower_obj, tower_details


def head(m, mount):
    """The turning head (Turret), the gun (Cannon → Recoil → Barrel); returns the
    animated parts."""
    turret = kit.parent(kit.empty('Turret', HEAD), mount)
    z = HEAD.z
    shell = [
        cylinder('Collar', m['steel'], 0.1, 0.03, HEAD + Vector((0, 0, 0.027)), segments=20),
        # an angular housing, narrower at the top, its nose at the front
        nb.prism('Housing', m['armour'],
                 [(-0.09, -0.11), (0.09, -0.11), (0.1, 0.1), (-0.1, 0.1)],
                 [(-0.065, -0.07), (0.065, -0.07), (0.075, 0.08), (-0.075, 0.08)], z + 0.042, z + 0.19, bevel=0.01),
        nb.prism('HousingStripe', m['remap'],
                 [(-0.092, -0.045), (0.092, -0.045), (0.098, 0.0), (-0.098, 0.0)],
                 [(-0.085, -0.03), (0.085, -0.03), (0.092, 0.012), (-0.092, 0.012)], z + 0.08, z + 0.115, bevel=0.002),
        box('Visor', m['glass'], (0.09, 0.012, 0.022), HEAD + Vector((0, -0.105, 0.155)), bevel=0.003),
        *detail.grille('BackVent', m['steel'], m['dark'], HEAD + Vector((0, 0.1, 0.11)), 0.1, 0.05, 'Y', 3, 0.008),
        box('Cheek+', m['armour_dark'], (0.03, 0.12, 0.08), HEAD + Vector((0.095, -0.02, GUN.z - HEAD.z)), bevel=0.006),
        box('Cheek-', m['armour_dark'], (0.03, 0.12, 0.08), HEAD + Vector((-0.095, -0.02, GUN.z - HEAD.z)), bevel=0.006),
    ]
    kit.parent(kit.merge('Head', shell, HEAD), turret)
    head_light = nb.lamp(m, turret, 'HeadLamp', HEAD + Vector((0.05, 0.06, 0.19)), 'red', 52)

    cannon = kit.parent(kit.empty('Cannon', GUN), turret)
    recoil = kit.parent(kit.empty('Recoil', GUN), cannon)
    along = (math.pi / 2, 0, 0)
    tube_mid = GUN - Vector((0, 0.06 + BARREL / 2, 0))
    parts = [
        cylinder('Breech', m['armour_dark'], 0.045, 0.14, GUN - Vector((0, 0.0, 0)), rotation=along, segments=16),
        cylinder('Tube', m['steel'], 0.02, BARREL, tube_mid, rotation=along, segments=14),
        cylinder('Shroud', m['armour'], 0.032, 0.16, GUN - Vector((0, 0.15, 0)), rotation=along, segments=16, bevel=0.004),
        cylinder('Emitter', m['armour_dark'], 0.03, 0.05, TIP + Vector((0, 0.025, 0)), rotation=along, segments=14),
        cylinder('EmitterRim', m['remap'], 0.032, 0.012, TIP + Vector((0, 0.044, 0)), rotation=along, segments=14, bevel=0),
        cylinder('Lens', m['lamp_red'], 0.02, 0.008, TIP + Vector((0, -0.002, 0)), rotation=along, segments=14, bevel=0),
        beam('Capacitor', m['steel_light'], GUN + Vector((0.034, -0.08, 0.026)), TIP + Vector((0.026, 0.09, 0.022)), 0.016),
        beam('CapacitorRed', m['remap'], GUN + Vector((0.034, -0.09, 0.026)), GUN + Vector((0.034, -0.15, 0.026)), 0.02),
    ]
    for k in range(6):
        y = GUN.y - 0.25 - k * 0.035
        parts.append(cylinder(f'Ring{k}', m['steel_light'], 0.027, 0.01, Vector((GUN.x, y, GUN.z)), rotation=along, segments=14, bevel=0))
    barrel = kit.parent(kit.merge('Barrel', parts, GUN), recoil)
    lens_glow = kit.parent(nb.glow(m, 'LensGlow', TIP - Vector((0, 0.008, 0)), 0.026, 'glow_laser', 1), cannon)
    lens_flare = kit.parent(nb.glow(m, 'LensFlare', TIP - Vector((0, 0.01, 0)), 0.045, 'glow_laser', 1), cannon)
    flash = kit.parent(nb.glow(m, 'Flash', TIP - Vector((0, 0.03, 0)), 0.05, 'glow_laser'), cannon)
    return barrel, recoil, flash, lens_glow, lens_flare, head_light


def build():
    root = nb.start('NodLaser', 'NodLaserTurret', BUILD_END)
    m = nb.materials()
    footing, foot_details, tower_obj, tower_details = tower(m, root)
    for obj in (footing, foot_details, tower_obj, tower_details):
        kit.parent(obj, root)
    tower_light = nb.lamp(m, root, 'TowerLamp', (-0.23, -0.25, FOOT), 'red', 34)
    mount = kit.parent(kit.empty('Mount', HEAD), root)
    barrel, recoil, flash, lens_glow, lens_flare, head_light = head(m, mount)

    # Build: the footing spreads, the tower grows, the head comes down
    for obj in (footing, foot_details):
        s = obj.scale.copy()
        kit.keys(obj, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 10: Vector((1.04, 1.04, 1)), 13: s})
    nb.grow_z(tower_obj, 8, 20)
    nb.grow_z(tower_details, 16, 14)
    # the head waits under the ground, then is lowered from above (never scaled: the
    # lamps and glows under it blink in Idle)
    kit.keys(mount, 'location', {0: HEAD - Vector((0, 0, 1.5)), 31: HEAD - Vector((0, 0, 1.5))}, 'CONSTANT')
    kit.keys(mount, 'location', {32: HEAD + Vector((0, 0, 0.45)), 46: HEAD - Vector((0, 0, 0.004)), 49: HEAD})
    nb.all_to_build()

    # Idle: the lens glows softly, the lamps blink
    nb.pulse(lens_glow, kit.IDLE_END, 0.75, 1.1)
    kit.to_track(lens_glow, 'Idle')
    nb.blinking([(head_light, kit.flashes((0, 8), (30, 8))), (tower_light, kit.flashes((15, 10)))])

    # Fire: the lens flares, the barrel kicks
    nb.flash_keys(flash, FIRE_FRAMES, 1, 7)
    kit.to_track(flash, 'Fire')
    hidden = Vector((HIDDEN,) * 3)
    kit.keys(lens_flare, 'scale', {0: hidden, 1: Vector((1.5,) * 3), 6: Vector((1.2,) * 3), 12: hidden, FIRE_FRAMES: hidden}, 'LINEAR')
    kit.to_track(lens_flare, 'Fire')
    rest = recoil.location.copy()
    kit.keys(recoil, 'location', {0: rest, 2: rest + Vector((0, 0.02, 0)), 9: rest, FIRE_FRAMES: rest})
    kit.to_track(recoil, 'Fire')

    recoil.location = rest
    mount.location = HEAD
    flash.scale = lens_flare.scale = (HIDDEN,) * 3
    lens_glow.scale = (1, 1, 1)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NALASR', {'Build': [20, 40, 66], 'Idle': [0], 'Fire': [3, FIRE_FRAMES]}, ortho=1.3, target=(0, 0, 0.32))
