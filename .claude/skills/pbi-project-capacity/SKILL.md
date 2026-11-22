---
name: pbi-project-capacity
description: Model, measure and visualise project management and people capacity data in Power BI - waterfall schedules (baseline vs forecast, milestones, slippage, critical path), earned value management (PV, EV, AC, SPI, CPI, EAC, VAC, TCPI, S-curve), agile delivery (sprints, velocity, say/do, burndown/burnup, throughput, cycle and lead time percentiles, WIP, ageing, cumulative flow), resource capacity vs demand in weekly hours (available hours, allocations, pipeline, capacity gap, over-allocation, bench, FTE) and timesheets & utilisation (booked, billable, targets, compliance). Covers sources from Jira, Azure DevOps, MS Project / Project Server, Planner and Excel/CSV, both exports and REST/OData. Use with pbip-format, pbi-data-modeling, pbi-dax-measures and pbi-report-visuals when building PMO, delivery or resource-planning reports.
---

# Project management & capacity planning

This skill holds the domain knowledge. The generic mechanics (TMDL/PBIR syntax, M rules, page grid, theme) stay in the other `pbi-*` skills.

## Workflow
1. **Identify the domains in scope**: schedule & EVM, agile delivery, capacity & demand, timesheets & utilisation. Each maps to a set of facts in `references/model-patterns.md` §3.
2. **Map the sources.** For each tool, take the field mapping in `references/model-patterns.md` §5 and the M pattern in `references/source-connectors.md`. Profile exports with `pbi-power-query/scripts/profile_data.py`. For APIs, read one page of the response before writing the full query. Never guess field ids (Jira custom fields differ per site).
3. **Agree the definitions** from `references/methodology.md` that the report will use: EV method, "done", cycle-time start point, available-hours formula, utilisation denominator. Ask the questions below for anything unknown.
4. **Fill in `pbi-data-modeling/templates/model-spec.md`**. In §2 Assumptions, replace the treasury rows with the PM rows: standard weekly hours, week start, holiday calendar, EV method, estimation unit, state mapping, utilisation definition. Present the spec and wait for approval.
5. **Write the model and measures** with `references/measures.md` (display folders `P1`–`P9`).
6. **Build pages** from `references/pages.md`, using the grid and visual templates in `pbi-report-visuals`.
7. **Validate** with `python .claude/skills/pbip-format/scripts/validate_pbip.py <project root>`.

## Rules
- **Time grain:** capacity, demand and EVM facts are **weekly**, keyed on the **Monday `Week Start`** date, which relates to `Dim Date[Date]`. Timesheets and work-item snapshots are daily. Use the week columns of `pbi-data-modeling/templates/date-table.tmdl`.
- **Unit:** hours are the base unit. FTE is derived: hours ÷ (standard weekly hours × weeks in context). Never store FTE and hours side by side as additive facts.
- **Snapshots are semi-additive:** remaining work, story points remaining, WIP, % complete, item counts by state. Evaluate them on one date (`[Status Date]` or the last date in context). Never sum across days.
- **Role-playing dates:** a work item has created, started, resolved and closed dates. One relationship to `Dim Date` is active (`Created Date`). The others are inactive and used with `USERELATIONSHIP` (for example throughput on `Resolved Date`).
- **State categories:** map every source workflow state to `Dim State[State Category]` = `To Do` / `In Progress` / `Done` (plus `Removed`, excluded from metrics). Metrics use the category, never raw state names. This makes Jira, Azure DevOps and Planner comparable.
- **Baseline vs actual:** baseline, current/forecast and actual values live in **separate columns** (`Baseline Finish`, `Finish`, `Actual Finish`). Never overwrite a baseline. If the source has no baselines, snapshot the task table periodically (`Fact Task` with a `Snapshot Date`).
- **Point-in-time attributes:** copy `Team Key` and `Role Key` onto capacity, demand and timesheet rows at load time. People move teams. The fact row keeps the team they were in that week, and `Dim Team` / `Dim Role` filter the facts directly (no snowflake through `Dim Person`).
- **EVM from sums:** portfolio SPI/CPI is Σ EV ÷ Σ PV and Σ EV ÷ Σ AC, never an average of project ratios. Future weeks have **blank** EV and AC, not 0.
- **Agile ratios are per team:** velocity and say/do are not comparable across teams. Rolling velocity requires a single team in context.
- **Colours:** RAG = green `#1A7F5A`, amber `#D97706`, red `#C23B22`, plus grey `#6B7280` for no status. Always show the RAG text too. SPI/CPI ≥ 1 is favourable. Allocation > 100 % is unfavourable and < 70 % is amber (under-used).

## Questions to ask the user when unknown
- Standard weekly hours (37.5 / 40), the week start (ISO Monday is the default), public holiday calendar per location, and where leave data comes from.
- Estimation unit: story points, hours or item count. Is the definition of "done" a status or a resolution?
- Cycle time start: first move to In Progress, or commitment to a sprint?
- Sprint length, and whether sprints are per team or shared.
- EV method: % complete, 0/100, 50/50, or physical % complete per task. Do BAC and cost rates come from the tool or from finance? Hours-based or cost-based EVM?
- Utilisation: denominator (available hours vs gross hours), the targets per role, the billable definition, and whether internal codes appear in timesheets.
- Demand: are pipeline projects included, and with what probability? Is there unnamed (role-only) demand?
- Team membership history: is a dated history available, or only the current team?

## References
- `references/methodology.md`: definitions and formulas for schedule, EVM, agile and flow, capacity and utilisation, with interpretation thresholds.
- `references/model-patterns.md`: dimensions, facts and grain, relationships, the date-table week columns, and source → model field mapping for Jira, Azure DevOps, MS Project / Project Server, Planner and Excel.
- `references/measures.md`: the DAX library (folders `P1. Schedule` … `P9. Helpers`).
- `references/source-connectors.md`: M for exports and APIs (Jira Cloud REST, Azure DevOps Analytics OData, Project Server ProjectData OData, Planner premium in Dataverse), plus refresh and credential rules.
- `references/pages.md`: the page catalogue with layouts, visual choices and colour rules.
