---
name: pbi-report-visuals
description: Design and create Power BI report pages and visuals (PBIR visual.json) - layout grid, visual selection, IBCS-style variance and status colouring, copy-ready visual templates, and the SC brand theme (SC palette, SC Prosper Sans font). Includes P&L-style finance pages; treasury and project / capacity page catalogues live in their domain skills. Use when the user asks to create visualizations, pages, dashboards or to style the report.
---

# Report pages & visuals (finance & banking)

## Workflow
1. **Understand the questions.** Each page answers one question, for example "Are we on budget?" or "Is credit quality deteriorating?". List the audience and the decisions they make.
2. **Check the model.** Read the measures and columns that exist. If a measure the page needs is missing, add it first with the `pbi-dax-measures` skill. **Never bind raw numeric columns.**
3. **Propose the page plan:**
   - page name
   - an ASCII layout sketch
   - each visual: type, the fields in each role, and why that visual
   - slicers

   Use `assets/page-layouts.md` for coordinates and `references/finance-visual-guide.md` for visual choice. Wait for approval.
4. **Write PBIR:**
   - Create the page folder and `page.json`, and add the page to `pages.json`.
   - Create one folder and `visual.json` per visual from `references/visual-templates.md`.
   - Copy `$schema` URLs from existing Desktop-generated files.
5. **Validate** with `pbip-format/scripts/validate_pbip.py`.
6. **Hand off the theme:** tell the user to import `assets/sc-theme.json` (View → Themes → Browse for themes) the first time, and to reopen the report. The brand font **SC Prosper Sans** must be installed on each viewer's machine. Where it isn't, Power BI falls back to Segoe UI (the theme sets a font stack).

## Design rules
- **Canvas:** use the size of the existing pages. Desktop's default is 1920 × 1080, so scale the 1280 × 720 grid in `assets/page-layouts.md` by 1.5. Margins are 16 px and gaps 12 px at 1280 width. **Max 8 visuals per page**, including the KPI cards.
- **Reading order:** top-left most important. KPI row first, then the trend or bridge, then the detail table.
- Every number needs context: compare it with budget, prior year or a target. A bare total isn't enough.
- **Brand palette (base):** Prosper Blue `#020B43` · SC Blue `#0473EA` · SC Green `#38D200` · SC Grey `#525355`. Tints for extra series: `#9AC7F7`, `#4E547B`, `#A8A9AA`, `#9BE87F`, `#CDE3FB`. Light background tint `#EAF3FE`.
- **Font:** SC Prosper Sans for all text (titles, callouts, labels, tables), with Segoe UI fallback. In PBIR `textStyle` / `fontFamily` use the same stack as the theme: `'SC Prosper Sans', 'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif`.
- **Status / variance colours** (from the theme):
  - favourable = dark green `#1E7A00` for text and numbers. SC Green `#38D200` is used only for fills, bars and icons, because it has too little contrast on white for text.
  - watch / amber = `#D97706`
  - unfavourable = red `#C23B22`
  - neutral = SC Grey `#525355`

  Always pair colour with a sign or arrow (▲▼) for colour-blind users. For expense lines, "up" is bad: use the `Var Color` measure, not raw sign colouring.
- **Scenario styling (IBCS-inspired):**
  - Actual: solid Prosper Blue `#020B43`
  - Prior year: light SC Grey `#A8A9AA`
  - Budget / baseline: light SC Blue `#9AC7F7` (outlined)
  - Forecast: SC Blue `#0473EA`

  Keep the same colour for the same scenario on every page.
- **Number display:**
  - **Let Power BI scale large numbers.** Measures keep plain format strings (`#,##0`); cards, axes and data labels use their Auto display units ("5.48bn"). Don't scale in the format string, and don't set display units on top of a scaled format: the value is divided twice and shows as 0. Set a visual's display units (e.g. Millions) only when a page needs one consistent unit.
  - Put the unit in the title: "(USD bn)" on cards and charts that auto-scale, "(USD)" on tables and matrices, which show full numbers.
  - Negatives in brackets for variances.
  - Percentages to 1 decimal.
- **Chart choice:**
  - Time runs horizontally (column/line).
  - Categories run vertically (bar), sorted by value.
  - Bridges use a waterfall.
  - Statements use a matrix.
  - Pie/donut only for ≤ 4 parts of a whole.
  - Gauges: avoid.
- **Titles state the insight or the measure + unit.** Use a dynamic title measure where it helps.
- **Slicers** go in the header band: fiscal year, period, entity/branch. Use dropdown mode to save space. Sync them across pages in Desktop.
- **Accessibility:** set `tabOrder` top-left to bottom-right. Text has ≥ 4.5:1 contrast (the theme handles this). No information carried by colour alone.

## References
- `references/finance-visual-guide.md`: which visual for which finance or banking question, and recommended P&L-style pages with their visuals.
- `pbi-treasury-liquidity/references/pages.md`: funding, stress cash-flow, corporate cash and working-capital pages.
- `references/visual-templates.md`: copy-ready `visual.json` for:
  - textbox title
  - card
  - KPI
  - clustered column (Actual vs Budget)
  - line trend
  - combo
  - waterfall bridge
  - matrix P&L with conditional formatting
  - bar ranking
  - table
  - slicer
- `assets/sc-theme.json`: the brand report theme (SC palette, SC Prosper Sans).
- `pbi-project-capacity/references/pages.md`: portfolio, schedule, earned value, sprint, flow, capacity vs demand and utilisation pages (same theme).
- `assets/page-layouts.md`: grid coordinates for standard page layouts.
