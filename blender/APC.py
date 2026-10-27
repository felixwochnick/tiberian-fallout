"""
Tiberian Fallout – GDI amphibious APC (APC), after Tiberian Sun.

A boxy amphibious troop carrier on six big wheels, three a side, tucked under the
wide upper hull: a boat-like bow under a long sloped glacis with vision blocks, a flat
roof with a raised troop compartment at the back (two hatches, periscopes, grab rails,
an antenna), small square windows along the slanted flanks, a folded trim vane on the
glacis, two water-jet outlets low at the back and the big rear ramp between the tail
lights. The hull is in the light camouflage of the buildings, tinted with the house
colour in the game (GAPILE.camo_material); stripes along the flanks, the roof plate
and a band on the ramp are in the house colour. It carries no weapon.

Clips (see nodvehicle.py for Idle and Walk):
    Idle     loop, 2 s: the engine runs, the body shivers a little
    Walk     loop: driving, the wheels turn (one turn per loop), the body rocks; the
             root's walkSpeed (glTF extras) is the ground speed in cells per second
    Unload   once, 0.8 s: the rear ramp drops onto the ground and closes again

Run headless:

    blender -b --factory-startup --python blender/APC.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the vehicle.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'APC.glb')
BLEND = os.path.join(HERE, 'APC.blend')

WHEEL_RADIUS = 0.075
WHEEL_X = 0.265
WHEEL_WIDTH = 0.065
AXLES = (-0.27, 0.0, 0.27)
WALK_FRAMES = 26
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
UNLOAD_FRAMES = 24
# the hull: the wide upper part over the wheels (sides slanted in), the glacis from
# its front edge up to the roof
SPONSON = (0.19, 0.31)        # bottom of the upper hull (z), its half width there
ROOF = (0.37, 0.27)           # the roof (z), its half width
FRONT = (-0.5, -0.3)          # the glacis: bottom edge (y), top edge (y)
BACK = 0.44
RAMP_HINGE = Vector((0, 0.452, 0.09))
RAMP_HEIGHT = 0.26
RAMP_OPEN = math.radians(-110)  # down: its top edge on the ground
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'tyre': material('Tyre', srgb('#25231f'), 0.9, 0.1),
        'glass': material('Windscreen', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#3a6a96'), strength=0.6),
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
    })
    return m


def camo(obj, root):
    """The light camouflage (baked; tinted with the house colour in the game)."""
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def glacis(t, out=0.0):
    """A point on the glacis, t from its bottom edge (0) to the roof (1); its normal."""
    p = Vector((0, FRONT[0] + (FRONT[1] - FRONT[0]) * t, SPONSON[0] + (ROOF[0] - SPONSON[0]) * t))
    n = Vector((0, -(ROOF[0] - SPONSON[0]), FRONT[1] - FRONT[0])).normalized()
    return p + n * out, n


GLACIS_TILT = math.atan2(ROOF[0] - SPONSON[0], FRONT[1] - FRONT[0]) - math.pi / 2  # a thin plate's tilt (about x) onto it


def side_x(z):
    """The upper hull's half width at height z (its flanks lean in)."""
    return SPONSON[1] + (ROOF[1] - SPONSON[1]) * (z - SPONSON[0]) / (ROOF[0] - SPONSON[0])


SIDE_TILT = math.atan2(SPONSON[1] - ROOF[1], ROOF[0] - SPONSON[0])


def hull(m, root):
    """The camouflaged hull: the bow below, the upper hull over the wheels, the
    raised troop compartment."""
    z0, w0 = SPONSON
    z1, w1 = ROOF
    shell = kit.merge('Hull', [
        # the bow and belly between the wheels, boat-like in front
        kit.hexahedron('Belly', m['sand'], (
            (-0.18, -0.38, 0.06), (0.18, -0.38, 0.06), (0.18, BACK, 0.06), (-0.18, BACK, 0.06),
            (-0.2, FRONT[0] - 0.01, z0 + 0.01), (0.2, FRONT[0] - 0.01, z0 + 0.01), (0.2, BACK, z0 + 0.01), (-0.2, BACK, z0 + 0.01)), bevel=0.012),
        kit.hexahedron('Upper', m['sand'], (
            (-w0, FRONT[0], z0), (w0, FRONT[0], z0), (w0, BACK, z0), (-w0, BACK, z0),
            (-w1, FRONT[1], z1), (w1, FRONT[1], z1), (w1, BACK - 0.01, z1), (-w1, BACK - 0.01, z1)), bevel=0.014),
        # the raised troop compartment at the back
        kit.hexahedron('Compartment', m['sand'], (
            (-0.21, -0.04, z1 - 0.01), (0.21, -0.04, z1 - 0.01), (0.21, 0.42, z1 - 0.01), (-0.21, 0.42, z1 - 0.01),
            (-0.19, 0.0, z1 + 0.06), (0.19, 0.0, z1 + 0.06), (0.19, 0.41, z1 + 0.06), (-0.19, 0.41, z1 + 0.06)), bevel=0.01),
    ])
    return camo(shell, root)


