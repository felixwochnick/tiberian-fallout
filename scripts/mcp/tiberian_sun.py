#!/usr/bin/env python3
"""
MCP server for the original Tiberian Sun (Steam version, run with Proton): starts the
game in its own rootful Xwayland window, so an agent can watch it (screenshots) and
play it (XTEST mouse and keyboard) while the desktop stays usable; and reads the
original rules and assets from its MIX archives, to compare them with Tiberian Fallout.

    python3 scripts/mcp/tiberian_sun.py     # registered in .mcp.json

Environment: TS_DIR (game folder), STEAM_DIR (default ~/.local/share/Steam), TS_PROTON
(Proton folder name, default the newest "Proton*" in steamapps/common), TS_DISPLAY
(default :7), TS_APPID (default 2229880).
"""
import io
import os
import re
import shutil
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mix  # noqa: E402
import x11  # noqa: E402
from mcp import Image, Server  # noqa: E402

STEAM = os.path.expanduser(os.environ.get('STEAM_DIR', '~/.local/share/Steam'))
APPID = os.environ.get('TS_APPID', '2229880')
GAME_DIR = os.environ.get('TS_DIR', os.path.join(STEAM, 'steamapps/common/Command & Conquer Tiberian Sun'))
DISPLAY = os.environ.get('TS_DISPLAY', ':7')
LOG = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), 'tiberian-sun-mcp.log')

server = Server('tiberian-sun', '1.0.0', instructions=(
    'Spielt das originale Tiberian Sun (Steam/Proton) in einem eigenen Xwayland-Fenster und liest dessen '
    'Regeln/Dateien. Ablauf: ts_start → ts_screenshot → ts_click/ts_key/ts_drag … Alle Koordinaten sind '
    'Bildschirmpixel des Spielfensters (wie im Screenshot bei scale=1; bei scale=2 die Bildkoordinaten verdoppeln). '
    'ts_rules / ts_rules_search / ts_file lesen rules.ini, firestrm.ini, art.ini usw. direkt aus den MIX-Archiven.'
))

state = {'xwayland': None, 'game': None, 'display': None}
library = mix.Library(GAME_DIR)


# --- processes -------------------------------------------------------------------

def proton_dir():
    common = os.path.join(STEAM, 'steamapps/common')
    if name := os.environ.get('TS_PROTON'):
        return os.path.join(common, name)
    candidates = [n for n in os.listdir(common) if n.startswith('Proton') and os.path.exists(os.path.join(common, n, 'proton'))]
    if not candidates:
        raise RuntimeError(f'Kein Proton in {common} gefunden (TS_PROTON setzen)')
    return os.path.join(common, 'Proton - Experimental' if 'Proton - Experimental' in candidates else sorted(candidates)[-1])


def compat_env():
    env = {k: v for k, v in os.environ.items() if k not in ('WAYLAND_DISPLAY', 'WINEPREFIX')}
    env.update(DISPLAY=DISPLAY, SteamAppId=APPID, SteamGameId=APPID,
               STEAM_COMPAT_DATA_PATH=os.path.join(STEAM, 'steamapps/compatdata', APPID),
               STEAM_COMPAT_CLIENT_INSTALL_PATH=STEAM)
    return env


def game_pids():
    """Running Game.exe processes of this installation (also ones started elsewhere)."""
    pids = []
    for pid in filter(str.isdigit, os.listdir('/proc')):
        try:
            cmdline = open(f'/proc/{pid}/cmdline', 'rb').read().replace(b'\0', b' ').decode(errors='replace')
        except OSError:
            continue
        if re.search(r'Tiberian Sun[\\/]Game\.exe', cmdline, re.I) and 'proton' not in cmdline.lower():
            pids.append(int(pid))
    return pids


def display():
    """The connected X display of the game window (opens it on first use)."""
    if state['display'] is None:
        try:
            state['display'] = x11.Display(DISPLAY)
        except RuntimeError:
            raise RuntimeError(f'Spielfenster ({DISPLAY}) läuft nicht – erst ts_start') from None
    return state['display']


