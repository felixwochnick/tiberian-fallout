"""
Tiberian Fallout – Nod advanced power plant (NAAPWR), after Tiberian Sun.

Three reactor cones in a row from the front to the back (foundation 2 × 3 cells, long
along y): in front the big cone of the power plant on its oval stained platform with
the long red blades (the parts of NAPOWR.py), behind it two smaller cones on a dark
concrete plinth, each standing on a flared skirt. The cones are broad, tapering, mid
grey concrete with dark ribs, open on top (a dark shaft inside a light lip) with two
thick red bands round the rim; pipes
and a cable link them at mid height. On screen the row runs from the lower left (the
big cone) to the upper right.

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
(extra nodColour), Remap the house colour, Lamp* emissive, Glow* additive.

Nodes: NodAdvancedPowerPlant (root) – PlatformGroup (deck, blades, fins), Plinth,
Cone0Group … Cone2Group (each a cone with its ribs, bands, open top, Cone…Glow and lamps),
Pipes.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.4 s: the platform and the plinth rise out of the ground, the
             blades shoot out, the three cones rise one after the other, the pipes
             grow between them, the lamps come on
    Idle     loop, 2 s: the reactors glow up and fade round their red bands (the
             original's NAAPWR_A overlay), one after the other; lamps blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/NAAPWR.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells of the
foundation are centred at x = ±0.5, y = -1, 0, 1.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nod  # noqa: E402
import NAPOWR as pw  # noqa: E402 – the power plant's platform, blades and bands

BUILD_END = 72
box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam

PLATFORM = Vector((0, -0.62, 0))    # the big cone's platform (NAPOWR's, a bit smaller)
PLATFORM_SCALE = 0.9
PLINTH_TOP = 0.08
# the cones: (centre on the ground, foot radius, top radius, height of the flank, standing on)
CONES = (
    (PLATFORM + Vector((0, 0.08 * PLATFORM_SCALE, 0)), 0.5, 0.31, 1.25, pw.DECK * PLATFORM_SCALE),
    (Vector((0.04, 0.46, 0)), 0.34, 0.21, 1.05, PLINTH_TOP),
    (Vector((0.42, 1.16, 0)), 0.3, 0.19, 0.8, PLINTH_TOP),
)
CONCRETE = '#9a9b9c'
PLINTH_CONCRETE = '#5b5c5f'


def radius_at(foot, top, height, z):
    """Radius of a cone's flank at height z above its foot (straight flank)."""
    t = max(0.0, min(1.0, z / height))
    return foot + (top - foot) * t


def reactor(m, root, k, centre, foot, top, height, ground):
    """One reactor cone: the concrete shell with a flared skirt (returned first), its
    details (ribs, red bands, the shaft in the open top) and the glow round the bands; origin on its
    foot."""
    base = centre + Vector((0, 0, ground))
    r = lambda z: radius_at(foot, top, height, z)  # noqa: E731
    skirt = foot * 1.12
    profile = [(skirt, 0.0), (skirt - 0.01, 0.035), (foot * 1.03, 0.1)] + [(r(z), z) for z in (0.16, 0.45, 0.75)] + [(r(height), height)]
    profile += [(top - 0.045, height), (top - 0.055, height - 0.1)]   # the lip of the open top
    shell = nod.concrete(f'Cone{k}', [nod.lathe(f'Cone{k}Shell', m['steel'], profile, base, 32)], root, CONCRETE, base)
    parts = [
        # the dark shaft inside the open top
        cylinder(f'Cone{k}Shaft', m['dark'], top - 0.05, 0.01, base + Vector((0, 0, height - 0.095)), segments=32, bevel=0),
        # a dark ring where the skirt meets the flank
        pw.band(f'Cone{k}Collar', m['nplate_dark'], base, ((foot * 1.04, 0.09), (foot * 1.1, 0.09), (foot * 1.1, 0.13), (foot * 1.03, 0.13))),
    ]
    for j in range(8):  # dark ribs up the flank
        a = 2 * math.pi * (j + 0.5) / 8
        d = Vector((math.cos(a), math.sin(a), 0))
        lo, hi = 0.14, height - 0.2
        parts.append(beam(f'Cone{k}Rib{j}', m['nplate'], base + d * (r(lo) + 0.005) + Vector((0, 0, lo)),
                          base + d * (r(hi) + 0.005) + Vector((0, 0, hi)), 0.022 * foot / 0.36 + 0.006, 0.014))
    for i, z in enumerate((height - 0.13, height - 0.04)):  # two thick red bands round the rim
        lo, hi = z - 0.035, z + 0.035
        parts.append(pw.band(f'Cone{k}Band{i}', m['remap'], base, ((r(lo) - 0.01, lo), (r(lo) + 0.02, lo), (r(lo) + 0.028, lo + 0.008),
                                                                    (r(hi) + 0.028, hi - 0.008), (r(hi) + 0.02, hi), (r(hi) - 0.01, hi))))
    z = height - 0.085
    parts.append(pw.band(f'Cone{k}Gap', m['nplate_dark'], base, ((r(z) - 0.01, z - 0.012), (r(z) + 0.016, z - 0.012),
                                                                (r(z) + 0.016, z + 0.012), (r(z) - 0.01, z + 0.012))))
    details = kit.merge(f'Cone{k}Details', parts, base)
    glow = pw.ring_glow(m, base + Vector((0, 0, height - 0.085)), r(height - 0.085) + 0.055, 0.2)
    glow.name = f'Cone{k}Glow'
    return shell, details, glow


