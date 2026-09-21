"""Servidor local de transporte para tests. Nunca se usa desde la aplicación."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import json


class FakeOllama:
    def __init__(self, extraction):
        self.extraction = extraction
        self.requests = []
        self.invalid_response = False
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def send_json(self, data):
                raw = json.dumps(data).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                self.send_json({'models': [{'name': 'test-local:latest'}, {'name': 'remote-cloud', 'remote_model': 'remote'}]})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                outer.requests.append(body)
                is_probe = 'mensaje' in body.get('format', {}).get('properties', {})
                answer = {'mensaje': 'Conexión correcta', 'resultado': 5} if is_probe else outer.extraction.model_dump()
                content = 'respuesta inválida' if outer.invalid_response else json.dumps(answer)
                self.send_json({'message': {'role': 'assistant', 'content': content}, 'done': True, 'done_reason': 'stop'})

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
