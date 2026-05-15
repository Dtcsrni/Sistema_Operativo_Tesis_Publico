# Carga las credenciales de Telegram desde config/env/openclaw.env
$envFile = "config\env\openclaw.env"
Get-Content $envFile | Where-Object { 
    $_.Contains("OPENCLAW_TELEGRAM") -and -not $_.StartsWith("#") 
} | ForEach-Object {
    $parts = $_ -split "=", 2
    if ($parts.Count -eq 2) {
        $var = $parts[0].Trim()
        $val = $parts[1].Trim()
        Write-Host "Loading: $var"
        [Environment]::SetEnvironmentVariable($var, $val, "Process")
    }
}

# Variables del watcher
$env:WATCHER_TELEGRAM_NOTIFY = "1"
$env:WATCHER_EXPECTED_MODELS = "phi4:14b,qwen3:14b,hermes3:3b,qwen2.5:1.5b,qwen2.5:0.5b"

Write-Host "🚀 Iniciando Watcher MOE Benchmark con notificaciones Telegram"
Write-Host "Token: $($env:OPENCLAW_TELEGRAM_TOKEN -replace '(.{10}).*(.{10})', '$1....*2')"
Write-Host "Chat ID: $($env:OPENCLAW_TELEGRAM_CHAT_ID)"
Write-Host "Modelos esperados: $($env:WATCHER_EXPECTED_MODELS)"
Write-Host ""

python 07_scripts/benchmarks/watch_runs.py --interval 15
