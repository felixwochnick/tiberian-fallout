"""
Tiberian Fallout – Nod power plant (NAPOWR), after Tiberian Sun.

A dark, ribbed reactor cone on a wide round platform (foundation 2 × 2 cells): the
cone wears two red bands under its domed cap, a cable runs from the cap down to the
platform. The platform is light, stained concrete on a dark drum, ringed by red
blades that stick out sharp and low over the ground, more red blades stand up on its
deck round the cone's foot; two generator blocks sit on the deck at the front right.
Glowing vents at the cone's foot, red beacons on the cap.

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
(extra nodColour), Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.4 s: the platform rises out of the ground, the blades shoot
             out, the cone rises, bands, cap, cable and generators appear, the lights
             come on
    Idle     loop, 2 s: the vents at the foot glow up and fade (the reactor's pulse),
             the beacons on the cap blink in turn, the generator lamps flicker

Run headless (builds, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/NAPOWR.py [-- --preview 0,30,72 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells of the
foundation are centred at (±0.5, ±0.5); seen in the game, (-0.5, 0.5) is the top one.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nod  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'NAPOWR.glb')
BLEND = os.path.join(HERE, 'NAPOWR.blend')
BUILD_END = 72

DECK = 0.17             # top of the platform
DECK_RADIUS = 0.8
CONE_FOOT = 0.46
CONE_TOP = 0.25
CONE_HEIGHT = 1.12      # above the deck
CABLE_DIR = Vector((1, 1, 0)).normalized()   # the cable runs down on the right (screen)

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def cone_radius(z):
    """Radius of the cone at a height z above the deck (slightly curved flank)."""
    t = max(0.0, min(1.0, z / CONE_HEIGHT))
    return CONE_FOOT + (CONE_TOP - CONE_FOOT) * (t ** 0.85)


def platform(m, root):
    """The stained concrete deck on its footing, and its dark drum, seams and rim
    (returned apart: the concrete is baked); origin on the ground."""
    deck = nod.concrete('Deck', [
        cylinder('Footing', m['steel'], 0.72, 0.04, (0, 0, 0.02), segments=40, bevel=0.006),
        nod.lathe('DeckTop', m['steel'], ((DECK_RADIUS, DECK - 0.05), (DECK_RADIUS + 0.02, DECK - 0.02), (DECK_RADIUS - 0.02, DECK),
                                          (0.2, DECK + 0.005)), (0, 0, 0), 48),
    ], root, nod.LIGHT)
    parts = [
        cylinder('Drum', m['nplate_dark'], 0.66, 0.11, (0, 0, 0.095), segments=40, bevel=0.006),
        nod.lathe('DeckUnder', m['nplate'], ((0.66, 0.13), (DECK_RADIUS, DECK - 0.05)), (0, 0, 0), 48),
        cylinder('DeckRim', m['nsteel'], DECK_RADIUS + 0.025, 0.02, (0, 0, DECK - 0.035), segments=48, bevel=0),
        # dirt round the foot, like the original's sandy edge
        cylinder('Dirt', m['dirt'], 0.86, 0.012, (0, 0, 0.006), segments=40, bevel=0),
    ]
    for k in range(12):  # radial seams
        a = 2 * math.pi * (k + 0.5) / 12
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(beam(f'Seam{k}', m['nplate_dark'], d * (CONE_FOOT + 0.04) + Vector((0, 0, DECK + 0.006)),
                          d * (DECK_RADIUS - 0.04) + Vector((0, 0, DECK + 0.003)), 0.014, 0.008))
    return deck, kit.merge('DeckDetails', parts)


def blades(m):
    """Red blades round the platform's edge (low, sharp) and on the deck (standing);
    each its own object, origin at its root (they pop out from there)."""
    out = []
    for k in range(8):
        a = 2 * math.pi * (k + 0.25) / 8
        d = Vector((math.cos(a), math.sin(a), 0))
        root = d * (DECK_RADIUS - 0.08) + Vector((0, 0, DECK - 0.05))
        parts = [nod.spike(f'Blade{k}', m['remap'], root, d, 0.48, 0.15, 0.05, droop=0.12),
                 box(f'BladeClamp{k}', m['nplate_dark'], (0.09, 0.15, 0.06), root + Vector((0, 0, 0.01)), bevel=0.006,
                     rotation=(0, 0, a))]
        out.append(kit.merge(f'Blade{k}', parts, root))
    for k in range(6):
        a = 2 * math.pi * (k + 0.5) / 6 + 0.2
        d = Vector((math.cos(a), math.sin(a), 0))
        root = d * (CONE_FOOT + 0.06) + Vector((0, 0, DECK))
        fin = kit.hexahedron(f'Fin{k}', m['remap'], (
            root + d * -0.02 + Vector((-d.y, d.x, 0)) * 0.018, root + d * 0.2 + Vector((-d.y, d.x, 0)) * 0.012,
            root + d * 0.2 - Vector((-d.y, d.x, 0)) * 0.012, root + d * -0.02 - Vector((-d.y, d.x, 0)) * 0.018,
            root + Vector((-d.y, d.x, 0)) * 0.012 + Vector((0, 0, 0.26)), root + d * 0.06 + Vector((-d.y, d.x, 0)) * 0.006 + Vector((0, 0, 0.05)),
            root + d * 0.06 - Vector((-d.y, d.x, 0)) * 0.006 + Vector((0, 0, 0.05)), root - Vector((-d.y, d.x, 0)) * 0.012 + Vector((0, 0, 0.26)),
        ), bevel=0.003)
        out.append(kit.merge(f'Fin{k}', [fin], root))
    return out


def cone(m, root):
    """The reactor cone (concrete, returned first) and its dark ribs; origin on the deck."""
    base = Vector((0, 0, DECK))
    profile = [(cone_radius(z), z) for z in (0, 0.15, 0.35, 0.55, 0.75, 0.95, CONE_HEIGHT)]
    shell = nod.concrete('Cone', [nod.lathe('ConeShell', m['steel'], profile, base, 32)], root, nod.GREY, base)
    parts = []
    for k in range(16):
        a = 2 * math.pi * k / 16
        d = Vector((math.cos(a), math.sin(a), 0))
        lo, hi = 0.05, CONE_HEIGHT - 0.2
        parts.append(beam(f'Rib{k}', m['nplate'], base + d * (cone_radius(lo) + 0.008) + Vector((0, 0, lo)),
                          base + d * (cone_radius(hi) + 0.008) + Vector((0, 0, hi)), 0.035, 0.022))
    parts.append(cylinder('ConeFoot', m['nplate_dark'], CONE_FOOT + 0.03, 0.06, base + Vector((0, 0, 0.03)), segments=32, bevel=0.006))
    return shell, kit.merge('ConeRibs', parts, base)


def crown(m):
    """Red bands and the domed cap with its vent ring; origin at the cone's top."""
    top = Vector((0, 0, DECK + CONE_HEIGHT))
    parts = []
    for i, z in enumerate((-0.17, -0.08)):
        parts.append(cylinder(f'Band{i}', m['remap'], cone_radius(CONE_HEIGHT + z) + 0.028, 0.05, top + Vector((0, 0, z)), segments=32, bevel=0.006))
    parts += [
        cylinder('CapRing', m['nplate_dark'], CONE_TOP + 0.02, 0.04, top + Vector((0, 0, 0.0)), segments=32, bevel=0.006),
        nod.lathe('Cap', m['nplate_dark'], ((CONE_TOP, 0), (CONE_TOP - 0.01, 0.05), (0.19, 0.1), (0.12, 0.14), (0.0, 0.155)), top, 24),
        cylinder('CapVent', m['dark'], 0.07, 0.02, top + Vector((0, 0, 0.15)), segments=16, bevel=0),
    ]
    for k in range(8):
        a = 2 * math.pi * k / 8
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(box(f'CapSlot{k}', m['dark'], (0.012, 0.05, 0.03), top + d * (CONE_TOP - 0.03) + Vector((0, 0, 0.06)), bevel=0,
                         rotation=(0, math.radians(-30), a)))
    return kit.merge('Crown', parts, top)


