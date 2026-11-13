"""
Tiberian Fallout – Nod stealth tank (STNK), after Tiberian Sun.

A low, flat, faceted wedge on four separate track pods: the hull is a turtle shell of
sloped facets (an upright skirt, steep flanks, a long glacis with the cockpit glass,
a flat top) between four short tracks at its corners, each in an armoured pod on two
struts, its road wheels showing under the pod's skirt. On the raised back of the
top the missile launcher: a low box with a row of six tubes facing forward, the
missiles' red (house colour) noses in their mouths. Red emblem plates on the flanks,
glowing orange conduits along the shoulders, a red lamp strip along the skirt between
the pods, red lenses on the pods' inner sides and marker lamps on their noses, a
vented engine deck and tail lights at the back. The game fades it out while it is
cloaked.

Nodes the game uses: "Turret" (the launcher's mount, not animated), "Cannon" (the
launcher, tipped towards the target), "FlashL"/"FlashR" (the muzzle flashes of its
left and right three tubes; the game fires from them in turn). Clips (see
nodvehicle.py):
    Idle    loop, 2 s: the engine runs, the hull shivers
    Walk    loop: driving, the road wheels turn; walkSpeed on the root
    Fire    once, 0.6 s: the left tubes fire, then the right ones; each bank kicks back

Run headless:

    blender -b --factory-startup --python blender/STNK.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'STNK.glb')
BLEND = os.path.join(HERE, 'STNK.blend')

POD_X = 0.25                       # the track pods' middle across
POD_Y = (-0.29, 0.27)              # … along: the front and the back pair
POD_LENGTH = 0.29
TRACK_WIDTH = 0.105
TRACK_HEIGHT = 0.12
WHEEL = 0.045
WALK_FRAMES = 20
WALK_SPEED = 2 * math.pi * WHEEL / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 18
MOUNT = Vector((0, 0.165, 0.318))  # the launcher's pivot (Turret, Cannon)
LAUNCHER = (0.21, 0.25, 0.08)      # its size (x, y, z), its middle at the pivot
TUBES_X = (0.023, 0.052, 0.081)    # the tubes of one bank, out from the middle
SCALE = 1.0

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam

# the hull's shell: half outlines (x, y) from the nose to the tail at four heights,
# mirrored to the other side: the foot, the top of the upright skirt, the shoulder,
# the flat top
SHELL = (
    (0.06, ((0.07, -0.44), (0.13, -0.37), (0.17, -0.16), (0.17, 0.13), (0.14, 0.35), (0.09, 0.4))),
    (0.13, ((0.08, -0.455), (0.14, -0.38), (0.18, -0.16), (0.18, 0.13), (0.15, 0.36), (0.1, 0.41))),
    (0.215, ((0.055, -0.3), (0.115, -0.25), (0.15, -0.1), (0.15, 0.12), (0.125, 0.31), (0.08, 0.36))),
    (0.262, ((0.04, -0.17), (0.08, -0.13), (0.105, -0.04), (0.105, 0.14), (0.095, 0.29), (0.06, 0.32))),
)
CENTRE = Vector((0, 0, 0.12))      # inside the shell: which way its faces look out


def rings():
    """The shell's rings of points: right side nose to tail, left side tail to nose."""
    out = []
    for z, half in SHELL:
        right = [Vector((x, y, z)) for x, y in half]
        out.append(right + [Vector((-p.x, p.y, z)) for p in reversed(right)])
    return out


