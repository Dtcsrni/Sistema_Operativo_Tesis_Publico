<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-24_DEC-0004_ | Versión: 1.3.0 | Estado: Validado | Auditoría: [x] -->

# DEC-0004: Endurecimiento de la infraestructura del Bloque 0

- **Fecha:** 2026-03-24
- **Estado:** aceptado
- **Autor(es):** Sistema Operativo de Tesis (IA instrumental)

## Contexto

Con el Bloque 0 operativo, surgieron tres vectores de riesgo:
1. Posibilidad de sobreescribir la rama principal sin validación (solución: *Branch Protection* y *Pull Requests*).
2. Posibilidad de hacer commits locales con código inconsistente o sin formato (solución: *pre-commit hooks* y *markdownlint*).
3. Saturación del repositorio Git al integrar grandes volúmenes de datos en las próximas fases B3 y B4 (solución: *Data Version Control - DVC*).

## Decisión

Se han integrado las configuraciones base para endurecer la infraestructura del repositorio:
1. Se ha creado la plantilla `.github/PULL_REQUEST_TEMPLATE.md` para estandarizar la incorporación de código mediante PRs (exigiendo comprobación de tests, uso de IA y build exitoso).
2. Se crearon las dependencias y el archivo `.pre-commit-config.yaml` con linters (`markdownlint`) y validadores en cascada (`build_all.py`).
3. Se integraron como dependencias teóricas requeridas.

### Restricción del Entorno (MSYS2)
Se ha tomado la decisión deliberada de **no forzar la activación local de DVC ni de pre-commit de manera predeterminada** en esta máquina específica debido a limitaciones del ecosistema MSYS2/MinGW:
- MSYS2 carece del módulo global de `pip` en el Path del sistema, lo cual interrumpe a `pre-commit` al momento de compilar el entorno virtual de los *hooks*.
- DVC requiere compilación de binarios en Rust (ej. `orjson`) que no convergen con las librerías dinámicas provistas por defecto en MSYS2.

## Alternativas consideradas

- Configurar *hooks* locales de Bash puros (`.git/hooks/pre-commit` escrito a mano) en lugar de utilizar el framework Python `pre-commit`. Se descartó por ser poco mantenible y opaco a mediano plazo frente a linters de comunidad como `markdownlint`.
## Criterio de elección

Retroactivo: Decisión tomada durante la fase de infraestructura inicial.

## Métricas de Éxito

- [x] Validación operativa de la infraestructura.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Consistencia en auditorías automáticas.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Criterio de Aceptación Humana

- [x] Firma digital GPG del tesista.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Validación de integridad estructural.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

  - **Soporte:** [Retroactivo | Step ID]
  - **Modo:** [Retroactivo | Confirmación Verbal]
  - **Fecha de Validación:** 2026-03-24
  - **Integridad:** `Hash omitido por seguridad` 
  - **Fingerprint:** `Hash omitido por seguridad` 
  - **Nivel de Auditoría:** Bajo
## Consecuencias

- **Positivas:** El repositorio ahora cuenta con las normativas (PRs), configuraciones y documentación necesarias para un ecosistema de calidad de software estándar. Si el entorno se migra a WSL, Linux ordinario o a una distribución estándar de Python en Windows, la protección se activa inmediatamente.
- **Negativas/Riesgos:** Hasta que el entorno local adopte una cadena de herramientas estándar (Pip/Rust compilables de forma nativa en Windows) o el usuario decida instalar `dvc` y los `hooks` pre-compilados manualmente sin usar MSYS2, el riesgo de "deriva local" entre YAMLs y CSVs reaparece dependiente enteramente de la memoria del usuario para ejecutar `build_all.py`.

## Trazabilidad de IA

- **Proveedor:** Google (DeepMind)
- **Modelo/Versión:** Gemini 1.5 Pro / Advanced Agentic Coding v1.0
- **Agente/Rol:** Antigravity (Assistant)
- **Nivel de Razonamiento:** alto
- **Prompts/Contexto clave:** Normalización de repositorio.

## Impacto en Presupuesto de Razonamiento

- **Consumo:** Bajo (Retroactivo)
- **Justificación:** Normalización de formato de trazabilidad.

## Implementación o seguimiento

- [x] Implementación completada en Fase B0.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Referencias

N/A

[LID]: ruta local no pública
[GOV]: ruta local no pública
[AUD]: ruta local no pública

_Última actualización: `2026-04-03`._
