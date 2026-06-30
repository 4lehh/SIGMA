from sensor import Sensor
import threading
import time

def main(): 
    # Create Sensors
    sensor_1 = Sensor(rate=2, identificador=1, room_type=1)
    sensor_2 = Sensor(rate=1.5, identificador=2, room_type=0)
    sensor_3 = Sensor(rate=0.1, identificador=3, room_type=1)
    sensor_4 = Sensor(rate=1, identificador=4, room_type=2)

    # Hilos (daemon = True hace que los procesos hijos mueran)
    hilo_1 = threading.Thread(target=sensor_1.init, daemon=True)
    hilo_2 = threading.Thread(target=sensor_2.init, daemon=True)
    hilo_3 = threading.Thread(target=sensor_3.init, daemon=True)
    hilo_4 = threading.Thread(target=sensor_4.init, daemon=True)
    
    hilo_1.start()
    hilo_2.start()
    hilo_3.start()
    hilo_4.start()

    # Mantenemos el Hilo padre en espera hasta finalizar presionando cualquier tecla
    try:
        while True: 
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Deteniendo todos los clientes de forma segura...")

if __name__ == "__main__":
    main()
