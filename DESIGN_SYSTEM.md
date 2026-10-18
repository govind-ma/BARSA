# BARSA Design System: Ice & Lava

"Ice and Lava": A bright frosted-white interface (ice) with molten yellow-orange-red energy (lava). Calm and precise like glacier ice, with a hot volcanic spark where the user should act. Premium, clean, techy, and distinctly differentiated from generic AI tools.

---

## 1. Visual Philosophy & Rationale

- **90/10 Balance:** 90% of every screen is composed of calm, crystalline ice neutrals, glass surfaces, and steel accents. Lava is reserved strictly for high-salience moments:
  1. Primary interactive buttons
  2. Live status indicators
  3. Recommended tasks and knowledge graph nodes
  4. Key metrics and active navigation indicators
  5. Blocker and issue states
  *Lava is never used as large full-bleed backgrounds.*
- **Dual-Themed:**
  - **ICE (Default Light Mode):** High clarity frost white canvas, pale blue ice tints, crisp steel typography, and frosted glass cards.
  - **OBSIDIAN (Dark Mode):** Volcanic black with warm ash undertones, dark glass surfaces, and warm bottom edge glow.
- **Tactile Transitions:** 150–300ms bezier curves (`cubic-bezier(0.22, 1, 0.36, 1)`) animating only `transform` and `opacity`.

---

## 2. Design Tokens

### Theme 1: ICE (Default, Light)
```css
--bg-base: #F3F7FA;         /* Frost white canvas */
--bg-surface: #FFFFFF;      /* Clean solid surface */
--bg-elevated: #E9F0F6;     /* Elevated drawer / popover background */

--ice-100: #E3EDF5;         /* Very pale blue-tinted fill */
--ice-200: #CFE0EC;         /* Soft hover highlight */
--ice-300: #B3CDE0;         /* The maximum blue tint; pale divider accent */

--steel-500: #6F8FA8;       /* Subtle steel icons, secondary nodes, inactive labels */
--steel-700: #3E5A72;       /* Strong steel typography, borders, dark accents */

--text-primary: #0D1A24;    /* Deep obsidian-navy typography */
--text-secondary: #4A5B69;  /* Secondary descriptive text */
--text-muted: #7D8D99;      /* Metadata, timestamps, shortcuts */

--border-subtle: rgba(110, 150, 180, 0.22);
--border-strong: rgba(110, 150, 180, 0.40);
```

### Theme 2: OBSIDIAN (Dark Mode)
```css
--bg-base: #0C0A0B;         /* Warm volcanic black canvas */
--bg-surface: #151113;      /* Deep volcanic surface */
--bg-elevated: #1E1819;     /* Elevated popovers & drawers */

--text-primary: #F4F8FB;    /* Ice-white typography */
--text-secondary: #A9B4BD;  /* Soft ash typography */
--text-muted: #6F7A83;      /* Muted metadata */

--border-subtle: rgba(255, 255, 255, 0.08);
--border-strong: rgba(255, 255, 255, 0.16);
```

### Lava & Magma Tokens (Both Themes)
```css
--lava-yellow: #FFC93C;     /* High spark accent, decisions */
--lava-orange: #FF7A1A;     /* Primary brand spark, live dot, agents */
--lava-red: #E5301F;        /* Blocker indicator, critical issues */
--lava-deep: #A81414;       /* Error states, deep shadows */

--magma: linear-gradient(135deg, #FFC93C 0%, #FF7A1A 45%, #E5301F 100%);
--lava-glow: 0 0 28px rgba(255, 122, 26, 0.35);
```

---

## 3. Typography

- **Headings:** `Space Grotesk`, font-weight 600.
- **Body:** `Inter`, sans-serif.
- **Codes, Hashes, IDs, Tags & Metrics:** `JetBrains Mono`, monospace.
- **Micro-Labels:** 11–12px uppercase, tracking `0.08em`, in `--text-muted`.

---

## 4. Components & Interactive Patterns

1. **Primary Button:**
   - Background: `--magma` gradient.
   - Text: High-contrast volcanic black `#0C0A0B` (or white with text-shadow), 600 font weight.
   - Border radius: 8px.
   - Hover: Lava glow `0 0 28px rgba(255,122,26,0.35)` + slow heat-shimmer sweep.
   - Active: `scale(0.97)`.
2. **Secondary Button:**
   - Background: White glass fill `rgba(255, 255, 255, 0.8)` (dark: `rgba(255, 255, 255, 0.06)`).
   - Border: 1px steel border (`--steel-500` at 30%).
   - Hover: `ice-200` fill + soft cool glow.
3. **Live Indicator:**
   - Pulsing lava-orange dot (`#FF7A1A`) with label "Live". Offline state is a muted gray dot.
4. **Active Sidebar Item:**
   - Magma vertical pill bar (`bg-gradient-to-b from-[#FFC93C] via-[#FF7A1A] to-[#E5301F]`) + `ice-100` filled tile.
   - Inactive icons: `--steel-500`.
5. **Chips & Filter Pills:**
   - Default: `ice-100` fill with `steel-700` text.
   - Active: White background with a sliding magma underline (`layoutId="pillUnderline"`).
6. **Recommended Task Card (Molten Border):**
   - Signature animated border: slowly rotating conic-gradient (yellow, orange, red) 1.5px border with a "Recommended" magma ribbon.
7. **Next Action Callout:**
   - Left border in `--magma`, elevated card container, slightly larger font.
8. **Glass Card Container:**
   - Light: `rgba(255, 255, 255, 0.72)` + `backdrop-blur(14px)` + 1px `--border-subtle` + inset top highlight `rgba(255,255,255,0.9)` + soft cool shadow.
   - Dark: Dark glass with warm bottom-edge glow.

---

## 5. Knowledge Graph Aesthetics

- **Canvas:** Ice-themed dotted grid in light mode; ash grid in Obsidian mode.
- **Node Semantics:**
  - **Task:** `steel-500` circle with white inner ring.
  - **Decision (ADR):** `lava-yellow` hexagon.
  - **Capability:** `ice-300` rounded square with steel border.
  - **Agent:** `lava-orange` diamond.
  - **Issue:** `lava-red` circle with soft red pulse.
  - **Recommended Node:** Magma gradient with pulsing glow ring and readiness score badge.
- **Edge Semantics:**
  - **DEPENDS_ON:** Solid steel line (40% opacity).
  - **BLOCKED_BY:** Dashed `lava-red` line.
  - **REQUIRES:** Dotted steel line.
- **Interactions:**
  - Node hover: Direct neighbors stay 100% bright, non-connected nodes dim to 25%.
  - "Run FalkorDB Re-rank": Magma beam sweeps across top of the graph pane; top task ignites with a 600ms glow.

---

## 6. Delight & Animations

- **Ember Particles:** A subtle drift of tiny orange sparks in empty states and the graph hero area.
- **Success Burst:** Combined crystalline shard burst with ember spark particles on checkpoint resume and handover copy.
- **Toasts:** Frosted white glass with accent left border (lava for success, steel for info, deep red for errors).
