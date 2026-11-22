# Project & capacity report pages

Use the 1280 × 720 grid and coordinates in `pbi-report-visuals/assets/page-layouts.md` (× 1.5 for 1920 × 1080) and the `visual.json` templates in `pbi-report-visuals/references/visual-templates.md`. Max 8 visuals per page. Measures are from `measures.md`.

## Colour rules (brand theme `sc-theme.json`)
| Meaning | Colour |
|---|---|
| Favourable / Green RAG / SPI, CPI ≥ 0.95 / allocation 70–100 % | `#1E7A00` text, SC Green `#38D200` fills |
| Watch / Amber RAG / SPI, CPI 0.90–0.95 / allocation < 70 % | `#D97706` |
| Unfavourable / Red RAG / SPI, CPI < 0.90 / allocation > 100 % | `#C23B22` |
| No status / neutral | SC Grey `#525355` |
| Plan, baseline, PV, capacity line | Prosper Blue `#020B43` |
| Actual, EV, completed | SC Blue `#0473EA` |
| Cost (AC), demand, scope | light SC Blue `#9AC7F7` or SC Grey `#525355` |

Apply colours with field-value conditional formatting bound to the `… Color` helper measures. Always show the value or RAG text as well.

Slicers in the header band: Portfolio / Project, Team, Role, and a week or month range (`Dim Date[Week Start]` between-slicer). Show `[Status Date]` in the title area ("Status as of 22 Nov 2026").

## 1. Portfolio overview: "Which projects need attention?"
Executive layout.
- KPI 1–4: Active projects · `SPI` (portfolio) · `CPI` (portfolio) · `VAC`.
- Main chart (scatter): X = `SPI`, Y = `CPI`, details = Project Name, size = `BAC`. Add constant lines at 1.0 on both axes. The bottom-left quadrant = late and over budget.
- Side chart: bar of `Max Slippage Days` by project, sorted descending, with `SPI Color` formatting.
- Detail: table with Project, PM, Health RAG (`RAG Color` background), `SPI`, `CPI`, `EAC`, `VAC`, `Milestones On Time %`, Finish Date.

## 2. Schedule & milestones: "Are we hitting our dates?"
Portfolio layout.
- KPI: `Milestones` due · `Milestones On Time %` · `Late Tasks` · `Overdue Tasks`.
- Composition: clustered column of `Milestones` vs `Milestones By Forecast` by month. Shows the planned date versus where milestones are now forecast.
- Ratio trend: line of `Avg Slippage Days` by month (baseline finish month).
- Breakdown: bar of `Late Tasks` by project or WBS Level 1.
- Table: milestone list with Task Name, Baseline Finish, Finish, slippage days (`Finish − Baseline Finish` as a measure), Is Critical. Conditional icon: ▲ late / ● on time.

A Gantt chart needs a custom visual (not in the PBIR templates). Offer it as a manual step in Desktop if the user wants one.

## 3. Earned value: "Will we finish on budget?"
Executive layout, one project selected (or the portfolio).
- KPI: `BAC` · `EAC` · `VAC` · `TCPI`.
- Main chart (line, continuous `Week Start` axis): `PV Cumulative` (Prosper Blue), `EV Cumulative` (SC Blue), `AC Cumulative` (SC Grey). This is the S-curve. EV and AC stop at the EVM status date.
- Side chart (line): `SPI` and `CPI` by week, with a constant line at 1.0.
- Detail: matrix by project (rows) with PV, EV, AC, SV, CV, SPI, CPI, EAC, VAC. Negatives in brackets, and SV/CV coloured by sign.

## 4. Sprint delivery: "Is the team delivering what it commits?"
Portfolio layout, one team selected (rolling velocity needs a single team).
- KPI: `Completed Points` (last closed sprint) · `Rolling Velocity 3` · `Say Do %` · `Scope Change %`.
- Composition: clustered column by Sprint Name (sorted by Sprint Order) with `Committed Points` and `Completed Points`, plus a `Rolling Velocity 3` line (combo).
- Ratio trend: line of `Say Do %` by sprint, with a target band of 80–100 %.
- Breakdown: sprint burndown for the selected sprint: line of `Remaining Points` vs `Ideal Remaining Points` by day.
- Table: burnup (line) of `Completed Points To Date` vs `Total Scope Points` by week, or the sprint backlog table.

## 5. Flow: "How fast and predictable is delivery?"
Portfolio layout.
- KPI: `Throughput Per Week` · `Cycle Time P85 Days` · `WIP` · `Ageing WIP Days`.
- Composition: cumulative flow, a stacked area of `CFD Items` by Date with State Category in the legend (sorted by `State Order`, Done at the bottom).
- Ratio trend: column of `Throughput` by week.
- Breakdown: scatter of `Fact Work Item[Cycle Time Days]` per item (details = Work Item Id) against Resolved Date, with a constant line at `Cycle Time P85 Days`.
- Table: ageing WIP list (items in progress, age, state, assignee), sorted by age, red when the age is above P85.

## 6. Capacity vs demand: "Do we have enough people for the plan?"
Executive layout.
- KPI: `Available FTE` · `Demand FTE` · `Capacity Gap FTE` (green if ≥ 0, red if < 0) · `Over-allocated People`.
- Main chart (combo, `Week Start` axis, next 12–26 weeks): stacked columns of `Allocated Hours`, `Unassigned Demand Hours`, `Pipeline Hours Weighted`, with a line for `Available Hours`. Weeks where the columns go above the line are shortfalls.
- Side chart: bar of `Capacity Gap Hours` by Role, diverging around zero (red negative, green positive).
- Detail: heatmap matrix with rows Person (or Role), columns `Week Start`, value `Allocation %`, and background from `Allocation Color`. This is the over/under-allocation map.

## 7. Utilisation: "Are people working on the right things?"
Portfolio layout, history weeks only.
- KPI: `Utilisation %` · `Utilisation vs Target` · `Billable Utilisation %` · `Timesheet Compliance %`.
- Composition: stacked column of `Billable Hours` and `Project Hours − Billable Hours` (as a measure), plus a line for `Available Hours`, by week.
- Ratio trend: line of `Utilisation %` vs `Utilisation Target %` by month.
- Breakdown: bar of `Utilisation vs Target` by Team or Role.
- Table: person list with Available, Booked, Project, Billable hours, `Utilisation %`, `Timesheet Compliance %` (amber below 95 %).

## 8. Drill-through: project detail
Drill-through on `Dim Project[Project Name]`, from pages 1–3 and 6. Shows the S-curve, milestone table, allocated people by week, and booked vs allocated hours (`Plan Variance Hours`).
