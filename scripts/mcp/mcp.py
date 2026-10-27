"""
Minimal MCP server over stdio (JSON-RPC 2.0, one message per line), standard library
only. A server registers its tools with `@server.tool(...)` and calls `server.run()`.

A tool returns a string, a dict/list (sent as JSON text), an `Image`, or a list
mixing those; raising an exception marks the call as failed with its message.
"""
import base64
import json
import sys
import traceback


class Image:
    def __init__(self, data: bytes, mime: str = 'image/png'):
        self.data = data
        self.mime = mime


class Server:
    def __init__(self, name: str, version: str, instructions: str = ''):
        self.name = name
        self.version = version
        self.instructions = instructions
        self.tools = {}

    def tool(self, name: str, description: str, properties: dict | None = None, required: list | None = None):
        """Registers a tool; `properties` is the JSON schema of its arguments."""
        def register(fn):
            self.tools[name] = {
                'fn': fn,
                'spec': {
                    'name': name,
                    'description': description,
                    'inputSchema': {'type': 'object', 'properties': properties or {}, 'required': required or []},
                },
            }
            return fn
        return register

    @staticmethod
    def _content(value):
        items = value if isinstance(value, list) and any(isinstance(v, Image) for v in value) else [value]
        content = []
        for item in items:
            if isinstance(item, Image):
                content.append({'type': 'image', 'data': base64.b64encode(item.data).decode(), 'mimeType': item.mime})
            elif isinstance(item, str):
                content.append({'type': 'text', 'text': item})
            elif item is not None:
                content.append({'type': 'text', 'text': json.dumps(item, ensure_ascii=False, indent=1)})
        return content

    def _handle(self, method: str, params: dict):
        if method == 'initialize':
            return {
                'protocolVersion': params.get('protocolVersion', '2025-06-18'),
                'capabilities': {'tools': {}},
                'serverInfo': {'name': self.name, 'version': self.version},
                **({'instructions': self.instructions} if self.instructions else {}),
            }
        if method == 'ping':
            return {}
        if method == 'tools/list':
            return {'tools': [t['spec'] for t in self.tools.values()]}
        if method == 'tools/call':
            tool = self.tools.get(params.get('name'))
            if not tool:
                raise LookupError(f'Unbekanntes Tool {params.get("name")}')
            try:
                return {'content': self._content(tool['fn'](**(params.get('arguments') or {})))}
            except Exception as error:  # the agent sees the message and can react
                if not isinstance(error, (RuntimeError, ValueError, KeyError, FileNotFoundError)):
                    print(traceback.format_exc(), file=sys.stderr)
                return {'content': [{'type': 'text', 'text': f'Fehler: {error}'}], 'isError': True}
        raise LookupError(f'Methode {method} nicht unterstützt')

    def run(self):
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if 'id' not in message:
                continue  # notifications (initialized, cancelled …) need no answer
            try:
                answer = {'jsonrpc': '2.0', 'id': message['id'], 'result': self._handle(message.get('method', ''), message.get('params') or {})}
            except LookupError as error:
                answer = {'jsonrpc': '2.0', 'id': message['id'], 'error': {'code': -32601, 'message': str(error)}}
            except Exception as error:
                answer = {'jsonrpc': '2.0', 'id': message['id'], 'error': {'code': -32603, 'message': str(error)}}
            sys.stdout.write(json.dumps(answer, ensure_ascii=False) + '\n')
            sys.stdout.flush()