def loft(name, mat, rings_, bevel=0.01):
    """A solid through rings of points (the same count each, symmetric about x = 0 as
    rings() makes them), its first and last ring capped with strips of quads."""
    def build(bm):
        verts = [[bm.verts.new(p) for p in ring] for ring in rings_]
        n = len(rings_[0])
        for a, b in zip(verts, verts[1:]):
            for i in range(n):
                bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
        for ring in (verts[0], verts[-1]):
            for i in range(n // 2 - 1):
                bm.faces.new((ring[i], ring[i + 1], ring[n - 2 - i], ring[n - 1 - i]))

    obj = kit.finish(kit.mesh_object(name, build), mat, bevel)
    obj.modifiers['Bevel'].angle_limit = math.radians(12)   # every facet's edge: crisp facets
    return obj


def facet(k, i):
    """The shell's face between ring k and k + 1 from point i to i + 1: its corners
    (u along the ring, v up the face)."""
    rs = rings()
    n = len(rs[0])
    return rs[k][i], rs[k][(i + 1) % n], rs[k + 1][(i + 1) % n], rs[k + 1][i]


def on(quad, u, v):
    """A point on a facet (bilinear, u and v from 0 to 1)."""
    a, b, c, d = quad
    return a.lerp(b, u).lerp(d.lerp(c, u), v)


def outward(quad):
    """A facet's normal, pointing out of the shell."""
    a, b, _, d = quad
    n = (b - a).cross(d - a).normalized()
    return n if n.dot((a + b) / 2 - CENTRE) > 0 else -n


def plate(name, mat, quad, u0, u1, v0, v1, thick=0.008, lift=0.001, bevel=0.003):
    """A plate lying on a facet over [u0, u1] × [v0, v1]."""
    n = outward(quad)
    corners = [on(quad, u, v) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
    return kit.hexahedron(name, mat, [p + n * lift for p in corners] + [p + n * (lift + thick) for p in corners], bevel)


def side_facet(k, i, s):
    """Right facet i (s = 1) or its mirror image on the left (s = -1), u running from
    the nose towards the tail on both sides."""
    if s > 0:
        return facet(k, i)
    a, b, c, d = facet(k, len(SHELL[0][1]) * 2 - 2 - i)
    return b, a, d, c


def hull(m):
    """The faceted shell and everything fixed on it."""
    rs = rings()
    parts = [loft('Shell', m['armour'], rs, bevel=0.008)]
    front = facet(1, 11)          # the glacis between the noses of rings 1 and 2
    top_front = facet(2, 11)
    parts += [
        # the cockpit glass on the glacis, framed, with two bars, and the vision slit above
        plate('CockpitFrame', m['armour_dark'], front, 0.12, 0.88, 0.3, 0.97, 0.008),
        plate('Cockpit', m['glass'], front, 0.17, 0.83, 0.36, 0.92, 0.012),
        *[beam(f'CockpitBar{k}', m['armour_dark'], on(front, u, 0.36) + outward(front) * 0.013, on(front, u, 0.92) + outward(front) * 0.013,
               0.01, 0.006) for k, u in enumerate((0.38, 0.62))],
        plate('VisionSlit', m['glass'], top_front, 0.25, 0.75, 0.25, 0.6, 0.006),
        # the nose: a dark bumper with the headlights and a grille between them
        box('Bumper', m['armour_dark'], (0.15, 0.03, 0.05), (0, -0.452, 0.09), bevel=0.008),
        *detail.grille('NoseVent', m['steel'], m['dark'], (0, -0.468, 0.092), 0.07, 0.03, 'Y', 3, 0.006),
        # the flat top: a dark plate, a hatch and a periscope in front of the launcher
        plate('TopPlate', m['armour_dark'], (rs[3][0], rs[3][5], rs[3][6], rs[3][11]), 0.02, 0.98, 0.1, 0.9, 0.006),
        box('Hatch', m['armour'], (0.07, 0.07, 0.012), (0.035, -0.07, 0.275), bevel=0.004),
        box('HatchHinge', m['steel'], (0.05, 0.01, 0.01), (0.035, -0.035, 0.282), bevel=0.002),
        cylinder('Periscope', m['armour_dark'], 0.014, 0.024, (-0.045, -0.1, 0.282), segments=10),
        box('PeriscopeGlass', m['glass'], (0.02, 0.006, 0.01), (-0.045, -0.114, 0.286), bevel=0.001),
        # the launcher's pedestal (fixed; the launcher on it turns) and its cable
        kit.hexahedron('Pedestal', m['armour_dark'], (
            (-0.07, 0.07, 0.262), (0.07, 0.07, 0.262), (0.07, 0.26, 0.262), (-0.07, 0.26, 0.262),
            (-0.05, 0.1, 0.285), (0.05, 0.1, 0.285), (0.05, 0.24, 0.285), (-0.05, 0.24, 0.285)), bevel=0.004),
        *detail.hose('LauncherCable', m['dark'], (0.06, 0.27, 0.28), (0.085, 0.32, 0.255), (0.06, 0.34, 0.235), 0.007, 5),
        # the back: the engine deck on the rear slope, the tail plate with lamps and a vent
        box('TailPlate', m['armour_dark'], (0.16, 0.012, 0.06), (0, 0.412, 0.1), bevel=0.004),
        *detail.grille('TailVent', m['steel'], m['dark'], (0, 0.42, 0.1), 0.08, 0.035, 'Y', 3, 0.006),
        *detail.lamp('TailLightL', m['dark'], m['lamp_red'], (-0.065, 0.42, 0.1), (0, 1, 0), 0.009),
        *detail.lamp('TailLightR', m['dark'], m['lamp_red'], (0.065, 0.42, 0.1), (0, 1, 0), 0.009),
    ]
    back = facet(2, 5)
    for k in range(4):
        v = 0.18 + k * 0.2
        parts.append(plate(f'DeckSlat{k}', m['dark'], back, 0.12, 0.88, v, v + 0.09, 0.006))
    for s in (-1, 1):
        skirt = side_facet(0, 2, s)      # the upright skirt between the pods
        flank = side_facet(1, 2, s)      # the sloped flank above it
        upper = side_facet(2, 2, s)      # the steep upper flank up to the top
        cheek = side_facet(1, 1, s)      # the shoulder's front corner
        glacis_side = side_facet(1, 0, s)
        parts += [
            # the house colour's emblem plate on the flank, in a dark rim
            plate(f'EmblemRim{s}', m['armour_dark'], flank, 0.3, 0.7, 0.14, 0.86, 0.005),
            plate(f'Emblem{s}', m['remap'], flank, 0.36, 0.64, 0.24, 0.76, 0.009),
            # the skirt: a red lamp strip between the pods, rivets along its top
            plate(f'SkirtLamp{s}', m['lamp_red'], skirt, 0.2, 0.8, 0.3, 0.5, 0.004),
            *detail.rivets(f'SkirtRivet{s}', m['steel'], on(skirt, 0.05, 0.82) + outward(skirt) * 0.002,
                           on(skirt, 0.95, 0.82) + outward(skirt) * 0.002, 7, 0.005, 'X'),
            # vents on the shoulder's front corner, a seam down the glacis' side
            *[plate(f'CheekVent{s}{k}', m['dark'], cheek, 0.3 + k * 0.14, 0.37 + k * 0.14, 0.2, 0.8, 0.005) for k in range(3)],
            *detail.seam(f'GlacisSeam{s}', m['seam'], on(glacis_side, 0.5, 0.0) + outward(glacis_side) * 0.002,
                         on(glacis_side, 0.5, 1.0) + outward(glacis_side) * 0.002, 0.006, 0.004),
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.05, -0.46, 0.115), (0, -1, 0.2), 0.011),
        ]
        # the glowing conduit along the shoulder in its rail, capped at both ends
        n = outward(upper)
        a, b = on(upper, 0.04, 0.25) + n * 0.012, on(upper, 0.96, 0.25) + n * 0.012
        conduit = cylinder(f'Conduit{s}', m['glow_orange'], 0.0065, (b - a).length, (a + b) / 2, segments=8, bevel=0)
        conduit.rotation_mode = 'QUATERNION'
        conduit.rotation_quaternion = (b - a).to_track_quat('Z', 'Y')
        parts += [beam(f'ConduitRail{s}', m['armour_dark'], a - n * 0.008, b - n * 0.008, 0.022, 0.012),
                  conduit,
                  *[sphere(f'ConduitEnd{s}{k}', m['steel'], 0.01, p, 8) for k, p in enumerate((a, b))]]
    return kit.merge('Hull', parts)


