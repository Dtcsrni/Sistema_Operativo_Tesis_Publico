param([Parameter(Mandatory=$true)][string]$Path)
Get-ChildItem -Path $Path -File | ForEach-Object { Get-FileHash -Algorithm SHA256 -Path $_.FullName }
