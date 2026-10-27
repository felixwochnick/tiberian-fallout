"""
Drives Chromium through the Chrome DevTools Protocol: a minimal WebSocket client
(standard library only) that sends commands and keeps the console messages and
uncaught exceptions of the page.
"""
import base64
import json
import os
import socket
import struct
import threading
import urllib.parse
import urllib.request
from collections import deque


class WebSocket:
    def __init__(self, url: str):
        parts = urllib.parse.urlparse(url)
        self.sock = socket.create_connection((parts.hostname, parts.port or 80), timeout=10)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((
            f'GET {parts.path} HTTP/1.1\r\nHost: {parts.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
            f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
        ).encode())
        head = b''
        while b'\r\n\r\n' not in head:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError('WebSocket-Handshake abgebrochen')
            head += chunk
        if b' 101 ' not in head.split(b'\r\n', 1)[0]:
            raise ConnectionError(head.split(b'\r\n', 1)[0].decode())
        self.buffer = head.split(b'\r\n\r\n', 1)[1]
        self.sock.settimeout(None)
        self.lock = threading.Lock()

    def send(self, text: str):
        data = text.encode()
        mask = os.urandom(4)
        n = len(data)
        header = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else
                                  bytes([0x80 | 126]) + struct.pack('>H', n) if n < 65536 else
                                  bytes([0x80 | 127]) + struct.pack('>Q', n))
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        with self.lock:
            self.sock.sendall(header + mask + masked)

    def _read(self, n: int):
        while len(self.buffer) < n:
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                raise ConnectionError('WebSocket geschlossen')
            self.buffer += chunk
        data, self.buffer = self.buffer[:n], self.buffer[n:]
        return data

    def receive(self) -> str:
        message = b''
        while True:
            b0, b1 = self._read(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack('>H', self._read(2))[0]
            elif n == 127:
                n = struct.unpack('>Q', self._read(8))[0]
            payload = self._read(n)
            opcode = b0 & 0x0F
            if opcode == 8:
                raise ConnectionError('WebSocket geschlossen')
            if opcode in (0, 1, 2):
                message += payload
                if b0 & 0x80:
                    return message.decode()

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class Page:
    """A connected page target: `call` runs a CDP method, `log` holds recent console output."""

    def __init__(self, ws_url: str):
        self.ws = WebSocket(ws_url)
        self.next_id = 0
        self.waiting = {}
        self.log = deque(maxlen=300)
        self.closed = False
        threading.Thread(target=self._reader, daemon=True).start()
        self.call('Runtime.enable')
        self.call('Page.enable')
        self.call('Log.enable')

    def _reader(self):
        try:
            while True:
                message = json.loads(self.ws.receive())
                if 'id' in message:
                    slot = self.waiting.pop(message['id'], None)
                    if slot:
                        slot['answer'] = message
                        slot['event'].set()
                else:
                    self._event(message.get('method'), message.get('params', {}))
        except (ConnectionError, OSError, ValueError):
            self.closed = True
            for slot in list(self.waiting.values()):
                slot['event'].set()

    def _event(self, method, params):
        if method == 'Runtime.consoleAPICalled':
            text = ' '.join(str(a.get('value', a.get('description', a.get('type')))) for a in params.get('args', []))
            self.log.append(f"[{params.get('type')}] {text}")
        elif method == 'Runtime.exceptionThrown':
            details = params.get('exceptionDetails', {})
            self.log.append(f"[exception] {details.get('exception', {}).get('description') or details.get('text')}")
        elif method == 'Log.entryAdded':
            entry = params.get('entry', {})
            self.log.append(f"[{entry.get('level')}] {entry.get('text')} {entry.get('url', '')}".rstrip())

    def call(self, method: str, timeout: float = 30, **params):
        if self.closed:
            raise ConnectionError('Verbindung zu Chromium verloren')
        self.next_id += 1
        slot = {'event': threading.Event()}
        self.waiting[self.next_id] = slot
        self.ws.send(json.dumps({'id': self.next_id, 'method': method, 'params': params}))
        if not slot['event'].wait(timeout) or 'answer' not in slot:
            self.waiting.pop(self.next_id, None)
            raise TimeoutError(f'{method}: keine Antwort von Chromium')
        answer = slot['answer']
        if 'error' in answer:
            raise RuntimeError(f"{method}: {answer['error'].get('message')}")
        return answer.get('result', {})

    def evaluate(self, expression: str, timeout: float = 30):
        result = self.call('Runtime.evaluate', timeout=timeout, expression=expression,
                           awaitPromise=True, returnByValue=True, userGesture=True)
        if 'exceptionDetails' in result:
            details = result['exceptionDetails']
            raise RuntimeError(details.get('exception', {}).get('description') or details.get('text'))
        return result.get('result', {}).get('value')

    def close(self):
        self.ws.close()


def targets(port: int):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list', timeout=3) as response:
        return json.load(response)
