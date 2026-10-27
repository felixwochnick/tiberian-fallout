"""
Tiberian Fallout – Temple of Nod (NATMPL), after Tiberian Sun.

On four cells by three (foundation 4 × 3, long along x; on screen from the upper left
to the lower right), like the original's: a long low dome of dark armour, covered
from end to end by four great arched shells that overlap like the plates of an
armadillo, each rimmed in red (house colour) along its front edge, its feet ending in
red claws on the ground. At the -x end (upper left on screen) a tall dark horn rises
out of the dome, curving back and up, with red blades round its root and a lamp on
its tip; at the +x end (lower right) the dome opens in a dark gateway. A red eye sits
on the back shell's front flank near the horn.

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
(extra nodColour), Remap the house colour, Lamp* emissive, Glow* additive.

Nodes:
    Dome         the dome (rises in Build)
    Shell0…3     the arched shells, the back one highest (rise one after another
                 in Build)
    Spire        the horn (rises out of the dome in Build)
    SpireLamp…   the lamp on the horn's tip (the light blinks in Idle, the original's
                 NATMPL_A)
    EyeGlow      the glow over the red eye (pulses in Idle)
Animations (glTF clips)
    Build    one-shot, 3 s: the footing spreads, the dome rises, the shells come up
             one after the other from the back, the horn rises, the lamp comes on
    Idle     loop, 2 s: the lamp on the horn blinks, the eye glows up and fades

Run headless:

    blender -b --factory-startup --python blender/NATMPL.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells are
centred at x = -1.5 … 1.5 and y = -1, 0, 1; origin in the middle on the ground.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nb  # noqa: E402
import NAPOWR as pw  # noqa: E402 – curves

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam
BUILD_END = 90

XC, L = 0.2, 1.8            # the dome's middle and half length along x
W, H = 1.32, 1.0            # its half width and height
SHELLS = ((-1.3, -0.68), (-0.78, -0.08), (-0.18, 0.56), (0.46, 1.18))   # x ranges, back to front
SPIRE_FOOT = Vector((-1.45, 0.12, 0.25))
SPIRE_TOP = Vector((-1.7, 0.3, 2.2))
SPIRE_BEND = Vector((-1.1, 0.18, 1.2))
EYE = Vector((-0.98, -1.08, 0.47))   # on the back shell's front flank
DOME_CONCRETE = '#8a8b8f'
SHELL_CONCRETE = '#3a3b3e'
FOOT_CONCRETE = '#55565a'


def envelope(x, grow=1.0):
    """Half width and height of the dome at x (an ellipsoid), scaled by `grow`."""
    t = max(0.0, 1 - ((x - XC) / L) ** 2)
    return W * math.sqrt(t) * grow, H * math.sqrt(t) * grow


def arch(x, grow, n=16, lift=0.0):
    """Points of the dome's cross-section at x, from the front foot over the top to the back."""
    w, h = envelope(x, grow)
    return [Vector((x, -w * math.sin(a), h * math.cos(a) + lift)) for a in (math.pi / 2 - math.pi * k / n for k in range(n + 1))]


def shell_band(name, mat, x0, x1, grow, thick, steps=5, n=16):
    """An arched plate following the dome from x0 to x1: outer surface at `grow`, inner
    at `grow - thick`, closed at both ends and at the feet."""
    sections = []
    for i in range(steps + 1):
        x = x0 + (x1 - x0) * i / steps
        outer = arch(x, grow, n)
        inner = arch(x, grow - thick, n)[::-1]
        ring = outer + inner + [outer[0]]
        sections.append([Vector((p.x, p.y, max(p.z, 0.0))) for p in ring])
    return nb.loft(name, sections, lambda i, k: mat, cap=mat)


def footing(m, root):
    outline = nb.chamfered(XC, 0, 3.86, 2.84, 0.6)
    top = nb.chamfered(XC, 0, 3.74, 2.72, 0.56)
    body = nb.concrete('Footing', [nb.prism('FootingSlab', m['steel'], outline, top, 0, 0.05, bevel=0.006)], root, FOOT_CONCRETE)
    parts = [nb.prism('FootingDirt', m['dirt'], nb.chamfered(XC, 0, 3.98, 2.96, 0.64), nb.chamfered(XC, 0, 3.98, 2.96, 0.64), 0, 0.008, bevel=0)]
    return body, kit.merge('FootingDetails', parts)


