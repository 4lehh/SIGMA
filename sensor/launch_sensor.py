from sensor import Sensor
import threading
import time

def main(): 
    # Create Sensors
    sensor_1 = Sensor(rate=1, identificador=1, room_type=1)
    sensor_2 = Sensor(rate=1, identificador=2, room_type=0)

    # Hilos (daemon = True hace que los procesos hijos mueran)
    hilo_1 = threading.Thread(target=sensor_1.init, daemon=True)
    hilo_2 = threading.Thread(target=sensor_2.init, daemon=True)
    
    hilo_1.start()
    hilo_2.start()

    # Mantenemos el Hilo padre en espera hasta finalizar presionando cualquier tecla
    try:
        while True: 
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Deteniendo todos los clientes de forma segura...")

if __name__ == "__main__":
    main()
