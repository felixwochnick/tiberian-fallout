"""
Tiberian Fallout – Tiberium silo (GASILO), after Tiberian Sun (built by GDI and Nod,
in the GDI style).

A round, squat tank (foundation 2 × 2 cells): a sloped camouflaged skirt on a dark
octagonal footing, a shallow blue-grey steel dome on it with a hatch in the middle.
Eight jagged fins in the house colour run like lightning from the hatch over the
dome and down the skirt to the ground, star-like. Between them, low in the skirt,
green windows glow with the Tiberium inside. At the front right a grey pump unit with
pipes into the tank.

Materials as for the barracks (see GAPILE.py): Camo_* is the baked camouflage in a
pale shade of the house colour, Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.2 s: the footing spreads, the tank rises out of the ground, the
             dome closes over it, the fins shoot out one after another, the pump and
             the lights appear
    Idle     loop, 2 s: the Tiberium glow in the windows swells and fades, the
             beacons blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GASILO.py [-- --preview 0,30,66 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -1 … 1 and y -1 … 1.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import gdibuilding as gb  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GASILO.glb')
BLEND = os.path.join(HERE, 'GASILO.blend')

BUILD_END = 66
FOOT = 0.03
SKIRT = ((0.86, FOOT), (0.86, FOOT + 0.05), (0.72, 0.3), (0.7, 0.31))
DOME = ((0.7, 0.31), (0.66, 0.35), (0.52, 0.405), (0.3, 0.44), (0.12, 0.452), (0.001, 0.455))
FINS = 8
FIN_ANGLE = math.pi / 8           # leaves a gap at the front right for the pump
PUMP = Vector((0.6, -0.6, FOOT))
# a fin's outline (radius, height): over the dome, a jag out, down the skirt to the ground
FIN = ((0.12, 0.52), (0.5, 0.5), (0.7, 0.46), (1.0, 0.43), (0.84, 0.33), (0.99, 0.22), (0.84, 0.15), (0.93, FOOT),
       (0.74, FOOT), (0.74, 0.1), (0.68, 0.29), (0.5, 0.39), (0.12, 0.44))
FIN_WIDTH = 0.065

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m['roof'] = material('SiloRoof', srgb('#7d879a'), 0.4, 0.75)
    m['tiberium'] = material('LampTiberium', srgb('#60ff70'), 0.3, emission=srgb('#40ff50'), strength=6)
    return m


def radial(a, r, z):
    return Vector((math.cos(a) * r, math.sin(a) * r, z))


# --------------------------------------------------------------------------- parts

def footing(m):
    outline = [(math.cos(a) * 0.97, math.sin(a) * 0.97) for a in (math.pi / 8 + k * math.pi / 4 for k in range(8))]
    parts = [gb.slab('Footing', m['concrete_dark'], outline, FOOT, inset=0.01, bevel=0.004)]
    parts.append(box('PumpPad', m['concrete'], (0.36, 0.36, 0.012), PUMP + Vector((0, 0, 0.006)), bevel=0.003, rotation=(0, 0, -math.pi / 4)))
    return kit.merge('Footing', parts)


def tank(m, root):
    """The camouflaged skirt; the steel band at its foot, the windows."""
    skirt = gb.camo(gb.lathe('Skirt', m['sand'], SKIRT, (0, 0, 0), 48), root)
    parts = [cylinder('SkirtBand', m['steel'], SKIRT[0][0] + 0.008, 0.03, (0, 0, FOOT + 0.035), segments=48, bevel=0)]
    windows = []
    for k in range(FINS):  # one window between each two fins
        a = FIN_ANGLE + (k + 0.5) * 2 * math.pi / FINS
        r, z = 0.8, 0.15
        p = radial(a, r + 0.012, z)
        frame = box(f'WindowFrame{k}', m['steel'], (0.06, 0.2, 0.09), p, bevel=0.006, rotation=(0, math.radians(-30), a))
        glass = box(f'Window{k}', m['tiberium'], (0.06, 0.16, 0.06), radial(a, r + 0.02, z), bevel=0.004, rotation=(0, math.radians(-30), a))
        parts += [frame, glass]
        windows.append(radial(a, r + 0.06, z))
    return skirt, kit.merge('TankDetails', parts), windows


def dome(m):
    """The steel dome with its seams and the hatch; origin on the skirt's top."""
    parts = [gb.lathe('Dome', m['roof'], DOME, (0, 0, 0), 48)]
    for k in range(16):
        a = k * math.pi / 8
        parts.append(beam(f'DomeSeam{k}', m['steel'], radial(a, 0.2, 0.452), radial(a, 0.68, 0.335), 0.01, 0.006))
    parts += [
        cylinder('Hatch', m['steel'], 0.13, 0.05, (0, 0, 0.47), segments=24),
        cylinder('HatchRing', m['remap'], 0.135, 0.015, (0, 0, 0.455), segments=24, bevel=0),
        cylinder('HatchLid', m['steel_light'], 0.09, 0.02, (0, 0, 0.5), segments=24),
    ]
    return kit.merge('DomeGroup', parts, (0, 0, SKIRT[-1][1]))


