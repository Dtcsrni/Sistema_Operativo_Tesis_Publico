# Mapa de modulos del sistema

## Vista general

El sistema se organiza por subsistemas coordinados. Cada subsistema tiene una funcion distinta, artefactos fuente, artefactos derivados y una frontera de visibilidad.

## Modulos nucleares

### 1. Gobierno y soberania humana

- Proposito: asegurar que toda decision sustantiva quede vinculada a consentimiento humano y a trazabilidad explicita.
- Fuentes principales: decisiones, `ia_gobernanza.yaml`, ledger, matriz.
- Derivados: proyecciones del canon, auditorias, indicadores.
- Visible al publico: principios generales y politica de supervision.
- Privado: confirmaciones verbales exactas, hashes, soporte fino de validacion.

### 2. Trazabilidad y evidencia

- Proposito: conservar cadena verificable entre instruccion, evidencia, sesion, cambio y artefacto.
- Fuentes principales: canon, ledger, matriz, evidencia privada, registros de ingestion.
- Derivados: indices, reportes de consistencia, estado de evidencia.
- Visible al publico: existencia del mecanismo y su papel metodologico.
- Privado: archivos de evidencia, transcripciones, rutas sensibles, hashes y correlaciones internas.

### 3. Planeacion y control del trabajo

- Proposito: traducir objetivos de tesis a backlog, riesgos, roadmap y entregables.
- Fuentes principales: `backlog.csv`, `riesgos.csv`, `roadmap.csv`, `entregables.csv`.
- Derivados: resumenes, dashboard, portada README.
- Visible al publico: estado de avance de alto nivel y prioridades visibles.
- Privado: trazabilidad operativa fina cuando corresponda.

### 4. Canon tecnico y configuracion

- Proposito: definir identidad, reglas, parametros y rutas canonicas del sistema.
- Fuentes principales: `sistema_tesis.yaml`, `bloques.yaml`, `hipotesis.yaml`, `publicacion.yaml`, `wiki.yaml`.
- Derivados: wiki, dashboard, bundle publico, chequeos automáticos.
- Visible al publico: estructura general del sistema y politicas de publicacion.
- Privado: configuraciones sensibles, identidad de agente y metadatos restringidos.

### 5. Automatizacion y validacion

- Proposito: materializar, verificar y regenerar artefactos sin edicion manual de salidas derivadas.
- Fuentes principales: `07_scripts/`.
- Derivados: README generado, wiki generada, dashboard, badges, bundle publico.
- Visible al publico: que la salida es derivada, reproducible y auditable.
- Privado: auditorias completas, evidencia local y rutas internas.

### 6. Publicacion derivada y superficie publica

- Proposito: exponer una vista tecnica util para evaluacion externa sin romper la frontera de seguridad.
- Fuentes principales: politica de publicacion y artefactos generados.
- Derivados: `06_dashboard/publico/`, wiki publica, manifest y nota de seguridad.
- Visible al publico: casi todo el modulo, salvo reglas internas de enforcement y superficies privadas.
- Privado: canon bruto y evidencia fuente.

### 7. Tesis IoT como objeto gobernado

- Proposito: usar el sistema para dar continuidad al trabajo de tesis sobre resiliencia de telemetria y control adaptativo.
- Fuentes principales: hipotesis, bloques, backlog, evidencia, implementacion y manuscrito.
- Derivados: narrativa publica del proyecto, seguimiento de cobertura y estado del manuscrito.
- Visible al publico: objetivo, problema, marco actual, modulos y limites.
- Privado: evidencia no publicada, borradores internos y soportes no sanitizados.

## Relaciones clave

- Gobierno define las reglas con las que opera trazabilidad.
- Trazabilidad conserva evidencia de lo que planeacion y ejecucion producen.
- Planeacion orienta que se construye, valida o redacta.
- Canon y configuracion determinan las rutas oficiales y las salidas derivadas.
- Automatizacion convierte fuentes en vistas legibles sin duplicacion manual.
- Publicacion filtra la vista externa sin alterar la base privada.
- La tesis IoT recibe estructura, continuidad y explicabilidad gracias a todos los modulos anteriores.

## Regla de lectura

Si una persona necesita entender rapidamente el sistema:

1. Primero identifica el modulo implicado.
2. Luego localiza sus fuentes canonicas.
3. Despues revisa el flujo operativo asociado.
4. Finalmente distingue que partes son privadas y cuales son publicas.

_Última actualización: `2026-04-04`._
