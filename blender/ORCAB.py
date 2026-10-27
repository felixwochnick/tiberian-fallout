"""
Tiberian Fallout – GDI Orca bomber (ORCAB), after Tiberian Sun.

The heavy brother of the Orca fighter (ORCA.py), a third bigger, after the build icon:
a broad, deep fuselage with a blunt nose, a stepped canopy and two red chin lamps, a
spine with an air intake, a long tail boom rising to a forked V tail with house-colour
tips. Wide stub wings carry two big engine pods (round nacelles with dark intakes,
glowing nozzles, house-colour bands and navigation lights, red left, green right);
they swing from cruise (level) into the hover position (nozzles down). Under the
belly the bomb bay: two doors hinged at its sides; four gear legs with pads.

The fuselage, wings and pods wear the light camouflage of GDI (baked, tinted with the
house colour in the game: GAPILE.camo_material).

Nodes for the game: "Flash" (under the open bomb bay, where the bombs leave); the
engine pods turn on "Engine-1"/"Engine1", the bay doors on "BayDoor-1"/"BayDoor1";
"Bomb" falls out of the bay in Fire.

Clips (see aircraft.py)
    Idle     loop, 2 s: landed, gear out, engines off and level, bay shut
    TakeOff  once, 1 s: the engines light up and swing into the hover position, the
             gear comes in
    Fly      loop, 1 s: engines glowing in the hover position, a gentle sway
    Land     once, 1 s: the gear goes out, the engines swing back level and go out
    Fire     once, 0.8 s: the bay doors swing open, a bomb drops out (the flash under
             the bay), the doors close again (Fly pose)

Run headless:

    blender -b --factory-startup --python blender/ORCAB.py [-- --preview <dir>]

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
import nodvehicle as nod  # noqa: E402 – flash()

OUT = os.path.join(air.PROJECT, 'public', 'models', 'ORCAB.glb')
BLEND = os.path.join(HERE, 'ORCAB.blend')

BELLY = 0.16                      # underside of the fuselage, landed (top of the gear)
ENGINE_X = 0.4
ENGINE = Vector((0, -0.12, 0.31))  # pivot of the right pod with x = ENGINE_X
NACELLE = (0.1, 0.42)             # radius, length
TILT_HOVER = -75                  # degrees about x: the nozzles swing down
BAY = (-0.26, 0.06)               # the bomb bay from y to y
BAY_HALF = 0.085                  # half its width (the doors' hinges)
DOOR_OPEN = 80                    # degrees
FLASH_AT = Vector((0, (BAY[0] + BAY[1]) / 2, BELLY - 0.07))
FIRE_FRAMES = 24
DROP = (6, 18)                    # frames: the bomb leaves the bay … has fallen away

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
loft = DSHP.loft
HIDDEN = kit.HIDDEN

HULL = (  # y, half width, bottom, top
    (-0.68, 0.05, 0.24, 0.3), (-0.62, 0.11, 0.19, 0.37), (-0.52, 0.16, BELLY, 0.41), (-0.25, 0.175, BELLY, 0.43),
    (0.05, 0.17, BELLY, 0.42), (0.2, 0.12, 0.19, 0.39),
)
BOOM = ((0.19, 0.115, 0.21, 0.39), (0.45, 0.07, 0.28, 0.385), (0.7, 0.045, 0.32, 0.375))


def materials():
    m = kit.materials()
    m.update({
        'glass': material('Canopy', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#22384a'), strength=0.4),
        'nozzle': material('GlowNozzle', srgb('#3a4048'), 0.5, emission=srgb('#8fd0ff'), strength=4),
        'plume': material('GlowPlume', (0, 0, 0), 1.0, emission=srgb('#9fd4ff'), strength=3, alpha=0.35),
        'flash': material('GlowFlash', (0, 0, 0), 1.0, emission=srgb('#ffd27a'), strength=6, alpha=0.7),
        'bomb': material('BombCasing', srgb('#3c4134'), 0.6, 0.4),
    })
    return m


def camo(obj, root, name):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{name}', root))
    return obj


def hull(m, root):
    """Fuselage, tail boom and wings in camouflage (one object) and their details."""
    w0, w1 = ENGINE_X - 0.06, -ENGINE_X + 0.06
    shell = kit.merge('Hull', [
        loft('Fuselage', m['sand'], HULL, chamfer=0.45),
        loft('Boom', m['sand'], BOOM, chamfer=0.4),
        kit.hexahedron('Wing', m['sand'], (
            (w1, -0.22, 0.29), (w0, -0.22, 0.29), (w0, -0.03, 0.29), (w1, -0.03, 0.29),
            (w1, -0.2, 0.33), (w0, -0.2, 0.33), (w0, -0.03, 0.325), (w1, -0.03, 0.325)), bevel=0),
    ])
    for poly in shell.data.polygons:
        poly.use_smooth = False
    camo(shell, root, 'Hull')

    parts = [
        loft('Canopy', m['glass'], ((-0.6, 0.05, 0.33, 0.37), (-0.53, 0.11, 0.36, 0.445), (-0.4, 0.115, 0.39, 0.47),
                                    (-0.27, 0.08, 0.4, 0.45))),
        box('CanopyFrame', m['dark'], (0.014, 0.34, 0.014), (0, -0.43, 0.47), bevel=0.003),
        box('CanopyBar', m['dark'], (0.23, 0.014, 0.04), (0, -0.45, 0.455), bevel=0.003),
        box('Spine', m['sand_light'], (0.12, 0.42, 0.035), (0, -0.04, 0.43), bevel=0.012),
        box('Intake', m['steel'], (0.13, 0.12, 0.014), (0, 0.06, 0.448), bevel=0.003),
        *[box(f'IntakeSlat{k}', m['dark'], (0.11, 0.012, 0.016), (0, 0.02 + 0.026 * k, 0.45), bevel=0) for k in range(4)],
        box('ChinPanel', m['dark'], (0.16, 0.12, 0.014), (0, -0.4, BELLY - 0.003), bevel=0.003),
        # the bay: a dark recess under the doors
        box('BayWell', m['dark'], (BAY_HALF * 2, BAY[1] - BAY[0], 0.006), (0, (BAY[0] + BAY[1]) / 2, BELLY - 0.002), bevel=0),
        *[kit.hexahedron(f'Fin{s}', m['sand_light'], (
            (s * 0.025, 0.58, 0.36), (s * 0.04, 0.58, 0.36), (s * 0.04, 0.72, 0.36), (s * 0.025, 0.72, 0.36),
            (s * 0.18, 0.65, 0.54), (s * 0.195, 0.65, 0.54), (s * 0.195, 0.74, 0.54), (s * 0.18, 0.74, 0.54)), bevel=0.005)
          for s in (-1, 1)],
        *[kit.hexahedron(f'FinTip{s}', m['remap'], (
            (s * 0.16, 0.632, 0.515), (s * 0.175, 0.632, 0.515), (s * 0.175, 0.735, 0.515), (s * 0.16, 0.735, 0.515),
            (s * 0.183, 0.648, 0.545), (s * 0.198, 0.648, 0.545), (s * 0.198, 0.746, 0.545), (s * 0.183, 0.746, 0.545)), bevel=0.002)
          for s in (-1, 1)],
        kit.hexahedron('VentralFin', m['sand_light'], (
            (-0.008, 0.58, 0.32), (0.008, 0.58, 0.32), (0.008, 0.7, 0.32), (-0.008, 0.7, 0.32),
            (-0.008, 0.64, 0.25), (0.008, 0.64, 0.25), (0.008, 0.71, 0.25), (-0.008, 0.71, 0.25)), bevel=0.002),
        box('BoomStripe', m['remap'], (0.1, 0.05, 0.012), (0, 0.34, 0.386), bevel=0.003),
        box('TailLight', m['lamp_white'], (0.024, 0.014, 0.014), (0, 0.705, 0.35), bevel=0),
        beam('Antenna', m['steel'], (0.05, 0.2, 0.42), (0.05, 0.22, 0.54), 0.007),
    ]
    for s in (-1, 1):
        parts += [
            *detail.lamp(f'ChinLamp{s}', m['dark'], m['lamp_red'], (s * 0.08, -0.65, 0.22), (0, -1, -0.3), 0.017),
            box(f'NoseStripe{s}', m['remap'], (0.012, 0.16, 0.028), (s * 0.168, -0.4, 0.31), bevel=0.003),
            *[box(f'SideSlit{s}{k}', m['dark'], (0.01, 0.07, 0.014), (s * 0.174, -0.15 + 0.09 * k, 0.35), bevel=0.002) for k in range(3)],
            box(f'WingRoot{s}', m['sand_light'], (0.07, 0.18, 0.06), (s * 0.17, -0.12, 0.31), bevel=0.015),
            box(f'BayRail{s}', m['steel'], (0.012, BAY[1] - BAY[0] + 0.02, 0.012), (s * (BAY_HALF + 0.01), (BAY[0] + BAY[1]) / 2, BELLY - 0.004),
                bevel=0.002),
            box(f'Sponson{s}', m['sand_light'], (0.04, 0.3, 0.05), (s * 0.165, -0.1, BELLY + 0.03), bevel=0.01),
        ]
    return shell, kit.merge('HullDetails', parts)


def nacelle(m, root, s):
    """An engine pod around its pivot; returns the joint's parts and the glow objects."""
    pivot = Vector((s * ENGINE_X, ENGINE.y, ENGINE.z))
    r, length = NACELLE
    along = (math.pi / 2, 0, 0)
    shell = kit.merge(f'Nacelle{s}', [
        cylinder(f'NacelleBody{s}', m['sand'], r, length, pivot, rotation=along, segments=20, bevel=0.01),
        cylinder(f'NacelleNose{s}', m['sand'], r * 0.8, 0.06, pivot - Vector((0, length / 2 + 0.025, 0)), rotation=along, segments=20,
                 bevel=0.006, radius2=r),
    ], pivot)
    camo(shell, root, f'Nacelle{s}')
    front, back = pivot.y - length / 2 - 0.055, pivot.y + length / 2
    parts = [
        cylinder(f'Intake{s}', m['dark'], r * 0.62, 0.012, Vector((pivot.x, front, pivot.z)), rotation=along, segments=18, bevel=0),
        cylinder(f'Spinner{s}', m['steel_light'], r * 0.22, 0.035, Vector((pivot.x, front - 0.006, pivot.z)), rotation=along, segments=10,
                 bevel=0.004),
        cylinder(f'NozzleRim{s}', m['steel'], r * 0.92, 0.05, Vector((pivot.x, back + 0.012, pivot.z)), rotation=along, segments=20,
                 bevel=0.004, radius2=r * 0.78),
        cylinder(f'Band{s}', m['remap'], r + 0.004, 0.045, Vector((pivot.x, pivot.y + 0.08, pivot.z)), rotation=along, segments=20, bevel=0.003),
        cylinder(f'Band2{s}', m['remap'], r + 0.004, 0.02, Vector((pivot.x, pivot.y - 0.1, pivot.z)), rotation=along, segments=20, bevel=0.002),
        box(f'Fairing{s}', m['sand_light'], (0.04, 0.22, 0.06), pivot + Vector((-s * (r - 0.005), 0, 0)), bevel=0.012),
        *detail.rivets(f'Rivets{s}', m['steel'], pivot + Vector((0, -0.14, r + 0.002)), pivot + Vector((0, 0.11, r + 0.002)), 6, 0.006, 'Z'),
    ]
    details = kit.merge(f'NacelleDetails{s}', parts, pivot)
    nav = 'green' if s > 0 else 'red'
    light = pivot + Vector((s * (r + 0.007), -0.06, 0.02))
    navlight = kit.merge(f'NavLight{s}', [sphere(f'NavBulb{s}', m[f'lamp_{nav}'], 0.014, light, 8),
                                         sphere(f'NavHalo{s}', m[f'glow_{nav}'], 0.03, light, 8)], pivot)
    nozzle = cylinder(f'Nozzle{s}', m['nozzle'], r * 0.72, 0.01, Vector((pivot.x, back + 0.035, pivot.z)), rotation=along, segments=18, bevel=0)
    nozzle = kit.merge(f'NozzleGlow{s}', [nozzle], Vector((pivot.x, back + 0.035, pivot.z)))
    plume = cylinder(f'PlumeCone{s}', m['plume'], r * 0.6, 0.32, Vector((pivot.x, back + 0.2, pivot.z)), rotation=(-math.pi / 2, 0, 0),
                     segments=16, bevel=0, radius2=r * 0.15)
    plume = kit.merge(f'Plume{s}', [plume], Vector((pivot.x, back + 0.04, pivot.z)))
    return pivot, (shell, details, navlight), nozzle, plume


