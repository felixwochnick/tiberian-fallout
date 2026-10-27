"""
Tiberian Fallout – GDI firestorm generator (GAFIRE, Firestorm), after the original.

A khaki plinth with cut corners (foundation 3 × 2 cells). At its right end the
emitter: a round camouflaged well with a pale violet steel rim, a dark bowl inside
with a coil core in its middle, and behind it, half over the well, the camouflaged
generator housing with a grey cap. At its left end the capacitor works: a dark steel
block with two slanted pylons (their tips in the house colour) reaching towards the
well, sloped armour plates in the house colour in front of them, and a ramp plate in
the house colour on the plinth's front.

Materials as for the barracks (see GAPILE.py): Camo_* is the baked camouflage in a
pale shade of the house colour, Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name; no channel is
shared between them)
    Build    one-shot, 2.2 s: the plinth spreads, the well and the works rise out of
             the ground, the housing closes over the well, the pylons swing up, the
             lights come on
    Idle     loop, 2 s: the coil core glows softly, the lamps blink
    Fire     loop, 2 s (while the firestorm is up): a blue energy ring burns round the
             bowl and pulses, lightning whirls in the bowl and flickers, the pylons'
             tips glow; all of it hidden at rest (and on the clip's first and last
             frame: a short flicker where the loop wraps)

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAFIRE.py [-- --preview 0,30,66 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -1.5 … 1.5 and y -1 … 1.
"""
import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import gdibuilding as gb  # noqa: E402
import GAPLUG as plug  # noqa: E402 – ring()

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAFIRE.glb')
BLEND = os.path.join(HERE, 'GAFIRE.blend')

BUILD_END = 66
FIRE_END = 60
DECK = 0.08                       # top of the plinth
WELL = Vector((0.72, -0.18, DECK))
WELL_R = 0.56                     # outer radius of the well
BOWL_R = 0.4                      # inner radius (the rim)
WELL_TOP = DECK + 0.2
HOUSING = Vector((0.66, 0.5, DECK))
WORKS = Vector((-0.78, 0.12, DECK))

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m['plinth'] = material('PlinthKhaki', srgb('#8a7550'), 0.95)
    m['rim'] = material('RimViolet', srgb('#b9b6d6'), 0.35, 0.8)
    m['machine'] = material('MachineDark', srgb('#3c3f44'), 0.55, 0.7)
    m['remap_dark'] = material('RemapDark', srgb('#9a7c22'), 0.6, 0.15)
    m['glow_blue'] = material('GlowFirestorm', (0, 0, 0), 1.0, emission=srgb('#6f7dff'), strength=6, alpha=0.5)
    m['glow_bolt'] = material('GlowBolt', (0, 0, 0), 1.0, emission=srgb('#e0e6ff'), strength=8, alpha=0.8)
    m['coil'] = material('LampCoil', srgb('#a8b4ff'), 0.2, emission=srgb('#7f90ff'), strength=4)
    return m


# --------------------------------------------------------------------------- parts

def plinth(m):
    outline = gb.chamfered(-1.46, -0.96, 1.46, 0.96, 0.28)
    parts = [gb.slab('Plinth', m['plinth'], outline, DECK, inset=0.04, bevel=0.006)]
    for k in range(5):  # tread seams
        x = -1.0 + k * 0.5
        parts.append(box(f'Seam{k}', m['concrete_dark'], (0.012, 1.6, 0.003), (x, 0, DECK + 0.001), bevel=0))
    parts.append(box('RampPlate', m['remap'], (0.36, 0.22, 0.03), (-0.05, -0.72, DECK + 0.015), bevel=0.006, rotation=(math.radians(-6), 0, 0)))
    parts.append(box('RampStripe', m['remap_dark'], (0.36, 0.02, 0.032), (-0.05, -0.68, DECK + 0.016), bevel=0, rotation=(math.radians(-6), 0, 0)))
    for k, (x, y) in enumerate(((1.25, -0.75), (-1.25, -0.75), (1.25, 0.75))):
        parts.append(box(f'Bollard{k}', m['steel'], (0.06, 0.06, 0.08), (x, y, DECK + 0.04), bevel=0.008))
    return kit.merge('Plinth', parts)