def pod(m, name, s, y):
    """A track pod at a corner: its armoured cover and struts (returned as parts for
    the hull), its belt and road wheels (returned as objects); (parts, belt, wheels)."""
    x = s * POD_X
    y0, y1 = y - POD_LENGTH / 2, y + POD_LENGTH / 2
    inner, outer = x - s * (TRACK_WIDTH / 2 + 0.008), x + s * (TRACK_WIDTH / 2 + 0.01)
    front = y < 0
    # the end that faces away from the hull's middle is the pod's nose: sloped steeper
    ny, ty = (y0, y1) if front else (y1, y0)
    d = 1 if front else -1           # from the nose towards the tail
    top, low = TRACK_HEIGHT + 0.042, TRACK_HEIGHT - 0.035     # the cover's top and lower edge
    parts = [
        kit.hexahedron(f'{name}Cover', m['armour_dark'], (
            (inner, ny + d * 0.012, low), (outer, ny + d * 0.012, low), (outer, ty - d * 0.02, low), (inner, ty - d * 0.02, low),
            (inner, ny + d * 0.08, top), (outer - s * 0.014, ny + d * 0.08, top), (outer - s * 0.014, ty - d * 0.05, top),
            (inner, ty - d * 0.05, top)), bevel=0.01),
        # the skirt down its outer side over the upper half of the wheels
        kit.hexahedron(f'{name}Skirt', m['armour'], (
            (outer, ny + d * 0.032, low - 0.008), (outer + s * 0.008, ny + d * 0.032, low - 0.008),
            (outer + s * 0.008, ty - d * 0.032, low - 0.008), (outer, ty - d * 0.032, low - 0.008),
            (outer, ny + d * 0.07, top - 0.018), (outer + s * 0.004, ny + d * 0.07, top - 0.018),
            (outer + s * 0.004, ty - d * 0.05, top - 0.018), (outer, ty - d * 0.05, top - 0.018)), bevel=0.003),
        # a raised red panel on top, a hatch and the marker lamp on the nose
        box(f'{name}Panel', m['remap'], (TRACK_WIDTH * 0.62, POD_LENGTH * 0.4, 0.01), (x + s * 0.002, y + d * 0.012, top + 0.004), bevel=0.003),
        box(f'{name}Hatch', m['armour'], (TRACK_WIDTH * 0.42, 0.045, 0.008), (x + s * 0.002, ty - d * 0.075, top + 0.003), bevel=0.003),
        *detail.lamp(f'{name}Marker', m['dark'], m['lamp_red'], (outer - s * 0.022, ny + d * 0.056, top - 0.012), (0, -d, 0.7), 0.008),
        *detail.rivets(f'{name}Rivet', m['steel'], (outer + s * 0.009, ny + d * 0.06, low + 0.018), (outer + s * 0.009, ty - d * 0.06, low + 0.018),
                       6, 0.004, 'X'),
        # the inner side: a glowing red lens facing the hull
        cylinder(f'{name}Lens', m['lamp_red'], 0.012, 0.006, (inner - s * 0.003, y, 0.075), rotation=(0, math.pi / 2, 0), segments=10,
                 bevel=0),
    ]
    for k, t in enumerate((0.3, 0.7)):
        sy = y0 + t * POD_LENGTH
        root = Vector((s * shell_x(sy, 0.11) - s * 0.01, sy, 0.105))
        parts += [
            kit.hexahedron(f'{name}Strut{k}', m['steel'], (
                (root.x, sy - 0.02, 0.085), (inner, sy - 0.018, 0.085), (inner, sy + 0.018, 0.085), (root.x, sy + 0.02, 0.085),
                (root.x, sy - 0.02, 0.125), (inner, sy - 0.016, 0.115), (inner, sy + 0.016, 0.115), (root.x, sy + 0.02, 0.125)), bevel=0.004),
            beam(f'{name}Ram{k}', m['steel_light'], (root.x, sy + 0.028, 0.13), (inner, sy + 0.028, 0.095), 0.01),
        ]
    belt = nod.track(m, f'{name}Track', x, TRACK_WIDTH, y0, y1, TRACK_HEIGHT, 7)
    wheels = [nod.road_wheel(m, f'{name}Wheel{k}', (s * (POD_X + TRACK_WIDTH / 2 + 0.004), wy, WHEEL + 0.006), WHEEL, 0.016)
              for k, wy in enumerate((y0 + 0.058, y, y1 - 0.058))]
    return parts, belt, wheels