def fin(m, k):
    """One jagged fin in the house colour; origin on the axis at the dome's top (they
    shoot out from the middle)."""
    a = FIN_ANGLE + k * 2 * math.pi / FINS
    obj = gb.prism(f'Fin{k}', m['remap'], FIN, -FIN_WIDTH / 2, FIN_WIDTH / 2, 'Y', bevel=0.006)
    obj.rotation_euler = (0, 0, a)
    kit.bake_modifiers(obj)
    return kit.merge(f'Fin{k}', [obj], (0, 0, 0.47))


def pump(m):
    """The grey pump unit at the front right with pipes into the tank; origin at its foot."""
    c = PUMP + Vector((0, 0, 0.012))
    turn = -math.pi / 4
    inward = Vector((-1, 1, 0)).normalized()
    parts = [
        box('PumpBody', m['steel_light'], (0.2, 0.16, 0.16), c + Vector((0, 0, 0.08)), bevel=0.015, rotation=(0, 0, turn)),
        box('PumpTop', m['steel'], (0.22, 0.18, 0.025), c + Vector((0, 0, 0.17)), bevel=0.005, rotation=(0, 0, turn)),
        cylinder('PumpMotor', m['steel'], 0.05, 0.12, c + Vector((0, 0, 0.12)) - inward * 0.11, rotation=(math.pi / 2, 0, turn), segments=14),
        box('PumpPanel', m['remap'], (0.1, 0.01, 0.06), c + Vector((0, 0, 0.09)) + Vector((0.06, -0.06, 0)), bevel=0.002, rotation=(0, 0, math.pi / 4)),
    ]
    for s in (-1, 1):
        side = Vector((1, 1, 0)).normalized() * 0.05 * s
        start = c + side + Vector((0, 0, 0.11))
        parts.append(beam(f'PumpPipe{s}', m['steel'], start, start + inward * 0.25 + Vector((0, 0, 0.02)), 0.04))
        parts.append(cylinder(f'PumpFlange{s}', m['steel_light'], 0.032, 0.02, start + inward * 0.09 + Vector((0, 0, 0.01)), segments=10,
                              rotation=(math.pi / 2, 0, turn)))
    return kit.merge('Pump', parts, c)


# --------------------------------------------------------------------------- model

def build():
    gb.start('GDISilo', BUILD_END)
    m = materials()
    root = kit.empty('GDISilo')
    keys = kit.keys

    ground = kit.parent(footing(m), root)
    keys(ground, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 12: Vector((1.03, 1.03, 1)), 15: Vector((1, 1, 1))})

    # ---- the tank rises, the dome closes over it
    body = kit.parent(kit.empty('TankGroup'), root)
    skirt, details, windows = tank(m, root)
    for obj in (skirt, details):
        kit.parent(obj, body)
    keys(body, 'location', {0: Vector((0, 0, -0.5)), 6: Vector((0, 0, -0.5)), 24: Vector((0, 0, 0.01)), 27: Vector((0, 0, 0))})
    cap = kit.parent(dome(m), body)
    keys(cap, 'scale', {0: Vector((kit.HIDDEN,) * 3), 22: Vector((kit.HIDDEN,) * 3), 23: Vector((0.2, 0.2, 1)), 32: Vector((1.02, 1.02, 1)), 35: Vector((1, 1, 1))})

    # ---- the fins shoot out one after another
    for k in range(FINS):
        kit.pop(kit.parent(fin(m, k), body), 32 + 2 * k, 7)
    kit.pop(kit.parent(pump(m), root), 44, 8)

    # ---- the Tiberium glow in the windows, the beacons
    idle = []
    for k, at in enumerate(windows):
        glow = kit.parent(sphere(f'TiberiumGlow{k}', m['glow_green'], 0.07, at, 10), details)
        glow.scale = (0.55, 0.55, 0.55)
        idle.append((glow, lambda o, s=k: gb.pulse(o, 0.4, 0.85, 1 if s % 2 else 2)))
    # the lights hang from parents that are not scaled to nothing in Build (that spoils
    # their keys in Idle); only their housings pop up
    lights = []
    for name, at, colour, holder, pop_at, pattern in (
            ('Top', Vector((0, 0, 0.51)), 'red', (cap, body), 54, kit.flashes((0, 8), (30, 8))),
            ('PumpLamp', PUMP + Vector((0, 0, 0.2)), 'amber', (root, root), 58, kit.flashes((10, 12), (40, 12))),
            ('Ready', radial(FIN_ANGLE + math.pi, 0.66, 0.36), 'green', (body, body), 60, kit.flashes((0, 50)))):
        housing, light = kit.beacon(name, m, at, colour)
        housing = kit.parent(kit.merge(name, [housing], at), holder[0])
        kit.parent(light, holder[1])
        kit.pop(housing, pop_at, 5)
        lights.append((light, pattern))
    gb.clips(idle, lights)
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    gb.run(build, OUT, BLEND, scale=2.7, target=(0, 0, 0.25))