def details(m):
    z0, _ = SPONSON
    z1, w1 = ROOF
    top = z1 + 0.06
    parts = [
        # roof: a house-colour plate on the compartment, two hatches, periscopes, rails
        box('RoofPlate', m['remap'], (0.3, 0.3, 0.008), (0, 0.22, top + 0.002), bevel=0.003),
        *[part for k, (x, y) in enumerate(((-0.09, 0.12), (0.09, 0.3)))
          for part in (cylinder(f'Hatch{k}', m['steel'], 0.05, 0.022, (x, y, top + 0.01), segments=18),
                       cylinder(f'HatchLid{k}', m['sand_light'], 0.042, 0.012, (x, y, top + 0.026), segments=18),
                       box(f'HatchHinge{k}', m['steel_light'], (0.04, 0.012, 0.012), (x, y + 0.05, top + 0.022), bevel=0.002))],
        *[box(f'Periscope{k}', m['glass'], (0.03, 0.016, 0.018), (x, 0.012, top + 0.006), bevel=0.003) for k, x in enumerate((-0.1, 0.0, 0.1))],
        *detail.rail('RoofRailL', m['steel_light'], [(-0.18, 0.06, top), (-0.18, 0.38, top)], 0.02),
        *detail.rail('RoofRailR', m['steel_light'], [(0.18, 0.06, top), (0.18, 0.2, top)], 0.02),
        # front roof: a driver's cupola, a stowage box, an antenna
        cylinder('Cupola', m['steel'], 0.045, 0.03, (-0.12, -0.2, z1 + 0.012), segments=16),
        box('CupolaGlass', m['glass'], (0.05, 0.012, 0.014), (-0.12, -0.24, z1 + 0.02), bevel=0.002),
        box('Stowage', m['olive'], (0.14, 0.08, 0.04), (0.12, -0.18, z1 + 0.02), bevel=0.008),
        *[box(f'StowageStrap{k}', m['dark'], (0.006, 0.084, 0.044), (0.07 + 0.1 * k, -0.18, z1 + 0.02), bevel=0) for k in range(2)],
        beam('Antenna', m['steel'], (0.2, 0.36, top), (0.22, 0.42, top + 0.3), 0.005),
        cylinder('AntennaBase', m['dark'], 0.012, 0.02, (0.2, 0.36, top + 0.008), segments=8, bevel=0),
    ]
    # the glacis: vision blocks, the folded trim vane, headlights
    for k, x in enumerate((-0.16, -0.06, 0.06, 0.16)):
        p, _ = glacis(0.86, 0.004)
        parts.append(box(f'Vision{k}', m['glass'], (0.06, 0.008, 0.022), (x, p.y, p.z), bevel=0.002, rotation=(GLACIS_TILT, 0, 0)))
    p, _ = glacis(0.42, 0.01)
    parts += [box('TrimVane', m['steel'], (0.46, 0.012, 0.11), (0, p.y, p.z), bevel=0.004, rotation=(GLACIS_TILT, 0, 0)),
              *[box(f'TrimVaneRib{k}', m['steel_light'], (0.012, 0.012, 0.1), (x, p.y - 0.008, p.z + 0.006), bevel=0.002, rotation=(GLACIS_TILT, 0, 0))
                for k, x in enumerate((-0.15, 0.0, 0.15))]]
    for s in (-1, 1):
        p, n = glacis(0.12, 0.0)
        parts += [
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.23, p.y - 0.006, p.z + 0.004), (0, -1, 0.3), 0.016),
            box(f'TowHook{s}', m['steel'], (0.03, 0.04, 0.03), (s * 0.12, FRONT[0] + 0.005, 0.15), bevel=0.005),
            # house-colour stripes along the lower edge of the flanks
            box(f'Stripe{s}', m['remap'], (0.008, BACK - FRONT[0] - 0.06, 0.03), (s * (side_x(0.215) + 0.002), (FRONT[0] + BACK) / 2 + 0.02, 0.215),
                bevel=0.002, rotation=(0, -s * SIDE_TILT, 0)),
            # mud flaps behind the wheels
            *[box(f'MudFlap{s}{k}', m['dark'], (0.06, 0.006, 0.06), (s * WHEEL_X, y + WHEEL_RADIUS + 0.02, 0.15), bevel=0.002)
              for k, y in enumerate(AXLES)],
            # the water jets low at the back, tail lights beside the ramp
            cylinder(f'Jet{s}', m['steel'], 0.035, 0.05, (s * 0.24, BACK + 0.01, 0.12), rotation=(math.pi / 2, 0, 0), segments=14),
            cylinder(f'JetMouth{s}', m['dark'], 0.026, 0.052, (s * 0.24, BACK + 0.012, 0.12), rotation=(math.pi / 2, 0, 0), segments=14, bevel=0),
            *detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.235, BACK + 0.004, 0.33), (0, 1, 0), 0.013),
            box(f'RampHinge{s}', m['steel'], (0.05, 0.03, 0.03), (s * 0.13, RAMP_HINGE.y, RAMP_HINGE.z), bevel=0.004),
        ]
        # windows along the flanks
        for k, y in enumerate((-0.12, 0.08, 0.26)):
            z = 0.29
            parts += [box(f'Window{s}{k}', m['glass'], (0.008, 0.06, 0.05), (s * (side_x(z) + 0.002), y, z), bevel=0.003, rotation=(0, -s * SIDE_TILT, 0)),
                      box(f'WindowFrame{s}{k}', m['steel'], (0.006, 0.074, 0.064), (s * side_x(z), y, z), bevel=0.003, rotation=(0, -s * SIDE_TILT, 0))]
        parts += detail.rivets(f'SideRivets{s}', m['steel_light'], (s * (side_x(0.35) + 0.002), -0.25, 0.35), (s * (side_x(0.35) + 0.002), 0.4, 0.35), 10,
                               axis='X')
    # the doorway behind the ramp (shows when it is down)
    parts.append(box('Doorway', m['dark'], (0.32, 0.01, 0.24), (0, BACK + 0.001, 0.22), bevel=0))
    return kit.merge('HullDetails', parts)


