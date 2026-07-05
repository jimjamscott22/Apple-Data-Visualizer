# UI Design Review

A readability and style review of the desktop UI, based on rendering every page
offscreen with realistic seeded data, reading `app/theme.py` and all page code,
and validating the chart palette against the dark chart surface with a
color-vision/contrast checker.

Overall direction is strong: the dark navy palette, rounded cards, sidebar
shell, and consistent card grammar already read as a real product. Findings
below are ranked by how much they would improve readability.

---

## High impact — fix these first

### 1. Every label paints its own dark box

The universal rule in `app/theme.py`:

```css
QWidget { background-color: #09111f; ... }
```

applies to `QLabel` too, so every piece of text draws a rectangle darker than
the card behind it — the striped look visible on every card, header, and
legend. This is the single biggest visual defect in the app.

**Fix:** make labels transparent (`QLabel { background: transparent; }`) or
scope background colors to container widgets only.

### 2. Range buttons have no selected state

`RangeButton` has no rules in the stylesheet, so the 7/30/90-day (and Trends
30/90/365) buttons all render as identical filled primary buttons. The active
range is invisible, and the buttons compete with the real primary action
("Import Apple Health Export").

**Fix:** style them as a segmented control — quiet/outlined by default
(`QPushButton#RangeButton`), filled accent only when `:checked`.

### 3. Overview metric cards stretch to fill the viewport

With only cards and two banners on the page, the metrics row absorbs all
vertical space, leaving large voids inside each card. Sleep and Heart avoid
this only because their charts consume the space.

**Fix:** cap the metric-card row height (or place the layout stretch before
the cards rather than after).

### 4. Pages don't scroll — content gets crushed instead

No page uses a `QScrollArea`. At 1440×920 the Sleep page squeezes the
"Nightly sessions" table to a single visible row; smaller laptops will be
worse.

**Fix:** wrap each page in a transparent `QScrollArea` and give tables a
sensible minimum height.

### 5. The bedtime axis is misleading

On "Bedtime & wake-time trend," bedtime is plotted in hours-past-noon
(23:00 → 11) while wake time is plotted in clock hours (06:21 → 6.35), on one
axis labeled "Clock hour." A 23:00 bedtime renders as a flat line at "11,"
which reads as 11 AM.

**Fix:** format the ticks as real HH:MM strings (pyqtgraph supports custom
tick labels), or split into two stacked mini-panels sharing the x-axis.

### 6. Legend markers carry no color

"● Bedtime | ● Wake time" (Sleep) and "● Daily avg | ● 7-day rolling avg"
(Heart) render entirely gray — series identity is color-alone in the plot and
absent from the legend.

**Fix:** QLabel supports rich text; color the dots with spans matching the
series colors.

---

## Medium impact — polish

### 7. Chart x-axes show indices, not dates

"0…30, Night (oldest → newest)" forces mental math. Show date labels at
intervals (e.g. every 5th night) via custom tick strings.

### 8. Dev-facing copy ships in the UI

- "MVP FOUNDATION" eyebrow on every page header.
- Startup description: "The application shell, database bootstrap, and page
  boundaries are now implemented."
- The permanent "Dashboard foundations are ready / …next implementation
  milestones" card on Overview, shown even when data exists.

These read like a changelog. The eyebrow is prime real estate for data
freshness (e.g. "Data through Jul 4").

### 9. Table formatting

- `stretchLastSection` inflates the last column (Consistency, Samples) to
  absurd width.
- Numeric columns are left-aligned; right-align them so digits line up.
- Enable alternating row colors (`setAlternatingRowColors` + QSS color).
- Use tabular/monospaced numerals in value cells to stop column wiggle.

### 10. Chart interaction defaults

pyqtgraph leaves wheel-zoom and drag-pan enabled, so scrolling can
accidentally fling a chart into empty space with no way back but restart.
Disable mouse interaction on these plots (or add an auto-range reset). Enable
global antialiasing (`pg.setConfigOptions(antialias=True)`) — lines currently
render slightly jagged. Longer-term: a hover crosshair/tooltip with exact
date + value.

### 11. Series orange is slightly too bright for the dark surface

Validated `#1e6bff` / `#ff6b35` against chart surface `#0f1b31`: the blue
passes all checks and the pair has excellent colorblind separation, but
`#ff6b35` sits just above the recommended lightness band for dark surfaces.

**Fix:** swap to `#f2600c` (passes lightness band, chroma floor, CVD
separation ΔE≈130, contrast ≥3:1) in `app/charts`. Visually near-identical.

---

## Lower impact — nice to have

- **Header actions:** the two stacked buttons have different widths with
  ragged edges; give them equal width. "Open Data Folder" opens a message box
  rather than the folder — the label over-promises.
- **Unlabeled average line:** the dashed orange line on the sleep-duration
  chart is never explained; add it to the legend or label it directly
  ("30-day avg").
- **Consistency "80" is unitless:** display as "80 / 100" so the scale is
  obvious.
- **Empty-state Overview stacks two redundant banners** ("No imports yet" +
  "Dashboard foundations are ready") — one strong empty state with the import
  call-to-action is better.
- **Font stack:** `font-family: "Segoe UI"` is Windows-only; on Linux it
  silently falls back. Use a stack: `"Segoe UI", "Inter", "Ubuntu", sans-serif`.
- **Sidebar:** works well; per-item icons and a subtle left accent bar on the
  selected item would sharpen it. The placeholder pages (Activity, Imports,
  Settings) are appropriately honest, though the Imports placeholder is ironic
  since `import_history` already holds the data that page needs.

---

## Suggested implementation order

1. Items **1–3** are pure stylesheet/layout changes with the biggest payoff
   per line.
2. Items **4–7** are structural chart/page work.
3. The rest is cleanup.

Items 1–6 together would transform how finished the app feels. A screenshot
harness that renders every page offscreen with seeded data (used to produce
this review) is a useful before/after tool:
`QT_QPA_PLATFORM=offscreen` + `QWidget.grab()` per navigation row.
