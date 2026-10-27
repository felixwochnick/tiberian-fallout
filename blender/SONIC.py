"""
Tiberian Fallout – GDI Disruptor (SONIC), after Tiberian Sun.

A broad, heavy tracked tank: a low hull between two massive track guards whose fronts
step down in layered armour plates, a sloped glacis with headlights and tow hooks, an
engine deck with grilles and exhausts at the back. On a flat turret behind the middle
sits the sonic emitter: a wide horn flaring forward, ringed with cooling bands, its
mouth glowing pale blue, under a curved grey reflector hood that arches over it (the
pale fin of the original's icon); capacitor drums on both sides of the turret feed
it. The hull and turret are in the light camouflage of the buildings, tinted with the
house colour in the game (GAPILE.camo_material); stripes on the guards, the turret's
cheeks and a band round the horn are in the house colour.

Nodes the game uses: "Turret" (turns about its vertical towards the target), "Cannon"
(the emitter, tipped up and down), "Flash" (the muzzle at the horn's mouth). Clips
(see nodvehicle.py for Idle and Walk):
    Idle   loop, 2 s: the engine runs, the hull shivers, the horn's core pulses softly
    Walk   loop: driving, the wheels and sprockets turn, the hull rocks; the root's
           walkSpeed (glTF extras) is the ground speed in cells per second
    Fire   once, 1 s: the core flares, three sound rings run out of the horn and
           widen, the horn shudders back

Run headless:

    blender -b --factory-startup --python blender/SONIC.py [-- --preview <dir>]

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
import walker  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'SONIC.glb')
BLEND = os.path.join(HERE, 'SONIC.blend')

TRACK_X = 0.255
TRACK_WIDTH = 0.12
TRACK = (-0.45, 0.42)
TRACK_HEIGHT = 0.12
WHEEL_RADIUS = 0.042
WHEELS_Y = (-0.28, -0.14, 0.0, 0.14, 0.28)
SPROCKET = 0.063                  # 2/3 of a turn per loop (3 bolts: seamless)
WALK_FRAMES = 30
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 30
DECK = 0.25                        # the hull's top
TURRET = Vector((0, 0.1, DECK))    # the turret's base (it turns about z here)
EMITTER = Vector((0, 0.02, 0.44))  # the horn's trunnion
HORN = (0.07, 0.125, 0.34)         # the horn: rear radius, mouth radius, length
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
ALONG_Y = (math.pi / 2, 0, 0)      # a cylinder's +z turned to -y (its radius2 end in front)


def materials():
    m = nod.materials()
    m.update({
        'glass': material('Windscreen', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#3a6a96'), strength=0.6),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'hood': material('HoodGrey', srgb('#b9bcbc'), 0.35, 0.75),
        'core': material('SonicCore', srgb('#bfefff'), 0.2, emission=srgb('#7fd8ff'), strength=5),
        'wave': material('SonicWave', (0, 0, 0), 1.0, emission=srgb('#a8e6ff'), strength=5, alpha=0.45),
    })
    return m


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def shell(name, mat, radius, thickness, y0, y1, centre, arc=math.pi, segments=12):
    """A curved plate: part of a tube about the y axis from y0 to y1 (arching over the
    top, `arc` wide), `thickness` thick; centre = the tube's axis (x, z)."""
    cx, cz = centre

    def build(bm):
        rings = []
        for k in range(segments + 1):
            a = math.pi / 2 - arc / 2 + arc * k / segments
            rings.append([bm.verts.new((cx + r * math.cos(a), y, cz + r * math.sin(a)))
                          for r in (radius, radius + thickness) for y in (y0, y1)])
        for a, b in zip(rings, rings[1:]):
            for i, j, p, q in ((0, 1, 1, 0), (2, 3, 3, 2), (0, 2, 2, 0), (1, 3, 3, 1)):
                bm.faces.new((a[i], a[j], b[p], b[q]))
        for ring in (rings[0], rings[-1]):
            bm.faces.new((ring[0], ring[1], ring[3], ring[2]))

    return kit.finish(kit.mesh_object(name, build), mat, 0.004)


# --------------------------------------------------------------------------- hull

