param(
  [Parameter(Mandatory=$true)][string]$ImagenPath,
  [Parameter(Mandatory=$true)][string]$Sha256Esperado
)
$hash = (Get-FileHash -Algorithm SHA256 -Path $ImagenPath).Hash.ToLower()
if ($hash -ne $Sha256Esperado.ToLower()) { throw "SHA256 invalido para $ImagenPath" }
Write-Host "VALIDACION_OK $ImagenPath"
