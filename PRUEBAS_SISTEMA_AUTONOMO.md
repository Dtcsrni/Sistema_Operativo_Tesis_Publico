# 🧪 GUÍA DE PRUEBAS - Sistema Autónomo de Telegram Bot

## 📋 Pre-requisitos

- [ ] `07_scripts/start_backends_auto.py` existe
- [ ] Orange Pi (192.168.1.124) ping-able desde esta PC
- [ ] Llave SSH para Orange Pi disponible
- [ ] LlamaCPP instalado localmente
- [ ] Modelo mistral-nemo-12b.gguf disponible
- [ ] Bot Telegram token configurado

---

## 🧪 Test 1: Sistema Autónomo - Ambos Backends Caídos

### Preparación
```bash
# 1. Detener ambos backends manualmente
#    - Cerrar LlamaCPP si está corriendo
#    - SSH a Orange Pi y: systemctl stop ollama

# 2. Ejecutar bot
cd  ruta local no pública 
python -m runtime.openclaw
```

### Ejecución
```
Enviar en Telegram: "Hola"
```

### Resultado Esperado
1. **Mensaje inmediato:** `🔧 Verificando backends de inferencia...`
2. **Después ~10-30 seg:** `✅ Backends iniciados: 🌐 Edge, 💻 Desktop`
3. **Respuesta del bot:** Respuesta normal con información

### Evidencia
- [ ] Captura de pantalla: Mensaje "Verificando backends"
- [ ] Captura de pantalla: Mensaje "Backends iniciados"
- [ ] Captura de pantalla: Respuesta del bot

---

## 🧪 Test 2: Sistema Autónomo - Backends Ya Funcionan

### Preparación
```bash
# 1. Iniciar ambos backends manualmente (si no están)
# 2. Verificar que responden: /salud
```

### Ejecución
```
Enviar en Telegram: "¿Cuál es la capital de México?"
```

### Resultado Esperado
1. **Sin mensaje de verificación** (sin delay perceptible)
2. **Respuesta directa del bot** (~2-5 segundos)

### Evidencia
- [ ] Captura de pantalla: Respuesta inmediata sin "Verificando"

---

## 🧪 Test 3: Comando de Diagnóstico `/salud`

### Preparación
- Ambos backends funcionando

### Ejecución
```
Enviar en Telegram: /salud
```

### Resultado Esperado
```
🏥 Diagnóstico de Salud del Sistema

✅ 🌐 Edge (Ollama):      OK (Xms)
✅ 💻 Desktop Runtime:     OK (Xms)

📊 Estadísticas:
• Servidor: ✅ OK
• Base de datos: ✅ OK
• Telegram: ✅ OK
```

### Evidencia
- [ ] Captura de pantalla del diagnóstico completo

---

## 🧪 Test 4: Solo Edge Caído

### Preparación
```bash
# 1. SSH a Orange Pi y: systemctl stop ollama
# 2. Verificar LlamaCPP funcionando en Desktop
```

### Ejecución
```
Enviar en Telegram: "Hola"
```

### Resultado Esperado
1. Bot detecta Edge caído
2. Bot intenta iniciar Edge vía SSH
3. Bot envía: `✅ Backends iniciados: 🌐 Edge`
4. Bot responde la pregunta

### Evidencia
- [ ] Captura: "Backends iniciados: 🌐 Edge"
- [ ] Orange Pi Ollama respondiendo después

---

## 🧪 Test 5: Solo Desktop Caído

### Preparación
```bash
# 1. Cerrar LlamaCPP en puerto 21434
# 2. Verificar Orange Pi Ollama funcionando
```

### Ejecución
```
Enviar en Telegram: "Explica la fotosíntesis"
```

### Resultado Esperado
1. Bot detecta Desktop caído
2. Bot intenta iniciar LlamaCPP
3. Bot envía: `✅ Backends iniciados: 💻 Desktop`
4. Bot responde (posiblemente con Edge si hay timeout)

### Evidencia
- [ ] Captura: "Backends iniciados: 💻 Desktop"

