"""
Tiberian Fallout – Nod laser turret (NALASR), after Tiberian Sun (in the low, squat
shape Tiberian Sun Rising gives it).

A gun emplacement on one cell: a low hexagonal pad of concrete with wide sloped edges,
dark armour ribs on its corners and a red (house colour) frame round its top; on top a
dark armour deck with seams, a hatch, a junction box with cables and a red lamp on a
post; in the slopes towards the front a vent, a dark plate with red stripes and a
hatch, down the back right one a cable into the ground. In the middle a round dark
pedestal with a red band carries the turning turret: a turntable and a yoke of two
angular cheeks with bearing drums, and between them the gun – a slim chamfered body
with a sight and a capacitor on top, a bigger box at its back (red band, vents, cooling
fins, a lamp) and in front the long slim laser barrel: a finned shroud at its root, a
rod along its underside, a red collar near the muzzle and the emitter with its lens.

Nodes the game uses (see nodstructure.py):
    Turret     the yoke on the pedestal, turning about the vertical
    Cannon     the gun's trunnion between the cheeks, tipped up and down; looks along -Y
    Flash      the flare at the lens, where the beam starts (the game draws the beam)
Other nodes
    Mount      above Turret: brings the turret down onto the pedestal (Build)
    Recoil     inside Cannon, carries the barrel: kicks back a little (Fire)
    LensGlow   on Cannon at the lens: glows softly (Idle)
    LensFlare  on Cannon at the lens: flares up (Fire)
Animations (glTF clips)
    Build    one-shot, 2.2 s: the pad spreads, the pedestal rises out of the deck, the
             deck's fittings grow, the turret is lowered onto the pedestal
    Idle     loop, 2 s: the lens glows softly, the lamp on the gun's back and the one on
             the pad blink
    Fire     one-shot, 0.5 s: the lens flares up, the barrel kicks a little

Run headless:

    blender -b --factory-startup --python blender/NALASR.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). Origin in the
middle of the cell on the ground.
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

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam
HIDDEN = kit.HIDDEN

# the hexagonal pad: corners at ±X, flat sides to the front and the back
PAD_BOTTOM = 0.45       # corner radius on the ground
PAD_TOP = 0.36          # corner radius at the top of the slopes
RIM = 0.06              # height of the slopes
DECK_R = 0.335          # corner radius of the armour deck on top
DECK = 0.076            # the deck's top
PAD_CONCRETE = nb.GREY
HEAD = Vector((0, 0, 0.17))         # the turret's pivot on the pedestal
GUN = Vector((0, -0.01, 0.31))      # the trunnion
BODY_FRONT = GUN.y - 0.12           # the front of the gun body
TIP = Vector((0, BODY_FRONT - 0.35, GUN.z))   # the lens
ALONG = (math.pi / 2, 0, 0)         # cylinders along Y
ACROSS = (0, math.pi / 2, 0)        # cylinders along X
FIRE_FRAMES = 15
BUILD_END = 66


def lerp(a, b, t):
    return a + (b - a) * t


def patch(quad, u0, u1, v0, v1, lift, thick, shear=0.0):
    """Corners of a plate on a face given by `quad` (bottom left, bottom right, top
    right, top left): the part u0..u1 across, v0..v1 up, its top edge shifted by
    `shear` across; lifted off the face by `lift`, `thick` thick."""
    bl, br, tr, tl = (Vector(p) for p in quad)
    normal = (br - bl).cross(tl - bl).normalized()

    def at(u, v):
        return lerp(lerp(bl, br, u), lerp(tl, tr, u), v)
    flat = [at(u0, v0), at(u1, v0), at(u1 + shear, v1), at(u0 + shear, v1)]
    return [p + normal * lift for p in flat] + [p + normal * (lift + thick) for p in flat]


def outward(quad, centre):
    """The quad in the order whose normal points away from `centre`."""
    bl, br, tr, tl = (Vector(p) for p in quad)
    if (br - bl).cross(tl - bl).dot((bl + tr) / 2 - Vector(centre)) < 0:
        return [br, bl, tl, tr]
    return [bl, br, tr, tl]


def corner(k, r, z=None):
    """Corner k of a hexagon of corner radius r (0 at +X, counter-clockwise)."""
    a = math.radians(60 * k)
    p = (r * math.cos(a), r * math.sin(a))
    return p if z is None else Vector((*p, z))


def hexagon(r):
    return [corner(k, r) for k in range(6)]


def slope(k):
    """The pad's sloped face k, between corners k and k + 1, facing out (0 back right,
    1 back, 2 back left, 3 front left, 4 front, 5 front right)."""
    j = (k + 1) % 6
    return outward([corner(k, PAD_BOTTOM, 0), corner(j, PAD_BOTTOM, 0), corner(j, PAD_TOP, RIM), corner(k, PAD_TOP, RIM)], (0, 0, 0))


def rib(name, mat, k, width=0.024, height=0.01):
    """An armour rib over the pad's corner edge k, from the ground to the top."""
    d = Vector((*corner(k, 1), 0))
    side = Vector((-d.y, d.x, 0)) * width / 2
    run = PAD_BOTTOM - PAD_TOP
    normal = Vector((d.x * RIM, d.y * RIM, run)).normalized()
    ends = []
    for r, z in ((PAD_BOTTOM + 0.004, -0.002), (PAD_TOP, RIM - 0.004)):
        p = corner(k, r, z)
        ends += [p - side - normal * 0.012, p + side - normal * 0.012, p + side * 0.6 + normal * height, p - side * 0.6 + normal * height]
    return kit.hexahedron(name, mat, ends, bevel=0.003)


