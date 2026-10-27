"""
Tiberian Fallout – Nod Tiberium waste facility (NAWAST), after Tiberian Sun / Firestorm.

On three cells by three (foundation 3 × 3), like the original's: a wide oval apron of
stained concrete (the original's bib NAWASTBB), and on it a dark star of four sloped
concrete wedges with red (house colour) rims, pointing to the screen's left, upper
left, upper right and lower left. In their middle sits an open tub of dark plate full of glowing green Tiberium sludge, and
out of it rises a slim dark spire with red bands. On the open side, the screen's lower
right, the tub has its hatch, facing a red and black striped
dock on the apron (+x, lower right on screen) where the Weed Eater backs in to unload.
Two red pods with blue lamps stand on the apron.

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
(extra nodColour), Remap the house colour, Lamp* emissive, Glow* additive.

Nodes:
    Dock        on the striped pad: where the Weed Eater stands to unload, its -Y axis
                the way the vehicle faces then (away from the hatch, +x)
    Core        the tub, hatch and spire (rise in Build)
    Sludge…     the glowing sludge in the tub; SludgeGlow swells, Bubble0…2 rise and
                burst (Idle, the original's NAWAST_A)
    Pod0/Pod1   the red pods (rise in Build) with their blue lamps (Idle, NAWAST_B)
Animations (glTF clips)
    Build    one-shot, 2.4 s: the apron spreads, the wedges rise one after another,
             the tub comes up with the spire, the dock's stripes and the pods appear
    Idle     loop, 2 s: the sludge glows and bubbles, the pods' lamps flicker, a red
             lamp on the spire blinks

Run headless:

    blender -b --factory-startup --python blender/NAWAST.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells are
centred at x, y = -1, 0, 1; origin in the middle on the ground.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nb  # noqa: E402

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam
HIDDEN = kit.HIDDEN
BUILD_END = 72

APRON = 0.03                # the apron's top
CORE_R = 0.42               # the tub's outer radius (octagon)
CORE_H = 0.4
SLUDGE = 0.33               # the sludge's surface
SPIRE = 1.15
CENTER = Vector((-0.15, 0.1, 0))      # the tub's middle
DOCK = Vector((1.06, 0.06, APRON))
PODS = (Vector((0.88, 0.86, 0)), Vector((0.42, -1.18, 0)))
APRON_CONCRETE = '#a89f88'
WEDGE_CONCRETE = '#5a5b5e'


def octagon(r, cx=0.0, cy=0.0, turn=math.pi / 8):
    return [(cx + r * math.cos(turn + k * math.pi / 4), cy + r * math.sin(turn + k * math.pi / 4)) for k in range(8)]


def oval(rx, ry, n=40):
    """The apron's outline: a rounded square (superellipse) centred a little to the front right."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        pts.append((0.06 + rx * math.copysign(abs(c) ** 0.6, c), -0.04 + ry * math.copysign(abs(s) ** 0.6, s)))
    return pts


def apron(m, root):
    """The apron (concrete, returned first), the dock's stripes and stains."""
    body = nb.concrete('Apron', [nb.prism('ApronSlab', m['steel'], oval(1.46, 1.42), oval(1.42, 1.38), 0, APRON, bevel=0.004)], root, APRON_CONCRETE)
    mats = dict(m)
    mats['hazard'] = m['remap']
    stripes = nb.stripes('DockStripes', mats, (DOCK.x, DOCK.y, APRON + 0.004), (0.72, 0.7, 0.008), 'Y', 8)
    parts = [nb.prism('ApronEdge', m['dirt'], oval(1.5, 1.46), oval(1.5, 1.46), 0, 0.006, bevel=0)]
    for k, (x, y, r) in enumerate(((-1.0, -0.6, 0.12), (0.95, -0.8, 0.09), (1.2, 0.5, 0.07), (-0.8, 1.05, 0.1))):
        parts.append(cylinder(f'Stain{k}', m['dirt'], r, 0.004, (x, y, APRON + 0.002), segments=12, bevel=0))
    # the dock's frame
    for s in (-1, 1):
        parts.append(box(f'DockRail{s}', m['nplate_dark'], (0.76, 0.03, 0.014), (DOCK.x, DOCK.y + s * 0.365, APRON + 0.007), bevel=0.003))
    return body, stripes, kit.merge('ApronDetails', parts)


