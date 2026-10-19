#!/usr/bin/env python3
"""CleanSamsungTV: limpia y diagnostica una tele Samsung (Tizen) desde el ordenador, por Wi-Fi.

Solo usa la biblioteca estándar de Python 3.8+, no hay que instalar nada:

    python3 tools/samsungtv.py buscar        # encuentra la tele en tu red
    python3 tools/samsungtv.py diagnostico   # modelo, año, red y qué hacer
    python3 tools/samsungtv.py limpiar       # cierra las apps que se quedan abiertas en memoria
    python3 tools/samsungtv.py guia          # te guía por los ajustes que solo se cambian con el mando

Habla con la API local que Samsung incluye en sus teles desde 2016: REST en el puerto 8001 y el
canal del mando a distancia por WebSocket (8001 sin cifrar en 2016-2017, 8002 con TLS y token
desde 2018). Tizen no tiene ADB, así que no puede desactivar paquetes del sistema como hace
cleanyourtv en Android TV: lo que no expone la API está en la guía.
"""

import argparse
import base64
import hashlib
import ipaddress
import json
import os
import re
import socket
import ssl
import statistics
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

APP_NAME = "CleanSamsungTV"
REST_PORT = 8001
WSS_PORT = 8002
WS_PATH = "/api/v2/channels/samsung.remote.control"
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
SSDP_TARGETS = ("urn:samsung.com:device:RemoteControlReceiver:1", "urn:dial-multiscreen-org:service:dial:1")
KEY_DELAY = 0.4  # pausa entre teclas: la tele descarta pulsaciones demasiado seguidas


class TVError(Exception):
    pass


# --- Configuración guardada (IP de la tele y token de emparejamiento) ---

def config_path():
    return os.environ.get("CLEANSAMSUNGTV_CONFIG") or os.path.join(os.path.expanduser("~"), ".cleansamsungtv.json")


def load_config():
    try:
        with open(config_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    path = config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    try:
        os.chmod(path, 0o600)  # el token permite controlar la tele
    except OSError:
        pass


# --- HTTP: siempre directo a la tele, sin pasar por un proxy del sistema ---

def _tv_tls_context():
    # La tele presenta un certificado autofirmado por Samsung que ningún sistema reconoce. La
    # conexión no sale de tu red local, así que se acepta igual que hace la app SmartThings.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


_opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=_tv_tls_context()))


