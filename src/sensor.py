import socket as s
import json as js

# DEFINE
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9001

class Sensor: 
    
    rate: float
    __state: bool
    __data: dict

    def __init__(self, identificador: int, rate: float = 0.1, server_host =  SERVER_HOST, server_port = SERVER_PORT):
        self.__client = s.socket(s.AF_INET, s.SOCK_DGRAM)
        self.__identificador = identificador
        self.rate = rate
        self.__state = True
        self.__server_host = server_host
        self.__server_port = server_port

        # Config data
        self.__data = {"identificador": f"Sensor N°{identificador}", "temp": 0.0, "humedad": "30%"}
    
    def init(self):
        import time 

        while self.__state:
            # Prepare the message
            message = self.__data
            message_encode = js.dumps(message).encode('utf-8')

            # Send message
            self.__client.sendto(message_encode, (self.__server_host, self.__server_port))

            try:
                # Ponemos un timeout pequeño para que no se quede trabado para siempre 
                self.__client.settimeout(0.5) 
                
                data, server_addr = self.__client.recvfrom(1024)
                respuesta = js.loads(data.decode('utf-8'))
                print(f"{respuesta["status"]} en Sensor {self.__identificador}: {respuesta["msg"]}")
                
            except s.timeout:
                # Si el servidor no respondió en 0.5 segundos, continúa el bucle
                pass

            # Timeout
            time.sleep(self.rate)

    def change_state(self):
        self.__state = not self.__state


    def get_data(self):
        return self.__data
    
    def set_data(self, data: dict):
        self.__data["temp"] = data["temp"]
        self.__data["humedad"] = data["humedad"]
    