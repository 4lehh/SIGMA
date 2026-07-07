FROM python:3.10-slim

WORKDIR /app

# se instala iproute2 para parámetros de red
RUN apt-get update && apt-get install -y iproute2 && rm -rf /var/lib/apt/lists/*

RUN pip install websockets --break-system-packages

RUN pip install --no-cache-dir pynacl

COPY . .

CMD ["python", "dashboard.py"]
