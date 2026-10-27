"""
Tiberian Fallout – Nod gate turned by 90° (NAGATE_B), after Tiberian Sun.

The Nod gate of NAGATE_A.py, turned a quarter round: three cells long along y
(Foundation=1x3; on screen it runs from the lower left to the upper right). The model
is built by NAGATE_A.build() and its root turned by +90° about the vertical; the arms
are renamed after the glTF axes they now point along.

Nodes (as NAGATE_A):
    Body     carries the gate up out of the ground (Build)
    Door     the wall itself, inside Body (sinks in Open)
    ArmZP    the wall slab from the gate's front end (-Y, glTF +Z) to the cell's edge,
             shown by the game when an NAWALL joins there
    ArmZN    … at the back end (+Y, glTF -Z)
    Lamp…    small red lamps on the high ends
Animations (glTF clips): Build (one-shot, 1.6 s), Idle (loop, 2 s), Open (one-shot,
1 s; played backwards it shuts) – see NAGATE_A.py.

Run headless:

    blender -b --factory-startup --python blender/NAGATE_B.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells are
centred at y = -1, 0, 1; origin in the middle on the ground.
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nb  # noqa: E402
import NAGATE_A as gate  # noqa: E402


def build():
    count = gate.build()
    root = bpy.data.objects['NodGate']
    root.rotation_euler = (0, 0, math.pi / 2)   # +x → +y
    # ArmXP (Blender +x) now points along +y = glTF -z, ArmXN along -y = glTF +z
    bpy.data.objects['ArmXP'].name = 'ArmZN'
    bpy.data.objects['ArmXN'].name = 'ArmZP'
    return count


if __name__ == '__main__':
    kit.render_preview = gate._render_and_rest
    nb.main(build, 'NAGATE_B', {'Build': [12, 26, 40], 'Idle': [0], 'Open': [10, 20, 30]}, ortho=3.4, target=(0, 0, 0.3), texture=1024)
