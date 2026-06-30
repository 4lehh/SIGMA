import socket as s
import json as js
import random as rd
import math
import time
from nacl.secret import SecretBox
from nacl.utils import random



SERVER_HOST = "server"
SERVER_PORT = 9001
SHARED_KEY = b"12345678901234567890123456789012"

class Sensor:

    def __init__(self, identificador: int, rate: float = 0.1, room_type=1,
                 server_host=SERVER_HOST, server_port=SERVER_PORT):

        self.__client = s.socket(s.AF_INET, s.SOCK_DGRAM)
        self.__identificador = identificador
        self.rate = rate
        self.__state = True
        self.__server_host = server_host
        self.__server_port = server_port
        self.__room_type = room_type

       
        # Datos del monitoreo
        # leaf_temp: temperatura de las hojas de las plantas
        # room_type: tipo de habitación en donde hay plantas en cierta etapa de crecimiento
        self.__data = {
            "identificador": f"Sensor N°{identificador}",
            "room_temp": 25.0,
            "humidity": 0.6,
            "leaf_temp": 24.5,
            "room_type": self.__room_type,
            "rate": self.rate,
        }

        if self.__room_type == 0:
            self.__data["room_temp"] = 25
            self.__data["leaf_temp"] = 24.5
            self.__data["humidity"] = 0.69
        elif self.__room_type == 1:
            self.__data["room_temp"] = 25
            self.__data["leaf_temp"] = 24.5
            self.__data["humidity"] = 0.62

        elif self.__room_type == 2:
            self.__data["room_temp"] = 27
            self.__data["leaf_temp"] = 26.5
            self.__data["humidity"] = 0.6


        # Actuadores
        # Estos valores ayudan a aumentar o disminuir la magnitud de los datos de monitoreo. 
        self.__system = {
            "cooling": 0.0,
            "heating": 0.0,
            "humidifier": 0.0,
            "light": 0.0,

            "cooling_target": 0.0,
            "heating_target": 0.0,
            "humidifier_target": 0.0,
            "light_target": 0.0
        }

        self.__data["VPD"] = self.calculate_leaf_VPD()


    def init(self):
        box = SecretBox(SHARED_KEY)
        while self.__state:

            self.__data["VPD"] = self.calculate_leaf_VPD()

            aux_dictionary = self.__data.copy()
            claves = ['cooling' , 'heating', 'humidifier', 'light']
            aux_dictionary["actuators"] = {k: self.__system[k] for k in claves if k in self.__system}

            message_encode = js.dumps(aux_dictionary).encode('utf-8')
            message_encripted = box.encrypt(message_encode)

            self.__client.sendto(message_encripted, (self.__server_host, self.__server_port))

            try:
                data, _ = self.__client.recvfrom(4096)

                data = box.decrypt(data)

                respuesta = js.loads(data.decode('utf-8'))

                if len(respuesta["msg"]) != 14:
                    print(f"{respuesta['status']} Sensor {self.__identificador}: {respuesta['msg'][13:]}")

                # Intentar obtener los valores de los actuadores
                try:
                    act = respuesta["actuators"]
                    self.__system["cooling"] = act["cooling"]
                    self.__system["heating"] = act["heating"]
                    self.__system["humidifier"] = act["humidifier"]
                    self.__system["light"] = act["light"]
                except KeyError:
                    pass

                # Al obtener mensaje "generate data" se llama al método aquí
                if "generate data" in respuesta["msg"]:
                    self.generate_data(0.00875)
                
                # Al obtener mensaje "rate" se actualiza rate de envío de datos
                try:
                    if "rate" in respuesta:
                        self.rate = float(respuesta["rate"])
                        self.__data["rate"] = self.rate
                except (KeyError, ValueError):
                    pass

            except s.timeout:
                pass

            time.sleep(self.rate)

    # Método para generar datos aleatorios
    def generate_data(self, change_value):

        # --- Temperatura ---
        if self.__room_type == 0:
            target_temp = 24
            target_humidity = 0.72

        elif self.__room_type == 1:
            target_temp = 24.5
            target_humidity = 0.65

        else:
            target_temp = 27.0
            target_humidity = 0.58

        self.__data["room_temp"] += rd.uniform(-change_value, change_value)
        self.__data["room_temp"] += -0.02 * (self.__data["room_temp"] - target_temp)

        self.__data["room_temp"] -= self.__system["cooling"]
        self.__data["room_temp"] += self.__system["heating"]

        # --- Humedad ---
        self.__data["humidity"] += rd.uniform(-change_value, change_value)
        self.__data["humidity"] += -0.09 * (self.__data["humidity"] - target_humidity)
        self.__data["humidity"] += self.__system["humidifier"]

        self.__data["humidity"] = max(0.2, min(1.0, self.__data["humidity"]))

        # --- Hoja ---
        self.__data["leaf_temp"] += 0.1 * (self.__data["room_temp"] - self.__data["leaf_temp"])
        self.__data["leaf_temp"] += rd.uniform(-change_value/2, change_value/2)
        self.__data["leaf_temp"] += self.__system["light"]

    def calculate_leaf_VPD(self):

        SVP_leaf = 0.6108 * math.exp(
            (17.27 * self.__data["leaf_temp"]) /
            (self.__data["leaf_temp"] + 237.3)
        )

        SVP_room = 0.6108 * math.exp(
            (17.27 * self.__data["room_temp"]) /
            (self.__data["room_temp"] + 237.3)
        )

        AVP_air = SVP_room * self.__data["humidity"]

        return SVP_leaf - AVP_air
