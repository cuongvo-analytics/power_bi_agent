# Project & capacity model patterns

The naming follows the project conventions: `Fact <Subject>`, `Dim <Entity>`, business names with spaces, and keys ending in `Key` (hidden). Load only the facts for the domains in scope.

## 1. Conformed dimensions

| Dimension | Key | Main columns | Notes |
|---|---|---|---|
| `Dim Date` | `Date` | Year, Month, `Week Start`, `ISO Week`, `ISO Year`, `Year Week`, `Is Working Day` | One calendar for all facts. Weekly facts join on their Monday date. Week columns: see §4. |
| `Dim Project` | `Project Key` | Project Code, Project Name, Portfolio, Programme, Project Manager, Methodology (Waterfall / Agile / Hybrid), Status, Health RAG, Stage, EV Method, BAC, Is Pipeline, Probability, Start Date, Finish Date | One row per project. Add the `-1 Unknown` row. |
| `Dim Person` | `Person Key` | Person Name, Current Team, Current Role, Location, Employment Type, Contract FTE, Standard Weekly Hours, Cost Rate, Utilisation Target %, Billable Target %, Start Date, End Date, Is Active | Current attributes only. Point-in-time team/role are on the facts. Add `-1 Unassigned`. |
| `Dim Team` | `Team Key` | Team Name, Department, Team Lead | Filters capacity, demand, timesheet, work-item and sprint facts directly. |
| `Dim Role` | `Role Key` | Role Name, Role Family, Seniority, Default Non-Project % | Demand is often by role. |
| `Dim Sprint` | `Sprint Key` | Sprint Name, `Team Key` (hidden), Start Date, End Date, Sprint Order, Sprint State (Future / Active / Closed) | `Sprint Order` is a sequence **within each team** (1, 2, 3…), set in M. Sort `Sprint Name` by `Sprint Order`. |
| `Dim State` | `State Key` | Source System, Source State, State Category (To Do / In Progress / Done / Removed), State Order | One row per tool + state. `State Order` drives the CFD stacking order. |
| `Dim Work Item Type` | `Work Item Type` (text) | Type Group (Feature work / Defect / Tech debt / Other) | Optional, small. Can stay a column on the fact. |

## 2. Relationships

```
Dim Date ─1──*─ Fact EVM Period[Week Start]
         ─1──*─ Fact Capacity[Week Start]
         ─1──*─ Fact Demand[Week Start]
         ─1──*─ Fact Timesheet[Date]
         ─1──*─ Fact Work Item Daily[Date]
         ─1──*─ Fact Work Item[Created Date]           (active)
         ┄1──*┄ Fact Work Item[Started Date]           (inactive)
         ┄1──*┄ Fact Work Item[Resolved Date]          (inactive)
         ─1──*─ Fact Task[Baseline Finish]             (active)
         ┄1──*┄ Fact Task[Finish]                      (inactive)

Dim Project ─1──*─ Fact Task, Fact EVM Period, Fact Work Item, Fact Demand, Fact Timesheet
Dim Person  ─1──*─ Fact Capacity, Fact Demand, Fact Timesheet
Dim Team    ─1──*─ Fact Capacity, Fact Demand, Fact Timesheet, Fact Work Item, Fact Work Item Daily, Fact Sprint Commitment
Dim Role    ─1──*─ Fact Capacity, Fact Demand, Fact Timesheet
Dim Sprint  ─1──*─ Fact Sprint Commitment, Fact Work Item Daily
Dim State   ─1──*─ Fact Work Item, Fact Work Item Daily
```
- All relationships are single-direction, dimension → fact.
- `Dim Sprint[Team Key]` is **not** related to `Dim Team` (that would create an ambiguous path through the facts). The team filter reaches sprints through the facts.
- No relationship between `Dim Person` and `Dim Team` / `Dim Role`: the facts carry the point-in-time keys.
- Date columns on facts are **date** type (no time part), or the relationship won't match.

## 3. Facts and grain

