"""
Reads files from Tiberian Sun MIX archives (also Blowfish-encrypted headers and nested
archives), a Python port of app/lib/formats/{mix,blowfish,hash,westwood-key}.ts.
"""
import base64
import os
import re
import struct
import zlib

ENTRY_SIZE = 12
FLAG_ENCRYPTED = 0x2
_TABLES = os.path.join(os.path.dirname(__file__), '../../app/lib/formats/blowfish-tables.ts')


def _load_tables():
    text = open(_TABLES, encoding='utf-8').read()
    p_part, s_part = text.split('BLOWFISH_S')
    numbers = lambda part: [int(n, 16) for n in re.findall(r'0x[0-9a-fA-F]+', part)]
    return numbers(p_part), numbers(s_part)


class Blowfish:
    _tables = None

    def __init__(self, key: bytes):
        Blowfish._tables = Blowfish._tables or _load_tables()
        p, s = Blowfish._tables
        self.p = list(p)
        self.s = list(s)
        j = 0
        for i in range(18):
            word = 0
            for _ in range(4):
                word = ((word << 8) | key[j % len(key)]) & 0xFFFFFFFF
                j += 1
            self.p[i] ^= word
        l = r = 0
        for i in range(0, 18, 2):
            l, r = self._encrypt(l, r)
            self.p[i], self.p[i + 1] = l, r
        for i in range(0, 1024, 2):
            l, r = self._encrypt(l, r)
            self.s[i], self.s[i + 1] = l, r

    def _f(self, x):
        s = self.s
        return ((((s[x >> 24] + s[256 + ((x >> 16) & 0xFF)]) & 0xFFFFFFFF) ^ s[512 + ((x >> 8) & 0xFF)]) + s[768 + (x & 0xFF)]) & 0xFFFFFFFF

    def _encrypt(self, l, r):
        for i in range(16):
            l ^= self.p[i]
            r ^= self._f(l)
            l, r = r, l
        return r ^ self.p[17], l ^ self.p[16]

    def _decrypt(self, l, r):
        for i in range(17, 1, -1):
            l ^= self.p[i]
            r ^= self._f(l)
            l, r = r, l
        return r ^ self.p[0], l ^ self.p[1]

    def decrypt(self, data: bytes) -> bytes:
        out = bytearray()
        for o in range(0, len(data) - len(data) % 8, 8):
            l, r = struct.unpack_from('>II', data, o)
            out += struct.pack('>II', *self._decrypt(l, r))
        return bytes(out)


_PUBLIC_KEY = base64.b64decode('AihRvNoIbTn85FZRYNZRcT+i6KpU+maCsEqr3Q5q+LDB5tH7Tz2qQ38V')
_MODULUS = int.from_bytes(_PUBLIC_KEY[2:2 + _PUBLIC_KEY[1]], 'big')


def decrypt_mix_key(source: bytes) -> bytes:
    out_block = (_MODULUS.bit_length() - 2) // 8
    in_block = out_block + 1
    dest = bytearray()
    for o in range(0, len(source) - in_block + 1, in_block):
        m = int.from_bytes(source[o:o + in_block], 'little')
        dest += (pow(m, 0x10001, _MODULUS) & ((1 << out_block * 8) - 1)).to_bytes(out_block, 'little')
    return bytes(dest[:56])


def hash_name(name: str) -> int:
    """Filename hash of TS/RA2 archives (CRC32 with Westwood's padding)."""
    data = bytearray(name.upper().encode('latin-1'))
    length = len(data)
    rounded = length & ~3
    if length != rounded:
        data.append(length - rounded)
        data += bytes([data[rounded]]) * (4 - length % 4 - 1)
    return zlib.crc32(bytes(data)) & 0xFFFFFFFF