def hull(m, root):
    """The camouflaged hull and guards (one mesh)."""
    parts = [
        kit.hexahedron('Hull', m['sand'], (
            (-0.19, -0.42, 0.07), (0.19, -0.42, 0.07), (0.19, 0.44, 0.07), (-0.19, 0.44, 0.07),
            (-0.18, -0.26, DECK), (0.18, -0.26, DECK), (0.18, 0.43, DECK), (-0.18, 0.43, DECK)), bevel=0.012),
        # the engine deck, a step lower at the back
        kit.hexahedron('EngineDeck', m['sand'], (
            (-0.17, 0.3, DECK - 0.01), (0.17, 0.3, DECK - 0.01), (0.17, 0.45, DECK - 0.01), (-0.17, 0.45, DECK - 0.01),
            (-0.16, 0.31, DECK + 0.02), (0.16, 0.31, DECK + 0.02), (0.16, 0.44, DECK + 0.01), (-0.16, 0.44, DECK + 0.01)), bevel=0.008),
    ]
    for s in (-1, 1):
        x0, x1 = s * 0.18, s * 0.33
        parts += [
            # the guard over the track, its front stepping down
            kit.hexahedron(f'Guard{s}', m['sand'], (
                (x0, -0.4, 0.13), (x1, -0.4, 0.13), (x1, 0.45, 0.13), (x0, 0.45, 0.13),
                (x0, -0.36, DECK + 0.02), (x1 - s * 0.015, -0.36, DECK), (x1 - s * 0.015, 0.44, DECK), (x0, 0.44, DECK + 0.02)), bevel=0.012),
            # the layered plates on its nose
            kit.hexahedron(f'NosePlate{s}', m['sand'], (
                (x0 + s * 0.005, -0.5, 0.1), (x1 - s * 0.005, -0.5, 0.1), (x1 - s * 0.005, -0.38, 0.1), (x0 + s * 0.005, -0.38, 0.1),
                (x0 + s * 0.005, -0.44, 0.19), (x1 - s * 0.01, -0.44, 0.18), (x1 - s * 0.01, -0.36, 0.18), (x0 + s * 0.005, -0.36, 0.19)),
                bevel=0.01),
            kit.hexahedron(f'NoseStep{s}', m['sand'], (
                (x0 + s * 0.01, -0.42, 0.18), (x1 - s * 0.015, -0.42, 0.17), (x1 - s * 0.015, -0.3, 0.17), (x0 + s * 0.01, -0.3, 0.18),
                (x0 + s * 0.01, -0.38, DECK + 0.03), (x1 - s * 0.02, -0.38, DECK + 0.01), (x1 - s * 0.02, -0.3, DECK + 0.01),
                (x0 + s * 0.01, -0.3, DECK + 0.03)), bevel=0.01),
        ]
    return camo(kit.merge('HullShell', parts), root)


def hull_details(m):
    parts = [
        # the glacis: a driver's hatch with vision blocks, headlights, tow hooks
        box('DriverHatch', m['sand_light'], (0.1, 0.08, 0.014), (-0.08, -0.2, DECK + 0.005), bevel=0.004),
        *[box(f'Vision{k}', m['glass'], (0.03, 0.01, 0.016), (-0.11 + 0.03 * k, -0.245, DECK - 0.002), bevel=0.002) for k in range(3)],
        box('Hatch2', m['sand_light'], (0.07, 0.07, 0.012), (0.09, -0.19, DECK + 0.004), bevel=0.004),
        *detail.grille('DeckVent', m['steel'], m['dark'], (0, 0.38, DECK + 0.022), 0.22, 0.09, 'Z', 7, 0.008),
        box('BackPlate', m['sand_light'], (0.34, 0.012, 0.15), (0, 0.447, 0.15), bevel=0.004),
        beam('Antenna', m['steel'], (0.14, 0.4, DECK + 0.02), (0.16, 0.45, DECK + 0.4), 0.006),
        cylinder('AntennaBase', m['dark'], 0.014, 0.02, (0.14, 0.4, DECK + 0.03), segments=8, bevel=0),
        box('Stowage', m['olive'], (0.12, 0.05, 0.04), (-0.1, 0.4, DECK + 0.04), bevel=0.008),
    ]
    for s in (-1, 1):
        parts += [
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.12, -0.36, 0.17), (0, -1, 0.5), 0.016),
            box(f'TowHook{s}', m['steel'], (0.03, 0.04, 0.03), (s * 0.08, -0.425, 0.1), bevel=0.005),
            # house-colour stripes along the guards, rivets, a side vent
            kit.hexahedron(f'GuardStripe{s}', m['remap'], (
                (s * 0.205, -0.3, DECK + 0.016), (s * 0.3, -0.3, DECK - 0.002), (s * 0.3, 0.4, DECK - 0.002), (s * 0.205, 0.4, DECK + 0.016),
                (s * 0.205, -0.3, DECK + 0.024), (s * 0.3, -0.3, DECK + 0.006), (s * 0.3, 0.4, DECK + 0.006), (s * 0.205, 0.4, DECK + 0.024)),
                bevel=0.002),
            box(f'NoseBand{s}', m['remap'], (0.12, 0.01, 0.03), (s * 0.255, -0.47, 0.13), bevel=0.002, rotation=(math.radians(-36), 0, 0)),
            *detail.rivets(f'GuardRivets{s}', m['steel_light'], (s * 0.333, -0.32, 0.17), (s * 0.333, 0.4, 0.17), 9, axis='X'),
            *detail.grille(f'GuardVent{s}', m['steel'], m['dark'], (s * 0.26, 0.2, DECK + 0.006), 0.08, 0.08, 'Z', 4, 0.006),
            *detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.24, 0.455, 0.2), (0, 1, 0), 0.012),
            # two exhausts on the back
            cylinder(f'Exhaust{s}', m['steel'], 0.02, 0.1, (s * 0.07, 0.46, 0.2), segments=10),
            cylinder(f'ExhaustTip{s}', m['dark'], 0.016, 0.012, (s * 0.07, 0.46, 0.25), segments=10, bevel=0),
        ]
    return kit.merge('HullDetails', parts)