def wedge(m, root, k, a):
    """A sloped wedge from the tub out along direction `a` (concrete, returned first)
    and its red rims; origin at its foot under the tub."""
    d = Vector((math.cos(a), math.sin(a), 0))
    s = Vector((-d.y, d.x, 0))
    c0, tip = CENTER + d * 0.25, CENTER + d * 1.28
    z = Vector((0, 0, 1))
    lo = (c0 - s * 0.42, tip - s * 0.13, tip + s * 0.13, c0 + s * 0.42)
    hi = (c0 - s * 0.24 + z * 0.56, tip - s * 0.07 + z * 0.12, tip + s * 0.07 + z * 0.12, c0 + s * 0.24 + z * 0.56)
    lo = [p + Vector((0, 0, APRON)) for p in lo]
    hi = [p + Vector((0, 0, APRON)) for p in hi]
    body = nb.concrete(f'Wedge{k}', [kit.hexahedron(f'Wedge{k}Body', m['steel'], lo + hi, bevel=0.01)], root, WEDGE_CONCRETE)
    parts = []
    for i, (p, q, sign) in enumerate(((lo[0], lo[1], -1), (lo[3], lo[2], 1))):    # red rims along the foot
        out = s * sign * 0.012
        parts.append(beam(f'Wedge{k}Rim{i}', m['remap'], p + out + Vector((0, 0, 0.03)) + d * 0.45, q + out + Vector((0, 0, 0.03)), 0.035, 0.03))
    for i, (p, q) in enumerate(((hi[0], hi[1]), (hi[3], hi[2]))):    # red edges along the ridge's outer half
        mid = p + (q - p) * 0.45
        parts.append(beam(f'Wedge{k}Edge{i}', m['remap'], mid + Vector((0, 0, 0.008)), q + Vector((0, 0, 0.008)) - d * 0.03, 0.03, 0.02))
    parts.append(beam(f'Wedge{k}Ridge', m['nplate_dark'], (hi[0] + hi[3]) / 2 + Vector((0, 0, 0.006)) + d * 0.12,
                      (hi[1] + hi[2]) / 2 + Vector((0, 0, 0.006)) - d * 0.12, 0.05, 0.016))
    # vents on the ridge
    for j, t in enumerate((0.25, 0.4)):
        p = (hi[0] + hi[3]) / 2 + ((hi[1] + hi[2]) / 2 - (hi[0] + hi[3]) / 2) * t
        parts.append(box(f'Wedge{k}Vent{j}', m['dark'], (0.07, 0.07, 0.01), p + Vector((0, 0, 0.006)) + s * 0.08, bevel=0, rotation=(0, 0, a)))
    return body, kit.merge(f'Wedge{k}Details', parts, CENTER + d * 0.25)


