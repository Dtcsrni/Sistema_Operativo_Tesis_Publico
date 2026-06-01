# Chequeo rápido de servicios que usan Dockerfile.agent
# Detecta si el servicio especifica un comando de arranque, un healthcheck y el volumen 07_scripts

$composeFiles = @(
    'docker-compose.yml',
    'docker-compose.pc.yml',
    'docker-compose.pc.clean.yml',
    'docker-compose-openclaw.yml'
)

$agentImageRegex = 'image:\s*(nucleo-openclaw|pasarela-openclaw|api-persistencia-misiones|observabilidad-command-center):'

$results = @()
$seen = @{}

foreach ($file in $composeFiles) {
    if (-not (Test-Path $file)) { continue }
    Write-Host "\n--- Analizando $file ---" -ForegroundColor Cyan
    $raw = Get-Content -Raw -Encoding UTF8 -Path $file
    $lines = $raw -split "`n"
    for ($i = 0; $i -lt $lines.Length; $i++) {
        if (($lines[$i] -match 'dockerfile:\s*Dockerfile.agent') -or ($lines[$i] -match $agentImageRegex)) {
            # buscar el nombre del servicio hacia arriba
            $service = '(desconocido)'
            for ($j = $i - 1; $j -ge 0; $j--) {
                if ($lines[$j] -match '^\s{2}([a-zA-Z0-9_-]+):\s*$') {
                    $service = $matches[1]
                    break
                }
            }
            $serviceKey = "${file}::${service}"
            if ($seen.ContainsKey($serviceKey)) { continue }
            $seen[$serviceKey] = $true
            # examinar bloque próximo
            $start = [Math]::Max(0, $i - 10)
            $end = [Math]::Min($lines.Length - 1, $i + 80)
            $block = $lines[$start..$end] -join "`n"
            $hasCommand = $false
            $hasHealthcheck = $false
            $has07Scripts = $false
            if ($block -match '(^|\n)\s*command:') { $hasCommand = $true }
            if ($block -match 'healthcheck:') { $hasHealthcheck = $true }
            if ($block -match '07_scripts') { $has07Scripts = $true }
            if ($block -match ':/workspace(\s|$)') { $has07Scripts = $true }

            $results += [PSCustomObject]@{
                File = $file
                Service = $service
                HasCommand = $hasCommand
                HasHealthcheck = $hasHealthcheck
                Has07Scripts = $has07Scripts
            }
            Write-Host "Servicio: $service | command: $hasCommand | healthcheck: $hasHealthcheck | 07_scripts: $has07Scripts"
        }
    }
}

Write-Host "\nResumen:" -ForegroundColor Green
$grouped = $results | Group-Object -Property File
foreach ($g in $grouped) {
    Write-Host ("`n{0}: {1} servicios con Dockerfile.agent" -f $g.Name, $g.Count) -ForegroundColor Yellow
    $g.Group | Format-Table Service, HasCommand, HasHealthcheck, Has07Scripts -AutoSize
}

# Recomendación breve
Write-Host "\nRecomendaciones:" -ForegroundColor Magenta
Write-Host "- Asegurar que servicios que usan Dockerfile.agent definan 'command' para arrancar la pasarela cuando corresponda." -ForegroundColor White
Write-Host "- Añadir 'healthcheck' apuntando a /health o endpoint propio por servicio." -ForegroundColor White
Write-Host "- Montar '07_scripts' y 'runtime/openclaw' donde se espere ejecutar 'openclaw_cli.py' o importar módulos locales." -ForegroundColor White
Write-Host "- Agregar un script CI que ejecute este chequeo y haga 'docker compose -f <file> config' seguido de comprobaciones HTTP." -ForegroundColor White

# Exit non-zero si se detectan problemas
$bad = @($results | Where-Object { -not $_.HasCommand -or -not $_.HasHealthcheck -or -not $_.Has07Scripts })
if ($bad.Count -gt 0) {
    Write-Host "\nProblemas detectados: $($bad.Count)" -ForegroundColor Red
    exit 2
}

Write-Host "\nNo se detectaron problemas básicos." -ForegroundColor Green
exit 0
