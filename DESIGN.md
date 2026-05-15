# Tesis IoT - Estándares de Diseño y UI/UX (DESIGN.md)

Este documento establece los principios fundacionales de diseño gráfico y experiencia de usuario (UX/UI) para la documentación, dashboards y reportes generados dentro del Sistema Operativo de Tesis.

## 1. Filosofía y Estética
Inspirados en publicaciones académico-tecnológicas como **Distill.pub**, el diseño prioriza:
- **Claridad Teórica:** Menos ruido, más enfoque en los datos, diagramas y narrativa.
- **Rigor y Modernidad:** Estética científica, pero usando estándares web modernos (HTML5 semántico, layouts fluidos).
- **Legibilidad Sostenida:** Optimizado para la lectura profunda (deep reading) mediante un uso extenso de espacios en blanco y anchos de línea controlados.

## 2. Tipografía (Google Fonts)
La jerarquía tipográfica busca crear un contraste elegante entre los elementos estructurales y la narrativa científica.

- **Cabeceras (Headings):** `Inter`, `Outfit` o `Roboto`. Tipografía *sans-serif* geométrica o neo-grotesca, limpia y con peso estructural alto (Bold 700 o ExtraBold 800) para delimitar claramente las secciones.
- **Cuerpo (Body Text):** `Merriweather`, `Lora` o serifas equivalentes legibles. La tipografía *serif* facilita la retención en lecturas largas, aportando un tono académico y formal.
- **Código y Datos (Monospace):** `Fira Code` o `JetBrains Mono`. Fundamental para bloques de código JSON, hashes SHA-256 o referencias de commits.

### Métrica Tipográfica:
- Tamaño de fuente base (cuerpo): `1.125rem` (18px) a `1.25rem` (20px).
- Ancho de línea máximo: `65-75 caracteres` (ideal para evitar fatiga ocular).
- Interlineado (Line-height): `1.7` o `1.8` para el cuerpo.

## 3. Paleta de Colores
Uso de colores orientados al contenido, no a la decoración.

- **Fondo:** Blanco hueso (`#fafafa`) para reducir la fatiga ocular en modo claro.
- **Texto Principal:** Gris muy oscuro (`#333333` o `#1a1a1a`), nunca negro puro (`#000000`).
- **Acentos (Teal/Cyan):** Utilizados estrictamente para interactividad (enlaces) y elementos de gobierno del sistema.
  - Primario: `#008080` (Teal)
  - Secundario: `#00BCD4` (Cyan)
- **Bloques Auxiliares (Notas/Admonitions):** Fondos sutiles (ej. `#f4f4f4` para notas genéricas) con un borde lateral fino. No abusar de colores saturados (rojos o amarillos brillantes) salvo en alertas críticas de seguridad/soberanía.

## 4. Disposición y Grids
- **Layout de Columna Central:** El contenido narrativo debe estar centrado con márgenes amplios (amplio `padding` lateral).
- **Marginalia:** Las figuras, citas o notas al margen (*asides*) pueden romper la cuadrícula y extenderse hacia los márgenes laterales (estilo *outset* o *breakout*), común en Distill.
- **Componentes Embebidos:** Tablas y diagramas Mermaid pueden usar anchos de columna mayores (`max-width: 100%` o superior si el contenedor lo permite) para evitar compresión.

## 5. Diseño de Diagramas (Mermaid y Gráficos)
Los diagramas generados no deben parecer "por defecto".
- **Esquema de Colores:** Los nodos en Mermaid deben evitar colores chillones. Usar fondos transparentes o pastel (`#f9f9f9`), bordes finos (`1px solid #ccc`), y tipografía sans-serif.
- **Direccionalidad:** Los diagramas de flujo (Flowcharts) deben ser lógicos y minimizar el cruce de líneas. Usar `graph TD` (Top-Down) para jerarquías y `graph LR` (Left-Right) para procesos secuenciales.
- **Sombra y Efectos:** Efectos sutiles como `glassmorphism` o sombras difuminadas (`box-shadow: 0 4px 12px rgba(0,0,0,0.05)`) para separar visualmente los diagramas del texto.

## 6. Componentes MkDocs y Material
Cuando se configure el theme *Material for MkDocs*:
- Ocultar elementos redundantes de navegación si interrumpen la lectura.
- Usar _Content Tabs_ (Pestañas) en lugar de listas interminables cuando se comparen métricas (ej. Edge NPU vs PC CUDA).
- Usar cuadros colapsables (`details`) para volcar hashes largos, JSONs de configuración cruda o logs técnicos que ensucian la narrativa visual pero que son necesarios para la verificabilidad.

## 7. Responsividad y Accesibilidad
- Todo el contenido debe ser navegable en móvil (tablas con scroll horizontal).
- Contraste WCAG 2.1 AA mínimo garantizado en los colores de texto y enlaces.
- Todos los diagramas deben mantener contraste incluso en el esquema *slate* (modo oscuro).

_Última actualización: `2026-05-15`._