def plinth(m, root):
    """The dark concrete plinth under the two small cones; origin on the ground."""
    outline = nod.chamfered(0.2, 0.83, 1.12, 1.34, 0.3)
    top = nod.chamfered(0.2, 0.83, 1.06, 1.28, 0.27)
    slab = nod.concrete('Plinth', [nod.prism('PlinthSlab', m['steel'], outline, top, 0, PLINTH_TOP)], root, PLINTH_CONCRETE)
    parts = [nod.prism('PlinthDirt', m['dirt'], nod.chamfered(0.2, 0.83, 1.22, 1.44, 0.34), nod.chamfered(0.2, 0.83, 1.22, 1.44, 0.34), 0, 0.01, bevel=0)]
    # a red trim along the front edges, as on the other Nod buildings
    for name, a, b in (('TrimL', (-0.36, 0.48), (-0.36, 1.18)), ('TrimF', (-0.06, 0.16), (0.46, 0.16)), ('TrimR', (0.76, 0.48), (0.76, 1.18))):
        p, q = Vector((*a, PLINTH_TOP * 0.55)), Vector((*b, PLINTH_TOP * 0.55))
        d = (q - p).normalized()
        out = Vector((d.y, -d.x, 0)) if name != 'TrimL' else Vector((-d.y, d.x, 0))
        parts.append(beam(name, m['remap'], p + out * 0.005, q + out * 0.005, 0.012, 0.03))
    # hatches on the plinth
    for i, (x, y) in enumerate(((-0.24, 1.3), (0.62, 0.3))):
        parts.append(box(f'Hatch{i}', m['nplate_dark'], (0.14, 0.14, 0.012), (x, y, PLINTH_TOP + 0.004), bevel=0.003))
        parts.append(box(f'HatchBar{i}', m['nsteel'], (0.1, 0.018, 0.006), (x, y, PLINTH_TOP + 0.012), bevel=0))
    return slab, kit.merge('PlinthDetails', parts)


def pipes(m):
    """The pipes and the cable from cone to cone at mid height; origin at the first."""
    parts = []
    (c0, f0, t0, h0, g0), (c1, f1, t1, h1, g1), (c2, f2, t2, h2, g2) = CONES
    for k, ((ca, fa, ta, ha, ga), (cb, fb, tb, hb, gb), za, zb) in enumerate((
            (CONES[0], CONES[1], 0.5, 0.42), (CONES[1], CONES[2], 0.34, 0.3))):
        d = (cb - ca).normalized()
        a = ca + d * (radius_at(fa, ta, ha, za) - 0.01) + Vector((0, 0, ga + za))
        b = cb - d * (radius_at(fb, tb, hb, zb) - 0.01) + Vector((0, 0, gb + zb))
        mid = (a + b) / 2 - Vector((0, 0, 0.07))
        side = Vector((-d.y, d.x, 0))
        n = 8
        pts = [pw.bezier(a, mid, b, i / n) for i in range(n + 1)]
        parts += pw.tube(f'Pipe{k}', m['nsteel'], pts, 0.034)
        thin = [p + side * 0.06 + Vector((0, 0, 0.05)) for p in pts]
        parts += pw.tube(f'Cable{k}', m['nplate_dark'], thin, 0.013, 8)
        for t in (0.25, 0.75):
            p, q = pw.bezier(a, mid, b, t), pw.bezier(a, mid, b, t + 0.03)
            ring = cylinder(f'Clamp{k}{t}', m['nplate_dark'], 0.046, 0.034, p, segments=10, bevel=0)
            ring.rotation_mode = 'QUATERNION'
            ring.rotation_quaternion = (q - p).to_track_quat('Z', 'Y')
            parts.append(ring)
            # the clamp's foot down to the ground/plinth
            parts.append(beam(f'Stay{k}{t}', m['nplate'], p - Vector((0, 0, 0.04)), Vector((p.x, p.y, PLINTH_TOP - 0.01)), 0.02, 0.02))
    return kit.merge('Pipes', parts, CONES[0][0])


