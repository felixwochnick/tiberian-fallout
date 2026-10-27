"""
Tiberian Fallout – GDI Carryall (TRNSPORT), after Tiberian Sun.

A long transport VTOL, after the build icon (about one and a half cells long): a slim
fuselage with a glazed nose cockpit, a spine with intakes and a tail with a fin and
house-colour tips; two pairs of short wings, at the front and at the back, carry four
ducted fans (rings round four-bladed fans with hubs in the house colour). Under the
middle of the fuselage the cargo clamp: a winch housing with four clamp arms; the
carried vehicle hangs there. Four gear legs with pads.

The fuselage, wings and ducts wear the light camouflage of GDI (baked, tinted with the
house colour in the game: GAPILE.camo_material).

Nodes for the game: "Hook" (under the clamp, where the carried vehicle hangs; it sways
with the body); the ducts tilt on "Duct0"…"Duct3", their fans turn on "Fan0"…"Fan3",
"FanBlur0"…"FanBlur3" show at speed.

Clips (see aircraft.py; it has no weapon, so no Fire)
    Idle     loop, 2 s: landed, fans standing
    TakeOff  once, 1 s: the fans spin up, the gear comes in, the ducts tilt forward
    Fly      loop, 1 s: fans fast (blur discs), ducts tilted, a gentle sway
    Land     once, 1 s: the gear goes out, the ducts level, the fans run down

Run headless:

    blender -b --factory-startup --python blender/TRNSPORT.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle; landed, the gear's pads touch Z = 0.
"""
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import DSHP  # noqa: E402 – loft()
import aircraft as air  # noqa: E402
import detail  # noqa: E402

OUT = os.path.join(air.PROJECT, 'public', 'models', 'TRNSPORT.glb')
BLEND = os.path.join(HERE, 'TRNSPORT.blend')

BELLY = 0.2                        # underside of the fuselage, landed
DUCT_X = 0.36
DUCT_Z = 0.31
DUCT_Y = (-0.36, 0.4)              # front and rear pair
DUCT_R, DUCT_H = 0.13, 0.07        # inner radius, height; the ring is 0.025 thick
TILT_FLY = -12                     # degrees about x: the ducts lean forward in flight
HOOK_AT = Vector((0, 0.02, BELLY - 0.1))
FAN_SPEED = 2 * (2 * math.pi) / air.FLY_FRAMES   # two turns per Fly loop

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
loft = DSHP.loft
HIDDEN = kit.HIDDEN

HULL = (  # y, half width, bottom, top
    (-0.76, 0.03, 0.27, 0.31), (-0.7, 0.08, 0.23, 0.36), (-0.58, 0.11, BELLY, 0.39), (0.0, 0.11, BELLY, 0.39),
    (0.45, 0.09, 0.22, 0.37), (0.62, 0.05, 0.26, 0.35), (0.72, 0.03, 0.29, 0.34),
)