def along_y(name, mat, back, front, y_back, y_front, centre, bevel=0.006):
    """A solid along Y between two cross-sections (outlines of (x, z) round `centre`):
    `back` at centre.y + y_back, `front` at centre.y + y_front."""
    obj = nb.prism(name, mat, back, front, -y_back, -y_front, bevel)
    obj.rotation_euler = (math.pi / 2, 0, 0)
    obj.location = centre
    return obj


def pad(m, root):
    """The concrete pad, its armour (deck, frame, ribs, plates in the slopes) and the
    fittings on the deck; returns the three objects."""
    rim = nb.concrete('Plinth', [
        nb.prism('PlinthRim', m['steel'], hexagon(PAD_BOTTOM), hexagon(PAD_TOP), 0, RIM, bevel=0.006),
    ], root, PAD_CONCRETE)

    parts = [nb.prism('Deck', m['nplate'], hexagon(DECK_R + 0.012), hexagon(DECK_R), RIM - 0.004, DECK, bevel=0.004)]
    # the red frame round the top of the slopes
    r0, r1, z0, z1 = DECK_R + 0.01, PAD_TOP + 0.004, RIM - 0.003, RIM + 0.005
    for k in range(6):
        j = (k + 1) % 6
        parts.append(kit.hexahedron(f'Frame{k}', m['remap'], [
            corner(k, r0, z0), corner(j, r0, z0), corner(j, r1, z0), corner(k, r1, z0),
            corner(k, r0, z1), corner(j, r0, z1), corner(j, r1, z1), corner(k, r1, z1)], bevel=0))
        parts.append(rib(f'Rib{k}', m['armour_dark'], k))
    # front right: a vent; front: a dark plate with red stripes; front left: a hatch
    vent = slope(5)
    parts.append(kit.hexahedron('Vent', m['nplate_dark'], patch(vent, 0.2, 0.8, 0.16, 0.84, 0.0, 0.006), bevel=0.002))
    for n in range(4):
        v = 0.24 + 0.15 * n
        parts.append(kit.hexahedron(f'VentSlat{n}', m['steel'], patch(vent, 0.23, 0.77, v, v + 0.06, 0.004, 0.006), bevel=0))
    front = slope(4)
    parts.append(kit.hexahedron('FrontPlate', m['nplate_dark'], patch(front, 0.14, 0.86, 0.14, 0.86, 0.0, 0.007), bevel=0.002))
    for n in range(3):
        u = 0.3 + 0.16 * n
        parts.append(kit.hexahedron(f'FrontStripe{n}', m['remap'], patch(front, u, u + 0.07, 0.22, 0.78, 0.006, 0.004, shear=0.1), bevel=0))
    hatch = slope(3)
    parts.append(kit.hexahedron('SlopeHatch', m['nplate'], patch(hatch, 0.32, 0.68, 0.18, 0.8, 0.0, 0.007), bevel=0.002))
    parts.append(kit.hexahedron('SlopeHatchGrip', m['steel'], patch(hatch, 0.44, 0.56, 0.5, 0.62, 0.007, 0.006), bevel=0))
    # the cable from the junction box over the back right edge, down the slope into the ground
    box_at = corner(0.5, 0.24, DECK)
    edge = corner(0.5, PAD_TOP * 0.866 + 0.006, RIM + 0.008)
    parts += detail.hose('EdgeCable', m['dark'], corner(0.5, 0.275, DECK + 0.009), corner(0.5, 0.305, DECK + 0.011), edge, 0.009, 4)
    parts += detail.hose('GroundCable', m['dark'], edge, corner(0.5, 0.36, 0.034), corner(0.5, 0.425, -0.012), 0.009, 5)
    armour = kit.merge('PlinthArmour', parts)

    # on the deck: seams, bolts, a hatch, the junction box, the lamp post
    fit = []
    for k in range(6):
        fit += detail.seam(f'Seam{k}', m['seam'], corner(k, DECK_R - 0.014, DECK + 0.001), corner(k, 0.16, DECK + 0.001), 0.006, 0.003)
        fit.append(cylinder(f'Bolt{k}', m['steel'], 0.011, 0.008, corner(k + 0.5, 0.27, DECK + 0.003), segments=8, bevel=0))
    a = math.radians(150)
    at = corner(2.5, 0.235, DECK)
    fit += [
        box('Hatch', m['nplate_dark'], (0.075, 0.09, 0.012), at + Vector((0, 0, 0.004)), bevel=0.003, rotation=(0, 0, a)),
        beam('HatchGrip', m['steel_light'], at + Vector((0.02 * math.sin(a), -0.02 * math.cos(a), 0.012)),
             at + Vector((-0.02 * math.sin(a), 0.02 * math.cos(a), 0.012)), 0.006),
    ]
    fit += [
        box('JunctionBox', m['armour_dark'], (0.05, 0.075, 0.045), box_at + Vector((0, 0, 0.022)), bevel=0.004, rotation=(0, 0, math.radians(30))),
        box('JunctionLid', m['steel'], (0.054, 0.079, 0.008), box_at + Vector((0, 0, 0.047)), bevel=0.002, rotation=(0, 0, math.radians(30))),
        box('JunctionMark', m['remap'], (0.004, 0.04, 0.012), box_at + corner(0.5, 0.027, 0.026), bevel=0, rotation=(0, 0, math.radians(30))),
    ]
    fit += detail.hose('PedestalCable', m['dark'], corner(0.5, 0.21, DECK + 0.01), corner(0.5, 0.16, DECK + 0.006), corner(0.3, 0.12, DECK + 0.019), 0.009, 6)
    fit.append(box('LampPost', m['steel'], (0.026, 0.026, 0.035), corner(0, 0.295, DECK + 0.0175), bevel=0.003))
    fittings = kit.merge('DeckFittings', fit, (0, 0, DECK))
    return rim, armour, fittings


