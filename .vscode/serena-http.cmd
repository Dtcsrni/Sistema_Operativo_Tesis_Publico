@echo off
setlocal

set "WORKSPACE_DIR=%~dp0.."
set "SERVER_SCRIPT=%WORKSPACE_DIR%\07_scripts\serena_mcp.py"
set "VENV_SCRIPTS_PY=%WORKSPACE_DIR%\.venv\Scripts\python.exe"
set "VENV_BIN_PY=%WORKSPACE_DIR%\.venv\bin\python.exe"

if not exist "%SERVER_SCRIPT%" (
  >&2 echo [serena-http] Script no encontrado: %SERVER_SCRIPT%
  exit /b 1
)

set "SISTEMA_TESIS_ROOT=%WORKSPACE_DIR%"
set "PYTHONUNBUFFERED=1"
set "PYTHONUTF8=1"
if not defined SERENA_MCP_DEBUG_LOG set "SERENA_MCP_DEBUG_LOG=%WORKSPACE_DIR%\00_sistema_tesis\bitacora\audit_history\serena_mcp_debug.log"

set "CHECK_SCRIPT=%WORKSPACE_DIR%\07_scripts\check_serena_access.py"

if exist "%VENV_SCRIPTS_PY%" (
  "%VENV_SCRIPTS_PY%" -u "%CHECK_SCRIPT%" --attempt-start-http
  exit /b %ERRORLEVEL%
)

if exist "%VENV_BIN_PY%" (
  "%VENV_BIN_PY%" -u "%CHECK_SCRIPT%" --attempt-start-http
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if not errorlevel 1 (
  python -u "%CHECK_SCRIPT%" --attempt-start-http
  exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 -u "%CHECK_SCRIPT%" --attempt-start-http
  exit /b %ERRORLEVEL%
)

>&2 echo [serena-http] Python no encontrado. Se intentó: %VENV_SCRIPTS_PY%, %VENV_BIN_PY%, python, py -3
exit /b 1