def gear(m):
    """Nose legs and main legs with pads; origin at the belly, scaling it in z pulls them in."""
    parts = []
    for name, (x, y) in (('NoseL', (-0.06, -0.48)), ('NoseR', (0.06, -0.48)), ('Left', (-0.13, 0.12)), ('Right', (0.13, 0.12))):
        parts += [
            cylinder(f'Leg{name}', m['steel_light'], 0.015, BELLY, (x, y, BELLY / 2), segments=8, bevel=0),
            cylinder(f'Strut{name}', m['steel'], 0.022, 0.05, (x, y, BELLY - 0.035), segments=8, bevel=0.002),
            cylinder(f'Pad{name}', m['dark'], 0.036, 0.014, (x, y, 0.007), segments=12, bevel=0.002),
        ]
    return kit.merge('Gear', parts, (0, 0, BELLY))


def bay_door(m, root, s):
    """A bay door hinged at the bay's side s; turning it about y swings it down."""
    hinge = Vector((s * BAY_HALF, (BAY[0] + BAY[1]) / 2, BELLY - 0.006))
    door = box(f'BayDoorPanel{s}', m['sand'], (BAY_HALF, BAY[1] - BAY[0], 0.008), hinge - Vector((s * BAY_HALF / 2, 0, 0)), bevel=0.002)
    door = kit.merge(f'BayDoor{s}', [door], hinge)
    camo(door, root, f'BayDoor{s}')
    return door


