# Power BI finance & banking report project

This repo holds a Power BI Project (PBIP) plus a Claude Code agent and skills that help design the semantic model and build the report.

## Project format
- **Power BI Project (.pbip)**, with the semantic model in **TMDL** and the report in **PBIR**.
- In Power BI Desktop → Options → Preview features, enable:
  - "Power BI Project (.pbip) save option"
  - "Store semantic model using TMDL format"
  - "Store reports using enhanced metadata format (PBIR)"
- **Close Power BI Desktop before Claude edits files**, then reopen the `.pbip`.

## Agents and skills
- `.claude/agents/powerbi-developer.md`: data model, DAX, Power Query and report pages for treasury & liquidity, project management and capacity planning.
- Skills in `.claude/skills/`:
  - `pbip-format`: TMDL/PBIR syntax and `scripts/validate_pbip.py`
  - `pbi-data-modeling`: star-schema method, date table, model spec template (generic)
  - `pbi-power-query`: M patterns for CSV/Excel/SQL and `scripts/profile_data.py`
  - `pbi-dax-measures`: DAX method, format strings, calculation-group template (generic)
  - `pbi-report-visuals`: page layouts, visual templates, brand theme `assets/sc-theme.json`
  - `pbi-treasury-liquidity`: bank ALM and corporate treasury model patterns, measures, stress calc groups, pages
  - `pbi-project-capacity`: schedule & EVM, agile & flow, capacity vs demand, utilisation; connectors for Jira, Azure DevOps, MS Project / Project Server, Planner, Excel

## Workflow
Profile the data → propose a spec (`docs/model-spec.md`) → **user approves** → write TMDL/PBIR → run the validator.

## Conventions
- **Tables:** `Fact <Subject>`, `Dim <Entity>`. Measures live in `_Measures`, in numbered display folders.
- **Columns** use business names with spaces. Keys end in `Key` and are hidden.
- **Measures:** every one has a description and a format string. Use `DIVIDE` and `VAR`/`RETURN`. Balances are semi-additive.
- **Brand:** SC palette Prosper Blue `#020B43`, SC Blue `#0473EA`, SC Green `#38D200`, SC Grey `#525355`; font **SC Prosper Sans** (Segoe UI fallback). Theme: `.claude/skills/pbi-report-visuals/assets/sc-theme.json`.
- **Status / variance colours:** favourable `#1E7A00` text (SC Green `#38D200` for fills), watch / amber `#D97706`, unfavourable `#C23B22`, neutral `#525355`. Expense increases count as unfavourable.
- **Data files** go in `data/` (CSV/Excel). SQL connection details go in the `SqlServer` / `SqlDatabase` parameters.

## Useful commands
```
python .claude/skills/pbi-power-query/scripts/profile_data.py data/ --out docs/data-profile.md
python .claude/skills/pbip-format/scripts/validate_pbip.py .
# synthetic demo data (CSVs are git-ignored; see the README in each folder for tables and expected results)
python scripts/generate_liquidity_sample.py --seed 42 --out data/liquidity_sample          # → power_bi_report/liquidity_report
python scripts/generate_capacity_sample.py --seed 42 --out data/capacity_planning_sample   # → power_bi_report/capacity_planning
```
