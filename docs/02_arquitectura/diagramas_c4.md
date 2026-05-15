# Diagramas de Arquitectura (Modelo C4)

Este documento utiliza el estándar C4 para visualizar la arquitectura del Sistema Operativo de Tesis en diferentes niveles de abstracción.

## 1. Nivel 1: Contexto del Sistema
El diagrama de contexto muestra cómo el Sistema Operativo de Tesis interactúa con los actores humanos y otros sistemas externos.

```mermaid
C4Context
    title Diagrama de Contexto - Sistema Operativo de Tesis (SOT)

    Person(tesista, "Tesista Principal", "Investigador y operador del sistema.")
    System(sot, "Sistema Operativo de Tesis (SOT)", "Gobernanza, trazabilidad y soporte científico.")
    System_Ext(openclaw, "OpenClaw / Hermes", "Capas asistivas de IA para razonamiento y síntesis.")
    System_Ext(edge_node, "Orange Pi 5 Plus (Edge)", "Ejecución de workloads IoT y recolección de métricas.")
    System_Ext(public_repo, "GitHub (Público)", "Repositorio derivado, sanitizado y curado.")

    Rel(tesista, sot, "Define decisiones, opera scripts y autoriza cambios.")
    Rel(sot, openclaw, "Solicita asistencia epistémica y ruteo de tareas.")
    Rel(sot, edge_node, "Sincroniza configuración y extrae evidencia edge.")
    Rel(sot, public_repo, "Publica bundle curado y sanitizado.")
    Rel(tesista, edge_node, "Intervención física y diagnóstico local.")
```

## 2. Nivel 2: Contenedores
El diagrama de contenedores detalla los componentes lógicos internos del SOT y cómo se distribuyen entre el Escritorio y el nodo Edge.

```mermaid
C4Container
    title Diagrama de Contenedores - SOT

    Boundary(desktop, "Escritorio Primario (Control Node)") {
        Container(canon, "Canon & Ledger", "JSONL, YAML, CSV", "Fuente de verdad soberana e inmutable.")
        Container(scripts, "Scripts Operativos (tesis.py)", "Python", "CLI de gestión, auditoría y materialización.")
        Container(wiki, "Wiki & Dashboard", "Markdown/HTML", "Proyecciones derivas para observabilidad humana.")
        Container(atzin, "Toltecayotl Engine", "Weaviate/Docker", "Base de conocimientos y RAG académico.")
    }

    Boundary(edge, "Orange Pi 5 Plus (Edge Node)") {
        Container(edge_stack, "IoT Stack", "Docker/Python", "Servicios de recolección y control local.")
        Container(npu_inference, "NPU Inference", "RKLLM", "Inferencia local optimizada para hardware edge.")
    }

    Rel(scripts, canon, "Lee/Escribe", "I/O")
    Rel(scripts, atzin, "Consulta Contexto", "gRPC/HTTP")
    Rel(scripts, wiki, "Genera", "Build Pipeline")
    Rel(scripts, edge_stack, "Sincroniza", "Git Sync / SSH")
    Rel(edge_stack, npu_inference, "Usa para Offloading", "Shared Memory / Socket")
```

## 3. Nivel 3: Componentes (Scripts de Auditoría)
Muestra la interacción interna de la capa de auditoría y guardrails.

```mermaid
graph TD
    subgraph "07_scripts/audit"
        SA[security_audit.py] --> G[guardrails.py]
        SA --> VL[verify_ledger.py]
        SA --> SS[secret_scanner.py]
        SA --> DA[document_audit.py]
    end
    
    G --> Manifest[integrity_manifest.json]
    VL --> Ledger[log_sesiones_trabajo_registradas.md]
    SS --> AllFiles[Cualquier archivo no excluido]
    DA --> GlobalRefs[Referencias Globales LID/GOV/AUD]
```

_Última actualización: `2026-05-15`._
