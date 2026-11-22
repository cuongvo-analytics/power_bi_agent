---
name: pbi-data-modeling
description: Design or change a Power BI semantic model as a star schema - inventory sources, classify facts (snapshot / flow / event / accumulating) and dimensions, state the grain, define keys, relationships and role-playing dates, handle semi-additive snapshots and point-in-time attributes, set up the date table, and write the model spec for approval. Domain patterns live in pbi-treasury-liquidity and pbi-project-capacity. Use before writing tables or relationships in TMDL, or when the user asks to "define the data model".
---

# Data modeling (star schema)

This skill covers the generic method. The domain patterns (tables, grain, attributes, assumptions) are in the domain skills:

| Domain | Skill | Model reference |
|---|---|---|
| Treasury & liquidity (bank ALM, corporate treasury) | `pbi-treasury-liquidity` | `pbi-treasury-liquidity/references/model-patterns.md` |
| Project management & capacity planning | `pbi-project-capacity` | `pbi-project-capacity/references/model-patterns.md` |

Load the matching domain skill before step 2. A model can combine domains: share `Dim Date`, and keep each domain's facts and dimensions separate unless a dimension is truly conformed (for example `Dim Entity`).

## Workflow
1. **Inventory the sources.** Profile with `pbi-power-query/scripts/profile_data.py`, or read the SQL DDL / API metadata. Never guess column names.
2. **Fix the domain's core concepts** (as-of date, horizon, sign convention, scenario or version set, unit of measure, week start) from the domain skill.
3. **Classify each table:**
   - **Snapshot fact:** a state on a date (balances, positions, remaining work, WIP). Semi-additive.
   - **Flow / transaction fact:** amounts or hours over time. Additive.
   - **Accumulating snapshot:** one row per process instance with milestone dates (tasks, work items, invoices).
   - **Dimension:** descriptive attributes used for filtering and grouping.
4. **State the grain of every fact** in one sentence, e.g. *"one row per contract per month-end"*, *"one row per person per week"*.
5. **Define keys.** Use source codes as keys (`… Code`, `… Key`, `… Id`), unique and non-blank. Map orphan fact keys to an Unknown member (`-1`) in Power Query.
6. **Define relationships:** dimension (1) → fact (*), single direction, one active path.
   - **Role-playing dates** (created / resolved, baseline / forecast): one active relationship, the others inactive and used with `USERELATIONSHIP` in measures.
   - **Point-in-time attributes** (team, role, segment at the time): copy the key onto the fact row at load time, and relate the dimension to the fact. Don't snowflake through the current-state dimension.
   - Reference tables (reconciliation values from the source) aren't related, or only to `Dim Date`, and are for reconciliation only.
7. **Date table:**
   - Use the source's calendar if it ships one. Otherwise use `templates/date-table.tmdl` and set its start, end and as-of variables for the domain.
   - Mark it as the date table on `Date`. Its range must cover history *and* every future date the facts hold (projections, contractual tail, planned weeks).
   - Weekly facts join on the Monday `Week Start` date.
   - Turn off auto date/time (`annotation __PBI_TimeIntelligenceEnabled = 0` in `model.tmdl`).
8. **Fill in `templates/model-spec.md`**, including the domain's assumption rows, and present it for approval. Only after approval, write TMDL (see `pbip-format`).

## Rules
- **Star schema.** Avoid snowflakes, except tiny ones that a domain skill explicitly accepts. No fact-to-fact relationships. Bi-directional or many-to-many only with a written reason.
- **Snapshots are semi-additive:** evaluate them on one date per context and never sum across dates. Flows are additive.
- **Scenarios vs versions:** stress or what-if scenarios and planning versions (Budget, Reforecast) are different dimensions. Never mix them in one table.
- **Naming:**
  - Tables: `Fact <Subject>`, `Dim <Entity>`; measures in `_Measures`.
  - Columns: business names in Title Case with spaces, acronyms kept.
  - Keys end in `Key` and are hidden.
- **Hide** keys, technical columns and raw amount columns. Users interact through measures.
- **Data types:**
  - `decimal` for money
  - `double` for rates, factors and hours
  - date-only values as `dateTime` with no time part, or relationships won't match
  - `summarizeBy: none` on rates, factors, days, keys and snapshot values
  - `sortByColumn` for month name, week label, bucket label and other ordered labels
- **Keep it narrow:** import only the columns and tables the agreed measures and pages need.

## Questions to ask the user when unknown
- The questions in the domain skill.
- Fiscal year start, week start, and the time zone of timestamps.
- Refresh frequency, data volume, and whether DirectQuery is required.
- Row-level security needs (by entity, team or portfolio).

## References
- `templates/model-spec.md`: the proposal template.
- `templates/date-table.tmdl`: fallback calendar with fiscal and ISO week columns.
- Domain model patterns: see the table above.
