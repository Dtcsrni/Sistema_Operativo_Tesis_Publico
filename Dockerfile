# Dockerfile para el Sistema Operativo de Tesis
# Basado en Python 3.14-slim para alinearlo con la versión estable actual del sistema.

FROM python:3.14-slim

# Evita la generación de archivos .pyc y fuerza el log a stdout
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias de sistema necesarias para Git y compilación de extensiones
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requerimientos e instalar
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# El código se montará como volumen para desarrollo activo, 
# pero copiamos lo esencial por si se quiere correr de forma aislada.
COPY . .

# Comando por defecto: Validar el sistema
CMD ["python", "07_scripts/build_all.py"]
