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

# ─── Copias quirúrgicas: solo lo que build_all.py necesita ───────
# Canon de tesis (fuente de datos del dashboard)
COPY 00_sistema_tesis /app/00_sistema_tesis
# Templates y fuentes del dashboard
COPY 06_dashboard /app/06_dashboard
# Script de build y utilidades de auditoría
COPY 07_scripts /app/07_scripts
# Configuración de entorno (sin secrets)
COPY config /app/config

# Generar el dashboard estático + auditoría de integridad
# Si Serena no está disponible, el build continúa sin errores
RUN python 07_scripts/build_all.py --force --no-serena-gate || echo "[WARN] build_all.py failed"

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
HEALTHCHECK --interval=30s --timeout=8s --start-period=45s --retries=3 \
  CMD curl -sf http://127.0.0.1/ > /dev/null || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
