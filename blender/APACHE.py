"""
Tiberian Fallout – Nod Harpy attack helicopter (APACHE), after Tiberian Sun.

A slim gunship, after the build icon and Tiberium Essence's Harpy: a narrow, faceted
fuselage with a large bubble canopy over the nose (framed for the two crew), a
three-barrelled chain gun in a ball turret under the chin and a sensor with a red eye
in front of it, two engine nacelles beside the raised rotor pylon (intakes in front,
exhausts angled out behind), short stub wings drooping a little with a rocket pod
under each and an end plate with a missile at the tips, and a thin tail boom ending
in a ducted tail rotor (a ring with a red rim) under two canted fins, a stabiliser
ahead of it. Four-bladed main rotor with red tips on a raised hub under a domed cap;
flying, a faint blur disc shows under the blades. Two main wheels and a tail wheel on
legs. Panel seams, a hatch, vents, nav lamps (red left, green right) and an antenna.

Nod's colours (nodvehicle.camouflage): the armour near black blotched with dark grey
and dark red; the fins, the wing end plates, the pods' noses, the duct's rim and
stripes red (house colour).

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

from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import aircraft as air  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402

OUT = os.path.join(air.PROJECT, 'public', 'models', 'APACHE.glb')
BLEND = os.path.join(HERE, 'APACHE.blend')

BELLY = 0.105                     # underside of the fuselage, landed
MAST = Vector((0, -0.02, 0.385))  # the rotor's hub
ROTOR_RADIUS = 0.46
TAIL_ROTOR = Vector((0, 0.625, 0.255))
TAIL_ROTOR_RADIUS = 0.058
DUCT = (0.066, 0.088, 0.05)       # the tail rotor's ring: inner and outer radius, depth
GUN = Vector((0, -0.42, 0.078))   # the chain gun's ball turret
FLASH_AT = Vector((0, -0.565, 0.078))
CANOPY = Vector((0, -0.335, 0.214))  # the bubble's middle, its radii and its tilt (nose down)
CANOPY_RADII = Vector((0.072, 0.185, 0.09))
CANOPY_TILT = 0.07
FIRE_FRAMES = 15                  # the rotor turns a whole number of quarter turns in it
WHEEL = 0.028
# the rotor at full speed: two turns per Fly loop (a quarter turn every 7.5 frames,
# the four blades read as turning, not as standing or running back)
ROTOR_SPEED = 2 * (2 * math.pi) / air.FLY_FRAMES
TAIL_RATIO = 3                    # the tail rotor turns three times as fast

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
HIDDEN = kit.HIDDEN

HULL = (  # y, half width, bottom, top
    (-0.565, 0.012, 0.135, 0.155), (-0.54, 0.036, 0.12, 0.182), (-0.49, 0.058, 0.108, 0.205), (-0.4, 0.074, BELLY, 0.222),
    (-0.26, 0.084, BELLY, 0.238), (-0.12, 0.09, BELLY, 0.262), (0.02, 0.092, 0.11, 0.285), (0.12, 0.082, 0.125, 0.285),
    (0.2, 0.06, 0.15, 0.272),
)
BOOM = ((0.17, 0.05, 0.16, 0.266), (0.3, 0.036, 0.196, 0.262), (0.48, 0.027, 0.218, 0.258), (0.57, 0.024, 0.224, 0.256))
NACELLE = ((-0.13, 0.022, 0.262, 0.292), (-0.1, 0.036, 0.25, 0.318), (0.1, 0.038, 0.25, 0.322), (0.16, 0.03, 0.258, 0.31),
           (0.2, 0.02, 0.266, 0.298))
NACELLE_X = 0.066


def materials():
    m = nod.materials()
    m.update({
        'blur': material('RotorBlur', srgb('#1a1a1c'), 0.8, alpha=0.22),
        'blade': material('RotorBlade', srgb('#2a2b2f'), 0.6, 0.4),
    })
    m['blur'].use_backface_culling = False
    return m


def shell(name, mat, sections, x=0.0, sides=12, power=2.6):
    """A faceted hull through rounded cross sections (y, half width, bottom, top):
    superellipses with `sides` corners (power 2 an ellipse, higher squarer), capped."""
    def ring(y, hw, zb, zt):
        zc, hh = (zb + zt) / 2, (zt - zb) / 2
        points = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            c, s = math.cos(a), math.sin(a)
            points.append((x + hw * math.copysign(abs(c) ** (2 / power), c), y, zc + hh * math.copysign(abs(s) ** (2 / power), s)))
        return points

    def build(bm):
        rings = [[bm.verts.new(p) for p in ring(*s)] for s in sections]
        for a, b in zip(rings, rings[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                bm.faces.new((a[i], a[j], b[j], b[i]))
        bm.faces.new(rings[0])
        bm.faces.new(rings[-1])

    obj = kit.mesh_object(name, build)
    kit.finish(obj, mat, 0)
    for poly in obj.data.polygons:
        poly.use_smooth = False  # faceted armour plates
    return obj


def duct(name, mat, inner, outer, depth, centre, segments=20):
    """A flat ring about the x axis (the tail rotor's duct), flat shaded."""
    centre = Vector(centre)

    def build(bm):
        loops = []
        for r, dx in ((outer, -depth / 2), (outer, depth / 2), (inner, depth / 2), (inner, -depth / 2)):
            loops.append([bm.verts.new(centre + Vector((dx, r * math.cos(2 * math.pi * k / segments), r * math.sin(2 * math.pi * k / segments))))
                          for k in range(segments)])
        for a, b in zip(loops, loops[1:] + loops[:1]):
            for i in range(segments):
                j = (i + 1) % segments
                bm.faces.new((a[i], a[j], b[j], b[i]))

    obj = kit.mesh_object(name, build)
    kit.finish(obj, mat, 0)
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj


def deck_vent(name, frame_mat, slat_mat, centre, width, length, slats=4, height=0.01):
    """A framed vent lying on a top face, its slats across (x) and in a row along y
    (detail.grille stands on a wall)."""
    centre = Vector(centre)
    parts = [box(f'{name}Frame', frame_mat, (width + 0.012, length + 0.012, height), centre, bevel=0.002)]
    for k in range(slats):
        y = -length / 2 + (k + 0.5) * length / slats
        parts.append(box(f'{name}Slat{k}', slat_mat, (width, length / slats * 0.45, height + 0.004), centre + Vector((0, y, 0)), bevel=0))
    return parts


def polyline(name, mat, points, width=0.008):
    """Beams through `points` (frames, rims, stripes), each a little longer so the
    corners close."""
    parts = []
    for k, (a, b) in enumerate(zip(points, points[1:])):
        a, b = Vector(a), Vector(b)
        overlap = (b - a).normalized() * width / 2
        parts.append(beam(f'{name}{k}', mat, a - overlap, b + overlap, width))
    return parts


def canopy(m):
    """The bubble over the nose and its frame: a bar along the top and two hoops (the
    gunner in front, the pilot behind)."""
    tilt = Euler((CANOPY_TILT, 0, 0)).to_matrix()

    def on(local, lift=1.04):
        return CANOPY + tilt @ (Vector(local) * lift)

    rx, ry, rz = CANOPY_RADII
    bubble = sphere('Canopy', m['glass'], 1.0, CANOPY, 18)
    bubble.scale = CANOPY_RADII
    bubble.rotation_euler = (CANOPY_TILT, 0, 0)
    parts = [bubble]
    parts += polyline('CanopyBar', m['steel'], [on((0, ry * math.cos(u), rz * math.sin(u))) for u in
                                               (math.radians(d) for d in range(20, 165, 18))], 0.011)
    for k, v in enumerate((-0.07, 0.06)):
        f = math.sqrt(1 - (v / ry) ** 2)
        parts += polyline(f'CanopyHoop{k}', m['steel'], [on((rx * f * math.cos(t), v, rz * f * math.sin(t))) for t in
                                                        (math.radians(d) for d in range(-10, 191, 20))], 0.011)
    return parts


def hull(m):
    """Fuselage, tail boom, wings, fins (camouflaged later) and their fittings."""
    parts = [
        shell('Fuselage', m['armour'], HULL),
        shell('Boom', m['armour'], BOOM, sides=10),
        *canopy(m),
        # the rotor pylon between the nacelles, its fairing and the mast
        kit.hexahedron('Pylon', m['armour_dark'], (
            (-0.03, -0.09, 0.27), (0.03, -0.09, 0.27), (0.03, 0.11, 0.27), (-0.03, 0.11, 0.27),
            (-0.026, -0.06, 0.33), (0.026, -0.06, 0.33), (0.026, 0.07, 0.33), (-0.026, 0.07, 0.33)), bevel=0.006),
        cylinder('MastFairing', m['armour_dark'], 0.036, 0.03, Vector((MAST.x, MAST.y, 0.338)), segments=12, bevel=0.006, radius2=0.024),
        cylinder('Mast', m['steel'], 0.016, MAST.z - 0.33, Vector((MAST.x, MAST.y, (MAST.z + 0.33) / 2)), segments=10, bevel=0),
        cylinder('Swashplate', m['steel_light'], 0.03, 0.008, Vector((MAST.x, MAST.y, 0.36)), segments=12, bevel=0.002),
        *[beam(f'PitchLink{k}', m['steel'], Vector((MAST.x + 0.024 * math.cos(a), MAST.y + 0.024 * math.sin(a), 0.36)),
               Vector((MAST.x + 0.024 * math.cos(a), MAST.y + 0.024 * math.sin(a), MAST.z - 0.01)), 0.005)
          for k, a in enumerate((math.pi / 4, 5 * math.pi / 4))],
        # the chin gun: the ball, its yoke and a three-barrelled cluster with shrouds
        box('GunMount', m['armour_dark'], (0.05, 0.06, 0.03), GUN + Vector((0, 0.005, 0.028)), bevel=0.008),
        sphere('GunBall', m['armour_dark'], 0.032, GUN, 14),
        cylinder('GunBreech', m['steel'], 0.02, 0.04, GUN + Vector((0, -0.04, 0)), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0.003),
        *[cylinder(f'GunBarrel{k}', m['steel'], 0.0055, 0.1, GUN + Vector((0.009 * math.cos(2 * math.pi * k / 3 + 0.5), -0.1,
                                                                          0.009 * math.sin(2 * math.pi * k / 3 + 0.5))),
                   rotation=(math.pi / 2, 0, 0), segments=6, bevel=0) for k in range(3)],
        cylinder('GunShroud', m['armour_dark'], 0.017, 0.014, GUN + Vector((0, -0.105, 0)), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0.002),
        cylinder('Muzzle', m['steel_light'], 0.017, 0.012, FLASH_AT + Vector((0, 0.022, 0)), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0),
        # the sensor under the nose tip with its red eye
        box('Sensor', m['armour_dark'], (0.036, 0.04, 0.03), (0, -0.52, 0.122), bevel=0.008),
        *detail.lamp('SensorEye', m['seam'], m['lamp_red'], (0, -0.542, 0.12), (0, -1, -0.2), 0.009),
        box('NoseCap', m['remap'], (0.03, 0.03, 0.02), (0, -0.552, 0.147), bevel=0.006),
        # boom fittings: a red stripe, the antenna, the tail gearbox in front of the duct
        box('BoomStripe', m['remap'], (0.056, 0.05, 0.012), (0, 0.33, 0.263), bevel=0.003),
        box('BoomStripeAft', m['remap'], (0.05, 0.03, 0.012), (0, 0.42, 0.26), bevel=0.003),
        beam('Antenna', m['steel'], (0, 0.18, 0.272), (0, 0.25, 0.35), 0.005),
        sphere('AntennaTip', m['steel_light'], 0.007, (0, 0.25, 0.35), 6),
        beam('Whip', m['steel'], (0.03, -0.08, 0.255), (0.045, 0.02, 0.27), 0.004),
        # the ducted tail rotor: the ring and its red rim, the fins over it, the stabiliser ahead
        duct('Duct', m['armour_dark'], DUCT[0], DUCT[1], DUCT[2], TAIL_ROTOR),
        duct('DuctRim', m['remap'], DUCT[1] - 0.004, DUCT[1] + 0.004, DUCT[2] * 0.6, TAIL_ROTOR),
        *[beam(f'DuctStrut{k}', m['steel'], TAIL_ROTOR + Vector((0, DUCT[0] * math.cos(a), DUCT[0] * math.sin(a))) * 1,
               TAIL_ROTOR + Vector((0, 0.012 * math.cos(a), 0.012 * math.sin(a))), 0.006) for k, a in enumerate((math.pi * 0.85, math.pi * 1.2))],
        cylinder('TailGearbox', m['armour_dark'], 0.016, DUCT[2] - 0.006, TAIL_ROTOR, rotation=(0, math.pi / 2, 0), segments=10, bevel=0.002),
        box('TailLight', m['lamp_white'], (0.012, 0.012, 0.012), (0, TAIL_ROTOR.y + DUCT[1] + 0.004, TAIL_ROTOR.z), bevel=0),
        kit.hexahedron('Stabiliser', m['armour_dark'], (
            (-0.12, 0.47, 0.232), (0.12, 0.47, 0.232), (0.12, 0.53, 0.232), (-0.12, 0.53, 0.232),
            (-0.12, 0.48, 0.244), (0.12, 0.48, 0.244), (0.12, 0.53, 0.244), (-0.12, 0.53, 0.244)), bevel=0.002),
        *seams_and_vents(m),
    ]
    for s in (-1, 1):
        x = s * NACELLE_X
        lamp = m['lamp_green'] if s > 0 else m['lamp_red']
        parts += [
            # engine nacelle: intake ring and fan face in front, a vent on top, the exhaust angled out behind
            shell(f'Nacelle{s}', m['armour'], NACELLE, x=x, sides=10, power=2.2),
            cylinder(f'Intake{s}', m['armour_dark'], 0.03, 0.02, (x, -0.125, 0.284), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.003),
            cylinder(f'IntakeFan{s}', m['seam'], 0.022, 0.02, (x, -0.13, 0.284), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0),
            cylinder(f'IntakeHub{s}', m['steel_light'], 0.007, 0.024, (x, -0.13, 0.284), rotation=(math.pi / 2, 0, 0), segments=8, bevel=0),
            *deck_vent(f'EngineVent{s}', m['steel'], m['seam'], (x + s * 0.004, 0.03, 0.322), 0.036, 0.07, 4, 0.008),
            cylinder(f'Exhaust{s}', m['steel'], 0.022, 0.05, (x + s * 0.012, 0.205, 0.284), rotation=(math.pi / 2, 0, s * 0.35), segments=12,
                     bevel=0.003, radius2=0.018),
            cylinder(f'ExhaustHole{s}', m['seam'], 0.015, 0.052, (x + s * 0.012, 0.207, 0.284), rotation=(math.pi / 2, 0, s * 0.35), segments=10,
                     bevel=0),
            # red stripe along the fuselage under the canopy
            beam(f'NoseStripe{s}', m['remap'], (s * 0.07, -0.47, 0.18), (s * 0.086, -0.2, 0.205), 0.008, 0.02),
            # stub wing drooping out to the tip, its end plate, the rocket pod and the missile
            kit.hexahedron(f'Wing{s}', m['armour'], (
                (s * 0.075, -0.075, 0.168), (s * 0.235, -0.045, 0.14), (s * 0.235, 0.045, 0.14), (s * 0.075, 0.07, 0.168),
                (s * 0.075, -0.068, 0.194), (s * 0.235, -0.04, 0.158), (s * 0.235, 0.045, 0.158), (s * 0.075, 0.07, 0.194)), bevel=0.004),
            kit.hexahedron(f'EndPlate{s}', m['remap'], (
                (s * 0.232, -0.06, 0.112), (s * 0.252, -0.06, 0.112), (s * 0.252, 0.05, 0.112), (s * 0.232, 0.05, 0.112),
                (s * 0.24, -0.045, 0.19), (s * 0.258, -0.045, 0.19), (s * 0.258, 0.06, 0.19), (s * 0.24, 0.06, 0.19)), bevel=0.003),
            *detail.lamp(f'NavLamp{s}', m['seam'], lamp, (s * 0.248, -0.062, 0.168), (0, -1, 0), 0.007),
            box(f'PodPylon{s}', m['armour_dark'], (0.016, 0.07, 0.03), (s * 0.155, -0.01, 0.15), bevel=0.003),
            cylinder(f'Pod{s}', m['armour_dark'], 0.027, 0.15, (s * 0.155, -0.01, 0.124), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.004),
            cylinder(f'PodBand{s}', m['steel'], 0.029, 0.012, (s * 0.155, 0.03, 0.124), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.002),
            cylinder(f'PodNose{s}', m['remap'], 0.027, 0.024, (s * 0.155, -0.097, 0.124), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.004,
                     radius2=0.021),
            *[cylinder(f'PodTube{s}{k}', m['seam'], 0.0065, 0.01, (s * 0.155 + 0.012 * math.cos(2 * math.pi * k / 6), -0.11,
                                                                   0.124 + 0.012 * math.sin(2 * math.pi * k / 6)),
                       rotation=(math.pi / 2, 0, 0), segments=6, bevel=0) for k in range(6)],
            cylinder(f'PodTubeMid{s}', m['seam'], 0.0065, 0.01, (s * 0.155, -0.11, 0.124), rotation=(math.pi / 2, 0, 0), segments=6, bevel=0),
            box(f'MissileRail{s}', m['steel'], (0.01, 0.1, 0.008), (s * 0.243, -0.01, 0.107), bevel=0),
            cylinder(f'Missile{s}', m['steel_light'], 0.0095, 0.12, (s * 0.243, -0.02, 0.096), rotation=(math.pi / 2, 0, 0), segments=8, bevel=0.002),
            cylinder(f'MissileTip{s}', m['remap'], 0.0095, 0.022, (s * 0.243, -0.091, 0.096), rotation=(math.pi / 2, 0, 0), segments=8, bevel=0,
                     radius2=0.002),
            *[box(f'MissileFin{s}{k}', m['steel'], (0.004 if k else 0.03, 0.02, 0.03 if k else 0.004), (s * 0.243, 0.03, 0.096), bevel=0)
              for k in range(2)],
            # canted fin on the duct
            kit.hexahedron(f'Fin{s}', m['remap'], (
                (s * 0.002, 0.585, 0.33), (s * 0.016, 0.585, 0.33), (s * 0.016, 0.67, 0.33), (s * 0.002, 0.67, 0.33),
                (s * 0.062, 0.655, 0.44), (s * 0.072, 0.655, 0.44), (s * 0.072, 0.705, 0.44), (s * 0.062, 0.705, 0.44)), bevel=0.003),
            box(f'FinLight{s}', m['lamp_red'], (0.01, 0.012, 0.01), (s * 0.067, 0.7, 0.443), bevel=0),
            box(f'StabiliserPlate{s}', m['remap'], (0.008, 0.06, 0.04), (s * 0.122, 0.505, 0.243), bevel=0.002),
        ]
    return kit.merge('Hull', parts)


def seams_and_vents(m):
    """Panel seams, the crew hatch, vents and rivets on the fuselage's sides and top."""
    parts = []
    for s in (-1, 1):
        side = s * 0.0925
        parts += [
            # the crew hatch behind the canopy
            *detail.seam(f'HatchFront{s}', m['seam'], (side, -0.12, 0.14), (side, -0.12, 0.235)),
            *detail.seam(f'HatchBack{s}', m['seam'], (side, 0.0, 0.14), (side, 0.0, 0.245)),
            *detail.seam(f'HatchTop{s}', m['seam'], (side, -0.12, 0.235), (side, 0.0, 0.245)),
            *detail.seam(f'HatchFoot{s}', m['seam'], (side, -0.12, 0.14), (side, 0.0, 0.14)),
            box(f'HatchHandle{s}', m['steel_light'], (0.006, 0.024, 0.006), (side + s * 0.002, -0.03, 0.19), bevel=0),
            *detail.grille(f'SideVent{s}', m['steel'], m['seam'], (s * 0.088, 0.09, 0.205), 0.06, 0.04, 'X', 4, 0.008),
            # seams round the nose and along the belly
            *detail.seam(f'NoseSeam{s}', m['seam'], (s * 0.074, -0.4, 0.13), (s * 0.084, -0.26, 0.13)),
            *detail.seam(f'BoomSeam{s}', m['seam'], (s * 0.04, 0.27, 0.21), (s * 0.04, 0.27, 0.255)),
            *detail.rivets(f'BoomRivets{s}', m['steel_light'], (s * 0.033, 0.33, 0.2), (s * 0.026, 0.46, 0.222), 4, 0.004, 'X'),
            *detail.rivets(f'WingRivets{s}', m['steel_light'], (s * 0.1, -0.05, 0.196), (s * 0.2, -0.035, 0.168), 3, 0.004, 'Z'),
        ]
    parts += [
        *detail.seam('TopSeam', m['seam'], (-0.05, -0.115, 0.258), (0.05, -0.115, 0.258)),
        *detail.seam('BellySeam', m['seam'], (0, -0.3, BELLY - 0.001), (0, 0.1, BELLY + 0.004)),
        *detail.lamp('BellyLamp', m['seam'], m['lamp_red'], (0, 0.02, 0.108), (0, 0, -1), 0.009),
    ]
    return parts


def rotor(m):
    """The main rotor about the hub: four tapered blades drooping a little with red tips,
    the hub with a domed cap, and the blur disc (its own object, shown only when the
    rotor runs fast)."""
    parts = [cylinder('Hub', m['steel'], 0.032, 0.022, MAST, segments=12, bevel=0.004),
             cylinder('HubRing', m['remap'], 0.046, 0.01, MAST + Vector((0, 0, 0.012)), segments=16, bevel=0.002)]
    cap = sphere('HubCap', m['armour_dark'], 1.0, MAST + Vector((0, 0, 0.016)), 16)
    cap.scale = (0.044, 0.044, 0.026)
    parts.append(cap)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        d = Vector((math.cos(a), math.sin(a), 0))
        n = Vector((-d.y, d.x, 0))  # across the blade

        def at(r, chord, z):
            return [MAST + d * r + n * chord / 2 + Vector((0, 0, z)), MAST + d * r - n * chord / 2 + Vector((0, 0, z))]

        root, tip = 0.05, ROTOR_RADIUS
        r0, r1 = at(root, 0.044, 0.0), at(tip, 0.032, -0.016)
        parts.append(kit.hexahedron(f'Blade{k}', m['blade'], (
            r0[0], r1[0], r1[1], r0[1],
            r0[0] + Vector((0, 0, 0.008)), r1[0] + Vector((0, 0, 0.006)), r1[1] + Vector((0, 0, 0.006)), r0[1] + Vector((0, 0, 0.008))),
            bevel=0))
        t0, t1 = at(tip - 0.045, 0.034, -0.0145), at(tip + 0.002, 0.033, -0.0162)
        parts.append(kit.hexahedron(f'BladeTip{k}', m['remap'], (
            t0[0], t1[0], t1[1], t0[1],
            t0[0] + Vector((0, 0, 0.008)), t1[0] + Vector((0, 0, 0.008)), t1[1] + Vector((0, 0, 0.008)), t0[1] + Vector((0, 0, 0.008))),
            bevel=0))
        parts.append(beam(f'Grip{k}', m['steel'], MAST + d * 0.02 + Vector((0, 0, 0.003)), MAST + d * 0.075 + Vector((0, 0, 0.002)), 0.024, 0.016))
    blades = kit.merge('Rotor', parts, MAST)
    disc = cylinder('BlurDisc', m['blur'], ROTOR_RADIUS, 0.004, MAST + Vector((0, 0, -0.01)), segments=40, bevel=0)
    disc = kit.merge('RotorBlur', [disc], MAST)
    return blades, disc


def tail_rotor(m, count=6):
    parts = [cylinder('TailHub', m['steel'], 0.013, DUCT[2] * 0.7, TAIL_ROTOR, rotation=(0, math.pi / 2, 0), segments=10, bevel=0),
             cylinder('TailHubCap', m['remap'], 0.008, DUCT[2] * 0.74, TAIL_ROTOR, rotation=(0, math.pi / 2, 0), segments=8, bevel=0)]
    for k in range(count):
        a = 2 * math.pi * k / count
        d = Vector((0, -math.sin(a), math.cos(a)))  # the box's z turned by a about x
        parts.append(box(f'TailBlade{k}', m['blade'], (0.004, 0.016, TAIL_ROTOR_RADIUS - 0.01),
                         TAIL_ROTOR + d * (TAIL_ROTOR_RADIUS + 0.01) / 2, bevel=0, rotation=(a + 0.25, 0, 0)))
    blades = kit.merge('TailRotor', parts, TAIL_ROTOR)
    disc = cylinder('TailBlurDisc', m['blur'], DUCT[0] - 0.003, 0.003, TAIL_ROTOR, rotation=(0, math.pi / 2, 0), segments=24, bevel=0)
    return blades, kit.merge('TailRotorBlur', [disc], TAIL_ROTOR)


def gear(m):
    """The two main wheels (origin at the belly) and the tail wheel (origin under the
    boom) on legs; scaling them in z pulls them in."""
    def leg(name, x, y, top):
        return [
            beam(f'Leg{name}', m['steel'], (x * 0.7, y + 0.02, top), (x, y, WHEEL), 0.012),
            beam(f'Damper{name}', m['steel_light'], (x * 0.7, y - 0.02, top), (x, y, WHEEL + 0.01), 0.008),
            box(f'Fork{name}', m['armour_dark'], (0.03, 0.02, 0.02), (x, y, WHEEL + 0.012), bevel=0.003),
            cylinder(f'Wheel{name}', m['tyre'], WHEEL, 0.018, (x, y, WHEEL), rotation=(0, math.pi / 2, 0), segments=12, bevel=0.003),
            cylinder(f'Hub{name}', m['steel_light'], WHEEL * 0.45, 0.021, (x, y, WHEEL), rotation=(0, math.pi / 2, 0), segments=8, bevel=0),
        ]

    main = kit.merge('Gear', leg('Left', -0.075, -0.17, BELLY) + leg('Right', 0.075, -0.17, BELLY), (0, -0.17, BELLY))
    tail = kit.merge('TailGear', leg('Tail', 0, 0.47, 0.22), (0, 0.47, 0.22))
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
