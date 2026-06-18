# Documentación libreria Socket

### Configuraciones importantes

|Configuración|Descripción|
|-------------|-----------|
|`AF_INET`|Usaremos direcciones IPv4|
|`SOCK_DGRAM`|Protocolo UDP|

### Comandos importantes de establecimiento de red
Primero establecemos nuestro server con la configuracion: 

`server = socket.socket(socket.AF_INET, SOCK.SOCK_DGRAM)`

Ahora bien, los comandos a utilizar son:

|Comando | Descripción|
|--------|------------|
|`server.bind(SERVER_IP, PORT)`|Esto coloca en escucha nuestro servidor, esperando recibir paquetes|
|`server.recvfrom(tamaño_paquete)`|Dentro de un `while True`, colocamos el servidor en escucha, esto dice que va a recibir paquete de un tamaño concreto. Normalmente se colocan 4092 que son 4Kb. La data que devuelve es una tupla que contiene la dirección y el mensaje. El mensaje debe ser codificado con `utf-8`.|