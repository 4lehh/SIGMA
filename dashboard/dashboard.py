"""
SIGMA Dashboard
- Escucha tráfico UDP en el mismo puerto que el server (modo espía)
- Brodadcast de datos a todos los clientes WebSocket conectados
- Sirve el HTML del dashboard
"""

import asyncio
import json
import socket
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import websockets

UDP_HOST    = "0.0.0.0"
UDP_PORT    = 9002          # Puerto "espía" distinto al server principal
WS_PORT     = 8765
HTTP_PORT   = 8080

ROOM_LABELS = {0: "Germinación", 1: "Vegetativo", 2: "Floración"}

sensors_state: dict[str, dict] = {}          # { "Sensor N°1": { ...datos... } }
ws_clients:    set              = set()
state_lock                      = threading.Lock()

async def ws_handler(websocket):
    ws_clients.add(websocket)
    try:
        # Enviar estado actual al conectarse
        with state_lock:
            snapshot = dict(sensors_state)
        if snapshot:
            await websocket.send(json.dumps({"type": "snapshot", "data": snapshot}))
        async for _ in websocket:
            pass   # No esperamos mensajes del cliente
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        ws_clients.discard(websocket)


async def broadcast(payload: dict):
    if not ws_clients:
        return
    msg = json.dumps(payload)
    await asyncio.gather(
        *[ws.send(msg) for ws in list(ws_clients)],
        return_exceptions=True,
    )


def udp_sniffer(loop: asyncio.AbstractEventLoop):
    """
    Corre en hilo separado.
    Re-envía al server real y captura la data para el dashboard.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_HOST, UDP_PORT))
    sock.settimeout(1.0)

    print(f"[UDP Sniffer] Escuchando en {UDP_HOST}:{UDP_PORT}")

    while True:
        try:
            data, addr = sock.recvfrom(4096)
        except socket.timeout:
            continue

        try:
            packet = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        sensor_id = packet.get("identificador", f"Sensor@{addr[1]}")
        room_type  = int(packet.get("room_type", 1))

        entry = {
            "identificador": sensor_id,
            "room_type":     room_type,
            "room_label":    ROOM_LABELS.get(room_type, "Desconocido"),
            "room_temp":     round(float(packet.get("room_temp", 0)), 3),
            "humidity":      round(float(packet.get("humidity", 0)), 3),
            "leaf_temp":     round(float(packet.get("leaf_temp", 0)), 3),
            "VPD":           round(float(packet.get("VPD", 0)), 4),
            "timestamp":     time.strftime("%H:%M:%S"),
            "actuators":     packet.get("actuators", {"cooling": 0, "heating": 0, "humidifier": 0, "light": 0}),
        }

        with state_lock:
            sensors_state[sensor_id] = entry

        # Push al dashboard en tiempo real
        asyncio.run_coroutine_threadsafe(
            broadcast({"type": "update", "sensor": entry}),
            loop,
        )


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def log_message(self, format, *args):  # silenciar logs HTTP
        pass


def run_http():
    httpd = HTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    print(f"[HTTP] Dashboard en http://localhost:{HTTP_PORT}")
    httpd.serve_forever()


async def main():
    loop = asyncio.get_running_loop()

    # Hilo UDP
    t = threading.Thread(target=udp_sniffer, args=(loop,), daemon=True)
    t.start()

    # Hilo HTTP
    h = threading.Thread(target=run_http, daemon=True)
    h.start()

    # WebSocket server
    print(f"[WS] WebSocket en ws://localhost:{WS_PORT}")
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()   # correr forever


if __name__ == "__main__":
    asyncio.run(main())
