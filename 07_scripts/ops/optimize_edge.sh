#!/usr/bin/env bash
# ============================================================
# optimize_edge.sh
# Optimizaciones de rendimiento y estabilidad para Orange Pi 5 Plus
# (Nodo Edge con NPU RK3588 / RK3576 y aceleracion CUDA/NVIDIA si aplica)
# Referencia: T-032 Servicios edge_iot + instruccion Tesista (VAL-STEP-779)
# Uso: sudo bash 07_scripts/ops/optimize_edge.sh
# ============================================================
set -euo pipefail

log()  { echo "[$(date +'%H:%M:%S')] INFO:  $*"; }
warn() { echo "[$(date +'%H:%M:%S')] WARN:  $*" >&2; }
ok()   { echo "[$(date +'%H:%M:%S')] OK:    $*"; }
fail() { echo "[$(date +'%H:%M:%S')] ERROR: $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || fail "Ejecutar como root: sudo bash $0"

log "=== Optimizacion del Nodo Edge (Orange Pi 5 Plus / RK3588) ==="

# ---------------------------------------------------------------
# 1. CPU Governor: performance para inferencia NPU/GPU
# ---------------------------------------------------------------
log "[CPU] Configurando governor a 'performance'..."
if [[ -d /sys/devices/system/cpu/cpu0/cpufreq ]]; then
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo performance > "$cpu"
    done
    ok "[CPU] Governor = performance"
    # Persistir via /etc/rc.local o sysfs-conf
    cat > /etc/systemd/system/cpu-performance.service << 'EOF'
[Unit]
Description=CPU Performance Governor
After=multi-user.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c "for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > $cpu; done"

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable --now cpu-performance.service
    ok "[CPU] Servicio cpu-performance habilitado"
else
    warn "[CPU] cpufreq no disponible, omitiendo."
fi

# ---------------------------------------------------------------
# 2. Memoria: swappiness baja para priorizar RAM (critico para NPU)
# ---------------------------------------------------------------
log "[MEM] Ajustando swappiness y cache pressure..."
sysctl -w vm.swappiness=10
sysctl -w vm.vfs_cache_pressure=50

# Persistir en sysctl.d (idempotente)
cat > /etc/sysctl.d/99-siot-edge.conf << 'EOF'
# SIOT Edge Node - Optimizaciones de Memoria
# Swappiness baja: priorizar RAM para inferencia NPU
vm.swappiness = 10
# Cache pressure reducido: mantener mas inodos en memoria
vm.vfs_cache_pressure = 50
# Buffers de red para telemetria IoT
net.core.rmem_max = 4194304
net.core.wmem_max = 4194304
net.ipv4.tcp_rmem = 4096 87380 4194304
net.ipv4.tcp_wmem = 4096 65536 4194304
EOF
sysctl -p /etc/sysctl.d/99-siot-edge.conf >/dev/null 2>&1 || true
ok "[MEM] Parametros de kernel aplicados y persistidos"

# ---------------------------------------------------------------
# 3. ZRAM: swap comprimido en RAM para el NPU (evita thrashing)
# ---------------------------------------------------------------
log "[ZRAM] Configurando ZRAM como swap comprimido..."
if modprobe zram 2>/dev/null; then
    TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    # Usar 25% de la RAM como ZRAM
    ZRAM_SIZE_MB=$(( TOTAL_MEM_KB / 4 / 1024 ))
    ZRAM_DEVICE="/dev/zram0"

    # Reiniciar si ya existe
    swapoff "${ZRAM_DEVICE}" 2>/dev/null || true
    echo 1 > /sys/block/zram0/reset 2>/dev/null || true
    echo lz4 > /sys/block/zram0/comp_algorithm 2>/dev/null || true
    echo "${ZRAM_SIZE_MB}M" > /sys/block/zram0/disksize
    mkswap "${ZRAM_DEVICE}" >/dev/null
    swapon --priority 100 "${ZRAM_DEVICE}"
    ok "[ZRAM] ${ZRAM_SIZE_MB}MB ZRAM activo como swap comprimido (algoritmo: lz4)"
else
    warn "[ZRAM] Modulo zram no disponible, omitiendo."
fi

# ---------------------------------------------------------------
# 4. Hugepages: beneficioso para cargas LLM / inferencia
# ---------------------------------------------------------------
log "[HUGEPAGEs] Habilitando transparent hugepages (madvise)..."
if [[ -f /sys/kernel/mm/transparent_hugepage/enabled ]]; then
    echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
    ok "[HUGEPAGEs] Modo 'madvise' activado"
else
    warn "[HUGEPAGEs] No disponible en este kernel."
fi

# ---------------------------------------------------------------
# 5. I/O Scheduler: mq-deadline para almacenamiento eMMC/NVMe
# ---------------------------------------------------------------
log "[I/O] Optimizando scheduler para eMMC/NVMe..."
for dev in /sys/block/mmcblk* /sys/block/nvme*; do
    [[ -d "$dev" ]] || continue
    SCHED_FILE="${dev}/queue/scheduler"
    if [[ -f "$SCHED_FILE" ]]; then
        if grep -q "mq-deadline" "$SCHED_FILE"; then
            echo mq-deadline > "$SCHED_FILE"
            ok "[I/O] Scheduler $(basename $dev) = mq-deadline"
        elif grep -q "none" "$SCHED_FILE"; then
            echo none > "$SCHED_FILE"
            ok "[I/O] Scheduler $(basename $dev) = none (NVMe optimal)"
        fi
    fi
done

# ---------------------------------------------------------------
# 6. IRQ Affinity: distribuir interrupciones en todos los cores
# ---------------------------------------------------------------
log "[IRQ] Habilitando irqbalance..."
if command -v irqbalance >/dev/null 2>&1; then
    systemctl enable --now irqbalance
    ok "[IRQ] irqbalance habilitado"
else
    apt-get install -y -qq irqbalance 2>/dev/null && systemctl enable --now irqbalance && ok "[IRQ] irqbalance instalado y habilitado" || warn "[IRQ] irqbalance no disponible"
fi

# ---------------------------------------------------------------
# 7. Deshabilitar servicios innecesarios (reducir overhead)
# ---------------------------------------------------------------
# SERVICIOS CONSERVADOS INTENCIONALMENTE:
#   bluetooth.service    -> Parte del stack IoT del proyecto (BLE/sensores).
#   avahi-daemon.service -> mDNS/DNS-SD para descubrimiento automatico de nodos
#                          en la red local cuando el DNS central no esta disponible.
#                          Util para resiliencia en escenarios de intermitencia urbana.
#   ModemManager.service -> Gestion de modems 3G/4G/5G USB. Canal de respaldo LTE
#                          para escenarios de intermitencia urbana (tema central T-008).
#                          Conservar si hay o habra modem LTE conectado al Edge.
log "[SVC] Deshabilitando servicios sin uso en el stack Edge IoT..."
DISABLE_SVCS=(
    "cups.service"        # Sistema de impresion: sin utilidad en nodo IoT/Edge.
)
for svc in "${DISABLE_SVCS[@]}"; do
    if systemctl is-enabled --quiet "${svc}" 2>/dev/null; then
        systemctl disable --now "${svc}" 2>/dev/null || true
        ok "[SVC] Deshabilitado: ${svc}"
    fi
done

# ---------------------------------------------------------------
# 8. Limites del sistema para edge_ops (Docker, descriptores)
# ---------------------------------------------------------------
log "[LIMITS] Configurando limites del sistema para edge_ops..."
cat > /etc/security/limits.d/99-siot-edge.conf << 'EOF'
# SIOT Edge Node - Limites para usuario edge_ops
edge_ops soft nofile 65536
edge_ops hard nofile 131072
edge_ops soft nproc  8192
edge_ops hard nproc  16384
EOF
ok "[LIMITS] Limites aplicados para edge_ops"

# ---------------------------------------------------------------
# 9. Docker daemon: optimizaciones para hardware ARM con NPU
# ---------------------------------------------------------------
log "[DOCKER] Optimizando Docker daemon para ARM / RK3588..."
mkdir -p /etc/docker
# Solo si no existe ya configuracion personalizada
if [[ ! -f /etc/docker/daemon.json ]]; then
    cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 131072,
      "Soft": 65536
    }
  },
  "features": {
    "buildkit": true
  }
}
EOF
    systemctl restart docker 2>/dev/null || true
    ok "[DOCKER] daemon.json configurado y Docker reiniciado"
else
    warn "[DOCKER] /etc/docker/daemon.json ya existe, omitiendo para no sobreescribir."
fi

log "=== Optimizacion completada ==="
echo ""
echo "RESUMEN DE OPTIMIZACIONES:"
echo "  CPU Governor : performance"
echo "  vm.swappiness: 10"
echo "  ZRAM swap    : ${ZRAM_SIZE_MB:-N/A}MB (lz4)"
echo "  I/O scheduler: mq-deadline"
echo "  IRQ balance  : habilitado"
echo "  Limites      : edge_ops 65536 fd"
echo "  Docker       : json-file logs, overlay2"
echo ""
echo "SERVICIOS CONSERVADOS (utiles para el proyecto):"
echo "  bluetooth    : stack IoT BLE/sensores"
echo "  avahi-daemon : descubrimiento mDNS local (resiliencia ante fallo DNS)"
echo "  ModemManager : respaldo LTE para escenarios de intermitencia urbana"
echo "  cups         : [DESHABILITADO] sin utilidad en nodo IoT/Edge"
echo ""
echo "SIGUIENTE PASO: sudo bash 07_scripts/ops/install_edge_service.sh"