def cable(m):
    """The cable from the cap down to the deck on the right, with its clamps."""
    top = Vector((0, 0, DECK + CONE_HEIGHT + 0.04)) + CABLE_DIR * (CONE_TOP + 0.02)
    foot = CABLE_DIR * (DECK_RADIUS - 0.12) + Vector((0, 0, DECK))
    mid = CABLE_DIR * (cone_radius(0.5) + 0.12) + Vector((0, 0, DECK + 0.55))
    parts = [beam('CableUp', m['nsteel'], top, mid, 0.022), beam('CableDown', m['nsteel'], mid, foot + Vector((0, 0, 0.04)), 0.022),
             box('CableFoot', m['nplate_dark'], (0.1, 0.1, 0.06), foot + Vector((0, 0, 0.03)), bevel=0.008),
             box('CableTop', m['nplate_dark'], (0.06, 0.06, 0.05), top, bevel=0.006)]
    return kit.merge('Cable', parts, foot)


def generator(m, name, centre, angle):
    """A generator block on the deck: dark housing, red stripe, grille, lamp spot; origin at its foot."""
    centre = Vector(centre)
    rot = (0, 0, angle)
    parts = [
        box(f'{name}Housing', m['nplate_dark'], (0.2, 0.13, 0.11), centre + Vector((0, 0, 0.055)), bevel=0.012, rotation=rot),
        box(f'{name}Top', m['nsteel'], (0.16, 0.1, 0.03), centre + Vector((0, 0, 0.125)), bevel=0.008, rotation=rot),
        box(f'{name}Stripe', m['remap'], (0.205, 0.135, 0.018), centre + Vector((0, 0, 0.085)), bevel=0, rotation=rot),
        cylinder(f'{name}Drum', m['nplate'], 0.04, 0.17, centre + Vector((0, 0, 0.17)), rotation=(0, math.pi / 2, angle), segments=12),
    ]
    return kit.merge(name, parts, centre)


