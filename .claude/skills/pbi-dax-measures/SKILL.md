---
name: pbi-dax-measures
description: Write, organise and document DAX measures in a Power BI semantic model - base and derived measure layers, numbered display folders, descriptions and format strings, DIVIDE and VAR/RETURN style, semi-additive snapshot patterns, role-playing dates with USERELATIONSHIP, time intelligence on flow measures only, conditional-formatting colour helpers and guarded calculation groups. Domain measure libraries live in pbi-treasury-liquidity and pbi-project-capacity. Use whenever adding or fixing measures in the semantic model.
---

# DAX measures

This skill covers the generic method. The measure libraries are in the domain skills:

| Domain | Library | Display folders |
|---|---|---|
| Treasury & liquidity | `pbi-treasury-liquidity/references/measures.md` | `1. Dates & Scenario` … `6. Corporate Treasury`, `9. Helpers` |
| Project management & capacity | `pbi-project-capacity/references/measures.md` | `P1. Schedule` … `P6. Utilisation`, `P9. Helpers` |

## Workflow
1. Read the model first: tables, columns, relationships and existing measures. Reuse base measures; never define a measure twice.
2. Build in layers:
   - **Base**: simple aggregations of fact columns (`SUM`, `COUNTROWS`), plus snapshot measures that pick one date.
   - **Derived**: ratios, variances and KPIs built only from base measures.
   - **Comparisons**: vs baseline / scenario / prior period, as measures or as guarded calc groups (`references/calc-groups.md`).
   - **Helpers**: status dates, labels, colours (hidden folder).
3. Propose the list (folder · name · plain-English definition · sign/unit · format) and get approval.
4. Write the measures into `tables/_Measures.tmdl` (see `pbip-format/references/tmdl-syntax.md`).
5. Validate with `pbip-format/scripts/validate_pbip.py`, and reconcile against source reference values where they exist.

## Rules
- **All measures** live in `_Measures`, in the domain's numbered display folders. A new domain gets its own prefix so folders don't collide.
- **Documentation:** every measure has a `///` description stating the definition, the unit, and the sign or direction (what "good" looks like). Domain skills add what else the description must state.
- **Snapshots (semi-additive):** evaluate on one date (a `[Reporting Date]` / `[Status Date]` helper) with `REMOVEFILTERS('Dim Date')` + a date filter. Don't use `LASTDATE('Dim Date'[Date])` when the calendar extends into the future. Never `SUM` a snapshot across dates.
- **Role-playing dates:** use `CALCULATE ( …, USERELATIONSHIP ( Fact[Other Date], 'Dim Date'[Date] ) )`.
- **Time intelligence on flow measures only.** For snapshots and ratios, compare two dates or recompute the ratio from period-shifted parts.
- **Ratios across groups** are computed from sums (Σ numerator ÷ Σ denominator), never as averages of row-level ratios.
- **Format strings:**

  | Measure kind | Format string |
  |---|---|
  | Amounts | `#,##0` |
  | Signed amounts and variances | `#,##0;(#,##0);-` |
  | Ratios / percentages | `0.0%` |
  | Ratio deltas | `+0.0%;-0.0%;0.0%` (state "pp" in the title) |
  | Indices (SPI, CPI) | `0.00` |
  | Hours, counts | `#,0` |
  | Days | `0` or `0.0` |
  | Millions | `#,##0.0,,"M"` |

- **DAX style:**
  - Use `VAR` / `RETURN` and `DIVIDE`.
  - Use column predicates in `CALCULATE`, not `FILTER(table)`, unless the condition compares two columns.
  - Precompute row-level logic in Power Query or the source where possible.
- **Blank, not 0,** when there's no data, so visuals don't plot false zeros.
- **Colour helpers** return hex codes for field-value conditional formatting, using the status colours in `pbi-report-visuals` (favourable `#1E7A00`, watch `#D97706`, unfavourable `#C23B22`, neutral `#525355`). Always pair colour with a sign, arrow or label.

## References
- `references/calc-groups.md`: when to use calculation groups, the guard rule, the Time Intelligence template and precedence.
- Domain libraries: see the table above.
