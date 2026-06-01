#!/usr/bin/env bash
# ==============================================================================
# Script de Prueba de Integración y Humo: Backups por Dominio (T-035)
# ==============================================================================
set -euo pipefail

# Obtener ruta absoluta del repositorio
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SANDBOX="${REPO_ROOT}/scratch/test_backup_restore"

# Crear directorio de ejecución único con timestamp para evitar colisiones
RUN_ID="run_$(date +%Y%m%d_%H%M%S)"
RUN_DIR="${SANDBOX}/${RUN_ID}"

echo "=== INICIANDO PRUEBA DE INTEGRACIÓN T-035 ==="
echo "Directorio de Sandbox: ${RUN_DIR}"

# 1. Crear estructura de directorios del Sandbox
mkdir -p "${RUN_DIR}/bin"
mkdir -p "${RUN_DIR}/mock_emmc/backups"
mkdir -p "${RUN_DIR}/mock_emmc/backups/reports"
mkdir -p "${RUN_DIR}/mock_emmc/snapshots"
mkdir -p "${RUN_DIR}/mock_etc"
mkdir -p "${RUN_DIR}/mock_srv/sistema_tesis"
mkdir -p "${RUN_DIR}/mock_srv/edge_iot"
mkdir -p "${RUN_DIR}/mock_srv/openclaw"
mkdir -p "${RUN_DIR}/mock_restore"
mkdir -p "${RUN_DIR}/mock_rotate_backups"
mkdir -p "${RUN_DIR}/mock_rotate_logs"
mkdir -p "${RUN_DIR}/tmp"

# 2. Generar wrapper de python3 para compatibilidad en Git Bash de Windows
cat <<'EOF' > "${RUN_DIR}/bin/python3"
#!/usr/bin/env bash
python "$@"
EOF
chmod +x "${RUN_DIR}/bin/python3"

# Configurar el PATH para usar nuestro wrapper de python3
export PATH="${RUN_DIR}/bin:${PATH}"

# Validar que python3 esté activo mediante el wrapper
python3_ver=$(python3 --version 2>&1)
echo "Python3 wrapper activo: ${python3_ver}"

# 3. Crear archivos de prueba simulados (datos de entrada)
echo "contenido critico sistema tesis" > "${RUN_DIR}/mock_srv/sistema_tesis/critical.txt"
echo "otros datos sistema" > "${RUN_DIR}/mock_srv/sistema_tesis/config.json"

echo "clave privada edge iot" > "${RUN_DIR}/mock_srv/edge_iot/critical_edge.txt"
echo "metadatos hardware" > "${RUN_DIR}/mock_srv/edge_iot/device_key.pem"

echo "logica bot autonomo openclaw" > "${RUN_DIR}/mock_srv/openclaw/critical_claw.txt"
echo "configuraciones" > "${RUN_DIR}/mock_srv/openclaw/bot.py"

# 4. Definir las rutas relativas que se guardarán en el tar
# En Git Bash de Windows, tar -C / removerá la letra de unidad (ej: V:/) convirtiéndola en Sistema_Operativo_Tesis_Posgrado/...
# Por lo tanto, para que coincida en la extracción de la sandbox, las rutas críticas deben declararse relativas.
RELATIVE_ROOT="Sistema_Operativo_Tesis_Posgrado/scratch/test_backup_restore/${RUN_ID}"
CRITICAL_SISTEMA="${RELATIVE_ROOT}/mock_srv/sistema_tesis/critical.txt"
CRITICAL_EDGE="${RELATIVE_ROOT}/mock_srv/edge_iot/critical_edge.txt"
CRITICAL_CLAW="${RELATIVE_ROOT}/mock_srv/openclaw/critical_claw.txt"