def shell_x(y, z):
    """The shell's half width at y and height z (between rings 0 and 2), roughly."""
    def at(half):
        for (x0, y0), (x1, y1) in zip(half, half[1:]):
            if y0 <= y <= y1:
                return x0 + (x1 - x0) * (y - y0) / (y1 - y0)
        return half[0][0] if y < half[0][1] else half[-1][0]
    (z0, h0), (z1, h1) = (SHELL[0], SHELL[1]) if z <= SHELL[1][0] else (SHELL[1], SHELL[2])
    t = (z - z0) / (z1 - z0)
    return at(h0) + (at(h1) - at(h0)) * t


def launcher(m, cannon):
    """The missile launcher on the Cannon node: its box, and the two banks of three
    tubes (they kick back when they fire); returns ((bank, flash) left, right)."""
    w, l, h = LAUNCHER
    c = MOUNT
    front, back = c.y - l / 2, c.y + l / 2
    kit.parent(kit.merge('Launcher', [
        kit.hexahedron('LauncherBox', m['armour_dark'], (
            (c.x - w / 2, front + 0.02, c.z - h / 2), (c.x + w / 2, front + 0.02, c.z - h / 2),
            (c.x + w / 2, back, c.z - h / 2), (c.x - w / 2, back, c.z - h / 2),
            (c.x - w / 2 + 0.012, front + 0.02, c.z + h / 2), (c.x + w / 2 - 0.012, front + 0.02, c.z + h / 2),
            (c.x + w / 2 - 0.012, back - 0.05, c.z + h / 2), (c.x - w / 2 + 0.012, back - 0.05, c.z + h / 2)), bevel=0.01),
        # red top, a dark spine and the reload hatch behind it
        box('LauncherTop', m['remap'], (w - 0.06, l * 0.42, 0.008), (c.x, front + 0.1, c.z + h / 2 + 0.002), bevel=0.003),
        box('LauncherSpine', m['armour'], (0.03, l * 0.75, 0.014), (c.x, c.y - 0.01, c.z + h / 2 + 0.004), bevel=0.003),
        box('ReloadHatch', m['armour'], (w - 0.08, 0.05, 0.01), (c.x, back - 0.075, c.z + h / 2 - 0.004), bevel=0.003),
        *[box(f'LauncherVent{s}{k}', m['dark'], (0.004, 0.035, 0.01), (s * (w / 2 + 0.001), c.y + 0.02 + k * 0.025, c.z + 0.005),
              bevel=0) for s in (-1, 1) for k in range(3)],
        # the trunnions on the pedestal
        *[cylinder(f'Trunnion{s}', m['steel'], 0.018, 0.02, (s * 0.06, c.y + 0.04, c.z - h / 2 - 0.005), rotation=(0, math.pi / 2, 0),
                   segments=10) for s in (-1, 1)],
    ], c), cannon)
    banks = []
    for s, side in ((-1, 'L'), (1, 'R')):
        parts = [box(f'BankFace{s}', m['armour'], (0.088, 0.03, h - 0.012), (s * 0.05, front + 0.012, c.z), bevel=0.005)]
        for k, tx in enumerate(TUBES_X):
            p = Vector((s * tx, front - 0.004, c.z))
            turn = (math.pi / 2, 0, 0)
            parts += [cylinder(f'Tube{s}{k}', m['steel'], 0.0135, 0.014, p, rotation=turn, segments=12, bevel=0.002),
                      cylinder(f'Bore{s}{k}', m['dark'], 0.0095, 0.004, p - Vector((0, 0.006, 0)), rotation=turn, segments=10, bevel=0),
                      cylinder(f'Nose{s}{k}', m['remap'], 0.0075, 0.012, p - Vector((0, 0.004, 0)), rotation=(-math.pi / 2, 0, 0),
                               segments=10, bevel=0, radius2=0.002)]
        bank = kit.parent(kit.merge(f'Pod{side}', parts, (s * 0.05, front, c.z)), cannon)
        flash = kit.parent(nod.flash(m, f'Flash{side}', (s * TUBES_X[1], front - 0.04, c.z), 0.045), cannon)
        banks.append((bank, flash))
    return banks