def well(m, root):
    """The camouflaged well, its rim, the bowl and the coil core; origin at its foot."""
    w = WELL
    shell = gb.camo(gb.lathe('WellWall', m['sand'], ((WELL_R, 0), (WELL_R, 0.05), (WELL_R - 0.06, WELL_TOP - DECK - 0.02), (BOWL_R + 0.06, WELL_TOP - DECK)),
                             (w.x, w.y, DECK), 40), root)
    parts = [
        gb.lathe('Rim', m['rim'], ((BOWL_R + 0.07, WELL_TOP - DECK - 0.005), (BOWL_R + 0.065, WELL_TOP - DECK + 0.02), (BOWL_R + 0.005, WELL_TOP - DECK + 0.02),
                                   (BOWL_R, WELL_TOP - DECK - 0.01)), (w.x, w.y, DECK), 40),
        cylinder('Bowl', m['dark'], BOWL_R, 0.01, (w.x, w.y, WELL_TOP - 0.06), segments=40, bevel=0),
        cylinder('CoreBase', m['machine'], 0.12, 0.08, (w.x, w.y, WELL_TOP - 0.03), segments=20, bevel=0.006),
        cylinder('CoreSpike', m['steel_light'], 0.05, 0.12, (w.x, w.y, WELL_TOP + 0.04), segments=16, bevel=0.003, radius2=0.012),
    ]
    for k in range(8):   # struts down the well's wall, emitters round the bowl
        a = 2 * math.pi * (k + 0.5) / 8
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(beam(f'WellRib{k}', m['steel'], w + d * (WELL_R + 0.008) + Vector((0, 0, 0.04)), w + d * (WELL_R - 0.05) + Vector((0, 0, WELL_TOP - DECK - 0.03)),
                          0.03, 0.012))
        parts.append(box(f'Emitter{k}', m['steel'], (0.05, 0.03, 0.05), w + d * (BOWL_R - 0.03) + Vector((0, 0, WELL_TOP - DECK - 0.03)), bevel=0.006,
                         rotation=(0, 0, a)))
    coils = [cylinder(f'Coil{k}', m['coil'], 0.085 - 0.012 * k, 0.012, (w.x, w.y, WELL_TOP + 0.0 + k * 0.025), segments=20, bevel=0) for k in range(3)]
    return shell, kit.merge('WellDetails', parts, (w.x, w.y, DECK)), kit.merge('Coils', coils, (w.x, w.y, WELL_TOP))


def housing(m, root):
    """The generator housing behind the well: a camouflaged hump lying along x with
    sloped ends and a grey cap; origin at its foot."""
    h = HOUSING
    profile = [(-0.3, 0), (0.28, 0), (0.28, 0.25), (0.2, 0.4), (0.0, 0.46), (-0.2, 0.42), (-0.3, 0.3)]
    body = gb.prism('Housing', m['sand'], [(h.y + y, h.z + z) for y, z in profile], h.x - 0.48, h.x + 0.48, 'X', bevel=0.03)
    body.modifiers['Bevel'].segments = 3
    shell = gb.camo(body, root)
    cap = gb.prism('Cap', m['steel_light'], [(h.y + y, h.z + z) for y, z in ((-0.15, 0.43), (0.15, 0.43), (0.12, 0.49), (-0.12, 0.49))],
                   h.x - 0.3, h.x + 0.3, 'X', bevel=0.008)
    parts = [cap,
             box('CapRidge', m['steel'], (0.62, 0.05, 0.02), h + Vector((0, 0, 0.495)), bevel=0.004),
             box('Vent', m['dark'], (0.012, 0.18, 0.1), h + Vector((0.485, 0.0, 0.22)), bevel=0.002),
             box('Band', m['remap'], (0.975, 0.03, 0.03), h + Vector((0, -0.29, 0.2)), bevel=0.003)]
    return shell, kit.merge('HousingDetails', parts, h)