def http_json(method, url, timeout=5):
    req = urllib.request.Request(url, method=method)
    with _opener.open(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
    try:
        return json.loads(body) if body.strip() else {}
    except ValueError:
        return body


# --- Cliente WebSocket mínimo (RFC 6455), lo justo para el canal del mando ---

class WebSocket:
    def __init__(self, url, timeout=10):
        parts = urllib.parse.urlsplit(url)
        secure = parts.scheme == "wss"
        port = parts.port or (443 if secure else 80)
        sock = socket.create_connection((parts.hostname, port), timeout=timeout)
        if secure:
            sock = _tv_tls_context().wrap_socket(sock, server_hostname=parts.hostname)
        self.sock = sock
        self._buf = b""
        key = base64.b64encode(os.urandom(16)).decode()
        path = parts.path + ("?" + parts.query if parts.query else "")
        self.sock.sendall((
            f"GET {path} HTTP/1.1\r\nHost: {parts.hostname}:{port}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode())
        while b"\r\n\r\n" not in self._buf:
            self._fill()
        head, self._buf = self._buf.split(b"\r\n\r\n", 1)
        lines = head.decode("latin-1").split("\r\n")
        if " 101 " not in lines[0] + " ":
            raise TVError(f"La tele no aceptó el WebSocket: {lines[0]}")
        headers = {k.strip().lower(): v.strip() for k, _, v in (l.partition(":") for l in lines[1:])}
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
        if headers.get("sec-websocket-accept") != accept:
            raise TVError("Respuesta WebSocket no válida")

    def _fill(self):
        chunk = self.sock.recv(65536)
        if not chunk:
            raise TVError("La tele cerró la conexión")
        self._buf += chunk

    def _read(self, n):
        while len(self._buf) < n:
            self._fill()
        data, self._buf = self._buf[:n], self._buf[n:]
        return data

    def _send_frame(self, opcode, payload):
        header = bytes([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header += bytes([0x80 | n])
        elif n < 65536:
            header += bytes([0x80 | 126]) + struct.pack("!H", n)
        else:
            header += bytes([0x80 | 127]) + struct.pack("!Q", n)
        mask = os.urandom(4)
        self.sock.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def send(self, text):
        self._send_frame(0x1, text.encode("utf-8"))

    def recv(self, timeout=None):
        self.sock.settimeout(timeout)
        message = b""
        while True:
            b1, b2 = self._read(2)
            opcode, n = b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack("!H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack("!Q", self._read(8))[0]
            mask = self._read(4) if b2 & 0x80 else None
            payload = self._read(n)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 0x8:
                raise TVError("La tele cerró la conexión")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            message += payload
            if b1 & 0x80:
                return message.decode("utf-8", "replace")

    def close(self):
        # Cierre ordenado: si cerráramos con mensajes de la tele sin leer, el sistema mandaría un RST
        # y la tele podría descartar la última tecla que le enviamos.
        try:
            self._send_frame(0x8, b"")
            self.sock.settimeout(1)
            while self.sock.recv(4096):
                pass
        except OSError:
            pass
        finally:
            self.sock.close()


# --- Año del modelo ---

SERIES_YEARS = {"HU": 2014, "JU": 2015, "JS": 2015, "KU": 2016, "KS": 2016, "MU": 2017, "NU": 2018,
                "RU": 2019, "TU": 2020, "AU": 2021, "BU": 2022, "CU": 2023, "DU": 2024}
QLED_YEARS = {"R": 2019, "T": 2020, "A": 2021, "B": 2022, "C": 2023, "D": 2024}


def model_year(device):
    """Año de la tele: el campo `model` empieza por él (p. ej. 18_KANTM2_UHD), si no, por el nombre."""
    m = re.match(r"(\d{2})_", device.get("model", ""))
    if m:
        return 2000 + int(m.group(1))
    name = device.get("modelName", "").upper()
    m = re.match(r"[A-Z]{2}\d{2}([A-Z]{2})\d", name)  # UE55NU7400, UN50RU7100...
    if m and m.group(1) in SERIES_YEARS:
        return SERIES_YEARS[m.group(1)]
    m = re.match(r"(?:QE|QN|QA|GQ)\d{2}QN?\d{2,3}([RTABCD])", name)  # QE55Q60R, QN65QN90A...
    if m:
        return QLED_YEARS[m.group(1)]
    return None


# --- La tele ---

class SamsungTV:
    def __init__(self, host, rest_port=REST_PORT, wss_port=WSS_PORT, timeout=5):
        self.host = host
        self.rest_port = rest_port
        self.wss_port = wss_port
        self.timeout = timeout
        self.ws = None
        self._info = None

    def info(self):
        if self._info is None:
            try:
                self._info = http_json("GET", f"http://{self.host}:{self.rest_port}/api/v2/", self.timeout)
            except (OSError, urllib.error.URLError) as e:
                raise TVError(
                    f"No hay respuesta de {self.host}:{self.rest_port} ({e}). ¿Está la tele encendida y en la "
                    "misma red? Las Samsung de 2015 o anteriores no tienen esta API: usa `guia`.") from e
        return self._info

    def device(self):
        return self.info().get("device", {})

    def token_auth(self):
        return str(self.device().get("TokenAuthSupport", "")).lower() == "true"

    def _app_url(self, app_id):
        base = (f"https://{self.host}:{self.wss_port}" if self.token_auth()
                else f"http://{self.host}:{self.rest_port}")
        return f"{base}/api/v2/applications/{urllib.parse.quote(app_id, safe='')}"

    def connect(self, wait_prompt=30):
        name = base64.b64encode(APP_NAME.encode()).decode()
        cfg = load_config()
        token = cfg.get("tokens", {}).get(self.host)
        if self.token_auth():
            url = f"wss://{self.host}:{self.wss_port}{WS_PATH}?name={name}"
            if token:
                url += f"&token={token}"
            else:
                print(f"Mira la tele: pulsa «Permitir» cuando pregunte por {APP_NAME} (solo la primera vez).")
        else:
            url = f"ws://{self.host}:{self.rest_port}{WS_PATH}?name={name}"
        try:
            ws = WebSocket(url, self.timeout)
        except OSError as e:
            raise TVError(f"No se pudo abrir el canal del mando: {e}") from e
        deadline = time.time() + wait_prompt
        while True:
            msg = self._recv_json(ws, deadline)
            event = msg.get("event")
            if event == "ms.channel.connect":
                new_token = (msg.get("data") or {}).get("token")
                if new_token and new_token != token:
                    cfg.setdefault("tokens", {})[self.host] = new_token
                    save_config(cfg)
                self.ws = ws
                return
            if event == "ms.channel.unauthorized":
                ws.close()
                raise TVError(
                    "La tele ha rechazado la conexión. Para volver a preguntar: Configuración > General > "
                    "Administrador de dispositivos externos > Administrador de conexión de dispositivos > "
                    f"Lista de dispositivos, borra {APP_NAME} y repite.")
            if event == "ms.channel.timeOut":
                ws.close()
                raise TVError("Nadie aceptó el aviso en la tele a tiempo. Repite y pulsa «Permitir».")

    @staticmethod
    def _recv_json(ws, deadline):
        remaining = deadline - time.time()
        if remaining <= 0:
            raise TVError("La tele no ha respondido a tiempo")
        try:
            return json.loads(ws.recv(timeout=remaining))
        except socket.timeout as e:
            raise TVError("La tele no ha respondido a tiempo") from e
        except ValueError:
            return {}

    def _emit(self, payload):
        if self.ws is None:
            self.connect()
        self.ws.send(json.dumps(payload))

    def send_key(self, key, cmd="Click"):
        self._emit({"method": "ms.remote.control", "params": {
            "Cmd": cmd, "DataOfCmd": key, "Option": "false", "TypeOfRemote": "SendRemoteKey"}})
        time.sleep(KEY_DELAY)

    def hold_key(self, key, seconds):
        self.send_key(key, "Press")
        time.sleep(seconds)
        self.send_key(key, "Release")

    def installed_apps(self, timeout=10):
        self._emit({"method": "ms.channel.emit", "params": {"event": "ed.installedApp.get", "to": "host"}})
        deadline = time.time() + timeout
        while True:
            msg = self._recv_json(self.ws, deadline)
            if msg.get("event") == "ed.installedApp.get":
                return (msg.get("data") or {}).get("data") or []

    def launch_app(self, app):
        action = "NATIVE_LAUNCH" if app.get("app_type") == 4 else "DEEP_LINK"
        self._emit({"method": "ms.channel.emit", "params": {
            "event": "ed.apps.launch", "to": "host",
            "data": {"appId": app["appId"], "action_type": action, "metaTag": ""}}})

    def app_running(self, app_id):
        """True o False, o None si la tele no informa de esa app."""
        try:
            status = http_json("GET", self._app_url(app_id), self.timeout)
        except (OSError, urllib.error.URLError):
            return None
        if isinstance(status, dict) and "running" in status:
            return bool(status["running"])
        return None

    def close_app(self, app_id):
        try:
            http_json("DELETE", self._app_url(app_id), self.timeout)
            return True
        except (OSError, urllib.error.URLError):
            return False

    def close(self):
        if self.ws:
            self.ws.close()
            self.ws = None


# --- Búsqueda en la red ---

def ssdp_search(wait=3.0):
    hosts = set()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(0.5)
    try:
        for target in SSDP_TARGETS:
            msg = (f"M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\n"
                   f"MX: 2\r\nST: {target}\r\n\r\n")
            sock.sendto(msg.encode(), ("239.255.255.250", 1900))
        end = time.time() + wait
        while time.time() < end:
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                continue
            if b"samsung" in data.lower() or b"dial" in data.lower():
                hosts.add(addr[0])
    except OSError:
        pass
    finally:
        sock.close()
    return hosts


def local_subnet():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # no envía nada, solo elige la interfaz de la red local
        ip = s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()
    return ipaddress.ip_network(f"{ip}/24", strict=False)


def port_scan(network, port=REST_PORT):
    def probe(ip):
        try:
            socket.create_connection((str(ip), port), timeout=0.4).close()
            return str(ip)
        except OSError:
            return None
    with ThreadPoolExecutor(max_workers=64) as pool:
        return {ip for ip in pool.map(probe, network.hosts()) if ip}


def describe(host):
    try:
        dev = SamsungTV(host, timeout=2).device()
    except TVError:
        return None
    if "samsung" not in json.dumps(dev).lower():
        return None
    return dev


def tcp_latency(host, port=REST_PORT, samples=10):
    times, lost = [], 0
    for _ in range(samples):
        t0 = time.perf_counter()
        try:
            socket.create_connection((host, port), timeout=2).close()
            times.append((time.perf_counter() - t0) * 1000)
        except OSError:
            lost += 1
        time.sleep(0.15)
    return times, lost


# --- Guía de ajustes que solo se pueden cambiar con el mando ---

OLD, NEW = "2016-2021", "2022+"

GUIDE = [
    {
        "id": "actualizar", "titulo": "Actualiza el software de la tele", "impacto": "alto",
        "por_que": "Samsung sigue corrigiendo fallos de memoria y de las apps de vídeo años después de la venta. "
                   "Una tele que nunca se ha actualizado arrastra errores que ya están resueltos.",
        "pasos": {OLD: "Configuración > Soporte > Actualización de software > Actualizar ahora. Activa también "
                       "«Actualización automática».",
                  NEW: "Configuración > Todos los ajustes > Soporte > Actualización de software > Actualizar ahora."},
    },
    {
        "id": "reinicio-frio", "titulo": "Haz un reinicio en frío (y repítelo cada semana)", "impacto": "alto",
        "por_que": "Apagar con el mando no apaga la tele: queda en reposo con la memoria llena de lo que tenías "
                   "abierto («Inicio instantáneo»). Tras semanas así se vuelve lenta y las apps se quedan "
                   "cargando. Un reinicio de verdad lo vacía todo.",
        "pasos": {OLD: "Con la tele encendida, mantén pulsado el botón de encendido del mando hasta que la pantalla "
                       "se apague y vuelva a salir el logo de Samsung (unos 5 segundos). Si no funciona, desenchúfala "
                       "1 minuto.",
                  NEW: "Igual: mantén pulsado el botón de encendido hasta ver el logo de Samsung, o desenchúfala "
                       "1 minuto."},
        "nota": "La herramienta lo intenta con `python3 tools/samsungtv.py reiniciar`.",
    },
    {
        "id": "autoejecutar", "titulo": "Que no se abran apps solas al encender", "impacto": "medio",
        "por_que": "Por defecto la tele arranca Smart Hub, la última app que usaste y a veces Samsung TV Plus en "
                   "cuanto se enciende, y todas compiten por la poca memoria que tiene.",
        "pasos": {OLD: "Configuración > General > Funciones inteligentes: desactiva «Ejecución automática de Smart "
                       "Hub», «Ejecutar automáticamente la última aplicación» y, si aparece, «Ejecución automática "
                       "de Samsung TV Plus».",
                  NEW: "Configuración > Todos los ajustes > General y privacidad > Opciones de la pantalla de inicio "
                       "(o «Funciones inteligentes»): desactiva el inicio automático de Smart Hub, de la última "
                       "aplicación y de Samsung TV Plus."},
    },
    {
        "id": "privacidad", "titulo": "Apaga el seguimiento y la publicidad en segundo plano", "impacto": "medio",
        "por_que": "«Servicios de información de visualización» analiza continuamente lo que sale en pantalla "
                   "(también por HDMI) para enviárselo a Samsung y sus anunciantes. Gasta procesador y red, y no "
                   "te aporta nada.",
        "pasos": {OLD: "Configuración > Soporte > Términos y privacidad > Configuración de privacidad (o «Términos "
                       "y políticas»): desactiva «Servicios de información de visualización» y «Anuncios basados en "
                       "intereses». Si no hablas a la tele, desactiva también los servicios de reconocimiento de voz.",
                  NEW: "Configuración > Todos los ajustes > General y privacidad > Términos y privacidad: desactiva "
                       "«Servicios de información de visualización» y «Anuncios basados en intereses». En "
                       "General y privacidad > Voz desactiva «Activación por voz» si no usas Bixby/Alexa."},
    },
    {
        "id": "apps", "titulo": "Borra las apps que no usas", "impacto": "medio",
        "por_que": "Muchas teles traen unas 2-4 GB de almacenamiento y menos de 2 GB de memoria. Con el "
                   "almacenamiento casi lleno las apps no pueden guardar su caché y cargan todo de nuevo cada vez.",
        "pasos": {OLD: "Inicio > Apps > Configuración (rueda arriba a la derecha) > selecciona la app > Eliminar.",
                  NEW: "Inicio > Apps > Configuración de apps (rueda) > selecciona la app > Eliminar."},
        "nota": "`python3 tools/samsungtv.py apps` lista lo que tienes instalado.",
    },
    {
        "id": "device-care", "titulo": "Pasa el «Cuidado del dispositivo»", "impacto": "medio", "desde": 2020,
        "por_que": "Desde 2020 la tele trae un limpiador que cierra procesos y libera memoria.",
        "pasos": {OLD: "Configuración > Soporte > Cuidado del dispositivo > Iniciar cuidado del dispositivo.",
                  NEW: "Configuración > Todos los ajustes > Soporte > Cuidado del dispositivo > Iniciar cuidado "
                       "del dispositivo."},
    },
    {
        "id": "cache", "titulo": "Vacía la caché de la app que se queda cargando", "impacto": "alto",
        "por_que": "Una caché corrupta es la causa más habitual de que una app concreta (Netflix, YouTube, "
                   "Prime Video, Disney+...) se quede en la pantalla de carga.",
        "pasos": {OLD: "En teles de 2020-2021: Configuración > Soporte > Cuidado del dispositivo > Gestionar "
                       "almacenamiento > marca la app > Ver detalles > Borrar caché. En 2016-2019 no existe ese "
                       "botón: elimina la app y vuelve a instalarla desde Apps.",
                  NEW: "Configuración > Todos los ajustes > Soporte > Cuidado del dispositivo > Gestionar "
                       "almacenamiento > marca la app > Ver detalles > Borrar caché."},
    },
    {
        "id": "red", "titulo": "Mejora la conexión", "impacto": "alto",
        "por_que": "Si la serie se para a cargar a mitad, casi siempre es la red y no la tele: el Wi-Fi de las "
                   "teles es flojo y está detrás del mueble. Netflix pide unos 5 Mbps en HD y 15-25 Mbps en 4K.",
        "pasos": {OLD: "Si puedes, conecta un cable de red. Si no, usa la red de 5 GHz del router y acerca el router "
                       "o pon un repetidor. Comprueba con Configuración > Soporte > Autodiagnóstico > Prueba de "
                       "conexión de Smart Hub.",
                  NEW: "Si puedes, conecta un cable de red. Si no, usa la red de 5 GHz. Comprueba con Configuración "
                       "> Todos los ajustes > Soporte > Cuidado del dispositivo > Autodiagnóstico > Prueba de "
                       "conexión de Smart Hub."},
    },
    {
        "id": "dns", "titulo": "Cambia el DNS", "impacto": "medio",
        "por_que": "El DNS de muchas operadoras es lento o falla a ratos, y la tele se queda «cargando» antes de "
                   "empezar a reproducir. Un DNS público suele arreglarlo.",
        "pasos": {OLD: "Configuración > General > Red > Estado de red > Configuración IP > Configuración DNS: "
                       "Introducir manualmente > 1.1.1.1 (o 8.8.8.8) > Aceptar.",
                  NEW: "Configuración > Todos los ajustes > Conexión > Red > Estado de red > Configuración IP > "
                       "Configuración DNS: Introducir manualmente > 1.1.1.1 (o 8.8.8.8) > Aceptar."},
        "nota": "Opcional: 94.140.14.14 (AdGuard DNS) además bloquea los anuncios y el rastreo de Samsung en la "
                "pantalla de inicio. No quita los anuncios de YouTube. Si alguna app deja de funcionar, vuelve a "
                "«Obtener automáticamente».",
    },
    {
        "id": "calidad", "titulo": "Si la red no da para más, baja la calidad en la app", "impacto": "bajo",
        "por_que": "Con una conexión justa es mejor ver en HD sin cortes que en 4K parándose cada minuto.",
        "pasos": {OLD: "Dentro de cada app: en Netflix, desde netflix.com > Cuenta > Perfil > Uso de datos; en "
                       "YouTube, en el vídeo > Configuración > Calidad.",
                  NEW: "Igual que en teles anteriores: la calidad se elige dentro de cada app."},
    },
    {
        "id": "reset-smarthub", "titulo": "Último recurso: restablece Smart Hub", "impacto": "alto",
        "por_que": "Borra todas las apps, sus datos y sesiones, pero no tus canales ni los ajustes de imagen. "
                   "Arregla la mayoría de teles que siguen lentas después de todo lo anterior.",
        "pasos": {OLD: "Configuración > Soporte > Autodiagnóstico > Restablecer Smart Hub (PIN por defecto: 0000).",
                  NEW: "Configuración > Todos los ajustes > Soporte > Cuidado del dispositivo > Autodiagnóstico > "
                       "Restablecer Smart Hub (PIN por defecto: 0000)."},
        "nota": "Después tendrás que volver a instalar las apps e iniciar sesión en cada una.",
    },
]

GUIDE_END = (
    "Si tu tele es de 2017 o anterior y sigue lenta después de todo esto, el problema es el hardware: las "
    "apps de hoy piden más memoria de la que trae. Un Chromecast con Google TV, un Fire TV Stick o un "
    "Google TV Streamer conectado por HDMI (30-100 €) va fluido, y a ese aparato sí se le puede aplicar "
    "cleanyourtv (https://github.com/Gathin23/cleanyourtv) para quitarle la publicidad."
)


def year_group(year):
    return NEW if year and year >= 2022 else OLD


def guide_markdown():
    out = [
        "# Guía de ajustes para una Samsung lenta",
        "",
        "<!-- Generado con `python3 tools/samsungtv.py guia --markdown > GUIA.md`; edita GUIDE en "
        "tools/samsungtv.py, no este archivo. -->",
        "",
        "Lo que la tele no deja cambiar por la red se cambia con el mando. Ve en orden: los primeros pasos "
        "son los que más ayudan. Los nombres de los menús pueden variar un poco según el modelo y la versión "
        "del software.",
        "",
        "`python3 tools/samsungtv.py guia` te lleva paso a paso y salta lo que tu tele no tiene.",
        "",
    ]
    for n, step in enumerate(GUIDE, 1):
        out.append(f"## {n}. {step['titulo']}")
        out.append("")
        extra = f" · teles de {step['desde']} en adelante" if step.get("desde") else ""
        out.append(f"*Impacto: {step['impacto']}{extra}*")
        out.append("")
        out.append(step["por_que"])
        out.append("")
        out.append(f"- **Teles de 2016 a 2021:** {step['pasos'][OLD]}")
        out.append(f"- **Teles de 2022 en adelante:** {step['pasos'][NEW]}")
        if step.get("nota"):
            out.append("")
            out.append(step["nota"])
        out.append("")
    out.append("## Y si nada de esto basta")
    out.append("")
    out.append(GUIDE_END)
    out.append("")
    return "\n".join(out)


# --- Comandos ---

def resolve_host(args):
    host = args.ip or os.environ.get("TV_HOST") or load_config().get("ip")
    if not host:
        raise TVError("No sé la IP de la tele. Ejecuta primero `buscar` o pasa --ip 192.168.1.50.")
    return host


def remember_host(host):
    cfg = load_config()
    if cfg.get("ip") != host:
        cfg["ip"] = host
        save_config(cfg)


def tv_from(args):
    return SamsungTV(resolve_host(args), rest_port=args.puerto, wss_port=args.puerto_tls)


def cmd_buscar(args):
    print("Buscando teles Samsung en la red...")
    candidates = ssdp_search()
    found = {h: d for h, d in ((h, describe(h)) for h in sorted(candidates)) if d}
    if not found:
        net = local_subnet()
        if net:
            print(f"No han contestado al aviso de red, pruebo uno a uno en {net}...")
            found = {h: d for h, d in ((h, describe(h)) for h in sorted(port_scan(net))) if d}
    if not found:
        print("No he encontrado ninguna. Comprueba que la tele está encendida (no en reposo) y en la misma red, "
              "o mira su IP en Configuración > General > Red > Estado de red y usa --ip.")
        return 1
    for host, dev in found.items():
        print(f"  {host}  {dev.get('name', '?')}  ({dev.get('modelName', '?')})")
    if len(found) == 1:
        remember_host(next(iter(found)))
        print("Guardada como tu tele: los demás comandos ya no necesitan --ip.")
    return 0


def cmd_info(args):
    tv = tv_from(args)
    dev = tv.device()
    remember_host(tv.host)
    year = model_year(dev)
    rows = [
        ("Nombre", dev.get("name")),
        ("Modelo", dev.get("modelName")),
        ("Plataforma", dev.get("model")),
        ("Año", year or "desconocido"),
        ("Sistema", dev.get("OS")),
        ("Resolución", dev.get("resolution")),
        ("Red", {"wireless": "Wi-Fi", "wired": "cable"}.get(dev.get("networkType"), dev.get("networkType"))),
        ("Wi-Fi", dev.get("ssid")),
        ("Encendida", dev.get("PowerState", "on")),
        ("Necesita emparejar", "sí (puerto 8002)" if tv.token_auth() else "no (puerto 8001)"),
    ]
    for label, value in rows:
        if value:
            print(f"{label + ':':<20} {value}")
    if args.json:
        print(json.dumps(tv.info(), indent=2, ensure_ascii=False))
    return 0


def _apps_with_state(tv):
    apps = tv.installed_apps()
    with ThreadPoolExecutor(max_workers=8) as pool:
        states = list(pool.map(lambda a: tv.app_running(a["appId"]), apps))
    return list(zip(apps, states))


def cmd_apps(args):
    tv = tv_from(args)
    try:
        items = _apps_with_state(tv)
    finally:
        tv.close()
    print(f"{len(items)} apps instaladas (* = abierta ahora en memoria):")
    for app, running in sorted(items, key=lambda x: x[0].get("name", "").lower()):
        print(f"  {'*' if running else ' '} {app.get('name', '?'):<30} {app['appId']}")
    print("\nPara borrar las que no uses: Inicio > Apps > Configuración > Eliminar (paso «apps» de la guía).")
    return 0


def cmd_limpiar(args):
    tv = tv_from(args)
    try:
        items = _apps_with_state(tv)
        running = [app for app, state in items if state]
        if not running:
            print("No había ninguna app abierta en segundo plano.")
        for app in running:
            ok = tv.close_app(app["appId"])
            print(f"  {'Cerrada' if ok else 'No se pudo cerrar'}: {app.get('name', app['appId'])}")
        tv.send_key("KEY_HOME")
    finally:
        tv.close()
    unknown = sum(1 for _, state in items if state is None)
    if unknown == len(items) and items:
        print("Esta tele no informa de qué apps están abiertas. Un reinicio en frío las cierra todas: `reiniciar`.")
    else:
        print(f"Listo: {len(running)} apps cerradas. Para vaciar la memoria del todo, haz un reinicio en frío "
              "(`reiniciar`).")
    return 0


def cmd_reiniciar(args):
    if not args.si:
        answer = input("Se reiniciará la tele (lo que estés viendo se cortará). ¿Seguir? [s/N] ").strip().lower()
        if answer not in ("s", "si", "sí", "y", "yes"):
            return 1
    tv = tv_from(args)
    try:
        print("Manteniendo pulsado el botón de encendido...")
        tv.hold_key("KEY_POWER", args.segundos)
    finally:
        tv.close()
    print("Hecho. Si ves el logo de Samsung, se está reiniciando. Si solo se ha apagado, enciéndela con el mando: "
          "tu modelo no reinicia así y el reinicio en frío hay que hacerlo con el mando (paso «reinicio-frio» "
          "de la guía) o desenchufándola 1 minuto.")
    return 0


def cmd_diagnostico(args):
    tv = tv_from(args)
    dev = tv.device()
    remember_host(tv.host)
    year = model_year(dev)
    print(f"Tele: {dev.get('name', '?')} · {dev.get('modelName', '?')} · {year or 'año desconocido'}\n")
    advice = []  # (id de la guía, motivo)

    if year and year <= 2017:
        print(f"! Es una tele de {year}: tiene poca memoria para las apps de hoy. Lo de abajo ayuda, pero no "
              "esperes que vaya como nueva.")
        advice.append(("reinicio-frio", "con tan poca memoria, reiniciar a menudo es lo que más se nota"))
    else:
        advice.append(("reinicio-frio", "apagar con el mando no vacía la memoria"))

    wireless = dev.get("networkType") == "wireless"
    print(f"{'!' if wireless else '✓'} Conectada por {'Wi-Fi' if wireless else 'cable'}"
          + (f" a «{dev['ssid']}»" if wireless and dev.get("ssid") else ""))

    times, lost = tcp_latency(tv.host, tv.rest_port, samples=args.muestras)
    unstable = bool(lost)
    if times:
        med, worst = statistics.median(times), max(times)
        unstable = unstable or med > 30 or worst > 150
        print(f"{'!' if unstable else '✓'} Latencia ordenador→tele: mediana {med:.0f} ms, peor {worst:.0f} ms, "
              f"{lost} de {args.muestras} perdidas")
    if unstable:
        advice.append(("red", "la conexión con la tele es inestable (o lo es la del ordenador)"))
    elif wireless:
        advice.append(("red", "el Wi-Fi es lo primero que falla cuando una serie se queda cargando"))

    try:
        items = _apps_with_state(tv)
        running = [app.get("name", app["appId"]) for app, state in items if state]
        print(f"{'!' if len(running) > 2 else '✓'} {len(items)} apps instaladas, {len(running)} abiertas en "
              f"memoria{': ' + ', '.join(running) if running else ''}")
        if running:
            advice.append(("limpiar", f"hay {len(running)} apps ocupando memoria (`limpiar` las cierra)"))
        if len(items) > 25:
            advice.append(("apps", f"tienes {len(items)} apps; borra las que no uses"))
    except TVError as e:
        print(f"· No he podido ver las apps: {e}")
    finally:
        tv.close()

    advice.append(("actualizar", "las actualizaciones arreglan fallos de rendimiento"))
    advice.append(("cache", "si una app concreta se queda cargando, suele ser su caché"))
    advice.append(("autoejecutar", "evita que Smart Hub y la última app arranquen solas"))
    advice.append(("privacidad", "el análisis de pantalla en segundo plano consume recursos"))
    advice.append(("dns", "el DNS de la operadora puede retrasar el inicio de cada vídeo"))
    if year and year >= 2020:
        advice.append(("device-care", "tu tele trae limpiador propio"))

    print("\nQué hacer, en este orden:")
    for n, (step, why) in enumerate(advice, 1):
        print(f"  {n}. {step}: {why}")
    print("\n`python3 tools/samsungtv.py guia` te explica cada paso con los menús de tu tele.")
    return 0


def cmd_tecla(args):
    tv = tv_from(args)
    try:
        for key in args.teclas:
            key = key.upper()
            tv.send_key(key if key.startswith("KEY_") else "KEY_" + key)
    finally:
        tv.close()
    return 0


def _find_app(tv, query):
    apps = tv.installed_apps()
    q = query.lower()
    exact = [a for a in apps if a["appId"] == query or a.get("name", "").lower() == q]
    matches = exact or [a for a in apps if q in a.get("name", "").lower()]
    if not matches:
        raise TVError(f"No hay ninguna app que se llame «{query}». Mira la lista con `apps`.")
    if len(matches) > 1:
        raise TVError("Hay varias: " + ", ".join(a.get("name", a["appId"]) for a in matches))
    return matches[0]


def cmd_abrir(args):
    tv = tv_from(args)
    try:
        app = _find_app(tv, args.app)
        tv.launch_app(app)
        time.sleep(KEY_DELAY)
    finally:
        tv.close()
    print(f"Abriendo {app.get('name', app['appId'])}")
    return 0


def cmd_cerrar(args):
    tv = tv_from(args)
    try:
        app = _find_app(tv, args.app)
    finally:
        tv.close()
    ok = tv.close_app(app["appId"])
    print(f"{'Cerrada' if ok else 'No se pudo cerrar'}: {app.get('name', app['appId'])}")
    return 0 if ok else 1


def cmd_guia(args):
    if args.markdown:
        sys.stdout.write(guide_markdown())
        return 0
    year = args.anyo
    if not year and (args.ip or os.environ.get("TV_HOST") or load_config().get("ip")):
        try:
            year = model_year(tv_from(args).device())
        except TVError:
            pass
    if not year:
        raw = input("¿De qué año es tu tele? (mira la etiqueta de atrás o Configuración > Soporte > "
                    "Acerca de este TV; Intro si no lo sabes) ").strip()
        year = int(raw) if raw.isdigit() else None
    if year and year < 2016:
        print("Tu tele es anterior a 2016: los menús son distintos y esta herramienta no puede conectarse a ella, "
              "pero las ideas de cada paso sirven igual.")
    group = year_group(year)
    steps = [s for s in GUIDE if not (s.get("desde") and year and year < s["desde"])]
    done, skipped = [], []
    print(f"\n{len(steps)} pasos. Responde s (hecho), n (saltar) o q (salir).\n")
    for n, step in enumerate(steps, 1):
        print(f"{n}/{len(steps)}  {step['titulo']}  [impacto {step['impacto']}]")
        print(f"   Por qué: {step['por_que']}")
        print(f"   Cómo:    {step['pasos'][group]}")
        if step.get("nota"):
            print(f"   Nota:    {step['nota']}")
        answer = input("   ¿Hecho? [s/n/q] ").strip().lower()
        print()
        if answer == "q":
            break
        (done if answer in ("s", "si", "sí", "y") else skipped).append(step["id"])
    print(f"Hechos: {', '.join(done) or 'ninguno'}")
    if skipped:
        print(f"Pendientes: {', '.join(skipped)}")
    if year is None or year <= 2017:
        print("\n" + GUIDE_END)
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="samsungtv.py", description="Limpia y diagnostica una tele Samsung (Tizen).")
    p.add_argument("--ip", help="IP de la tele (o variable TV_HOST; por defecto la guardada por `buscar`)")
    p.add_argument("--puerto", type=int, default=REST_PORT, help=argparse.SUPPRESS)
    p.add_argument("--puerto-tls", type=int, default=WSS_PORT, help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd", required=True, metavar="comando")

    sub.add_parser("buscar", help="encuentra la tele en tu red").set_defaults(func=cmd_buscar)
    s = sub.add_parser("info", help="modelo, año, red")
    s.add_argument("--json", action="store_true", help="muestra también la respuesta completa de la tele")
    s.set_defaults(func=cmd_info)
    s = sub.add_parser("diagnostico", help="revisa la tele y te dice qué hacer")
    s.add_argument("--muestras", type=int, default=10, help="mediciones de latencia (10)")
    s.set_defaults(func=cmd_diagnostico)
    sub.add_parser("apps", help="lista las apps instaladas y cuáles están abiertas").set_defaults(func=cmd_apps)
    sub.add_parser("limpiar", help="cierra las apps abiertas en segundo plano").set_defaults(func=cmd_limpiar)
    s = sub.add_parser("reiniciar", help="reinicio en frío (mantiene pulsado encendido; experimental)")
    s.add_argument("--si", action="store_true", help="no pedir confirmación")
    s.add_argument("--segundos", type=float, default=5.0, help="cuánto mantener pulsado (5)")
    s.set_defaults(func=cmd_reiniciar)
    s = sub.add_parser("tecla", help="pulsa teclas del mando: tecla HOME, tecla KEY_VOLUP...")
    s.add_argument("teclas", nargs="+")
    s.set_defaults(func=cmd_tecla)
    s = sub.add_parser("abrir", help="abre una app por nombre")
    s.add_argument("app")
    s.set_defaults(func=cmd_abrir)
    s = sub.add_parser("cerrar", help="cierra una app por nombre")
    s.add_argument("app")
    s.set_defaults(func=cmd_cerrar)
    s = sub.add_parser("guia", help="te guía por los ajustes que se cambian con el mando")
    s.add_argument("--anyo", type=int, help="año de la tele, si no se detecta")
    s.add_argument("--markdown", action="store_true", help="imprime la guía completa en Markdown")
    s.set_defaults(func=cmd_guia)
    return p


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")  # consolas de Windows sin UTF-8: «✓» no debe romper nada
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except TVError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print()
        return 130


if __name__ == "__main__":
    sys.exit(main())
