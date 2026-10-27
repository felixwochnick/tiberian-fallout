"""
Tiberian Fallout – Nod laser turret (NALASR), after Tiberian Sun.

A slender tower on one cell: a low dark concrete footing with hazard-striped edges, a
sloped armoured pillar wearing red (house colour) chevrons, on top a round domed head
that turns, and from its front the long laser barrel with cooling rings, a capacitor
pipe along its side and a red lens at the tip.

Nodes the game uses (see nodbuilding.py):
    Turret   the head, turning about the vertical
    Cannon   the barrel's trunnion in the head, tipped up and down; looks along -Y
    Flash    the glow at the lens (the beam itself is drawn by the game)
Animations (glTF clips)
    Build    one-shot, 2.2 s: the footing spreads, the pillar grows, the head rises
             onto it, the barrel slides out
    Idle     loop, 2 s: the lens glows softly, a lamp on the head's back blinks
    Fire     one-shot, 0.5 s: the lens flares up, the barrel kicks a little

Run headless:

    blender -b --factory-startup --python blender/NALASR.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). Origin in the
middle of the cell on the ground.
"""
import math
import os
import sys

from mathutils import Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodbuilding as nb  # noqa: E402

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam

FOOT = 0.05
PILLAR_TOP = 0.42
HEAD = Vector((0, 0, PILLAR_TOP))
GUN = Vector((0, -0.05, 0.53))
BARREL = 0.36
FIRE_FRAMES = 15
HIDDEN = kit.HIDDEN


def footing(m, root):
    slab = nb.concrete('Footing', [
        kit.frustum('FootSlab', m['steel'], (0.84, 0.84), (0.78, 0.78), FOOT, (0, 0, 0), bevel=0.012),
        kit.frustum('PillarBase', m['steel'], (0.42, 0.42), (0.34, 0.34), 0.06, (0, 0, FOOT), bevel=0.01),
    ], root)
    parts = []
    for k in range(4):
        a = k * math.pi / 2
        edge = nb.stripes(f'FootStripe{k}', m, (0, 0, 0), (0.72, 0.05, 0.006), 'X', 9)
        edge.location = Vector((0.36 * math.sin(a), -0.36 * math.cos(a), FOOT + 0.003))
        edge.rotation_euler = (0, 0, a)
        parts.append(edge)
    for x in (-1, 1):
        for y in (-1, 1):
            parts.append(cylinder(f'Bolt{x}{y}', m['steel'], 0.02, 0.016, (x * 0.15, y * 0.15, FOOT + 0.06), segments=8, bevel=0))
    return slab, kit.merge('FootingDetails', parts)


def pillar(m):
    """The sloped armour pillar with red chevrons; origin on the footing."""
    z0 = FOOT + 0.06
    body = kit.frustum('PillarBody', m['armour_dark'], (0.3, 0.3), (0.2, 0.2), PILLAR_TOP - z0, (0, 0, z0), bevel=0.012)
    parts = [body]
    h = PILLAR_TOP - z0
    for k in range(4):           # the chevrons on all four faces: two red bands each
        a = k * math.pi / 2
        for j, t in enumerate((0.25, 0.62)):
            z = z0 + h * t
            half = 0.15 - 0.05 * t
            for s in (-1, 1):
                p0 = Vector((s * half * 0.95, -half - 0.004, z - 0.05))
                p1 = Vector((0, -half - 0.004 + 0.0, z + 0.03))
                stripe = beam(f'Chevron{k}{j}{s}', m['remap'], p0, p1, 0.04, 0.008)
                q = stripe.rotation_quaternion.copy()
                rot = Quaternion((0, 0, 1), a)
                stripe.location = rot @ stripe.location
                stripe.rotation_quaternion = rot @ q
                parts.append(stripe)
    parts += detail.ladder('Ladder', m['steel'], (0.0, 0.135, z0), (0.0, 0.1, PILLAR_TOP - 0.02), 0.05, 6)
    parts += [box('CableBox', m['steel'], (0.08, 0.04, 0.07), (0.1, 0.13, z0 + 0.08), bevel=0.006)]
    parts += detail.hose('Cable', m['dark'], (0.1, 0.15, z0 + 0.1), (0.13, 0.18, 0.3), (0.06, 0.1, PILLAR_TOP - 0.01), 0.008)
    return kit.merge('Pillar', parts, (0, 0, z0))


