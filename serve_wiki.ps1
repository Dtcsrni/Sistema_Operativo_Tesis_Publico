# serve_wiki.ps1
# Script para iniciar MkDocs automáticamente dentro del entorno nativo WSL2.

Write-Host "Iniciando entorno WSL2 para MkDocs..." -ForegroundColor Cyan
Write-Host "El servidor estará disponible en http://127.0.0.1:8000/" -ForegroundColor Green
Write-Host "Presiona Ctrl+C para detener el servidor.`n" -ForegroundColor Yellow

# Ejecuta mkdocs dentro de WSL, activando previamente el entorno virtual.
wsl bash -c "source .venv/bin/activate && mkdocs serve"