# 5. Generar archivo de política de backup de dominios
# Nota: La ruta de include_paths debe ser absoluta de Windows (con V:/) para que Python os.path.exists sea True
cat <<EOF > "${RUN_DIR}/mock_etc/domain_backup_policy.json"
{
  "encryption": "required_age_or_gpg",
  "domains": {
    "sistema_tesis": {
      "backup_dir": "${RUN_DIR}/mock_emmc/backups/sistema_tesis",
      "snapshot_dir": "${RUN_DIR}/mock_emmc/snapshots/sistema_tesis",
      "include_paths": ["V:/Sistema_Operativo_Tesis_Posgrado/scratch/test_backup_restore/${RUN_ID}/mock_srv/sistema_tesis"],
      "exclude_globs": ["*.tmp"],
      "critical_paths": ["${CRITICAL_SISTEMA}"]
    },
    "edge_iot": {
      "backup_dir": "${RUN_DIR}/mock_emmc/backups/edge_iot",
      "snapshot_dir": "${RUN_DIR}/mock_emmc/snapshots/edge_iot",
      "include_paths": ["V:/Sistema_Operativo_Tesis_Posgrado/scratch/test_backup_restore/${RUN_ID}/mock_srv/edge_iot"],
      "exclude_globs": ["*.tmp"],
      "critical_paths": ["${CRITICAL_EDGE}"]
    },
    "openclaw": {
      "backup_dir": "${RUN_DIR}/mock_emmc/backups/openclaw",
      "snapshot_dir": "${RUN_DIR}/mock_emmc/snapshots/openclaw",
      "include_paths": ["V:/Sistema_Operativo_Tesis_Posgrado/scratch/test_backup_restore/${RUN_ID}/mock_srv/openclaw"],
      "exclude_globs": ["*.tmp"],
      "critical_paths": ["${CRITICAL_CLAW}"]
    }
  }
}
EOF

# 6. Configurar variables de entorno requeridas por los scripts de respaldo
export TESIS_EMMC_ROOT="${RUN_DIR}/mock_emmc"
export TESIS_BACKUP_POLICY="${RUN_DIR}/mock_etc/domain_backup_policy.json"
export TESIS_BACKUP_TMPDIR="${RUN_DIR}/tmp"
export TESIS_BACKUP_SIGN_KEY="clave_secreta_de_prueba_hmac_2026_t035"

echo "=== PASO 1: Ejecutando ejecutar_respaldo.sh ==="
backup_out=$(bash "${REPO_ROOT}/ops/respaldo/ejecutar_respaldo.sh")
echo "${backup_out}"

if [[ ! "${backup_out}" =~ BACKUP_OK:(.+) ]]; then
  echo "ERROR: Falló la ejecución del respaldo."
  exit 1
fi
report_json="${BASH_REMATCH[1]}"
echo "Reporte de backup generado en: ${report_json}"

echo "=== PASO 2: Verificando firmas criptográficas HMAC ==="
# Buscar todos los manifest.json generados y verificar sus firmas
find "${RUN_DIR}/mock_emmc/backups" -name "manifest.json" | while read -r manifest; do
  echo "Validando manifest: ${manifest}"
  verify_out=$(bash "${REPO_ROOT}/ops/respaldo/verificar_respaldos.sh" "${manifest}")
  echo "${verify_out}"
  if [[ ! "${verify_out}" =~ VERIFY_SIGNATURE_OK ]]; then
    echo "ERROR: Falló la verificación de firma en ${manifest}"
    exit 1
  fi
done

echo "=== PASO 3: Ejecutando restauración en modo Sandbox ==="
# Restaurar cada dominio en una carpeta destino limpia
find "${RUN_DIR}/mock_emmc/backups" -name "manifest.json" | while read -r manifest; do
  domain=$(python3 - "${manifest}" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1], encoding='utf-8').read())['domain'])
PY
)
  echo "Restaurando dominio [${domain}] desde manifest [${manifest}]..."
  restore_out=$(bash "${REPO_ROOT}/ops/recuperacion/restaurar_desde_emmc.sh" \
    --domain "${domain}" \
    --manifest "${manifest}" \
    --mode sandbox \
    --target "${RUN_DIR}/mock_restore/${domain}")
  echo "${restore_out}"
  if [[ ! "${restore_out}" =~ RESTORE_OK: ]]; then
    echo "ERROR: Falló la restauración del dominio ${domain}"
    exit 1
  fi
done

echo "=== PASO 4: Generando y validando reporte de restauración global ==="
bash "${REPO_ROOT}/ops/recuperacion/reporte_restauracion.sh" "${RUN_DIR}/mock_emmc/backups" > "${RUN_DIR}/global_recovery_report.json"
cat "${RUN_DIR}/global_recovery_report.json"

# Validar que todos los reportes integrados tengan status 'ok'
failures=$(python3 - "${RUN_DIR}/global_recovery_report.json" <<'PY'
import json, sys
data = json.loads(open(sys.argv[1], encoding='utf-8').read())
fails = [r for r in data['reports'] if r['status'] != 'ok']
print(len(fails))
PY
)