def core(m):
    """The tub with its hatch and the spire; origin on the apron."""
    base = Vector((0, 0, APRON))
    tub = nb.prism('TubWall', m['nplate'], octagon(CORE_R), octagon(CORE_R - 0.05), APRON, APRON + CORE_H, bevel=0.008)
    parts = [
        tub,
        nb.prism('TubRim', m['nplate_dark'], octagon(CORE_R - 0.03), octagon(CORE_R - 0.04), APRON + CORE_H - 0.004, APRON + CORE_H + 0.03, bevel=0.004),
        nb.prism('TubBand', m['remap'], octagon(CORE_R - 0.012 + 0.012), octagon(CORE_R - 0.03 + 0.012), APRON + CORE_H - 0.13, APRON + CORE_H - 0.09, bevel=0.002),
        # the hatch on the +x side, facing the dock
        box('Hatch', m['dark'], (0.03, 0.3, 0.22), (CORE_R - 0.01, 0, APRON + 0.12), bevel=0.004),
        box('HatchFrame', m['nplate_dark'], (0.04, 0.38, 0.04), (CORE_R - 0.005, 0, APRON + 0.25), bevel=0.004),
        box('HatchLip', m['nsteel'], (0.12, 0.34, 0.02), (CORE_R + 0.04, 0, APRON + 0.01), bevel=0.004),
    ]
    # the spire: tapering stages with red bands and two prongs
    stages = ((0.0, 0.2, 0.17), (0.55, 0.15, 0.13), (0.85, 0.11, 0.08), (SPIRE, 0.03, 0.03))
    for i, ((z0, w0, d0), (z1, w1, d1)) in enumerate(zip(stages, stages[1:])):
        parts.append(nb.prism(f'Spire{i}', m['nplate_dark'] if i % 2 else m['nplate'], nb.chamfered(0, 0, w0, d0, w0 * 0.25),
                              nb.chamfered(0, 0, w1, d1, w1 * 0.25), APRON + 0.1 + z0, APRON + 0.1 + z1, bevel=0.004))
    for j, z in enumerate((0.48, 0.62, 0.76)):
        t = (z - 0.0) / 0.55 if z < 0.55 else (z - 0.55) / 0.3
        w = (0.2 + (0.15 - 0.2) * t) if z < 0.55 else (0.15 + (0.11 - 0.15) * t)
        parts.append(box(f'SpireBand{j}', m['remap'], (w + 0.024, w * 0.85 + 0.024, 0.03), (0, 0, APRON + 0.1 + z), bevel=0.004))
    for s in (-1, 1):
        parts.append(nb.spike(f'SpireFin{s}', m['nplate_dark'], (0, s * 0.05, APRON + 0.1 + 0.62), (0, s, 0.8), 0.24, 0.05, 0.02))
    return kit.merge('Core', parts, base)


def pod(m, k, at):
    """A red pod (a drum with a domed top); origin at its foot."""
    parts = [
        cylinder(f'Pod{k}Foot', m['nplate_dark'], 0.15, 0.04, at + Vector((0, 0, APRON + 0.02)), segments=20, bevel=0.004),
        cylinder(f'Pod{k}Drum', m['remap'], 0.12, 0.12, at + Vector((0, 0, APRON + 0.1)), segments=20, bevel=0.01),
        nb.lathe(f'Pod{k}Dome', m['nsteel'], [(0.12, 0), (0.1, 0.04), (0.05, 0.065), (0.01, 0.07)], at + Vector((0, 0, APRON + 0.16)), 20),
        cylinder(f'Pod{k}Band', m['nplate_dark'], 0.124, 0.02, at + Vector((0, 0, APRON + 0.08)), segments=20, bevel=0),
    ]
    return kit.merge(f'Pod{k}', parts, at)


def bubble(m, k, at):
    return kit.merge(f'Bubble{k}', [sphere(f'Bubble{k}Ball', m['sludge_light'], 0.03, at, 10)], at)


