@echo off
echo ======================================================
echo   LANZANDO ASISTENTE TOLTECAYOTL (MODO DOCKER)
echo ======================================================
echo Iniciando contenedor...
docker-compose -f docker-compose-openclaw.yml up -d

echo Entrando a la TUI Soberana...
docker exec -it openclaw-orchestrator openclaw chat --local

echo Asistente cerrado.
pause
