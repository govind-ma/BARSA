# Barsa Dashboard Design System: Ice & Lava

"Ice and Lava": A bright frosted-white interface (ice) with molten yellow-orange-red energy (lava). Calm and precise like glacier ice, with a hot volcanic spark where the user should act.

---

## 1. Visual Philosophy & Principles

- **90/10 Balance:** 90% of every screen is composed of calm, crystalline ice neutrals, glass surfaces, and steel accents. Lava is reserved strictly for high-salience moments (primary buttons, live indicators, recommendations, blockers).
- **Dual-Themed:**
  - **ICE (Default Light Mode):** High clarity frost white canvas, pale blue ice tints, crisp steel typography, and frosted glass cards.
  - **OBSIDIAN (Dark Mode):** Volcanic black with warm ash undertones, dark glass surfaces, and warm bottom edge glow.
- **Accessible Contrast:** Meets WCAG 2.1 AA standards in both light and dark modes with high contrast ratios.
- **Predictable Focus & Navigation:** Fully keyboard navigable with outline rings in `steel-500` (Ice) or `lava-yellow` (Obsidian).

---

## 2. Color System & Design Tokens

Colors are defined using CSS custom properties in `src/index.css` and extended in `tailwind.config.js`:

| Token | Ice Mode (Light) | Obsidian Mode (Dark) | Purpose |
| :--- | :--- | :--- | :--- |
| `--bg-base` | `#F3F7FA` | `#0C0A0B` | Page canvas background |
| `--bg-surface` | `#FFFFFF` | `#151113` | Card & surface container |
| `--bg-elevated` | `#E9F0F6` | `#1E1819` | Elevated popovers, drawers |
| `--ice-100` | `#E3EDF5` | `rgba(255,255,255,0.06)` | Pill backgrounds, subtle hover |
| `--ice-200` | `#CFE0EC` | `rgba(255,255,255,0.12)` | Secondary hover |
| `--ice-300` | `#B3CDE0` | `rgba(255,255,255,0.20)` | Subtle divider line |
| `--steel-500`| `#6F8FA8` | `#6F7A83` | Inactive icons, secondary nodes |
| `--steel-700`| `#3E5A72` | `#A9B4BD` | Primary typography, borders |
| `--lava-yellow` | `#FFC93C` | `#FFC93C` | Decision nodes, spark |
| `--lava-orange` | `#FF7A1A` | `#FF7A1A` | Live dot, agents, primary spark |
| `--lava-red` | `#E5301F` | `#E5301F` | Blockers, issue nodes, critical |
| `--magma` | `linear-gradient(135deg, #FFC93C, #FF7A1A, #E5301F)` | Brand primary interactive gradient |

---

## 3. Core UI Primitives

1. **Primary Button:** Magma gradient with heat-shimmer sweep and lava glow.
2. **Secondary Button:** White glass fill with 1px steel border and cool glow on hover.
3. **Card:** Glass container with inset top highlight and subtle cool shadow in Ice; warm bottom edge in Obsidian.
4. **Recommended Task Card:** Molten rotating border with "Recommended" ribbon.
5. **Next Action Callout:** Elevated container with prominent `--magma` left border.
6. **Live Indicator:** Pulsing lava-orange dot with "Live" label; muted gray when offline.