def pedestal(m):
    """The round pedestal in the middle of the deck (with its red band)."""
    z0 = DECK - 0.004
    h = HEAD.z - z0
    parts = [
        nb.lathe('PedestalDrum', m['armour_dark'], [
            (0.13, 0), (0.13, 0.012), (0.112, 0.03), (0.104, 0.034), (0.104, h - 0.016), (0.113, h - 0.009), (0.113, h)],
            (0, 0, z0), segments=24, bevel=0.003),
        cylinder('PedestalBand', m['remap'], 0.107, 0.022, (0, 0, z0 + 0.056), segments=24, bevel=0),
    ]
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        parts.append(cylinder(f'PedestalBolt{k}', m['steel'], 0.009, 0.01, (0.12 * math.cos(a), 0.12 * math.sin(a), z0 + 0.021), segments=6, bevel=0))
    for k in range(6):
        a = 2 * math.pi * k / 6
        parts.append(box(f'PedestalRib{k}', m['armour'], (0.012, 0.012, 0.02), (0.105 * math.cos(a), 0.105 * math.sin(a), z0 + 0.038 + 0.01),
                         bevel=0.002, rotation=(0, 0, a)))
    return kit.merge('Pedestal', parts, (0, 0, z0))


def turret(m, mount):
    """The turning yoke (Turret) and the gun (Cannon → Recoil → Barrel); returns the
    animated parts."""
    yoke = kit.parent(kit.empty('Turret', HEAD), mount)
    z = HEAD.z
    shell = [
        cylinder('Turntable', m['steel'], 0.112, 0.022, HEAD + Vector((0, 0, 0.011)), segments=24, bevel=0.003),
        nb.prism('YokeBase', m['armour'], nb.chamfered(0, 0.005, 0.2, 0.23, 0.055), nb.chamfered(0, 0.005, 0.18, 0.21, 0.05),
                 z + 0.02, z + 0.05, bevel=0.005),
        box('YokeStripe', m['remap'], (0.08, 0.008, 0.012), (0, -0.106, z + 0.035), bevel=0),
    ]
    for x in (-1, 1):
        for y in (-1, 1):
            shell.append(cylinder(f'YokeBolt{x}{y}', m['steel'], 0.009, 0.008, (x * 0.07, 0.005 + y * 0.085, z + 0.052), segments=6, bevel=0))
    zb, zt = z + 0.048, GUN.z + 0.044
    for s in (-1, 1):
        cheek = []
        for x in (0.063, 0.092):
            xt = x - (0.006 if x > 0.07 else 0)
            cheek += [(s * x, GUN.y + 0.085, zb), (s * x, GUN.y - 0.08, zb), (s * xt, GUN.y - 0.036, zt), (s * xt, GUN.y + 0.046, zt)]
        shell += [
            kit.hexahedron(f'Cheek{s}', m['armour_dark'], cheek, bevel=0.005),
            cylinder(f'Bearing{s}', m['steel'], 0.042, 0.022, (s * 0.1, GUN.y, GUN.z), rotation=ACROSS, segments=18, bevel=0.003),
            cylinder(f'BearingCap{s}', m['steel_light'], 0.024, 0.01, (s * 0.113, GUN.y, GUN.z), rotation=ACROSS, segments=12, bevel=0.002),
            box(f'CheekPlate{s}', m['nplate'], (0.006, 0.07, 0.045), (s * 0.093, GUN.y + 0.012, z + 0.085), bevel=0.002),
        ]
    shell += detail.hose('YokeCable', m['dark'], (0.075, GUN.y + 0.1, z + 0.05), (0.11, GUN.y + 0.1, z + 0.11), (0.104, GUN.y + 0.03, GUN.z - 0.04), 0.008)
    kit.parent(kit.merge('Yoke', shell, HEAD), yoke)

    cannon = kit.parent(kit.empty('Cannon', GUN), yoke)
    g = GUN
    body = [
        along_y('Body', m['armour'], nb.chamfered(0, 0, 0.11, 0.085, 0.022), nb.chamfered(0, -0.004, 0.1, 0.07, 0.02), 0.09, -0.12, g),
        along_y('RearBox', m['armour_dark'], nb.chamfered(0, 0.012, 0.12, 0.095, 0.025), nb.chamfered(0, 0.012, 0.135, 0.11, 0.025), 0.225, 0.085, g),
        along_y('RearBand', m['remap'], nb.chamfered(0, 0.012, 0.14, 0.115, 0.027), nb.chamfered(0, 0.012, 0.14, 0.115, 0.027), 0.155, 0.128, g, bevel=0.002),
        *detail.grille('BackVent', m['steel'], m['dark'], g + Vector((0, 0.229, 0.012)), 0.07, 0.05, 'Y', 3, 0.008),
        # a sight on the top left, a capacitor on the top right
        box('Sight', m['armour_dark'], (0.03, 0.06, 0.03), g + Vector((-0.03, -0.035, 0.05)), bevel=0.004),
        box('SightGlass', m['glass'], (0.022, 0.006, 0.016), g + Vector((-0.03, -0.066, 0.052)), bevel=0.001),
        cylinder('Capacitor', m['steel_light'], 0.012, 0.13, g + Vector((0.03, -0.03, 0.047)), rotation=ALONG, segments=10, bevel=0.002),
    ]
    for k, y in enumerate((-0.07, 0.01)):
        body.append(cylinder(f'CapacitorClamp{k}', m['remap'], 0.015, 0.01, g + Vector((0.03, y, 0.047)), rotation=ALONG, segments=10, bevel=0))
    for s in (-1, 1):   # panel seams on the body's sides in front of the cheeks
        body += detail.seam(f'BodySeam{s}', m['seam'], g + Vector((s * 0.051, -0.1, -0.028)), g + Vector((s * 0.051, -0.1, 0.028)), 0.004, 0.004)
    for k in range(3):
        y = 0.17 + 0.02 * k
        body.append(box(f'Fin{k}', m['steel'], (0.07, 0.008, 0.012), g + Vector((0.015, y, 0.067)), bevel=0))
    kit.parent(kit.merge('GunBody', body, GUN), cannon)
    head_light = nb.lamp(m, cannon, 'HeadLamp', g + Vector((-0.045, 0.19, 0.062)), 'red', 52)

    recoil = kit.parent(kit.empty('Recoil', GUN), cannon)
    tube_back = BODY_FRONT + 0.01
    tube_front = TIP.y + 0.02
    parts = [
        cylinder('Shroud', m['armour_dark'], 0.03, 0.08, Vector((0, BODY_FRONT - 0.03, g.z)), rotation=ALONG, segments=16, bevel=0.003),
        cylinder('Tube', m['steel'], 0.016, tube_back - tube_front, Vector((0, (tube_back + tube_front) / 2, g.z)), rotation=ALONG, segments=12, bevel=0),
        beam('Rod', m['steel_light'], Vector((0, BODY_FRONT - 0.06, g.z - 0.024)), Vector((0, TIP.y + 0.09, g.z - 0.024)), 0.008),
        cylinder('Clamp', m['steel'], 0.02, 0.01, Vector((0, BODY_FRONT - 0.16, g.z)), rotation=ALONG, segments=12, bevel=0),
        box('ClampStrut', m['steel'], (0.008, 0.01, 0.014), Vector((0, BODY_FRONT - 0.16, g.z - 0.022)), bevel=0),
        # the collar near the muzzle: a red ring between two steel ones
        cylinder('Collar', m['remap'], 0.031, 0.026, Vector((0, TIP.y + 0.08, g.z)), rotation=ALONG, segments=16, bevel=0.003),
        cylinder('Emitter', m['armour_dark'], 0.024, 0.04, Vector((0, TIP.y + 0.02, g.z)), rotation=ALONG, segments=14, bevel=0.002, radius2=0.018),
        cylinder('Lens', m['lamp_red'], 0.013, 0.006, Vector((0, TIP.y + 0.0, g.z)), rotation=ALONG, segments=14, bevel=0),
    ]
    for k in range(3):
        parts.append(cylinder(f'ShroudFin{k}', m['steel_light'], 0.035, 0.007, Vector((0, BODY_FRONT - 0.018 - 0.022 * k, g.z)), rotation=ALONG, segments=16, bevel=0))
    for k, dy in enumerate((-0.018, 0.018)):
        parts.append(cylinder(f'CollarRing{k}', m['steel_light'], 0.025, 0.007, Vector((0, TIP.y + 0.08 + dy, g.z)), rotation=ALONG, segments=14, bevel=0))
    kit.parent(kit.merge('Barrel', parts, GUN), recoil)
    lens_glow = kit.parent(nb.glow(m, 'LensGlow', TIP - Vector((0, 0.006, 0)), 0.022, 'glow_laser', 1), cannon)
    lens_flare = kit.parent(nb.glow(m, 'LensFlare', TIP - Vector((0, 0.01, 0)), 0.045, 'glow_laser', 1), cannon)
    flash = kit.parent(nb.glow(m, 'Flash', TIP - Vector((0, 0.03, 0)), 0.05, 'glow_laser'), cannon)
    return recoil, flash, lens_glow, lens_flare, head_light