---

## 🧪 Test 6: Ambos Backends Caídos - Autoarranque Falla

### Preparación
```bash
# 1. Detener Orange Pi completamente (apagar si es posible)
# 2. No tener LlamaCPP instalado
# 3. Esperar a que el bot intente autoarranque
```

### Ejecución
```
Enviar en Telegram: "Hola"
```

### Resultado Esperado
1. `🔧 Verificando backends de inferencia...`
2. (Esperar ~30 segundos)
3. Bot envía: `⚠️ No se pudieron iniciar backends...` + instrucciones
4. Bot NO congela / NO crashea

### Evidencia
- [ ] Captura: Mensaje de error graceful
- [ ] Bot sigue respondiendo después

---

## 🧪 Test 7: Diagnóstico Manual Script

### Ejecución
```bash
cd  ruta local no pública 
python 07_scripts/diagnose_backends.py
```

### Resultado Esperado
```
======================================================================
🔧 DIAGNÓSTICO DE BACKENDS - OpenClaw Telegram Bot
======================================================================

1️⃣  CONFIGURACIÓN DE BACKENDS
  🌐 Edge (Ollama):            http://192.168.1.124:11434
  💻 Desktop Runtime:          http://127.0.0.1:21434

2️⃣  DISPONIBILIDAD DE ENDPOINTS
  edge                 → ✅ OK (Xms)
  desktop_runtime      → ✅ OK (Xms)

...
```

### Evidencia
- [ ] Captura de consola completa

---

## 📊 Matriz de Validación

| Test | Descripción | Esperado | Resultado | ✅/❌ |
|------|-------------|----------|-----------|-------|
| 1 | Ambos caídos | Auto-inicia | | |
| 2 | Ambos funcionan | Sin delay | | |
| 3 | `/salud` | Diagnóstico | | |
| 4 | Solo Edge caído | Inicia Edge | | |
| 5 | Solo Desktop caído | Inicia Desktop | | |
| 6 | Ambos + fallo | Error graceful | | |
| 7 | Script diagnóstico | Salida correcta | | |

---

## 🎯 Criterios de Aceptación

✅ **PASS** si:
- [x] Test 1: Auto-inicia ambos backends sin error
- [x] Test 2: Responde sin delay cuando backends ok
- [x] Test 3: `/salud` muestra diagnóstico correcto
- [x] Test 4: Inicia solo Edge cuando está caído
- [x] Test 5: Inicia solo Desktop cuando está caído
- [x] Test 6: No crashea si falla el auto-arranque
- [x] Test 7: Script de diagnóstico funciona

❌ **FAIL** si:
- Algún test no pasa
- Bot se congela/crashea
- Mensajes no informativos

---

## 📝 Notas Adicionales

1. **Latencia esperada:**
   - Backends ok: 0-2 segundos (sin verificación)
   - Auto-arranque Edge: 5-15 segundos total
   - Auto-arranque Desktop: 15-40 segundos total

2. **Robustez:**
   - Si SSH falla, el script lo intenta una sola vez (gracefully)
   - Si LlamaCPP no se encuentra, lo reporta pero no crashea
   - Múltiples usuarios pueden disparar auto-arranque simultáneamente (thread-safe)

3. **Logs:**
   - Ver `telegram_audit.log` para auditoría de mensajes
   - Ver consola del bot para debug detallado

---

## 🔗 Documentación Relacionada

- `00_sistema_tesis/bitacora/SISTEMA_AUTONOMO_BACKENDS_2026-05-05.md` - Spec técnica
- `RESUMEN_SISTEMA_AUTONOMO.md` - Resumen ejecutivo
- `07_scripts/start_backends_auto.py` - Script de auto-arranque
- `07_scripts/diagnose_backends.py` - Script de diagnóstico

---

**Status:** ✅ Listo para validación

*Ejecutar estos tests y confirmar todos los criterios de aceptación antes de marcar como completado.*

_Última actualización: `2026-05-15`._
