"""
Tiberian Fallout – Nod Obelisk of Light (NAOBEL), after Tiberian Sun.

A tall, slightly leaning needle on a flat armoured hull (foundation 2 × 2 cells), like
the original's: the hull is a dark, pointed lens of sloped concrete lying along the
diagonal from the lower left to the upper right of the screen, with long dark blades
at both tips and smaller ones at its flanks; in its middle a raised collar with a red
(house colour) band, from which the obelisk rises. The obelisk is a tapering,
four-sided shaft of grey concrete with a dark spine, fins and side vents, leaning a
little to the back; on its top a dark clamp holds the red crystal, from whose tip the
beam leaves.

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
(extra nodColour), Remap the house colour (the crystal too), Lamp* emissive, Glow*
additive.

Nodes:
    Flash        the glow at the crystal's tip, where the beam starts (shown in Fire;
                 the beam itself is drawn by the game)
    Tower        the leaning shaft with the crystal (rises in Build via TowerLift)
    CrystalGlow  the halo round the crystal (charges up in Fire)
    BandGlow     the glow round the red band at the foot (Idle, the original's NAOBEL_A)
    Lamp…        red lamps on the hull
Animations (glTF clips)
    Build    one-shot, 2.4 s: the hull rises out of the ground, the blades shoot out,
             the obelisk comes up out of the collar, the crystal slides out of its top
    Idle     loop, 2 s: the band at the foot glows up and fades, lamps blink
    Fire     one-shot, 1.2 s: the crystal charges (its halo swells and brightens),
             then discharges in a flash at the tip and falls back to rest

Run headless:

    blender -b --factory-startup --python blender/NAOBEL.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells of the
foundation are centred at (±0.5, ±0.5); origin in the middle on the ground.
"""
import math
import os
import sys

from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nb  # noqa: E402

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam
HIDDEN = kit.HIDDEN

BUILD_END = 72
FIRE_FRAMES = 36
HULL = 0.3                    # top of the hull
AXIS = Vector((1, 1, 0)).normalized()     # the hull's long axis (screen left to right)
SIDE = Vector((-1, 1, 0)).normalized()
FOOT = Vector((-0.04, 0.02, HULL + 0.05))   # the obelisk's foot (on the collar)
SHAFT = 1.12                  # the shaft's height above its foot
LEAN = Euler((math.radians(-11), math.radians(5), 0))
CRYSTAL = (SHAFT + 0.06, SHAFT + 0.42)    # the crystal's foot and tip (in the shaft's frame)
HULL_CONCRETE = '#505154'
W0, W1, W2 = (0.5, 0.44), (0.4, 0.35), (0.2, 0.17)   # the shaft's width and depth at its foot, step, top
SHAFT_CONCRETE = '#86878a'


def lens(length, width, cx=0.0, cy=0.0, n=20):
    """A pointed lens outline along AXIS (counter-clockwise)."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        u = length * math.cos(a)
        v = width * math.sin(a) * (0.55 + 0.45 * abs(math.sin(a)))
        p = AXIS * u + SIDE * v
        pts.append((cx + p.x, cy + p.y))
    return pts


def hull(m, root):
    """The flat armoured hull (concrete, returned first) and its details; origin on the ground."""
    body = nb.concrete('Hull', [nb.prism('HullLower', m['steel'], lens(1.26, 0.64), lens(1.18, 0.6), 0, 0.12),
                                nb.prism('HullUpper', m['steel'], lens(1.18, 0.6), lens(0.7, 0.42), 0.12, HULL)], root, HULL_CONCRETE)
    parts = [nb.prism('HullShadow', m['dirt'], lens(1.36, 0.68), lens(1.36, 0.68), 0, 0.008, bevel=0)]
    # the collar the obelisk stands in, with its red band
    collar = nb.chamfered(FOOT.x, FOOT.y, 0.72, 0.64, 0.18)
    parts.append(nb.prism('Collar', m['nplate_dark'], collar, nb.chamfered(FOOT.x, FOOT.y, 0.56, 0.5, 0.15), HULL - 0.02, HULL + 0.06, bevel=0.006))
    parts.append(nb.prism('CollarBand', m['remap'], nb.chamfered(FOOT.x, FOOT.y, 0.75, 0.67, 0.19), nb.chamfered(FOOT.x, FOOT.y, 0.58, 0.52, 0.15),
                          HULL - 0.035, HULL + 0.07, bevel=0.002))
    # seams over the hull and dark plates at the tips
    for k in (-1, 1):
        for j, t in enumerate((0.45, 0.75)):
            c = AXIS * k * t * 1.0
            parts.append(beam(f'Seam{k}{j}', m['nplate_dark'], c - SIDE * 0.36 * (1.1 - t) + Vector((0, 0, 0.165)),
                              c + SIDE * 0.36 * (1.1 - t) + Vector((0, 0, 0.165)), 0.016, 0.01))
    for k in (-1, 1):
        parts.append(beam(f'Ridge{k}', m['nplate'], AXIS * k * 0.45 + Vector((0, 0, HULL + 0.004)), AXIS * k * 0.68 + Vector((0, 0, HULL + 0.004)), 0.05, 0.016))
    return body, kit.merge('HullDetails', parts)


def blades(m):
    """Long dark blades at the hull's tips and short ones on its flanks."""
    out = []
    for k, (d, at, length, width, droop) in enumerate((
            (AXIS, AXIS * 1.0, 0.5, 0.2, 0.1), (-AXIS, -AXIS * 1.0, 0.55, 0.22, 0.1),
            ((AXIS * 0.4 - SIDE).normalized(), AXIS * 0.35 - SIDE * 0.42, 0.3, 0.12, 0.08),
            ((-AXIS * 0.6 - SIDE).normalized(), -AXIS * 0.45 - SIDE * 0.38, 0.32, 0.12, 0.08),
            ((AXIS * 0.3 + SIDE).normalized(), AXIS * 0.3 + SIDE * 0.4, 0.26, 0.12, 0.07))):
        root = Vector((at.x, at.y, 0.12))
        obj = nb.spike(f'Blade{k}', m['nplate_dark'], root, d, length, width, 0.05, droop=droop)
        out.append(kit.merge(f'Blade{k}', [obj], root))
    return out


