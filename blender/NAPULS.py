"""
Tiberian Fallout – Nod EMP cannon (NAPULS), after Tiberian Sun.

A big tower on 2 × 2 cells: a pyramid of greenish grey concrete braced by four sloped
legs that run out to the corners, on top a red (house colour) drum, and on it the
turning housing with the pulse cannon – a thick barrel wound with copper coils that
opens into a parabolic dish with an emitter spike in its middle. Doors and vents in
the pyramid's faces, a red lamp over the door.

Nodes the game uses (see nodbuilding.py):
    Turret   the housing, turning about the vertical
    Cannon   the pulse cannon's trunnion, tipped up and down; the dish looks along -Y
    Flash    the discharge in front of the dish
Animations (glTF clips)
    Build    one-shot, 2.6 s: the pyramid rises, its legs come up, the drum, the
             housing rises onto it and the cannon pushes out
    Idle     loop, 2 s: the emitter glows softly, the lamps blink
    Fire     one-shot, 1 s: the emitter charges up (a growing blue glow), then the
             discharge flashes out of the dish, the cannon kicks back

Run headless:

    blender -b --factory-startup --python blender/NAPULS.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells of the
foundation are centred at (±0.5, ±0.5); origin in the middle on the ground.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodbuilding as nb  # noqa: E402

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
HIDDEN = kit.HIDDEN

TOP = 0.5                       # the pyramid's top
DRUM = 0.12
HOUSING = Vector((0, 0, TOP + DRUM))
GUN = Vector((0, 0.0, TOP + DRUM + 0.2))
FIRE_FRAMES = 30
BUILD_END = 78


def pyramid(m, root):
    """The concrete pyramid and its legs (baked), the details; returns both."""
    body = kit.hexahedron('PyramidBody', m['steel'], (
        (-0.62, -0.62, 0), (0.62, -0.62, 0), (0.62, 0.62, 0), (-0.62, 0.62, 0),
        (-0.3, -0.3, TOP), (0.3, -0.3, TOP), (0.3, 0.3, TOP), (-0.3, 0.3, TOP)), bevel=0.02)
    legs = []
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        d = Vector((math.cos(a), math.sin(a), 0))
        n = Vector((-d.y, d.x, 0))
        foot, head = d * 1.28, d * 0.36
        legs.append(kit.hexahedron(f'Leg{k}', m['steel'], (
            foot - n * 0.13, foot + n * 0.13, d * 0.5 + n * 0.3, d * 0.5 - n * 0.3,
            foot * 0.98 - n * 0.1 + Vector((0, 0, 0.1)), foot * 0.98 + n * 0.1 + Vector((0, 0, 0.1)),
            head + n * 0.08 + Vector((0, 0, TOP - 0.02)), head - n * 0.08 + Vector((0, 0, TOP - 0.02))), bevel=0.02))
    shell = nb.concrete('Pyramid', [body, *legs], root, 'olive')

    parts = []
    slope = math.atan2(TOP, 0.32)
    for k in range(4):
        a = k * math.pi / 2
        turn = kit.Matrix.Rotation(a, 4, 'Z')
        normal = Vector((0, -math.sin(slope), math.cos(slope)))

        def on_face(name, mat, size, t, x=0.0, lift=0.006):
            """A plate on the face's slope at height fraction t."""
            at = Vector((x, -0.62 + 0.32 * t, TOP * t)) + normal * lift
            obj = box(name, mat, size, (0, 0, 0), bevel=0.004)
            obj.matrix_world = turn @ kit.Matrix.Translation(at) @ kit.Matrix.Rotation(slope, 4, 'X')
            return obj
        parts.append(on_face(f'Band{k}', m['remap'], (0.9 - 0.5 * 0.82, 0.05, 0.012), 0.82))
        if k == 0:     # the door at the front and its lamp
            parts += [on_face('Door', m['armour_dark'], (0.22, 0.22, 0.02), 0.25),
                      on_face('DoorFrame', m['steel'], (0.26, 0.03, 0.024), 0.43),
                      on_face('DoorStep', m['steel'], (0.3, 0.06, 0.02), 0.06)]
        else:
            parts += [on_face(f'Vent{k}', m['dark'], (0.26, 0.1, 0.02), 0.35),
                      *[on_face(f'VentSlat{k}{j}', m['steel'], (0.27, 0.012, 0.024), 0.31 + 0.04 * j) for j in range(3)]]
    for k in range(4):   # bolts on the legs' feet
        a = math.pi / 4 + k * math.pi / 2
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(box(f'LegFoot{k}', m['armour_dark'], (0.18, 0.18, 0.05), d * 1.2 + Vector((0, 0, 0.025)), bevel=0.01, rotation=(0, 0, a)))
    parts += [
        cylinder('Collar', m['steel'], 0.36, 0.03, (0, 0, TOP + 0.015), segments=28),
        cylinder('Drum', m['remap'], 0.3, DRUM - 0.03, (0, 0, TOP + 0.03 + (DRUM - 0.03) / 2), segments=28, bevel=0.01),
        *[box(f'DrumRib{k}', m['armour_dark'], (0.03, 0.03, DRUM - 0.03), (0.3 * math.cos(k * math.pi / 6), 0.3 * math.sin(k * math.pi / 6), TOP + 0.03 + (DRUM - 0.03) / 2),
              bevel=0.004, rotation=(0, 0, k * math.pi / 6)) for k in range(12)],
    ]
    lamps = []
    for k, (x, y, z) in enumerate(((0.0, -0.45, 0.27), (0.85, 0.85, 0.05), (-0.85, -0.85, 0.05))):
        housing, light = nb.lamp(f'Lamp{k}', m, (x, y, z))
        lamps.append((housing, light))
    return shell, kit.merge('PyramidDetails', parts), lamps


