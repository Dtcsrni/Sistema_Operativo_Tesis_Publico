# Integracion Segura entre Dominios

Fuente maquina-legible:
- `manifests/domain_integration_security_policy.yaml`
- `manifests/interdomain_exchange_contract.yaml`

## Objetivo
- demostrar en host real que solo funcionan los canales declarados;
- bloquear accesos cruzados directos entre `sistema_tesis`, `openclaw` y `edge_iot`;
- dejar evidencia administrativa reproducible.

## Canal administrativo
- script principal: `bash ops/seguridad/validar_integracion_entre_dominios.sh`
- smoke subyacente: `bash tests/smoke/test_domain_integration_security.sh`
- salida por default: `/var/log/tesis-admin/domain_integration_security_report_<timestamp>.log`

## Casos positivos
- `openclaw -> sistema_tesis` por `archivo_draft`
- `sistema_tesis -> openclaw` por `cli_explicita`
- `edge_iot -> sistema_tesis` por `spool_local`

## Casos negativos
- `edge_iot` no puede leer runtime ni SQLite de `openclaw`
- `openclaw` no puede tocar runtime ni workspace de `edge_iot`
- no hay HTTP entre dominios
- no hay lectura cruzada libre de `workspaces`
- no hay lectura de secretos fuera del dominio permitido
- no hay restore cruzado entre dominios

## Interpretacion de resultados
- un caso negativo pasa cuando falla por permisos, ruta no legible o rechazo explicito de contrato;
- un caso positivo pasa solo cuando la operacion se ejecuta en el usuario correcto y deja el artefacto esperado;
- si una prueba negativa falla por falta accidental del archivo y no por permiso, hay que corregir el montaje del caso antes de aceptar el resultado.

_Última actualización: `2026-04-14`._
