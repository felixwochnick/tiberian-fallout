"""
Tiberian Fallout – GDI mobile EMP (MOBILEMP), after Tiberian Sun Firestorm.

A low, broad tracked carrier: a flat hull between two tracks under wide sloped side
sponsons of ribbed armour plates with small lights along their edges, a driver's
cab with vision blocks in the nose and a power plant with vents and exhausts at the
back. In the middle stands the pulse emitter: a squat generator drum, a mast wound
with copper coils between insulator discs and on top of it the glowing blue-white
emitter sphere in a ring cage. The hull is in the light camouflage of the buildings,
tinted with the house colour in the game (GAPILE.camo_material); bands on the
sponsons, the cab's roof plate and the generator's collar are in the house colour.

Nodes the game uses: "Flash" (the discharge's glare at the emitter, the muzzle of
the pulse). Clips (see nodvehicle.py for Idle and Walk):
    Idle    loop, 2 s: the engine runs, the emitter's halo breathes
    Walk    loop: driving, the tracks' wheels turn, the body rocks; the root's
            walkSpeed (glTF extras) is the ground speed in cells per second
    Fire    once, 1.2 s: the discharge – the coils charge up, the emitter flares and
            a bright blue ring of energy runs out over the ground and fades

Run headless:

    blender -b --factory-startup --python blender/MOBILEMP.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the vehicle.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402
import walker  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'MOBILEMP.glb')
BLEND = os.path.join(HERE, 'MOBILEMP.blend')

TRACK_X = 0.25
TRACK_WIDTH = 0.12
TRACK = (-0.42, 0.42)
TRACK_HEIGHT = 0.12
WHEEL_RADIUS = 0.045
WHEELS_Y = (-0.27, -0.13, 0.01, 0.15, 0.29)
SPROCKET = 0.055
WALK_FRAMES = 28
WALK_SPEED = 2 * math.pi * SPROCKET / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 36
DECK = 0.25                       # the hull's top
EMITTER = Vector((0, 0.06, 0.62))  # the emitter sphere's middle
EMITTER_RADIUS = 0.07
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = nod.materials()
    m.update({
        'copper': material('Copper', srgb('#b0683a'), 0.35, 0.9),
        'insulator': material('Insulator', srgb('#d8d4c8'), 0.3, 0.0),
        'emp': material('EmpCore', srgb('#d8f4ff'), 0.1, emission=srgb('#a8e4ff'), strength=9),
        'emp_glow': material('EmpGlow', (0, 0, 0), 1.0, emission=srgb('#58b8ff'), strength=5, alpha=0.3),
        'emp_ring': material('EmpRing', (0, 0, 0), 1.0, emission=srgb('#7ccaff'), strength=8, alpha=0.6),
        'lamp_blue': material('LampBlue', srgb('#9ad8ff'), 0.2, emission=srgb('#78c8ff'), strength=7),
    })
    return m


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def torus(name, mat, major, minor, location, segments=32, sides=8):
    """A flat ring lying in the ground plane."""
    def make(bm):
        rings = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            ring = []
            for j in range(sides):
                b = 2 * math.pi * j / sides
                r = major + minor * math.cos(b)
                ring.append(bm.verts.new(Vector(location) + Vector((r * math.cos(a), r * math.sin(a), minor * math.sin(b)))))
            rings.append(ring)
        for i in range(segments):
            a, b = rings[i], rings[(i + 1) % segments]
            for j in range(sides):
                bm.faces.new((a[j], b[j], b[(j + 1) % sides], a[(j + 1) % sides]))
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    make(bm)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    kit.collection().objects.link(obj)
    mesh.materials.append(mat)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj


def hull(m, root):
    """The camouflaged hull: the lower body between the tracks, the sloped sponsons
    over them, the cab in the nose and the engine deck at the back."""
    shell = kit.merge('Hull', [
        kit.hexahedron('Lower', m['sand'], (
            (-0.19, -0.4, 0.06), (0.19, -0.4, 0.06), (0.19, 0.42, 0.06), (-0.19, 0.42, 0.06),
            (-0.2, -0.47, 0.17), (0.2, -0.47, 0.17), (0.2, 0.45, 0.17), (-0.2, 0.45, 0.17)), bevel=0.01),
        # the deck with its sloped sponsons out over the tracks
        kit.hexahedron('Deck', m['sand'], (
            (-0.33, -0.44, 0.15), (0.33, -0.44, 0.15), (0.33, 0.44, 0.15), (-0.33, 0.44, 0.15),
            (-0.24, -0.36, DECK), (0.24, -0.36, DECK), (0.24, 0.42, DECK), (-0.24, 0.42, DECK)), bevel=0.012),
        # the cab, front left of the emitter
        kit.hexahedron('Cab', m['sand'], (
            (-0.22, -0.36, DECK - 0.01), (0.04, -0.36, DECK - 0.01), (0.04, -0.14, DECK - 0.01), (-0.22, -0.14, DECK - 0.01),
            (-0.2, -0.3, DECK + 0.08), (0.02, -0.3, DECK + 0.08), (0.02, -0.16, DECK + 0.08), (-0.2, -0.16, DECK + 0.08)), bevel=0.01),
        # the power plant at the back
        kit.hexahedron('Engine', m['sand'], (
            (-0.22, 0.22, DECK - 0.01), (0.22, 0.22, DECK - 0.01), (0.22, 0.42, DECK - 0.01), (-0.22, 0.42, DECK - 0.01),
            (-0.2, 0.25, DECK + 0.06), (0.2, 0.25, DECK + 0.06), (0.2, 0.41, DECK + 0.06), (-0.2, 0.41, DECK + 0.06)), bevel=0.01),
    ])
    return camo(shell, root)


def sponson_z(x):
    """The sloped deck's height at |x| (on the sponsons)."""
    return 0.15 + (DECK - 0.15) * (0.33 - abs(x)) / (0.33 - 0.24)