def shaft(m, root):
    """The obelisk, built upright with its foot at the origin (concrete returned first,
    then the details and the crystal)."""
    def section(w, d, z, c=0.3):
        return nb.chamfered(0, 0, w, d, min(w, d) * c)

    low = nb.prism('ShaftLow', m['steel'], section(*W0, 0), section(*W1, 0.32), 0, 0.32)
    high = nb.prism('ShaftHigh', m['steel'], section(W1[0] - 0.02, W1[1] - 0.02, 0.32), section(*W2, SHAFT), 0.32, SHAFT)
    body = nb.concrete('Shaft', [low, high], root, SHAFT_CONCRETE)

    def at(z, sx, sy):
        """A point on the shaft's surface at height z (sx, sy: -1..1 across it)."""
        if z < 0.32:
            t = z / 0.32
            w, d = W0[0] + (W1[0] - W0[0]) * t, W0[1] + (W1[1] - W0[1]) * t
        else:
            t = (z - 0.32) / (SHAFT - 0.32)
            w, d = W1[0] - 0.02 + (W2[0] - W1[0] + 0.02) * t, W1[1] - 0.02 + (W2[1] - W1[1] + 0.02) * t
        return Vector((sx * w / 2, sy * d / 2, z))

    parts = [
        # the dark spine up the front and the back
        beam('SpineF', m['nplate_dark'], at(0.34, 0, -1) - Vector((0, 0.008, 0)), at(SHAFT - 0.06, 0, -1) - Vector((0, 0.008, 0)), 0.05, 0.02),
        beam('SpineB', m['nplate_dark'], at(0.34, 0, 1) + Vector((0, 0.008, 0)), at(SHAFT - 0.06, 0, 1) + Vector((0, 0.008, 0)), 0.05, 0.02),
        # the step between the two stages
        nb.prism('Step', m['nplate_dark'], section(W1[0] + 0.03, W1[1] + 0.03, 0), section(*W1, 0), 0.29, 0.345, bevel=0.003),
        # the clamp holding the crystal
        nb.prism('Clamp', m['nplate_dark'], section(W2[0] + 0.03, W2[1] + 0.03, 0), section(W2[0] - 0.06, W2[1] - 0.05, 0), SHAFT - 0.02, CRYSTAL[0] + 0.03, bevel=0.004),
    ]
    for s in (-1, 1):   # vents on the sides
        for j, z in enumerate((0.48, 0.62, 0.76)):
            p = at(z, s, 0) + Vector((s * 0.004, 0, 0))
            parts.append(box(f'Vent{s}{j}', m['dark'], (0.01, 0.1, 0.04), p, bevel=0))
    for s in (-1, 1):   # small dark fins high on the sides, pointing out and up
        p = at(0.95, s, 0)
        parts.append(nb.spike(f'Fin{s}', m['nplate_dark'], p, (s, 0, 0.35), 0.13, 0.07, 0.02))
        q = at(SHAFT - 0.05, s, 0)
        parts.append(nb.spike(f'Prong{s}', m['nplate_dark'], q, (s * 0.5, 0, 1), 0.16, 0.04, 0.02))
    details = kit.merge('ShaftDetails', parts)
    # the crystal: a long four-sided red point on a short one
    lo, tip = CRYSTAL
    mid = lo + 0.08
    r = 0.1
    diamond = lambda q: [(q, 0), (0, q), (-q, 0), (0, -q)]  # noqa: E731
    crystal = kit.merge('Crystal', [nb.prism('CrystalLow', m['remap'], diamond(0.03), diamond(r), lo, mid, bevel=0.002),
                                    nb.prism('CrystalHigh', m['remap'], diamond(r), diamond(0.004), mid, tip, bevel=0.002)], Vector((0, 0, lo)))
    return body, details, crystal


