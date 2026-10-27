"""
Tiberian Fallout – Nod EMP cannon (NAPULS), after Tiberian Sun.

A big tower on 2 × 2 cells: a pyramid of greenish grey concrete braced by four sloped
legs that run out to the corners, on top a red (house colour) drum, and on it the
turning housing with the pulse cannon – a thick barrel wound with copper coils that
opens into a parabolic dish with an emitter spike in its middle. Doors and vents in
the pyramid's faces, a red lamp over the door.

Nodes the game uses (see nodstructure.py):
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
import nodstructure as nb  # noqa: E402

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
HIDDEN = kit.HIDDEN

TOP = 0.42                      # the pyramid's top
BODY_B, BODY_T = 0.6, 0.38      # half the pyramid's width at the foot and at the top
LEG = 1.2                       # how far the legs run out along the diagonals
HOUSING = Vector((0, 0, TOP + 0.03))   # the turret's pivot on the collar
DRUM_R, DRUM_H = 0.36, 0.38
DRUM_TOP = HOUSING.z + DRUM_H
GUN = Vector((0, 0.02, DRUM_TOP + 0.11))
FIRE_FRAMES = 30
BUILD_END = 78


def pyramid(m, root):
    """The concrete pyramid and its legs (baked), the details; returns both."""
    body = kit.hexahedron('PyramidBody', m['steel'], (
        (-BODY_B, -BODY_B, 0), (BODY_B, -BODY_B, 0), (BODY_B, BODY_B, 0), (-BODY_B, BODY_B, 0),
        (-BODY_T, -BODY_T, TOP), (BODY_T, -BODY_T, TOP), (BODY_T, BODY_T, TOP), (-BODY_T, BODY_T, TOP)), bevel=0.02)
    legs = []
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        d = Vector((math.cos(a), math.sin(a), 0))
        n = Vector((-d.y, d.x, 0))
        foot, head = d * LEG, d * BODY_T * math.sqrt(2) * 0.92
        legs.append(kit.hexahedron(f'Leg{k}', m['steel'], (
            foot - n * 0.13, foot + n * 0.13, d * 0.45 + n * 0.3, d * 0.45 - n * 0.3,
            foot * 0.97 - n * 0.1 + Vector((0, 0, 0.1)), foot * 0.97 + n * 0.1 + Vector((0, 0, 0.1)),
            head + n * 0.08 + Vector((0, 0, TOP + 0.1)), head - n * 0.08 + Vector((0, 0, TOP + 0.1))), bevel=0.02))
    shell = nb.concrete('Pyramid', [body, *legs], root, '#7e8070')

    parts = []
    run = BODY_B - BODY_T
    slope = math.atan2(TOP, run)
    for k in range(4):
        turn = kit.Matrix.Rotation(k * math.pi / 2, 4, 'Z')
        normal = Vector((0, -math.sin(slope), math.cos(slope)))

        def on_face(name, mat, size, t, x=0.0, lift=0.006):
            """A plate on the face's slope at height fraction t."""
            at = Vector((x, -BODY_B + run * t, TOP * t)) + normal * lift
            obj = box(name, mat, size, (0, 0, 0), bevel=0.004)
            obj.matrix_world = turn @ kit.Matrix.Translation(at) @ kit.Matrix.Rotation(slope, 4, 'X')
            return obj
        parts.append(on_face(f'Band{k}', m['nplate_dark'], (2 * (BODY_B - run * 0.85) - 0.12, 0.04, 0.012), 0.85))
        if k == 0:     # the door at the front
            parts += [on_face('Door', m['armour_dark'], (0.2, 0.2, 0.02), 0.27),
                      on_face('DoorFrame', m['steel'], (0.24, 0.03, 0.024), 0.45),
                      on_face('DoorStep', m['steel'], (0.28, 0.06, 0.02), 0.06)]
        else:
            parts += [on_face(f'Vent{k}', m['dark'], (0.26, 0.1, 0.02), 0.35),
                      *[on_face(f'VentSlat{k}{j}', m['steel'], (0.27, 0.012, 0.024), 0.31 + 0.04 * j) for j in range(3)]]
    for k in range(4):   # plates on the legs' feet
        a = math.pi / 4 + k * math.pi / 2
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(box(f'LegFoot{k}', m['armour_dark'], (0.16, 0.16, 0.05), d * (LEG - 0.1) + Vector((0, 0, 0.025)), bevel=0.01, rotation=(0, 0, a)))
    parts += [
        cylinder('Collar', m['steel'], DRUM_R + 0.025, 0.03, (0, 0, TOP + 0.015), segments=32),
        cylinder('CollarRim', m['armour_dark'], DRUM_R + 0.035, 0.012, (0, 0, TOP + 0.006), segments=32, bevel=0.002),
    ]
    return shell, kit.merge('PyramidDetails', parts)