| Fact | Grain | Measures/columns | Type |
|---|---|---|---|
| `Fact Task` | One row per task (optionally per `Snapshot Date`) | Task Id, `Project Key`, WBS Level 1–3, Task Name, Is Milestone, Is Critical, Is Summary, Baseline Start, Baseline Finish, Start, Finish, Actual Finish, % Complete, Baseline Work Hours, Work Hours, Actual Work Hours, Total Slack Days | Accumulating snapshot. **Exclude summary tasks** from counts and sums (keep the flag for WBS views). |
| `Fact EVM Period` | One row per project × week | `Project Key`, `Week Start`, PV, EV, AC (period amounts, not cumulative) | Flow. EV and AC are blank after the status date. |
| `Fact Work Item` | One row per work item | Work Item Id, Title, Work Item Type, `Project Key`, `Team Key`, `State Key` (current), Parent Id, Epic, Story Points, Original Estimate Hours, Created Date, Started Date, Resolved Date, Lead Time Days, Cycle Time Days | Accumulating snapshot. Compute Lead/Cycle Time Days in M. |
| `Fact Work Item Daily` | One row per work item × day it was open (or aggregated: day × team × sprint × state) | `Date`, Work Item Id, `Team Key`, `Sprint Key`, `State Key`, Story Points, Remaining Hours | Periodic snapshot, **semi-additive**. Use the aggregated grain for large backlogs. |
| `Fact Sprint Commitment` | One row per work item × sprint | `Sprint Key`, `Team Key`, Work Item Id, Committed Points, Added Points, Removed Points, Completed Points, Completed Committed Points | Computed in M or the source at sprint close. Carried-over items appear in each sprint they were in. |
| `Fact Capacity` | One row per person × week | `Person Key`, `Team Key`, `Role Key`, `Week Start`, Gross Hours, Holiday Hours, Leave Hours, Non-Project Hours, Available Hours | Flow (hours are additive across weeks). |
| `Fact Demand` | One row per project × person (or role) × week × demand type | `Project Key`, `Person Key` (-1 when unnamed), `Role Key`, `Team Key`, `Week Start`, Demand Type (Allocated / Unassigned / Pipeline), Planned Hours, Probability | Flow. Probability = 1 for approved projects. |
| `Fact Timesheet` | One row per person × project × day (× task/activity if needed) | `Person Key`, `Team Key`, `Role Key`, `Project Key` (-1 for internal codes), `Date`, Activity, Hours, Is Billable, Is Project Time, Approval Status | Flow. Load approved lines only, or filter in measures. |

**Keep it narrow:** load `Fact Work Item Daily` only if burndown, CFD or historic WIP is needed. For large Azure DevOps or Jira instances, aggregate in the source (OData `$apply`) instead of loading item × day.

## 4. Date table week columns