def start_display(width: int, height: int):
    try:
        x11.Display(DISPLAY).close()
        return False  # already there (e.g. started by an earlier server)
    except RuntimeError:
        pass
    if not os.environ.get('WAYLAND_DISPLAY'):
        raise RuntimeError('Kein Wayland-Desktop (WAYLAND_DISPLAY fehlt) – Xwayland braucht einen Compositor')
    log = open(LOG, 'ab')
    state['xwayland'] = subprocess.Popen(
        ['Xwayland', DISPLAY, '-geometry', f'{width}x{height}', '-decorate', '-noreset'],
        stdout=log, stderr=log, start_new_session=True)
    for _ in range(50):
        time.sleep(0.1)
        try:
            x11.Display(DISPLAY).close()
            return True
        except RuntimeError:
            pass
    raise RuntimeError(f'Xwayland {DISPLAY} startet nicht, siehe {LOG}')


def snapshot(scale: int = 1, x: int = 0, y: int = 0, w: int | None = None, h: int | None = None):
    d = display()
    w = min(w or d.width, d.width - x)
    h = min(h or d.height, d.height - y)
    png = x11.png(*x11.scale_down(*d.capture(x, y, w, h), max(1, int(scale))))
    if magick := shutil.which('magick'):
        jpeg = subprocess.run([magick, 'png:-', '-quality', '85', 'jpg:-'], input=png, capture_output=True)
        if jpeg.returncode == 0:
            return Image(jpeg.stdout, 'image/jpeg')
    return Image(png)


def after(screenshot: bool, delay: float, text: str):
    if not screenshot:
        return text
    time.sleep(delay)
    return [text, snapshot()]


SCREENSHOT_ARGS = {
    'screenshot': {'type': 'boolean', 'default': False, 'description': 'danach einen Screenshot liefern'},
    'delay': {'type': 'number', 'default': 0.5, 'description': 'Sekunden bis zum Screenshot'},
}


@server.tool('ts_start', 'Startet Tiberian Sun (Proton) in einem eigenen Xwayland-Fenster und liefert nach dem Laden einen Screenshot. Esc überspringt Intros.', {
    'width': {'type': 'integer', 'default': 1024}, 'height': {'type': 'integer', 'default': 768},
    'wait': {'type': 'number', 'default': 20, 'description': 'Sekunden bis zum Screenshot'},
})
def ts_start(width: int = 1024, height: int = 768, wait: float = 20):
    if game_pids():
        return ['Läuft bereits.', snapshot()]
    new_display = start_display(width, height)
    if state['display'] is not None:
        state['display'].close()
        state['display'] = None
    game = os.path.join(GAME_DIR, 'Game.exe')
    if not os.path.exists(game):
        raise RuntimeError(f'{game} fehlt (TS_DIR setzen)')
    log = open(LOG, 'ab')
    state['game'] = subprocess.Popen(
        ['python3', os.path.join(proton_dir(), 'proton'), 'waitforexitandrun', game],
        cwd=GAME_DIR, env=compat_env(), stdout=log, stderr=log, start_new_session=True)
    deadline = time.time() + 60
    while not game_pids():
        if state['game'].poll() is not None or time.time() > deadline:
            raise RuntimeError(f'Game.exe startet nicht, siehe {LOG}')
        time.sleep(0.5)
    time.sleep(max(0, wait))
    d = display()
    return [f'Gestartet auf {DISPLAY} ({d.width}×{d.height}{", neues Fenster" if new_display else ""}).', snapshot()]


