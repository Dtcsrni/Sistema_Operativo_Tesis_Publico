param(
  [Parameter(Mandatory=$true)][string]$ImagenPath,
  [Parameter(Mandatory=$true)][string]$DispositivoObjetivo
)
Write-Host "Usa una herramienta de imagen raw confiable para grabar $ImagenPath en $DispositivoObjetivo"
Write-Host "Verifica dos veces el dispositivo antes de escribir."
