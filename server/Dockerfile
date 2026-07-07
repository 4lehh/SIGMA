FROM python:3.10-slim

WORKDIR /app

# se instala herramienta iproute2 para simular parámetros de red
RUN apt-get update && apt-get install -y iproute2 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pynacl

CMD ["python", "launch_server.py"]