@server.tool('ts_stop', 'Beendet Tiberian Sun (alle Wine-Prozesse der Steam-Prefix) und schließt das Xwayland-Fenster.', {
    'keep_window': {'type': 'boolean', 'default': False},
})
def ts_stop(keep_window: bool = False):
    env = compat_env()
    env['WINEPREFIX'] = os.path.join(env['STEAM_COMPAT_DATA_PATH'], 'pfx')
    subprocess.run([os.path.join(proton_dir(), 'files/bin/wineserver'), '-k'], env=env, capture_output=True, timeout=30)
    for pid in game_pids():
        os.kill(pid, signal.SIGKILL)
    if state['display'] is not None:
        state['display'].close()
        state['display'] = None
    if not keep_window:
        for pid in filter(str.isdigit, os.listdir('/proc')):
            try:
                args = open(f'/proc/{pid}/cmdline', 'rb').read().split(b'\0')
            except OSError:
                continue
            if os.path.basename(args[0]) == b'Xwayland' and DISPLAY.encode() in args:
                os.kill(int(pid), signal.SIGTERM)
        state['xwayland'] = None
    return 'Beendet.'


@server.tool('ts_status', 'Ob das Spiel läuft, Display, Fenstergröße, Log-Datei.')
def ts_status():
    pids = game_pids()
    info = {'running': bool(pids), 'pids': pids, 'display': DISPLAY, 'log': LOG, 'game_dir': GAME_DIR}
    try:
        d = display()
        info['size'] = [d.width, d.height]
    except RuntimeError:
        info['size'] = None
    return info


# --- seeing and acting ---------------------------------------------------------------

@server.tool('ts_screenshot', 'Screenshot des Spielfensters. scale=2 halbiert die Auflösung (Koordinaten dann ×2); x/y/w/h schneiden einen Ausschnitt aus (in vollen Pixeln).', {
    'scale': {'type': 'integer', 'default': 1, 'enum': [1, 2, 3, 4]},
    'x': {'type': 'integer', 'default': 0}, 'y': {'type': 'integer', 'default': 0},
    'w': {'type': 'integer'}, 'h': {'type': 'integer'},
})
def ts_screenshot(scale: int = 1, x: int = 0, y: int = 0, w: int | None = None, h: int | None = None):
    return snapshot(scale, x, y, w, h)


BUTTONS = {'left': 1, 'middle': 2, 'right': 3}


def press_modifiers(d, modifiers, down):
    for name in (modifiers if down else reversed(modifiers)):
        d.key(d.keycode(name), down)


@server.tool('ts_click', 'Mausklick an (x, y). Links: auswählen/Befehl; rechts: abwählen bzw. (je nach Optionen) Befehl. modifiers z. B. ["ctrl"] (Zwangsangriff), ["shift"] (Auswahl erweitern), ["alt"] (Zwangsbewegen).', {
    'x': {'type': 'integer'}, 'y': {'type': 'integer'},
    'button': {'type': 'string', 'enum': ['left', 'right', 'middle'], 'default': 'left'},
    'double': {'type': 'boolean', 'default': False},
    'modifiers': {'type': 'array', 'items': {'type': 'string'}, 'default': []},
    **SCREENSHOT_ARGS,
}, ['x', 'y'])
def ts_click(x: int, y: int, button: str = 'left', double: bool = False, modifiers: list | None = None,
             screenshot: bool = False, delay: float = 0.5):
    d = display()
    modifiers = modifiers or []
    d.move(x, y)
    time.sleep(0.3)  # the game reads cursor and buttons once per frame; shorter presses get lost in menus
    press_modifiers(d, modifiers, True)
    for _ in range(2 if double else 1):
        d.button(BUTTONS[button], True)
        time.sleep(0.15)
        d.button(BUTTONS[button], False)
        time.sleep(0.1)
    press_modifiers(d, modifiers, False)
    return after(screenshot, delay, f'{button}-Klick auf ({x}, {y})')


