"""
SIGMA Dashboard
- Escucha paquetes UDP (Batches y Anomalías) enviados por el Servidor Central.
- Broadcast de datos a todos los clientes WebSocket conectados.
- Sirve el HTML/JS del dashboard.
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
UDP_PORT    = 9002          # Puerto donde recibe datos del Servidor Central
WS_PORT     = 8765
HTTP_PORT   = 8080

ROOM_LABELS = {0: "Germinación", 1: "Vegetativo", 2: "Floración"}

sensors_state: dict[str, dict] = {}          # { "Sensor N°1": { ...datos... } }
ws_clients:    set              = set()
state_lock                      = threading.Lock()

async def ws_handler(websocket):
    ws_clients.add(websocket)
    try:
        # Enviar estado actual al conectarse (Snapshot)
        with state_lock:
            snapshot = dict(sensors_state)
        if snapshot:
            await websocket.send(json.dumps({"type": "snapshot", "data": snapshot}))
        async for _ in websocket:
            pass   # No esperamos mensajes del cliente hacia el servidor web
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

def process_and_broadcast_sensor(packet: dict, loop: asyncio.AbstractEventLoop, is_anomaly: bool = False):
    """Procesa un diccionario de sensor individual y lo envía por WebSocket"""
    sensor_id = packet.get("identificador", "Desconocido")
    room_type = int(packet.get("room_type", 1))

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
        "is_anomaly":    is_anomaly # Bandera útil para que el JS frontend sepa si mostrar una alerta
    }

    with state_lock:
        sensors_state[sensor_id] = entry

    # Push al dashboard en tiempo real
    asyncio.run_coroutine_threadsafe(
        broadcast({"type": "update", "sensor": entry}),
        loop,
    )

def udp_receiver(loop: asyncio.AbstractEventLoop):
    """
    Corre en hilo separado.
    Recibe los datos del Servidor Central (Batches y Anomalías).
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_HOST, UDP_PORT))
    sock.settimeout(1.0)

    print(f"[UDP Receiver] Escuchando datos del Servidor Central en {UDP_HOST}:{UDP_PORT}")

    while True:
        try:
            data, addr = sock.recvfrom(65535) # Aumentado el buffer por si el batch es grande
        except socket.timeout:
            continue

        try:
            payload = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        # Lógica de desempaquetado según lo que envía server.py
        p_type = payload.get("type")

        if p_type == "batch":
            # Es un lote de lecturas normales. Iteramos sobre el arreglo 'data'
            for sensor_data in payload.get("data", []):
                process_and_broadcast_sensor(sensor_data, loop, is_anomaly=False)

        elif p_type == "anomaly":
            # Es una alerta crítica enviada por la Vía Rápida (Fast-Track)
            sensor_data = payload.get("data", {})
            process_and_broadcast_sensor(sensor_data, loop, is_anomaly=True)
            print(f"ALERTA: Anomalía recibida del sensor: {sensor_data.get('identificador')}")

        else:
            # Fallback en caso de que reciba un dato crudo antiguo o sin formato
            process_and_broadcast_sensor(payload, loop, is_anomaly=False)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def log_message(self, format, *args):  # silenciar logs HTTP
        pass

def run_http():
    httpd = HTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    print(f"[HTTP] Dashboard sirviendo UI en http://localhost:{HTTP_PORT}")
    httpd.serve_forever()

async def main():
    loop = asyncio.get_running_loop()

    # Hilo UDP (Receptor de datos)
    t = threading.Thread(target=udp_receiver, args=(loop,), daemon=True)
    t.start()

    # Hilo HTTP (Servidor de archivos estáticos HTML/JS/CSS)
    h = threading.Thread(target=run_http, daemon=True)
    h.start()

    # WebSocket server
    print(f"[WS] WebSocket escuchando en ws://localhost:{WS_PORT}")
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()   # correr forever

if __name__ == "__main__":
    asyncio.run(main())
