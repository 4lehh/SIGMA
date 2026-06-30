FROM python:3.10-slim

WORKDIR /app

RUN pip install websockets --break-system-packages

RUN pip install --no-cache-dir pynacl

COPY . .

CMD ["python", "dashboard.py"]