if [ "${failures}" -ne 0 ]; then
  echo "ERROR: Se encontraron fallas de verificación en el reporte de restauración global."
  exit 1
fi
echo "Verificación de restauración global exitosa."

echo "=== PASO 5: Validando rotación de backups (rotate_backups.py) ==="
# Crear una política de rotación ficticia para el sandbox
cat <<EOF > "${RUN_DIR}/mock_etc/backup_rotation_policy.json"
{
  "version": "2.0",
  "backup_rotation": {
    "enabled": true,
    "description": "Política de rotación de pruebas",
    "retention_days": {
      "critico": 14,
      "alto": 7,
      "operativo": 3
    },
    "limits": {
      "max_files": 3,
      "max_total_size_mb": 10,
      "min_protected_days": 1
    },
    "compression": {
      "enabled": true,
      "algorithm": "gzip",
      "trigger_age_days": 5,
      "compression_level": 6
    },
    "deduplication": {
      "enabled": true,
      "method": "sha256_content_hash",
      "keep_newer": true
    },
    "risk_patterns": {
      "critico": ["00_sistema_tesis_decisiones_"],
      "alto": ["00_sistema_tesis_bitacora_"],
      "operativo": []
    },
    "logging": {
      "enabled": true,
      "output": "${RUN_DIR}/mock_rotate_logs/backup_rotation.log",
      "level": "INFO"
    }
  }
}
EOF

# Configurar variables de entorno de rotación para apuntar a carpetas simuladas
export TESIS_ROTATE_BACKUP_DIR="${RUN_DIR}/mock_rotate_backups"
export TESIS_ROTATE_LOG_DIR="${RUN_DIR}/mock_rotate_logs"

# Crear archivos de backup mock en la carpeta de rotación para disparar límites y compresión
# Usamos el patrón de nombre esperado: stem.timestamp.bak
# 1. Archivo crítico reciente (dentro de ventana de protección de 1 día)
echo "critico reciente" > "${TESIS_ROTATE_BACKUP_DIR}/00_sistema_tesis_decisiones_a.20260522_000000.bak"
# 2. Archivo crítico viejo (>14 días, debe expirar y purgarse)
echo "critico viejo" > "${TESIS_ROTATE_BACKUP_DIR}/00_sistema_tesis_decisiones_b.20260501_000000.bak"
# 3. Archivo alto de 6 días (comprimible si trigger_age_days fuera menor, pero de 6 días, no purgable porque retención es 7)
echo "alto intermedio" > "${TESIS_ROTATE_BACKUP_DIR}/00_sistema_tesis_bitacora_a.20260516_000000.bak"
# 4. Archivo operativo viejo (>3 días, debe expirar y purgarse)
echo "operativo viejo" > "${TESIS_ROTATE_BACKUP_DIR}/diagnostico_legacy.20260510_000000.bak"
# 5. Archivos duplicados para probar deduplicación
echo "mismo contenido" > "${TESIS_ROTATE_BACKUP_DIR}/duplicado1.20260521_120000.bak"
echo "mismo contenido" > "${TESIS_ROTATE_BACKUP_DIR}/duplicado2.20260520_120000.bak" # Más antiguo, debe eliminarse por deduplicación

echo "Ejecutando rotación en modo Dry-Run..."
python "${REPO_ROOT}/07_scripts/ops/rotate_backups.py" --policy "${RUN_DIR}/mock_etc/backup_rotation_policy.json" --json

echo "Ejecutando rotación real (--apply)..."
python "${REPO_ROOT}/07_scripts/ops/rotate_backups.py" --policy "${RUN_DIR}/mock_etc/backup_rotation_policy.json" --apply --json

# Validar que duplicado2 fue eliminado
if [ -f "${TESIS_ROTATE_BACKUP_DIR}/duplicado2.20260520_120000.bak" ]; then
  echo "ERROR: La deduplicación no eliminó duplicado2"
  exit 1
fi

# Validar que operativo viejo fue eliminado
if [ -f "${TESIS_ROTATE_BACKUP_DIR}/diagnostico_legacy.20260510_000000.bak" ]; then
  echo "ERROR: No se purgó el backup operativo viejo"
  exit 1
fi

echo "=== INTEGRACIÓN Y PRUEBA DE HUMO COMPLETADAS CON ÉXITO ==="
exit 0