# --------------------------------------------------------------------------- turret

def turret(m, root, body):
    """The turret on its ring (node Turret) with the emitter on the Cannon; returns
    (turret, horn, core, flash, waves)."""
    turn = kit.parent(kit.empty('Turret', TURRET), body)
    z0, z1 = DECK, 0.37
    camo_part = camo(kit.merge('TurretShell', [kit.hexahedron('TurretShell', m['sand'], (
        (-0.17, -0.12, z0 + 0.012), (0.17, -0.12, z0 + 0.012), (0.17, 0.3, z0 + 0.012), (-0.17, 0.3, z0 + 0.012),
        (-0.14, -0.06, z1), (0.14, -0.06, z1), (0.14, 0.27, z1), (-0.14, 0.27, z1)), bevel=0.014)], TURRET), root)
    kit.parent(camo_part, turn)
    parts = [
        cylinder('TurretRing', m['steel'], 0.15, 0.03, (0, TURRET.y, z0 + 0.012), segments=24),
        box('TurretRoof', m['sand_light'], (0.22, 0.2, 0.012), (0, 0.15, z1 + 0.004), bevel=0.004),
        cylinder('Cupola', m['steel'], 0.04, 0.03, (0.08, 0.19, z1 + 0.018), segments=16),
        box('CupolaGlass', m['glass'], (0.045, 0.012, 0.012), (0.08, 0.152, z1 + 0.02), bevel=0.002),
        *detail.grille('TurretVent', m['steel'], m['dark'], (-0.06, 0.22, z1 + 0.01), 0.1, 0.06, 'Z', 4, 0.006),
        # the horn's cradle: two cheeks with the trunnion between
        *[kit.hexahedron(f'Cheek{s}', m['sand_light'], (
            (s * 0.09, -0.06, z1 - 0.005), (s * 0.13, -0.06, z1 - 0.005), (s * 0.13, 0.12, z1 - 0.005), (s * 0.09, 0.12, z1 - 0.005),
            (s * 0.09, -0.02, EMITTER.z + 0.04), (s * 0.12, -0.02, EMITTER.z + 0.04), (s * 0.12, 0.08, EMITTER.z + 0.04),
            (s * 0.09, 0.08, EMITTER.z + 0.04)), bevel=0.008) for s in (-1, 1)],
        *[box(f'CheekBand{s}', m['remap'], (0.008, 0.12, 0.03), (s * 0.132, 0.03, z1 + 0.02), bevel=0.002) for s in (-1, 1)],
        cylinder('Trunnion', m['steel_light'], 0.022, 0.27, EMITTER, rotation=(0, math.pi / 2, 0), segments=12),
        *detail.lamp('TurretLight', m['dark'], m['lamp_red'], (-0.13, 0.27, z1 - 0.01), (0, 1, 0), 0.01),
    ]
    for s in (-1, 1):
        # capacitor drums on the turret's flanks, cabled to the trunnion
        c = Vector((s * 0.185, 0.12, 0.31))
        parts += [
            cylinder(f'Capacitor{s}', m['steel'], 0.04, 0.2, c, rotation=ALONG_Y, segments=14),
            *[cylinder(f'CapacitorRing{s}{k}', m['steel_light'], 0.043, 0.012, c + Vector((0, -0.07 + 0.07 * k, 0)), rotation=ALONG_Y,
                       segments=14, bevel=0) for k in range(3)],
            cylinder(f'CapacitorCap{s}', m['remap'], 0.03, 0.01, c + Vector((0, -0.102, 0)), rotation=ALONG_Y, segments=14, bevel=0),
            *detail.hose(f'Cable{s}', m['dark'], c + Vector((-s * 0.02, -0.08, 0.03)), c + Vector((-s * 0.02, -0.14, 0.12)),
                         EMITTER + Vector((s * 0.12, 0.0, 0.0)), 0.008),
        ]
    kit.parent(kit.merge('TurretDetails', parts, TURRET), turn)

    pivot = kit.parent(kit.empty('Cannon', EMITTER), turn)
    r0, r1, length = HORN
    mouth = EMITTER - Vector((0, length, 0))
    horn_parts = [
        # the housing behind the trunnion, the flaring horn, its rings and the band
        cylinder('Housing', m['steel'], r0, 0.14, EMITTER + Vector((0, 0.03, 0)), rotation=ALONG_Y, segments=20),
        cylinder('HousingCap', m['steel_light'], r0 - 0.015, 0.02, EMITTER + Vector((0, 0.1, 0)), rotation=ALONG_Y, segments=20),
        cylinder('Horn', m['hood'], r0, length - 0.04, EMITTER - Vector((0, (length - 0.04) / 2 + 0.04, 0)), rotation=ALONG_Y,
                 segments=24, radius2=r1),
        cylinder('Lip', m['steel'], r1 + 0.008, 0.02, mouth + Vector((0, 0.01, 0)), rotation=ALONG_Y, segments=24),
        cylinder('HornBand', m['remap'], r0 + 0.02, 0.025, EMITTER - Vector((0, 0.09, 0)), rotation=ALONG_Y, segments=24, bevel=0),
    ]
    for k in range(3):
        t = 0.38 + 0.2 * k
        r = r0 + (r1 - r0) * (t * length - 0.04) / (length - 0.04)
        horn_parts.append(cylinder(f'HornRib{k}', m['steel'], r + 0.008, 0.012, EMITTER - Vector((0, t * length, 0)), rotation=ALONG_Y,
                                   segments=24, bevel=0))
    # the reflector hood arching over the horn, on two struts
    horn_parts += [
        shell('Hood', m['hood'], r1 + 0.03, 0.012, mouth.y + 0.02, EMITTER.y + 0.02, (0, EMITTER.z + 0.01), math.radians(150), 14),
        *[beam(f'HoodStrut{s}', m['steel'], EMITTER + Vector((s * 0.05, 0.0, r0 - 0.005)),
               EMITTER + Vector((s * 0.07, -0.04, r1 + 0.03)), 0.014) for s in (-1, 1)],
        box('HoodSpine', m['remap'], (0.024, length - 0.02, 0.008), EMITTER + Vector((0, -length / 2 + 0.03, r1 + 0.048)), bevel=0.002),
        # emitter plates inside the mouth
        *[box(f'Vane{k}', m['steel_light'], (0.006, 0.012, 2 * r1 - 0.06 - 0.04 * abs(k - 1)), mouth - Vector((-0.05 + 0.05 * k, 0.008, 0)), bevel=0)
          for k in range(3)],
    ]
    horn = kit.parent(kit.merge('Emitter', horn_parts, EMITTER), pivot)
    core = kit.parent(kit.merge('Core', [cylinder('Core', m['core'], r1 - 0.016, 0.006, mouth - Vector((0, 0.002, 0)), rotation=ALONG_Y,
                                                  segments=24, bevel=0)], mouth), horn)
    flash = kit.parent(kit.merge('Flash', [sphere('FlashBall', m['wave'], 0.07, mouth - Vector((0, 0.04, 0)), 12)],
                                 mouth - Vector((0, 0.03, 0))), pivot)
    waves = []
    for k in range(3):
        ring = []
        for j in range(16):  # a ring of short glowing segments
            a0, a1 = 2 * math.pi * j / 16, 2 * math.pi * (j + 1) / 16
            p0 = mouth + Vector((r1 * math.cos(a0), 0, r1 * math.sin(a0)))
            p1 = mouth + Vector((r1 * math.cos(a1), 0, r1 * math.sin(a1)))
            ring.append(beam(f'Wave{k}_{j}', m['wave'], p0, p1, 0.02, 0.014))
        waves.append(kit.parent(kit.merge(f'Wave{k}', ring, mouth), pivot))
    return turn, horn, core, flash, waves


