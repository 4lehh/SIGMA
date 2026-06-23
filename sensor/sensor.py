import socket as s
import json as js
import random
import math
import os

SERVER_HOST = "server"
SERVER_PORT = 9001

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
            "room_type": self.__room_type
        }

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
        import time

        while self.__state:

            self.__data["VPD"] = self.calculate_leaf_VPD()

            aux_dictionary = self.__data.copy()
            claves = ['cooling' , 'heating', 'humidifier', 'light']
            aux_dictionary["actuators"] = {k: self.__system[k] for k in claves if k in self.__system}

            message_encode = js.dumps(aux_dictionary).encode('utf-8')
            self.__client.sendto(message_encode, (self.__server_host, self.__server_port))

            try:
                self.__client.settimeout(0.5)

                data, _ = self.__client.recvfrom(4096)
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
                    self.generate_data(0.005)

            except s.timeout:
                pass

            time.sleep(self.rate)

    # Método para generar datos aleatorios
    def generate_data(self, change_value):
        factor = 0.05

        self.__system["cooling"] += factor * (
            self.__system["cooling_target"] -
            self.__system["cooling"]
        )

        self.__system["heating"] += factor * (
            self.__system["heating_target"] -
            self.__system["heating"]
        )

        self.__system["humidifier"] += factor * (
            self.__system["humidifier_target"] -
            self.__system["humidifier"]
        )

        self.__system["light"] += factor * (
            self.__system["light_target"] -
            self.__system["light"]
        )

        # --- Temperatura ---
        if self.__room_type == 0:
            target_temp = 22
            target_humidity = 0.80

        elif self.__room_type == 1:
            target_temp = 25
            target_humidity = 0.65

        else:
            target_temp = 27
            target_humidity = 0.55
        self.__data["room_temp"] += random.uniform(-change_value, change_value)
        self.__data["room_temp"] += -0.02 * (self.__data["room_temp"] - target_temp)

        self.__data["room_temp"] -= self.__system["cooling"]
        self.__data["room_temp"] += self.__system["heating"]

        # --- Humedad ---
        self.__data["humidity"] += random.uniform(-change_value, change_value)
        self.__data["humidity"] += -0.005 * (self.__data["humidity"] - target_humidity)
        self.__data["humidity"] += self.__system["humidifier"]

        self.__data["humidity"] = max(0.2, min(1.0, self.__data["humidity"]))

        # --- Hoja ---
        self.__data["leaf_temp"] += 0.1 * (self.__data["room_temp"] - self.__data["leaf_temp"])
        self.__data["leaf_temp"] += random.uniform(-change_value/2, change_value/2)
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