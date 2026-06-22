FROM python:3.10-slim

WORKDIR /app

RUN pip install websockets --break-system-packages

COPY . .

CMD ["python", "dashboard.py"]
