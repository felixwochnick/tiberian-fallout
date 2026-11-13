"""
Tiberian Fallout – Nod Banshee (SCRIN), after Tiberian Sun Firestorm.

A VTOL strike craft, after the build icon and Tiberium Essence's Banshee: a flying
wing like a manta – broad, flat and faceted, its back edge rounded, sloping from a
raised middle down to sharp edges, its front cut into two claws that sweep forward
and droop a little at the tips; red stripes (house colour) run along the edges and
the claws, dark seams across the plates. On the middle a raised spine: the cockpit's
dark bubble in front, a keel under it reaching into the notch between the claws, two
engine tubes beside it with red-rimmed intakes and glowing exhausts at the back. Two
plasma (proton) cannons hang under the wing roots and reach out of the notch, each
with a glowing green canister in a cage; under each wing a lift fan that glows and
blows down while it hovers. Three gear legs with pads. Nav lamps on the claws.

Nod's colours (nodvehicle.camouflage): the armour near black blotched with dark grey
and dark red; the stripes, the intake rims and the cannons' bands red (house colour).

Nodes for the game: "Flash" (the cannons' muzzle flash, between the two muzzles; it
shows a flash at each).

Clips (see aircraft.py)
    Idle     loop, 2 s: landed, engines off
    TakeOff  once, 1 s: the exhausts and lift fans light up, the gear comes in, the
             nose dips
    Fly      loop, 1 s: hovering, fans and exhausts glowing, a gentle sway
    Land     once, 1 s: the gear goes out, the glow dies away
    Fire     once, 0.5 s: two proton shots from both cannons (Fly pose)

Run headless:

    blender -b --factory-startup --python blender/SCRIN.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle; landed, the gear's pads touch Z = 0.
"""
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import APACHE as harpy  # noqa: E402 – shell(), polyline()
import aircraft as air  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402

OUT = os.path.join(air.PROJECT, 'public', 'models', 'SCRIN.glb')
BLEND = os.path.join(HERE, 'SCRIN.blend')

BELLY = 0.16                       # underside of the keel, landed
CANNON_X, CANNON_Z = 0.165, 0.17   # the cannons' axes
MUZZLE_Y = -0.47
FLASH_AT = Vector((0, MUZZLE_Y - 0.02, CANNON_Z))
FIRE_FRAMES = 15
FAN = (0.33, 0.05)                 # the lift fans under the wings: x, y
NACELLE_X = 0.1                    # the engine tubes beside the spine
EXHAUST_Y = 0.445

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
HIDDEN = kit.HIDDEN

KEEL = (  # y, half width, bottom, top
    (-0.45, 0.018, 0.222, 0.238), (-0.41, 0.045, 0.205, 0.262), (-0.33, 0.07, 0.185, 0.285), (-0.2, 0.09, 0.165, 0.3),
    (0.0, 0.1, BELLY, 0.308), (0.2, 0.1, 0.165, 0.305), (0.36, 0.085, 0.18, 0.29), (0.44, 0.06, 0.2, 0.27),
)
NACELLE = ((-0.17, 0.024, 0.262, 0.29), (-0.13, 0.05, 0.25, 0.32), (0.3, 0.054, 0.248, 0.326), (0.4, 0.05, 0.252, 0.32),
           (EXHAUST_Y - 0.01, 0.044, 0.258, 0.312))
# the right half of the wing's outline, from the notch in front round the claw to the
# tail: x, y and the point that place is inset towards for the raised plates (the
# claw towards its own root, so the plates follow it)
OUTLINE = (
    (0.0, -0.22, 0.0, 0.04), (0.1, -0.245, 0.04, 0.04), (0.2, -0.31, 0.1, -0.02), (0.29, -0.42, 0.2, -0.15),
    (0.37, -0.57, 0.22, -0.15), (0.45, -0.47, 0.22, -0.12), (0.51, -0.34, 0.15, -0.05), (0.55, -0.18, 0.1, 0.0),
    (0.56, -0.02, 0.05, 0.04), (0.53, 0.12, 0.0, 0.04), (0.46, 0.24, 0.0, 0.04), (0.36, 0.33, 0.0, 0.04),
    (0.24, 0.39, 0.0, 0.04), (0.12, 0.42, 0.0, 0.04), (0.0, 0.43, 0.0, 0.04),
)
CLAW = 4                           # the claw's tip in OUTLINE
# the wing's rings from the edge in: how far towards the inset point, top and bottom
# off the mid plane
RINGS = ((0.0, 0.0, 0.0), (0.28, 0.02, -0.012), (0.6, 0.04, -0.024))


