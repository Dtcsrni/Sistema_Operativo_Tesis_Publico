$ErrorActionPreference = "Stop"

function Resolve-FirstExistingPath {
  param(
    [string[]]$Candidates
  )
  foreach ($candidate in $Candidates) {
    if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path $candidate)) {
      return $candidate
    }
  }
  return ""
}

function Resolve-OllamaModelPath {
  param(
    [string]$ModelName
  )
  if ([string]::IsNullOrWhiteSpace($ModelName)) {
    return ""
  }
  try {
    $modelfile = & ollama show $ModelName --modelfile 2>$null
  } catch {
    return ""
  }
  foreach ($line in $modelfile) {
    if ($line -match '^\s*FROM\s+(.+)\s*$') {
      return $Matches[1].Trim()
    }
  }
  return ""
}

$repoRoot = if ($env:OPENCLAW_REPO_ROOT) { $env:OPENCLAW_REPO_ROOT } else { "V:\Sistema_Operativo_Tesis_Posgrado" }
$serverBin = if ($env:OPENCLAW_LLAMACPP_SERVER_BIN) { $env:OPENCLAW_LLAMACPP_SERVER_BIN } else { Resolve-FirstExistingPath @(
    "$env:LOCALAPPDATA\Programs\OpenClaw\llama.cpp\llama-server.exe",
    "$env:LOCALAPPDATA\Programs\OpenClaw\llama.cpp\bin\llama-server.exe",
    "$env:USERPROFILE\.docker\bin\inference\llama-server.exe",
    "$env:USERPROFILE\.docker\bin\inference\com.docker.llama-server.exe"
  ) }
$modelName = if ($env:OPENCLAW_LLAMACPP_MODEL_NAME) { $env:OPENCLAW_LLAMACPP_MODEL_NAME } else { "mistral-nemo:12b" }
$modelPath = if ($env:OPENCLAW_LLAMACPP_MODEL_PATH) { $env:OPENCLAW_LLAMACPP_MODEL_PATH } else { Resolve-OllamaModelPath -ModelName $modelName }
$bindHost = if ($env:OPENCLAW_LLAMACPP_BIND_HOST) { $env:OPENCLAW_LLAMACPP_BIND_HOST } else { "127.0.0.1" }
$port = if ($env:OPENCLAW_LLAMACPP_BIND_PORT) { $env:OPENCLAW_LLAMACPP_BIND_PORT } else { "21435" }
$ctx = if ($env:OPENCLAW_LLAMACPP_CTX_SIZE) { $env:OPENCLAW_LLAMACPP_CTX_SIZE } else { "4096" }
$gpuLayers = if ($env:OPENCLAW_LLAMACPP_GPU_LAYERS) { $env:OPENCLAW_LLAMACPP_GPU_LAYERS } else { "99" }
$noMmap = if ($env:OPENCLAW_LLAMACPP_NO_MMAP) { $env:OPENCLAW_LLAMACPP_NO_MMAP } else { "1" }
$extraArgsRaw = if ($env:OPENCLAW_LLAMACPP_EXTRA_ARGS) { $env:OPENCLAW_LLAMACPP_EXTRA_ARGS } else { "" }

if (-not (Test-Path $serverBin)) {
  throw "llama.cpp server no encontrado en $serverBin"
}
if ([string]::IsNullOrWhiteSpace($modelPath)) {
  throw "OPENCLAW_LLAMACPP_MODEL_PATH es obligatorio o debe existir el modelo $modelName en ollama"
}
if (-not (Test-Path $modelPath)) {
  throw "Modelo llama.cpp no encontrado en $modelPath"
}

$args = @(
  "--host", $bindHost,
  "--port", $port,
  "--ctx-size", $ctx,
  "--n-gpu-layers", $gpuLayers,
  "--model", $modelPath
)

if ($noMmap.ToLowerInvariant() -in @("1", "true", "yes", "on", "si", "sí")) {
  $args += "--no-mmap"
}

if (-not [string]::IsNullOrWhiteSpace($extraArgsRaw)) {
  $args += ($extraArgsRaw -split "\\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

& $serverBin @args