def ramp(m, root):
    """The rear ramp, hinged at its bottom edge; returns (shell, fittings) with the
    fittings parented to the shell (origin on the hinge)."""
    h = RAMP_HINGE
    shell = camo(kit.merge('Ramp', [box('RampPlate', m['sand'], (0.34, 0.014, RAMP_HEIGHT), h + Vector((0, 0.002, RAMP_HEIGHT / 2)), bevel=0.004)], h),
                 root)
    parts = [
        box('RampBand', m['remap'], (0.3, 0.004, 0.035), h + Vector((0, 0.011, RAMP_HEIGHT - 0.05)), bevel=0.001),
        cylinder('RampKnuckle', m['steel'], 0.014, 0.18, h, rotation=(0, math.pi / 2, 0), segments=10),
        *[box(f'RampHandle{s}', m['steel_light'], (0.012, 0.012, 0.05), h + Vector((s * 0.1, 0.014, RAMP_HEIGHT - 0.11)), bevel=0.002) for s in (-1, 1)],
        # treads on its inner face (up when it is down)
        *[box(f'RampTread{k}', m['steel'], (0.28, 0.006, 0.01), h + Vector((0, -0.007, 0.03 + k * 0.045)), bevel=0) for k in range(5)],
        *detail.rivets('RampRivets', m['steel_light'], h + Vector((-0.15, 0.011, 0.03)), h + Vector((0.15, 0.011, 0.03)), 7, axis='Y'),
    ]
    kit.parent(kit.merge('RampFittings', parts, h), shell)
    return shell


def build():
    root, body = nod.start('GDIAPC', 'APC', WALK_SPEED)
    m = materials()
    kit.parent(hull(m, root), body)
    kit.parent(details(m), body)
    door = kit.parent(ramp(m, root), body)
    wheels = [kit.parent(nod.wheel(m, f'Wheel{s}{k}', (s * WHEEL_X, y, WHEEL_RADIUS), WHEEL_RADIUS, WHEEL_WIDTH, lugs=14, rim=m['steel_light']), body)
              for s in (-1, 1) for k, y in enumerate(AXLES)]
    kit.bake_camo(512)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.004)
    shut, down = Vector((0, 0, 0)), Vector((RAMP_OPEN, 0, 0))
    kit.keys(door, 'rotation_euler', {0: shut, 9: down, 15: down, UNLOAD_FRAMES: shut})
    kit.to_track(door, 'Unload')
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    door.rotation_euler = shut
    for w in wheels:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Unload': [12]}, scale=1.4, target=(0, 0, 0.2))