def materials():
    m = nod.materials()
    m.update({
        'coil': material('PlasmaCoil', srgb('#40ff90'), 0.3, emission=srgb('#30ff80'), strength=4),
        'plasma': material('GlowPlasma', (0, 0, 0), 1.0, emission=srgb('#70ffb0'), strength=8, alpha=0.75),
        'exhaust': material('GlowExhaust', srgb('#3a3036'), 0.5, emission=srgb('#ff7a3a'), strength=5),
        'plume': material('GlowPlume', (0, 0, 0), 1.0, emission=srgb('#ff9a5a'), strength=3, alpha=0.3),
    })
    return m


def mid_plane(x, y):
    """The wing's middle height: highest in the middle, the claws and the edges droop."""
    return 0.245 - 0.04 * (abs(x) / 0.56) ** 2 - 0.05 * max(0.0, -(y + 0.3)) / 0.27 - 0.015 * max(0.0, y - 0.2) / 0.23


def outline():
    """The whole outline (both halves, round from the front notch): (x, y, inset x, inset y)."""
    right = list(OUTLINE)
    left = [(-x, y, -ax, ay) for x, y, ax, ay in reversed(OUTLINE[1:-1])]
    return right + left


def wing_point(i, ring, top=True):
    """A point of the wing's surface: on ring `ring` (RINGS) at outline point i."""
    x, y, ax, ay = outline()[i % len(outline())]
    t, up, down = RINGS[ring]
    px, py = x + (ax - x) * t, y + (ay - y) * t
    return Vector((px, py, mid_plane(px, py) + (up if top else down)))


def wing(m):
    """The flying wing: rings of faceted plates from the sharp edge up to the raised
    middle (inset towards each place's own point, so the claws keep their shape), the
    top in armour, the underside darker; the middle closed by one polygon each side."""
    count = len(outline())

    def build(bm):
        edge = [bm.verts.new(wing_point(i, 0)) for i in range(count)]
        tops = [edge] + [[bm.verts.new(wing_point(i, r)) for i in range(count)] for r in range(1, len(RINGS))]
        bottoms = [edge] + [[bm.verts.new(wing_point(i, r, False)) for i in range(count)] for r in range(1, len(RINGS))]
        for rings, index in ((tops, 0), (bottoms, 1)):
            for a, b in zip(rings, rings[1:]):
                for i in range(count):
                    j = (i + 1) % count
                    face = bm.faces.new((a[i], a[j], b[j], b[i]))
                    face.material_index = index
            face = bm.faces.new(rings[-1])
            face.material_index = index
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])

    obj = kit.mesh_object('Wing', build)
    obj.data.materials.append(m['armour'])
    obj.data.materials.append(m['armour_dark'])
    m['armour'].use_backface_culling = True
    m['armour_dark'].use_backface_culling = True
    for poly in obj.data.polygons:
        poly.use_smooth = False  # faceted armour plates
    return obj


def on_wing(i, ring, t, lift=0.005):
    """A point on the wing's top a fraction t from ring `ring` towards the next one."""
    return wing_point(i, ring).lerp(wing_point(i, ring + 1), t) + Vector((0, 0, lift))


def wing_trim(m):
    """Red stripes along the edges and the claws, dark seams across the plates, the nav
    lamps on the claws."""
    count = len(outline())
    half = len(OUTLINE) - 1
    parts = []
    for s, ids in ((1, range(1, 10)), (-1, [count - i for i in range(1, 10)])):
        parts += harpy.polyline(f'EdgeStripe{s}', m['remap'], [on_wing(i, 0, 0.42) for i in ids], 0.016)
        # the claw's inner panel and a stripe along its root
        parts += harpy.polyline(f'ClawStripe{s}', m['remap'], [on_wing(i, 1, 0.5) for i in list(ids)[2:6]], 0.012)
        for k, i in enumerate(list(ids)[1::2]):
            parts.append(beam(f'Seam{s}{k}', m['seam'], on_wing(i, 0, 0.75, 0.003), on_wing(i, 1, 0.9, 0.003), 0.007, 0.006))
        lamp = m['lamp_green'] if s > 0 else m['lamp_red']
        tip = CLAW if s > 0 else count - CLAW
        parts += detail.lamp(f'NavLamp{s}', m['seam'], lamp, on_wing(tip, 0, 0.18, 0.004), (0, 0, 1), 0.008)
    for s, ids in ((1, range(10, half + 1)), (-1, [count - i for i in range(10, half)] + [half])):
        parts += harpy.polyline(f'TailSeam{s}', m['seam'], [on_wing(i, 0, 0.5, 0.003) for i in ids], 0.007)
    return parts