def cannon(m, mount):
    """The red drum (Turret) and the pulse cannon (Cannon → Recoil); returns the animated parts."""
    turret = kit.parent(kit.empty('Turret', HOUSING), mount)
    z = HOUSING.z
    drum = nb.lathe('Drum', m['remap'], [
        (DRUM_R - 0.02, 0), (DRUM_R, 0.02), (DRUM_R, DRUM_H - 0.07), (DRUM_R - 0.03, DRUM_H - 0.025),
        (DRUM_R - 0.1, DRUM_H - 0.003), (0, DRUM_H)], HOUSING, segments=36)
    housing = [
        drum,
        cylinder('DrumFoot', m['armour_dark'], DRUM_R + 0.008, 0.03, (0, 0, z + 0.015), segments=36, bevel=0.003),
        cylinder('DrumBand', m['armour_dark'], DRUM_R + 0.006, 0.025, (0, 0, z + DRUM_H - 0.085), segments=36, bevel=0.003),
        *[box(f'DrumRib{k}', m['armour_dark'], (0.035, 0.02, DRUM_H - 0.13), (DRUM_R * math.cos(a), DRUM_R * math.sin(a), z + 0.03 + (DRUM_H - 0.13) / 2),
              bevel=0.004, rotation=(0, 0, a + math.pi / 2)) for k, a in ((k, math.pi / 16 + k * math.pi / 4) for k in range(8))],
        # the cradle on the drum's top: trunnion cheeks, capacitors at the back
        box('CradleBase', m['armour_dark'], (0.34, 0.26, 0.03), (0, GUN.y + 0.02, DRUM_TOP - 0.005), bevel=0.006),
        *[box(f'Trunnion{s}', m['armour'], (0.045, 0.16, 0.15), (s * 0.135, GUN.y, (DRUM_TOP + GUN.z) / 2 + 0.015), bevel=0.01) for s in (-1, 1)],
        *[cylinder(f'TrunnionHub{s}', m['steel'], 0.04, 0.012, (s * 0.16, GUN.y, GUN.z), rotation=(0, math.pi / 2, 0), segments=14, bevel=0.002) for s in (-1, 1)],
        *[cylinder(f'Capacitor{s}', m['steel_light'], 0.045, 0.2, (s * 0.2, 0.24, DRUM_TOP - 0.01), rotation=(math.pi / 2, 0, 0), segments=16)
          for s in (-1, 1)],
        *[cylinder(f'CapCap{s}', m['remap'], 0.048, 0.025, (s * 0.2, 0.35, DRUM_TOP - 0.01), rotation=(math.pi / 2, 0, 0), segments=16)
          for s in (-1, 1)],
        *detail.hose('Feed0', m['dark'], (0.2, 0.14, DRUM_TOP - 0.01), (0.2, 0.06, DRUM_TOP + 0.02), (0.157, 0.02, DRUM_TOP + 0.06), 0.012),
        *detail.hose('Feed1', m['dark'], (-0.2, 0.14, DRUM_TOP - 0.01), (-0.2, 0.06, DRUM_TOP + 0.02), (-0.157, 0.02, DRUM_TOP + 0.06), 0.012),
        *detail.grille('DrumVent', m['steel'], m['dark'], (0, DRUM_R + 0.005, z + 0.1), 0.2, 0.08, 'Y', 4),
    ]
    kit.parent(kit.merge('DrumBody', housing, HOUSING), turret)
    lamp = nb.lamp(m, turret, 'DrumLamp', (0.0, 0.3, DRUM_TOP - 0.03), 'red', 58)

    pivot = kit.parent(kit.empty('Cannon', GUN), turret)
    recoil = kit.parent(kit.empty('Recoil', GUN), pivot)
    along = (math.pi / 2, 0, 0)
    copper = material('Copper', srgb('#b5703a'), 0.35, 1.0)
    dish_y = GUN.y - 0.36
    parts = [
        cylinder('Core', m['armour_dark'], 0.065, 0.46, GUN + Vector((0, -0.1, 0)), rotation=along, segments=20),
        cylinder('Breech', m['armour'], 0.09, 0.12, GUN + Vector((0, 0.1, 0)), rotation=along, segments=20, bevel=0.01),
        cylinder('BreechCap', m['remap'], 0.07, 0.02, GUN + Vector((0, 0.17, 0)), rotation=along, segments=20, bevel=0.004),
        # a small parabolic dish: cone rings opening forwards
        cylinder('DishBack', m['steel'], 0.07, 0.04, (GUN.x, dish_y + 0.02, GUN.z), rotation=along, radius2=0.11, segments=24, bevel=0.003),
        cylinder('Dish', m['steel_light'], 0.11, 0.05, (GUN.x, dish_y - 0.02, GUN.z), rotation=along, radius2=0.16, segments=28, bevel=0.003),
        cylinder('DishInner', m['dark'], 0.07, 0.056, (GUN.x, dish_y - 0.018, GUN.z), rotation=along, radius2=0.148, segments=28, bevel=0),
        *[beam(f'DishRim{k}', m['remap'],
               (0.162 * math.cos(2 * math.pi * k / 16), dish_y - 0.047, GUN.z + 0.162 * math.sin(2 * math.pi * k / 16)),
               (0.162 * math.cos(2 * math.pi * (k + 1) / 16), dish_y - 0.047, GUN.z + 0.162 * math.sin(2 * math.pi * (k + 1) / 16)), 0.018, 0.014)
          for k in range(16)],
        cylinder('Spike', m['steel'], 0.018, 0.12, (GUN.x, dish_y - 0.05, GUN.z), rotation=along, radius2=0.006, segments=12),
        sphere('Emitter', m['lamp_pulse'], 0.024, (GUN.x, dish_y - 0.105, GUN.z), 12),
    ]
    for k in range(4):   # dish struts holding the spike
        a = math.pi / 4 + k * math.pi / 2
        parts.append(beam(f'Strut{k}', m['steel'], (0.13 * math.cos(a), dish_y - 0.035, GUN.z + 0.13 * math.sin(a)), (0, dish_y - 0.09, GUN.z), 0.008))
    for k in range(5):   # copper coils round the core
        parts.append(cylinder(f'Coil{k}', copper, 0.088, 0.026, GUN + Vector((0, -0.05 - k * 0.045, 0)), rotation=along, segments=20, bevel=0.005))
    kit.parent(kit.merge('PulseCannon', parts, GUN), recoil)
    emitter = Vector((GUN.x, dish_y - 0.105, GUN.z))
    glow = kit.parent(nb.glow(m, 'EmitterGlow', emitter, 0.04, 'glow_pulse', 1), pivot)
    flare = kit.parent(nb.glow(m, 'EmitterFlare', emitter, 0.05, 'glow_pulse', 1), pivot)
    charge = kit.parent(nb.glow(m, 'Charge', emitter + Vector((0, 0.05, 0)), 0.13, 'glow_pulse', 1), pivot)
    flash = kit.parent(nb.glow(m, 'Flash', emitter - Vector((0, 0.06, 0)), 0.12, 'glow_pulse', 4), pivot)
    return recoil, flash, charge, glow, flare, lamp


