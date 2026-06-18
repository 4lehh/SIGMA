from src.sensor import Sensor
import threading
import time

def main(): 
    # Create Sensors
    sensor_1 = Sensor(rate=1, identificador=1)
    sensor_2 = Sensor(rate=1, identificador=2)

    sensor_2.set_data({"temp": 55, "humedad": "10%"})

    # Hilos (daemon = True hace que los procesos hijos mueran)
    hilo_1 = threading.Thread(target=sensor_1.init, daemon=True)
    hilo_2 = threading.Thread(target=sensor_2.init, daemon=True)
    
    hilo_1.start()
    hilo_2.start()

    # Mantenemos el Hilo padre en espera hasta finalizar presionando cualquier tecla
    try:
        input("\n")
    except KeyboardInterrupt:
        print("\n[!] Deteniendo todos los clientes de forma segura...")

if __name__ == "__main__":
    main()
