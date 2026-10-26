"""
Tiberian Fallout – GDI Tiberium refinery (PROC), after Tiberian Sun.

A wide round plant (foundation 4 × 3 cells): a tall, sloped skirt in a crown of
house-colour ribs, with a dark deck on top and a hopper in its middle. The processing
tower with its gas burnoff stands at the back, two smaller stacks on the deck, a
spherical storage tank at the back right. The plant stands on a light concrete pad
whose front edge runs on slanting past it. Towards the bottom right of the screen the
skirt is open: a gate cut square into it, framed in the house colour,
all black inside, that the harvester dumps its Tiberium through. In front of it the
bay in hazard stripes, where the harvester parks.

The bay is the empty node Dock (on the pad, its -Y axis pointing away from the
plant: the way the harvester faces when it has backed up to the opening).

Materials as for the barracks (see GAPILE.py): Camo_* is the baked desert camouflage,
Remap the house colour, Lamp* emissive, Glow* additive (lights, flames, Tiberium).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 3.2 s: the pad spreads, the skirt rises out of the ground and
             puts up its ribs, the gate's frame appears, the tower rises, the stacks grow,
             the tank appears, the lights come on
    Idle     loop, 2 s: the burnoff flames flicker, the beacons blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    Blender -b --factory-startup --python blender/PROC.py [-- --preview 0,48,96 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -2 … 2 and y -1.5 … 1.5; seen in the game, -X is the left and +X the right.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script

kit.COLLECTION = 'GDIRefinery'
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'PROC.glb')
BLEND = os.path.join(HERE, 'PROC.blend')

BUILD_END = 96
IDLE_END = kit.IDLE_END
kit.BUILD_END = BUILD_END  # the export shows the finished plant

PAD = 0.03                              # top of the concrete pad
FOOTING = PAD + 0.012                   # top of the dark footing ring under the plant
DISH = Vector((-0.55, 0.0, 0))          # centre of the round plant, in the middle row of cells
# the skirt from its foot up to the deck: (radius, height)
SKIRT = ((1.3, 0.0), (1.3, 0.12), (0.68, 0.72), (0.66, 0.74))
DECK = 0.74                             # top of the skirt, where the deck lies
DECK_RADIUS = 0.6
RIBS = 18
DOCK_DIR = Vector((1.0, 0, 0))                      # from the plant to the dock, square to the cells
DOCK_ANGLE = math.atan2(DOCK_DIR.y, DOCK_DIR.x)
BAY = (0.95, 0.85)                                  # length (along DOCK_DIR) and width
GATE = (0.36, 0.56)                                 # the opening in the skirt: half width, height
PIT = 0.68                                          # its back wall, distance from DISH
DOCK = DISH + DOCK_DIR * (SKIRT[0][0] + BAY[0] / 2 + 0.02)   # middle of the bay, right in front of the gate
TOWER = DISH + Vector((-0.6, 0.62, 0.35))           # processing tower, at the back (its foot inside the skirt)
TANK = Vector((0.55, 0.78, 0))                      # storage tank, back right
STACKS = ((DISH + Vector((0.12, -0.18, 0)), 0.5), (DISH + Vector((0.28, 0.12, 0)), 0.36))

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'deck': material('Deck', srgb('#262c38'), 0.6, 0.4),
        'copper': material('Copper', srgb('#8a5a3c'), 0.45, 0.6),
        'hazard': material('Hazard', srgb('#e2a21c'), 0.6),
        'flame': material('GlowFlame', (0, 0, 0), 1.0, emission=srgb('#ff8a1e'), strength=5, alpha=0.7),
    })
    return m


def lathe(name, mat, profile, location, segments=48, bevel=0.0):
    """Surface of revolution from (radius, height) points, bottom to top, capped."""
    def build(bm):
        rings = []
        for r, z in profile:
            rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z))
                          for a in (2 * math.pi * i / segments for i in range(segments))])
        for lower, upper in zip(rings, rings[1:]):
            for i in range(segments):
                j = (i + 1) % segments
                bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
        bm.faces.new(rings[0])
        bm.faces.new(rings[-1])

    obj = kit.mesh_object(name, build)
    obj.location = location
    return kit.finish(obj, mat, bevel)


def skirt_height(r):
    """Height of the skirt's surface at a distance r from DISH."""
    for (r0, z0), (r1, z1) in zip(SKIRT, SKIRT[1:]):
        if min(r0, r1) <= r <= max(r0, r1) and r0 != r1:
            return z0 + (z1 - z0) * (r - r0) / (r1 - r0)
    return SKIRT[-1][1] if r < SKIRT[-1][0] else SKIRT[0][1]