def dome(m, root):
    """The dome (concrete, returned first) and its details: the gateway at +x."""
    sections = [arch(XC - L * 0.995 + 2 * L * 0.995 * i / 24, 1.0, 20) for i in range(25)]
    body = nb.loft('DomeShell', sections, lambda i, k: m['steel'], cap=m['steel'])
    dome_obj = nb.concrete('Dome', [body], root, DOME_CONCRETE)
    parts = []
    # the gateway at the +x end: a dark recess with a red frame
    gx = XC + L * 0.94
    _, gh = envelope(gx)
    parts.append(box('Gate', m['dark'], (0.06, 0.6, 0.42), (gx + 0.02, 0, 0.26), bevel=0.01))
    for s in (-1, 1):
        parts.append(box(f'GatePost{s}', m['remap'], (0.08, 0.06, 0.48), (gx + 0.03, s * 0.33, 0.27), bevel=0.006))
    parts.append(box('GateLintel', m['remap'], (0.08, 0.72, 0.06), (gx + 0.03, 0, 0.52), bevel=0.006))
    parts.append(box('GateStep', m['nplate_dark'], (0.3, 0.8, 0.05), (gx + 0.14, 0, 0.075), bevel=0.006))
    return dome_obj, kit.merge('DomeDetails', parts)


def shell(m, root, k, x0, x1):
    """Arched shell k (concrete, returned first) and its red rim and claws."""
    grow = 1.22 - 0.045 * k   # the back shells highest: each front rim lies over the next shell
    body = nb.concrete(f'Shell{k}', [shell_band(f'Shell{k}Band', m['steel'], x0, x1, grow, 0.06)], root, SHELL_CONCRETE)
    parts = [shell_band(f'Shell{k}Rim', m['remap'], x1 - 0.1, x1 + 0.01, grow + 0.02, 0.1, steps=1)]
    parts.append(shell_band(f'Shell{k}Seam', m['nplate_dark'], x0 + 0.08, x0 + 0.13, grow + 0.006, 0.02, steps=1))
    if k == 0:   # the eye: a red oval plate on the flank, ringed in dark plate
        n = (EYE - Vector((EYE.x, 0, 0))).normalized()
        eye = sphere('Eye', m['remap'], 0.2, EYE, 16)
        eye.scale = (1.3, 0.45, 0.8)
        ring = sphere('EyeRing', m['nplate_dark'], 0.23, EYE - n * 0.02, 16)
        ring.scale = (1.3, 0.4, 0.82)
        parts += [eye, ring]
    # red claws at the feet, curling out
    for s in (-1, 1):
        w, _ = envelope(x1 - 0.1, grow)
        foot = Vector((x1 - 0.12, s * (w - 0.03), 0.1))
        parts.append(nb.spike(f'Shell{k}Claw{s}', m['remap'], foot, (0.45, s * 1.0, 0), 0.42 + 0.04 * k, 0.14, 0.05, droop=0.07))
    # ridges along the top: two dark ribs
    for j, y in enumerate((-0.25, 0.25)):
        pts = []
        for i in range(5):
            x = x0 + 0.15 + (x1 - x0 - 0.3) * i / 4
            w, h = envelope(x, grow)
            z = h * math.sqrt(max(0.0, 1 - (y / w) ** 2)) if w > abs(y) else 0
            pts.append(Vector((x, y, z + 0.005)))
        for i, (p, q) in enumerate(zip(pts, pts[1:])):
            parts.append(beam(f'Shell{k}Ridge{j}_{i}', m['nplate_dark'], p, q, 0.04, 0.02))
    return body, kit.merge(f'Shell{k}Details', parts, Vector((0.5 * (x0 + x1), 0, 0)))


def spire(m, root):
    """The horn: square sections along a curve, tapering (concrete, returned first),
    red blades round its root and its tip; origin at its foot."""
    n = 14
    pts = [pw.bezier(SPIRE_FOOT, SPIRE_BEND, SPIRE_TOP, i / n) for i in range(n + 1)]
    sections = []
    for i, p in enumerate(pts):
        t = i / n
        r = 0.3 * (1 - t) + 0.07 * t
        ahead = pts[min(i + 1, n)] - pts[max(i - 1, 0)]
        ahead.normalize()
        side = ahead.cross(Vector((0, 1, 0))).normalized()
        up = side.cross(ahead).normalized()
        corners = [p + side * r, p + up * r * 0.85, p - side * r, p - up * r * 0.85]
        sections.append(corners + [corners[0]])
    horn = nb.loft('SpireHorn', sections, lambda i, k: m['steel'], cap=m['steel'])
    for poly in horn.data.polygons:
        poly.use_smooth = False
    body = nb.concrete('Spire', [horn], root, '#38393c', SPIRE_FOOT)
    parts = []
    for k, a in enumerate((-60, 30, 120, 210)):   # red blades round the root, sweeping down
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        root_pt = SPIRE_FOOT + Vector((0, 0, 0.55)) + d * 0.18
        parts.append(nb.spike(f'RootBlade{k}', m['remap'], root_pt, d + Vector((0, 0, -0.55)), 0.5, 0.14, 0.04, droop=0.05))
    for k, sgn in enumerate((-1, 1)):   # red trims up the horn's two side edges
        for i in range(int(n * 0.55)):
            def edge(j):
                t = j / n
                p = pw.bezier(SPIRE_FOOT, SPIRE_BEND, SPIRE_TOP, t)
                ahead = (pw.bezier(SPIRE_FOOT, SPIRE_BEND, SPIRE_TOP, min(1, t + 0.02)) - pw.bezier(SPIRE_FOOT, SPIRE_BEND, SPIRE_TOP, max(0, t - 0.02))).normalized()
                side = ahead.cross(Vector((0, 1, 0))).normalized()
                r = 0.3 * (1 - t) + 0.07 * t
                return p + side * sgn * (r + 0.01)
            parts.append(beam(f'HornTrim{k}_{i}', m['remap'], edge(i + 2), edge(i + 3), 0.04, 0.04))
    parts.append(cylinder('TipCap', m['nplate_dark'], 0.09, 0.05, SPIRE_TOP + Vector((0, 0, 0.0)), segments=12, bevel=0.006))
    parts.append(cylinder('TipMast', m['nsteel'], 0.012, 0.18, SPIRE_TOP + Vector((0.03, 0, 0.12)), segments=8, bevel=0))
    return body, kit.merge('SpireDetails', parts, SPIRE_FOOT)


