# serve_wiki.ps1
# Script para iniciar la wiki desde Docker Compose.

Write-Host "Iniciando siot-docs en Docker Compose..." -ForegroundColor Cyan
Write-Host "La documentación estará disponible en http://127.0.0.1:8081/" -ForegroundColor Green
Write-Host "Presiona Ctrl+C para detener el seguimiento de salida.`n" -ForegroundColor Yellow

docker compose up -d --build siot-docs
docker compose logs -f --no-log-prefix siot-docs
