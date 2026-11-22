# Calculation groups

## When to use
- **Use them** when the same transformation applies to many measures: period logic (MTD/YTD/PY), comparison with a baseline or scenario, or a unit/currency switch.
- **Skip them** when there are only a few measures, or when users analyse in Excel or Q&A.
- The model must have `discourageImplicitMeasures` in `model.tmdl`.

## The guard rule
A calculation group applies to **every** measure in the visual. Some measures must not be transformed:
- **Snapshot** measures (balances, remaining work, WIP, headcount): MTD/YTD of a snapshot is meaningless.
- **Ratios and day counts** (%, SPI/CPI, cycle-time percentiles, days): a ratio must be recomputed from its transformed parts, not wrapped.

Each item starts with a guard that returns `SELECTEDMEASURE()` unchanged for those measures. Keep the guard list in sync with the measure library. `ISSELECTEDMEASURE` errors on a name that doesn't exist in the model.

Domain-specific guard lists and groups:
- Treasury: `pbi-treasury-liquidity/references/calc-groups.md` (Time Intelligence on cash flows, Stress Comparison vs BASE, Currency View).
- Project & capacity: hours and points are additive flows and can take Time Intelligence. Guard `P1` counts, all ratios, and the `P3`/`P4` snapshot measures (`Remaining Points`, `WIP`, `CFD Items`, `Ageing WIP Days`).

## Time Intelligence template (tables/Time Intelligence.tmdl)
Replace `<guarded measures>` with the snapshot and ratio measures of the model, and `"12-31"` with the fiscal year-end if needed.
```tmdl
/// Period logic for flow measures. Snapshot and ratio measures are passed through unchanged.
table 'Time Intelligence'
	lineageTag: <guid>

	calculationGroup
		precedence: 20

		calculationItem Current = SELECTEDMEASURE()
			ordinal: 0

		calculationItem MTD =
				IF ( ISSELECTEDMEASURE ( <guarded measures> ),
				     SELECTEDMEASURE (),
				     CALCULATE ( SELECTEDMEASURE (), DATESMTD ( 'Dim Date'[Date] ) ) )
			ordinal: 1

		calculationItem QTD =
				IF ( ISSELECTEDMEASURE ( <guarded measures> ),
				     SELECTEDMEASURE (),
				     CALCULATE ( SELECTEDMEASURE (), DATESQTD ( 'Dim Date'[Date] ) ) )
			ordinal: 2

		calculationItem YTD =
				IF ( ISSELECTEDMEASURE ( <guarded measures> ),
				     SELECTEDMEASURE (),
				     CALCULATE ( SELECTEDMEASURE (), DATESYTD ( 'Dim Date'[Date], "12-31" ) ) )
			ordinal: 3

		calculationItem PY = CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( 'Dim Date'[Date] ) )
			ordinal: 4

		calculationItem 'YoY %' =
				VAR _cur = SELECTEDMEASURE ()
				VAR _py = CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( 'Dim Date'[Date] ) )
				RETURN DIVIDE ( _cur - _py, ABS ( _py ) )
			ordinal: 5

			formatStringDefinition = "0.0%"
```
`PY` needs no guard when snapshot measures pick their date from the filter context (shifting the filter moves the snapshot date back a year).

Calc-group columns (`'Time Calc'` sourced from `Name` and sorted by `Ordinal`) and the `partition … = calculationGroup` block are the same as in `pbip-format/references/tmdl-syntax.md`.

## Precedence
A higher `precedence` is applied first, i.e. outermost. Use Time Intelligence = 20, comparison groups (scenario / baseline) = 10, and unit or currency switches = 5. Then "YTD Δ vs Base" applies the comparison inside the YTD window.

## Using them in visuals
- Put the calc-group column on matrix **Columns**, with base measures in **Values**.
- Alternatively, filter a card to one item.

In PBIR the column is a normal `Column` reference, e.g. Entity `Time Intelligence`, Property `Time Calc`.
