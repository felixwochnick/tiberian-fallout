"""
Tiberian Fallout – Nod Banshee (SCRIN), after Tiberian Sun Firestorm.

A VTOL strike craft, after the build icon: a flying wing round a short, armoured body
with a pointed nose and a dark crescent canopy; broad wings sweep forward into two
claw-like tips (red, in the house colour, the claws dark), drooping a little to the
tips. Two plasma (proton) cannons hang under the wing roots, green coils on their
barrels; behind, two glowing exhausts; under each wing a lift fan that glows and
blows down while it hovers. Three gear legs with pads.

Nod's colours (nodvehicle.camouflage): the armour near black blotched with dark grey
and dark red; the wings red (house colour).

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

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import DSHP  # noqa: E402 – loft()
import aircraft as air  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402

OUT = os.path.join(air.PROJECT, 'public', 'models', 'SCRIN.glb')
BLEND = os.path.join(HERE, 'SCRIN.blend')

BELLY = 0.14                       # underside of the body, landed
CANNON_X, CANNON_Z = 0.17, 0.165   # the cannons' axes
MUZZLE_Y = -0.47
FLASH_AT = Vector((0, MUZZLE_Y - 0.02, CANNON_Z))
FIRE_FRAMES = 15
FAN = (0.29, 0.0)                  # the lift fans under the wings: x, y

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
loft = DSHP.loft
HIDDEN = kit.HIDDEN

BODY = (  # y, half width, bottom, top
    (-0.52, 0.025, 0.2, 0.23), (-0.44, 0.08, 0.17, 0.29), (-0.25, 0.13, BELLY, 0.33), (0.08, 0.13, 0.15, 0.32),
    (0.3, 0.09, 0.18, 0.29), (0.38, 0.06, 0.2, 0.27),
)
# a wing's stations from the root out: x, leading edge y, trailing edge y, height of
# its middle, thickness, material of the section out to the next station
WING = (
    (0.11, -0.2, 0.28, 0.245, 0.07, 'armour'),
    (0.24, -0.27, 0.22, 0.24, 0.05, 'remap'),
    (0.38, -0.36, 0.1, 0.22, 0.036, 'remap'),
    (0.5, -0.47, -0.08, 0.185, 0.026, 'armour_dark'),
    (0.55, -0.58, -0.36, 0.155, 0.016, None),
)


def materials():
    m = nod.materials()
    m.update({
        'coil': material('PlasmaCoil', srgb('#40ff90'), 0.3, emission=srgb('#30ff80'), strength=4),
        'plasma': material('GlowPlasma', (0, 0, 0), 1.0, emission=srgb('#70ffb0'), strength=8, alpha=0.75),
        'exhaust': material('GlowExhaust', srgb('#3a3036'), 0.5, emission=srgb('#ff7a3a'), strength=5),
        'plume': material('GlowPlume', (0, 0, 0), 1.0, emission=srgb('#ff9a5a'), strength=3, alpha=0.3),
    })
    return m


def wing(m, s):
    """One wing (s = 1 right, -1 left): hexahedra between the stations."""
    parts = []
    for i, (a, b) in enumerate(zip(WING, WING[1:])):
        def corners(st, top):
            x, lead, trail, mid, t, _ = st
            z = mid + (t / 2 if top else -t / 2)
            return [(s * x, lead, z), (s * x, trail, z)]
        a0, a1 = corners(a, False)
        b0, b1 = corners(b, False)
        c0, c1 = corners(a, True)
        d0, d1 = corners(b, True)
        parts.append(kit.hexahedron(f'Wing{s}{i}', m[a[5]], (a0, b0, b1, a1, c0, d0, d1, c1), bevel=0.003))
    return parts


def hull(m):
    parts = [
        loft('Fuselage', m['armour'], BODY, chamfer=0.45),
        loft('Canopy', m['glass'], ((-0.43, 0.04, 0.27, 0.295), (-0.38, 0.1, 0.28, 0.325), (-0.3, 0.115, 0.3, 0.34),
                                    (-0.24, 0.08, 0.31, 0.34))),
        box('CanopyRim', m['seam'], (0.2, 0.012, 0.014), (0, -0.3, 0.342), bevel=0.003),
        box('Dorsal', m['armour_dark'], (0.1, 0.36, 0.03), (0, 0.04, 0.33), bevel=0.01),
        box('DorsalStripe', m['remap'], (0.03, 0.3, 0.032), (0, 0.04, 0.334), bevel=0.004),
        box('NoseStripe', m['remap'], (0.12, 0.05, 0.012), (0, -0.46, 0.27), bevel=0.003),
        box('Sensor', m['armour_dark'], (0.04, 0.03, 0.03), (0, -0.52, 0.2), bevel=0.006),
        *detail.lamp('SensorEye', m['seam'], m['lamp_red'], (0, -0.536, 0.2), (0, -1, 0), 0.01),
        box('TailLight', m['lamp_white'], (0.014, 0.012, 0.012), (0, 0.386, 0.25), bevel=0),
    ]
    for s in (-1, 1):
        parts += wing(m, s)
        parts += [
            # wing fences and the claw's dark edge
            box(f'Fence{s}', m['armour_dark'], (0.012, 0.3, 0.03), (s * 0.24, -0.02, 0.265), bevel=0.003),
            box(f'WingStripe{s}', m['armour_dark'], (0.1, 0.03, 0.012), (s * 0.36, 0.0, 0.24), bevel=0.003),
            # exhausts at the back of the body
            cylinder(f'ExhaustRim{s}', m['armour_dark'], 0.042, 0.04, (s * 0.06, 0.39, 0.235), rotation=(math.pi / 2, 0, 0), segments=14,
                     bevel=0.004),
            # the lift fan's ring under the wing
            cylinder(f'FanRing{s}', m['armour_dark'], 0.075, 0.02, (s * FAN[0], FAN[1], 0.2), segments=18, bevel=0.003),
            # the proton cannon under the wing root: pylon, housing, barrel, coils, muzzle
            box(f'Pylon{s}', m['armour_dark'], (0.03, 0.12, 0.05), (s * CANNON_X, -0.12, 0.2), bevel=0.006),
            box(f'CannonHousing{s}', m['armour'], (0.06, 0.22, 0.055), (s * CANNON_X, -0.15, CANNON_Z), bevel=0.012),
            box(f'CannonStripe{s}', m['remap'], (0.062, 0.03, 0.057), (s * CANNON_X, -0.08, CANNON_Z), bevel=0.004),
            cylinder(f'CannonBarrel{s}', m['armour_dark'], 0.016, 0.2, (s * CANNON_X, MUZZLE_Y + 0.1, CANNON_Z),
                     rotation=(math.pi / 2, 0, 0), segments=10, bevel=0),
            *[cylinder(f'Coil{s}{k}', m['coil'], 0.022, 0.014, (s * CANNON_X, -0.3 - 0.035 * k, CANNON_Z), rotation=(math.pi / 2, 0, 0),
                       segments=10, bevel=0) for k in range(3)],
            cylinder(f'Muzzle{s}', m['seam'], 0.022, 0.025, (s * CANNON_X, MUZZLE_Y + 0.012, CANNON_Z), rotation=(math.pi / 2, 0, 0),
                     segments=10, bevel=0.003),
        ]
    return kit.merge('Hull', parts)


def glows(m):
    """The exhausts' and fans' glow (shown when the engines run) and the fans' plumes."""
    exhaust = kit.merge('ExhaustGlow', [cylinder(f'ExhaustDisc{s}', m['exhaust'], 0.032, 0.01, (s * 0.06, 0.412, 0.235),
                                                 rotation=(math.pi / 2, 0, 0), segments=14, bevel=0) for s in (-1, 1)],
                        (0, 0.41, 0.235))
    fans = kit.merge('FanGlow', [cylinder(f'FanDisc{s}', m['exhaust'], 0.06, 0.008, (s * FAN[0], FAN[1], 0.188), segments=18, bevel=0)
                                 for s in (-1, 1)], (0, FAN[1], 0.188))
    plumes = kit.merge('FanPlume', [cylinder(f'FanCone{s}', m['plume'], 0.055, 0.16, (s * FAN[0], FAN[1], 0.1), segments=16, bevel=0,
                                             radius2=0.015) for s in (-1, 1)], (0, FAN[1], 0.184))
    for obj in (exhaust, fans, plumes):
        for mat in obj.data.materials:
            mat.use_backface_culling = False
    return exhaust, fans, plumes


def gear(m):
    parts = []
    for name, (x, y) in (('Nose', (0, -0.3)), ('Left', (-0.1, 0.12)), ('Right', (0.1, 0.12))):
        parts += [
            cylinder(f'Leg{name}', m['steel_light'], 0.012, BELLY, (x, y, BELLY / 2), segments=8, bevel=0),
            cylinder(f'Strut{name}', m['steel'], 0.018, 0.04, (x, y, BELLY - 0.03), segments=8, bevel=0.002),
            cylinder(f'Pad{name}', m['seam'], 0.03, 0.012, (x, y, 0.006), segments=12, bevel=0.002),
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
