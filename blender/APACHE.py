"""
Tiberian Fallout – Nod Harpy attack helicopter (APACHE), after Tiberian Sun.

A slim gunship, after the build icon: a narrow, angular fuselage with a stepped
tandem canopy, a pointed nose with a chain gun in a turret under it, two engine
humps beside the rotor mast with exhausts, stub wings with rocket pods and a missile
rail at each tip, a long tail boom with a swept fin, a tail rotor on its left side
and a stabiliser. Four-bladed main rotor on a mast; flying, a faint blur disc shows
under the blades. Two main wheels and a tail wheel on legs.

Nod's colours (nodvehicle.camouflage): the armour near black blotched with dark grey
and dark red; the fin, the wing tips, the pods' noses and stripes red (house colour).

Nodes for the game: "Rotor" (the main rotor, turns about its vertical), "Flash" (the
chain gun's muzzle flash under the nose).

Clips (see aircraft.py)
    Idle     loop, 2 s: landed, rotors standing
    TakeOff  once, 1 s: the rotors spin up, the gear comes in, the nose dips
    Fly      loop, 1 s: rotors fast (blur disc), nose down a little, a gentle sway
    Land     once, 1 s: the gear goes out, the rotors run down
    Fire     once, 0.5 s: a burst of the chain gun (three flashes, Fly pose)

Run headless:

    blender -b --factory-startup --python blender/APACHE.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle; landed, the wheels touch Z = 0.
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

OUT = os.path.join(air.PROJECT, 'public', 'models', 'APACHE.glb')
BLEND = os.path.join(HERE, 'APACHE.blend')

BELLY = 0.11                      # underside of the fuselage, landed
MAST = Vector((0, -0.04, 0.37))   # the rotor's hub
ROTOR_RADIUS = 0.46
TAIL_ROTOR = Vector((-0.04, 0.6, 0.31))
TAIL_ROTOR_RADIUS = 0.085
GUN = Vector((0, -0.34, 0.075))   # the chain gun's turret
FLASH_AT = Vector((0, -0.5, 0.07))
FIRE_FRAMES = 15                  # the rotor turns a whole number of quarter turns in it
WHEEL = 0.028
# the rotor at full speed: two turns per Fly loop (a quarter turn every 7.5 frames,
# the four blades read as turning, not as standing or running back)
ROTOR_SPEED = 2 * (2 * math.pi) / air.FLY_FRAMES
TAIL_RATIO = 3                    # the tail rotor turns three times as fast

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
loft = DSHP.loft
HIDDEN = kit.HIDDEN

HULL = (  # y, half width, bottom, top
    (-0.52, 0.015, 0.14, 0.17), (-0.47, 0.05, 0.12, 0.21), (-0.38, 0.07, BELLY, 0.24), (-0.18, 0.08, BELLY, 0.27),
    (0.05, 0.085, BELLY, 0.29), (0.16, 0.06, 0.14, 0.27),
)
BOOM = ((0.15, 0.055, 0.15, 0.27), (0.4, 0.032, 0.21, 0.27), (0.6, 0.025, 0.24, 0.28))


def materials():
    m = nod.materials()
    m.update({
        'blur': material('RotorBlur', srgb('#1a1a1c'), 0.8, alpha=0.22),
        'blade': material('RotorBlade', srgb('#2a2b2f'), 0.6, 0.4),
    })
    m['blur'].use_backface_culling = False
    return m


def hull(m):
    """Fuselage, tail boom, wings, fin (camouflaged later) and their fittings."""
    parts = [
        loft('Fuselage', m['armour'], HULL, chamfer=0.4),
        loft('Boom', m['armour'], BOOM, chamfer=0.35),
        # tandem canopy: the gunner low in front, the pilot higher behind
        loft('CanopyFront', m['glass'], ((-0.42, 0.03, 0.2, 0.23), (-0.37, 0.06, 0.21, 0.275), (-0.27, 0.06, 0.22, 0.285))),
        loft('CanopyBack', m['glass'], ((-0.27, 0.05, 0.24, 0.29), (-0.22, 0.07, 0.25, 0.33), (-0.12, 0.065, 0.26, 0.335),
                                        (-0.08, 0.04, 0.27, 0.3))),
        box('CanopyFrame', m['seam'], (0.01, 0.34, 0.01), (0, -0.25, 0.32), bevel=0),
        # engine humps beside the mast, intakes in front, exhausts behind
        *[loft(f'Engine{s}', m['armour_dark'], ((-0.1, 0.03, 0.25, 0.3), (-0.06, 0.045, 0.24, 0.33), (0.12, 0.045, 0.24, 0.33),
                                                (0.16, 0.03, 0.25, 0.31))) for s in (-1, 1)],
        # stub wings
        kit.hexahedron('Wing', m['armour'], (
            (-0.24, -0.1, 0.17), (0.24, -0.1, 0.17), (0.24, 0.0, 0.17), (-0.24, 0.0, 0.17),
            (-0.24, -0.09, 0.19), (0.24, -0.09, 0.19), (0.24, 0.0, 0.19), (-0.24, 0.0, 0.19)), bevel=0.004),
        # swept tail fin and the stabiliser
        kit.hexahedron('Fin', m['remap'], (
            (-0.008, 0.5, 0.26), (0.008, 0.5, 0.26), (0.008, 0.63, 0.26), (-0.008, 0.63, 0.26),
            (-0.006, 0.6, 0.42), (0.006, 0.6, 0.42), (0.006, 0.67, 0.42), (-0.006, 0.67, 0.42)), bevel=0.003),
        kit.hexahedron('Stabiliser', m['armour_dark'], (
            (-0.12, 0.5, 0.25), (0.12, 0.5, 0.25), (0.12, 0.56, 0.25), (-0.12, 0.56, 0.25),
            (-0.12, 0.51, 0.262), (0.12, 0.51, 0.262), (0.12, 0.56, 0.262), (-0.12, 0.56, 0.262)), bevel=0.002),
        # the gun turret's ball under the nose (the barrels on it)
        sphere('GunBall', m['armour_dark'], 0.035, GUN, 14),
        box('GunMount', m['armour_dark'], (0.04, 0.05, 0.04), GUN + Vector((0, 0.01, 0.03)), bevel=0.006),
        *[cylinder(f'GunBarrel{k}', m['steel'], 0.006, 0.13, GUN + Vector(((k % 2 - 0.5) * 0.014, -0.09, (k // 2 - 0.5) * 0.014)),
                   rotation=(math.pi / 2, 0, 0), segments=6, bevel=0) for k in range(4)],
        cylinder('GunShroud', m['armour_dark'], 0.016, 0.03, GUN + Vector((0, -0.05, 0)), rotation=(math.pi / 2, 0, 0), segments=10,
                 bevel=0.003),
        cylinder('Muzzle', m['steel_light'], 0.017, 0.012, FLASH_AT + Vector((0, 0.03, 0.005)), rotation=(math.pi / 2, 0, 0), segments=10,
                 bevel=0),
        # mast and hub
        cylinder('Mast', m['steel'], 0.018, MAST.z - 0.28, Vector((MAST.x, MAST.y, (MAST.z + 0.28) / 2)), segments=10, bevel=0),
        cylinder('MastFairing', m['armour_dark'], 0.04, 0.04, Vector((MAST.x, MAST.y, 0.31)), segments=14, bevel=0.008, radius2=0.025),
        box('Sensor', m['armour_dark'], (0.04, 0.03, 0.03), (0, -0.5, 0.17), bevel=0.006),
        *detail.lamp('SensorEye', m['seam'], m['lamp_red'], (0, -0.518, 0.17), (0, -1, 0), 0.01),
        beam('Antenna', m['steel'], (0, 0.18, 0.28), (0, 0.24, 0.36), 0.005),
        box('BoomStripe', m['remap'], (0.07, 0.035, 0.012), (0, 0.32, 0.27), bevel=0.003),
        box('TailLight', m['lamp_white'], (0.012, 0.012, 0.012), (0, 0.675, 0.42), bevel=0),
        cylinder('TailGearbox', m['armour_dark'], 0.02, 0.03, TAIL_ROTOR + Vector((0.025, 0, 0)), rotation=(0, math.pi / 2, 0), segments=10,
                 bevel=0.003),
    ]
    for s in (-1, 1):
        parts += [
            box(f'Exhaust{s}', m['seam'], (0.035, 0.02, 0.035), (s * 0.03, 0.17, 0.29), bevel=0.004),
            box(f'IntakeFace{s}', m['seam'], (0.04, 0.012, 0.045), (s * 0.03, -0.105, 0.285), bevel=0.003),
            box(f'NoseStripe{s}', m['remap'], (0.008, 0.12, 0.02), (s * 0.072, -0.35, 0.19), bevel=0.002),
            *[box(f'SidePanel{s}{k}', m['seam'], (0.006, 0.05, 0.03), (s * 0.084, -0.05 + 0.07 * k, 0.2), bevel=0.002) for k in range(3)],
            # rocket pods under the wings and a missile rail at each tip
            cylinder(f'Pod{s}', m['armour_dark'], 0.03, 0.14, (s * 0.15, -0.05, 0.14), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.004),
            cylinder(f'PodNose{s}', m['remap'], 0.03, 0.025, (s * 0.15, -0.13, 0.14), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.004,
                     radius2=0.022),
            *[cylinder(f'PodTube{s}{k}', m['seam'], 0.007, 0.01, (s * 0.15 + 0.013 * math.cos(2 * math.pi * k / 5), -0.145,
                                                                  0.14 + 0.013 * math.sin(2 * math.pi * k / 5)),
                       rotation=(math.pi / 2, 0, 0), segments=6, bevel=0) for k in range(5)],
            box(f'PodPylon{s}', m['armour_dark'], (0.015, 0.06, 0.03), (s * 0.15, -0.05, 0.165), bevel=0.003),
            box(f'WingTip{s}', m['remap'], (0.02, 0.1, 0.03), (s * 0.245, -0.05, 0.18), bevel=0.004),
            cylinder(f'Missile{s}', m['steel_light'], 0.01, 0.13, (s * 0.255, -0.07, 0.15), rotation=(math.pi / 2, 0, 0), segments=8, bevel=0.002),
            cylinder(f'MissileTip{s}', m['remap'], 0.01, 0.02, (s * 0.255, -0.145, 0.15), rotation=(math.pi / 2, 0, 0), segments=8, bevel=0,
                     radius2=0.002),
        ]
    return kit.merge('Hull', parts)


def rotor(m):
    """The main rotor about the hub: four blades drooping a little, the hub, and the
    blur disc (its own object, shown only when the rotor runs fast)."""
    parts = [cylinder('Hub', m['steel'], 0.03, 0.025, MAST, segments=12, bevel=0.004),
             cylinder('HubCap', m['remap'], 0.018, 0.02, MAST + Vector((0, 0, 0.02)), segments=10, bevel=0.003)]
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        d = Vector((math.cos(a), math.sin(a), 0))
        tip = MAST + d * ROTOR_RADIUS + Vector((0, 0, -0.015))
        parts += [beam(f'Blade{k}', m['blade'], MAST + d * 0.03, tip, 0.035, 0.006),
                  beam(f'BladeTip{k}', m['remap'], MAST + d * (ROTOR_RADIUS - 0.04) + Vector((0, 0, -0.014)), tip, 0.036, 0.007)]
    blades = kit.merge('Rotor', parts, MAST)
    disc = cylinder('BlurDisc', m['blur'], ROTOR_RADIUS, 0.004, MAST + Vector((0, 0, -0.01)), segments=40, bevel=0)
    disc = kit.merge('RotorBlur', [disc], MAST)
    return blades, disc


def tail_rotor(m):
    parts = [cylinder('TailHub', m['steel'], 0.012, 0.02, TAIL_ROTOR, rotation=(0, math.pi / 2, 0), segments=10, bevel=0)]
    for k in range(4):
        a = k * math.pi / 2
        d = Vector((0, -math.sin(a), math.cos(a)))  # the box's z turned by a about x
        parts.append(box(f'TailBlade{k}', m['blade'], (0.004, 0.018, TAIL_ROTOR_RADIUS - 0.01),
                         TAIL_ROTOR + d * (TAIL_ROTOR_RADIUS + 0.01) / 2, bevel=0, rotation=(a, 0, 0)))
    blades = kit.merge('TailRotor', parts, TAIL_ROTOR)
    disc = cylinder('TailBlurDisc', m['blur'], TAIL_ROTOR_RADIUS, 0.003, TAIL_ROTOR, rotation=(0, math.pi / 2, 0), segments=24, bevel=0)
    return blades, kit.merge('TailRotorBlur', [disc], TAIL_ROTOR)


def gear(m):
    """The two main wheels (origin at the belly) and the tail wheel (origin under the
    boom) on legs; scaling them in z pulls them in."""
    def leg(name, x, y, top):
        return [
            beam(f'Leg{name}', m['steel'], (x * 0.7, y + 0.02, top), (x, y, WHEEL), 0.012),
            cylinder(f'Wheel{name}', m['tyre'], WHEEL, 0.018, (x, y, WHEEL), rotation=(0, math.pi / 2, 0), segments=12, bevel=0.003),
            cylinder(f'Hub{name}', m['steel_light'], WHEEL * 0.45, 0.021, (x, y, WHEEL), rotation=(0, math.pi / 2, 0), segments=8, bevel=0),
        ]

    main = kit.merge('Gear', leg('Left', -0.075, -0.15, BELLY) + leg('Right', 0.075, -0.15, BELLY), (0, -0.15, BELLY))
    tail = kit.merge('TailGear', leg('Tail', 0, 0.48, 0.22), (0, 0.48, 0.22))
    return main, tail


def build():
    root, body = air.start('NodHarpy', 'Harpy')
    m = materials()
    shell = kit.parent(hull(m), body)
    legs, tail_legs = (kit.parent(obj, body) for obj in gear(m))
    blades, blur = rotor(m)
    kit.parent(blades, body)
    kit.parent(blur, body)
    tail, tail_blur = tail_rotor(m)
    kit.parent(tail, body)
    kit.parent(tail_blur, body)
    flash = kit.parent(nod.flash(m, 'Flash', FLASH_AT, 0.035), body)
    nod.camouflage([shell, legs])

    channels = [(body, 'location'), (body, 'rotation_euler'), (legs, 'scale'), (tail_legs, 'scale'), (flash, 'scale'), (blades, 'rotation_euler'),
                (blur, 'scale'), (tail, 'rotation_euler'), (tail_blur, 'scale')]
    rad = math.radians
    hidden = Vector((HIDDEN,) * 3)

    def pose(angle, speed, gear_out, pitch=0.0, roll=0.0, lift=0.0):
        """angle: the main rotor's (radians); speed: 0 standing … 1 full."""
        shown = Vector((1, 1, 1)) if speed > 0.6 else hidden
        return {
            ('Body', 'location'): Vector((0, 0, lift)),
            ('Body', 'rotation_euler'): Vector((rad(pitch), rad(roll), 0)),
            ('Gear', 'scale'): Vector((1, 1, air.mix(0.02, 1, gear_out))),
            ('TailGear', 'scale'): Vector((1, 1, air.mix(0.02, 1, gear_out))),
            ('Flash', 'scale'): hidden,
            ('Rotor', 'rotation_euler'): Vector((0, 0, angle)),
            ('RotorBlur', 'scale'): shown,
            ('TailRotor', 'rotation_euler'): Vector((TAIL_RATIO * angle, 0, 0)),
            ('TailRotorBlur', 'scale'): shown,
        }

    frames = air.FLY_FRAMES

    def fly(f):
        t = 2 * math.pi * f / frames
        return pose(ROTOR_SPEED * f, 1, 0, pitch=-4 + 0.8 * math.sin(2 * t), roll=1.5 * math.sin(t), lift=0.008 * math.sin(t))

    def idle(f):
        return pose(0, 0, 1)

    # spinning up and down evenly: the rotor turns a whole turn in each (no jump to Fly or Idle)
    def take_off(f):
        T = air.TAKEOFF_FRAMES
        return pose(ROTOR_SPEED * f * f / (2 * T), f / T, 1 - air.span(f, 10, 28), pitch=air.mix(0, -4, air.span(f, 12, 30)))

    def land(f):
        T = air.LAND_FRAMES
        return pose(ROTOR_SPEED * (f - f * f / (2 * T)), 1 - f / T, air.span(f, 0, 16), pitch=air.mix(-4, 0, air.span(f, 0, 22)))

    def fire(f):
        v = fly(f)
        if f in (0, 1, 5, 6, 10, 11):  # a burst
            v[('Flash', 'scale')] = Vector((1, 1, 1)) * (1.0 if f % 5 == 0 else 1.3)
        v[('Body', 'rotation_euler')].x += rad(0.6 * math.sin(f * 2.1))
        return v

    air.clip('Idle', air.IDLE_FRAMES, channels, idle)
    air.clip('TakeOff', air.TAKEOFF_FRAMES, channels, take_off)
    air.clip('Fly', frames, channels, fly)
    air.clip('Land', air.LAND_FRAMES, channels, land)
    air.clip('Fire', FIRE_FRAMES, channels, fire)

    def rest():
        for (name, prop), value in idle(0).items():
            setattr(kit.collection().objects[name], prop, value)

    rest()
    return rest


if __name__ == '__main__':
    air.main(build, OUT, BLEND, {'Idle': [0], 'TakeOff': [20], 'Fly': [3], 'Fire': [1]}, scale=1.5, target=(0, 0.05, 0.2))