def build():
    root = nod.start('NodAdvancedPowerPlant', 'NodAdvancedPowerPlant', BUILD_END)
    m = nod.materials()
    m['glow_white'] = kit.material('GlowWhite', (0, 0, 0), 1.0, emission=kit.srgb('#fff2c8'), strength=3, alpha=0.25)
    keys = kit.keys

    # ---- the big cone's platform (the power plant's, scaled down a little)
    group = kit.parent(kit.empty('PlatformGroup', PLATFORM), root)
    deck, details = pw.platform(m, root)
    movers = [deck, details]
    for i, a in enumerate((200, 245, 285, 330, 160)):
        movers.append(pw.blade(m, i, math.radians(a)))
    for i, a in enumerate((215, 250, 290, 325)):
        movers.append(pw.fin(m, i, math.radians(a)))
    for obj in movers:
        obj.location = PLATFORM + (obj.location * PLATFORM_SCALE)
        obj.scale = Vector((PLATFORM_SCALE,) * 3)
    kit.parent(deck, group)
    kit.parent(details, deck)
    for k, obj in enumerate(movers[2:]):
        kit.parent(obj, group)
        kit.pop(obj, 14 + 2 * k, 7)
    nod.rise(group, 0, 16, 0.24)

    # ---- the plinth of the small cones
    slab, plinth_details = plinth(m, root)
    plinth_group = kit.parent(kit.empty('Plinth'), root)
    kit.parent(slab, plinth_group)
    kit.parent(plinth_details, slab)
    nod.rise(plinth_group, 4, 14, PLINTH_TOP + 0.04)

    # ---- the cones rise one after the other (translation: their lamps blink in Idle)
    idle, lights = [], []
    for k, (centre, foot, top, height, ground) in enumerate(CONES):
        cone_group = kit.parent(kit.empty(f'Cone{k}Group'), root)
        shell, cone_details, glow = reactor(m, root, k, centre, foot, top, height, ground)
        kit.parent(shell, cone_group)
        kit.parent(cone_details, shell)
        kit.parent(glow, shell)
        start = 14 + 8 * k
        low = Vector((0, 0, -(ground + height + 0.3)))
        keys(cone_group, 'location', {0: low, start: low, start + 22: Vector((0, 0, 0.012)), start + 26: Vector((0, 0, 0))})

        def throb(obj, phase):
            base = Vector(obj.scale)
            frames = {}
            for f in range(0, kit.IDLE_END + 1, 3):
                t = (math.sin(2 * math.pi * (2 * f / kit.IDLE_END + phase)) + 1) / 2
                frames[f] = Vector((base.x, base.y, base.z * (0.4 + 0.6 * t)))
            frames[kit.IDLE_END] = frames[0]
            kit.keys(obj, 'scale', frames, 'LINEAR')

        idle.append((glow, lambda o, p=0.15 + 0.17 * k: throb(o, p)))
        # white lamps on the flank (two on the big cone, one on the others)
        for j, (a, z) in enumerate(((250, 0.35), (300, 0.66))[:2 if k == 0 else 1]):
            d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
            at = centre + d * (radius_at(foot, top, height, z) + 0.01) + Vector((0, 0, ground + z - 0.03))
            housing, light = kit.beacon(f'Cone{k}Lamp{j}', m, at, 'white', m['lamp_white'])
            housing = kit.parent(kit.merge(f'Cone{k}Lamp{j}', [housing], at), shell)
            kit.parent(light, shell)
            kit.pop(housing, 50 + 3 * k + 2 * j, 5)
            lights.append((light, kit.flashes(((k * 2 + j) * 11, 6), ((k * 2 + j) * 11 + 30, 3))))

    # ---- the pipes grow between the cones
    pipe_obj = kit.parent(pipes(m), root)
    kit.pop(pipe_obj, 50, 10)
    # an amber lamp on the plinth's front corner
    lights.append((nod.lamp(m, slab, 'PlinthLamp', (0.66, 0.52, PLINTH_TOP), 'amber', 56), kit.flashes((5, 4), (14, 4), (40, 6))))

    nod.clips(lights, idle)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, 'NAAPWR', {'Build': [BUILD_END // 3, 2 * BUILD_END // 3, BUILD_END], 'Idle': [0, 8, 15]},
             ortho=3.6, target=(0.0, 0.1, 0.5))
