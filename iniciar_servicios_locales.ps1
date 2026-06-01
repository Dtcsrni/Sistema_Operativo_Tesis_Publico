# iniciar_servicios_locales.ps1
# Script para iniciar de forma automatizada y segura los servicios locales de OpenClaw y la tesis.
# Carga variables de entorno desde .env, libera puertos ocupados y levanta los servidores en background.

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  INICIANDO SERVICIOS LOCALES DE LA TESIS (OPENCLAW)" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# 1. Cargar archivo .env si existe en el directorio raíz
if (Test-Path ".env") {
    Write-Host "[INFO] Cargando variables de entorno desde .env..." -ForegroundColor Yellow
    Get-Content .env | ForEach-Object {
        if ($_ -match '^(?<name>[^=]+)=(?<value>.*)$') {
            $name = $Matches.name.Trim()
            $value = $Matches.value.Trim().Trim('"').Trim("'")
            if ($name -and $value) {
                [System.Environment]::SetEnvironmentVariable($name, $value)
                Set-Item -Path "Env:\$name" -Value $value
            }
        }
    }
    Write-Host "[OK] Variables de entorno cargadas con éxito." -ForegroundColor Green
} else {
    Write-Host "[WARN] No se encontró el archivo .env en la raíz del proyecto." -ForegroundColor Red
}

# Forzar codificación UTF-8 en el entorno de Python para evitar errores con emojis en Windows
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# 2. Verificar y liberar puertos si están previamente ocupados
$ports = @{
    18789 = "Pasarela OpenClaw (Gateway)"
    8001  = "API de Persistencia PET"
    4000  = "Mission Control (Next.js)"
    8082  = "Dashboard de Observabilidad"
    8765  = "Serena MCP HTTP"
}

foreach ($port in $ports.Keys) {
    $conn = Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq $port } -ErrorAction SilentlyContinue
    if ($conn) {
        $procId = $conn.OwningProcess
        $procName = (Get-Process -Id $procId -ErrorAction SilentlyContinue).ProcessName
        Write-Host "[WARN] El puerto $port ($($ports[$port])) ya está en uso por el proceso ID $procId ($procName)." -ForegroundColor Yellow
        Write-Host "[INFO] Liberando puerto $port..." -ForegroundColor Yellow
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
}

# 3. Lanzar API de Persistencia PET (Puerto 8001)
Write-Host "[START] Iniciando API de Persistencia PET (puerto 8001)..." -ForegroundColor Yellow
Start-Process python -ArgumentList "07_scripts/pet_api_server.py --host 127.0.0.1 --port 8001 --db runtime/openclaw/openclaw_store.db" -NoNewWindow -PassThru

# 4. Lanzar Pasarela OpenClaw (Puerto 18789)
Write-Host "[START] Iniciando Pasarela OpenClaw (puerto 18789)..." -ForegroundColor Yellow
Start-Process python -ArgumentList "runtime/openclaw/bin/openclaw_cli.py pasarela servir --host 127.0.0.1 --port 18789" -NoNewWindow -PassThru

# 5. Iniciar Serena MCP en puerto 8765 si está apagada
$serenaConn = Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq 8765 } -ErrorAction SilentlyContinue
if (-not $serenaConn) {
    Write-Host "[START] Iniciando Serena MCP HTTP (puerto 8765)..." -ForegroundColor Yellow
    Start-Process python -ArgumentList "07_scripts/serena/serena_http_supervisor.py" -NoNewWindow -PassThru
} else {
    Write-Host "[OK] Serena MCP ya está activa en el puerto 8765." -ForegroundColor Green
}

# 6. Iniciar Dashboard de Observabilidad en puerto 8082 si está apagado
$obsConn = Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq 8082 } -ErrorAction SilentlyContinue
if (-not $obsConn) {
    Write-Host "[START] Iniciando Dashboard de Observabilidad (puerto 8082)..." -ForegroundColor Yellow
    Start-Process python -ArgumentList "07_scripts/ops/serve_observability_dashboard.py" -NoNewWindow -PassThru
} else {
    Write-Host "[OK] Dashboard de Observabilidad ya está activo en el puerto 8082." -ForegroundColor Green
}

# 7. Iniciar Mission Control (Next.js) en puerto 4000 si está apagado
$mcConn = Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq 4000 } -ErrorAction SilentlyContinue
if (-not $mcConn) {
    Write-Host "[START] Iniciando Mission Control (Next.js en puerto 4000)..." -ForegroundColor Yellow
    $mcPath = Join-Path $PSScriptRoot "mission_control"
    if (Test-Path $mcPath) {
        Start-Process powershell.exe -ArgumentList "-NoProfile -Command `"cd '$mcPath'; npm run dev 2>&1`"" -NoNewWindow -PassThru
    } else {
        Write-Host "[WARN] No se encontró el directorio mission_control. Saltando." -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] Mission Control ya está activo en el puerto 4000." -ForegroundColor Green
}

Write-Host "[SUCCESS] Todos los servicios locales han sido iniciados correctamente." -ForegroundColor Green
Write-Host "Puedes interactuar con el chat en http://localhost:4000" -ForegroundColor Cyan
