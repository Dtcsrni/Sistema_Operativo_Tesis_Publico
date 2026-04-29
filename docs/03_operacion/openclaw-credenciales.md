# Credenciales Operativas de OpenClaw

## Principio
Las credenciales viven fuera de Git. Configurarlas solo en `/etc/tesis-os/openclaw.env` o en `/etc/tesis-os/domains/*.env`, con permisos `0640`, y verificar con:

```bash
set -a
source /etc/tesis-os/openclaw.env
set +a
"$OPENCLAW_PYTHON_BIN" runtime/openclaw/bin/openclaw_local.py secretos estado
```

## Serena
- Variable normal: `OPENCLAW_SERENA_URL=http://127.0.0.1:8765/mcp`.
- No requiere API key para uso local.
- Activación esperada:

```bash
python3 07_scripts/check_serena_access.py --attempt-start-http --json
```

- Para exponer Serena a runtimes externos por bridge, crear un secreto local fuerte:

```bash
python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
```

Guardar el valor como `SERENA_BRIDGE_BEARER_TOKEN` fuera del repo antes de arrancar `runtime/serena_bridge/bin/serena_bridge.py`.

## Matrix latente
Matrix queda pausado por ahora y no forma parte del camino operativo diario.

Variables a futuro:
- `OPENCLAW_MATRIX_ENABLED=0`
- `OPENCLAW_MATRIX_HOMESERVER`
- `OPENCLAW_MATRIX_ACCESS_TOKEN`
- `OPENCLAW_MATRIX_USER_ID`
- `OPENCLAW_MATRIX_ROOM_IDS`
- `OPENCLAW_MATRIX_READY_ROOM_ID`

Cuando se reactive:
- Crear una cuenta bot dedicada en el homeserver.
- Obtener un access token de cliente para esa cuenta mediante login Matrix o con el flujo administrativo del homeserver.
- En Synapse, un administrador puede crear o modificar usuarios por Admin API; las llamadas administrativas requieren token de administrador.
- Invitar el bot a la sala y usar el room id real que empieza con `!`.

Verificación futura:

```bash
"$OPENCLAW_PYTHON_BIN" runtime/openclaw/bin/openclaw_local.py matrix estado
"$OPENCLAW_PYTHON_BIN" runtime/openclaw/bin/openclaw_local.py matrix polling --once
```

## Telegram
Variables:
- `OPENCLAW_TELEGRAM_ENABLED=1`
- `OPENCLAW_TELEGRAM_BOT_TOKEN`
- `OPENCLAW_TELEGRAM_CHAT_ID`

Obtención:
- En Telegram, abrir `@BotFather`.
- Crear bot con `/newbot`.
- Guardar el token entregado por BotFather como `OPENCLAW_TELEGRAM_BOT_TOKEN`.
- Escribirle al bot desde tu cuenta autorizada.
- Obtener tu chat id con un mensaje de prueba o leyendo `getUpdates` desde el endpoint de Telegram Bot API.

Verificación:

```bash
"$OPENCLAW_PYTHON_BIN" runtime/openclaw/bin/openclaw_local.py telegram estado
"$OPENCLAW_PYTHON_BIN" runtime/openclaw/bin/openclaw_local.py telegram polling --once
```

## proveedor de IA no publicado API
Variable:
- `OPENAI_API_KEY`

Obtención:
- Crear una secret key en la página de API keys de la plataforma de proveedor de IA no publicado.
- Definir límites de uso antes de habilitar el proveedor.
- Guardar la key solo en el env del dominio que vaya a usarla.

## Groq API
Variable:
- `GROQ_API_KEY`

Obtención:
- Entrar a GroqCloud Console.
- Ir a API Keys.
- Crear una key y guardarla fuera de Git.

## Gemini API
Variable:
- `GEMINI_API_KEY`

Obtención:
- Entrar a Google AI Studio.
- Crear o seleccionar un proyecto.
- Crear una API key para Gemini API.
- Configurar cuotas o alertas de facturación antes de habilitarla.

## GitHub Models
Variables:
- `GITHUB_MODELS_TOKEN` o `GITHUB_TOKEN`

Obtención:
- Crear un Personal Access Token fino en GitHub.
- Incluir permiso `models:read`.
- Usarlo solo para contexto público o redactado.

## Web Asistida
Variables:
- `OPENCLAW_CHATGPT_PLUS_ENABLED=1`
- `OPENCLAW_GEMINI_STUDENT_ENABLED=1`

Obtención:
- No son API keys; son toggles de política local.
- Requieren primer login humano supervisado en el navegador persistente.

```bash
OPENCLAW_WEB_SESSION_HEADLESS=0 "$OPENCLAW_PYTHON_BIN" runtime/openclaw/bin/openclaw_local.py sesion-web login --timeout 900
```

## Seguridad mínima
- No pegar tokens en chat, issues, commits o archivos versionados.
- Rotar cualquier token que haya sido mostrado por accidente.
- Usar cuentas bot dedicadas para Telegram y, cuando se reactive Matrix, para Matrix.
- Mantener `OPENCLAW_CLOUD_ENABLED=0` salvo activación explícita por dominio.

## Referencias externas
- proveedor de IA no publicado API keys: https://platform.openai.com/api-keys
- Groq API keys: https://console.groq.com/keys/
- Gemini API keys: https://ai.google.dev/gemini-api/docs/api-key
- Telegram Bot API: https://core.telegram.org/bots/api
- Synapse Admin API: https://matrix-org.github.io/synapse/latest/usage/administration/admin_api/
- GitHub Models quickstart: https://docs.github.com/en/github-models/quickstart

_Última actualización: `2026-04-29`._
