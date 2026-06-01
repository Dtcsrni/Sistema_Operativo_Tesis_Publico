# ==============================================================================
# generar_accesos_directos.ps1 - Generador de Accesos Directos Resilientes para Windows
# ==============================================================================
# Este script crea o repara los accesos directos (.lnk) en el escritorio
# del usuario para facilitar la operación del Sistema Operativo de Tesis (SIOT).
# Es completamente dinámico y detecta la ubicación física del repositorio.
# ==============================================================================

# 1. Determinar la raíz del repositorio dinámicamente
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Write-Host "SIOT Repositorio detectado en: $RepoRoot" -ForegroundColor Cyan

# 2. Obtener la ruta del Escritorio de Windows del usuario actual
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
if (-not $DesktopPath) {
    $DesktopPath = "$env:USERPROFILE\Desktop"
}
Write-Host "Escritorio del usuario detectado en: $DesktopPath" -ForegroundColor Cyan

# 3. Inicializar el objeto COM de WScript.Shell para la creación de links
$WshShell = New-Object -ComObject WScript.Shell

# Definición de accesos directos a generar
$Shortcuts = @(
    @{
        Name = "SIOT - Wiki de Tesis.lnk"
        Target = "pythonw.exe"
        Args = "07_scripts/ops/siot_launcher.py --port 8081"
        WorkingDir = $RepoRoot
        Icon = "$env:SystemRoot\System32\shell32.dll,14" # Icono de libro/documento
        Desc = "Abre la Wiki de documentación técnica y bitácoras del SIOT (Puerto 8081)"
    },
    @{
        Name = "SIOT - Tablero de Misiones.lnk"
        Target = "pythonw.exe"
        Args = "07_scripts/ops/siot_launcher.py --port 4000"
        WorkingDir = $RepoRoot
        Icon = "$env:SystemRoot\System32\shell32.dll,24" # Icono de panel de control
        Desc = "Abre el Mission Control Web UI de Next.js (Puerto 4000)"
    },
    @{
        Name = "SIOT - Observabilidad y Estado.lnk"
        Target = "pythonw.exe"
        Args = "07_scripts/ops/siot_launcher.py --port 8082"
        WorkingDir = $RepoRoot
        Icon = "$env:SystemRoot\System32\shell32.dll,18" # Icono de gráfica/estado
        Desc = "Abre el Tablero de Observabilidad y Telemetría del stack (Puerto 8082)"
    },
    @{
        Name = "SIOT - Consola de Tesis.lnk"
        Target = "powershell.exe"
        Args = "-NoExit -Command `"Set-Location '$RepoRoot'; python 07_scripts/tesis.py status`""
        WorkingDir = $RepoRoot
        Icon = "$env:SystemRoot\System32\shell32.dll,95" # Icono de consola/herramienta
        Desc = "Abre una consola de comandos en la raíz del proyecto ejecutando tesis.py status"
    },
    @{
        Name = "SIOT - Iniciar Todo el Stack.lnk"
        Target = "powershell.exe"
        Args = "-NoExit -Command `"Set-Location '$RepoRoot'; docker compose up -d; python 07_scripts/start_backends_auto_v2.py`""
        WorkingDir = $RepoRoot
        Icon = "$env:SystemRoot\System32\shell32.dll,238" # Icono de inicio/play
        Desc = "Inicia el stack Docker unificado y los backends locales de inferencia (Ollama/LlamaCPP)"
    },
    @{
        Name = "SIOT - Correr Auditoría de Tesis.lnk"
        Target = "powershell.exe"
        Args = "-NoExit -Command `"Set-Location '$RepoRoot'; python 07_scripts/build_all.py`""
        WorkingDir = $RepoRoot
        Icon = "$env:SystemRoot\System32\shell32.dll,142" # Icono de check/aprobación
        Desc = "Ejecuta el script de auditoría build_all.py para validar integridad del Ledger y bitácoras"
    }
)

Write-Host "`nGenerando y reparando accesos directos en el escritorio..." -ForegroundColor Yellow

foreach ($Sc in $Shortcuts) {
    $FilePath = Join-Path $DesktopPath $Sc.Name
    
    # Si ya existe, se elimina para recrearlo con las rutas actualizadas
    if (Test-Path $FilePath) {
        Remove-Item $FilePath -Force
        Write-Host "Reparando acceso directo existente: $($Sc.Name)" -ForegroundColor DarkYellow
    } else {
        Write-Host "Creando nuevo acceso directo: $($Sc.Name)" -ForegroundColor Green
    }
    
    try {
        $Shortcut = $WshShell.CreateShortcut($FilePath)
        $Shortcut.TargetPath = $Sc.Target
        $Shortcut.Arguments = $Sc.Args
        $Shortcut.WorkingDirectory = $Sc.WorkingDir
        $Shortcut.IconLocation = $Sc.Icon
        $Shortcut.Description = $Sc.Desc
        $Shortcut.Save()
    } catch {
        Write-Error "Error al crear el acceso directo $($Sc.Name): $_"
    }
}

Write-Host "`n[OK] ¡Proceso completado con éxito! Se han regenerado 6 accesos directos en tu escritorio." -ForegroundColor Green