def materials():
    m = kit.materials()
    m.update({
        'glass': material('Canopy', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#22384a'), strength=0.4),
        'blade': material('FanBlade', srgb('#3a3d40'), 0.5, 0.6),
        'blur': material('FanBlur', srgb('#2a2c2e'), 0.8, alpha=0.25),
    })
    m['blur'].use_backface_culling = False
    return m


def camo(obj, root, name):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{name}', root))
    return obj


def ring(name, mat, centre, inner, outer, height, segments=24):
    """An open ring (a duct) round the vertical through `centre`."""
    def build(bm):
        rings = []
        for r in (inner, outer):
            for z in (-height / 2, height / 2):
                rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / segments), r * math.sin(2 * math.pi * k / segments), z))
                              for k in range(segments)])
        ib, it, ob, ot = rings
        for k in range(segments):
            j = (k + 1) % segments
            bm.faces.new((ib[k], ib[j], it[j], it[k]))
            bm.faces.new((ob[k], ot[k], ot[j], ob[j]))
            bm.faces.new((it[k], it[j], ot[j], ot[k]))
            bm.faces.new((ib[k], ob[k], ob[j], ib[j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    obj = kit.mesh_object(name, build)
    obj.location = centre
    kit.finish(obj, mat, 0)
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj


def hull(m, root):
    """Fuselage and wings in camouflage (one object) and their fittings."""
    wings = []
    for i, y in enumerate(DUCT_Y):
        x0 = DUCT_X - DUCT_R
        wings.append(kit.hexahedron(f'Wing{i}', m['sand'], (
            (-x0, y - 0.06, 0.29), (x0, y - 0.06, 0.29), (x0, y + 0.06, 0.29), (-x0, y + 0.06, 0.29),
            (-x0, y - 0.05, 0.325), (x0, y - 0.05, 0.325), (x0, y + 0.06, 0.32), (-x0, y + 0.06, 0.32)), bevel=0))
    shell = kit.merge('Hull', [loft('Fuselage', m['sand'], HULL, chamfer=0.45), *wings])
    for poly in shell.data.polygons:
        poly.use_smooth = False
    camo(shell, root, 'Hull')

    parts = [
        loft('Canopy', m['glass'], ((-0.74, 0.03, 0.28, 0.31), (-0.7, 0.075, 0.25, 0.35), (-0.6, 0.1, 0.26, 0.4),
                                    (-0.5, 0.08, 0.33, 0.405))),
        box('CanopyFrame', m['dark'], (0.012, 0.24, 0.012), (0, -0.62, 0.41), bevel=0.003),
        box('Spine', m['sand_light'], (0.1, 0.8, 0.03), (0, -0.04, 0.395), bevel=0.01),
        box('SpineStripe', m['remap'], (0.04, 0.6, 0.032), (0, -0.04, 0.398), bevel=0.004),
        *[box(f'IntakeSlat{k}', m['dark'], (0.08, 0.012, 0.014), (0, 0.4 + 0.024 * k, 0.4), bevel=0) for k in range(4)],
        # the tail fin with a house-colour tip
        kit.hexahedron('Fin', m['sand_light'], (
            (-0.01, 0.52, 0.36), (0.01, 0.52, 0.36), (0.01, 0.7, 0.34), (-0.01, 0.7, 0.34),
            (-0.008, 0.66, 0.5), (0.008, 0.66, 0.5), (0.008, 0.75, 0.5), (-0.008, 0.75, 0.5)), bevel=0.003),
        kit.hexahedron('FinTip', m['remap'], (
            (-0.011, 0.645, 0.47), (0.011, 0.645, 0.47), (0.011, 0.742, 0.47), (-0.011, 0.742, 0.47),
            (-0.009, 0.66, 0.502), (0.009, 0.66, 0.502), (0.009, 0.752, 0.502), (-0.009, 0.752, 0.502)), bevel=0.002),
        box('TailLight', m['lamp_white'], (0.016, 0.012, 0.012), (0, 0.73, 0.32), bevel=0),
        # the cargo clamp: winch housing, cable drum, four arms reaching down and in
        box('Winch', m['steel'], (0.14, 0.2, 0.05), (0, HOOK_AT.y, BELLY - 0.02), bevel=0.01),
        cylinder('WinchDrum', m['dark'], 0.025, 0.12, (0, HOOK_AT.y, BELLY - 0.05), rotation=(0, math.pi / 2, 0), segments=12, bevel=0),
        box('ClampPlate', m['steel_light'], (0.09, 0.09, 0.015), (0, HOOK_AT.y, HOOK_AT.z + 0.02), bevel=0.004),
        beam('HookCable', m['dark'], (0, HOOK_AT.y, BELLY - 0.05), (0, HOOK_AT.y, HOOK_AT.z + 0.02), 0.008),
        box('HookStripe', m['remap'], (0.142, 0.03, 0.052), (0, HOOK_AT.y, BELLY - 0.02), bevel=0.004),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            top = Vector((sx * 0.05, HOOK_AT.y + sy * 0.07, BELLY - 0.03))
            knee = Vector((sx * 0.1, HOOK_AT.y + sy * 0.12, BELLY - 0.08))
            tip = Vector((sx * 0.08, HOOK_AT.y + sy * 0.1, HOOK_AT.z - 0.01))
            parts += [beam(f'ClampArm{sx}{sy}', m['steel'], top, knee, 0.016),
                      beam(f'ClampClaw{sx}{sy}', m['dark'], knee, tip, 0.014)]
    for s in (-1, 1):
        parts += [
            *detail.lamp(f'ChinLamp{s}', m['dark'], m['lamp_red'], (s * 0.05, -0.72, 0.25), (0, -1, -0.3), 0.012),
            box(f'NoseStripe{s}', m['remap'], (0.01, 0.14, 0.024), (s * 0.108, -0.45, 0.3), bevel=0.003),
            *[box(f'SideSlit{s}{k}', m['dark'], (0.008, 0.06, 0.012), (s * 0.112, -0.2 + 0.12 * k, 0.33), bevel=0.002) for k in range(4)],
            box(f'Door{s}', m['sand_light'], (0.008, 0.14, 0.1), (s * 0.111, -0.4, 0.28), bevel=0.002),
        ]
    return shell, kit.merge('HullDetails', parts)


def duct(m, root, i, centre):
    """A duct with its pylon (tilting about x on the empty), the fan inside it and
    the fan's blur disc."""
    s = 1 if centre.x > 0 else -1
    shell = ring(f'DuctRing{i}', m['sand'], centre, DUCT_R, DUCT_R + 0.025, DUCT_H)
    shell = kit.merge(f'DuctShell{i}', [shell], centre)
    camo(shell, root, f'Duct{i}')
    parts = [
        ring(f'DuctLip{i}', m['remap'], centre + Vector((0, 0, DUCT_H / 2 + 0.004)), DUCT_R + 0.002, DUCT_R + 0.027, 0.008),
        ring(f'DuctBand{i}', m['steel'], centre - Vector((0, 0, DUCT_H / 2 + 0.004)), DUCT_R + 0.002, DUCT_R + 0.027, 0.008),
        # stator struts across the duct under the fan, the motor in the middle
        *[beam(f'Stator{i}{k}', m['dark'], centre + Vector((math.cos(a) * DUCT_R, math.sin(a) * DUCT_R, -0.025)),
               centre + Vector((-math.cos(a) * DUCT_R, -math.sin(a) * DUCT_R, -0.025)), 0.012, 0.008)
          for k, a in enumerate((0.0, math.pi / 2))],
        cylinder(f'Motor{i}', m['steel'], 0.03, 0.03, centre - Vector((0, 0, 0.025)), segments=12, bevel=0.003),
        *detail.lamp(f'Nav{i}', m['dark'], m['lamp_green' if s > 0 else 'lamp_red'],
                     centre + Vector((s * (DUCT_R + 0.03), 0, 0)), (s, 0, 0), 0.01),
    ]
    details = kit.merge(f'DuctDetails{i}', parts, centre)
    blades = [cylinder(f'FanHub{i}', m['remap'], 0.025, 0.025, centre + Vector((0, 0, 0.005)), segments=12, bevel=0.003)]
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        d = Vector((math.cos(a), math.sin(a), 0))
        blades.append(beam(f'FanBlade{i}{k}', m['blade'], centre + d * 0.02, centre + d * (DUCT_R - 0.008), 0.032, 0.006))
    fan = kit.merge(f'Fan{i}', blades, centre)
    blur = kit.merge(f'FanBlur{i}', [cylinder(f'FanDisc{i}', m['blur'], DUCT_R - 0.005, 0.004, centre + Vector((0, 0, 0.012)),
                                              segments=24, bevel=0)], centre)
    return shell, details, fan, blur


def gear(m):
    parts = []
    for name, (x, y) in (('FrontL', (-0.08, -0.45)), ('FrontR', (0.08, -0.45)), ('RearL', (-0.08, 0.35)), ('RearR', (0.08, 0.35))):
        parts += [
            cylinder(f'Leg{name}', m['steel_light'], 0.013, BELLY, (x, y, BELLY / 2), segments=8, bevel=0),
            cylinder(f'Strut{name}', m['steel'], 0.02, 0.05, (x, y, BELLY - 0.035), segments=8, bevel=0.002),
            cylinder(f'Pad{name}', m['dark'], 0.032, 0.012, (x, y, 0.006), segments=12, bevel=0.002),
        ]
    return kit.merge('Gear', parts, (0, 0, BELLY))


def build():
    root, body = air.start('GDICarryall', 'Carryall')
    m = materials()
    for obj in hull(m, root):
        kit.parent(obj, body)
    legs = kit.parent(gear(m), body)
    kit.parent(kit.empty('Hook', HOOK_AT), body)
    ducts, fans, blurs = [], [], []
    i = 0
    for y in DUCT_Y:
        for s in (-1, 1):
            centre = Vector((s * DUCT_X, y, DUCT_Z))
            joint = kit.parent(kit.empty(f'Duct{i}', centre), body)
            shell, details, fan, blur = duct(m, root, i, centre)
            for obj in (shell, details, fan, blur):
                kit.parent(obj, joint)
            ducts.append(joint)
            fans.append(fan)
            blurs.append(blur)
            i += 1

    channels = [(body, 'location'), (body, 'rotation_euler'), (legs, 'scale')]
    for joint, fan, blur in zip(ducts, fans, blurs):
        channels += [(joint, 'rotation_euler'), (fan, 'rotation_euler'), (blur, 'scale')]
    rad = math.radians
    hidden = Vector((HIDDEN,) * 3)

    def pose(angle, speed, gear_out, tilt=0.0, pitch=0.0, roll=0.0, lift=0.0):
        shown = Vector((1, 1, 1)) if speed > 0.6 else hidden
        v = {
            ('Body', 'location'): Vector((0, 0, lift)),
            ('Body', 'rotation_euler'): Vector((rad(pitch), rad(roll), 0)),
            ('Gear', 'scale'): Vector((1, 1, air.mix(0.02, 1, gear_out))),
        }
        for k, (joint, fan, blur) in enumerate(zip(ducts, fans, blurs)):
            turn = 1 if k % 2 else -1    # the fans of a pair turn against each other
            v[(joint.name, 'rotation_euler')] = Vector((rad(tilt), 0, 0))
            v[(fan.name, 'rotation_euler')] = Vector((0, 0, turn * angle))
            v[(blur.name, 'scale')] = shown
        return v

    def fly(f):
        t = 2 * math.pi * f / air.FLY_FRAMES
        return pose(FAN_SPEED * f, 1, 0, TILT_FLY, pitch=-1.5 + 0.6 * math.sin(2 * t), roll=1.2 * math.sin(t), lift=0.008 * math.sin(t))

    def idle(f):
        return pose(0, 0, 1)

    # spinning up and down evenly: the fans turn a whole turn in each (no jump to Fly or Idle)
    def take_off(f):
        T = air.TAKEOFF_FRAMES
        return pose(FAN_SPEED * f * f / (2 * T), f / T, 1 - air.span(f, 10, 28), air.mix(0, TILT_FLY, air.span(f, 12, 30)),
                    pitch=air.mix(0, -1.5, air.span(f, 12, 30)))

    def land(f):
        T = air.LAND_FRAMES
        return pose(FAN_SPEED * (f - f * f / (2 * T)), 1 - f / T, air.span(f, 0, 16), air.mix(TILT_FLY, 0, air.span(f, 0, 18)),
                    pitch=air.mix(-1.5, 0, air.span(f, 0, 22)))

    air.clip('Idle', air.IDLE_FRAMES, channels, idle)
    air.clip('TakeOff', air.TAKEOFF_FRAMES, channels, take_off)
    air.clip('Fly', air.FLY_FRAMES, channels, fly)
    air.clip('Land', air.LAND_FRAMES, channels, land)

    def rest():
        for (name, prop), value in idle(0).items():
            setattr(kit.collection().objects[name], prop, value)

    rest()
    return rest


if __name__ == '__main__':
    air.main(build, OUT, BLEND, {'Idle': [0], 'TakeOff': [20], 'Fly': [3]}, bake=512, scale=2.0, target=(0, 0, 0.25))