def build():
    root = nod.start('NodPowerPlant', 'NodPowerPlant', BUILD_END)
    m = nod.materials()
    keys = kit.keys

    base, details = platform(m, root)
    kit.parent(base, root)
    kit.parent(details, base)
    cone_obj, ribs = cone(m, root)
    crown_obj = crown(m)
    cable_obj = cable(m)
    gens = [generator(m, 'Generator0', Vector((0.42, -0.42, DECK)), math.radians(45)),
            generator(m, 'Generator1', Vector((0.1, -0.6, DECK)), math.radians(15))]

    # ---- the platform rises out of the ground
    nod.rise(base, 0, 16, 0.25)
    # ---- the blades shoot out
    for i, blade in enumerate(blades(m)):
        kit.parent(blade, base)
        kit.pop(blade, 14 + i, 6)
    # ---- the cone rises out of the deck, the crown on it
    group = kit.parent(kit.empty('ConeGroup'), root)
    kit.parent(cone_obj, group)
    kit.parent(ribs, cone_obj)
    keys(group, 'location', {0: Vector((0, 0, -1.3)), 12: Vector((0, 0, -1.3)), 42: Vector((0, 0, 0.012)), 46: Vector((0, 0, 0))})
    kit.parent(crown_obj, group)
    kit.pop(crown_obj, 42, 8)
    kit.parent(cable_obj, base)
    kit.grow(cable_obj, 48, 10, 2)
    for i, g in enumerate(gens):
        kit.parent(g, base)
        kit.pop(g, 30 + 5 * i, 7)

    # ---- glowing vents at the cone's foot (pulse), beacons on the cap
    idle = []
    for k in range(4):
        a = 2 * math.pi * (k + 0.125) / 4
        d = Vector((math.cos(a), math.sin(a), 0))
        at = d * (CONE_FOOT + 0.005) + Vector((0, 0, DECK + 0.16))
        frame = box(f'Vent{k}', m['nplate_dark'], (0.05, 0.13, 0.08), at, bevel=0.006, rotation=(0, math.radians(-10), a))
        frame = kit.parent(kit.merge(f'Vent{k}', [frame], at), cone_obj)
        kit.pop(frame, 46 + k, 5)
        glow = kit.merge(f'VentGlow{k}', [
            box(f'VentCore{k}', m['ember'], (0.03, 0.09, 0.05), at + d * 0.016, bevel=0, rotation=(0, math.radians(-10), a)),
            box(f'VentHalo{k}', m['glow_red'], (0.06, 0.15, 0.1), at + d * 0.03, bevel=0, rotation=(0, math.radians(-10), a)),
        ], at)
        kit.parent(glow, frame)
        idle.append((glow, lambda o, k=k: nod.pulse(o, kit.IDLE_END, 0.55, 1.1, phase=k * 0.1)))
    lights = []
    top = Vector((0, 0, DECK + CONE_HEIGHT))
    for k in range(4):
        a = 2 * math.pi * (k + 0.5) / 4
        at = top + Vector((math.cos(a), math.sin(a), 0)) * (CONE_TOP + 0.005) + Vector((0, 0, 0.02))
        light = nod.lamp(m, crown_obj, f'CapLamp{k}', at, 'red', 52 + k)
        lights.append((light, kit.flashes((k * 15, 8))))
    for i, g in enumerate(gens):
        at = g.location + Vector((0, 0, 0.25))
        light = nod.lamp(m, g, f'GenLamp{i}', at, 'amber', 56 + i)
        lights.append((light, kit.flashes((5 + 30 * i, 3), (12 + 30 * i, 4), (40 - 20 * i, 3))))

    nod.clips(lights, idle)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, ortho=2.9, target=(0.05, 0, 0.5))
