# Hardening Base

- Activar firewall.
- Reducir servicios expuestos.
- Mantener paquetes minimos necesarios.
- Separar secretos en `config/env` o vault.
- No ejecutar automatizaciones privilegiadas sin justificacion.

## Baseline T-030
- Usuarios y grupos dedicados por dominio: `tesis`, `openclaw`, `edgeiot`, `tesisadmin`.
- `systemd` endurecido con `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict` y rutas mínimas de escritura.
- Sin HTTP entre dominios por default.
- Comunicación interdominio solo por archivos draft, spool local o CLI explícita.
- `openclaw` escucha solo en `localhost` y no acepta exposición externa.
- `edge_iot` queda sin acceso directo a canon, publicación ni SQLite de `openclaw`.

## Corte T-031
- `edge_iot` añade hardening del host con `ufw`, `fail2ban` y `ssh` endurecido.
- Se mantiene `ssh` como único ingreso por default hasta que `T-032` defina servicios y puertos del dominio.
- La política detallada vive en `docs/04_seguridad/hardening-edge-iot.md`.

_Última actualización: `2026-04-14`._