def hull(m):
    parts = [
        wing(m),
        *wing_trim(m),
        harpy.shell('Keel', m['armour'], KEEL, sides=12, power=2.4),
        # the cockpit's bubble and its rim at the front of the spine
        *canopy(m),
        box('DorsalStripe', m['remap'], (0.026, 0.34, 0.01), (0, 0.16, 0.307), bevel=0.003),
        *harpy.deck_vent('SpineVent', m['steel'], m['seam'], (0, -0.1, 0.31), 0.05, 0.07, 4, 0.01),
        box('Sensor', m['armour_dark'], (0.036, 0.04, 0.026), (0, -0.425, 0.205), bevel=0.006),
        *detail.lamp('SensorEye', m['seam'], m['lamp_red'], (0, -0.447, 0.205), (0, -1, 0), 0.009),
        box('TailLight', m['lamp_white'], (0.014, 0.012, 0.012), (0, 0.446, 0.255), bevel=0),
        *detail.lamp('BellyLamp', m['seam'], m['lamp_red'], (0, 0.15, 0.163), (0, 0, -1), 0.009),
    ]
    for s in (-1, 1):
        x = s * NACELLE_X
        parts += [
            # an engine tube beside the spine: red-rimmed intake, vents, rivets, the exhaust's rim
            harpy.shell(f'Nacelle{s}', m['armour_dark'], NACELLE, x=x, sides=10, power=2.2),
            cylinder(f'IntakeRim{s}', m['remap'], 0.04, 0.02, (x, -0.14, 0.286), rotation=(math.pi / 2, 0, 0), segments=14, bevel=0.003),
            cylinder(f'Intake{s}', m['seam'], 0.031, 0.022, (x, -0.143, 0.286), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0),
            cylinder(f'IntakeHub{s}', m['steel_light'], 0.009, 0.026, (x, -0.143, 0.286), rotation=(math.pi / 2, 0, 0), segments=8, bevel=0),
            *harpy.deck_vent(f'NacelleVent{s}', m['steel'], m['seam'], (x, 0.14, 0.326), 0.05, 0.1, 5, 0.008),
            *detail.rivets(f'NacelleRivets{s}', m['steel_light'], (x + s * 0.052, -0.06, 0.286), (x + s * 0.054, 0.3, 0.286), 6, 0.004, 'X'),
            box(f'NacelleBand{s}', m['remap'], (0.112, 0.024, 0.082), (x, 0.36, 0.287), bevel=0.006),
            cylinder(f'ExhaustRim{s}', m['steel'], 0.044, 0.03, (x, EXHAUST_Y - 0.004, 0.285), rotation=(math.pi / 2, 0, 0), segments=14,
                     bevel=0.004),
            cylinder(f'ExhaustHole{s}', m['seam'], 0.034, 0.032, (x, EXHAUST_Y - 0.002, 0.285), rotation=(math.pi / 2, 0, 0), segments=12,
                     bevel=0),
            # the lift fan's ring under the wing and its vanes
            cylinder(f'FanRing{s}', m['armour_dark'], 0.075, 0.02, (s * FAN[0], FAN[1], 0.205), segments=18, bevel=0.003),
            *[box(f'FanVane{s}{k}', m['steel'], (0.13, 0.008, 0.006), (s * FAN[0], FAN[1], 0.196), rotation=(0, 0, k * math.pi / 3), bevel=0)
              for k in range(3)],
            # the proton cannon under the wing root: pylon, housing, the caged canister, barrel, muzzle
            box(f'Pylon{s}', m['armour_dark'], (0.03, 0.16, 0.05), (s * CANNON_X, -0.13, 0.2), bevel=0.006),
            box(f'CannonHousing{s}', m['armour'], (0.062, 0.24, 0.058), (s * CANNON_X, -0.14, CANNON_Z), bevel=0.012),
            box(f'CannonBand{s}', m['remap'], (0.064, 0.026, 0.06), (s * CANNON_X, -0.06, CANNON_Z), bevel=0.004),
            *detail.grille(f'CannonVent{s}', m['steel'], m['seam'], (s * (CANNON_X + 0.032), -0.15, CANNON_Z), 0.08, 0.034, 'X', 3, 0.006),
            cylinder(f'Canister{s}', m['coil'], 0.022, 0.07, (s * CANNON_X, -0.3, CANNON_Z), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.003),
            *[cylinder(f'CageRing{s}{k}', m['armour_dark'], 0.027, 0.012, (s * CANNON_X, -0.27 - 0.03 * k, CANNON_Z),
                       rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.002) for k in range(3)],
            *[beam(f'CageBar{s}{k}', m['steel'], (s * CANNON_X + 0.025 * c, -0.26, CANNON_Z + 0.025 * d),
                   (s * CANNON_X + 0.025 * c, -0.34, CANNON_Z + 0.025 * d), 0.007)
              for k, (c, d) in enumerate(((1, 0), (-1, 0), (0, 1), (0, -1)))],
            cylinder(f'CannonBarrel{s}', m['armour_dark'], 0.015, 0.12, (s * CANNON_X, MUZZLE_Y + 0.07, CANNON_Z),
                     rotation=(math.pi / 2, 0, 0), segments=10, bevel=0),
            cylinder(f'Muzzle{s}', m['steel'], 0.024, 0.03, (s * CANNON_X, MUZZLE_Y + 0.014, CANNON_Z), rotation=(math.pi / 2, 0, 0),
                     segments=10, bevel=0.003, radius2=0.02),
            cylinder(f'MuzzleBore{s}', m['coil'], 0.013, 0.032, (s * CANNON_X, MUZZLE_Y + 0.013, CANNON_Z), rotation=(math.pi / 2, 0, 0),
                     segments=8, bevel=0),
        ]
    return kit.merge('Hull', parts)