def build():
    root = nb.start('NodObelisk', 'NodObelisk', BUILD_END)
    m = nb.materials()
    keys = kit.keys

    # ---- the hull rises out of the ground, the blades shoot out
    hull_group = kit.parent(kit.empty('HullGroup'), root)
    body, details = hull(m, root)
    kit.parent(body, hull_group)
    kit.parent(details, body)
    nb.rise(hull_group, 0, 18, HULL + 0.06)
    for k, blade in enumerate(blades(m)):
        kit.parent(blade, hull_group)
        kit.pop(blade, 16 + 3 * k, 8)

    # ---- the obelisk, built upright at the origin, then stood on its foot and leant back
    lift = kit.parent(kit.empty('TowerLift'), root)
    tower = kit.parent(kit.empty('Tower'), lift)
    sbody, sdetails, crystal = shaft(m, root)
    kit.parent(sbody, tower)
    kit.parent(sdetails, sbody)
    holder = kit.parent(kit.empty('CrystalHolder', (0, 0, CRYSTAL[0])), tower)
    kit.parent(crystal, holder)
    tip = Vector((0, 0, CRYSTAL[1]))
    halo = kit.parent(kit.merge('CrystalGlow', [sphere('CrystalHalo', m['glow_red'], 0.06, tip - Vector((0, 0, 0.14)), 14)], tip - Vector((0, 0, 0.14))), holder)
    halo.scale = (0.7, 0.7, 1.6)
    flash = kit.parent(nb.glow(m, 'Flash', tip, 0.07, 'glow_laser', balls=1), holder)
    tower.location = FOOT
    tower.rotation_euler = LEAN

    # Build: the obelisk comes up out of the collar, the crystal slides out of its top
    low = Vector((0, 0, -(SHAFT + 0.5)))
    keys(lift, 'location', {0: low, 22: low, 52: Vector((0, 0, 0.01)), 56: Vector((0, 0, 0))})
    # the crystal slides up out of the shaft's top (translation: its halo and the flash ride on it)
    sunk = Vector((0, 0, -(CRYSTAL[1] - CRYSTAL[0])))
    rest = Vector(holder.location)
    keys(holder, 'location', {0: rest + sunk, 54: rest + sunk, 66: rest + Vector((0, 0, 0.01)), 69: rest})
    flash.scale = Vector((HIDDEN,) * 3)

    # lamps on the hull
    lights = []
    for k, p in enumerate((AXIS * 0.84, -AXIS * 0.84)):
        lights.append((nb.lamp(m, body, f'HullLamp{k}', (p.x, p.y, 0.24), 'red', 60 + 3 * k), kit.flashes((k * 30, 8))))

    # Idle: the band at the foot glows up and fades
    band = kit.parent(kit.merge('BandGlow', [nb.prism('BandHalo', m['glow_red'], nb.chamfered(FOOT.x, FOOT.y, 0.8, 0.72, 0.2),
                                                      nb.chamfered(FOOT.x, FOOT.y, 0.7, 0.64, 0.18), HULL - 0.04, HULL + 0.07, bevel=0)],
                                Vector((FOOT.x, FOOT.y, HULL - 0.04))), body)

    def throb(obj):
        frames = {}
        for f in range(0, kit.IDLE_END + 1, 3):
            t = (math.sin(2 * math.pi * f / kit.IDLE_END) + 1) / 2
            frames[f] = Vector((1, 1, 0.35 + 0.65 * t))
        frames[kit.IDLE_END] = frames[0]
        kit.keys(obj, 'scale', frames, 'LINEAR')

    nb.clips(lights, [(band, throb)])

    # Fire: the crystal charges, then discharges at the tip
    s = Vector(halo.scale)
    keys(halo, 'scale', {0: s, 22: s * 2.1, 26: s * 2.4, 30: s * 0.7, FIRE_FRAMES: s}, 'LINEAR')
    kit.to_track(halo, 'Fire')
    hidden = Vector((HIDDEN,) * 3)
    keys(flash, 'scale', {0: hidden, 25: hidden, 26: Vector((1, 1, 1)), 28: Vector((1.6, 1.6, 1.6)), 32: Vector((0.8, 0.8, 0.8)), 33: hidden,
                          FIRE_FRAMES: hidden}, 'CONSTANT')
    kit.to_track(flash, 'Fire')
    halo.scale = s
    flash.scale = hidden
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NAOBEL', {'Build': [24, 48, BUILD_END], 'Idle': [0, 15], 'Fire': [12, 24, 28]}, ortho=3.2, target=(0, 0.1, 0.75))