SPONSON_TILT = math.atan2(DECK - 0.15, 0.33 - 0.24)


def details(m):
    parts = [
        # the cab: vision blocks, a roof plate in the house colour, a hatch
        *[box(f'Vision{k}', m['glass'], (0.05, 0.008, 0.022), (x, -0.335, DECK + 0.05), bevel=0.002, rotation=(math.radians(-24), 0, 0))
          for k, x in enumerate((-0.16, -0.09, -0.02))],
        box('CabRoof', m['remap'], (0.2, 0.12, 0.008), (-0.09, -0.23, DECK + 0.083), bevel=0.002),
        cylinder('CabHatch', m['steel'], 0.032, 0.014, (-0.13, -0.21, DECK + 0.09), segments=14),
        *detail.lamp('CabLight', m['dark'], m['lamp_white'], (0.0, -0.33, DECK + 0.06), (0, -1, 0), 0.012),
        # the nose: a glacis plate, tow hooks, headlights
        box('Glacis', m['steel'], (0.36, 0.012, 0.06), (0, -0.462, 0.13), bevel=0.003, rotation=(math.radians(-30), 0, 0)),
        *[box(f'TowHook{s}', m['steel_light'], (0.03, 0.03, 0.03), (s * 0.14, -0.475, 0.09), bevel=0.004) for s in (-1, 1)],
        *[p for s in (-1, 1) for p in detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.15, -0.46, 0.16), (0, -1, 0.2), 0.014)],
        # the engine deck: vents, exhausts, an antenna, tail lights
        *detail.grille('EngineVent', m['steel'], m['dark'], (-0.08, 0.33, DECK + 0.062), 0.14, 0.1, 'Z', 5, 0.008),
        *detail.grille('EngineVent2', m['steel'], m['dark'], (0.1, 0.33, DECK + 0.062), 0.12, 0.1, 'Z', 4, 0.008),
        *[cylinder(f'Exhaust{s}', m['steel_light'], 0.016, 0.1, (s * 0.17, 0.42, DECK + 0.08), segments=10) for s in (-1, 1)],
        *[cylinder(f'ExhaustTip{s}', m['dark'], 0.014, 0.01, (s * 0.17, 0.42, DECK + 0.13), segments=10, bevel=0) for s in (-1, 1)],
        beam('Antenna', m['steel'], (0.18, 0.38, DECK + 0.06), (0.2, 0.43, DECK + 0.38), 0.005),
        box('BackPlate', m['steel'], (0.36, 0.01, 0.08), (0, 0.452, 0.12), bevel=0.003),
        *[p for s in (-1, 1) for p in detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.15, 0.458, 0.13), (0, 1, 0), 0.011)],
    ]
    # the sponsons: ribbed plates with house-colour bands and small blue lights along their edges
    for s in (-1, 1):
        x = s * 0.3
        z = sponson_z(x)
        for k in range(6):
            y = -0.36 + k * 0.14
            parts.append(box(f'Rib{s}{k}', m['steel'], (0.075, 0.016, 0.012), (s * 0.285, y, sponson_z(0.285) + 0.006), bevel=0.003,
                             rotation=(0, s * SPONSON_TILT, 0)))
        parts.append(box(f'Band{s}', m['remap'], (0.03, 0.74, 0.006), (s * 0.265, 0.0, sponson_z(0.265) + 0.004), bevel=0.002,
                         rotation=(0, s * SPONSON_TILT, 0)))
        parts.append(box(f'Skirt{s}', m['steel'], (0.012, 0.86, 0.05), (s * 0.336, 0.0, 0.14), bevel=0.003))
        for k, y in enumerate((-0.33, -0.12, 0.09, 0.3)):
            parts += detail.lamp(f'EdgeLight{s}{k}', m['dark'], m['lamp_blue'], (s * 0.342, y, 0.145), (s, 0, 0), 0.009)
    return kit.merge('HullDetails', parts)


