"""Una tele Samsung de mentira: REST y canal del mando por WebSocket en un solo puerto, sin TLS."""

import base64
import hashlib
import json
import socketserver
import struct
import threading
import time

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class MockTV:
    def __init__(self, model="18_KANTM2_UHD", model_name="UE55NU7405", network="wireless", token_auth=False,
                 apps=None, running=(), authorize=True):
        self.device = {
            "OS": "Tizen", "PowerState": "on", "TokenAuthSupport": "true" if token_auth else "false",
            "model": model, "modelName": model_name, "name": "[TV] Samsung 7 Series (55)",
            "networkType": network, "ssid": "MiCasa", "resolution": "3840x2160", "type": "Samsung SmartTV",
        }
        self.apps = apps if apps is not None else [
            {"appId": "11101200001", "name": "Netflix", "app_type": 2},
            {"appId": "111299001912", "name": "YouTube", "app_type": 2},
            {"appId": "3201907018807", "name": "Prime Video", "app_type": 2},
        ]
        self.running = set(running)
        self.authorize = authorize
        self.keys = []
        self.launched = []
        self.connect_urls = []
        self._active = 0
        self._lock = threading.Lock()
        tv = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                tv._handle(self.request)

        self.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def wait_idle(self, timeout=5):
        """Espera a que se hayan procesado todos los mensajes de los clientes ya desconectados."""
        end = time.time() + timeout
        while self._active and time.time() < end:
            time.sleep(0.01)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    # --- HTTP ---

    def _handle(self, conn):
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                return
            buf += chunk
        head = buf.split(b"\r\n\r\n", 1)[0].decode("latin-1").split("\r\n")
        method, path, _ = head[0].split(" ", 2)
        headers = {k.strip().lower(): v.strip() for k, _, v in (l.partition(":") for l in head[1:])}
        if headers.get("upgrade", "").lower() == "websocket":
            with self._lock:
                self._active += 1
            try:
                return self._websocket(conn, path, headers)
            finally:
                with self._lock:
                    self._active -= 1
        status, body = self._rest(method, path)
        data = json.dumps(body).encode()
        conn.sendall(f"HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {len(data)}\r\n"
                     f"Connection: close\r\n\r\n".encode() + data)

    def _rest(self, method, path):
        if path == "/api/v2/":
            return "200 OK", {"device": self.device, "type": "Samsung SmartTV", "version": "2.0.25"}
        prefix = "/api/v2/applications/"
        if path.startswith(prefix):
            app_id = path[len(prefix):]
            if app_id not in {a["appId"] for a in self.apps}:
                return "404 Not Found", {"code": 404}
            if method == "DELETE":
                self.running.discard(app_id)
                return "200 OK", True
            return "200 OK", {"id": app_id, "running": app_id in self.running, "visible": False}
        return "404 Not Found", {}

    # --- WebSocket ---

    def _websocket(self, conn, path, headers):
        self.connect_urls.append(path)
        accept = base64.b64encode(hashlib.sha1((headers["sec-websocket-key"] + WS_GUID).encode()).digest())
        conn.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                     b"Sec-WebSocket-Accept: " + accept + b"\r\n\r\n")
        if not self.authorize:
            self._send(conn, {"event": "ms.channel.unauthorized"})
            return
        self._send(conn, {"event": "ms.channel.connect", "data": {"token": "12345678", "clients": []}})
        self._send(conn, {"event": "ms.channel.ready", "data": {}})
        while True:
            text = self._recv(conn)
            if text is None:
                return
            msg = json.loads(text)
            params = msg.get("params", {})
            if msg.get("method") == "ms.remote.control":
                self.keys.append((params["Cmd"], params["DataOfCmd"]))
            elif params.get("event") == "ed.installedApp.get":
                self._send(conn, {"event": "ed.installedApp.get", "data": {"data": self.apps}})
            elif params.get("event") == "ed.apps.launch":
                self.launched.append(params["data"]["appId"])
                self.running.add(params["data"]["appId"])

    @staticmethod
    def _send(conn, obj):
        data = json.dumps(obj).encode()
        header = bytes([0x81]) + (bytes([len(data)]) if len(data) < 126 else bytes([126]) + struct.pack("!H", len(data)))
        conn.sendall(header + data)

    @staticmethod
    def _recv(conn):
        def read(n):
            data = b""
            while len(data) < n:
                chunk = conn.recv(n - len(data))
                if not chunk:
                    raise EOFError
                data += chunk
            return data
        try:
            b1, b2 = read(2)
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack("!H", read(2))[0]
            elif n == 127:
                n = struct.unpack("!Q", read(8))[0]
            mask = read(4)
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(read(n)))
        except (EOFError, OSError):
            return None
        if b1 & 0x0F == 0x8:
            return None
        return payload.decode()