Add these to the calendar (they're already in `pbi-data-modeling/templates/date-table.tmdl`):
```dax
"Week Start", [Date] - WEEKDAY ( [Date], 2 ) + 1,                         // Monday
"ISO Week", WEEKNUM ( [Date], 21 ),
"ISO Year", YEAR ( [Date] - WEEKDAY ( [Date], 2 ) + 4 ),                   // year of the week's Thursday
"Year Week", FORMAT ( YEAR ( [Date] - WEEKDAY ( [Date], 2 ) + 4 ), "0000" ) & "-W" & FORMAT ( WEEKNUM ( [Date], 21 ), "00" ),
"Is Working Day", WEEKDAY ( [Date], 2 ) <= 5
```
Sort `Year Week` by `Week Start`. Public holidays: merge a holiday list in Power Query and set `Is Working Day = false`. If locations have different calendars, holidays belong in `Fact Capacity[Holiday Hours]`, not in `Dim Date`.

## 5. Source → model field mapping

Verify the field names against the actual export or API metadata. Jira custom field ids differ per site (`GET /rest/api/3/field`).

### Jira Cloud
| Model | Jira field (REST `fields.` / CSV header) |
|---|---|
| Work Item Id | `key` / Issue key |
| Work Item Type | `issuetype.name` / Issue Type |
| State, State Category | `status.name`, `status.statusCategory.name` (To Do / In Progress / Done) |
| Created / Resolved Date | `created`, `resolutiondate` |
| Started Date | first changelog transition into an In Progress-category status (`expand=changelog`) |
| Story Points | custom field, often `customfield_10016` ("Story point estimate") or the site's "Story Points" field |
| Sprint | custom field, often `customfield_10020`: array of {id, name, state, startDate, endDate}. Multi-valued if carried over: the last element is the current sprint |
| Epic / Parent | `parent.key` (team-managed and new company-managed), older: "Epic Link" custom field |
| Team | `customfield_…` (Atlassian Team) or the board/project mapping table |
| Project Code | `project.key` |

### Azure DevOps (Analytics OData)
| Model | Entity.field |
|---|---|
| Work Item Id, Title, Type, State | `WorkItems.WorkItemId`, `Title`, `WorkItemType`, `State` |
| State Category | `StateCategory`: Proposed → To Do, InProgress / Resolved → In Progress, Completed → Done, Removed → Removed |
| Created / Started / Resolved | `CreatedDate`, `ActivatedDate` (or `InProgressDate`), `CompletedDate` (or `ClosedDate`) |
| Lead / Cycle Time Days | `LeadTimeDays`, `CycleTimeDays` (computed by Analytics) |
| Story Points | `StoryPoints` (Agile) / `Effort` (Scrum) / `Size` (CMMI) |
| Sprint | `IterationSK` → `Iterations` (`IterationName`, `IterationPath`, `StartDate`, `EndDate`, `IsEnded`) |
| Team | `AreaSK` → `Areas` / `Teams` (team ↔ area-path mapping) |
| Daily snapshot | `WorkItemSnapshot` (`DateSK`, `State`, `IterationSK`, …) aggregated with `$apply` |

### MS Project desktop / Project Server Subscription Edition
| Model | Field (Project Server `ProjectData` OData / desktop export) |
|---|---|
| Task attributes | `Tasks.TaskName`, `TaskOutlineLevel`, `ParentTaskId`, `TaskIsMilestone`, `TaskIsCritical`, `TaskIsSummary`, `TaskTotalSlack` |
| Dates | `TaskBaselineStartDate`, `TaskBaselineFinishDate`, `TaskStartDate`, `TaskFinishDate`, `TaskActualFinishDate` |
| Work | `TaskBaselineWork`, `TaskWork`, `TaskActualWork`, `TaskPercentCompleted` |
| EVM | `TaskBCWS` (PV), `TaskBCWP` (EV), `TaskACWP` (AC); time-phased from `AssignmentTimephasedDataSet` (`TimeByDay`, `AssignmentBaselineCost`, `AssignmentActualCost`, …) |
| Timesheets | `TimesheetLineActualDataSet` (`TimeByDay`, `ActualWorkBillable`, `ActualWorkNonBillable`) |
| Resources | `Resources` (`ResourceName`, `ResourceStandardRate`, …) |

Desktop-only: export to Excel (File → Export → Excel with Task / Resource / Assignment maps), or Project Online / Server reporting. Project Online itself was retired on 30 Sep 2026. Treat existing PWA OData queries as legacy.

### Planner (premium plans, Dataverse)
| Model | Dataverse table.column |
|---|---|
| Project | `msdyn_project` (`msdyn_subject`, `msdyn_scheduledstart`, `msdyn_finish`, `msdyn_progress`) |
| Task | `msdyn_projecttask` (`msdyn_subject`, `msdyn_outlinelevel`, `msdyn_parenttask`, `msdyn_scheduledstart`, `msdyn_scheduledend`, `msdyn_progress`, `msdyn_effort`, `msdyn_effortcompleted`) |
| Assignment | `msdyn_resourceassignment` |
Baselines aren't reliably exposed. Use periodic snapshots (`Fact Task[Snapshot Date]`). Basic Planner plans have no connector: use Excel export, or a Power Automate flow to a SharePoint list.

### Excel resource plan (typical PMO layout)
Wide layout `Person | Role | Team | Project | 2026-01-05 | 2026-01-12 | …` (hours per week) → unpivot to `Fact Demand` (see `source-connectors.md` §1.3). Leave and holiday sheets → `Fact Capacity`.
