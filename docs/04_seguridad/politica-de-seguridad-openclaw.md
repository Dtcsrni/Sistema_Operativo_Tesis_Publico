# Politica de Seguridad OpenClaw

OpenClaw opera con minimo privilegio. Las acciones destructivas o de alto impacto requieren confirmacion humana reforzada.

## Secretos por dominio
- v1 usa `EnvironmentFile` por dominio en `/etc/tesis-os/domains/`.
- Cada dominio carga solo su archivo:
  - `personal.env`
  - `profesional.env`
  - `academico.env`
  - `edge.env`
  - `administrativo.env`
- `doctor`, `secretos estado` y `presupuesto estado` nunca imprimen llaves, tokens ni rutas sensibles completas.

## Restricciones duras
- `edge` y `administrativo` no usan nube por default.
- `personal` no mezcla sesiones académicas ni operativas.
- `academico` y `profesional` pueden usar nube solo si el dominio lo permite y el presupuesto no está agotado.
- Las sesiones `gemini_web_assisted` y `chatgpt_plus_web_assisted` se etiquetan como `human_supervised_web_session`.

## Presupuesto y degradación
- El presupuesto global del sistema manda.
- Cada dominio tiene sublímites y acción operativa propia.
- En `warning` o `critical`, el sistema degrada a `local`, `offline` o `manual`.
- En `exhausted`, la nube queda bloqueada.

## Referencias
- Ver también `docs/04_seguridad/modelo-de-amenazas-openclaw.md`.

_Última actualización: `2026-04-13`._
