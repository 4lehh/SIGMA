import socket
import json
import os
from nacl.secret import SecretBox
from nacl.exceptions import CryptoError

HOST = "0.0.0.0"
PORT = 9001

SHARED_KEY = b"12345678901234567890123456789012"

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
        
        # TODO: revisar valores
        # -- rate adapatativo --
        self.__max_rate = 5 # rate máximo de sensores (cuando no hay mayor variación)
        self.__min_rate = 0.3 # rate mínimo de sensores (cuando hay mayor variación)
        self.__last_VPDs_per_sensor = {} # dict que mapea identificador -> último VPD recibido
        self.__delta_VPD_threshold = 0.03 # TODO: jugar con este valor

    def init(self): 
        box = SecretBox(SHARED_KEY)

        self.__server.bind((self.__host, self.__port))


        while self.__state:
            data, addr = self.__server.recvfrom(4096)    

            data = box.decrypt(data)
        
            data_decode = json.loads(data.decode("utf-8"))
            
            print(f"Paquete de ({addr[1]}, Sensor {data_decode['identificador']}): (Temperatura: {data_decode['room_temp']:4f}, Humedad: {data_decode['humidity']:4f}), VPD: {data_decode['VPD']:4f}", flush=True)
            
            # -------------- RATE ADAPATATIVO DE SENSORES -------------- 
            current_rate = float(data_decode["rate"])
            sensor_VPD = float(data_decode["VPD"])
            sensor_id = data_decode["identificador"]

            last_VPD = self.__last_VPDs_per_sensor.get(sensor_id, sensor_VPD) # si no hay VPD previo, se deja el actual como último VPD
            
            # se calcula variación de VPD
            delta_VPD = abs(sensor_VPD - last_VPD)
            
            self.__last_VPDs_per_sensor[sensor_id] = sensor_VPD # se actualiza último VPD recibido 
            
            if delta_VPD > self.__delta_VPD_threshold:
                new_rate = self.__min_rate
            else:
                new_rate = self.__max_rate



            # --------------- BLOQUE DE ACTUADOR --------------------
            # VPD (Vapor pressure deficit): diferencia entre cuánta húmedad puede mantener el aire y cuánta mantiene actualmente.
            # Los sensores se dividen en 3 tipos, sensores en habitaciones con plantas en germinación,
            # en habitaciones con plantas en estado vegetativo y en habitaciones con plantas que han florecido.
            # Para cada etapa de crecimiento de la planta hay límites de VPD recomendados.
            # 0 => germinacion, 1 => vegetativo, 2 => floracion

            actuators = {"cooling": 0.0, "heating": 0.0, "humidifier": 0.0, "light": 0.5}
            extra_message = " "
            # --- Habitación en donde las plantas están en la etapa de germinación ---
            if int(data_decode["room_type"]) == 0:
                VPD_value = float(data_decode["VPD"])

                if VPD_value > 1.0:
                    actuators["humidifier"] = 0.015
                    self.__anomaly_detected = True
                    extra_message += "VPD Alto"

                elif VPD_value <= 0.8:
                    actuators["cooling"] = 0.05
                    self.__anomaly_detected = True
                    extra_message += "VPD Bajo"

            #  --- Habitación en donde las plantas están en la etapa vegetativa de crecimiento ---
            elif int(data_decode["room_type"]) == 1:
                VPD_value = float(data_decode["VPD"])

                if VPD_value > 1.2:
                    actuators["cooling"] = 0.15
                    extra_message += "VPD Alto"
                    self.__anomaly_detected = True

                elif VPD_value <= 1.0:
                    actuators["heating"] = 0.15
                    extra_message += "VPD Bajo"
                    self.__anomaly_detected = True

            #  --- Habitación en donde las plantas están en la etapa de floración ---
            elif int(data_decode["room_type"]) == 2:
                VPD_value = float(data_decode["VPD"])

                if VPD_value > 1.4:
                    actuators["cooling"] = 0.12
                    actuators["light"] = 0.05
                    extra_message += "VPD Alto"
                    self.__anomaly_detected = True

                elif VPD_value <= 1.2:
                    actuators["heating"] = 0.15
                    extra_message += "VPD Bajo"
                    self.__anomaly_detected = True
            
            # si hay anomalía, también se fuerza a sensores a enviar datos a mayor frecuencia
            if self.__anomaly_detected:
                new_rate = self.__min_rate
            
            self.send_response(addr, actuators, message="generate data"+extra_message, rate=new_rate)
            

            # ── Dashboard ──────────────────
            
            # si anomalía, reenviar directo a dashboard
            if self.__anomaly_detected:
                package_anomaly = {"type": "anomaly", "data": data_decode}
                package_anomaly_encoded = json.dumps(package_anomaly).encode("utf-8")
                package_anomaly_encrypted = box.encrypt(package_anomaly_encoded)

                try:
                    self.__server.sendto(package_anomaly_encrypted, (DASHBOARD_HOST, DASHBOARD_PORT))
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


    def send_response(self, addr, actuators=None,message=None, rate=None):
        box = SecretBox(SHARED_KEY)

        reply_dict = {
            "status": "En alerta" if self.__anomaly_detected else "Normal"
        }

        text = "" if message is None else message

        reply_dict["msg"] = text
        
        if actuators is not None:
            reply_dict["actuators"] = actuators

        if rate is not None:
            reply_dict["rate"] = rate

        reply = json.dumps(reply_dict).encode("utf-8")

        reply = box.encrypt(reply)
        
        self.__server.sendto(reply, addr)
