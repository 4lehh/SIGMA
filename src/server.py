import socket
import json

HOST = "127.0.0.1"
PORT = 9001

class Server:
    
    __state: bool
    
    def __init__(self, host = HOST, port = PORT):
        self.__server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__host = host
        self.__port = port
        self.__state = True

    def init(self): 

        # Escucha
        self.__server.bind((self.__host, self.__port))

        while self.__state:
            data, addr = self.__server.recvfrom(4096)    
        
            # La data llega como un string, entonces debemos pasarla a un dict
            data_decode = json.loads(data.decode("utf-8"))

            print(f"Paquete de ({addr[1]}, Sensor {data_decode["identificador"]}): (Temperatura: {data_decode["temp"]}, Humedad: {data_decode["humedad"]})")

            
            if int(data_decode["temp"]) >= 40:

                # --------------- BLOQUE DE ACTUADOR --------------------
                
                self.send_response(message="¡¡Activa tu protocolo de seguridad!!", addr=addr)
    
    def send_response(self, message: str, addr: dict):
        reply_dict = {
            "status": "alerta",
            "msg": message
        }

        reply = json.dumps(reply_dict).encode("utf-8")
        
        self.__server.sendto(reply, addr)