def flat(d, r, z):
    """The point at distance r from DISH in direction d, at height z."""
    return DISH + d * r + Vector((0, 0, z))


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


# --------------------------------------------------------------------------- parts

def pad(m):
    """Light concrete pad under the plant and the dock, its front edge running on
    slanting past the plant, the corners chamfered, with the bay in hazard stripes; a
    dark footing ring under the plant."""
    outline = [(-1.4, -1.15), (-1.05, -1.47), (1.6, -1.47), (1.97, -1.1), (1.97, 0.55), (1.5, 1.02), (0.3, 1.02)]

    def build(bm):
        low = [bm.verts.new((x, y, 0)) for x, y in outline]
        top = [bm.verts.new((x, y, PAD)) for x, y in outline]
        bm.faces.new(low[::-1])
        bm.faces.new(top)
        for k in range(len(outline)):
            j = (k + 1) % len(outline)
            bm.faces.new((low[k], low[j], top[j], top[k]))

    parts = [
        kit.finish(kit.mesh_object('PadSlab', build), m['concrete'], 0.008),
        # on top of the pad, not level with it (the surfaces would flicker into each other)
        cylinder('Footing', m['concrete_dark'], SKIRT[0][0] + 0.06, FOOTING, DISH + Vector((0, 0, FOOTING / 2)), segments=48, bevel=0.005),
    ]
    # the bay: a dark plate with bars across it, like a ramp's warning stripes
    length, width = BAY
    across = Vector((-DOCK_DIR.y, DOCK_DIR.x, 0))
    parts.append(box('BayPlate', m['dark'], (length, width, 0.008), DOCK + Vector((0, 0, PAD + 0.004)), bevel=0, rotation=(0, 0, DOCK_ANGLE)))
    for k in range(7):
        along = -length / 2 + (k + 0.5) * length / 7
        parts.append(box(f'BayStripe{k}', m['hazard'], (length / 14, width - 0.04, 0.01),
                         DOCK + DOCK_DIR * along + Vector((0, 0, PAD + 0.005)), bevel=0, rotation=(0, 0, DOCK_ANGLE + math.radians(14))))
    for s in (-1, 1):  # kerbs along the sides
        parts.append(box(f'BayKerb{s}', m['steel'], (length, 0.035, 0.03), DOCK + across * s * (width / 2 + 0.02) + Vector((0, 0, PAD + 0.015)),
                         bevel=0.004, rotation=(0, 0, DOCK_ANGLE)))
    return kit.merge('Pad', parts, DOCK)