def cannon(m, mount):
    """Housing (Turret) and pulse cannon (Cannon); returns (barrel, flash, charge, glow)."""
    turret = kit.parent(kit.empty('Turret', HOUSING), mount)
    housing = [
        kit.hexahedron('Housing', m['armour'], (
            (-0.26, -0.24, HOUSING.z), (0.26, -0.24, HOUSING.z), (0.28, 0.3, HOUSING.z), (-0.28, 0.3, HOUSING.z),
            (-0.2, -0.16, HOUSING.z + 0.2), (0.2, -0.16, HOUSING.z + 0.2), (0.22, 0.26, HOUSING.z + 0.2), (-0.22, 0.26, HOUSING.z + 0.2)), bevel=0.02),
        *[kit.hexahedron(f'Cheek{s}', m['remap'], (
            (s * 0.265, -0.2, HOUSING.z + 0.02), (s * 0.285, -0.2, HOUSING.z + 0.02), (s * 0.29, 0.26, HOUSING.z + 0.02), (s * 0.27, 0.26, HOUSING.z + 0.02),
            (s * 0.215, -0.14, HOUSING.z + 0.17), (s * 0.235, -0.14, HOUSING.z + 0.17), (s * 0.245, 0.22, HOUSING.z + 0.17), (s * 0.225, 0.22, HOUSING.z + 0.17)), bevel=0.004)
          for s in (-1, 1)],
        *[cylinder(f'Capacitor{s}', m['steel_light'], 0.05, 0.3, (s * 0.2, 0.18, HOUSING.z + 0.24), rotation=(math.pi / 2, 0, 0), segments=16)
          for s in (-1, 1)],
        *[cylinder(f'CapCap{s}', m['remap'], 0.053, 0.03, (s * 0.2, 0.34, HOUSING.z + 0.24), rotation=(math.pi / 2, 0, 0), segments=16)
          for s in (-1, 1)],
        *detail.grille('HousingVent', m['steel'], m['dark'], (0, 0.31, HOUSING.z + 0.09), 0.24, 0.1, 'Y', 4),
        *detail.hose('Feed0', m['dark'], (0.2, 0.03, HOUSING.z + 0.24), (0.16, -0.02, HOUSING.z + 0.3), (0.08, -0.08, GUN.z + 0.06), 0.012),
        *detail.hose('Feed1', m['dark'], (-0.2, 0.03, HOUSING.z + 0.24), (-0.16, -0.02, HOUSING.z + 0.3), (-0.08, -0.08, GUN.z + 0.06), 0.012),
        *[box(f'Trunnion{s}', m['armour_dark'], (0.05, 0.14, 0.12), (s * 0.15, GUN.y + 0.02, GUN.z - 0.02), bevel=0.01) for s in (-1, 1)],
    ]
    kit.parent(kit.merge('HousingBody', housing, HOUSING), turret)

    pivot = kit.parent(kit.empty('Cannon', GUN), turret)
    along = (math.pi / 2, 0, 0)
    copper = material('Copper', srgb('#b5703a'), 0.35, 1.0)
    dish_y = GUN.y - 0.42
    parts = [
        cylinder('Core', m['armour_dark'], 0.1, 0.5, GUN + Vector((0, -0.12, 0)), rotation=along, segments=20),
        cylinder('Breech', m['armour'], 0.12, 0.12, GUN + Vector((0, 0.12, 0)), rotation=along, segments=20, bevel=0.01),
        # the parabolic dish: a few cone rings opening forwards
        cylinder('DishBack', m['steel'], 0.1, 0.05, (GUN.x, dish_y + 0.03, GUN.z), rotation=along, radius2=0.16, segments=24, bevel=0.003),
        cylinder('Dish', m['steel_light'], 0.16, 0.06, (GUN.x, dish_y - 0.025, GUN.z), rotation=along, radius2=0.24, segments=28, bevel=0.003),
        cylinder('DishInner', m['dark'], 0.1, 0.07, (GUN.x, dish_y - 0.022, GUN.z), rotation=along, radius2=0.225, segments=28, bevel=0),
        *[beam(f'DishRim{k}', m['remap'],
               (0.243 * math.cos(2 * math.pi * k / 20), dish_y - 0.056, GUN.z + 0.243 * math.sin(2 * math.pi * k / 20)),
               (0.243 * math.cos(2 * math.pi * (k + 1) / 20), dish_y - 0.056, GUN.z + 0.243 * math.sin(2 * math.pi * (k + 1) / 20)), 0.022, 0.016)
          for k in range(20)],
        cylinder('Spike', m['steel'], 0.022, 0.16, (GUN.x, dish_y - 0.06, GUN.z), rotation=along, radius2=0.008, segments=12),
        sphere('Emitter', m['lamp_pulse'], 0.03, (GUN.x, dish_y - 0.13, GUN.z), 12),
    ]
    for k in range(4):   # dish struts holding the spike
        a = math.pi / 4 + k * math.pi / 2
        parts.append(beam(f'Strut{k}', m['steel'], (0.2 * math.cos(a), dish_y - 0.04, GUN.z + 0.2 * math.sin(a)), (0, dish_y - 0.11, GUN.z), 0.01))
    for k in range(6):   # copper coils round the core
        parts.append(cylinder(f'Coil{k}', copper, 0.125, 0.03, GUN + Vector((0, -0.04 - k * 0.05, 0)), rotation=along, segments=20, bevel=0.006))
    barrel = kit.parent(kit.merge('PulseCannon', parts, GUN), pivot)
    emitter = Vector((GUN.x, dish_y - 0.13, GUN.z))
    glow = kit.parent(nb.glow(m, 'EmitterGlow', emitter, 0.05, 'glow_pulse', 1), barrel)
    charge = kit.parent(nb.glow(m, 'Charge', emitter + Vector((0, 0.06, 0)), 0.17, 'glow_pulse', 1), barrel)
    flash = kit.parent(nb.glow(m, 'Flash', emitter - Vector((0, 0.08, 0)), 0.14, 'glow_pulse', 4), pivot)
    return barrel, flash, charge, glow


