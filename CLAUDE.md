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
  - `pbi-data-modeling`: star schema and finance/banking patterns, date table, model spec template
  - `pbi-power-query`: M patterns for CSV/Excel/SQL and `scripts/profile_data.py`
  - `pbi-dax-measures`: finance and banking measure library, calculation groups
  - `pbi-report-visuals`: page layouts, visual templates, `assets/finance-theme.json`
  - `pbi-project-capacity`: schedule & EVM, agile & flow, capacity vs demand, utilisation; connectors for Jira, Azure DevOps, MS Project / Project Server, Planner, Excel

## Workflow
Profile the data → propose a spec (`docs/model-spec.md`) → **user approves** → write TMDL/PBIR → run the validator.

## Conventions
- **Tables:** `Fact <Subject>`, `Dim <Entity>`. Measures live in `_Measures`, in numbered display folders.
- **Columns** use business names with spaces. Keys end in `Key` and are hidden.
- **Measures:** every one has a description and a format string. Use `DIVIDE` and `VAR`/`RETURN`. Balances are semi-additive.
- **Variance colours:** favourable `#1A7F5A`, unfavourable `#C23B22`, neutral `#6B7280`. Expense increases count as unfavourable. RAG status adds amber `#D97706`.
- **Data files** go in `data/` (CSV/Excel). SQL connection details go in the `SqlServer` / `SqlDatabase` parameters.

## Useful commands
```
python .claude/skills/pbi-power-query/scripts/profile_data.py data/ --out docs/data-profile.md
python .claude/skills/pbip-format/scripts/validate_pbip.py .
```
