"""
Tiberian Fallout – GDI Carryall (TRNSPORT), after Tiberian Sun.

A long transport VTOL (about one and a half cells long). In front a rounded cockpit
under a wide, faceted glass canopy (light frame, two red chin lamps, an intake behind
it); the middle carries the cargo frame: a broad hood with sloped side plates and two
house-colour stripes on top, under its edges four hinged clamp arms on each side and
under its middle the cargo clamp (winch housing, cable, clamp plate): the carried
vehicle hangs there. A narrower boom runs back to a tall, rounded tail fin with the GDI
emblem and a house-colour tip. Two pairs of short arms with house-colour stripes, at
the front and at the back, carry four ducted fans: thick faceted rings with a dark
skirt and vents below, a fan of five blades round a house-colour hub over a stator.
Four gear legs with pads.

The fuselage, hood, boom, fin, arms and ducts wear the light camouflage of GDI (baked,
tinted with the house colour in the game: GAPILE.camo_material).

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

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import DSHP  # noqa: E402 – decal_material(), quad(), on_side(): the GDI emblem
import ORCA  # noqa: E402 – section_loft(), canopy(), ring()
import aircraft as air  # noqa: E402
import detail  # noqa: E402

OUT = os.path.join(air.PROJECT, 'public', 'models', 'TRNSPORT.glb')
BLEND = os.path.join(HERE, 'TRNSPORT.blend')

BELLY = 0.2                        # underside of the fuselage, landed
DUCT_X = 0.37
DUCT_Z = 0.31
DUCT_Y = (-0.42, 0.42)             # front and rear pair
DUCT_R, DUCT_OUT, DUCT_H = 0.13, 0.165, 0.075  # inner and outer radius, height of a duct's ring
TILT_FLY = -12                     # degrees about x: the ducts lean forward in flight
HOOD = (-0.32, 0.2)                # the cargo hood from y to y
HOOK_AT = Vector((0, -0.05, BELLY - 0.1))
FAN_SPEED = 2 * (2 * math.pi) / air.FLY_FRAMES   # two turns per Fly loop

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
HIDDEN = kit.HIDDEN

# y, right half of the cross section (x, z) from the bottom up: the nose, the cockpit,
# the middle under the hood, the boom narrowing to the tail
HULL = (
    (-0.78, ((0.03, 0.255), (0.05, 0.265), (0.052, 0.3), (0.032, 0.315))),
    (-0.73, ((0.065, 0.225), (0.098, 0.24), (0.104, 0.3), (0.07, 0.35))),
    (-0.63, ((0.08, 0.205), (0.118, 0.222), (0.124, 0.3), (0.08, 0.39))),
    (-0.5, ((0.085, BELLY), (0.122, 0.215), (0.126, 0.31), (0.085, 0.4))),
    (0.22, ((0.085, BELLY), (0.12, 0.215), (0.124, 0.33), (0.08, 0.395))),
    (0.45, ((0.055, 0.24), (0.085, 0.252), (0.088, 0.345), (0.058, 0.38))),
    (0.78, ((0.025, 0.3), (0.036, 0.305), (0.036, 0.345), (0.025, 0.358))),
)
CANOPY = range(1, 4)   # the hull sections the glass runs over
HOOD_SECTIONS = (  # the side plates: upright below, sloping in above
    (HOOD[0], ((0.14, 0.29), (0.18, 0.302), (0.18, 0.33), (0.155, 0.39), (0.11, 0.418))),
    (HOOD[0] + 0.05, ((0.17, 0.262), (0.222, 0.276), (0.222, 0.33), (0.19, 0.4), (0.14, 0.432))),
    (HOOD[1] - 0.06, ((0.17, 0.262), (0.222, 0.276), (0.222, 0.33), (0.19, 0.4), (0.14, 0.432))),
    (HOOD[1], ((0.13, 0.29), (0.17, 0.302), (0.17, 0.33), (0.145, 0.385), (0.1, 0.414))),
)
CLAWS = (-0.24, -0.11, 0.02, 0.13)  # y of the clamp arms under the hood's edges
# the tail fin's outline (y, z): the root on the boom, the trailing edge, a rounded top
FIN = ((0.48, 0.36), (0.775, 0.33), (0.78, 0.47),
       *[(0.7 + 0.08 * math.cos(math.radians(a)), 0.47 + 0.08 * math.sin(math.radians(a))) for a in range(15, 131, 23)])


def materials():
    m = ORCA.materials()
    m.update({
        'blade': material('FanBlade', srgb('#3a3d40'), 0.5, 0.6),
        'blur': material('FanBlur', srgb('#2a2c2e'), 0.8, alpha=0.25),
    })
    m['blur'].use_backface_culling = False
    return m


def camo(obj, root, name):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{name}', root))
    return obj


def lathe(name, mat, centre, profile, segments=16):
    """A solid of revolution round the vertical through `centre`: the closed outline
    `profile` ((r, z) points) turned once round; flat shaded."""
    def build(bm):
        rings = [[bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for r, z in profile]
                 for a in (2 * math.pi * (k + 0.5) / segments for k in range(segments))]
        n = len(profile)
        for k in range(segments):
            a, b = rings[k], rings[(k + 1) % segments]
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((a[i], a[j], b[j], b[i]))

    obj = kit.mesh_object(name, build)
    obj.location = centre
    kit.finish(obj, mat, 0)
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj


def plate(name, mat, outline, x, half):
    """A flat plate (the fin) from a convex outline of (y, z) points, `half` thick each
    way of x."""
    def build(bm):
        sides = [[bm.verts.new((x + d, y, z)) for y, z in outline] for d in (-half, half)]
        bm.faces.new(sides[0])
        bm.faces.new(list(reversed(sides[1])))
        n = len(outline)
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((sides[0][k], sides[0][j], sides[1][j], sides[1][k]))

    obj = kit.mesh_object(name, build)
    kit.finish(obj, mat, 0)
    return obj


def hull(m, root):
    """Fuselage, hood, fin and the ducts' arms in camouflage (one object), their
    fittings and the emblems."""
    arms = []
    for y in DUCT_Y:
        x1 = DUCT_X - DUCT_R - 0.01   # into the duct's wall
        arms.append(kit.hexahedron(f'Arm{y}', m['sand'], (
            (-x1, y - 0.055, DUCT_Z - 0.022), (x1, y - 0.055, DUCT_Z - 0.022), (x1, y + 0.05, DUCT_Z - 0.022), (-x1, y + 0.05, DUCT_Z - 0.022),
            (-x1, y - 0.045, DUCT_Z + 0.018), (x1, y - 0.045, DUCT_Z + 0.018), (x1, y + 0.05, DUCT_Z + 0.014), (-x1, y + 0.05, DUCT_Z + 0.014)),
            bevel=0))
    shell = kit.merge('Hull', [
        ORCA.section_loft('Fuselage', m['sand'], HULL),
        ORCA.section_loft('Hood', m['sand'], HOOD_SECTIONS),
        plate('Fin', m['sand'], FIN, 0, 0.012),
        *arms,
    ])
    for poly in shell.data.polygons:
        poly.use_smooth = False
    camo(shell, root, 'Hull')

    top = 0.432
    parts = [
        *ORCA.canopy('Canopy', m, [HULL[k] for k in CANOPY], (2, 3), frame=0.009),
        # behind the canopy an intake, a spine with a stripe along the boom
        box('IntakeFrame', m['steel'], (0.1, 0.08, 0.014), (0, -0.44, 0.402), bevel=0.003),
        *[box(f'IntakeSlat{k}', m['dark'], (0.086, 0.009, 0.014), (0, -0.47 + 0.015 * k, 0.405), bevel=0) for k in range(5)],
        box('BoomSpine', m['sand_light'], (0.06, 0.34, 0.02), (0, 0.38, 0.39), bevel=0.006),
        box('BoomStripe', m['remap'], (0.062, 0.05, 0.022), (0, 0.27, 0.39), bevel=0.004),
        # the hood: two house-colour stripes, a hatch and seams between them
        *[box(f'HoodStripe{s}', m['remap'], (0.03, HOOD[1] - HOOD[0] - 0.12, 0.008), (s * 0.095, (HOOD[0] + HOOD[1]) / 2, top + 0.002),
              bevel=0.002) for s in (-1, 1)],
        box('HoodHatch', m['sand_light'], (0.1, 0.12, 0.01), (0, -0.16, top + 0.003), bevel=0.003),
        *[detail.seam(f'HoodSeam{k}', m['dark'], (-0.075, y, top + 0.002), (0.075, y, top + 0.002), 0.004, 0.003)[0]
          for k, y in enumerate((-0.02, 0.08))],
        *detail.lamp('Beacon', m['dark'], m['lamp_red'], (0, 0.05, top + 0.004), (0, 0, 1), 0.012),
        # the tail fin's house-colour tip and lights
        plate('FinTip', m['remap'], [(0.7 + 0.083 * math.cos(math.radians(a)), 0.47 + 0.083 * math.sin(math.radians(a))) for a in range(0, 131, 26)],
              0, 0.014),
        box('TailLight', m['lamp_white'], (0.016, 0.012, 0.012), (0, 0.785, 0.32), bevel=0),
        # the cargo clamp under the hood's middle: winch housing, cable drum, cable, clamp plate
        box('Winch', m['steel'], (0.15, 0.22, 0.05), (0, HOOK_AT.y, BELLY - 0.02), bevel=0.01),
        box('WinchStripe', m['remap'], (0.152, 0.03, 0.052), (0, HOOK_AT.y - 0.07, BELLY - 0.02), bevel=0.004),
        cylinder('WinchDrum', m['dark'], 0.025, 0.12, (0, HOOK_AT.y, BELLY - 0.05), rotation=(0, math.pi / 2, 0), segments=12, bevel=0),
        beam('HookCable', m['dark'], (0, HOOK_AT.y, BELLY - 0.05), (0, HOOK_AT.y, HOOK_AT.z + 0.02), 0.008),
        box('ClampPlate', m['steel_light'], (0.1, 0.1, 0.016), (0, HOOK_AT.y, HOOK_AT.z + 0.02), bevel=0.004),
        *[beam(f'ClampHook{k}', m['dark'], (sx * 0.04, HOOK_AT.y, HOOK_AT.z + 0.015), (sx * 0.045, HOOK_AT.y, HOOK_AT.z - 0.012), 0.012)
          for k, sx in enumerate((-1, 1))],
    ]
    for s in (-1, 1):
        parts += [
            *detail.lamp(f'ChinLamp{s}', m['dark'], m['lamp_red'], (s * 0.05, -0.75, 0.25), (0, -1, -0.3), 0.012),
            box(f'NoseStripe{s}', m['remap'], (0.008, 0.16, 0.016), (s * 0.121, -0.54, 0.222), bevel=0.002),
            box(f'Door{s}', m['sand_light'], (0.008, 0.09, 0.058), (s * 0.123, -0.58, 0.264), bevel=0.002),
            # the hood's side plate: a vent and rivets
            *detail.grille(f'HoodVent{s}', m['steel'], m['dark'], (s * 0.225, -0.05, 0.303), 0.12, 0.034, 'X', slats=3, depth=0.01),
            *detail.rivets(f'HoodRivets{s}', m['steel'], (s * 0.224, -0.25, 0.322), (s * 0.224, 0.13, 0.322), 9, 0.005, 'X'),
            *detail.seam(f'HoodSideSeam{s}', m['dark'], (s * 0.207, -0.25, 0.364), (s * 0.207, 0.13, 0.364), 0.005, 0.004),
        ]
        # the clamp arms under the hood's edge: a hinge, the arm, the claw turned in
        for k, y in enumerate(CLAWS):
            top_at = Vector((s * 0.2, y, 0.27))
            knee = Vector((s * 0.215, y, 0.165))
            tip = Vector((s * 0.175, y, 0.095))
            parts += [
                cylinder(f'ClawHinge{s}{k}', m['steel_light'], 0.014, 0.04, top_at, rotation=(math.pi / 2, 0, 0), segments=10, bevel=0.002),
                beam(f'ClawArm{s}{k}', m['steel'], top_at, knee, 0.022, 0.03),
                cylinder(f'ClawKnee{s}{k}', m['dark'], 0.012, 0.034, knee, rotation=(math.pi / 2, 0, 0), segments=8, bevel=0),
                beam(f'ClawTip{s}{k}', m['dark'], knee, tip, 0.018, 0.026),
            ]
        # the arms' house-colour stripes
        for y in DUCT_Y:
            x0, x1 = 0.11 if y < 0 else 0.08, DUCT_X - DUCT_OUT + 0.006
            parts.append(box(f'ArmStripe{s}{y}', m['remap'], (x1 - x0, 0.03, 0.008), (s * (x0 + x1) / 2, y + 0.005, DUCT_Z + 0.018), bevel=0.002))
    details = kit.merge('HullDetails', parts)

    emblem = DSHP.decal_material()
    emblems = kit.merge('Emblems', [DSHP.on_side(DSHP.quad(f'Emblem{s}', emblem, 0.1, 0.1), s, Vector((s * 0.012, 0.68, 0.43)))
                                    for s in (-1, 1)])
    return shell, details, emblems


def duct(m, root, i, centre):
    """A duct (tilting about x on the empty), the fan inside it and the fan's blur
    disc."""
    s = 1 if centre.x > 0 else -1
    h = DUCT_H / 2
    shell = lathe(f'DuctRing{i}', m['sand'], centre, (
        (DUCT_R, -h + 0.012), (DUCT_R, h), (DUCT_OUT - 0.018, h), (DUCT_OUT, h - 0.016), (DUCT_OUT, -h + 0.02), (DUCT_OUT - 0.012, -h + 0.012)))
    shell = kit.merge(f'DuctShell{i}', [shell], centre)
    camo(shell, root, f'Duct{i}')
    vents = []
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        out = Vector((math.cos(a), math.sin(a), 0))
        vents.append(box(f'Vent{i}{k}', m['dark'], (0.006, 0.034, 0.018), centre + out * (DUCT_OUT - 0.001) + Vector((0, 0, -h + 0.03)),
                         bevel=0, rotation=(0, 0, a)))
    parts = [
        # the skirt under the ring, a light rim round the top
        ORCA.ring(f'Skirt{i}', m['steel'], centre - Vector((0, 0, h)), DUCT_R, DUCT_OUT - 0.014, 0.026, 16),
        ORCA.ring(f'Rim{i}', m['steel_light'], centre + Vector((0, 0, h + 0.002)), DUCT_R - 0.002, DUCT_R + 0.01, 0.006, 16),
        *vents,
        # stator struts across the duct under the fan, the motor in the middle
        *[beam(f'Stator{i}{k}', m['dark'], centre + Vector((math.cos(a) * DUCT_R, math.sin(a) * DUCT_R, -0.025)),
               centre + Vector((0, 0, -0.025)), 0.012, 0.008)
          for k, a in enumerate(2 * math.pi * (k + 0.25) / 3 for k in range(3))],
        cylinder(f'Motor{i}', m['steel'], 0.034, 0.034, centre - Vector((0, 0, 0.024)), segments=12, bevel=0.003),
        *detail.lamp(f'Nav{i}', m['dark'], m['lamp_green' if s > 0 else 'lamp_red'],
                     centre + Vector((s * (DUCT_OUT + 0.004), 0, 0.012)), (s, 0, 0), 0.011),
    ]
    details = kit.merge(f'DuctDetails{i}', parts, centre)
    blades = [cylinder(f'FanHub{i}', m['remap'], 0.03, 0.022, centre + Vector((0, 0, 0.004)), segments=12, bevel=0.003),
              cylinder(f'FanCone{i}', m['steel_light'], 0.024, 0.026, centre + Vector((0, 0, 0.026)), segments=12, bevel=0, radius2=0.006)]
    for k in range(5):
        a = 0.1 + k * 2 * math.pi / 5
        d = Vector((math.cos(a), math.sin(a), 0))
        blades.append(beam(f'FanBlade{i}{k}', m['blade'], centre + d * 0.024, centre + d * (DUCT_R - 0.008), 0.006, 0.036))
    fan = kit.merge(f'Fan{i}', blades, centre)
    blur = kit.merge(f'FanBlur{i}', [cylinder(f'FanDisc{i}', m['blur'], DUCT_R - 0.005, 0.004, centre + Vector((0, 0, 0.012)),
                                              segments=24, bevel=0)], centre)
    return shell, details, fan, blur


def gear(m):
    parts = []
    for name, (x, y) in (('FrontL', (-0.08, -0.52)), ('FrontR', (0.08, -0.52)), ('RearL', (-0.08, 0.2)), ('RearR', (0.08, 0.2))):
        parts += [
            cylinder(f'Leg{name}', m['steel_light'], 0.013, BELLY, (x, y, BELLY / 2), segments=8, bevel=0),
            cylinder(f'Strut{name}', m['steel'], 0.02, 0.05, (x, y, BELLY - 0.035), segments=8, bevel=0.002),
            beam(f'Link{name}', m['steel'], (x, y + 0.022, BELLY - 0.012), (x, y + 0.006, 0.045), 0.009),
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