def emitter(m):
    """The generator drum, the coil mast, the insulators and the cage round the
    sphere (fixed parts); the sphere and its halo are separate."""
    base = DECK
    parts = [
        cylinder('Generator', m['steel'], 0.13, 0.08, (0, EMITTER.y, base + 0.04), segments=24),
        cylinder('GeneratorCollar', m['remap'], 0.134, 0.022, (0, EMITTER.y, base + 0.06), segments=24, bevel=0.002),
        cylinder('GeneratorTop', m['steel_light'], 0.11, 0.02, (0, EMITTER.y, base + 0.09), segments=24),
        *[box(f'GeneratorFin{k}', m['steel'], (0.012, 0.05, 0.06), (0.13 * math.cos(a), EMITTER.y + 0.13 * math.sin(a), base + 0.04), bevel=0.002,
              rotation=(0, 0, a)) for k, a in enumerate(2 * math.pi * (k + 0.5) / 8 for k in range(8))],
        cylinder('Mast', m['steel'], 0.03, EMITTER.z - base - 0.1, (0, EMITTER.y, (base + EMITTER.z) / 2), segments=12),
        # coils between insulator discs
        *[cylinder(f'Coil{k}', m['copper'], 0.05, 0.05, (0, EMITTER.y, base + 0.14 + 0.075 * k), segments=16, bevel=0.01) for k in range(3)],
        *[cylinder(f'Insulator{k}', m['insulator'], 0.065, 0.014, (0, EMITTER.y, base + 0.1025 + 0.075 * k), segments=16, bevel=0.004)
          for k in range(4)],
        # the cage: four bows round the sphere, on a ring
        cylinder('CageRing', m['steel_light'], 0.085, 0.012, (0, EMITTER.y, EMITTER.z - EMITTER_RADIUS - 0.004), segments=20, bevel=0.003),
    ]
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        d = Vector((math.cos(a), math.sin(a), 0))
        lo = EMITTER + d * 0.085 + Vector((0, 0, -EMITTER_RADIUS))
        mid = EMITTER + d * 0.095
        hi = EMITTER + d * 0.05 + Vector((0, 0, EMITTER_RADIUS + 0.02))
        parts += [beam(f'Cage{k}a', m['steel_light'], lo, mid, 0.01), beam(f'Cage{k}b', m['steel_light'], mid, hi, 0.01)]
    parts.append(sphere('CageTop', m['steel'], 0.02, EMITTER + Vector((0, 0, EMITTER_RADIUS + 0.025)), 8))
    return kit.merge('Emitter', parts)