def build():
    root = nb.start('NodEMP', 'NodEMPCannon', BUILD_END + 10)
    m = nb.materials()
    shell, details, lamps = pyramid(m, root)
    kit.parent(shell, root)
    kit.parent(details, root)
    lights = []
    for k, (housing, light) in enumerate(lamps):
        kit.parent(housing, root)
        kit.parent(light, housing)
        nb.show_at(housing, 40 + 3 * k)
        lights.append((light, kit.flashes((k * 20, 8))))
    mount = kit.parent(kit.empty('Mount', HOUSING), root)
    barrel, flash, charge, glow = cannon(m, mount)

    # Build
    nb.rise(shell, 0, 26, TOP + 0.05)
    nb.rise(details, 6, 26, TOP + DRUM + 0.05)
    kit.keys(mount, 'scale', {0: Vector((HIDDEN,) * 3), 33: Vector((HIDDEN,) * 3), 34: Vector((1, 1, 1))}, 'CONSTANT')
    nb.rise(mount, 34, 16, 0.4)
    short = Vector((1, HIDDEN, 1))
    kit.keys(barrel, 'scale', {0: short, 52: short, 68: Vector((1, 1.05, 1)), 72: Vector((1, 1, 1))})
    nb.all_to_build()

    # Idle: the emitter glows softly, lamps blink
    kit.keys(glow, 'scale', {f: Vector((1, 1, 1)) * (0.8 + 0.3 * math.sin(2 * math.pi * 2 * f / kit.IDLE_END)) for f in range(0, kit.IDLE_END + 1, 3)}, 'LINEAR')
    kit.to_track(glow, 'Idle')
    nb.blinking(lights)

    # Fire: charge, discharge, kick
    hidden = Vector((HIDDEN,) * 3)
    kit.keys(charge, 'scale', {0: Vector((0.15,) * 3), 18: Vector((1, 1, 1)), 20: Vector((1.15,) * 3), 21: hidden, FIRE_FRAMES: hidden}, 'LINEAR')
    kit.to_track(charge, 'Fire')
    kit.keys(glow, 'scale', {0: Vector((1.2,) * 3), 19: Vector((2.2,) * 3), 21: Vector((0.3,) * 3), FIRE_FRAMES: Vector((0.8,) * 3)}, 'LINEAR')
    kit.to_track(glow, 'Fire')
    nb.flash_keys(flash, FIRE_FRAMES, 20, 27, 1.6)
    kit.to_track(flash, 'Fire')
    rest = barrel.location.copy()
    kit.keys(barrel, 'location', {0: rest, 20: rest, 22: rest + Vector((0, 0.05, 0)), 25: rest + Vector((0, 0.05, 0)), FIRE_FRAMES: rest})
    kit.to_track(barrel, 'Fire')

    shell.location = details.location = (0, 0, 0)
    mount.location = HOUSING
    barrel.location, barrel.scale = rest, (1, 1, 1)
    flash.scale = charge.scale = (HIDDEN,) * 3
    glow.scale = (0.8,) * 3
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NAPULS', {'Build': [20, 45, 62, BUILD_END], 'Idle': [0], 'Fire': [12, 22]}, scale=2.6, target=(0, 0, 0.4), texture=1024)
