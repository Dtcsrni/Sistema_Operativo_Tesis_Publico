<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0046 | 2026-05-21 | v1.0 | vigente -->
---
id: DEC-0046
titulo: "Principio de Arquitectura Abierta, Auto-Descubrimiento Seguro y Viabilidad Comercial"
fecha: 2026-05-21
estado: vigente
impacto: arquitectonico
area: arquitectura_sistema
autores: ["Erick Renato Vega Ceron (Tesista Principal)"]
evidencia_humana: "evento interno no público"
step_id: "validación humana interna no pública"
decisiones_relacionadas: ["DEC-0001", "DEC-0004", "DEC-0005", "DEC-0025", "DEC-0030", "DEC-0042"]
---

# DEC-0046: Principio de Arquitectura Abierta, Auto-Descubrimiento Seguro y Viabilidad Comercial

## Contexto

Durante la implementacion de los servicios del Nodo Edge (T-031, T-032), el Tesista Principal
establecio una directriz estrategica fundamental que trasciende lo tecnico y define la vision de
transferencia tecnologica del proyecto: la arquitectura del sistema SIOT/Toltecayotl debe ser
abierta, agnóstica y maximizar compatibilidades en cada decision de diseno.

Esta decision captura ese mandato como principio rector de nivel arquitectonico.

## Decision

El sistema adopta el **Principio de Arquitectura Abierta y Viabilidad Comercial (PAVC)**
como criterio de diseno transversal, con las siguientes dimensiones mandatorias:

### 1. Auto-Descubrimiento Seguro y Agnostico

- **Protocolo primario:** mDNS/DNS-SD (RFC 6762/6763) via Avahi para descubrimiento en LAN,
  garantizando interoperabilidad con Linux, macOS, iOS, Android y Windows sin configuracion manual.
- **Protocolo secundario:** MQTT con topicos de registro (`$SYS/siot/nodes/+/presence`) como
  capa de descubrimiento sobre WAN o cuando mDNS no alcanza el segmento de red.
- **Seguridad:** Toda comunicacion inter-nodo usara TLS 1.3 minimo. El descubrimiento mDNS
  se limita a la red interna; los servicios expuestos al exterior requieren autenticacion explicita.
- **Tipos de servicio DNS-SD estandarizados** del proyecto:
  - `_siot-hub._tcp.local` — Nodo PC/Hub central
  - `_siot-edge._tcp.local` — Nodo Edge (Orange Pi y similares)
  - `_siot-sensor._tcp.local` — Sensores BLE/MQTT

### 2. Maximizar Compatibilidades (Open-First)

Toda decision de protocolo, formato o interfaz debe priorizar, en este orden:

1. **Estandar abierto IETF/ISO/W3C** (MQTT, CoAP, HTTP/REST, mDNS, TLS).
2. **Formato neutro** (JSON, CBOR para dispositivos restringidos, Protobuf si la latencia lo exige).
3. **Implementaciones de referencia permisivamente licenciadas** (MIT, Apache 2.0, BSD).
4. Nunca adoptar protocolos propietarios como requerimiento primario.

### 3. Arquitectura como Producto Comercialmente Viable

Todo componente del sistema debe diseñarse con consciencia de su potencial como:

- **Producto SaaS:** El Hub central puede desplegarse en nube (Azure IoT, AWS IoT Greengrass,
  GCP IoT Core) sin modificaciones al protocolo de nodos Edge. La abstraccion de transporte
  es obligatoria.
- **Producto On-Premise / Local-First:** Deployment completo en infraestructura propia
  (Docker Compose, Kubernetes) sin dependencia de nube. Documentado en DEC-0030.
- **Licenciamiento Dual:** El codigo generado tendra estructura que permita licenciamiento
  dual (open-source para investigacion / comercial para uso productivo).
- **Casos de Uso de Negocio documentados:** Cada modulo del sistema debe tener al menos
  un caso de uso comercial identificado en `05_tesis/casos_uso_negocio/`.

### 4. Criterio de Aceptacion para Nuevas Decisiones de Diseno

Antes de adoptar cualquier tecnologia, biblioteca o protocolo, se evaluara:

| Criterio | Pregunta |
|---|---|
| Apertura | ¿Es un estandar abierto o tiene implementaciones de referencia abiertas? |
| Compatibilidad | ¿Funciona en ARM (Orange Pi), x86 (PC) y la nube sin fork? |
| Seguridad | ¿Tiene soporte nativo de TLS/autenticacion? |
| Escalabilidad | ¿Escala de un nodo a cientos sin cambio de arquitectura? |
| Adopcion | ¿Tiene comunidad activa y traccion comercial verificable? |

## Consecuencias

### Inmediatas
- El servicio de auto-descubrimiento del Edge usara **mDNS + MQTT** como mecanismo dual.
- Los scripts de hardening conservaran `avahi-daemon` y `ModemManager` por ser estandar abierto
  y canal de redundancia WAN respectivamente.
- T-033 (Observabilidad) adoptara **Prometheus + OpenTelemetry** (estandar CNCF) en lugar
  de soluciones propietarias.

### Estructurales
- Se creara el directorio `05_tesis/casos_uso_negocio/` para documentar el potencial comercial
  de cada modulo (priorizando los de mayor densidad de valor: inferencia edge, resiliencia IoT,
  auto-descubrimiento seguro).
- Toda decision DEC futura que adopte una tecnologia debera incluir una seccion
  `## Viabilidad Comercial` con al menos un caso de uso identificado.

## Viabilidad Comercial de este Principio

La adopcion de arquitectura abierta es en si misma un multiplicador de valor:

| Segmento | Oportunidad |
|---|---|
| **Municipios** | Ciudades inteligentes con infraestructura heterogenea existente requieren exactamente esta interoperabilidad (ej. Pachuca, CDMX, Guadalajara) |
| **Industria 4.0** | Plantas con PLCs, sensores legacy y nuevos dispositivos IoT coexistiendo |
| **Salud** | Dispositivos medicos IoT (FHIR + MQTT) en entornos con conectividad intermitente |
| **AgriTech** | Sensores de campo con conectividad celular esporadica (ModemManager + MQTT) |
| **Retail / Logistica** | Inventario con BLE + mDNS sin configuracion manual de red |

## Registro de Auditoria

```
Instruccion Humana : evento interno no público (2026-05-21)
Step ID            : validación humana interna no pública
Sesion             : 2e3a1332-d176-485d-9f69-9f3afbab837a
Hash instruccion   : [auto-calculado por guardrails.py]
```

[LID]:  ruta local no pública 
[GOV]:  ruta local no pública 
[AUD]:  ruta local no pública

_Última actualización: `2026-06-01`._