def build():
    root, body = nod.start('NodStealthTank', 'StealthTank', WALK_SPEED)
    m = nod.materials()
    m['glow_orange'] = kit.material('GlowOrange', kit.srgb('#ff6a20'), 0.3, emission=kit.srgb('#ff5212'), strength=5)
    pods_parts, wheels = [], []
    for s in (-1, 1):
        for end, y in zip(('Front', 'Rear'), POD_Y):
            name = f'Bogie{end}{"L" if s < 0 else "R"}'
            parts, belt, pod_wheels = pod(m, name, s, y)
            pods_parts += parts
            kit.parent(belt, body)
            wheels += [kit.parent(w, body) for w in pod_wheels]
    kit.parent(kit.merge('Bogies', pods_parts), body)
    kit.parent(hull(m), body)
    turret = kit.parent(kit.empty('Turret', MOUNT), body)
    cannon = kit.parent(kit.empty('Cannon', MOUNT), turret)
    banks = launcher(m, cannon)
    nod.camouflage(kit.collection().objects)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.003)
    # Fire: the left bank, then the right one (the game's two shots of a burst)
    hidden = Vector((kit.HIDDEN,) * 3)
    for k, (obj, flash) in enumerate(banks):
        start = k * 6
        kit.keys(flash, 'scale', {0: hidden, start: Vector((1, 1, 1)), start + 2: Vector((1.3, 1.5, 1.3)), start + 4: hidden,
                                  FIRE_FRAMES: hidden}, 'CONSTANT')
        kit.to_track(flash, 'Fire')
        rest = obj.location.copy()
        kick = rest + Vector((0, 0.018, 0))
        kit.keys(obj, 'location', {0: rest, start: rest, start + 2: kick, start + 4: kick, start + 11: rest, FIRE_FRAMES: rest})
        kit.to_track(obj, 'Fire')
        obj.location = rest
        flash.scale = hidden
    flashes = [f for _, f in banks]
    walker.hide(flashes, kit.IDLE_END, 'Idle')
    walker.hide(flashes, WALK_FRAMES, 'Walk')
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Fire': [1, 7]}, scale=1.3, target=(0, -0.02, 0.18))