def head(m, mount):
    """The domed head on the node Turret, the gun on Cannon; returns (barrel, flash, lens glow, lamp)."""
    turret = kit.parent(kit.empty('Turret', HEAD), mount)
    shell = [
        cylinder('HeadRing', m['steel'], 0.13, 0.03, HEAD + Vector((0, 0, 0.015)), segments=20),
        kit.frustum('HeadBody', m['armour'], (0.26, 0.3), (0.22, 0.26), 0.1, HEAD + Vector((0, 0.01, 0.03)), bevel=0.015),
        sphere('Dome', m['armour'], 0.125, HEAD + Vector((0, 0.03, 0.125)), 20),
        box('HeadBand', m['remap'], (0.268, 0.2, 0.025), HEAD + Vector((0, 0.04, 0.085)), bevel=0.005),
        box('Visor', m['glass'], (0.1, 0.02, 0.025), HEAD + Vector((0.06, -0.135, 0.11)), bevel=0.004),
        *detail.grille('BackVent', m['steel'], m['dark'], HEAD + Vector((0, 0.165, 0.08)), 0.1, 0.05, 'Y', 3, 0.008),
        box('SidePod', m['armour_dark'], (0.05, 0.14, 0.07), HEAD + Vector((0.14, 0.02, 0.08)), bevel=0.008),
        box('SidePod2', m['armour_dark'], (0.05, 0.14, 0.07), HEAD + Vector((-0.14, 0.02, 0.08)), bevel=0.008),
    ]
    dome = shell[2]
    dome.scale = (1.0, 1.15, 0.7)
    kit.parent(kit.merge('Head', shell, HEAD), turret)
    housing, light = nb.lamp('HeadLamp', m, HEAD + Vector((-0.14, 0.05, 0.115)))
    kit.parent(housing, turret)
    kit.parent(light, turret)

    cannon = kit.parent(kit.empty('Cannon', GUN), turret)
    tip = GUN - Vector((0, BARREL, 0))
    along = (math.pi / 2, 0, 0)
    parts = [
        cylinder('Breech', m['armour_dark'], 0.05, 0.1, GUN - Vector((0, 0.04, 0)), rotation=along, segments=16),
        cylinder('Tube', m['steel'], 0.022, BARREL, GUN - Vector((0, BARREL / 2 + 0.02, 0)), rotation=along, segments=14),
        cylinder('Emitter', m['armour_dark'], 0.03, 0.06, tip + Vector((0, 0.01, 0)), rotation=along, segments=14),
        cylinder('Lens', m['lamp_red'], 0.02, 0.012, tip - Vector((0, 0.022, 0)), rotation=along, segments=14, bevel=0),
        beam('Capacitor', m['steel_light'], GUN + Vector((0.035, -0.06, 0.03)), tip + Vector((0.03, 0.08, 0.025)), 0.018),
        beam('CapacitorRed', m['remap'], GUN + Vector((0.035, -0.08, 0.03)), GUN + Vector((0.035, -0.14, 0.03)), 0.022),
    ]
    for k in range(5):
        y = GUN.y - 0.12 - k * 0.04
        parts.append(cylinder(f'Ring{k}', m['steel_light'], 0.03, 0.012, Vector((0, y, GUN.z)), rotation=along, segments=14, bevel=0))
    barrel = kit.parent(kit.merge('Barrel', parts, GUN), cannon)
    lens_glow = kit.parent(nb.glow(m, 'LensGlow', tip - Vector((0, 0.03, 0)), 0.03, 'glow_laser', 1), barrel)
    flash = kit.parent(nb.glow(m, 'Flash', tip - Vector((0, 0.035, 0)), 0.045, 'glow_laser'), cannon)
    return barrel, flash, lens_glow, light


def build():
    root = nb.start('NodLaser', 'NodLaserTurret')
    m = nb.materials()
    slab, slab_details = footing(m, root)
    for obj in (slab, slab_details):
        kit.parent(obj, root)
    column = kit.parent(pillar(m), root)
    mount = kit.parent(kit.empty('Mount', HEAD), root)
    barrel, flash, lens_glow, light = head(m, mount)

    # Build: footing, pillar, head, barrel
    for obj in (slab, slab_details):
        s = obj.scale.copy()
        kit.keys(obj, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 12: Vector((1.04, 1.04, 1)), 15: s})
    nb.grow_z(column, 10, 18)
    nb.rise(mount, 28, 14, 0.32)
    kit.keys(mount, 'scale', {0: Vector((HIDDEN,) * 3), 27: Vector((HIDDEN,) * 3), 28: Vector((1, 1, 1))}, 'CONSTANT')
    rest = barrel.location.copy()
    short = Vector((1, HIDDEN, 1))
    kit.keys(barrel, 'scale', {0: short, 44: short, 58: Vector((1, 1.04, 1)), 62: Vector((1, 1, 1))})
    nb.all_to_build()

    # Idle: the lens glows softly, the lamp blinks
    kit.keys(lens_glow, 'scale', {f: Vector((1, 1, 1)) * (0.75 + 0.25 * math.sin(2 * math.pi * f / kit.IDLE_END)) for f in range(0, kit.IDLE_END + 1, 5)}, 'LINEAR')
    kit.to_track(lens_glow, 'Idle')
    nb.blinking([(light, kit.flashes((0, 8), (30, 8)))])

    # Fire: the lens flares, the barrel kicks
    nb.flash_keys(flash, FIRE_FRAMES, 1, 7)
    kit.to_track(flash, 'Fire')
    kit.keys(lens_glow, 'scale', {0: Vector((1.6, 1.6, 1.6)), 6: Vector((1.3, 1.3, 1.3)), FIRE_FRAMES: Vector((0.75, 0.75, 0.75))}, 'LINEAR')
    kit.to_track(lens_glow, 'Fire')
    kit.keys(barrel, 'location', {0: rest, 2: rest + Vector((0, 0.015, 0)), 9: rest, FIRE_FRAMES: rest})
    kit.to_track(barrel, 'Fire')

    barrel.location = rest
    barrel.scale = (1, 1, 1)
    flash.scale = (HIDDEN,) * 3
    lens_glow.scale = (0.75,) * 3
    light.scale = (1, 1, 1)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NALASR', {'Build': [20, 40, 66], 'Idle': [0], 'Fire': [3]}, scale=1.3, target=(0, 0, 0.32))
