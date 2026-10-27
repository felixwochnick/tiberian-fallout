"""
Screenshots and synthetic mouse/keyboard input on an X display via Xlib and the
XTEST extension (ctypes, no extra packages). Used to play Tiberian Sun running in
its own Xwayland window.
"""
import ctypes
import ctypes.util
import struct
import zlib

_x = ctypes.CDLL(ctypes.util.find_library('X11') or 'libX11.so.6')
_xt = ctypes.CDLL(ctypes.util.find_library('Xtst') or 'libXtst.so.6')

_x.XOpenDisplay.restype = ctypes.c_void_p
_x.XOpenDisplay.argtypes = [ctypes.c_char_p]
_x.XCloseDisplay.argtypes = [ctypes.c_void_p]
_x.XDefaultRootWindow.restype = ctypes.c_ulong
_x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
_x.XDefaultScreen.argtypes = [ctypes.c_void_p]
_x.XDisplayWidth.argtypes = [ctypes.c_void_p, ctypes.c_int]
_x.XDisplayHeight.argtypes = [ctypes.c_void_p, ctypes.c_int]
_x.XFlush.argtypes = [ctypes.c_void_p]
_x.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
_x.XStringToKeysym.restype = ctypes.c_ulong
_x.XStringToKeysym.argtypes = [ctypes.c_char_p]
_x.XKeysymToKeycode.restype = ctypes.c_ubyte
_x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
_x.XGetImage.restype = ctypes.c_void_p
_x.XGetImage.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
                         ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong, ctypes.c_int]
_x.XFree.argtypes = [ctypes.c_void_p]
_xt.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
_xt.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
_xt.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]


class _XImage(ctypes.Structure):
    _fields_ = [
        ('width', ctypes.c_int), ('height', ctypes.c_int), ('xoffset', ctypes.c_int),
        ('format', ctypes.c_int), ('data', ctypes.POINTER(ctypes.c_ubyte)),
        ('byte_order', ctypes.c_int), ('bitmap_unit', ctypes.c_int), ('bitmap_bit_order', ctypes.c_int),
        ('bitmap_pad', ctypes.c_int), ('depth', ctypes.c_int), ('bytes_per_line', ctypes.c_int),
        ('bits_per_pixel', ctypes.c_int), ('red_mask', ctypes.c_ulong), ('green_mask', ctypes.c_ulong),
        ('blue_mask', ctypes.c_ulong), ('obdata', ctypes.c_void_p),
        # struct funcs { create_image, destroy_image, … }
        ('create_image', ctypes.c_void_p), ('destroy_image', ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)),
    ]


ALL_PLANES = 0xFFFFFFFF
Z_PIXMAP = 2

# names an agent may use for keys, mapped to X keysym names
KEY_ALIASES = {
    'esc': 'Escape', 'escape': 'Escape', 'enter': 'Return', 'return': 'Return', 'tab': 'Tab',
    'space': 'space', 'backspace': 'BackSpace', 'delete': 'Delete', 'del': 'Delete', 'insert': 'Insert',
    'home': 'Home', 'end': 'End', 'pageup': 'Prior', 'pagedown': 'Next',
    'up': 'Up', 'down': 'Down', 'left': 'Left', 'right': 'Right',
    'ctrl': 'Control_L', 'control': 'Control_L', 'shift': 'Shift_L', 'alt': 'Alt_L',
    '-': 'minus', '+': 'plus', '=': 'equal', ',': 'comma', '.': 'period', '/': 'slash',
}
SHIFTED = {'+': 'plus', '!': 'exclam', '?': 'question', ':': 'colon', '_': 'underscore'}


class Display:
    def __init__(self, name: str):
        self.name = name
        self.dpy = _x.XOpenDisplay(name.encode())
        if not self.dpy:
            raise RuntimeError(f'X-Display {name} nicht erreichbar')
        self.root = _x.XDefaultRootWindow(self.dpy)
        screen = _x.XDefaultScreen(self.dpy)
        self.width = _x.XDisplayWidth(self.dpy, screen)
        self.height = _x.XDisplayHeight(self.dpy, screen)

    def close(self):
        if self.dpy:
            _x.XCloseDisplay(self.dpy)
            self.dpy = None

    # --- input ---------------------------------------------------------------

    def move(self, x: int, y: int):
        _xt.XTestFakeMotionEvent(self.dpy, -1, int(x), int(y), 0)
        _x.XFlush(self.dpy)

    def button(self, button: int, down: bool):
        _xt.XTestFakeButtonEvent(self.dpy, button, 1 if down else 0, 0)
        _x.XFlush(self.dpy)

    def keycode(self, name: str) -> int:
        keysym_name = KEY_ALIASES.get(name.lower(), name)
        if len(keysym_name) == 1 and keysym_name.isalpha():
            keysym_name = keysym_name.lower()
        keysym = _x.XStringToKeysym(keysym_name.encode())
        code = _x.XKeysymToKeycode(self.dpy, keysym) if keysym else 0
        if not code:
            raise ValueError(f'Unbekannte Taste "{name}"')
        return code

    def key(self, code: int, down: bool):
        _xt.XTestFakeKeyEvent(self.dpy, code, 1 if down else 0, 0)
        _x.XFlush(self.dpy)

    def sync(self):
        _x.XSync(self.dpy, 0)

    # --- screenshot ----------------------------------------------------------

    def capture(self, x=0, y=0, w=None, h=None):
        """Raw RGB bytes of a screen area: (width, height, bytes)."""
        w = self.width - x if w is None else w
        h = self.height - y if h is None else h
        ptr = _x.XGetImage(self.dpy, self.root, x, y, w, h, ALL_PLANES, Z_PIXMAP)
        if not ptr:
            raise RuntimeError('XGetImage fehlgeschlagen')
        image = _XImage.from_address(ptr)
        try:
            if image.bits_per_pixel != 32:
                raise RuntimeError(f'Nur 32-Bit-Displays werden unterstützt ({image.bits_per_pixel})')
            stride = image.bytes_per_line
            raw = ctypes.string_at(image.data, stride * h)
        finally:
            image.destroy_image(ptr)
        rgb = bytearray(w * h * 3)
        for row in range(h):
            line = raw[row * stride: row * stride + w * 4]
            out = memoryview(rgb)[row * w * 3:(row + 1) * w * 3]
            out[0::3] = line[2::4]
            out[1::3] = line[1::4]
            out[2::3] = line[0::4]
        return w, h, bytes(rgb)


def scale_down(w: int, h: int, rgb: bytes, factor: int):
    """Keeps every `factor`-th pixel in both directions (nearest neighbour)."""
    if factor <= 1:
        return w, h, rgb
    nw, nh = w // factor, h // factor
    out = bytearray(nw * nh * 3)
    for row in range(nh):
        src = rgb[row * factor * w * 3: (row * factor * w + nw * factor) * 3]
        dst = memoryview(out)[row * nw * 3:(row + 1) * nw * 3]
        for c in range(3):
            dst[c::3] = src[c::3 * factor]
    return nw, nh, bytes(out)


def png(w: int, h: int, rgb: bytes) -> bytes:
    def chunk(kind: bytes, data: bytes):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
    stride = w * 3
    raw = b''.join(b'\x00' + rgb[r * stride:(r + 1) * stride] for r in range(h))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
