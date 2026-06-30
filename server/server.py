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
        
        # buffer temporal para almacenar datos antes de enviarlos a dashboard (para situaciones normales)
        self.__data_buffer = []

        # en caso de anomalía, servidor envía datos directamente al dashboard, sin pasar por buffer
        self.__anomaly_detected = False
        

    def init(self): 
        self.__server.bind((self.__host, self.__port))

        while self.__state:
            # NOTE: recvfrom es bloqueante y pausa ejecución completa hasta que llegue paquete
            # problema de esto es que si sensores mueren y se estaba armando un batch de datos, nunca se enviará al dashboard
            # y se perdería información
            data, addr = self.__server.recvfrom(4096)    
        
            data_decode = json.loads(data.decode("utf-8"))
            
            print(f"Paquete de ({addr[1]}, Sensor {data_decode['identificador']}): (Temperatura: {data_decode['room_temp']:4f}, Humedad: {data_decode['humidity']:4f}), VPD: {data_decode['VPD']:4f}", flush=True)
            
            # --------------- BLOQUE DE ACTUADOR --------------------
            # VPD (Vapor pressure deficit): diferencia entre cuánta húmedad puede mantener el aire y cuánta mantiene actualmente.
            # Los sensores se dividen en 3 tipos, sensores en habitaciones con plantas en germinación,
            # en habitaciones con plantas en estado vegetativo y en habitaciones con plantas que han florecido.
            # Para cada etapa de crecimiento de la planta hay límites de VPD recomendados.
            # 0 => germinacion, 1 => vegetativo, 2 => floracion

            # --- Habitación en donde las plantas están en la etapa de germinación ---
            if int(data_decode["room_type"]) == 0:
                VPD_value = float(data_decode["VPD"])
                actuators = {"cooling": 0.0, "heating": 0.0, "humidifier": 0.0, "light": 0.5}

                if VPD_value > 1.0:
                    actuators["humidifier"] = 0.06
                    self.__anomaly_detected = True

                elif VPD_value <= 0.8:
                    actuators["cooling"] = 0.03
                    self.__anomaly_detected = True

                # NOTE: esto no es una anomalía? por ahora asumiré que no porque siempre se ejecuta
                else:
                    actuators["humidifier"] = 0.02

                self.send_response(addr, actuators, message="generate data")

            #  --- Habitación en donde las plantas están en la etapa vegetativa de crecimiento ---
            elif int(data_decode["room_type"]) == 1:
                VPD_value = float(data_decode["VPD"])
                actuators = {"cooling": 0.0, "heating": 0.0, "humidifier": 0.0, "light": 0.7}
                extra_message = " "

                if VPD_value > 1.2:
                    actuators["cooling"] = 0.06
                    extra_message += "VPD Alto"
                    self.__anomaly_detected = True

                elif VPD_value <= 1.0:
                    actuators["heating"] = 0.04
                    extra_message += "VPD Bajo"
                    self.__anomaly_detected = True

                self.send_response(addr, actuators, message="generate data"+extra_message)

            #  --- Habitación en donde las plantas están en la etapa de floración ---
            elif int(data_decode["room_type"]) == 2:
                VPD_value = float(data_decode["VPD"])
                actuators = {"cooling": 0.0, "heating": 0.0, "humidifier": 0.0, "light": 1.0}

                if VPD_value > 1.2:
                    actuators["light"] = 0.05
                    self.__anomaly_detected = True

                elif VPD_value <= 1.0:
                    actuators["heating"] = 0.03
                    self.__anomaly_detected = True

                self.send_response(addr, actuators, message="generate data")
            
            # ── Dashboard ──────────────────
            
            # si anomalía, reenviar directo a dashboard
            if self.__anomaly_detected:
                package_anomaly = {"type": "anomaly", "data": data_decode}
                package_anomaly_encoded = json.dumps(package_anomaly).encode("utf-8")
                try:
                    self.__server.sendto(package_anomaly_encoded, (DASHBOARD_HOST, DASHBOARD_PORT))
                except Exception:
                    pass
                self.__anomaly_detected = False
            else:
                # si no anomalía, almacenar en buffer y enviar cada cierto tiempo
                self.__data_buffer.append(data)
                if len(self.__data_buffer) >= 10: # por ahora se envía cada 10 paquetes, revisar (tiempo final depende de rate de los sensores)
                    data_batch = [json.loads(data.decode("utf-8")) for data in self.__data_buffer] 
                    
                    # se construye un solo paquete que lleva la data en lote
                    package_batch = {"type": "batch", "data": data_batch}
                    package_batch_encoded = json.dumps(package_batch).encode("utf-8")                   
                    
                    try:
                        self.__server.sendto(package_batch_encoded, (DASHBOARD_HOST, DASHBOARD_PORT))
                    except Exception:
                        pass

                    self.__data_buffer.clear() # se limpia buffer


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
