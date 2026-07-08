# Dockerfile para OfficePing Backend (FastAPI + WebSockets)
FROM python:3.11-slim

# Evita generar archivos .pyc y fuerza salida de logs en tiempo real sin búfer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias mínimas del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Crear carpeta para persistencia de datos por defecto
RUN mkdir -p /app/data

EXPOSE 8000

# Ejecutar Uvicorn en el puerto 8000 dentro del contenedor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
