# Aislamiento de Red y Runtime por Dominio

Fuente maquina-legible:
- `manifests/domain_runtime_isolation.yaml`
- `manifests/domain_network_policy.yaml`
- `manifests/interdomain_exchange_contract.yaml`

## Baseline
- Modelo: mixto fuerte.
- `systemd` endurecido para `sistema_tesis`, `openclaw` y servicios administrativos.
- Contenedores reservados para wrappers auxiliares o carriles experimentales de `openclaw`.
- Sin HTTP entre dominios por default.

## Dominios
- `sistema_tesis`: base operativa, publicación y auditoría.
- `openclaw`: capa asistiva opcional con salida controlada y entrada solo por `localhost`.
- `edge_iot`: aislado del canon y de la base documental.
- `administrativo`: mantenimiento y backups, sin nube.
- `personal`: workspace lógico sin servicio persistente.

## Contratos permitidos
- archivos draft,
- spool local,
- CLI explícita,
- nada de lectura libre entre workspaces ni acceso directo a SQLite de otros dominios.

## Enforcement validado
- `openclaw` solo integra por `archivo_draft` y `cli_explicita`.
- `edge_iot` solo integra por `spool_local`.
- secretos por dominio se leen solo por el dominio autorizado.
- HTTP interdominio y acceso directo a SQLite de otro dominio deben fallar en pruebas reales del host.

## Validacion operativa
- bateria host: `bash ops/seguridad/validar_integracion_entre_dominios.sh`
- exito esperado:
  - `archivo_draft`, `spool_local` y `cli_explicita` pasan;
  - lectura cruzada de workspaces, secretos y SQLite falla;
  - restore cruzado falla por discrepancia explicita de dominio.
- interpretacion:
  - `permission denied`, `unreadable`, `explicit failure` y salida distinta de cero son cumplimiento esperado en casos negativos;
  - `no such file` no cuenta como evidencia suficiente si la prueba no preparo antes el artefacto centinela.

_Última actualización: `2026-04-13`._
