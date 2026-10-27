#!/usr/bin/env python3
"""
MCP server for Tiberian Fallout: plays the game open in the browser through the dev
server's agent relay (server/utils/agent-relay.ts, commands in app/lib/agent/commands.ts),
like scripts/agent.mjs does from the terminal.

    python3 scripts/mcp/tiberian_fallout.py     # registered in .mcp.json

Also drives Chromium (the browser this project is tested in) through the DevTools
protocol: a separate profile with the game data, screenshots, clicks, keys, script
evaluation and the console.

AGENT_URL sets the dev server (default http://localhost:3000); TF_CHROMIUM the browser
(default `chromium`), TF_CHROMIUM_PORT its debugging port (9333), TF_CHROMIUM_PROFILE
its profile folder (~/.cache/tiberian-fallout/chromium).
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp  # noqa: E402
from mcp import Image, Server  # noqa: E402

BASE = os.environ.get('AGENT_URL', 'http://localhost:3000')
CHROMIUM = os.environ.get('TF_CHROMIUM', 'chromium')
PORT = int(os.environ.get('TF_CHROMIUM_PORT', '9333'))
PROFILE = os.path.expanduser(os.environ.get('TF_CHROMIUM_PROFILE', '~/.cache/tiberian-fallout/chromium'))
STEAM_TS = os.path.expanduser('~/.local/share/Steam/steamapps/common/Command & Conquer Tiberian Sun')

server = Server('tiberian-fallout', '1.0.0', instructions=(
    'Spielt das laufende Tiberian Fallout (Browser-Tab mit Gefecht /skirmish oder Mission, Dev-Server `pnpm dev`). '
    'Positionen sind Weltzellen (x, z) wie in tf_state; Objekte werden über ihre `ref` angesprochen. '
    'Getestet wird in Chromium: tf_browser_open startet es (eigenes Profil, Spieldaten einmalig mit '
    'tf_browser_import laden); tf_browser_* klicken, tippen, werten JS aus und lesen die Konsole.'
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


@server.tool('tf_map', "ASCII-Karte um (x, z) bzw. ohne x/z um die Basis: '.' frei, '#' blockiert/Hang, 'g'/'b' Tiberium, 'S'/'X' Gebäude eigen/Feind, 'u'/'x' Einheit eigen/Feind.", {
    'x': {'type': 'number'}, 'z': {'type': 'number'},
    'radius': {'type': 'number', 'default': 16, 'description': '2 … 40 Zellen'},
})
def tf_map(x: float | None = None, z: float | None = None, radius: float = 16):
    return map_text(send('map', [x, z, radius]))


@server.tool('tf_screenshot', 'Bild des Schlachtfelds, wie es der Spieler sieht (Kamera mit tf_command look verschieben).')
def tf_screenshot():
    return screenshot_image(send('screenshot', []))


def screenshot_image(result):
    header, data = result['image'].split(',', 1)
    mime = header.removeprefix('data:').split(';')[0] or 'image/jpeg'
    return Image(base64.b64decode(data), mime)


def map_text(result):
    return f"x ab {result['x0']}, Zeilen = z\n" + '\n'.join(result['rows'])



# --- Chromium ----------------------------------------------------------------------

page: cdp.Page | None = None


def connect():
    """The page of the game in the debugged Chromium (connects on first use)."""
    global page
    if page is not None and not page.closed:
        return page
    try:
        tabs = [t for t in cdp.targets(PORT) if t.get('type') == 'page']
    except OSError:
        raise RuntimeError('Chromium läuft nicht mit Debugging – erst tf_browser_open') from None
    tab = next((t for t in tabs if t.get('url', '').startswith(BASE)), tabs[0] if tabs else None)
    if not tab:
        raise RuntimeError('Kein Tab offen')
    page = cdp.Page(tab['webSocketDebuggerUrl'])
    return page


def wait_loaded(p: cdp.Page, timeout: float = 30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if p.evaluate('document.readyState') == 'complete':
                return
        except (RuntimeError, TimeoutError):
            pass
        time.sleep(0.3)


def browser_shot(quality: int = 80):
    data = connect().call('Page.captureScreenshot', format='jpeg', quality=quality)['data']
    return Image(base64.b64decode(data), 'image/jpeg')


@server.tool('tf_browser_open', (
    'Öffnet das Spiel in Chromium (eigenes Profil, Remote-Debugging, ohne Hintergrund-Drosselung, damit das Spiel '
    'auch verdeckt weiterläuft) bzw. navigiert den offenen Tab zu `path` (z. B. "/", "/skirmish", "/menu"). '
    'Liefert einen Screenshot.'
), {
    'path': {'type': 'string', 'default': '/'},
    'width': {'type': 'integer', 'default': 1280}, 'height': {'type': 'integer', 'default': 800},
    'wait': {'type': 'number', 'default': 3, 'description': 'Sekunden nach dem Laden bis zum Screenshot'},
})
def tf_browser_open(path: str = '/', width: int = 1280, height: int = 800, wait: float = 3):
    global page
    url = BASE + (path if path.startswith('/') else '/' + path)
    try:
        cdp.targets(PORT)
        running = True
    except OSError:
        running = False
    if not running:
        binary = shutil.which(CHROMIUM)
        if not binary:
            raise RuntimeError(f'{CHROMIUM} nicht gefunden (TF_CHROMIUM setzen)')
        os.makedirs(PROFILE, exist_ok=True)
        log = open(os.path.join(PROFILE, 'mcp.log'), 'ab')
        subprocess.Popen([
            binary, f'--remote-debugging-port={PORT}', f'--user-data-dir={PROFILE}',
            # X11 keeps requestAnimationFrame running while the window is covered (Wayland stops it)
            '--ozone-platform=x11', '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding',
            '--autoplay-policy=no-user-gesture-required',
            # sets navigator.webdriver: the game then stays in the window (no full screen, no pointer lock)
            '--enable-automation',
            # Chromium under X11/Xwayland sees no pointer device and the game would ask for a mouse:
            # report a mouse (fine pointer that can hover)
            '--blink-settings=primaryPointerType=4,availablePointerTypes=4,primaryHoverType=2,availableHoverTypes=2', '--no-first-run', '--no-default-browser-check',
            f'--window-size={width},{height}', url,
        ], stdout=log, stderr=log, start_new_session=True)
        for _ in range(100):
            time.sleep(0.2)
            try:
                if any(t.get('type') == 'page' for t in cdp.targets(PORT)):
                    break
            except OSError:
                pass
        else:
            raise RuntimeError(f'Chromium startet nicht, siehe {PROFILE}/mcp.log')
        page = None
        p = connect()
    else:
        p = connect()
        p.call('Page.navigate', url=url)
        time.sleep(0.5)
    wait_loaded(p)
    time.sleep(max(0, wait))
    return [f'Chromium: {url}', browser_shot()]


@server.tool('tf_browser_screenshot', 'Screenshot des Chromium-Tabs (ganze Seite inkl. Menüs und HUD, Koordinaten = CSS-Pixel).', {
    'quality': {'type': 'integer', 'default': 80},
})
def tf_browser_screenshot(quality: int = 80):
    return browser_shot(quality)


MOUSE_BUTTONS = {'left': 1, 'middle': 4, 'right': 2}
MODIFIERS = {'alt': 1, 'ctrl': 2, 'control': 2, 'meta': 4, 'shift': 8}


@server.tool('tf_browser_click', 'Klickt im Chromium-Tab an (x, y) (CSS-Pixel wie im Screenshot).', {
    'x': {'type': 'number'}, 'y': {'type': 'number'},
    'button': {'type': 'string', 'enum': ['left', 'right', 'middle'], 'default': 'left'},
    'double': {'type': 'boolean', 'default': False},
    'modifiers': {'type': 'array', 'items': {'type': 'string'}, 'default': []},
    'screenshot': {'type': 'boolean', 'default': True}, 'delay': {'type': 'number', 'default': 0.5},
}, ['x', 'y'])
def tf_browser_click(x: float, y: float, button: str = 'left', double: bool = False, modifiers: list | None = None,
                     screenshot: bool = True, delay: float = 0.5):
    p = connect()
    mods = sum(MODIFIERS[m.lower()] for m in modifiers or [])
    p.call('Input.dispatchMouseEvent', type='mouseMoved', x=x, y=y, modifiers=mods)
    for count in ([1, 2] if double else [1]):
        for kind in ('mousePressed', 'mouseReleased'):
            p.call('Input.dispatchMouseEvent', type=kind, x=x, y=y, button=button, clickCount=count,
                   buttons=MOUSE_BUTTONS[button] if kind == 'mousePressed' else 0, modifiers=mods)
            time.sleep(0.05)
    if not screenshot:
        return f'{button}-Klick auf ({x}, {y})'
    time.sleep(delay)
    return [f'{button}-Klick auf ({x}, {y})', browser_shot()]


@server.tool('tf_browser_move', 'Bewegt die Maus im Chromium-Tab (Hover, Rand-Scrollen); mit `to_x`/`to_y` als Ziehen mit gedrückter Taste.', {
    'x': {'type': 'number'}, 'y': {'type': 'number'},
    'to_x': {'type': 'number'}, 'to_y': {'type': 'number'},
    'button': {'type': 'string', 'enum': ['left', 'right', 'middle'], 'default': 'left'},
    'hold': {'type': 'number', 'default': 0, 'description': 'Sekunden am Ziel stehen bleiben (z. B. Rand-Scrollen)'},
}, ['x', 'y'])
def tf_browser_move(x: float, y: float, to_x: float | None = None, to_y: float | None = None,
                    button: str = 'left', hold: float = 0):
    p = connect()
    p.call('Input.dispatchMouseEvent', type='mouseMoved', x=x, y=y)
    if to_x is not None and to_y is not None:
        p.call('Input.dispatchMouseEvent', type='mousePressed', x=x, y=y, button=button, clickCount=1, buttons=MOUSE_BUTTONS[button])
        for i in range(1, 11):
            p.call('Input.dispatchMouseEvent', type='mouseMoved', x=x + (to_x - x) * i / 10, y=y + (to_y - y) * i / 10,
                   buttons=MOUSE_BUTTONS[button])
            time.sleep(0.02)
        p.call('Input.dispatchMouseEvent', type='mouseReleased', x=to_x, y=to_y, button=button, clickCount=1)
    time.sleep(max(0, min(30, hold)))
    return [f'Maus auf ({x}, {y})' + (f' → ({to_x}, {to_y})' if to_x is not None else ''), browser_shot()]


KEYS = {
    'escape': ('Escape', 'Escape', 27), 'esc': ('Escape', 'Escape', 27), 'enter': ('Enter', 'Enter', 13),
    'tab': ('Tab', 'Tab', 9), 'backspace': ('Backspace', 'Backspace', 8), 'delete': ('Delete', 'Delete', 46),
    'space': (' ', 'Space', 32), 'arrowup': ('ArrowUp', 'ArrowUp', 38), 'arrowdown': ('ArrowDown', 'ArrowDown', 40),
    'arrowleft': ('ArrowLeft', 'ArrowLeft', 37), 'arrowright': ('ArrowRight', 'ArrowRight', 39),
    'up': ('ArrowUp', 'ArrowUp', 38), 'down': ('ArrowDown', 'ArrowDown', 40),
    'left': ('ArrowLeft', 'ArrowLeft', 37), 'right': ('ArrowRight', 'ArrowRight', 39),
    'home': ('Home', 'Home', 36), 'end': ('End', 'End', 35), 'pageup': ('PageUp', 'PageUp', 33),
    'pagedown': ('PageDown', 'PageDown', 34),
    **{f'f{n}': (f'F{n}', f'F{n}', 111 + n) for n in range(1, 13)},
}


def key_info(name: str, shift: bool):
    if name.lower() in KEYS:
        key, code, vk = KEYS[name.lower()]
        return key, code, vk, None
    if len(name) == 1:
        char = name.upper() if shift else name
        code = f'Key{name.upper()}' if name.isalpha() else f'Digit{name}' if name.isdigit() else ''
        return char, code, ord(name.upper()), char
    raise ValueError(f'Unbekannte Taste "{name}"')


@server.tool('tf_browser_key', 'Drückt Tasten im Chromium-Tab nacheinander, Kombinationen mit "+", z. B. ["Escape"], ["ctrl+1"], ["h"], ["shift+a"], ["F2"].', {
    'keys': {'type': 'array', 'items': {'type': 'string'}},
    'screenshot': {'type': 'boolean', 'default': True}, 'delay': {'type': 'number', 'default': 0.5},
}, ['keys'])
def tf_browser_key(keys: list, screenshot: bool = True, delay: float = 0.5):
    p = connect()
    for combo in keys:
        *mod_names, name = [part for part in combo.split('+') if part] or ['+']
        mods = sum(MODIFIERS[m.lower()] for m in mod_names)
        key, code, vk, text = key_info(name, bool(mods & 8))
        down = {'type': 'keyDown' if text else 'rawKeyDown', 'key': key, 'code': code, 'windowsVirtualKeyCode': vk, 'modifiers': mods}
        if text and not mods & 6:
            down['text'] = text
        p.call('Input.dispatchKeyEvent', **down)
        time.sleep(0.05)
        p.call('Input.dispatchKeyEvent', type='keyUp', key=key, code=code, windowsVirtualKeyCode=vk, modifiers=mods)
        time.sleep(0.05)
    if not screenshot:
        return f'Tasten: {", ".join(keys)}'
    time.sleep(delay)
    return [f'Tasten: {", ".join(keys)}', browser_shot()]


@server.tool('tf_browser_eval', 'Wertet JavaScript im Chromium-Tab aus (Promises werden abgewartet) und liefert das Ergebnis als JSON.', {
    'expression': {'type': 'string'},
}, ['expression'])
def tf_browser_eval(expression: str):
    return connect().evaluate(expression)


@server.tool('tf_browser_console', 'Die letzten Konsolenmeldungen, Warnungen und Fehler des Chromium-Tabs (seit dem Verbinden).', {
    'last': {'type': 'integer', 'default': 50}, 'clear': {'type': 'boolean', 'default': False},
    'errors_only': {'type': 'boolean', 'default': False},
})
def tf_browser_console(last: int = 50, clear: bool = False, errors_only: bool = False):
    p = connect()
    lines = [l for l in p.log if not errors_only or l.startswith(('[error]', '[exception]', '[warning]'))]
    if clear:
        p.log.clear()
    return '\n'.join(lines[-last:]) or '(keine Meldungen)'


@server.tool('tf_browser_import', (
    'Importiert die Spieldaten (MIX-Dateien) aus einer Tiberian-Sun-Installation in den Browser-Speicher von Chromium '
    '(wie „Dateien wählen“ auf der Startseite). Standard: die Steam-Installation, ohne Filmarchive.'
), {
    'directory': {'type': 'string', 'description': f'Standard: {STEAM_TS}'},
    'movies': {'type': 'boolean', 'default': False, 'description': 'MOVIES*.MIX mitnehmen (~1,4 GB)'},
    'names': {'type': 'array', 'items': {'type': 'string'}, 'description': 'nur diese Dateien, z. B. ["MOVIES01.MIX"]'},
})
def tf_browser_import(directory: str | None = None, movies: bool = False, names: list | None = None):
    directory = os.path.expanduser(directory or STEAM_TS)
    wanted = {n.lower() for n in names or []}
    files = sorted(os.path.join(directory, n) for n in os.listdir(directory)
                   if (n.lower() in wanted if wanted else
                       n.lower().endswith('.mix') and (movies or not n.lower().startswith('movies'))))
    if not files:
        raise RuntimeError(f'Keine MIX-Dateien in {directory}')
    p = connect()
    if not p.evaluate("!!document.querySelector('input[type=file][multiple]')"):
        tf_browser_open('/', wait=2)
        p = connect()
    root = p.call('DOM.getDocument')['root']['nodeId']
    node = p.call('DOM.querySelector', nodeId=root, selector='input[type=file][multiple]')['nodeId']
    if not node:
        raise RuntimeError('Kein Import-Feld auf der Startseite (sind die Daten schon da?)')
    p.call('DOM.setFileInputFiles', nodeId=node, files=files)
    return [f'{len(files)} Dateien übergeben ({sum(os.path.getsize(f) for f in files) // 2**20} MB); '
            'Fortschritt mit tf_browser_screenshot prüfen.', browser_shot()]


@server.tool('tf_browser_close', 'Beendet das per tf_browser_open gestartete Chromium.')
def tf_browser_close():
    global page
    try:
        p = connect()
        p.call('Browser.close', timeout=5)
    except (RuntimeError, TimeoutError, ConnectionError):
        pass
    page = None
    return 'Chromium beendet.'

if __name__ == '__main__':
    server.run()
