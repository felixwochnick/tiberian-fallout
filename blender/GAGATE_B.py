"""
Tiberian Fallout – GDI gate, turned (GAGATE_B), after Tiberian Sun.

The gate of GAGATE_A.py turned by 90°: across three cells along y (foundation 1 × 3,
long in glTF z), built by the same code with its root node turned. The grilles face
glTF ±x, the lamps sit on the sill on the +x side (the screen's lower right).

At its ends it shows stubs towards neighbouring walls and component towers
(Battlefield.connectWalls), one pair for each kind of wall (glTF axes):

    ArmZP, ArmZN     the concrete wall (GAWALL.arm: block and half a joint)
    SandZP, SandZN   sandbags (GASAND.stub)

Nodes and clips as for GAGATE_A: GateRise (Build) holds Gate (Open).

Animations (glTF clips)
    Build    one-shot, 1.6 s: the footing and sill spread out, the stubs grow, the gate
             comes up out of the sill, the lamps' housings pop up
    Idle     loop, 2 s: the lamps blink in turn
    Open     one-shot, 1 s: the gate sinks into the sill (played backwards it closes)

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAGATE_B.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells are
centred at y = -1, 0, 1; origin in the middle on the ground.
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAGATE_A as gate  # noqa: E402 – the gate itself

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAGATE_B.glb')
BLEND = os.path.join(HERE, 'GAGATE_B.blend')

if __name__ == '__main__' and bpy.app.background:
    gate.main(OUT, BLEND, turned=True)