def build():
    root = nb.start('NodLaser', 'NodLaserTurret', BUILD_END)
    m = nb.materials()
    rim, armour, fittings = pad(m, root)
    stand = pedestal(m)
    for obj in (rim, armour, fittings, stand):
        kit.parent(obj, root)
    pad_light = nb.lamp(m, root, 'PlinthLamp', corner(0, 0.295, DECK + 0.035), 'red', 36)
    mount = kit.parent(kit.empty('Mount', HEAD), root)
    recoil, flash, lens_glow, lens_flare, head_light = turret(m, mount)

    # Build: the pad spreads, the pedestal rises, the fittings grow, the turret comes down
    for obj in (rim, armour):
        s = obj.scale.copy()
        kit.keys(obj, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 10: Vector((1.04, 1.04, 1)), 13: s})
    nb.rise(stand, 14, 14, 0.12)
    nb.grow_z(fittings, 24, 10)
    # the turret waits under the ground, then is lowered from above (never scaled: the
    # lamps and glows under it blink in Idle)
    kit.keys(mount, 'location', {0: HEAD - Vector((0, 0, 1.5)), 31: HEAD - Vector((0, 0, 1.5))}, 'CONSTANT')
    kit.keys(mount, 'location', {32: HEAD + Vector((0, 0, 0.45)), 46: HEAD - Vector((0, 0, 0.004)), 49: HEAD})
    nb.all_to_build()

    # Idle: the lens glows softly, the lamps blink
    nb.pulse(lens_glow, kit.IDLE_END, 0.75, 1.1)
    kit.to_track(lens_glow, 'Idle')
    nb.blinking([(head_light, kit.flashes((0, 8), (30, 8))), (pad_light, kit.flashes((15, 10)))])

    # Fire: the lens flares, the barrel kicks
    nb.flash_keys(flash, FIRE_FRAMES, 1, 7)
    kit.to_track(flash, 'Fire')
    hidden = Vector((HIDDEN,) * 3)
    kit.keys(lens_flare, 'scale', {0: hidden, 1: Vector((1.5,) * 3), 6: Vector((1.2,) * 3), 12: hidden, FIRE_FRAMES: hidden}, 'LINEAR')
    kit.to_track(lens_flare, 'Fire')
    rest = recoil.location.copy()
    kit.keys(recoil, 'location', {0: rest, 2: rest + Vector((0, 0.02, 0)), 9: rest, FIRE_FRAMES: rest})
    kit.to_track(recoil, 'Fire')

    recoil.location = rest
    mount.location = HEAD
    flash.scale = lens_flare.scale = (HIDDEN,) * 3
    lens_glow.scale = (1, 1, 1)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NALASR', {'Build': [14, 30, 44, 66], 'Idle': [0], 'Fire': [3, FIRE_FRAMES]}, ortho=1.3, target=(0, -0.03, 0.18))