def works(m, root):
    """The capacitor works on the left: (dark block with armour, list of pylons)."""
    c = WORKS
    parts = [
        box('Block', m['machine'], (0.62, 0.62, 0.26), c + Vector((0, 0, 0.13)), bevel=0.02),
        box('BlockTop', m['steel'], (0.5, 0.5, 0.04), c + Vector((0, 0, 0.28)), bevel=0.008),
        cylinder('Capacitor0', m['steel_light'], 0.07, 0.24, c + Vector((-0.18, 0.18, 0.4)), segments=16, bevel=0.005),
        cylinder('Capacitor1', m['steel_light'], 0.07, 0.2, c + Vector((-0.18, -0.02, 0.38)), segments=16, bevel=0.005),
        *[cylinder(f'CapRing{k}', m['remap'], 0.074, 0.014, c + Vector((-0.18, 0.18 - 0.2 * (k // 2), 0.32 + 0.1 * (k % 2))), segments=16, bevel=0) for k in range(4)],
        # cable runs over the plinth to the well
        beam('Cable0', m['dark'], c + Vector((0.31, -0.05, 0.03)), WELL + Vector((-WELL_R, 0.05, 0.03)), 0.04, 0.03),
        beam('Cable1', m['dark'], c + Vector((0.31, 0.15, 0.03)), HOUSING + Vector((-0.48, -0.05, 0.03)), 0.04, 0.03),
    ]
    armour = gb.camo(kit.hexahedron('Armour', m['sand'], [
        (c.x - 0.36, c.y - 0.34, c.z), (c.x + 0.2, c.y - 0.34, c.z), (c.x + 0.2, c.y - 0.2, c.z), (c.x - 0.36, c.y - 0.2, c.z),
        (c.x - 0.33, c.y - 0.26, c.z + 0.3), (c.x + 0.17, c.y - 0.26, c.z + 0.3), (c.x + 0.17, c.y - 0.2, c.z + 0.3), (c.x - 0.33, c.y - 0.2, c.z + 0.3),
    ], 0.012), root)
    plates = []
    for k, x in enumerate((-0.25, 0.05)):
        p = c + Vector((x, -0.42, 0))
        plates.append(kit.hexahedron(f'RedPlate{k}', m['remap'], [
            (p.x - 0.13, p.y - 0.14, p.z), (p.x + 0.13, p.y - 0.14, p.z), (p.x + 0.13, p.y + 0.06, p.z), (p.x - 0.13, p.y + 0.06, p.z),
            (p.x - 0.12, p.y + 0.02, p.z + 0.22), (p.x + 0.12, p.y + 0.02, p.z + 0.22), (p.x + 0.12, p.y + 0.08, p.z + 0.22), (p.x - 0.12, p.y + 0.08, p.z + 0.22),
        ], 0.01))
    block = kit.merge('Works', parts + plates, c)
    pylons = []
    for k, y in enumerate((-0.05, 0.25)):
        foot = c + Vector((0.12, y, 0.3))
        tip = foot + Vector((0.42, 0, 0.34 - 0.06 * k))
        pylon = kit.merge(f'Pylon{k}', [
            cylinder(f'PylonHinge{k}', m['steel'], 0.05, 0.1, foot, rotation=(math.pi / 2, 0, 0), segments=16, bevel=0.004),
            beam(f'PylonArm{k}', m['machine'], foot, tip, 0.07, 0.06),
            beam(f'PylonRib{k}', m['steel_light'], foot + Vector((0.05, 0, 0.07)), tip + Vector((-0.03, 0, 0.03)), 0.02, 0.012),
            box(f'PylonTip{k}', m['remap'], (0.1, 0.09, 0.08), tip, bevel=0.01),
            cylinder(f'PylonPoint{k}', m['steel_light'], 0.025, 0.08, tip + Vector((0.06, 0, 0.0)), rotation=(0, math.pi / 2, 0), segments=10, bevel=0.002, radius2=0.006),
        ], foot)
        pylons.append((pylon, tip + Vector((0.11, 0, 0))))
    return armour, block, pylons


def bolt(name, mat, centre, radius, seed):
    """A jagged lightning bolt from the core out to the bowl's rim (in the plane)."""
    rnd = random.Random(seed)
    a = rnd.uniform(0, 2 * math.pi)
    pts = []
    n = 6
    for k in range(n + 1):
        r = 0.06 + (radius - 0.06) * k / n
        aa = a + rnd.uniform(-0.25, 0.25) * (k > 0)
        pts.append(Vector(centre) + Vector((math.cos(aa) * r, math.sin(aa) * r, rnd.uniform(-0.02, 0.05) * (0 < k < n))))
    return kit.merge(name, [beam(f'{name}_{k}', mat, p, q, 0.012, 0.012) for k, (p, q) in enumerate(zip(pts, pts[1:]))], centre)


# --------------------------------------------------------------------------- model

def build():
    gb.start('GDIFirestormGenerator', BUILD_END)
    m = materials()
    root = kit.empty('GDIFirestormGenerator')
    keys = kit.keys
    H = kit.HIDDEN

    base = kit.parent(plinth(m), root)
    keys(base, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 13: Vector((1.02, 1.02, 1)), 16: Vector((1, 1, 1))})

    # ---- the well rises (moved, never scaled: the energy in it animates)
    wg = kit.parent(kit.empty('WellGroup', WELL), root)
    shell, details, coils = well(m, root)
    for obj in (shell, details, coils):
        kit.parent(obj, wg)
    keys(wg, 'location', {0: WELL + Vector((0, 0, -0.4)), 6: WELL + Vector((0, 0, -0.4)), 24: WELL + Vector((0, 0, 0.01)), 27: WELL})

    # ---- the housing slides up behind it
    hg = kit.parent(kit.empty('HousingGroup', HOUSING), root)
    for obj in housing(m, root):
        kit.parent(obj, hg)
    keys(hg, 'location', {0: HOUSING + Vector((0, 0, -0.6)), 16: HOUSING + Vector((0, 0, -0.6)), 34: HOUSING + Vector((0, 0, 0.01)), 37: HOUSING})

    # ---- the works rise, the pylons swing up
    kg = kit.parent(kit.empty('WorksGroup', WORKS), root)
    armour, block, pylons = works(m, root)
    for obj in (armour, block):
        kit.parent(obj, kg)
    keys(kg, 'location', {0: WORKS + Vector((0, 0, -0.5)), 10: WORKS + Vector((0, 0, -0.5)), 28: WORKS + Vector((0, 0, 0.01)), 31: WORKS})
    tips = []
    for k, (pylon, tip) in enumerate(pylons):
        swing = kit.parent(kit.empty(f'PylonSwing{k}', pylon.location), kg)
        kit.parent(pylon, swing)
        keys(swing, 'rotation_euler', {0: Vector((0, math.radians(45), 0)), 34 + 4 * k: Vector((0, math.radians(45), 0)),
                                       44 + 4 * k: Vector((0, math.radians(-3), 0)), 47 + 4 * k: Vector((0, 0, 0))})
        tips.append((swing, tip))

    # ---- lamps
    lights = []
    gb.beacon('HousingLamp', m, HOUSING + Vector((0.4, 0.2, 0.42)), 'red', hg, 50, kit.flashes((0, 8), (30, 8)), lights)
    gb.beacon('WorksLamp', m, WORKS + Vector((0.2, 0.22, 0.3)), 'amber', kg, 52, kit.flashes((15, 10), (45, 10)), lights)
    gb.beacon('CornerLamp', m, Vector((1.25, -0.75, DECK + 0.08)), 'green', root, 54, kit.flashes((0, 40)), lights)

    # ---- Fire: the firestorm energy (hidden at rest)
    core = WELL + Vector((0, 0, WELL_TOP - DECK))
    ring = kit.parent(kit.merge('EnergyRing', [
        plug.ring('EnergyBand', m['glow_blue'], ((BOWL_R - 0.03, 0), (BOWL_R + 0.03, 0), (BOWL_R + 0.015, 0.07), (BOWL_R - 0.015, 0.07)), core, 40),
    ], core), wg)
    swirl = kit.parent(kit.empty('Lightning', core + Vector((0, 0, -0.01))), wg)
    bolts = []
    for k in range(4):
        b = kit.parent(bolt(f'Bolt{k}', m['glow_bolt'], core + Vector((0, 0, -0.01)), BOWL_R - 0.02, 7 + k), swirl)
        bolts.append(b)
    flare = kit.parent(sphere('CoreFlare', m['glow_bolt'], 0.12, core + Vector((0, 0, 0.06)), 12), wg)
    tip_glows = []
    for k, (swing, tip) in enumerate(tips):
        g = kit.parent(kit.merge(f'TipGlow{k}', [sphere(f'TipGlowS{k}', m['glow_blue'], 0.07, tip, 10),
                                                  sphere(f'TipGlowC{k}', m['glow_bolt'], 0.025, tip, 8)], tip), swing)
        tip_glows.append(g)

    idle = [(coils, lambda o: gb.pulse(o, 0.95, 1.05, 2))]
    gb.clips(idle, lights)

    # Every energy channel is hidden on the first and the last frame and lit in between:
    # the glTF export takes the first frame of each clip as the pose at rest (hidden),
    # and the clip loops with a dip of two frames at its seam (a flicker among flickers).
    def lit_loop(obj, frames, interpolation):
        frames[1] = frames.pop(0)
        frames[FIRE_END - 1] = frames[1]
        frames[0] = frames[FIRE_END] = Vector((H, H, H))
        keys(obj, 'scale', frames, interpolation)
        kit.to_track(obj, 'Fire')

    def flicker(obj, seed, low, high):
        rnd = random.Random(seed)
        lit_loop(obj, {f: Vector((1, 1, 1)) * rnd.uniform(low, high) for f in range(0, FIRE_END - 2, 2)}, 'LINEAR')

    lit_loop(ring, {f: Vector((1, 1, 1)) * (1.0 + 0.04 * math.sin(2 * math.pi * 4 * f / FIRE_END)) for f in range(0, FIRE_END - 2, 3)}, 'LINEAR')
    keys(swirl, 'rotation_euler', {0: Vector((0, 0, 0)), FIRE_END: Vector((0, 0, 2 * math.pi * 2))}, 'LINEAR')
    kit.to_track(swirl, 'Fire')
    for k, b in enumerate(bolts):
        lit_loop(b, {f: (Vector((1, 1, 1)) if (f // 3 + k) % 4 != 0 else Vector((H, H, H))) for f in range(0, FIRE_END - 2, 3)}, 'CONSTANT')
    flicker(flare, 3, 0.6, 1.1)
    for k, g in enumerate(tip_glows):
        flicker(g, 11 + k, 0.7, 1.2)
    for obj in [ring, flare, *bolts, *tip_glows]:
        obj.scale = (H, H, H)   # hidden at rest: only Fire shows the firestorm
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    gb.run(build, OUT, BLEND, scale=3.9, target=(0, 0, 0.25))
