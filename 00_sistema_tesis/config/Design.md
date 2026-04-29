# Sistema de Diseño: Tesis OS Wiki

Este documento define los estándares estéticos, estructurales y de interacción para la Wiki del Sistema Operativo de Tesis. Se basa en principios de diseño moderno, legibilidad académica y soberanía humana.

## 1. Identidad Visual

### Paleta de Colores (Curated Harmonious Palette)
- **Primary (Teal/Emerald):** `#0f766e` (Deep Teal) - Representa estabilidad y profundidad.
- **Secondary (Slate):** `#1e293b` (Deep Slate) - Color base para texto y estructura.
- **Accent (Cyan/Indigo):** `#06b6d4` / `#6366f1` - Para interactividad y resaltados.
- **Background (Soft Bone):** `#f8fafc` (Light Slate 50) - Fondo limpio y descansado.
- **Surface (Glassmorphism):** `rgba(255, 255, 255, 0.7)` con `backdrop-filter: blur(12px)`.

### Tipografía (Modern & Premium)
- **Cuerpo:** `Inter`, `system-ui`, `sans-serif` - Para máxima legibilidad en pantallas.
- **Títulos:** `Outfit` o `Roboto Slab` - Para un toque académico sofisticado.
- **Monoespaciado:** `Fira Code` o `JetBrains Mono` - Para hashes, rutas y código.

## 2. Principios de Interacción

- **Micro-animaciones:** Transiciones suaves de 200ms en hovers y cambios de página.
- **Feedback Visual:** Los enlaces deben tener efectos de subrayado dinámico.
- **Responsividad:** Layout fluido que se adapte desde móviles (320px) hasta pantallas ultra-wide.

## 3. Estructura de Navegación

- **Sidebar Persistente:** Acceso rápido a todas las secciones principales (Sistema, Gobernanza, Bitácoras, etc.).
- **Breadcrumbs:** Indicador claro de la ubicación actual dentro de la jerarquía.
- **Indicadores de Estado:** Badges dinámicos para "Verificado", "Parcial" o "Ausente".

## 4. Estándares Técnicos (Guardrails)

- **Vanilla CSS:** Sin frameworks externos pesados, priorizando el rendimiento.
- **Accesibilidad (A11y):** Contrastes adecuados (WCAG AA), etiquetas semánticas y navegación por teclado.
- **Optimización:** Carga asíncrona de fuentes y minimalismo en assets pesados.

## 5. Visual Excellence Checklist

- [ ] ¿Usa degradados sutiles en lugar de colores planos?
- [ ] ¿Los bordes tienen radios suaves (12px - 16px)?
- [ ] ¿La tipografía tiene jerarquía clara (H1, H2, H3)?
- [ ] ¿El diseño se siente "vivo" al interactuar con él?

_Última actualización: `2026-04-29`._