@server.tool('ts_drag', 'Zieht mit gedrückter Taste von (x1, y1) nach (x2, y2) – mit links ein Auswahlrahmen für Einheiten.', {
    'x1': {'type': 'integer'}, 'y1': {'type': 'integer'}, 'x2': {'type': 'integer'}, 'y2': {'type': 'integer'},
    'button': {'type': 'string', 'enum': ['left', 'right', 'middle'], 'default': 'left'},
    **SCREENSHOT_ARGS,
}, ['x1', 'y1', 'x2', 'y2'])
def ts_drag(x1: int, y1: int, x2: int, y2: int, button: str = 'left', screenshot: bool = False, delay: float = 0.5):
    d = display()
    d.move(x1, y1)
    time.sleep(0.3)
    d.button(BUTTONS[button], True)
    time.sleep(0.1)
    steps = 12
    for i in range(1, steps + 1):
        d.move(x1 + (x2 - x1) * i // steps, y1 + (y2 - y1) * i // steps)
        time.sleep(0.03)
    time.sleep(0.1)
    d.button(BUTTONS[button], False)
    return after(screenshot, delay, f'Gezogen von ({x1}, {y1}) nach ({x2}, {y2})')


@server.tool('ts_move_mouse', 'Bewegt nur den Mauszeiger (Tooltips, Cursorform prüfen). Am Rand scrollt die Karte – dafür besser ts_scroll.', {
    'x': {'type': 'integer'}, 'y': {'type': 'integer'}, **SCREENSHOT_ARGS,
}, ['x', 'y'])
def ts_move_mouse(x: int, y: int, screenshot: bool = False, delay: float = 0.5):
    display().move(x, y)
    return after(screenshot, delay, f'Maus auf ({x}, {y})')


@server.tool('ts_key', 'Drückt Tasten nacheinander; Kombinationen mit "+", z. B. ["Escape"], ["ctrl+1"] (Gruppe 1 bilden), ["1"], ["s"] (Stopp), ["h"] (Basis), ["F1"]. X-Keysym-Namen gehen auch.', {
    'keys': {'type': 'array', 'items': {'type': 'string'}},
    'hold': {'type': 'number', 'default': 0.12, 'description': 'Sekunden je Tastendruck'},
    **SCREENSHOT_ARGS,
}, ['keys'])
def ts_key(keys: list, hold: float = 0.12, screenshot: bool = False, delay: float = 0.5):
    d = display()
    for combo in keys:
        parts = [p for p in re.split(r'\+(?!$)', combo) if p]
        codes = [d.keycode(p) for p in parts]
        for code in codes:
            d.key(code, True)
            time.sleep(0.02)
        time.sleep(hold)
        for code in reversed(codes):
            d.key(code, False)
        time.sleep(0.08)
    return after(screenshot, delay, f'Tasten: {", ".join(keys)}')


@server.tool('ts_type', 'Tippt einen Text (Namen, Chat, Spielstand-Namen).', {
    'text': {'type': 'string'}, **SCREENSHOT_ARGS,
}, ['text'])
def ts_type(text: str, screenshot: bool = False, delay: float = 0.5):
    d = display()
    shift = d.keycode('Shift_L')
    for char in text:
        name = {' ': 'space', '\n': 'Return'}.get(char) or x11.SHIFTED.get(char) or char
        upper = char.isupper() or char in x11.SHIFTED
        code = d.keycode(name)
        if upper:
            d.key(shift, True)
        d.key(code, True)
        time.sleep(0.03)
        d.key(code, False)
        if upper:
            d.key(shift, False)
        time.sleep(0.03)
    return after(screenshot, delay, f'Getippt: {text!r}')


@server.tool('ts_scroll', 'Scrollt die Karte: hält den Mauszeiger am Fensterrand (up/down/left/right, auch up-left …) für `seconds`.', {
    'direction': {'type': 'string'}, 'seconds': {'type': 'number', 'default': 0.5}, **SCREENSHOT_ARGS,
}, ['direction'])
def ts_scroll(direction: str, seconds: float = 0.5, screenshot: bool = True, delay: float = 0.2):
    d = display()
    x, y = d.width // 2, d.height // 2
    for part in direction.lower().split('-'):
        if part not in ('up', 'down', 'left', 'right'):
            raise ValueError(f'Richtung {direction}?')
        x = {'left': 0, 'right': d.width - 1}.get(part, x)
        y = {'up': 0, 'down': d.height - 1}.get(part, y)
    d.move(x, y)
    time.sleep(max(0.05, min(10, seconds)))
    d.move(d.width // 2, d.height // 2)
    return after(screenshot, delay, f'Gescrollt nach {direction} ({seconds} s)')


@server.tool('ts_wait', 'Wartet echte Sekunden (das Spiel läuft weiter) und liefert dann einen Screenshot.', {
    'seconds': {'type': 'number', 'default': 5}, 'scale': {'type': 'integer', 'default': 1, 'enum': [1, 2, 3, 4]},
})
def ts_wait(seconds: float = 5, scale: int = 1):
    time.sleep(max(0, min(300, seconds)))
    return snapshot(scale)


# --- original data -------------------------------------------------------------------

def ini_file(name: str):
    return mix.parse_ini(library.read(name).decode('latin-1'))


@server.tool('ts_rules', (
    'Liest eine Sektion aus den Original-INIs (aus den MIX-Archiven), z. B. section="E1", "GACNST", "Minigun", "General". '
    'Standard: rules.ini mit den Firestorm-Änderungen aus firestrm.ini darüber (wie im Spiel Firestorm); '
    'firestorm=false liefert reines rules.ini. file="ART.INI" (+ARTFS.INI), "AI.INI" (+AIFS.INI), "SOUND.INI" … geht auch.'
), {
    'section': {'type': 'string'},
    'file': {'type': 'string', 'default': 'RULES.INI'},
    'firestorm': {'type': 'boolean', 'default': True},
}, ['section'])
def ts_rules(section: str, file: str = 'RULES.INI', firestorm: bool = True):
    file = file.upper()
    values = dict(ini_file(file).get(section.upper(), {}))
    overrides = {'RULES.INI': 'FIRESTRM.INI', 'ART.INI': 'ARTFS.INI', 'AI.INI': 'AIFS.INI'}
    changed = {}
    if firestorm and file in overrides:
        for key, value in ini_file(overrides[file]).get(section.upper(), {}).items():
            existing = next((k for k in values if k.lower() == key.lower()), key)
            if values.get(existing) != value:
                changed[existing] = values.get(existing)
            values[existing] = value
    if not values:
        raise KeyError(f'Sektion [{section}] nicht in {file}')
    result = {'section': section.upper(), 'values': values}
    if changed:
        result['firestorm_changed_from'] = changed
    return result


@server.tool('ts_rules_search', 'Sucht in einer Original-INI (Standard rules.ini + firestrm.ini) per Regex in Sektionsnamen, Schlüsseln und Werten, z. B. "Cost=", "^Name=.*Titan", "Prerequisite=.*RADAR".', {
    'pattern': {'type': 'string', 'description': 'Regex (ohne Groß/Klein), geprüft gegen "[SEKTION]" und "Schlüssel=Wert"'},
    'file': {'type': 'string', 'default': 'RULES.INI'},
    'limit': {'type': 'integer', 'default': 80},
}, ['pattern'])
def ts_rules_search(pattern: str, file: str = 'RULES.INI', limit: int = 80):
    regex = re.compile(pattern, re.I)
    files = [file.upper()] + ([{'RULES.INI': 'FIRESTRM.INI', 'ART.INI': 'ARTFS.INI', 'AI.INI': 'AIFS.INI'}[file.upper()]]
                              if file.upper() in ('RULES.INI', 'ART.INI', 'AI.INI') else [])
    hits = []
    for name in files:
        for section, values in ini_file(name).items():
            if regex.search(f'[{section}]'):
                hits.append(f'{name} [{section}]')
            hits += [f'{name} [{section}] {k}={v}' for k, v in values.items() if regex.search(f'{k}={v}')]
            if len(hits) >= limit:
                return '\n'.join(hits[:limit]) + f'\n… (mehr als {limit} Treffer)'
    return '\n'.join(hits) or 'Keine Treffer'


@server.tool('ts_file', (
    'Findet eine Datei der Installation (lose oder in MIX-Archiven, auch verschachtelt; z. B. "E1.SHP", "RULES.INI", '
    '"MISSION.INI", "SOUND01.MIX"). Ohne save_to: Fundorte, Größe und bei Textdateien der Inhalt (offset/limit in Zeilen). '
    'Mit save_to (Verzeichnis): extrahiert die Datei dorthin, wie das Spiel sie nimmt.'
), {
    'name': {'type': 'string'}, 'save_to': {'type': 'string'},
    'offset': {'type': 'integer', 'default': 0}, 'limit': {'type': 'integer', 'default': 400},
}, ['name'])
def ts_file(name: str, save_to: str | None = None, offset: int = 0, limit: int = 400):
    data = library.read(name)
    if save_to:
        os.makedirs(save_to, exist_ok=True)
        path = os.path.join(save_to, name.upper())
        open(path, 'wb').write(data)
        return {'saved': path, 'bytes': len(data)}
    info = {'name': name.upper(), 'bytes': len(data), 'found_in': [a.name for a in library.find(name)] or ['(lose Datei)']}
    if name.lower().endswith(('.ini', '.txt', '.csf.txt', '.map', '.mpr')) or data[:1] == b'[':
        lines = data.decode('latin-1').splitlines()
        info['lines'] = f'{offset}–{min(len(lines), offset + limit)} von {len(lines)}'
        return [info, '\n'.join(lines[offset:offset + limit])]
    return info


@server.tool('ts_archives', 'Listet die MIX-Archive (auch verschachtelte) mit Eintragszahl; mit archive= deren Einträge (Hash, Größe, Name falls bekannt – Namen werden aus rules/art.ini abgeleitet).', {
    'archive': {'type': 'string', 'description': 'z. B. "TIBSUN.MIX/CONQUER.MIX"'},
})
def ts_archives(archive: str | None = None):
    archives = library.archives()
    if not archive:
        return '\n'.join(f'{a.name}  ({len(a.entries)} Einträge)' for a in archives)
    match = next((a for a in archives if a.name.lower() == archive.lower()), None)
    if not match:
        raise KeyError(f'{archive} unbekannt')
    names = known_names()
    out = io.StringIO()
    for h, (_, length) in sorted(match.entries.items(), key=lambda e: names.get(e[0], f'~{e[0]:08X}')):
        out.write(f'{h:08X} {length:>10}  {names.get(h, "")}\n')
    return out.getvalue()


_names = None


def known_names():
    """Hash → filename for names guessable from the INIs (objects and their images with the usual extensions)."""
    global _names
    if _names is None:
        ids = set(mix.KNOWN_NESTED) | {
            'MOUSE.SHP', 'PIPS.SHP', 'PIPS2.SHP', 'SIDEBAR.PAL', 'CAMEO.PAL', 'ANIM.PAL', 'UNITTEM.PAL', 'UNITSNO.PAL',
            'ISOTEM.PAL', 'ISOSNO.PAL', 'TEMPERAT.PAL', 'SNOW.PAL', 'PALETTE.PAL', 'MOUSEPAL.PAL', 'LIBTEM.PAL',
            'LIBSNO.PAL', 'TEMPERAT.INI', 'SNOW.INI', 'BATTLE.INI', 'MISSION.INI', 'THEME.INI', 'EVA.INI', 'TUTORIAL.INI',
            'MPMAPS.INI', 'TUTORIAL.INI',
        }
        for file in ('RULES.INI', 'FIRESTRM.INI', 'ART.INI', 'ARTFS.INI', 'SOUND.INI'):
            try:
                for section, values in ini_file(file).items():
                    ids.add(section)
                    ids.update(v.upper() for k, v in values.items() if k.lower() in ('image', 'cameo', 'alphaimage', 'buildup'))
                    if file == 'SOUND.INI':
                        ids.update(n.strip().upper() for v in values.values() for n in v.split(',') if n.strip())
            except FileNotFoundError:
                pass
        names = {}
        for base in ids:
            for ext in ('', '.SHP', '.VXL', '.HVA', '.AUD', '.INI', '.PAL', '.TEM', '.SNO', '.MIX', '.VQA', '.MAP', '.CSF'):
                for variant in (base, base + 'ICON', base + 'MK', base + 'BIB', base + 'UI'):
                    names[mix.hash_name(variant + ext)] = variant + ext
        _names = names
    return _names


if __name__ == '__main__':
    server.run()
