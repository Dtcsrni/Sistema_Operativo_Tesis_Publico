#!/bin/bash
# setup_tunnel.sh - Configuración del túnel de seguridad PC-Edge

HUB_USER="evega"
HUB_IP="192.168.1.XX" # Reemplazar con la IP real de la PC
EDGE_KEY_PATH="/srv/tesis/keys/id_rsa_edge"

echo "[*] Configurando túnel SSH reverso para acceso a la PC..."

# Crear túnel persistente:
# Puerto 8080 de la PC (Dashboard) -> Puerto 8080 local del Edge
# Puerto 22 del Edge -> Puerto 2222 de la PC (Acceso remoto)

ssh -N -f -R 2222:localhost:22 -L 8080:localhost:8080 ${HUB_USER}@${HUB_IP} -i ${EDGE_KEY_PATH}

if [ $? -eq 0 ]; then
    echo "[OK] Túnel establecido."
    echo "    - Dashboard PC disponible en: http://localhost:8080"
    echo "    - Acceso remoto desde PC: ssh tesisai@localhost -p 2222"
else
    echo "[ERROR] No se pudo establecer el túnel."
fi
