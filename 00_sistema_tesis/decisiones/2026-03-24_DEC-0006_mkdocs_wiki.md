<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-24_DEC-0006_ | Versión: 1.3.0 | Estado: Validado | Auditoría: [x] -->

# DEC-0006: Integración de MkDocs Material y GitHub Pages

- **Fecha:** 2026-03-24
- **Estado:** aceptado
- **Autor(es):** Tesista / Sistema Operativo de Tesis

## Contexto

El Sistema Operativo de Tesis genera artefactos Markdown consistentes mediante `build_wiki.py`. Sin embargo, para que el maestrante pueda compartir sus avances con directores de tesis y pares académicos, se requiere una interfaz visual profesional, móvil-friendly y accesible desde una URL pública sin costo.

## Decisión

Se ha seleccionado **MkDocs** con el tema **Material for MkDocs** como el motor de visualización oficial. 

La wiki se servirá de manera gratuita a través de **GitHub Pages**.

### Flujo de Trabajo
1. El usuario ejecuta `build_all.py` localmente (generando los .md en `06_dashboard/wiki`).
2. El usuario hace `git push`.
3. Un GitHub Action (`pages.yml`) detecta el cambio, instala MkDocs-Material en la nube, compila el sitio estático y lo publica en la URL del repositorio de GitHub.

## Alternativas consideradas

- **GitHub Wiki Nativa:** Se descartó por su limitada personalización y dificultad para automatizar la inserción de tablas complejas desde scripts.
- **Docusaurus:** Se descartó por requerir Node.js/React, añadiendo complejidad innecesaria (rozamiento alto) frente a MkDocs que es nativo de Python.
- **Alojamiento en Servidor Propio:** Se descartó para evitar el mantenimiento de infraestructura y asegurar la persistencia gratuita.
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

- **Positivas:**
  - **Cero costo:** Hosting gratuito de por vida por parte de GitHub.
  - **Estética Profesional:** Tema Material con soporte para modo oscuro, búsqueda instantánea y navegación fluida.
  - **Docs-as-Code:** Toda la wiki está versiónada y se deriva directamente del código fuente.
- **Negativas/Riesgos:**
  - Requiere que el repositorio sea público (o tener GitHub Pro para Pages privado). 
  - Añade un tiempo de espera de ~2-3 minutos tras el push para ver los cambios en vivo.

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

_Última actualización: `2026-04-04`._
