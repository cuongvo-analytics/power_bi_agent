---
name: pbi-treasury-liquidity
description: Model, measure and visualise treasury and liquidity data in Power BI - bank ALM (positions, HQLA, contractual / behavioural / stressed cash flows, maturity buckets, Basel LCR/NSFR attributes, funding KPIs such as LTD, CASA, wholesale reliance, concentration, NII/NIM) and corporate treasury (cash position and forecast, facilities and headroom, net debt, weeks of cover, DSO/DPO, AR ageing, forecast accuracy). Covers as-of date and projection horizon, the + in / - out cash sign convention, semi-additive snapshots, the stress-scenario dimension, stress-vs-base comparison and FX rules. Use with pbip-format, pbi-data-modeling, pbi-dax-measures and pbi-report-visuals when building treasury, ALM or liquidity stress-testing reports.
---

# Treasury & liquidity

This skill holds the treasury domain knowledge. The generic mechanics (star schema, TMDL/PBIR, M rules, page grid, theme) stay in the other `pbi-*` skills.

## Workflow
1. **Inventory the sources.** Profile files with `pbi-power-query/scripts/profile_data.py`, or read the SQL DDL.
2. **Fix the core concepts first** (`references/model-patterns.md` §1):
   - as-of date and projection horizon
   - which cash-flow view each source represents (contractual / behavioural / stressed)
   - sign convention (+ in / − out, balances positive)
   - scenario set
3. **Classify each table:**
   - **Snapshot fact:** positions, HQLA holdings, corporate cash balance. Semi-additive.
   - **Flow fact:** realised flows, contractual / stressed / forecast flows.
   - **Event fact:** invoices.
   - **Dimension:** date, scenario, currency, entity, product (with LCR/NSFR parameters), time bucket, segment, contract, counterparty, facility, CF category.
4. **Fill in `pbi-data-modeling/templates/model-spec.md`**, using the treasury assumption rows below, and get approval.
5. **Write measures** from `references/measures.md` (folders `1.`–`9.`), and calculation groups from `references/calc-groups.md`.
6. **Build pages** from `references/pages.md`. **Validate** with `pbip-format/scripts/validate_pbip.py`.

## Model rules
- **Date table:** use the source's calendar if it ships one, spanning history start to the last contractual flow. Otherwise use `pbi-data-modeling/templates/date-table.tmdl`, with `_AsOf` = the last snapshot month-end and `_End` covering the projection horizon *and* the contractual tail. The treasury measures need its `Days From Asof` and `Period Type` columns.
- **`Dim Scenario` = stress scenarios** (ACT, BASE, IDIO, MARKET, COMBINED, REVERSE). Budget or reforecast versions go in a separate `Dim Version`. Never mix the two.
- **Keep the regulatory parameters on `Dim Product`:** LCR basis, flow and rate; HQLA level and haircut; NSFR type and factors. Measures read them from there, so changing a rate means changing data, not DAX.
- `Dim Segment` hanging off `Dim Product` is the only accepted snowflake (tiny). Don't relate `Dim Contract` to `Dim Product`, because the facts already carry `Product Code` (ambiguous path).
- **Amounts** come in `… Local` and `… RC` (reporting currency) pairs. Report in RC. Never sum `Local` across currencies.
- **Naming extras:** `Ref <Name>` for reconciliation tables, `WI <Name>` for what-if tables. Keep acronyms in column names (`Balance RC`, `LCR Rate`, `HQLA Level`).
- **Hide** technical columns (`Days From Asof`, `NSFR Band`, `LCR Base RC`).
- **Keep it narrow:** import `Dim Contract` only if contract drill-through or concentration analysis is needed.

## Measure rules
- **Display folders:** `1. Dates & Scenario`, `2. Balances`, `3. Cash Flows`, `4. Variance`, `5. Bank Liquidity`, `6. Corporate Treasury`, `9. Helpers` (hidden).
- **Sign convention:** cash flows are + received / − paid; balances are positive. A higher signed cash amount is better. **Don't** invert variance by account type, which is P&L logic and doesn't apply here. Invert only for measures shown as positive outflows, such as `Stressed 30D Net Outflow`.
- **Descriptions** state the definition, the sign (+ in / − out, or "positive balance") and the view (contractual, behavioural or stressed).
- **Snapshots:** bank balances use `[Reporting Date]` and corporate cash uses `[Corp Balance Date]`, both with `REMOVEFILTERS('Dim Date')`. **Never** use `LASTDATE('Dim Date'[Date])`: the calendar runs to the contractual tail decades ahead, so unfiltered cards go blank.
- **Scenario:** read it via `[Selected Scenario]` (defaults to BASE). Compare scenarios with `REMOVEFILTERS('Dim Scenario')` + a key filter.
- **Time intelligence on flow measures only**, with calendar year-end `"12-31"`. For snapshots and ratios, compare two dates. Don't use YTD.
- **Annualise** NIM, ROA/ROE and cost of risk using `[Annualisation Factor]`.
- Label every view as contractual, behavioural (BASE) or stressed.

## Assumption rows for the model spec
| Topic | Assumption |
|---|---|
| As-of date & horizon | <yyyy-mm-dd>; daily projection 365 days; contractual tail to final maturity |
| Sign convention | Cash flows + received / − paid; balances positive (`Side Sign` gives direction) |
| Cash-flow views | Contractual, behavioural = BASE, stressed = other scenarios |
| Scenarios | ACT, BASE, IDIO, MARKET, COMBINED, REVERSE (stress only; no budget versions) |
| Regulatory basis | Basel III LCR (BCBS 238) / NSFR (BCBS 295); national discretion: <none / EBA / SBV …> |
| Non-maturity deposits | Contractual: O/N. Behavioural: run-off curve per scenario |
| Currency | Reporting currency <EUR / USD> (`… RC` columns); projections at as-of spot × scenario FX shock |
| Corporate | Minimum cash per entity; committed facilities only count as headroom |

## Questions to ask the user when unknown
- As-of date and projection horizon; whether forecasts are re-run (forecast vintages → `references/model-patterns.md` §5).
- Regulatory framework and national discretion (Basel / EBA / SBV). Who sets the LCR/NSFR rates: the data or local rules?
- Sign convention of the source cash flows (bank or customer perspective), and how non-maturity deposits are treated (contractual O/N vs behavioural core/non-core).
- Reporting currency, significant currencies for per-currency LCR, and the FX source for projections (spot vs forward).
- Corporate: minimum operating cash per entity, committed vs uncommitted facilities, covenants to monitor.

## References
- `references/model-patterns.md`: core concepts, conformed dimensions, bank and corporate table patterns, LCR/NSFR attributes for real sources, forecast vintages, FX rules, KPI → tables map.
- `references/measures.md`: the measure library (dates & scenario, balances, flows, variance, flow TI, bank funding KPIs, corporate treasury KPIs, helpers).
- `references/calc-groups.md`: treasury Time Intelligence guard list, Stress Comparison (vs BASE), Currency View.
- `references/pages.md`: treasury and liquidity page catalogue.
