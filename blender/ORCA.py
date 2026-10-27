"""
Tiberian Fallout – GDI Orca fighter (ORCA), after Tiberian Sun.

A VTOL fighter, after the build icon: a short, deep fuselage with a rounded nose,
a two-pane canopy on top and two red lamps at the chin; a slim tail boom rising to a
forked V tail with house-colour tips. Short stub wings carry the two engine pods out at
the sides (round nacelles with dark intakes, glowing nozzles, a house-colour band and
navigation lights, red left, green right); they swing from cruise (level) into the
hover position (nozzles down). Under the wings two rocket pods with four tubes each,
three gear legs with pads under the fuselage.

The fuselage, wings and pods wear the light camouflage of GDI (baked, tinted with the
house colour in the game: GAPILE.camo_material).

Nodes for the game: "Flash" (the rockets' muzzle flash, between the pods); the
engine pods turn on "Engine-1"/"Engine1".

Clips (see aircraft.py)
    Idle     loop, 2 s: landed, gear out, engines off and level
    TakeOff  once, 1 s: the engines light up and swing into the hover position, the
             gear comes in
    Fly      loop, 1 s: engines glowing in the hover position, a gentle sway
    Land     once, 1 s: the gear goes out, the engines swing back level and go out
    Fire     once, 0.4 s: two rocket salvoes flash between the pods (Fly pose)

Run headless:

    blender -b --factory-startup --python blender/ORCA.py [-- --preview <dir>]

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
import DSHP  # noqa: E402 – loft(), camo()
import aircraft as air  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402 – flash()

OUT = os.path.join(air.PROJECT, 'public', 'models', 'ORCA.glb')
BLEND = os.path.join(HERE, 'ORCA.blend')

BELLY = 0.12                      # underside of the fuselage, landed (top of the gear)
ENGINE_X = 0.29
ENGINE = Vector((0, -0.1, 0.22))  # pivot of the right pod with x = ENGINE_X
NACELLE = (0.075, 0.32)           # radius, length
TILT_HOVER = -75                  # degrees about x: the nozzles swing down
PODS = (0.165, 0.11)              # rocket pods: x, z of their middle
FLASH_AT = Vector((0, -0.3, 0.1))
FIRE_FRAMES = 12

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
loft = DSHP.loft
HIDDEN = kit.HIDDEN

HULL = (  # y, half width, bottom, top
    (-0.5, 0.03, 0.17, 0.22), (-0.46, 0.075, 0.14, 0.27), (-0.38, 0.11, BELLY, 0.3), (-0.2, 0.125, BELLY, 0.31),
    (0.0, 0.12, BELLY, 0.3), (0.12, 0.09, 0.14, 0.28),
)
BOOM = ((0.11, 0.085, 0.15, 0.28), (0.3, 0.05, 0.2, 0.275), (0.5, 0.035, 0.23, 0.27))


def materials():
    m = kit.materials()
    m.update({
        'glass': material('Canopy', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#22384a'), strength=0.4),
        'red': material('WarningRed', srgb('#b3271c'), 0.6),
        'nozzle': material('GlowNozzle', srgb('#3a4048'), 0.5, emission=srgb('#8fd0ff'), strength=4),
        'plume': material('GlowPlume', (0, 0, 0), 1.0, emission=srgb('#9fd4ff'), strength=3, alpha=0.35),
        'flash': material('GlowFlash', (0, 0, 0), 1.0, emission=srgb('#ffd27a'), strength=6, alpha=0.7),
    })
    return m


def camo(obj, root, name):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{name}', root))
    return obj


def hull(m, root):
    """Fuselage, tail boom and wings in camouflage (one object) and their details."""
    shell = kit.merge('Hull', [
        loft('Fuselage', m['sand'], HULL, chamfer=0.45),
        loft('Boom', m['sand'], BOOM, chamfer=0.4),
        # stub wings out to the pods, thin, swept a little
        kit.hexahedron('Wing', m['sand'], (
            (-ENGINE_X + 0.04, -0.17, 0.2), (ENGINE_X - 0.04, -0.17, 0.2), (ENGINE_X - 0.04, -0.04, 0.2), (-ENGINE_X + 0.04, -0.04, 0.2),
            (-ENGINE_X + 0.04, -0.15, 0.235), (ENGINE_X - 0.04, -0.15, 0.235), (ENGINE_X - 0.04, -0.04, 0.23), (-ENGINE_X + 0.04, -0.04, 0.23)),
            bevel=0),
    ])
    for poly in shell.data.polygons:
        poly.use_smooth = False
    camo(shell, root, 'Hull')

    parts = [
        loft('Canopy', m['glass'], ((-0.44, 0.035, 0.24, 0.27), (-0.38, 0.08, 0.26, 0.325), (-0.27, 0.085, 0.28, 0.345),
                                    (-0.16, 0.06, 0.29, 0.33))),
        box('CanopyFrame', m['dark'], (0.012, 0.29, 0.012), (0, -0.3, 0.345), bevel=0.003),
        box('CanopyBar', m['dark'], (0.17, 0.012, 0.03), (0, -0.33, 0.333), bevel=0.003),
        box('Spine', m['sand_light'], (0.08, 0.3, 0.03), (0, -0.02, 0.305), bevel=0.01),
        box('Intake', m['steel'], (0.09, 0.09, 0.012), (0, 0.06, 0.29), bevel=0.003),
        *[box(f'IntakeSlat{k}', m['dark'], (0.075, 0.01, 0.014), (0, 0.03 + 0.02 * k, 0.292), bevel=0) for k in range(4)],
        box('ChinPanel', m['dark'], (0.12, 0.1, 0.012), (0, -0.25, BELLY - 0.003), bevel=0.003),
        # the V tail: two fins rising outwards, tips in the house colour; a small ventral fin
        *[kit.hexahedron(f'Fin{s}', m['sand_light'], (
            (s * 0.02, 0.4, 0.26), (s * 0.03, 0.4, 0.26), (s * 0.03, 0.53, 0.26), (s * 0.02, 0.53, 0.26),
            (s * 0.13, 0.47, 0.39), (s * 0.14, 0.47, 0.39), (s * 0.14, 0.55, 0.39), (s * 0.13, 0.55, 0.39)), bevel=0.004)
          for s in (-1, 1)],
        *[kit.hexahedron(f'FinTip{s}', m['remap'], (
            (s * 0.115, 0.455, 0.37), (s * 0.125, 0.455, 0.37), (s * 0.125, 0.55, 0.37), (s * 0.115, 0.55, 0.37),
            (s * 0.135, 0.468, 0.395), (s * 0.145, 0.468, 0.395), (s * 0.145, 0.556, 0.395), (s * 0.135, 0.556, 0.395)), bevel=0.002)
          for s in (-1, 1)],
        kit.hexahedron('VentralFin', m['sand_light'], (
            (-0.006, 0.42, 0.23), (0.006, 0.42, 0.23), (0.006, 0.52, 0.23), (-0.006, 0.52, 0.23),
            (-0.006, 0.47, 0.17), (0.006, 0.47, 0.17), (0.006, 0.53, 0.17), (-0.006, 0.53, 0.17)), bevel=0.002),
        box('BoomStripe', m['remap'], (0.075, 0.04, 0.01), (0, 0.24, 0.277), bevel=0.003),
        box('TailLight', m['lamp_white'], (0.02, 0.012, 0.012), (0, 0.505, 0.25), bevel=0),
        beam('Antenna', m['steel'], (0.03, 0.1, 0.3), (0.04, 0.16, 0.4), 0.006),
    ]
    for s in (-1, 1):
        parts += [
            # red lamps at the chin, as on the icon
            *detail.lamp(f'ChinLamp{s}', m['dark'], m['lamp_red'], (s * 0.06, -0.47, 0.16), (0, -1, -0.3), 0.014),
            box(f'NoseStripe{s}', m['remap'], (0.01, 0.12, 0.022), (s * 0.118, -0.3, 0.22), bevel=0.003),
            *[box(f'SideSlit{s}{k}', m['dark'], (0.008, 0.06, 0.012), (s * 0.122, -0.1 + 0.08 * k, 0.25), bevel=0.002) for k in range(3)],
            box(f'WingRoot{s}', m['sand_light'], (0.05, 0.14, 0.05), (s * 0.12, -0.1, 0.22), bevel=0.012),
            # rocket pods under the wings: four tubes in front, a remap band
            box(f'Pod{s}', m['steel'], (0.06, 0.2, 0.06), (s * PODS[0], -0.12, PODS[1]), bevel=0.012),
            box(f'PodBand{s}', m['remap'], (0.064, 0.025, 0.064), (s * PODS[0], -0.06, PODS[1]), bevel=0.01),
            box(f'PodPylon{s}', m['dark'], (0.02, 0.1, 0.06), (s * PODS[0], -0.11, 0.16), bevel=0.004),
            *[cylinder(f'Tube{s}{k}', m['dark'], 0.011, 0.02, (s * PODS[0] + (k % 2 - 0.5) * 0.026, -0.222, PODS[1] + (k // 2 - 0.5) * 0.026),
                       rotation=(math.pi / 2, 0, 0), segments=8, bevel=0) for k in range(4)],
        ]
    return shell, kit.merge('HullDetails', parts)


def nacelle(m, root, s):
    """An engine pod around its pivot; returns the joint's parts and the glow objects."""
    pivot = Vector((s * ENGINE_X, ENGINE.y, ENGINE.z))
    r, length = NACELLE
    along = (math.pi / 2, 0, 0)
    shell = kit.merge(f'Nacelle{s}', [
        cylinder(f'NacelleBody{s}', m['sand'], r, length, pivot, rotation=along, segments=20, bevel=0.01),
        cylinder(f'NacelleNose{s}', m['sand'], r * 0.8, 0.05, pivot - Vector((0, length / 2 + 0.02, 0)), rotation=along, segments=20,
                 bevel=0.006, radius2=r),
    ], pivot)
    camo(shell, root, f'Nacelle{s}')
    front, back = pivot.y - length / 2 - 0.045, pivot.y + length / 2
    parts = [
        cylinder(f'Intake{s}', m['dark'], r * 0.62, 0.012, Vector((pivot.x, front, pivot.z)), rotation=along, segments=18, bevel=0),
        cylinder(f'Spinner{s}', m['steel_light'], r * 0.22, 0.03, Vector((pivot.x, front - 0.005, pivot.z)), rotation=along, segments=10,
                 bevel=0.004),
        cylinder(f'NozzleRim{s}', m['steel'], r * 0.92, 0.04, Vector((pivot.x, back + 0.01, pivot.z)), rotation=along, segments=20,
                 bevel=0.004, radius2=r * 0.78),
        cylinder(f'Band{s}', m['remap'], r + 0.004, 0.035, Vector((pivot.x, pivot.y + 0.06, pivot.z)), rotation=along, segments=20, bevel=0.003),
        box(f'Fairing{s}', m['sand_light'], (0.03, 0.16, 0.05), pivot + Vector((-s * (r - 0.005), 0, 0)), bevel=0.01),
        *detail.rivets(f'Rivets{s}', m['steel'], pivot + Vector((0, -0.1, r + 0.002)), pivot + Vector((0, 0.08, r + 0.002)), 5, 0.005, 'Z'),
    ]
    details = kit.merge(f'NacelleDetails{s}', parts, pivot)
    nav = 'green' if s > 0 else 'red'
    light = pivot + Vector((s * (r + 0.006), -0.05, 0.02))
    navlight = kit.merge(f'NavLight{s}', [sphere(f'NavBulb{s}', m[f'lamp_{nav}'], 0.012, light, 8),
                                         sphere(f'NavHalo{s}', m[f'glow_{nav}'], 0.026, light, 8)], pivot)
    nozzle = cylinder(f'Nozzle{s}', m['nozzle'], r * 0.72, 0.01, Vector((pivot.x, back + 0.028, pivot.z)), rotation=along, segments=18, bevel=0)
    nozzle = kit.merge(f'NozzleGlow{s}', [nozzle], Vector((pivot.x, back + 0.028, pivot.z)))
    plume = cylinder(f'PlumeCone{s}', m['plume'], r * 0.6, 0.26, Vector((pivot.x, back + 0.16, pivot.z)), rotation=(-math.pi / 2, 0, 0),
                     segments=16, bevel=0, radius2=r * 0.15)
    plume = kit.merge(f'Plume{s}', [plume], Vector((pivot.x, back + 0.03, pivot.z)))
    return pivot, (shell, details, navlight), nozzle, plume