def build():
    root, body = nod.start('GDIMobileEMP', 'MobileEMP', WALK_SPEED)
    m = materials()
    kit.parent(hull(m, root), body)
    kit.parent(details(m), body)
    kit.parent(emitter(m), body)
    core = kit.parent(kit.merge('EmitterCore', [sphere('EmitterCore', m['emp'], EMITTER_RADIUS, EMITTER, 16)], EMITTER), body)
    halo = kit.parent(kit.merge('Halo', [sphere('Halo', m['emp_glow'], EMITTER_RADIUS * 1.6, EMITTER, 14)], EMITTER), body)
    flash = kit.parent(kit.merge('Flash', [sphere('Flash', m['emp_glow'], EMITTER_RADIUS * 2.2, EMITTER, 14),
                                           sphere('FlashCore', m['emp'], EMITTER_RADIUS * 1.25, EMITTER, 12)], EMITTER), body)
    ground = Vector((0, EMITTER.y, 0.03))
    ring = kit.parent(kit.merge('Pulse', [torus('Pulse', m['emp_ring'], 0.25, 0.025, ground)], ground), root)
    wheels, sprockets = [], []
    for s in (-1, 1):
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], TRACK_HEIGHT, 20), body)
        x = s * (TRACK_X + TRACK_WIDTH / 2 + 0.004)
        wheels += [kit.parent(nod.road_wheel(m, f'Wheel{s}{k}', (x, y, WHEEL_RADIUS + 0.004), WHEEL_RADIUS, 0.02), body)
                   for k, y in enumerate(WHEELS_Y)]
        sprockets += [kit.parent(nod.road_wheel(m, f'Sprocket{s}{k}', (x, y, SPROCKET + 0.004), SPROCKET, 0.02), body)
                      for k, y in enumerate((TRACK[0] + 0.06, TRACK[1] - 0.06))]
    kit.bake_camo(512)
    nod.drive(body, wheels, WALK_FRAMES, extra=[(sprockets, WHEEL_RADIUS / SPROCKET)], rock=0.003)

    one, hidden = Vector((1, 1, 1)), Vector((kit.HIDDEN,) * 3)
    # Idle: the halo breathes
    kit.keys(halo, 'scale', {f: one * (1 + 0.12 * math.sin(2 * math.pi * f / kit.IDLE_END)) for f in range(0, kit.IDLE_END + 1, 5)}, 'LINEAR')
    kit.to_track(halo, 'Idle')
    walker.hide([flash, ring], kit.IDLE_END, 'Idle')
    walker.hide([flash, ring], WALK_FRAMES, 'Walk')
    # Fire: charge up (the core and halo swell), the flash, the ring runs out and fades
    kit.keys(core, 'scale', {0: one, 8: one * 1.25, 10: one * 1.4, 14: one * 0.85, 24: one, FIRE_FRAMES: one})
    kit.to_track(core, 'Fire')
    kit.keys(halo, 'scale', {0: one, 8: one * 1.5, 10: one * 1.9, 14: one * 0.6, 26: one, FIRE_FRAMES: one})
    kit.to_track(halo, 'Fire')
    kit.keys(flash, 'scale', {0: hidden, 9: hidden, 10: one * 0.8, 12: one * 1.6, 16: one * 1.2, 20: hidden, FIRE_FRAMES: hidden}, 'LINEAR')
    kit.to_track(flash, 'Fire')
    kit.keys(ring, 'scale', {0: hidden, 9: hidden, 10: Vector((0.6, 0.6, 1)), 22: Vector((4.2, 4.2, 0.8)), 30: Vector((6.0, 6.0, 0.4)),
                             31: hidden, FIRE_FRAMES: hidden}, 'LINEAR')
    kit.to_track(ring, 'Fire')
    flash.scale = ring.scale = hidden
    core.scale = halo.scale = one
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels + sprockets:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Fire': [11, 22]}, scale=1.6, target=(0, 0, 0.25))
