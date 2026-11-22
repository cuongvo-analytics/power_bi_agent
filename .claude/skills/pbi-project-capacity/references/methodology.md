# Project management & capacity methodology

Definitions only. The DAX is in `measures.md`. Agree each definition with the user before building, and state it in the measure's `///` description.

## 1. Schedule (waterfall / hybrid)

| Term | Definition |
|---|---|
| Baseline Start / Finish | Dates approved at plan sign-off (MS Project "Baseline 0"). Never changes unless formally re-baselined. |
| Start / Finish | Current schedule: actual date if it has happened, otherwise the forecast. |
| Actual Finish | Set only when the task is complete. |
| Finish Variance (slippage) days | `Finish − Baseline Finish`. Positive = late. Report in calendar days unless the user wants working days. |
| Milestone | A zero-duration task, or one flagged as a milestone in the source. |
| Milestone hit rate | Completed milestones with `Actual Finish ≤ Baseline Finish` ÷ completed milestones. |
| Late task | Not complete and `Finish > Baseline Finish`. |
| Overdue task | Not complete and `Finish < Status Date`. The schedule wasn't updated, which is a data-quality signal. |
| % Complete (work) | Actual work hours ÷ total work hours. Prefer it to duration % complete for roll-ups. |
| Critical path / total slack | **Read from the scheduling tool** (`Is Critical`, `Total Slack Days`). Don't recompute CPM in DAX. |
| Status Date | The date the schedule and EVM figures are "as of". Values after it are forecast. |

## 2. Earned value management (EVM)

All values are cumulative to the status date unless labelled "period". Use cost (reporting currency) or hours consistently, never mixed.

| Term | Formula | Meaning |
|---|---|---|
| BAC | Σ planned value over the whole project | Budget at completion |
| PV (BCWS) | Σ time-phased baseline cost up to the date | What should have been done |
| EV (BCWP) | Σ (BAC per task × % complete) | What was done, valued at baseline cost |
| AC (ACWP) | Σ actual cost / hours booked | What it actually cost |
| SV | EV − PV | < 0 behind schedule |
| CV | EV − AC | < 0 over cost |
| SPI | EV ÷ PV | < 1 behind schedule |
| CPI | EV ÷ AC | < 1 over cost |
| EAC (CPI) | BAC ÷ CPI | Forecast at completion if current cost efficiency continues (default) |
| EAC (CPI × SPI) | AC + (BAC − EV) ÷ (CPI × SPI) | When schedule pressure also drives cost |
| EAC (plan rate) | AC + (BAC − EV) | When the overrun is one-off |
| ETC | EAC − AC | Remaining spend |
| VAC | BAC − EAC | < 0 forecast overrun |
| TCPI | (BAC − EV) ÷ (BAC − AC) | Efficiency needed on the remaining work to finish on budget. > 1.1 is usually unrealistic |
| % Complete (EV) | EV ÷ BAC | |
| % Spent | AC ÷ BAC | Compare with % complete |

**EV methods** (task level): `% complete` (subjective), `0/100` (EV only at finish; conservative, for short tasks), `50/50` (half at start, half at finish), `physical % complete` (measured deliverables). Pick one per project and record it on `Dim Project[EV Method]`.

**Thresholds** (default; confirm with the PMO): SPI/CPI ≥ 0.95 green, 0.90–0.95 amber, < 0.90 red. SPI drifts to 1.0 at project end by definition, so for late projects also look at slippage days.

**S-curve:** cumulative PV over the whole timeline (baseline), with cumulative EV and AC up to the status date. The EAC can be drawn as a point at the forecast finish.

## 3. Agile delivery

| Term | Definition |
|---|---|
| Velocity | Story points (or items) **completed** in a sprint. Only items "done" by sprint end count. |
| Rolling velocity | Average of the last 3 closed sprints for one team. Use it for forecasting. |
| Committed | Points in the sprint at sprint start. |
| Added / Removed | Scope change after sprint start. |
| Say/Do % | Completed committed points ÷ committed points. 80–100 % is healthy; consistently > 100 % means under-commitment. |
| Sprint burndown | Remaining points of the sprint per day, against an ideal line from committed points to 0 over the sprint's working days. |
| Burnup | Cumulative completed vs total scope over time. Shows scope creep, which burndown hides. |
| Release forecast | Remaining backlog ÷ rolling velocity = sprints left. Give a range using min/max velocity of the last 6 sprints. |

## 4. Flow (Kanban metrics, work-item level)

| Term | Definition |
|---|---|
| Lead time | Resolved Date − Created Date (customer view). |
| Cycle time | Resolved Date − Started Date. Started = first transition into an `In Progress` category state. |
| Throughput | Items resolved per period (week). |
| WIP | Items in `In Progress` on a date. |
| Work item age | Status Date − Started Date for items still in progress. Compare with the cycle-time P85: items older than P85 are at risk. |
| Percentiles | Report P50 / P85 / P95 cycle time, never only the mean (the distribution is right-skewed). "85 % of items finish within N days." |
| Cumulative flow (CFD) | Count of items per state category per day, stacked. Widening bands = growing queues. |
| Little's law | Avg cycle time ≈ avg WIP ÷ avg throughput (same time unit). A sanity check for the data. |

## 5. Capacity & demand (people, weekly hours)

```
Gross Hours      = Standard Weekly Hours × FTE contract (0.5, 0.8, 1.0)   per person-week
Holiday Hours    = public holidays on working days × daily hours (per location calendar)
Leave Hours      = approved leave
Non-Project Hrs  = Gross × non-project % (admin, training, BAU) — per role or person
Available Hours  = Gross − Holiday − Leave − Non-Project
```

| Term | Definition |
|---|---|
| Allocated hours | Hours assigned to named people on approved projects, per week. |
| Unassigned demand | Role-level demand with no named person yet (`Person Key = -1`). |
| Pipeline hours (weighted) | Planned hours of not-yet-approved projects × win/approval probability. |
| Demand hours | Allocated + unassigned + weighted pipeline. |
| Capacity gap | Available − Demand. Positive = spare capacity, negative = shortfall. Analyse by role and week. |
| Allocation % | Allocated ÷ Available, **per person-week**. > 100 % over-allocated, < 70 % under-used (default thresholds). |
| Bench hours | Σ max(0, Available − Allocated) per person-week. Never net over-allocation of one person against the bench of another. |
| FTE | Hours ÷ (Standard Weekly Hours × number of weeks in context). |

Weeks that cross a month boundary belong to the month of their Monday. If a monthly view must be exact, split weekly hours to working days in Power Query.

## 6. Timesheets & utilisation

| Term | Definition |
|---|---|
| Booked hours | All approved timesheet hours (project + internal codes). |
| Project hours | Booked hours on project codes. |
| Billable hours | Booked hours flagged billable. |
| Utilisation % | Project hours ÷ Available hours. (Some firms use Gross hours as the denominator; agree which.) |
| Billable utilisation % | Billable hours ÷ Available hours. |
| Billable mix % | Billable ÷ Booked. |
| Utilisation vs target | Utilisation − target, where the target is weighted by available hours (targets per role on `Dim Person` or `Dim Role`). |
| Timesheet compliance % | Booked hours ÷ expected hours (Gross − Holiday − Leave). Below ~95 % the actuals (and AC in EVM) are understated. |
| Plan accuracy | Project hours booked − allocated hours, per project and week. |
