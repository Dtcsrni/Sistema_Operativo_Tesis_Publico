# ==========================================
# STAGE 1: BUILDER
# ==========================================
FROM python:3.12-slim AS builder

# Evitar generación de .pyc y habilitar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV GITHUB_ACTIONS=true

WORKDIR /app

# Instalar dependencias base del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
# Nota: El sistema usa principalmente librerías estándar, pero requiere PyYAML y python-dotenv
RUN pip install --no-cache-dir PyYAML python-dotenv

# Copiar el código fuente (respetando .dockerignore)
COPY . .

# Ejecutar la suite completa de construcción y auditoría
# Esto genera 06_dashboard/generado/ y valida la integridad
RUN python 07_scripts/build_all.py

# ==========================================
# STAGE 2: RUNNER (NGINX)
# ==========================================
FROM nginx:alpine AS runner

LABEL maintainer="Erick Renato Vega Ceron"
LABEL project="SIOT-Docs"

# Copiar el contenido estático generado desde la etapa builder
COPY --from=builder /app/06_dashboard/generado /usr/share/nginx/html

# Copiar configuración optimizada de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Metadata de salud del contenedor
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
