#!/usr/bin/env python3
"""
MCP server for Tiberian Fallout: plays the game open in the browser through the dev
server's agent relay (server/utils/agent-relay.ts, commands in app/lib/agent/commands.ts),
like scripts/agent.mjs does from the terminal.

    python3 scripts/mcp/tiberian_fallout.py     # registered in .mcp.json

AGENT_URL sets the dev server (default http://localhost:3000).
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import Image, Server  # noqa: E402

BASE = os.environ.get('AGENT_URL', 'http://localhost:3000')

server = Server('tiberian-fallout', '1.0.0', instructions=(
    'Spielt das laufende Tiberian Fallout (Browser-Tab mit Gefecht /skirmish oder Mission, Dev-Server `pnpm dev`). '
    'Positionen sind Weltzellen (x, z) wie in tf_state; Objekte werden über ihre `ref` angesprochen. '
    'Der Browser-Tab muss sichtbar bleiben, sonst steht das Spiel.'
))


def send(cmd: str, args: list):
    wait = float(args[0]) if cmd == 'wait' and args else 0
    request = urllib.request.Request(
        f'{BASE}/api/agent/command', method='POST',
        data=json.dumps({'cmd': cmd, 'args': args}).encode(),
        headers={'content-type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(request, timeout=30 + wait * 3) as response:
            answer = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'{error.code} {error.reason}') from None
    except urllib.error.URLError as error:
        raise RuntimeError(f'Dev-Server nicht erreichbar ({BASE}): {error.reason}; läuft `pnpm dev`?') from None
    if not answer.get('ok'):
        raise RuntimeError(answer.get('error', 'unbekannter Fehler'))
    return answer.get('result')


@server.tool('tf_command', (
    'Schickt einen beliebigen Agent-Befehl an das Spiel. Befehle (Argumente in Klammern): '
    'help; state; wait(sekunden≤120); map(x?, z?, radius=16); build(id, anzahl=1); cancel(id); '
    'place(x?, z?, near?) – fertiges Gebäude mit unterer Ecke auf (x,z) oder neben der Basis; '
    'deploy(ref); move(refs, x, z); attackMove(refs, x, z); attack(refs, zielRef); stop(refs); '
    'harvest(refs, x?, z?); unload(refs, raffinerieRef); rally(fabrikRef, x, z); sell(ref); repair(ref); '
    'power(ref); look(x, z) oder look(ref); screenshot. refs: Zahl, "1,2,3" oder Liste.'
), {
    'cmd': {'type': 'string', 'description': 'Befehlsname, z. B. "build"'},
    'args': {'type': 'array', 'description': 'Argumente in Reihenfolge, z. B. ["GAPOWR"] oder ["4,5", 40, 30]', 'items': {}},
}, ['cmd'])
def tf_command(cmd: str, args: list | None = None):
    result = send(cmd, args or [])
    if cmd == 'screenshot':
        return screenshot_image(result)
    if cmd == 'map':
        return map_text(result)
    return result


@server.tool('tf_state', 'Aktueller Spielstand: Zeit, Geld, Strom, Produktion, baubare Objekte, alle Objekte (ref, Besitzer, Position, Zustand), Tiberium-Felder, Hinweise.')
def tf_state():
    return send('state', [])


@server.tool('tf_wait', 'Lässt die Spielzeit laufen (Spielsekunden, höchstens 120) und liefert danach den Spielstand.', {
    'seconds': {'type': 'number', 'description': 'Spielsekunden', 'default': 5},
})
def tf_wait(seconds: float = 5):
    return send('wait', [seconds])


@server.tool('tf_map', "ASCII-Karte um (x, z) bzw. um die Basis: '.' frei, '#' blockiert/Hang, 'g'/'b' Tiberium, 'S'/'X' Gebäude eigen/Feind, 'u'/'x' Einheit eigen/Feind.", {
    'x': {'type': 'number'}, 'z': {'type': 'number'},
    'radius': {'type': 'number', 'default': 16, 'description': '2 … 40 Zellen'},
})
def tf_map(x: float | None = None, z: float | None = None, radius: float = 16):
    args = [] if x is None or z is None else [x, z, radius]
    if not args and radius != 16:
        raise ValueError('radius nur zusammen mit x und z')
    return map_text(send('map', args))


@server.tool('tf_screenshot', 'Bild des Schlachtfelds, wie es der Spieler sieht (Kamera mit tf_command look verschieben).')
def tf_screenshot():
    return screenshot_image(send('screenshot', []))


def screenshot_image(result):
    header, data = result['image'].split(',', 1)
    mime = header.removeprefix('data:').split(';')[0] or 'image/jpeg'
    return Image(base64.b64decode(data), mime)


def map_text(result):
    return f"x ab {result['x0']}, Zeilen = z\n" + '\n'.join(result['rows'])


if __name__ == '__main__':
    server.run()