def build():
    root, body = air.start('GDIOrcaBomber', 'OrcaBomber')
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
    doors = [kit.parent(bay_door(m, root, s), body) for s in (-1, 1)]
    bomb_at = Vector((0, (BAY[0] + BAY[1]) / 2, BELLY - 0.04))
    bomb = kit.merge('Bomb', [
        cylinder('BombBody', m['bomb'], 0.03, 0.16, bomb_at, rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.008),
        cylinder('BombNose', m['bomb'], 0.03, 0.05, bomb_at - Vector((0, 0.1, 0)), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0,
                 radius2=0.008),
        cylinder('BombBand', m['remap'], 0.032, 0.02, bomb_at - Vector((0, 0.04, 0)), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0),
        box('BombFinV', m['dark'], (0.006, 0.05, 0.09), bomb_at + Vector((0, 0.09, 0)), bevel=0),
        box('BombFinH', m['dark'], (0.09, 0.05, 0.006), bomb_at + Vector((0, 0.09, 0)), bevel=0),
    ], bomb_at)
    kit.parent(bomb, body)
    flash = kit.parent(nod.flash(m, 'Flash', FLASH_AT, 0.05, facing=(0, 0, -1)), body)

    channels = [(body, 'location'), (body, 'rotation_euler'), (legs, 'scale'), (flash, 'scale'), (bomb, 'location'), (bomb, 'scale')]
    for door in doors:
        channels.append((door, 'rotation_euler'))
    for joint, nozzle, plume in zip(engines, nozzles, plumes):
        channels += [(joint, 'rotation_euler'), (nozzle, 'scale'), (plume, 'scale')]

    rad = math.radians
    hidden = Vector((HIDDEN,) * 3)

    def pose(tilt, thrust, gear_out, pitch=0.0, roll=0.0, lift=0.0, door=0.0):
        v = {
            ('Body', 'location'): Vector((0, 0, lift)),
            ('Body', 'rotation_euler'): Vector((rad(pitch), rad(roll), 0)),
            ('Gear', 'scale'): Vector((1, 1, air.mix(0.02, 1, gear_out))),
            ('Flash', 'scale'): hidden,
            ('Bomb', 'location'): bomb_at.copy(),
            ('Bomb', 'scale'): hidden,
        }
        for d, s in zip(doors, (-1, 1)):
            v[(d.name, 'rotation_euler')] = Vector((0, rad(s * DOOR_OPEN * door), 0))
        for joint, nozzle, plume in zip(engines, nozzles, plumes):
            v[(joint.name, 'rotation_euler')] = Vector((rad(tilt), 0, 0))
            v[(nozzle.name, 'scale')] = Vector((1, 1, 1)) if thrust > 0.05 else hidden
            v[(plume.name, 'scale')] = Vector((1, thrust, 1)) if thrust > 0.05 else hidden
        return v

    def flicker(f):
        return 1 + 0.12 * math.sin(f * 2.3) * math.sin(f * 0.7 + 1)

    def fly(f, frames=air.FLY_FRAMES):
        t = 2 * math.pi * f / frames
        return pose(TILT_HOVER, flicker(f), 0, pitch=-2 + 0.6 * math.sin(2 * t), roll=1.2 * math.sin(t), lift=0.008 * math.sin(t))

    def idle(f):
        return pose(0, 0, 1)

    def take_off(f):
        return pose(air.mix(0, TILT_HOVER, air.span(f, 4, 24)), air.span(f, 0, 10) * flicker(f), 1 - air.span(f, 12, 28),
                    pitch=air.mix(0, -2, air.span(f, 10, 30)))

    def land(f):
        return pose(air.mix(TILT_HOVER, 0, air.span(f, 8, 28)), (1 - air.span(f, 18, 30)) * flicker(f), air.span(f, 0, 16),
                    pitch=air.mix(-2, 0, air.span(f, 0, 20)))

    def fire(f):
        # the Fly loop's sway over the whole clip would not end where Fly goes on: hold its first pose
        v = fly(0)
        door = air.span(f, 0, 5) * (1 - air.span(f, 17, FIRE_FRAMES))
        for d, s in zip(doors, (-1, 1)):
            v[(d.name, 'rotation_euler')] = Vector((0, rad(s * DOOR_OPEN * door), 0))
        if DROP[0] <= f < DROP[1]:
            t = (f - DROP[0]) / (DROP[1] - DROP[0])
            v[('Bomb', 'location')] = bomb_at - Vector((0, -0.04 * t, 0.5 * t * t + 0.03))
            v[('Bomb', 'scale')] = Vector((1, 1, 1))
        if f in (DROP[0], DROP[0] + 1):
            v[('Flash', 'scale')] = Vector((1, 1, 1)) * (1.3 if f > DROP[0] else 1.0)
        v[('Body', 'rotation_euler')].x += rad(1.0 * math.sin(math.pi * air.span(f, DROP[0], DROP[0] + 10)))  # it lifts a little
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
    air.main(build, OUT, BLEND, {'Idle': [0], 'TakeOff': [15], 'Fly': [0], 'Fire': [10]}, bake=512, scale=2.0, target=(0, 0, 0.25))