def gear(m):
    """Nose leg and two main legs with pads; origin at the belly, scaling it in z pulls
    them in."""
    parts = []
    for name, (x, y) in (('Nose', (0, -0.3)), ('Left', (-0.085, 0.04)), ('Right', (0.085, 0.04))):
        parts += [
            cylinder(f'Leg{name}', m['steel_light'], 0.012, BELLY, (x, y, BELLY / 2), segments=8, bevel=0),
            cylinder(f'Strut{name}', m['steel'], 0.018, 0.04, (x, y, BELLY - 0.03), segments=8, bevel=0.002),
            cylinder(f'Pad{name}', m['dark'], 0.03, 0.012, (x, y, 0.006), segments=12, bevel=0.002),
        ]
    return kit.merge('Gear', parts, (0, 0, BELLY))


def build():
    root, body = air.start('GDIOrca', 'Orca')
    m = materials()
    for obj in hull(m, root):
        kit.parent(obj, body)
    legs = kit.parent(gear(m), body)
    engines, nozzles, plumes = [], [], []
    for s in (-1, 1):
        pivot, parts, nozzle, plume = nacelle(m, root, s)
        joint = kit.parent(kit.empty(f'Engine{s}', pivot), body)
        for obj in (*parts, nozzle, plume):
            kit.parent(obj, joint)
        engines.append(joint)
        nozzles.append(nozzle)
        plumes.append(plume)
    flash = kit.parent(nod.flash(m, 'Flash', FLASH_AT, 0.045), body)

    channels = [(body, 'location'), (body, 'rotation_euler'), (legs, 'scale'), (flash, 'scale')]
    for joint, nozzle, plume in zip(engines, nozzles, plumes):
        channels += [(joint, 'rotation_euler'), (nozzle, 'scale'), (plume, 'scale')]

    rad = math.radians
    hidden = Vector((HIDDEN,) * 3)

    def pose(tilt, thrust, gear_out, pitch=0.0, roll=0.0, lift=0.0, fire=None):
        v = {
            ('Body', 'location'): Vector((0, 0, lift)),
            ('Body', 'rotation_euler'): Vector((rad(pitch), rad(roll), 0)),
            ('Gear', 'scale'): Vector((1, 1, air.mix(0.02, 1, gear_out))),
            ('Flash', 'scale'): fire if fire is not None else hidden,
        }
        for joint, nozzle, plume in zip(engines, nozzles, plumes):
            v[(joint.name, 'rotation_euler')] = Vector((rad(tilt), 0, 0))
            v[(nozzle.name, 'scale')] = Vector((1, 1, 1)) if thrust > 0.05 else hidden
            v[(plume.name, 'scale')] = Vector((1, thrust, 1)) if thrust > 0.05 else hidden
        return v

    def flicker(f):
        return 1 + 0.12 * math.sin(f * 2.3) * math.sin(f * 0.7 + 1)

    def fly(f):
        t = 2 * math.pi * f / air.FLY_FRAMES
        return pose(TILT_HOVER, flicker(f), 0, pitch=-2 + 0.8 * math.sin(2 * t), roll=1.5 * math.sin(t), lift=0.008 * math.sin(t))

    def idle(f):
        return pose(0, 0, 1)

    def take_off(f):
        return pose(air.mix(0, TILT_HOVER, air.span(f, 4, 24)), air.span(f, 0, 10) * flicker(f), 1 - air.span(f, 12, 28),
                    pitch=air.mix(0, -2, air.span(f, 10, 30)))

    def land(f):
        return pose(air.mix(TILT_HOVER, 0, air.span(f, 8, 28)), (1 - air.span(f, 18, 30)) * flicker(f), air.span(f, 0, 16),
                    pitch=air.mix(-2, 0, air.span(f, 0, 20)))

    def fire(f):
        v = fly(f)
        if f in (0, 1, 5, 6):  # two salvoes
            v[('Flash', 'scale')] = Vector((1, 1, 1)) * (1.3 if f % 5 else 1.0)
        v[('Body', 'rotation_euler')].x += rad(1.5 * math.sin(math.pi * min(1, f / 8)))  # a small kick
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
    air.main(build, OUT, BLEND, {'Idle': [0], 'TakeOff': [15], 'Fly': [0], 'Fire': [1]}, bake=512, scale=1.5, target=(0, 0, 0.2))
