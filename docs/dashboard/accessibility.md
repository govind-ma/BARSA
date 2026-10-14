# Dashboard Accessibility Guide (a11y)

The Barsa Web Dashboard is engineered to comply with **WCAG 2.1 Level AA** accessibility standards.

---

## 1. Accessible Knowledge Graph Alternative

Per Section 18:
> *"The graph visualization must provide an accessible alternative list or table. Do not make important information accessible only by hovering over graph nodes."*

### Implementation:
- In `src/features/graph/GraphExplorerPage.tsx`, users can toggle between the interactive SVG canvas and the **Accessible Table View**:
  ```tsx
  <Button onClick={() => setViewMode('table')}>
    <TableIcon className="h-4 w-4 mr-1.5" />
    Accessible Table
  </Button>
  ```
- The Accessible Table renders a structured semantic `<table>` element with `<th scope="col">` headers and accessible text labels for all entity properties, allowing screen reader users and assistive technology tools to inspect all graph entities without mouse interaction.

---

## 2. Keyboard Navigation & Dialog Management

1. **Escape Key Dismissal:**
   - All modals (`components/ui/Modal.tsx`) attach a global `keydown` listener listening for `Escape` to close the dialog.
2. **Scroll Lock:**
   - Opening a dialog locks background scrolling (`document.body.style.overflow = 'hidden'`) and restores it upon unmounting.
3. **Focus Indicators:**
   - All buttons, inputs, and links include prominent focus rings:
     ```css
     focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
     ```
4. **Semantic HTML:**
   - Navigational links use semantic `<nav>` and `<aside>` elements with `aria-label="Main Navigation"`.

---

## 3. Visual Contrast & Color Invariance

- **No Color-Only State Indicators:**
  - Status badges combine distinct color backgrounds with explicit text labels (`Active`, `Running`, `Blocked`, `Verified`, `Refuted`).
  - Icons accompany text labels (e.g. checkmark for verified, cross for refuted).
- **Contrast Ratios:**
  - Neutral foreground text meets a minimum contrast ratio of **4.5:1** against card and background surfaces in both light and dark themes.
