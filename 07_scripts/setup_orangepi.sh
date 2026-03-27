#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[SETUP] Wrapper legado hacia bootstrap/orangepi por fases"
for phase in \
  "bootstrap/orangepi/10_primer-arranque.sh" \
  "bootstrap/orangepi/50_hardening-base.sh" \
  "bootstrap/orangepi/60_instalar-node-herramientas-opcionales.sh" \
  "bootstrap/orangepi/80_configurar-workspace-tesis.sh"
do
  echo "[SETUP] Ejecutando ${phase}"
  bash "${ROOT}/${phase}"
done

echo "[SETUP] Fases base completadas. Revisa y ejecuta manualmente las fases con mayor riesgo:"
echo "  - bootstrap/orangepi/20_preparar-nvme.sh"
echo "  - bootstrap/orangepi/30_instalar-rootfs-en-nvme.sh"
echo "  - bootstrap/orangepi/40_montar-emmc.sh"
echo "  - bootstrap/orangepi/70_instalar-servicios.sh"
echo "  - bootstrap/orangepi/90_postcheck.sh"
