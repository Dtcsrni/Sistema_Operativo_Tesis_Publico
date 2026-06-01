# pull_hermes_models.ps1 -- Descarga modelos Hermes 3 en PC via Ollama
# Uso: .\07_scripts\pull_hermes_models.ps1
# Requisito: Ollama corriendo en localhost:11434

param(
    [string]$BaseUrl = "http://127.0.0.1:11434",
    [switch]$SkipCheck
)

$ErrorActionPreference = "Stop"
$models = @(
    @{ name = "hermes3:8b";  size = "~5.0GB"; vram = "8GB"; notes = "Principal - RTX 4060 Ti 8GB" },
    @{ name = "hermes3:3b";  size = "~2.2GB"; vram = "4GB"; notes = "Fallback ligero" }
)

Write-Host "`n[HERMES PULL] Descargando modelos para PC (RTX 4060 Ti 8GB VRAM)"
Write-Host "  Ollama: $BaseUrl`n"

# Verificar Ollama disponible
if (-not $SkipCheck) {
    try {
        $null = Invoke-RestMethod -Uri "$BaseUrl/api/tags" -TimeoutSec 5
        Write-Host "[OK] Ollama disponible`n"
    } catch {
        Write-Host "[ERROR] Ollama no disponible en $BaseUrl"
        Write-Host "  Inicia Ollama con: ollama serve"
        exit 1
    }
}

foreach ($m in $models) {
    Write-Host "[PULL] $($m.name)  ($($m.size), VRAM minima: $($m.vram))"
    Write-Host "       $($m.notes)"
    ollama pull $m.name
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK]   $($m.name) descargado`n"
    } else {
        Write-Host "[WARN] $($m.name) fallo (puede no estar disponible en este registro)`n"
    }
}

Write-Host "[DONE] Modelos Hermes descargados."
Write-Host "`nSIGUIENTE PASO:"
Write-Host "  1. Ejecuta el benchmark:   python 07_scripts/run_pc_benchmark_hermes.py"
Write-Host "  2. Si el benchmark es positivo, activa Hermes:"
Write-Host "     $env:OPENCLAW_HERMES_ENABLED='1'"
Write-Host "  3. Verifica el router:     python 07_scripts/build_all.py --group openclaw"
