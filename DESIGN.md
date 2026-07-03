# Design

> v-rag admin console visual system. Seed version, derived from PRODUCT.md (Linear-like, restrained, dual-theme). Refine via `/impeccable document` once frontend code exists.

## Color Strategy
Restrained: tinted neutrals carry the surface, one accent at 10% or less. Linear-line quietness. Color is information (state, focus, the one accent), never decoration.

## Theme
Dual theme (light + dark), both first-class. Physical scene: engineers switch between a bright shared office by day and a dim home desk by night, scanning dense agent traces and long conversations on a 27 inch monitor for extended stretches. Low fatigue and high legibility win over drama. Default follows `prefers-color-scheme`, with a manual toggle.

## Palette (OKLCH; neutrals tinted toward the accent hue; never #000 or #fff)

Light:
- bg: `oklch(0.99 0.005 250)`
- surface: `oklch(0.975 0.006 250)`
- border: `oklch(0.92 0.008 250)`
- text: `oklch(0.32 0.02 255)` (off-black)
- muted: `oklch(0.55 0.015 255)`
- accent: `oklch(0.62 0.14 235)` (a deliberate cold blue-teal, not AI violet)

Dark:
- bg: `oklch(0.165 0.012 255)`
- surface: `oklch(0.205 0.012 255)`
- border: `oklch(0.27 0.015 255)`
- text: `oklch(0.94 0.006 250)`
- muted: `oklch(0.66 0.012 255)`
- accent: `oklch(0.70 0.13 235)`

Status colors used sparingly, only where state is real: success `oklch(0.70 0.15 155)`, warn `oklch(0.78 0.14 75)`, danger `oklch(0.65 0.18 25)`.

## Typography
- Sans: Geist (display and body). Mono: Geist Mono (trace, JSON, ids, all numbers).
- Scale ratio 1.25 or more between steps. Body 14 to 15px, line length 65 to 75ch.
- Hierarchy via weight and scale, not color tricks or gradient text.

## Components (shadcn/ui, customized, never default state)
- Radii: one system. Surfaces 10px, inputs 8px, toggles and tags full pill. Never mix.
- Shadows: tinted to bg hue, subtle. No pure-black drops.
- Bans: no side-stripe borders, no gradient text, no decorative glassmorphism, no hero-metric template, no identical card grids.

## Layout
- App shell: persistent left rail (icon plus label nav), no heavy top bar. Generous content max-width, real breathing room.
- Spacing rhythm varies (not uniform padding). Cards used only where elevation is meaningful; nested cards always wrong.
- Density: moderate. Trace and data views denser; config views airier.

## Motion
Restrained. Ease-out-quart / quint / expo only. Motion only for: state change, focus guidance, feedback. No ambient loops, no parallax for show. Honors `prefers-reduced-motion`.

## Iconography
One family: Phosphor (fallback Tabler). strokeWidth standardized at 1.5. No hand-rolled SVG paths, no emoji.

## Data and Density
Numbers in mono. Trace and JSON in Geist Mono on surface-tinted bg. Dense tables use hairline rows, never heavy top-and-bottom borders on every row.