def build():
    root = nb.start('NodWasteFacility', 'NodWasteFacility', BUILD_END)
    m = nb.materials()
    m['sludge'] = kit.material('Sludge', kit.srgb('#2f8a2a'), 0.3, emission=kit.srgb('#3cd23a'), strength=1.6)
    m['sludge_light'] = kit.material('SludgeLight', kit.srgb('#8cff7a'), 0.3, emission=kit.srgb('#7aff60'), strength=4)
    m['glow_blue'] = kit.material('GlowBlue', (0, 0, 0), 1.0, emission=kit.srgb('#5aa8ff'), strength=3, alpha=0.3)
    m['lamp_blue'] = kit.material('LampBlue', kit.srgb('#bfe0ff'), 0.2, emission=kit.srgb('#7ab8ff'), strength=8)
    keys = kit.keys

    # ---- the apron spreads, the dock's stripes appear
    ground = kit.parent(kit.empty('ApronGroup'), root)
    body, stripes, details = apron(m, root)
    kit.parent(body, ground)
    kit.parent(details, body)
    kit.parent(stripes, ground)
    keys(ground, 'scale', {0: Vector((0.05, 0.05, 1)), 12: Vector((1.02, 1.02, 1)), 15: Vector((1, 1, 1))})
    kit.pop(stripes, 50, 8)
    dock = kit.parent(kit.empty('Dock', DOCK), root)
    dock.rotation_euler = (0, 0, math.pi / 2)    # -Y (the vehicle's front) along +x

    # ---- the wedges rise one after another
    for k, a in enumerate((220, 160, 85, 275)):
        wbody, wdetails = wedge(m, root, k, math.radians(a))
        holder = kit.parent(kit.empty(f'Wedge{k}Group'), root)
        kit.parent(wbody, holder)
        kit.parent(wdetails, wbody)
        nb.rise(holder, 10 + 5 * k, 14, 0.65)

    # ---- the tub and spire rise (translation: the sludge and bubbles ride along)
    lift = kit.parent(kit.empty('CoreLift'), root)
    core_obj = kit.parent(core(m), lift)
    core_obj.name = 'Core'
    sludge = kit.parent(kit.merge('Sludge', [nb.prism('SludgePool', m['sludge'], octagon(CORE_R - 0.05), octagon(CORE_R - 0.05), APRON + SLUDGE - 0.01,
                                                      APRON + SLUDGE, bevel=0)], (0, 0, APRON + SLUDGE)), core_obj)
    glow = kit.parent(kit.merge('SludgeGlow', [nb.prism('SludgeHalo', m['glow_green'], octagon(CORE_R - 0.06), octagon(CORE_R - 0.16), 0, 0.14, bevel=0)],
                                (0, 0, 0)), core_obj)
    glow.location = (0, 0, APRON + SLUDGE)
    bubbles = [kit.parent(bubble(m, k, Vector((x, y, APRON + SLUDGE - 0.03))), core_obj)
               for k, (x, y) in enumerate(((0.2, 0.1), (-0.15, 0.2), (0.05, -0.22)))]
    low = CENTER - Vector((0, 0, SPIRE + 0.4))
    keys(lift, 'location', {0: low, 26: low, 52: CENTER + Vector((0, 0, 0.01)), 56: CENTER})
    lights = [(nb.lamp(m, core_obj, 'SpireLamp', (CENTER.x, CENTER.y, APRON + 0.1 + SPIRE - 0.02), 'red', 60), kit.flashes((0, 6), (30, 6)))]

    # ---- the pods pop up, their blue lamps flicker
    for k, at in enumerate(PODS):
        p = kit.parent(pod(m, k, at), root)
        nb.rise(p, 56 + 4 * k, 8, APRON + 0.24)
        top = at + Vector((0, 0, APRON + 0.23))
        housing, light = kit.beacon(f'Pod{k}Lamp', m, top, 'blue', m['lamp_blue'])
        kit.parent(kit.merge(f'Pod{k}Lamp', [housing], top), p)
        kit.parent(light, p)
        lights.append((light, kit.flashes((k * 17, 3), (k * 17 + 6, 3), (k * 17 + 33, 4))))

    def swell(obj):
        frames = {}
        for f in range(0, kit.IDLE_END + 1, 3):
            t = (math.sin(2 * math.pi * 2 * f / kit.IDLE_END) + 1) / 2
            frames[f] = Vector((1, 1, 0.4 + 0.6 * t))
        frames[kit.IDLE_END] = frames[0]
        kit.keys(obj, 'scale', frames, 'LINEAR')

    def rise_and_burst(obj, k):
        p = Vector(obj.location)
        start = (k * 20) % kit.IDLE_END
        frames_l, frames_s = {}, {}
        hidden, shown = Vector((HIDDEN,) * 3), Vector((1, 1, 1))
        for f in range(0, kit.IDLE_END + 1, 2):
            t = ((f - start) % kit.IDLE_END) / 24.0
            if t < 1:
                frames_l[f] = p + Vector((0, 0, 0.05 * t))
                frames_s[f] = shown * (0.4 + 0.8 * t)
            else:
                frames_l[f] = p
                frames_s[f] = hidden
        frames_l[kit.IDLE_END], frames_s[kit.IDLE_END] = frames_l[0], frames_s[0]
        kit.keys(obj, 'location', frames_l, 'LINEAR')
        kit.keys(obj, 'scale', frames_s, 'CONSTANT')

    idle = [(glow, swell)] + [(b, lambda o, k=k: rise_and_burst(o, k)) for k, b in enumerate(bubbles)]
    nb.clips(lights, idle)
    for b in bubbles:
        b.scale = (1, 1, 1)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NAWAST', {'Build': [24, 48, BUILD_END], 'Idle': [0, 15]}, ortho=3.9, target=(0.1, 0, 0.3), texture=1024)
