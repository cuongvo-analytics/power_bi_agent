# Treasury & liquidity report pages

Use the 1280 × 720 grid in `pbi-report-visuals/assets/page-layouts.md` (× 1.5 for 1920 × 1080), the `visual.json` templates in `pbi-report-visuals/references/visual-templates.md`, and the brand theme `pbi-report-visuals/assets/sc-theme.json`. Max 8 visuals per page. Measures are from `measures.md`.

## Colour rules
| Meaning | Colour |
|---|---|
| Actual / ACT | Prosper Blue `#020B43` |
| BASE (behavioural) | SC Blue `#0473EA` |
| IDIO | amber `#D97706` |
| MARKET | `#4E547B` (Prosper Blue tint) |
| COMBINED | red `#C23B22` |
| REVERSE | SC Grey `#525355` |
| Contractual view | light SC Blue `#9AC7F7` |
| Favourable variance (higher cash) | `#1E7A00` text, SC Green `#38D200` fills |
| Unfavourable variance | `#C23B22` |

Use the same scenario colour on every page (set per series with `dataPoint` selectors). Always label the view (contractual / behavioural / stressed) in the visual title, and show `[Title As-of]` in the header.

Header slicers: Scenario (single-select on KPI pages), Currency, Entity, and a Year Month / date range.

## 1. Funding overview: "Is the balance sheet funded stably?"
Executive layout.
- KPI: `Total Deposits` · `Loan to Deposit %` · `CASA Ratio %` · `Wholesale Funding Reliance %`.
- Main chart (combo): `Total Deposits` and `Gross Loans` columns by month-end, with a `Loan to Deposit %` line.
- Side chart: stacked bar of `Balance` by `Dim Product[Category]` (liabilities side), sorted.
- Detail: matrix by Category → Product with `Balance`, `Weighted Avg Rate %`, and share of funding.

## 2. Funding concentration & profitability
Portfolio layout.
- KPI: `Top 10 Deposit Concentration %` · `Short-term Wholesale Share %` · `Net Interest Income` · `NIM %`.
- Composition: stacked column of `Balance` by Segment over month-ends.
- Ratio trend: line of `NIM %` by month.
- Breakdown: bar of `Interest Income` and `Interest Expense` by product category.
- Table: top-10 depositors (`Dim Contract` / counterparty) with balance and share.

## 3. Cash-flow projection & stress: "How do flows evolve under stress?"
Executive layout. Scenario slicer multi-select on this page.
- KPI: `Stressed Net CF` (next 30 days, BASE) · same for the selected stress scenario · `Stressed CF vs BASE` · `Is Projection` label.
- Main chart (line, daily or weekly axis, projection only): `Cumulative Projected CF` by Scenario. This is the liquidity-position curve before the counterbalancing capacity.
- Side chart: bar of `Stressed CF vs BASE` by `Dim Product[Category]` or flow type. The most negative bar = largest stress driver.
- Detail: matrix with Scenario on rows and the `Stress Comparison` calc group (Selected / Base / Δ vs Base) on columns, values `Stressed Net CF` (see `calc-groups.md`).

## 4. Corporate cash & headroom: "Do we stay above minimum cash?"
Executive layout.
- KPI: `Corp Cash` · `Corp Headroom` (red if < 0) · `Facility Utilisation %` · `Weeks of Cover`.
- Main chart (line, daily axis across history and projection): `Corp Cash` and `Corp Headroom`, with a constant line at 0. Projection dates use the scenario selected.
- Side chart: bar of `Corp Headroom` by entity.
- Detail: facility table (`Dim Facility`): type, limit, drawn, `Facility Utilisation %`, maturity, covenant.

## 5. Working capital: "Are customers paying on time?"
Portfolio layout.
- KPI: `Open AR` · `Overdue AR %` · `DSO (days)` · `DPO (days)`.
- Composition: stacked column of `Open AR` by `AR Ageing` bucket over month-ends.
- Ratio trend: line of `DSO (days)` and `DPO (days)`.
- Breakdown: bar of `Overdue AR` by counterparty (top 10), with `Key Account AR Share %` in the tooltip.
- Table: open invoices past due, sorted by days past due.

## 6. Regulatory liquidity (LCR / NSFR / survival)
Requires `LCR %`, `NSFR %`, `HQLA Stock`, `CBC` and `Survival Days`, which aren't in `measures.md` yet. Define them with the user first (methodology, HQLA caps, run-off rates from `Dim Product`). Then use the executive layout:
- KPI: `LCR %` · `NSFR %` · `Survival Days` · `CBC`.
- Main chart: `LCR %` and `NSFR %` trend with a 100 % constant line.
- Side chart: `LCR %` by scenario.
- Detail: maturity ladder matrix (`Dim Time Bucket` on columns, contractual vs stressed rows) or a survival table by scenario.