# --------------------------------------------------------------------------- clips

def clips(horn, core, flash, waves):
    """Idle: the core pulses; Fire: core flare, rings out, horn kick."""
    one, hidden = Vector((1, 1, 1)), Vector((kit.HIDDEN,) * 3)
    kit.keys(core, 'scale', {f: Vector((1, 1, 1)) * (0.85 + 0.15 * math.sin(2 * math.pi * f / kit.IDLE_END * 2) ** 2)
                             for f in range(0, kit.IDLE_END + 1, 5)}, 'LINEAR')
    kit.to_track(core, 'Idle')
    kit.keys(core, 'scale', {0: one, 2: Vector((1.15, 1, 1.15)), 8: one, FIRE_FRAMES: one})
    kit.to_track(core, 'Fire')
    walker.hold(core, 'scale', one, WALK_FRAMES, 'Walk')
    # the flash: a glowing ball at the mouth for a few frames
    kit.keys(flash, 'scale', {0: Vector((1, 0.6, 1)), 2: Vector((1.5, 1.2, 1.5)), 5: Vector((1.2, 1, 1.2)), 7: hidden,
                              FIRE_FRAMES: hidden}, 'CONSTANT')
    kit.to_track(flash, 'Fire')
    walker.hide([flash], kit.IDLE_END, 'Idle')
    walker.hide([flash], WALK_FRAMES, 'Walk')
    # the rings run out of the mouth one after another and widen
    for k, ring in enumerate(waves):
        rest = ring.location.copy()
        start = 1 + 4 * k
        kit.keys(ring, 'location', {0: rest, start: rest, start + 14: rest - Vector((0, 0.9, 0)), FIRE_FRAMES: rest - Vector((0, 0.9, 0))},
                 'LINEAR')
        kit.keys(ring, 'scale', {0: hidden, start - 1 if start else 0: hidden, start: Vector((0.9, 1, 0.9)),
                                 start + 13: Vector((2.6, 1, 2.6)), start + 14: hidden, FIRE_FRAMES: hidden}, 'LINEAR')
        kit.to_track(ring, 'Fire')
        walker.hide([ring], kit.IDLE_END, 'Idle')
        walker.hide([ring], WALK_FRAMES, 'Walk')
        walker.hold(ring, 'location', rest, kit.IDLE_END, 'Idle')
        walker.hold(ring, 'location', rest, WALK_FRAMES, 'Walk')
        ring.location, ring.scale = rest, hidden
    # the horn shudders back on the shot
    rest = horn.location.copy()
    kit.keys(horn, 'location', {0: rest, 2: rest + Vector((0, 0.035, 0)), 6: rest + Vector((0, 0.03, 0)), 16: rest, FIRE_FRAMES: rest})
    kit.to_track(horn, 'Fire')
    walker.hold(horn, 'location', rest, kit.IDLE_END, 'Idle')
    walker.hold(horn, 'location', rest, WALK_FRAMES, 'Walk')
    horn.location, core.scale, flash.scale = rest, one, hidden


def build():
    root, body = nod.start('GDIDisruptor', 'Disruptor', WALK_SPEED)
    m = materials()
    kit.parent(hull(m, root), body)
    kit.parent(hull_details(m), body)
    _, horn, core, flash, waves = turret(m, root, body)
    wheels, sprockets = [], []
    for s in (-1, 1):
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], TRACK_HEIGHT, 22), body)
        x = s * (TRACK_X + TRACK_WIDTH / 2 + 0.004)
        wheels += [kit.parent(nod.road_wheel(m, f'Wheel{s}{k}', (x, y, WHEEL_RADIUS + 0.004), WHEEL_RADIUS, 0.02), body)
                   for k, y in enumerate(WHEELS_Y)]
        sprockets += [kit.parent(nod.road_wheel(m, f'Sprocket{s}{k}', (x, y, SPROCKET + 0.004), SPROCKET, 0.022), body)
                      for k, y in enumerate((TRACK[0] + 0.06, TRACK[1] - 0.06))]
    kit.bake_camo(512)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.003, extra=((sprockets, WHEEL_RADIUS / SPROCKET),))
    clips(horn, core, flash, waves)
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels + sprockets:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Walk': [6], 'Fire': [3, 9]}, scale=1.5, target=(0, 0, 0.25))
