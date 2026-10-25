"""
Tiberian Fallout – GDI power turbine (GAPOWRUP), the upgrade of the power plant.

A low stepped turbine like in the original: three tiers of blue-violet metal with
slanted vanes, and a brass core on top with a ring of glowing amber windows. Its foot locks into the four holes of one of the power plant's
turbine places with four pegs; everything above the foot turns. Its origin is the
middle of the foot, which the game puts onto a place's node (TurbineSlot1 … 3 in
GAPOWR.glb).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 1.1 s: the foot locks in, the tiers stack up one after another,
             the windows light up
    Idle     loop, 2 s: the whole turbine above its foot turns, the windows pulse

Run headless:

    Blender -b --factory-startup --python blender/GAPOWRUP.py

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z).
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import GAPOWR as plant  # noqa: E402 – lathe() and the power plant's materials

kit.COLLECTION = 'GDIPowerTurbine'  # after importing GAPOWR, which sets its own
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAPOWRUP.glb')
BLEND = os.path.join(HERE, 'GAPOWRUP.blend')

BUILD_END = 33
IDLE_END = kit.IDLE_END
TURNS = 1               # turns of the turbine per Idle loop

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material

# the stepped turbine body: (radius at the bottom, radius at the top, height) per tier
TIERS = ((0.235, 0.205, 0.07), (0.185, 0.158, 0.06), (0.138, 0.122, 0.05))
VANES = (16, 12, 0)     # slanted vanes per tier (the top tier is the brass core)


def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = IDLE_END
    scene.frame_current = BUILD_END

    m = plant.materials()
    m['shell'] = material('TurbineShell', srgb('#6c71a6'), 0.35, 0.8)
    m['brass'] = material('Brass', srgb('#c9a24a'), 0.3, 0.9)
    m['vane'] = material('TurbineVane', srgb('#a3a8cc'), 0.35, 0.85)
    root = kit.empty('GDIPowerTurbine')
    keys = kit.keys

    # ---- foot ring, with four pegs down into the place's holes; it does not turn
    foot_parts = [cylinder('FootRing', m['pod_dark'], 0.24, 0.025, (0, 0, 0.0125), segments=32, bevel=0.004)]
    for k in range(4):
        a = math.pi / 4 + math.pi / 2 * k
        p = Vector((math.cos(a), math.sin(a), 0)) * plant.HOLE_RADIUS
        foot_parts.append(cylinder(f'Peg{k}', m['steel_light'], 0.026, 0.04, p, segments=12, bevel=0.002))
        foot_parts.append(cylinder(f'PegCap{k}', m['steel'], 0.04, 0.012, p + Vector((0, 0, 0.026)), segments=12, bevel=0.002))
    foot = kit.parent(kit.merge('Foot', foot_parts), root)
    kit.pop(foot, 0, 6)

    # everything above the foot turns (Idle) on this
    spinner = kit.parent(kit.empty('Spinner'), root)

    # ---- three stepped tiers of blue-violet metal with slanted vanes, stacking up
    z = 0.025
    for t, ((r0, r1, h), vanes) in enumerate(zip(TIERS, VANES)):
        parts = [plant.lathe(f'Tier{t}', m['shell'] if vanes else m['brass'], ((r0, 0), (r1, h)), (0, 0, z), 40)]
        parts.append(cylinder(f'Lip{t}', m['pod_dark'], r1 + 0.008, 0.012, (0, 0, z + h), segments=40, bevel=0.002))
        if t == 0:
            parts.append(cylinder('Band', m['remap'], r0 + 0.004, 0.016, (0, 0, z + 0.014), segments=40, bevel=0))
        for k in range(vanes):
            a = 2 * math.pi * k / vanes
            b = a + math.radians(18)  # slanted like turbine blades
            low = Vector((math.cos(a) * (r0 + 0.004), math.sin(a) * (r0 + 0.004), z + 0.004 + (0.02 if t == 0 else 0)))
            high = Vector((math.cos(b) * (r1 + 0.004), math.sin(b) * (r1 + 0.004), z + h - 0.004))
            parts.append(beam(f'Vane{t}_{k}', m['vane'], low, high, 0.012, 0.016))
        if not vanes:
            # the brass core: a dome on top
            parts.append(plant.lathe('Dome', m['brass'], ((r1, 0), (r1 * 0.8, 0.025), (r1 * 0.45, 0.045), (0.02, 0.052)), (0, 0, z + h), 32))
            parts.append(cylinder('Nub', m['steel'], 0.018, 0.03, (0, 0, z + h + 0.06), segments=12, bevel=0.002))
        tier = kit.parent(kit.merge(f'Tier{t}', parts, (0, 0, z)), spinner)
        kit.grow(tier, 4 + t * 6, 9, 2)
        z += h
    core_z = z - TIERS[-1][2] / 2

    # ---- a ring of glowing windows round the brass core (pulse in Idle, mount pops in Build)
    r = TIERS[-1][0] - 0.004
    windows, halos = [], []
    for k in range(6):
        a = 2 * math.pi * k / 6
        d = Vector((math.cos(a), math.sin(a), 0))
        windows.append(box(f'Window{k}', m['lamp_amber'], (0.012, 0.05, 0.026), d * r + Vector((0, 0, core_z)),
                           bevel=0.003, rotation=(0, 0, a)))
        halos.append(box(f'WindowHalo{k}', m['glow_amber'], (0.016, 0.062, 0.036), d * (r + 0.006) + Vector((0, 0, core_z)),
                         bevel=0, rotation=(0, 0, a)))
    mount = kit.parent(kit.merge('Windows', windows, (0, 0, core_z)), spinner)
    glow = kit.merge('WindowGlow', halos, (0, 0, core_z))
    kit.parent(glow, mount)
    kit.pop(mount, 24, 6)

    # ---- clips
    for obj in kit.collection().objects:
        if obj.animation_data and obj.animation_data.action:
            kit.to_track(obj, 'Build')
    keys(spinner, 'rotation_euler', {f: Vector((0, 0, 2 * math.pi * TURNS * f / IDLE_END)) for f in range(0, IDLE_END + 1, 3)}, 'LINEAR')
    kit.to_track(spinner, 'Idle')
    keys(glow, 'scale', {f: Vector((1, 1, 1)) * (1 + 0.2 * math.sin(2 * math.pi * 2 * f / IDLE_END)) for f in range(IDLE_END + 1)}, 'LINEAR')
    kit.to_track(glow, 'Idle')
    return len(kit.collection().objects)


def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    bpy.context.scene.frame_set(BUILD_END)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)


if __name__ == '__main__' and bpy.app.background:
    main()
