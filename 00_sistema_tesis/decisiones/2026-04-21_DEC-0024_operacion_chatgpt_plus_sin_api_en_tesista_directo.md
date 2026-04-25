<!-- SISTEMA_TESIS:PROTEGIDO -->

# DEC-0024 Operacion ChatGPT Plus sin API en Tesista Directo

- Fecha: 2026-04-21
- Estado: aceptada
- Alcance: operacion | gobernanza

## Contexto

El tesista requiere una forma legitima y trazable de aprovechar ChatGPT Plus en el flujo de trabajo de tesis sin convertir la cuenta personal en un conector programatico ni exponer credenciales en el repositorio soberano. El objetivo es usar la interfaz oficial de ChatGPT y su integracion operativa con OpenClaw para investigacion, redaccion, revision y planeacion, manteniendo la soberania humana y la separacion entre uso interactivo y automatizacion de API.

## Decision

1. ChatGPT Plus personal se autoriza como herramienta de apoyo para el trabajo de tesis y operacion diaria, siempre dentro de la interfaz oficial de ChatGPT web/app o como sesion web asistida supervisada por OpenClaw.
2. Queda prohibido construir un cliente OAuth propio para la cuenta personal, extraer tokens, automatizar login, hacer scraping de sesion o almacenar cookies/credenciales en el repositorio.
3. Las decisiones tecnicas u operativas derivadas de una sesion de ChatGPT se registran en el ledger y en la matriz de trazabilidad con su `VAL-STEP` correspondiente.
4. El uso de ChatGPT Plus no sustituye `DEC-0014` ni los mecanismos de validacion humana, auditabilidad y cierre trazable.
5. La capa publica sanitizada no debe contener artefactos de autenticacion, llaves, tokens, trazas de sesion ni exportes directos de ChatGPT/proveedor de IA no publicado.
6. Cuando OpenClaw use `chatgpt_plus_web_assisted`, la tarea debe declararlo de forma explicita y conservar su approval gate humano.

## Consecuencias

- Positivas: acceso practico a razonamiento avanzado, redaccion y revision sin complejidad de integracion API.
- Negativas: requiere disciplina manual para registrar decisiones y no ofrece automatizacion directa del flujo de autenticacion.
- Riesgo controlado: se mitiga al mantener el uso en la interfaz oficial, separar uso interactivo de automatizacion y reforzar el escaneo de secretos.

## Soporte de Validacion

- **Soporte principal:** [validación humana interna no pública]

## Referencias

- [DEC-0014](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md)
- [DEC-0015](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0015_protocolo_de_sanitización_para_exposición_pública.md)
- [manual_operacion_humana.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/manual_operacion_humana.md)

[LID]: ruta local no pública
[GOV]: ruta local no pública
[AUD]: ruta local no pública

_Última actualización: `2026-04-25`._