def build():
    root = nb.start('NodEMP', 'NodEMPCannon', BUILD_END)
    m = nb.materials()
    shell, details = pyramid(m, root)
    kit.parent(shell, root)
    kit.parent(details, root)
    lights = []
    run = BODY_B - BODY_T
    lamp_spots = [(0.0, -BODY_B + run * 0.93 - 0.02, TOP * 0.93)]
    for a in (math.pi / 4, -3 * math.pi / 4):
        d = Vector((math.cos(a), math.sin(a), 0)) * (LEG - 0.1)
        lamp_spots.append((d.x, d.y, 0.05))
    for k, at in enumerate(lamp_spots):
        light = nb.lamp(m, root, f'Lamp{k}', at, 'red', 30 + 3 * k)
        lights.append((light, kit.flashes((k * 20, 8))))
    mount = kit.parent(kit.empty('Mount', HOUSING), root)
    recoil, flash, charge, glow, flare, drum_light = cannon(m, mount)
    lights.append((drum_light, kit.flashes((10, 6), (40, 6))))

    # Build: the pyramid rises, then the drum with the cannon is lowered onto it
    nb.rise(shell, 0, 26, TOP + 0.05)
    nb.rise(details, 6, 26, TOP + 0.08)
    kit.keys(mount, 'location', {0: HOUSING - Vector((0, 0, 2)), 39: HOUSING - Vector((0, 0, 2))}, 'CONSTANT')
    kit.keys(mount, 'location', {40: HOUSING + Vector((0, 0, 0.7)), 60: HOUSING - Vector((0, 0, 0.005)), 64: HOUSING})
    nb.all_to_build()

    # Idle: the emitter glows softly, lamps blink
    nb.pulse(glow, kit.IDLE_END, 0.7, 1.2, cycles=2)
    kit.to_track(glow, 'Idle')
    nb.blinking(lights)

    # Fire: charge, discharge, kick
    hidden = Vector((HIDDEN,) * 3)
    kit.keys(charge, 'scale', {0: hidden, 1: Vector((0.15,) * 3), 18: Vector((1, 1, 1)), 20: Vector((1.15,) * 3), 21: hidden, FIRE_FRAMES: hidden}, 'LINEAR')
    kit.to_track(charge, 'Fire')
    kit.keys(flare, 'scale', {0: hidden, 1: Vector((1.0,) * 3), 19: Vector((2.2,) * 3), 21: Vector((0.3,) * 3), 23: hidden, FIRE_FRAMES: hidden}, 'LINEAR')
    kit.to_track(flare, 'Fire')
    nb.flash_keys(flash, FIRE_FRAMES, 20, 27, 1.6)
    kit.to_track(flash, 'Fire')
    rest = recoil.location.copy()
    kit.keys(recoil, 'location', {0: rest, 20: rest, 22: rest + Vector((0, 0.05, 0)), 25: rest + Vector((0, 0.05, 0)), FIRE_FRAMES: rest})
    kit.to_track(recoil, 'Fire')

    shell.location = details.location = (0, 0, 0)
    mount.location = HOUSING
    recoil.location = rest
    flash.scale = charge.scale = flare.scale = (HIDDEN,) * 3
    glow.scale = (1, 1, 1)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NAPULS', {'Build': [20, 45, 62, BUILD_END], 'Idle': [0], 'Fire': [12, 22, FIRE_FRAMES]}, ortho=2.6, target=(0, 0, 0.4), texture=1024)
