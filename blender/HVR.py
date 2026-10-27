"""
Tiberian Fallout – GDI Hover MLRS (HVR), after Tiberian Sun.

A flat hovercraft: a low, wedge-nosed hull on a dark rubber skirt, two long
pontoons along its flanks whose fronts step down in layered plates, two ducted
thrust fans at the back with their rudders. On a turret ring in the middle sits the
launcher: a low turret with a target-laser eye in front, carrying two box-shaped
rocket pods on its cheeks, four tubes each with red warheads. Under the skirt the
air cushion glows pale blue. The hull, pontoons, turret and pods are in the light
camouflage of the buildings, tinted with the house colour in the game
(GAPILE.camo_material); stripes on the pontoons and bands on the pods are in the
house colour.

Nodes the game uses: "Turret" (turns about its vertical towards the target),
"Cannon" (the pods, tipped up and down), "Flash0"/"Flash1" (the pods' muzzles,
used in turn). Clips:
    Idle   loop, 2 s: hovering on the spot, the hull bobs, the cushion glows, the
           fans turn slowly
    Walk   loop, 1 s: gliding, the hull leans back a little and sways, the fans
           race, the cushion glows brighter; the root's walkSpeed (glTF extras) is
           the speed the sway is made for (nothing touches the ground)
    Fire   once, 1 s: both pods fire a rocket, flashes and a kick back

Run headless:

    blender -b --factory-startup --python blender/HVR.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'HVR.glb')
BLEND = os.path.join(HERE, 'HVR.blend')

WALK_FRAMES = 30
WALK_SPEED = 0.8                    # cells per second the glide is made for
FIRE_FRAMES = 30
LIFT = 0.07                         # the skirt's bottom over the ground
DECK = 0.22
TURRET = Vector((0, 0.04, DECK))
LAUNCHER = Vector((0, 0.06, 0.33))  # the pods' trunnion
POD_X = 0.14
FANS = ((-0.12, 0.41, 0.2), (0.12, 0.41, 0.2))
FAN_RADIUS = 0.075
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
ALONG_Y = (math.pi / 2, 0, 0)


def materials():
    m = nod.materials()
    m.update({
        'glass': material('Windscreen', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#3a6a96'), strength=0.6),
        'skirt': material('Skirt', srgb('#2a2926'), 0.9, 0.05),
        'warhead': material('Warhead', srgb('#b3261c'), 0.45, 0.3),
        'cushion': material('HoverGlow', (0, 0, 0), 1.0, emission=srgb('#8fd6ff'), strength=3, alpha=0.3),
        'laser': material('LaserEye', srgb('#ff3020'), 0.2, emission=srgb('#ff2a10'), strength=10),
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
    z0 = LIFT + 0.04
    parts = [
        kit.hexahedron('Hull', m['sand'], (
            (-0.17, -0.36, z0), (0.17, -0.36, z0), (0.17, 0.42, z0), (-0.17, 0.42, z0),
            (-0.16, -0.2, DECK), (0.16, -0.2, DECK), (0.16, 0.41, DECK), (-0.16, 0.41, DECK)), bevel=0.012),
    ]
    for s in (-1, 1):
        x0, x1 = s * 0.16, s * 0.29
        parts += [
            kit.hexahedron(f'Pontoon{s}', m['sand'], (
                (x0, -0.34, z0), (x1, -0.34, z0), (x1, 0.42, z0), (x0, 0.42, z0),
                (x0, -0.28, DECK - 0.02), (x1 - s * 0.02, -0.28, DECK - 0.04), (x1 - s * 0.02, 0.41, DECK - 0.04), (x0, 0.41, DECK - 0.02)),
                bevel=0.012),
            kit.hexahedron(f'PontoonNose{s}', m['sand'], (
                (x0 + s * 0.005, -0.46, z0 - 0.01), (x1 - s * 0.005, -0.46, z0 - 0.01), (x1 - s * 0.005, -0.33, z0), (x0 + s * 0.005, -0.33, z0),
                (x0 + s * 0.005, -0.38, DECK - 0.04), (x1 - s * 0.02, -0.38, DECK - 0.06), (x1 - s * 0.02, -0.3, DECK - 0.05),
                (x0 + s * 0.005, -0.3, DECK - 0.03)), bevel=0.01),
        ]
    return camo(kit.merge('HullShell', parts), root)


def hull_details(m):
    z0 = LIFT + 0.04
    parts = [
        # the skirt round the bottom
        kit.hexahedron('Skirt', m['skirt'], (
            (-0.27, -0.42, LIFT), (0.27, -0.42, LIFT), (0.27, 0.42, LIFT), (-0.27, 0.42, LIFT),
            (-0.29, -0.45, z0 + 0.005), (0.29, -0.45, z0 + 0.005), (0.29, 0.43, z0 + 0.005), (-0.29, 0.43, z0 + 0.005)), bevel=0.012),
        # the cockpit on the nose: a sloped canopy, a hatch
        kit.hexahedron('Cockpit', m['sand_light'], (
            (-0.1, -0.3, DECK - 0.04), (0.1, -0.3, DECK - 0.04), (0.1, -0.14, DECK), (-0.1, -0.14, DECK),
            (-0.08, -0.24, DECK + 0.03), (0.08, -0.24, DECK + 0.03), (0.08, -0.15, DECK + 0.035), (-0.08, -0.15, DECK + 0.035)), bevel=0.008),
        kit.hexahedron('Canopy', m['glass'], (
            (-0.085, -0.297, DECK - 0.03), (0.085, -0.297, DECK - 0.03), (0.085, -0.29, DECK - 0.03), (-0.085, -0.29, DECK - 0.03),
            (-0.07, -0.245, DECK + 0.03), (0.07, -0.245, DECK + 0.03), (0.07, -0.238, DECK + 0.03), (-0.07, -0.238, DECK + 0.03)), bevel=0),
        *detail.grille('DeckVent', m['steel'], m['dark'], (0, 0.3, DECK + 0.004), 0.16, 0.08, 'Z', 6, 0.008),
        beam('Antenna', m['steel'], (-0.12, 0.32, DECK), (-0.14, 0.38, DECK + 0.32), 0.006),
        cylinder('AntennaBase', m['dark'], 0.012, 0.02, (-0.12, 0.32, DECK + 0.008), segments=8, bevel=0),
        box('Stowage', m['olive'], (0.1, 0.05, 0.035), (0.09, 0.3, DECK + 0.02), bevel=0.008),
    ]
    for s in (-1, 1):
        parts += [
            kit.hexahedron(f'PontoonStripe{s}', m['remap'], (
                (s * 0.18, -0.24, DECK - 0.021), (s * 0.26, -0.24, DECK - 0.036), (s * 0.26, 0.38, DECK - 0.036), (s * 0.18, 0.38, DECK - 0.021),
                (s * 0.18, -0.24, DECK - 0.013), (s * 0.26, -0.24, DECK - 0.028), (s * 0.26, 0.38, DECK - 0.028), (s * 0.18, 0.38, DECK - 0.013)),
                bevel=0.002),
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.225, -0.41, 0.15), (0, -1, 0.6), 0.014),
            *detail.rivets(f'PontoonRivets{s}', m['steel_light'], (s * 0.29, -0.28, z0 + 0.03), (s * 0.29, 0.38, z0 + 0.03), 8, axis='X'),
            *detail.grille(f'SideIntake{s}', m['steel'], m['dark'], (s * 0.22, 0.12, DECK - 0.03), 0.06, 0.12, 'Z', 5, 0.006),
            box(f'SkirtBolt{s}', m['steel'], (0.012, 0.6, 0.012), (s * 0.285, 0.0, z0), bevel=0.003),
        ]
    for k, (x, y, z) in enumerate(FANS):
        c = Vector((x, y, z))
        parts += [
            # the duct round the fan, its pylon onto the deck, the rudder behind
            shell(f'Duct{k}', m['sand_light'], FAN_RADIUS + 0.002, 0.016, y - 0.04, y + 0.04, (x, z), 2 * math.pi, 24),
            cylinder(f'DuctBand{k}', m['remap'], FAN_RADIUS + 0.021, 0.018, c + Vector((0, 0.02, 0)), rotation=ALONG_Y, segments=24, bevel=0),
            cylinder(f'DuctBack{k}', m['dark'], FAN_RADIUS + 0.004, 0.006, c - Vector((0, 0.035, 0)), rotation=ALONG_Y, segments=24, bevel=0),
            box(f'Pylon{k}', m['steel'], (0.04, 0.06, z - DECK), Vector((x, y - 0.02, (z + DECK) / 2 - 0.03)), bevel=0.004),
            box(f'Rudder{k}', m['steel_light'], (0.008, 0.04, 2 * FAN_RADIUS + 0.02), c + Vector((0, 0.06, 0)), bevel=0.002),
            beam(f'RudderPost{k}', m['steel'], c + Vector((0, 0.04, -FAN_RADIUS - 0.015)), c + Vector((0, 0.06, -FAN_RADIUS - 0.015)), 0.012),
        ]
        parts += detail.lamp(f'TailLight{k}', m['dark'], m['lamp_red'], (x * 2.0, 0.425, 0.12), (0, 1, 0), 0.011)
    return kit.merge('HullDetails', parts)


def fan(m, k):
    """A fan in its duct turning about y; origin on its hub."""
    c = Vector(FANS[k])
    parts = [cylinder(f'FanHub{k}', m['steel_light'], 0.02, 0.05, c, rotation=ALONG_Y, segments=12)]
    for j in range(6):
        a = 2 * math.pi * j / 6
        d = Vector((math.cos(a), 0, math.sin(a)))
        blade = box(f'FanBlade{k}{j}', m['steel'], (0.024, 0.006, FAN_RADIUS - 0.022), c + d * (FAN_RADIUS / 2 + 0.008), bevel=0)
        blade.rotation_mode = 'QUATERNION'
        blade.rotation_quaternion = d.to_track_quat('Z', 'Y')
        parts.append(blade)
    return kit.merge(f'Fan{k}', parts, c)


def cushion(m):
    """The glowing air cushion under the skirt: two flat ovals, the outer one just
    peeking out round the skirt."""
    parts = []
    for name, (w, l), z in (('CushionGlow', (0.64, 0.98), LIFT - 0.008), ('CushionCore', (0.5, 0.82), LIFT - 0.028)):
        disc = cylinder(name, m['cushion'], 0.5, 0.003, (0, -0.01, z), segments=32, bevel=0)
        disc.scale = (w, l, 1)
        parts.append(disc)
    return kit.merge('Cushion', parts, (0, 0, LIFT))


# --------------------------------------------------------------------------- launcher

def launcher(m, root, body):
    """The turret with the two pods on the Cannon; returns (pods, flashes)."""
    turn = kit.parent(kit.empty('Turret', TURRET), body)
    top = 0.31
    kit.parent(camo(kit.merge('TurretShell', [kit.hexahedron('TurretShell', m['sand'], (
        (-0.1, -0.11, DECK + 0.008), (0.1, -0.11, DECK + 0.008), (0.1, 0.16, DECK + 0.008), (-0.1, 0.16, DECK + 0.008),
        (-0.08, -0.06, top), (0.08, -0.06, top), (0.08, 0.14, top), (-0.08, 0.14, top)), bevel=0.012)], TURRET), root), turn)
    kit.parent(kit.merge('TurretDetails', [
        cylinder('TurretRing', m['steel'], 0.13, 0.024, (0, TURRET.y, DECK + 0.008), segments=24),
        cylinder('TurretRingTop', m['steel_light'], 0.115, 0.006, (0, TURRET.y, DECK + 0.022), segments=24, bevel=0),
        # the target laser's eye in front, a sensor box on the roof
        box('EyeHousing', m['steel'], (0.05, 0.03, 0.04), (0, -0.095, top - 0.04), bevel=0.006),
        *detail.lamp('Eye', m['dark'], m['laser'], (0, -0.112, top - 0.04), (0, -1, 0), 0.012),
        box('Sensor', m['steel'], (0.06, 0.06, 0.03), (-0.02, 0.07, top + 0.015), bevel=0.006),
        box('SensorGlass', m['glass'], (0.04, 0.008, 0.016), (-0.02, 0.038, top + 0.018), bevel=0.002),
        cylinder('Hatch', m['steel'], 0.03, 0.014, (0.04, 0.06, top + 0.005), segments=14),
        cylinder('Trunnion', m['steel_light'], 0.02, 2 * POD_X - 0.02, LAUNCHER, rotation=(0, math.pi / 2, 0), segments=12),
    ], TURRET), turn)

    pivot = kit.parent(kit.empty('Cannon', LAUNCHER), turn)
    pods, flashes = [], []
    for k, s in enumerate((-1, 1)):
        c = Vector((s * POD_X, LAUNCHER.y - 0.02, LAUNCHER.z + 0.01))
        front = c.y - 0.12
        shell = camo(kit.merge(f'PodShell{k}', [kit.hexahedron(f'PodShell{k}', m['sand'], (
            (c.x - 0.055, front, c.z - 0.05), (c.x + 0.055, front, c.z - 0.05), (c.x + 0.055, c.y + 0.12, c.z - 0.05),
            (c.x - 0.055, c.y + 0.12, c.z - 0.05),
            (c.x - 0.055, front, c.z + 0.05), (c.x + 0.055, front, c.z + 0.05), (c.x + 0.05, c.y + 0.1, c.z + 0.06),
            (c.x - 0.05, c.y + 0.1, c.z + 0.06)), bevel=0.01)], c), root)
        pod = kit.parent(kit.empty(f'Pod{k}', c), pivot)
        kit.parent(shell, pod)
        parts = [
            box(f'PodFace{k}', m['steel'], (0.1, 0.012, 0.09), (c.x, front - 0.004, c.z), bevel=0.004),
            box(f'PodBand{k}', m['remap'], (0.114, 0.03, 0.104), (c.x, c.y + 0.04, c.z + 0.002), bevel=0.003),
            box(f'PodArm{k}', m['steel'], (0.04, 0.08, 0.03), (s * (POD_X - 0.06), c.y + 0.02, LAUNCHER.z), bevel=0.004),
            *detail.rivets(f'PodRivets{k}', m['steel_light'], (c.x + s * 0.057, c.y - 0.08, c.z), (c.x + s * 0.057, c.y + 0.08, c.z), 4, axis='X'),
        ]
        for i in range(2):
            for j in range(2):
                t = Vector((c.x - 0.024 + 0.048 * i, front - 0.006, c.z - 0.022 + 0.044 * j))
                parts += [cylinder(f'Tube{k}{i}{j}', m['dark'], 0.019, 0.012, t, rotation=ALONG_Y, segments=12, bevel=0),
                          cylinder(f'Warhead{k}{i}{j}', m['warhead'], 0.014, 0.02, t - Vector((0, 0.002, 0)), rotation=ALONG_Y,
                                   segments=12, bevel=0, radius2=0.004)]
        kit.parent(kit.merge(f'PodDetails{k}', parts, c), pod)
        tip = Vector((c.x, front - 0.04, c.z))
        flashes.append(kit.parent(nod.flash(m, f'Flash{k}', tip, 0.045), pivot))
        pods.append(pod)
    return pods, flashes


# --------------------------------------------------------------------------- clips

def clips(body, fans, glow, pods, flashes):
    one, hidden = Vector((1, 1, 1)), Vector((kit.HIDDEN,) * 3)
    n = kit.IDLE_END
    # Idle: bobbing on the cushion, fans slow, glow breathing
    kit.keys(body, 'location', {f: Vector((0, 0, 0.008 * math.sin(2 * math.pi * f / n))) for f in range(0, n + 1, 3)}, 'LINEAR')
    kit.keys(body, 'rotation_euler', {f: Vector((0.01 * math.sin(2 * math.pi * f / n + 1), 0.008 * math.sin(4 * math.pi * f / n), 0))
                                      for f in range(0, n + 1, 3)}, 'LINEAR')
    kit.to_track(body, 'Idle')
    kit.keys(glow, 'scale', {f: Vector((1, 1, 1)) * (0.9 + 0.1 * math.sin(4 * math.pi * f / n) ** 2) for f in range(0, n + 1, 5)}, 'LINEAR')
    kit.to_track(glow, 'Idle')
    # Walk: gliding, leaning back, swaying, fans fast, glow brighter (wider)
    w = WALK_FRAMES
    kit.keys(body, 'location', {f: Vector((0, 0, 0.012 + 0.006 * math.sin(2 * math.pi * f / w))) for f in range(0, w + 1, 2)}, 'LINEAR')
    kit.keys(body, 'rotation_euler', {f: Vector((0.035 + 0.01 * math.sin(2 * math.pi * f / w), 0.015 * math.sin(2 * math.pi * f / w + 1), 0))
                                      for f in range(0, w + 1, 2)}, 'LINEAR')
    kit.to_track(body, 'Walk')
    kit.keys(glow, 'scale', {f: Vector((1.06, 1.08, 1)) * (1.0 + 0.06 * math.sin(4 * math.pi * f / w) ** 2) for f in range(0, w + 1, 3)}, 'LINEAR')
    kit.to_track(glow, 'Walk')
    # Fire: the left pod, then the right one; each kicks back and flashes
    for k, (pod, flash) in enumerate(zip(pods, flashes)):
        rest = pod.location.copy()
        t = 6 * k
        kick = rest + Vector((0, 0.03, 0))
        kit.keys(pod, 'location', {0: rest, t: rest, t + 2: kick, t + 5: kick, t + 14: rest, FIRE_FRAMES: rest})
        kit.to_track(pod, 'Fire')
        frames = {0: hidden, t: Vector((1, 1, 1)), t + 2: Vector((1.3, 1.6, 1.3)), t + 4: hidden, FIRE_FRAMES: hidden}
        if t == 0:
            frames[0] = Vector((1, 1, 1))
        kit.keys(flash, 'scale', frames, 'CONSTANT')
        kit.to_track(flash, 'Fire')
        walker.hide([flash], n, 'Idle')
        walker.hide([flash], w, 'Walk')
        pod.location, flash.scale = rest, hidden
    body.location, body.rotation_euler, glow.scale = (0, 0, 0), (0, 0, 0), one
    for f in fans:
        f.rotation_euler = (0, 0, 0)


def build():
    root, body = nod.start('GDIHoverMLRS', 'HoverMLRS', WALK_SPEED)
    m = materials()
    kit.parent(hull(m, root), body)
    kit.parent(hull_details(m), body)
    fans = [kit.parent(fan(m, k), body) for k in range(len(FANS))]
    glow = kit.parent(cushion(m), body)
    pods, flashes = launcher(m, root, body)
    kit.bake_camo(512)
    clips(body, fans, glow, pods, flashes)
    # the fans turn about y (nod.spin turns about x)
    for obj in fans:
        kit.keys(obj, 'rotation_euler', {f: Vector((0, 2 * math.pi * f / kit.IDLE_END, 0)) for f in range(0, kit.IDLE_END + 1, 2)}, 'LINEAR')
        kit.to_track(obj, 'Idle')
        kit.keys(obj, 'rotation_euler', {f: Vector((0, 6 * math.pi * f / WALK_FRAMES, 0)) for f in range(0, WALK_FRAMES + 1)}, 'LINEAR')
        kit.to_track(obj, 'Walk')
        obj.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Walk': [8], 'Fire': [1, 7]}, scale=1.5, target=(0, 0, 0.22))