def canopy(m):
    """The cockpit's dark bubble at the front of the spine, a frame over it."""
    centre, radii = Vector((0, -0.27, 0.272)), Vector((0.056, 0.125, 0.05))
    bubble = sphere('Canopy', m['glass'], 1.0, centre, 16)
    bubble.scale = radii
    parts = [bubble]
    parts += harpy.polyline('CanopyBar', m['steel'], [centre + Vector((0, radii.y * math.cos(u), radii.z * math.sin(u)))
                                                      + Vector((0, 0, 0.002)) for u in (math.radians(d) for d in range(25, 160, 20))], 0.01)
    f = math.sqrt(1 - (0.04 / radii.y) ** 2)
    parts += harpy.polyline('CanopyHoop', m['steel'], [centre + Vector((radii.x * f * math.cos(t) * 1.04, 0.04, radii.z * f * math.sin(t) * 1.04))
                                                       for t in (math.radians(d) for d in range(-10, 191, 25))], 0.01)
    return parts


def glows(m):
    """The exhausts' and fans' glow (shown when the engines run) and the fans' plumes."""
    exhaust = kit.merge('ExhaustGlow', [cylinder(f'ExhaustDisc{s}', m['exhaust'], 0.033, 0.01, (s * NACELLE_X, EXHAUST_Y + 0.01, 0.285),
                                                 rotation=(math.pi / 2, 0, 0), segments=14, bevel=0) for s in (-1, 1)],
                        (0, EXHAUST_Y + 0.01, 0.285))
    fans = kit.merge('FanGlow', [cylinder(f'FanDisc{s}', m['exhaust'], 0.06, 0.008, (s * FAN[0], FAN[1], 0.19), segments=18, bevel=0)
                                 for s in (-1, 1)], (0, FAN[1], 0.19))
    plumes = kit.merge('FanPlume', [cylinder(f'FanCone{s}', m['plume'], 0.055, 0.16, (s * FAN[0], FAN[1], 0.102), segments=16, bevel=0,
                                             radius2=0.015) for s in (-1, 1)], (0, FAN[1], 0.186))
    for obj in (exhaust, fans, plumes):
        for mat in obj.data.materials:
            mat.use_backface_culling = False
    return exhaust, fans, plumes


