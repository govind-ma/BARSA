# Barsa Dashboard Design System

The Barsa dashboard visual style follows a minimalist, developer-first aesthetic inspired by tools like GitHub, Linear, and Supabase.

---

## 1. Visual Philosophy & Principles

- **Zero Clutter:** No decorative gradients, glowing borders, or unnecessary animations.
- **High Information Density:** Clean, compact tables, monospaced hashes, and structured badges.
- **Accessible Contrast:** Meets WCAG 2.1 AA standards in both light and dark modes.
- **Predictable Focus & Navigation:** Fully keyboard navigable with prominent outline rings.

---

## 2. Color System & Design Tokens

Colors are defined using HSL variables in `src/index.css` and extended in `tailwind.config.js`:

| Token | Light Value | Dark Value | Purpose |
| :--- | :--- | :--- | :--- |
| `--background` | `hsl(210 20% 98%)` | `hsl(222 47% 8%)` | Page canvas background |
| `--foreground` | `hsl(222 47% 11%)` | `hsl(210 40% 98%)` | Primary typography |
| `--card` | `hsl(0 0% 100%)` | `hsl(222 47% 11%)` | Card surface container |
| `--border` | `hsl(214 32% 91%)` | `hsl(217 32% 18%)` | Structural borders & dividers |
| `--primary` | `hsl(217 91% 60%)` | `hsl(217 91% 60%)` | Interactive actions & brand blue |
| `--muted-foreground` | `hsl(215 16% 47%)` | `hsl(215 20% 65%)` | Secondary labels & metadata |
| `--destructive` | `hsl(0 84% 60%)` | `hsl(0 63% 31%)` | Error states & delete actions |

---

## 3. Core UI Primitives

1. **Button (`components/ui/Button.tsx`):**
   - Variants: `primary`, `secondary`, `outline`, `ghost`, `destructive`
   - Sizes: `sm`, `md`, `lg`, `icon`
   - Integrated loading spinner state and accessible focus rings.
2. **Card (`components/ui/Card.tsx`):**
   - Standardized `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, and `CardFooter` containers.
3. **Badge (`components/ui/Badge.tsx`):**
   - Semantic color tags: `default` (primary), `success` (green), `warning` (amber), `destructive` (red), `outline`.
4. **Modal / Dialog (`components/ui/Modal.tsx`):**
   - Accessible keyboard dismissal (`Escape` key), body scroll lock, backdrop click dismissal, and `role="dialog"`.
5. **EmptyState (`components/ui/EmptyState.tsx`):**
   - Consistent zero-state UI with action button when collections are empty.
