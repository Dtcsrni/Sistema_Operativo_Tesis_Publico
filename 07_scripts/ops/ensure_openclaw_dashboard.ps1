param(
    [int]$Port = 18789,
    [int]$WaitSeconds = 30,
    [switch]$NoOpen,
    [switch]$EnsureOnly,
    [switch]$InstallStartup
)

$ErrorActionPreference = "Stop"

function Get-OpenClawCommandPath {
    $command = Get-Command openclaw -ErrorAction Stop
    return $command.Path
}

function Test-GatewayListener {
    param([int]$TargetPort)

    $listener = Get-NetTCPConnection `
        -LocalAddress 127.0.0.1 `
        -LocalPort $TargetPort `
        -State Listen `
        -ErrorAction SilentlyContinue |
        Select-Object -First 1

    return $null -ne $listener
}

function Test-DashboardHttp {
    param([int]$TargetPort)

    try {
        $response = Invoke-WebRequest `
            -UseBasicParsing `
            -Uri "http://127.0.0.1:$TargetPort/" `
            -TimeoutSec 5
        return $response.StatusCode -eq 200 -and
            [string]$response.Headers["Content-Type"] -like "text/html*"
    } catch {
        return $false
    }
}

function Load-EnvFile {
    param([string]$EnvPath)
    
    if (-not (Test-Path $EnvPath)) {
        Write-Warning "Environment file not found: $EnvPath"
        return @{}
    }
    
    $envVars = @{}
    Get-Content -Path $EnvPath | Where-Object { $_ -match '^\s*[A-Z_]+=.+$' } | ForEach-Object {
        $parts = $_ -split '=', 2
        if ($parts.Length -eq 2) {
            $key = $parts[0].Trim()
            $value = $parts[1].Trim() -replace '^"(.*)"$', '$1'
            $envVars[$key] = $value
        }
    }
    return $envVars
}

function Start-GatewayIfNeeded {
    param(
        [int]$TargetPort,
        [int]$TimeoutSeconds
    )

    if ((Test-GatewayListener -TargetPort $TargetPort) -and (Test-DashboardHttp -TargetPort $TargetPort)) {
        Write-Host "OpenClaw Gateway already listening on 127.0.0.1:$TargetPort"
        return
    }

    if (Test-GatewayListener -TargetPort $TargetPort) {
        throw "Port 127.0.0.1:$TargetPort is listening, but it did not return the OpenClaw dashboard HTTP response."
    }

    $openclaw = Get-OpenClawCommandPath
    $logDir = Join-Path $env:USERPROFILE ".openclaw\logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $outLog = Join-Path $logDir "gateway-ensure-$timestamp.out.log"
    $errLog = Join-Path $logDir "gateway-ensure-$timestamp.err.log"

    # Load openclaw.env to ensure OPENCLAW_RUNTIME=docker is set
    $repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
    $envFile = Join-Path $repoRoot "config\env\openclaw.env"
    $envVars = Load-EnvFile -EnvPath $envFile
    
    # Build environment for child process
    $childEnv = @{}
    $envVars.GetEnumerator() | ForEach-Object { $childEnv[$_.Key] = $_.Value }

    Write-Host "Starting OpenClaw Gateway on 127.0.0.1:$TargetPort with OPENCLAW_RUNTIME=$($childEnv['OPENCLAW_RUNTIME'] -or 'default')"
    
    $pinfo = New-Object System.Diagnostics.ProcessStartInfo
    $pinfo.FileName = "pwsh.exe"
    $pinfo.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$openclaw`" gateway run --port $TargetPort --auth token"
    $pinfo.UseShellExecute = $false
    $pinfo.RedirectStandardOutput = $true
    $pinfo.RedirectStandardError = $true
    $pinfo.CreateNoWindow = $true
    
    # Copy workspace environment and overlay openclaw.env values
    [System.Environment]::GetEnvironmentVariables([System.EnvironmentVariableTarget]::Process).GetEnumerator() | 
        ForEach-Object { $pinfo.EnvironmentVariables[$_.Key] = $_.Value }
    $childEnv.GetEnumerator() | ForEach-Object { 
        $pinfo.EnvironmentVariables[$_.Key] = $_.Value 
    }
    
    $process = [System.Diagnostics.Process]::Start($pinfo)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ((Test-GatewayListener -TargetPort $TargetPort) -and (Test-DashboardHttp -TargetPort $TargetPort)) {
            Write-Host "OpenClaw Gateway ready on 127.0.0.1:$TargetPort"
            return
        }
        Start-Sleep -Milliseconds 500
    }

    throw "OpenClaw Gateway did not start on 127.0.0.1:$TargetPort within $TimeoutSeconds seconds."
}

function Install-UserStartupShim {
    param([int]$TargetPort)

    $startupDir = [Environment]::GetFolderPath("Startup")
    if (-not $startupDir) {
        throw "Windows Startup folder could not be resolved."
    }

    $scriptPath = $PSCommandPath
    $shimPath = Join-Path $startupDir "OpenClaw Gateway Ensure.cmd"
    $content = @"
@echo off
pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "$scriptPath" -Port $TargetPort -EnsureOnly
"@

    Set-Content -LiteralPath $shimPath -Value $content -Encoding ASCII
    Write-Host "Installed user startup shim: $shimPath"
}

if ($InstallStartup) {
    Install-UserStartupShim -TargetPort $Port
}

Start-GatewayIfNeeded -TargetPort $Port -TimeoutSeconds $WaitSeconds

if ($EnsureOnly) {
    exit 0
} elseif ($NoOpen) {
    # Return the canonical local dashboard URL without opening the browser.
    Write-Output "http://127.0.0.1:$Port/"
} else {
    # Open the canonical OpenClaw gateway dashboard URL directly to avoid opening a custom observability UI.
    $url = "http://127.0.0.1:$Port/"
    Write-Host "Opening OpenClaw gateway dashboard: $url"
    Start-Process $url
}