def build():
    root = nb.start('NodTemple', 'NodTemple', BUILD_END)
    m = nb.materials()
    m['glow_white'] = kit.material('GlowWhite', (0, 0, 0), 1.0, emission=kit.srgb('#bcd4ff'), strength=3, alpha=0.3)
    m['lamp_blue'] = kit.material('LampBlue', kit.srgb('#d8e8ff'), 0.2, emission=kit.srgb('#9ac0ff'), strength=8)
    keys = kit.keys

    foot_group = kit.parent(kit.empty('FootingGroup', (XC, 0, 0)), root)
    fbody, fdetails = footing(m, root)
    kit.parent(fbody, foot_group)
    kit.parent(fdetails, fbody)
    keys(foot_group, 'scale', {0: Vector((0.05, 0.05, 1)), 12: Vector((1.02, 1.02, 1)), 15: Vector((1, 1, 1))})

    lift = kit.parent(kit.empty('Dome'), root)
    dbody, ddetails = dome(m, root)
    kit.parent(dbody, lift)
    kit.parent(ddetails, dbody)
    nb.rise(lift, 8, 22, H + 0.1)

    eye_holder = None
    for k, (x0, x1) in enumerate(SHELLS):
        holder = kit.parent(kit.empty(f'Shell{k}', (0.5 * (x0 + x1), 0, 0)), root)
        sbody, sdetails = shell(m, root, k, x0, x1)
        kit.parent(sbody, holder)
        kit.parent(sdetails, sbody)
        eye_holder = eye_holder or sbody
        nb.rise(holder, 26 + 8 * k, 16, H + 0.3)

    spire_lift = kit.parent(kit.empty('Spire', SPIRE_FOOT), root)
    hbody, hdetails = spire(m, root)
    kit.parent(hbody, spire_lift)
    kit.parent(hdetails, hbody)
    low = SPIRE_FOOT - Vector((0, 0, SPIRE_TOP.z + 0.3))
    keys(spire_lift, 'location', {0: low, 50: low, 78: SPIRE_FOOT + Vector((0, 0, 0.015)), 82: Vector(SPIRE_FOOT)})

    tip = SPIRE_TOP + Vector((0, 0, 0.025))
    housing, light = kit.beacon('SpireLamp', m, tip, 'white', m['lamp_blue'])
    housing = kit.parent(kit.merge('SpireLamp', [housing], tip), hbody)
    kit.parent(light, hbody)
    kit.pop(housing, 82, 5)

    n = (EYE - Vector((EYE.x, 0, 0))).normalized()
    eye_glow = kit.merge('EyeGlow', [sphere('EyeHalo', m['glow_red'], 0.22, EYE + n * 0.03, 16)], EYE + n * 0.03)
    eye_glow.scale = (1.4, 0.5, 0.9)
    kit.parent(eye_glow, eye_holder)   # rides up with the back shell

    def throb(obj):
        base = Vector(obj.scale)
        frames = {}
        for f in range(0, kit.IDLE_END + 1, 3):
            t = (math.sin(2 * math.pi * f / kit.IDLE_END) + 1) / 2
            frames[f] = base * (0.75 + 0.35 * t)
        frames[kit.IDLE_END] = frames[0]
        kit.keys(obj, 'scale', frames, 'LINEAR')

    nb.clips([(light, kit.flashes((0, 5), (10, 5), (30, 12)))], [(eye_glow, throb)])
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NATMPL', {'Build': [30, 60, BUILD_END], 'Idle': [0, 15]}, ortho=5.2, target=(0.1, 0, 0.8), texture=1024)
