import socket
import json
import os

HOST = "0.0.0.0"
PORT = 9001

DASHBOARD_HOST = os.environ.get("DASHBOARD_HOST", "dashboard")
DASHBOARD_PORT = int(os.environ.get("DASHBOARD_PORT", 9002))

class Server:
    
    __state: bool
    
    def __init__(self, host = HOST, port = PORT):
        self.__server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__host = host
        self.__port = port
        self.__state = True

    def init(self): 
        self.__server.bind((self.__host, self.__port))
        while self.__state:
            data, addr = self.__server.recvfrom(4096)    
        
            data_decode = json.loads(data.decode("utf-8"))
            
            print(f"Paquete de ({addr[1]}, Sensor {data_decode['identificador']}): (Temperatura: {data_decode['room_temp']:4f}, Humedad: {data_decode['humidity']:4f}), VPD: {data_decode['VPD']:4f}", flush=True)
            
            # --------------- BLOQUE DE ACTUADOR --------------------
            # VPD (Vapor pressure deficit): diferencia entre cuánta húmedad puede mantener el aire y cuánta mantiene actualmente.
            # Los sensores se dividen en 3 tipos, sensores en habitaciones con plantas en germinación,
            # en habitaciones con plantas en estado vegetativo y en habitaciones con plantas que han florecido.
            # Para cada etapa de crecimiento de la planta hay límites de VPD recomendados.
            
            actuators = {"cooling": 0.0, "heating": 0.0, "humidifier": 0.0, "light": 0.0}
            # --- Habitación en donde las plantas están en la etapa de germinación ---
            if int(data_decode["room_type"]) == 0:
                VPD_value = float(data_decode["VPD"])
                extra_message = " "

                if VPD_value > 1.0:
                    actuators["humidifier"] = 0.015
                    extra_message += "VPD Alto"

                elif VPD_value <= 0.8:
                    actuators["heating"] = 0.05
                    extra_message += "VPD Bajo"


                self.send_response(addr, actuators, message="generate data"+extra_message)

            #  --- Habitación en donde las plantas están en la etapa vegetativa de crecimiento ---
            elif int(data_decode["room_type"]) == 1:
                VPD_value = float(data_decode["VPD"])
                extra_message = " "

                if VPD_value > 1.2:
                    actuators["cooling"] = 0.15
                    extra_message += "VPD Alto"

                elif VPD_value <= 1.0:
                    actuators["heating"] = 0.15
                    extra_message += "VPD Bajo"

                self.send_response(addr, actuators, message="generate data"+extra_message)

            #  --- Habitación en donde las plantas están en la etapa de floración ---
            elif int(data_decode["room_type"]) == 2:
                VPD_value = float(data_decode["VPD"])
                extra_message = " "

                if VPD_value > 1.4:
                    actuators["cooling"] = 0.12
                    actuators["light"] = 0.05
                    extra_message += "VPD Alto"

                elif VPD_value <= 1.2:
                    actuators["heating"] = 0.15
                    extra_message += "VPD Bajo"

                self.send_response(addr, actuators, message="generate data")
            
            # ── Dashboard ──────────────────
            try:
                self.__server.sendto(data, (DASHBOARD_HOST, DASHBOARD_PORT))
            except Exception:
                pass
  

    def send_response(self, addr, actuators=None,message=None):

        reply_dict = {
            "status": "En alerta"
        }

        text = "" if message is None else message

        reply_dict["msg"] = text
        
        if actuators is not None:
            reply_dict["actuators"] = actuators

        reply = json.dumps(reply_dict).encode("utf-8")
        self.__server.sendto(reply, addr)