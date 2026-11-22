# Model spec: <Report name>

_Status: DRAFT, awaiting approval · Date: <yyyy-mm-dd> · Domain: <treasury & liquidity / project & capacity / …>_

## 1. Purpose & audience
- Business questions this report answers (3–6 bullets), e.g. *Can we meet 30-day stressed outflows?*, *Which projects are late or over budget?*, *Do we have enough people for the next 12 weeks?*
- Primary users (ALCO, Treasury, PMO, delivery leads, resource managers, CFO):
- Refresh frequency / as-of cadence:

## 2. Assumptions (confirm or correct)
Start with the general rows, then paste the domain's assumption rows from its `SKILL.md` (`pbi-treasury-liquidity`, `pbi-project-capacity`).

| Topic | Assumption |
|---|---|
| Data sources | <CSV/Excel files in data/ · SQL database · Jira / Azure DevOps / Project Server API> |
| As-of / status date | <yyyy-mm-dd, or end of selected period capped at today> |
| Calendar | Fiscal year starts <month>; weeks start on Monday (ISO); time zone <…> |
| Currency / unit | <reporting currency · hours · story points> |
| <domain rows> | <…> |

## 3. Sources
| Source | Type | Rows | Used for |
|---|---|---|---|
| data/<file>.csv | CSV | <rows> | Fact <Subject> |
| <API / OData entity> | REST / OData | <rows> | Fact <Subject> |

## 4. Tables
| Table | Kind | Grain (one row per …) | Key | Source / transform |
|---|---|---|---|---|
| Fact <Subject> | Snapshot / Flow / Accumulating | <grain> | <key> | <source, main transforms> |
| Dim <Entity> | Dimension | <entity> | <Entity Key> | <source> (+ Unknown row) |
| Dim Date | Dimension | day | Date | <source calendar / templates/date-table.tmdl> (marked date table) |
| _Measures | Measure table | — | — | — |

### Columns (visible columns only; hidden keys and technical columns are implied)
**Dim <Entity>**: <Column>, <Column>, …

## 5. Relationships
| From (many) | To (one) | Active | Direction | Note |
|---|---|---|---|---|
| Fact <Subject>[<Date>] | Dim Date[Date] | ✔ | Single | |
| Fact <Subject>[<Other Date>] | Dim Date[Date] | ✖ | Single | role-playing, used with `USERELATIONSHIP` |

## 6. Hierarchies
- Dim Date › Calendar: Year → Quarter → Year Month → Date
- <Dim> › <Hierarchy>: <Level> → <Level>

## 7. Measures
| Folder | Measure | Definition (plain English) | Sign / unit / view | Format |
|---|---|---|---|---|
| <1. / P1.> <Folder> | <Measure> | <definition> | <+ good / hours / snapshot> | <format> |

## 8. Report pages
| Page | Question it answers | Visuals |
|---|---|---|
| <Page> | <question> | <KPI cards, trend, breakdown, detail> |

```
┌──────── Title · as of <date> ─────────────────── Slicer ▾ Slicer ▾ ─────┐
│ KPI 1   │ KPI 2    │ KPI 3         │ KPI 4                              │
│ Main chart (trend)                    │ Side chart (breakdown)          │
│ Detail table / matrix                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## 9. Reconciliation
DAX vs <source reference values / regulatory return / tool's own report> for <key metrics>; tolerance < 0.1%.

## 10. Open questions
1. …

## 11. Files to be written
- `definition/tables/*.tmdl` (list)
- `definition/relationships.tmdl`, `definition/model.tmdl` (`ref table` lines)
- `definition/expressions.tmdl` (parameters: `DataFolder`, `SqlServer`, API base URLs)
- `*.Report/definition/pages/...`