def gate_cut(obj, cutter):
    """Cuts the gate out of `obj` (boolean, applied)."""
    mod = obj.modifiers.new('Gate', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    return kit.bake_modifiers(obj)


def skirt(m, root):
    """The sloped skirt (camouflage) with the gate cut into it, its deck and the hopper."""
    cutter = box('GateCutter', m['dark'], (2, 2 * GATE[0], GATE[1] + 0.2), flat(DOCK_DIR, PIT + 1, (GATE[1] - 0.2) / 2), bevel=0)
    shell = gate_cut(camo(lathe('Skirt', m['sand'], SKIRT, DISH, 48), root), cutter)
    band = gate_cut(cylinder('SkirtBand', m['steel_light'], SKIRT[0][0] + 0.01, 0.03, DISH + Vector((0, 0, 0.05)), segments=48, bevel=0), cutter)
    bpy.data.objects.remove(cutter, do_unlink=True)
    parts = [band,
        cylinder('DeckPlate', m['deck'], DECK_RADIUS, 0.03, DISH + Vector((0, 0, DECK + 0.015)), segments=48, bevel=0.004),
        cylinder('DeckRim', m['remap'], SKIRT[-1][0] + 0.03, 0.035, DISH + Vector((0, 0, DECK - 0.005)), segments=48, bevel=0.003),
        cylinder('Hopper', m['steel'], 0.2, 0.08, DISH + Vector((0, 0, DECK + 0.07)), segments=24, radius2=0.25),
        cylinder('HopperHole', m['dark'], 0.21, 0.01, DISH + Vector((0, 0, DECK + 0.111)), segments=24, bevel=0),
    ]
    # panel seams on the deck
    for k in range(8):
        a = math.pi / 8 + k * math.pi / 4
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(beam(f'DeckSeam{k}', m['steel'], flat(d, 0.27, DECK + 0.032), flat(d, DECK_RADIUS - 0.03, DECK + 0.032), 0.012, 0.006))
    return shell, kit.merge('Deck', parts, DISH)


def ribs(m):
    """House-colour ribs standing on the skirt, from its foot up to the deck; the
    dock's way is left free. Each rib's origin is its foot (it pops up from there)."""
    out = []
    for k in range(RIBS):
        a = 2 * math.pi * (k + 0.5) / RIBS
        if abs(math.remainder(a - DOCK_ANGLE, 2 * math.pi)) < 0.32:
            continue
        d = Vector((math.cos(a), math.sin(a), 0))
        foot = flat(d, SKIRT[0][0] + 0.07, 0)
        parts = [
            beam(f'Rib{k}', m['remap'], flat(d, SKIRT[0][0] + 0.06, 0.08), flat(d, SKIRT[-1][0] + 0.02, DECK + 0.015), 0.065, 0.06),
            box(f'RibFoot{k}', m['remap'], (0.12, 0.05, 0.1), foot + Vector((0, 0, 0.05)), bevel=0.008, rotation=(0, 0, a)),
        ]
        out.append(kit.merge(f'Rib{k}', parts, foot))
    return out


def tower(m, root):
    """Processing tower: a camouflaged base with a gallery, the stack on top with house
    colour bands; returns (base, stack, burner position)."""
    base = camo(lathe('TowerBase', m['sand'], ((0.27, 0.0), (0.27, 0.12), (0.22, 0.6), (0.2, 0.66)), TOWER, 32), root)
    top = TOWER + Vector((0, 0, 1.32))
    parts = [
        cylinder('Gallery', m['grating'], 0.27, 0.025, TOWER + Vector((0, 0, 0.67)), segments=32, bevel=0.003),
        cylinder('TowerHut', m['copper'], 0.15, 0.16, TOWER + Vector((0.04, -0.04, 0.76)), segments=20),
        cylinder('Stack', m['steel_light'], 0.085, 0.62, TOWER + Vector((0, 0, 1.0)), segments=20),
        cylinder('StackCap', m['steel'], 0.1, 0.04, top - Vector((0, 0, 0.01)), segments=20),
        cylinder('StackHole', m['dark'], 0.07, 0.01, top + Vector((0, 0, 0.012)), segments=20, bevel=0),
        # a thin second flue beside it
        cylinder('Flue', m['steel'], 0.035, 0.75, TOWER + Vector((0.14, 0.1, 0.9)), segments=12),
        cylinder('FlueCap', m['copper'], 0.045, 0.03, TOWER + Vector((0.14, 0.1, 1.28)), segments=12),
    ]
    for i, z in enumerate((0.82, 1.02, 1.2)):
        parts.append(cylinder(f'StackBand{i}', m['remap'], 0.092, 0.035, TOWER + Vector((0, 0, z)), segments=20, bevel=0))
    for k in range(12):  # railing round the gallery
        a = 2 * math.pi * k / 12
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(beam(f'Post{k}', m['steel_light'], TOWER + d * 0.26 + Vector((0, 0, 0.68)), TOWER + d * 0.26 + Vector((0, 0, 0.76)), 0.008))
    parts.append(cylinder('Railing', m['steel_light'], 0.265, 0.012, TOWER + Vector((0, 0, 0.76)), segments=32, bevel=0))
    # pipes from the tower down onto the deck
    for i, s in enumerate((-0.08, 0.08)):
        side = Vector((-0.62, 0.62, 0)).normalized()
        across = Vector((-side.y, side.x, 0))
        start = TOWER - side * 0.2 + across * s + Vector((0, 0, 0.45))
        bend = DISH + side * 0.5 + across * s + Vector((0, 0, DECK + 0.2))
        end = DISH + side * 0.3 + across * s + Vector((0, 0, DECK + 0.04))
        parts += [beam(f'Pipe{i}', m['copper'], start, bend, 0.04), beam(f'PipeDown{i}', m['copper'], bend, end, 0.04)]
    return base, kit.merge('Tower', parts, TOWER), top + Vector((0, 0, 0.06))


def stack(m, i, foot, height):
    """A thin stack on the deck; origin at its foot (it grows from there)."""
    parts = [
        cylinder(f'DeckStack{i}', m['steel_light'], 0.045, height, foot + Vector((0, 0, height / 2)), segments=14),
        cylinder(f'DeckStackFoot{i}', m['copper'], 0.07, 0.08, foot + Vector((0, 0, 0.04)), segments=14),
        cylinder(f'DeckStackBand{i}', m['remap'], 0.048, 0.03, foot + Vector((0, 0, height * 0.6)), segments=14, bevel=0),
        cylinder(f'DeckStackCap{i}', m['steel'], 0.055, 0.03, foot + Vector((0, 0, height)), segments=14),
    ]
    return kit.merge(f'DeckStack{i}', parts, foot)


def tank(m):
    """Spherical storage tank on a ring of legs, a pipe to the plant; origin at its foot."""
    centre = TANK + Vector((0, 0, PAD + 0.36))
    parts = [
        sphere('Tank', m['copper'], 0.27, centre, 24),
        cylinder('TankBand', m['remap'], 0.275, 0.04, centre, segments=24, bevel=0),
        cylinder('TankBase', m['concrete_dark'], 0.24, 0.06, TANK + Vector((0, 0, PAD + 0.03)), segments=24, bevel=0.005),
        cylinder('TankValve', m['steel'], 0.05, 0.05, centre + Vector((0, 0, 0.28)), segments=12),
        beam('TankPipe', m['steel'], TANK + Vector((-0.2, -0.05, PAD + 0.2)), flat((TANK - DISH).normalized(), 0.95, 0.18), 0.035),
    ]
    for k in range(6):
        a = 2 * math.pi * k / 6
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(beam(f'TankLeg{k}', m['steel'], TANK + d * 0.2 + Vector((0, 0, PAD + 0.06)), centre + d * 0.17 - Vector((0, 0, 0.12)), 0.03))
    return kit.merge('TankGroup', parts, TANK + Vector((0, 0, PAD)))


ACROSS = Vector((-DOCK_DIR.y, DOCK_DIR.x, 0))


def on_edge(side, z):
    """Where the gate's side wall (y = side · half width) meets the skirt at height z."""
    if z <= SKIRT[1][1]:
        r = SKIRT[0][0]
    else:
        (r0, z0), (r1, z1) = SKIRT[1], SKIRT[2]
        r = r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    across = GATE[0] * side
    return flat(DOCK_DIR, math.sqrt(r * r - across * across), z) + ACROSS * across


def gate(m):
    """The inside of the gate (all dark: walls, ceiling, back wall and floor) and its
    house-colour frame on the skirt; returns (lining, frame, the frame's top corners)."""
    half, height = GATE
    front = SKIRT[0][0]
    depth = front - PIT
    middle = flat(DOCK_DIR, PIT + depth / 2, 0)
    t = 0.01  # the lining sits just inside the cut
    lining = kit.merge('GateLining', [
        box('GatePit', m['dark'], (t, 2 * half, height), flat(DOCK_DIR, PIT + t, height / 2), bevel=0, rotation=(0, 0, DOCK_ANGLE)),
        box('GateCeiling', m['dark'], (depth, 2 * half, t), middle + Vector((0, 0, height - t / 2)), bevel=0, rotation=(0, 0, DOCK_ANGLE)),
        *[box(f'GateWall{s}', m['dark'], (depth, t, height), middle + ACROSS * s * (half - t / 2) + Vector((0, 0, height / 2)), bevel=0,
              rotation=(0, 0, DOCK_ANGLE)) for s in (-1, 1)],
        box('GateFloor', m['dark'], (depth + 0.1, 2 * half, 0.012), middle + DOCK_DIR * 0.05 + Vector((0, 0, FOOTING + 0.006)), bevel=0,
            rotation=(0, 0, DOCK_ANGLE)),
    ], middle)

    # the frame follows the cut edges up the skirt; the lintel lies across the top
    parts = []
    corners = []
    for s in (-1, 1):
        low, knee, top = on_edge(s, 0.0), on_edge(s, SKIRT[1][1]), on_edge(s, height)
        out = ACROSS * s * 0.035
        parts += [beam(f'Post{s}', m['remap'], low + out, knee + out, 0.07, 0.06),
                  beam(f'Jamb{s}', m['remap'], knee + out, top + out, 0.07, 0.06)]
        corners.append(top + out + Vector((0, 0, 0.035)))
    lintel = on_edge(0, height)  # in the middle the skirt stands furthest out
    ends = [Vector((lintel.x, lintel.y, height + 0.03)) + ACROSS * s * (half + 0.07) for s in (-1, 1)]
    parts.append(beam('Lintel', m['remap'], ends[0], ends[1], 0.07, 0.07))
    parts.append(box('LintelStripe', m['hazard'], (0.012, 2 * half, 0.025), Vector((lintel.x, lintel.y, height + 0.03)) + DOCK_DIR * 0.036,
                     bevel=0, rotation=(0, 0, DOCK_ANGLE)))
    return lining, kit.merge('GateFrame', parts, flat(DOCK_DIR, front, 0)), corners


def flame(m, name, at, size):
    """A burnoff flame: a few additive blobs; origin at its foot."""
    blobs = [sphere(f'{name}{k}', m['flame'], size * (1 - 0.22 * k), at + Vector((0.01 * (k % 2), 0, size * 0.9 * k)), 10) for k in range(3)]
    obj = kit.merge(name, blobs, at)
    obj.scale = (1, 1, 1.4)
    return obj


# --------------------------------------------------------------------------- animation

def flicker(obj, seed):
    """The Idle loop: a flame that never stands still."""
    frames = {}
    for f in range(0, IDLE_END + 1, 4):
        t = (f % IDLE_END) / IDLE_END * 2 * math.pi
        k = 1 + 0.16 * math.sin(3 * t + seed) + 0.1 * math.sin(7 * t + 2 * seed)
        frames[f] = Vector((k, k, 1.4 * (1 + 0.25 * math.sin(5 * t + seed))))
    kit.keys(obj, 'scale', frames)


# --------------------------------------------------------------------------- model

def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = BUILD_END + 12
    scene.frame_current = BUILD_END  # parenting reads the evaluated pose: the finished plant

    m = materials()
    root = kit.empty('GDIRefinery')
    keys = kit.keys

    # ---- the pad spreads from the dock
    ground = kit.parent(pad(m), root)
    keys(ground, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 14: Vector((1.02, 1.02, 1)), 17: Vector((1, 1, 1))})
    dock = kit.parent(kit.empty('Dock', DOCK + Vector((0, 0, PAD))), root)
    dock.rotation_euler = (0, 0, DOCK_ANGLE + math.pi / 2)  # -Y (the front) away from the plant, the back in the gate
    dock.empty_display_size = 0.3

    # ---- the skirt rises and puts up its ribs
    plant = kit.parent(kit.empty('PlantGroup'), root)
    for obj in skirt(m, root):
        kit.parent(obj, plant)
    keys(plant, 'location', {0: Vector((0, 0, -0.8)), 6: Vector((0, 0, -0.8)), 30: Vector((0, 0, 0.01)), 33: Vector((0, 0, 0))})
    for i, rib in enumerate(ribs(m)):
        kit.parent(rib, plant)
        kit.pop(rib, 24 + i * 2, 6)

    # ---- the tower rises behind it, the stacks grow out of the deck
    tower_group = kit.parent(kit.empty('TowerGroup', TOWER), root)
    base, stack_parts, burner = tower(m, root)
    for obj in (base, stack_parts):
        kit.parent(obj, tower_group)
    keys(tower_group, 'location', {0: TOWER - Vector((0, 0, 1.8)), 20: TOWER - Vector((0, 0, 1.8)), 52: TOWER + Vector((0, 0, 0.015)), 56: TOWER})
    stacks = []
    for i, (foot, height) in enumerate(STACKS):
        obj = kit.parent(stack(m, i, foot + Vector((0, 0, DECK + 0.03)), height), plant)
        kit.grow(obj, 50 + i * 6, 12, 2)
        stacks.append((obj, foot + Vector((0, 0, DECK + 0.03 + height + 0.04)), height))

    # ---- the gate: lined inside, its frame pops up on the skirt
    lining, frame, corners = gate(m)
    kit.parent(lining, plant)
    kit.parent(frame, plant)
    kit.pop(frame, 34, 8)

    # ---- the tank
    tank_obj = kit.parent(tank(m), root)
    kit.pop(tank_obj, 58, 8)

    # ---- flames (Idle); each sits in a holder that pops in the Build
    idle = []
    flames = [(flame(m, 'Burnoff', burner, 0.07), tower_group, 0.0)]
    flames += [(flame(m, f'DeckFlame{i}', top, 0.04), obj, 1.7 + i) for i, (obj, top, _) in enumerate(stacks[:1])]
    for obj, holder, seed in flames:
        mount = kit.parent(kit.empty(f'{obj.name}Mount', obj.location), holder)
        kit.parent(obj, mount)
        kit.pop(mount, 84, 6)
        idle.append((obj, lambda o, s=seed: flicker(o, s)))

    # ---- beacons: red on the stack's cap, amber on the gate's top corners
    lights = []
    tops = [(burner - Vector((0, 0, 0.06)) + Vector((math.cos(a), math.sin(a), 0)) * 0.1, 'red', tower_group) for a in (0.6, 2.7, 4.8)]
    tops += [(corner, 'amber', frame) for corner in corners]
    for k, (at, colour, holder) in enumerate(tops):
        housing, light = kit.beacon(f'Beacon{k}', m, at, colour)
        housing = kit.parent(kit.merge(f'Beacon{k}', [housing], at), holder)
        kit.parent(light, housing)
        kit.pop(housing, 86 + k, 5)
        pattern = kit.flashes((0, 12), (30, 12)) if colour == 'red' else kit.flashes((15 + 3 * k, 8), (45 + 3 * k, 8))
        lights.append((light, pattern))

    # ---- clips
    for obj in kit.collection().objects:
        if obj.animation_data and obj.animation_data.action:
            kit.to_track(obj, 'Build')
    for obj, animate in idle:
        animate(obj)
        kit.to_track(obj, 'Idle')
    for light, pattern in lights:
        kit.blink(light, pattern)
        kit.to_track(light, 'Idle')
    return len(kit.collection().objects)


def preview(frames, out_dir):
    """kit.render_preview with a camera wide enough for the 4 × 3 foundation."""
    kit.render_preview([], out_dir)
    cam = bpy.data.objects['PreviewCamera']
    cam.data.ortho_scale = 4.8
    direction = Vector((math.sin(math.radians(45)) * math.cos(math.radians(30)),
                        -math.cos(math.radians(45)) * math.cos(math.radians(30)),
                        math.sin(math.radians(30))))
    cam.location = Vector((0, -0.1, 0.65)) + direction * 10
    kit.render_preview(frames, out_dir)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    kit.bake_camo()
    bpy.context.scene.frame_set(BUILD_END)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2])


if __name__ == '__main__' and bpy.app.background:
    main()