class Mix:
    """An archive inside `path` starting at byte `base` (nested archives share the file)."""

    def __init__(self, path: str, name: str, base: int = 0, size: int | None = None):
        self.path, self.name, self.base = path, name, base
        self.size = os.path.getsize(path) - base if size is None else size
        with open(path, 'rb') as f:
            f.seek(base)
            head = f.read(4)
            if len(head) < 4:
                raise ValueError(f'{name}: zu klein')
            if struct.unpack_from('<H', head)[0] != 0:
                raise ValueError(f'{name}: kein TS-MIX (altes Format)')
            flags = struct.unpack_from('<H', head, 2)[0]
            if flags & ~3:
                raise ValueError(f'{name}: unbekannte Flags {flags:#x}')
            if flags & FLAG_ENCRYPTED:
                fish = Blowfish(decrypt_mix_key(f.read(80)))
                count = struct.unpack_from('<H', fish.decrypt(f.read(8)))[0]
                blocks = (13 + count * ENTRY_SIZE) // 8
                f.seek(base + 84)
                index = fish.decrypt(f.read(blocks * 8))
                self.data_start = 84 + blocks * 8
            else:
                index = f.read(6)
                count = struct.unpack_from('<H', index)[0]
                index += f.read(count * ENTRY_SIZE)
                self.data_start = 4 + 6 + count * ENTRY_SIZE
        if len(index) < 6 + count * ENTRY_SIZE:
            raise ValueError(f'{name}: Index unvollständig')
        self.entries = {}
        for i in range(count):
            h, offset, length = struct.unpack_from('<III', index, 6 + i * ENTRY_SIZE)
            if self.data_start + offset + length > self.size:
                raise ValueError(f'{name}: Eintrag hinter dem Dateiende')
            self.entries[h] = (offset, length)

    def get(self, name: str):
        return self.entries.get(hash_name(name))

    def read(self, entry) -> bytes:
        offset, length = entry
        with open(self.path, 'rb') as f:
            f.seek(self.base + self.data_start + offset)
            return f.read(length)

    def nested(self, h: int, name: str):
        """Opens the entry `h` as an archive, None if it is none."""
        offset, length = self.entries[h]
        if length < 64:
            return None
        try:
            return Mix(self.path, name, self.base + self.data_start + offset, length)
        except (ValueError, struct.error, IndexError):
            return None


# nested archives of TS and Firestorm (names so listings can show them)
KNOWN_NESTED = [
    'LOCAL.MIX', 'CACHE.MIX', 'CONQUER.MIX', 'SIDEC01.MIX', 'SIDEC02.MIX', 'ISOSNOW.MIX', 'ISOTEMP.MIX',
    'SNOW.MIX', 'TEMPERAT.MIX', 'SOUNDS.MIX', 'SOUNDS01.MIX', 'SPEECH01.MIX', 'SPEECH02.MIX', 'MAPS01.MIX',
    'MAPS02.MIX', 'MOVIES01.MIX', 'ECACHE01.MIX', 'ELOCAL01.MIX', 'ECONQ01.MIX', 'ESOUND01.MIX',
    'ISOSNO01.MIX', 'ISOTEM01.MIX', 'SNOW01.MIX', 'TEM01.MIX', 'E01SC01.MIX', 'E01SC02.MIX', 'E01VOX01.MIX',
    'E01VOX02.MIX', 'SIDENC01.MIX', 'SIDENC02.MIX', 'MULTI.MIX', 'SCORES.MIX', 'SCORES01.MIX',
]
_KNOWN_HASHES = {hash_name(n): n for n in KNOWN_NESTED}


def _priority(filename: str):
    """Order in which the game finds a file: expansions and patch first, as TS loads them."""
    lower = filename.lower()
    if m := re.match(r'expand(\d+)\.mix$', lower):
        return (0, -int(m.group(1)))
    if lower in ('patch.mix', 'ecache01.mix', 'elocal01.mix'):
        return (1, 0)
    if lower.startswith('movies'):
        return (3, lower)
    return (2, lower)


class Library:
    """All archives of a TS installation, nested ones included (opened lazily, cached)."""

    def __init__(self, directory: str):
        self.directory = directory
        self._archives = None

    def archives(self):
        if self._archives is None:
            found = []
            names = sorted((n for n in os.listdir(self.directory) if n.lower().endswith('.mix')), key=_priority)
            for name in names:
                try:
                    self._collect(Mix(os.path.join(self.directory, name), name), found)
                except (ValueError, struct.error):
                    continue
            self._archives = found
        return self._archives

    def _collect(self, archive: Mix, found: list, depth=0):
        found.append(archive)
        if depth > 2:
            return
        for h in archive.entries:
            label = _KNOWN_HASHES.get(h, f'{h:08X}.mix')
            inner = archive.nested(h, f'{archive.name}/{label}')
            if inner and inner.entries:
                self._collect(inner, found, depth + 1)

    def find(self, name: str):
        """Every archive holding `name`, the one the game uses first."""
        h = hash_name(name)
        return [a for a in self.archives() if h in a.entries]

    def read(self, name: str) -> bytes:
        loose = os.path.join(self.directory, name)
        for candidate in os.listdir(self.directory):
            if candidate.lower() == name.lower():
                return open(os.path.join(self.directory, candidate), 'rb').read()
        holders = self.find(name)
        if not holders:
            raise FileNotFoundError(f'{name} in keinem MIX-Archiv gefunden ({loose})')
        return holders[0].read(holders[0].entries[hash_name(name)])


def parse_ini(text: str):
    """Sections (upper case) → ordered key/value pairs, like app/lib/formats/ini.ts, but keeping key case."""
    ini = {}
    section = None
    for raw in text.splitlines():
        line = raw.split(';', 1)[0].strip()
        if not line:
            continue
        if line.startswith('[') and line.endswith(']'):
            section = ini.setdefault(line[1:-1].strip().upper(), {})
        elif '=' in line and section is not None:
            key, value = line.split('=', 1)
            section[key.strip()] = value.strip()
    return ini