def gear(m):
    parts = []
    for name, (x, y) in (('Nose', (0, -0.3)), ('Left', (-0.11, 0.14)), ('Right', (0.11, 0.14))):
        top = BELLY + (0.03 if name == 'Nose' else 0.01)
        parts += [
            cylinder(f'Leg{name}', m['steel_light'], 0.012, top, (x, y, top / 2), segments=8, bevel=0),
            cylinder(f'Strut{name}', m['steel'], 0.019, 0.05, (x, y, BELLY - 0.03), segments=8, bevel=0.002),
            beam(f'Brace{name}', m['steel'], (x, y + 0.04, BELLY), (x, y, BELLY - 0.07), 0.008),
            cylinder(f'Pad{name}', m['seam'], 0.032, 0.012, (x, y, 0.006), segments=12, bevel=0.002),
        ]
    return kit.merge('Gear', parts, (0, 0, BELLY))


def flash(m):
    """A flash at each muzzle; origin between them, hidden at rest."""
    balls = []
    for s in (-1, 1):
        at = Vector((s * CANNON_X, MUZZLE_Y - 0.02, CANNON_Z))
        balls += [sphere(f'Flash{s}{k}', m['plasma'], 0.04 * (1 - 0.25 * k), at + Vector((0, -0.036 * k, 0)), 10) for k in range(3)]
    obj = kit.merge('Flash', balls, FLASH_AT)
    obj.scale = (HIDDEN,) * 3
    return obj


def build():
    root, body = air.start('NodBanshee', 'Banshee')
    m = materials()
    shell = kit.parent(hull(m), body)
    legs = kit.parent(gear(m), body)
    exhaust, fans, plumes = (kit.parent(obj, body) for obj in glows(m))
    muzzle = kit.parent(flash(m), body)
    nod.camouflage([shell, legs])

    channels = [(body, 'location'), (body, 'rotation_euler'), (legs, 'scale'), (muzzle, 'scale'),
                (exhaust, 'scale'), (fans, 'scale'), (plumes, 'scale')]
    rad = math.radians
    hidden = Vector((HIDDEN,) * 3)

    def pose(thrust, gear_out, pitch=0.0, roll=0.0, lift=0.0):
        on = thrust > 0.05
        return {
            ('Body', 'location'): Vector((0, 0, lift)),
            ('Body', 'rotation_euler'): Vector((rad(pitch), rad(roll), 0)),
            ('Gear', 'scale'): Vector((1, 1, air.mix(0.02, 1, gear_out))),
            ('Flash', 'scale'): hidden,
            ('ExhaustGlow', 'scale'): Vector((1, 1, 1)) if on else hidden,
            ('FanGlow', 'scale'): Vector((1, 1, 1)) if on else hidden,
            ('FanPlume', 'scale'): Vector((1, 1, thrust)) if on else hidden,
        }

    def flicker(f):
        return 1 + 0.12 * math.sin(f * 2.3) * math.sin(f * 0.7 + 1)

    def fly(f):
        t = 2 * math.pi * f / air.FLY_FRAMES
        return pose(flicker(f), 0, pitch=-3 + 0.8 * math.sin(2 * t), roll=2 * math.sin(t), lift=0.01 * math.sin(t))

    def idle(f):
        return pose(0, 1)

    def take_off(f):
        return pose(air.span(f, 0, 10) * flicker(f), 1 - air.span(f, 10, 26), pitch=air.mix(0, -3, air.span(f, 8, 30)))

    def land(f):
        return pose((1 - air.span(f, 16, 30)) * flicker(f), air.span(f, 0, 16), pitch=air.mix(-3, 0, air.span(f, 0, 22)))

    def fire(f):
        v = fly(f)
        if f in (0, 1, 7, 8):
            v[('Flash', 'scale')] = Vector((1, 1, 1)) * (1.25 if f % 7 else 1.0)
        v[('Body', 'rotation_euler')].x += rad(1.2 * math.sin(math.pi * min(1, (f % 7) / 6)))
        return v

    air.clip('Idle', air.IDLE_FRAMES, channels, idle)
    air.clip('TakeOff', air.TAKEOFF_FRAMES, channels, take_off)
    air.clip('Fly', air.FLY_FRAMES, channels, fly)
    air.clip('Land', air.LAND_FRAMES, channels, land)
    air.clip('Fire', FIRE_FRAMES, channels, fire)

    def rest():
        for (name, prop), value in idle(0).items():
            setattr(kit.collection().objects[name], prop, value)

    rest()
    return rest


if __name__ == '__main__':
    air.main(build, OUT, BLEND, {'Idle': [0], 'TakeOff': [20], 'Fly': [3], 'Fire': [1]}, scale=1.6, target=(0, -0.05, 0.2))
