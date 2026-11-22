# Project & capacity measure library

All measures go in `_Measures`, in the folders below. The `P` prefix keeps them apart from the treasury folders `1.`–`9.`. Table and column names follow `model-patterns.md`. Every measure gets a `///` description (definition + unit + view), a `formatString`, a `displayFolder` and a fresh `lineageTag` (see `pbip-format/references/tmdl-syntax.md`).

TMDL shape, for example:
```tmdl
	/// Schedule Performance Index = cumulative EV ÷ cumulative PV at the selected date (capped at the EVM status date). < 1 = behind schedule. Portfolio value is Σ EV ÷ Σ PV.
	measure SPI = DIVIDE ( [EV Cumulative], [PV Cumulative] )
		formatString: 0.00
		displayFolder: P2. Earned Value
		lineageTag: <guid>
```

Format strings: hours `#,0`; currency `#,0;(#,0);-`; ratios (SPI, CPI, TCPI) `0.00`; percentages `0.0%`; days `0.0`; counts `#,0`.

## P9. Helpers (hidden unless stated)
```dax
// "As of" date for snapshots and WIP: end of the selected period, never in the future (visible)
Status Date = MIN ( TODAY (), MAX ( 'Dim Date'[Date] ) )

// Last week with actual cost booked: EV and AC stop here on the S-curve
EVM Status Date =
CALCULATE ( MAX ( 'Fact EVM Period'[Week Start] ), REMOVEFILTERS ( 'Dim Date' ), NOT ISBLANK ( 'Fact EVM Period'[AC] ) )

// Mondays in the current filter context = number of weeks
Weeks In Context = COUNTROWS ( FILTER ( VALUES ( 'Dim Date'[Date] ), WEEKDAY ( 'Dim Date'[Date], 2 ) = 1 ) )

// Company standard week; replace with the agreed value (or a What-if parameter)
Standard Weekly Hours = 40

// Colours: return hex for conditional formatting (Format → field value)
RAG Color =
SWITCH ( SELECTEDVALUE ( 'Dim Project'[Health RAG] ),
    "Green", "#1A7F5A", "Amber", "#D97706", "Red", "#C23B22", "#6B7280" )

SPI Color =
VAR _v = [SPI]
RETURN SWITCH ( TRUE (), ISBLANK ( _v ), "#6B7280", _v >= 0.95, "#1A7F5A", _v >= 0.90, "#D97706", "#C23B22" )

CPI Color =
VAR _v = [CPI]
RETURN SWITCH ( TRUE (), ISBLANK ( _v ), "#6B7280", _v >= 0.95, "#1A7F5A", _v >= 0.90, "#D97706", "#C23B22" )

Allocation Color =
VAR _a = [Allocation %]
RETURN SWITCH ( TRUE (), ISBLANK ( _a ), "#6B7280", _a > 1, "#C23B22", _a < 0.7, "#D97706", "#1A7F5A" )
```

## P1. Schedule (`Fact Task`, summary tasks excluded)
```dax
Tasks = CALCULATE ( COUNTROWS ( 'Fact Task' ), 'Fact Task'[Is Summary] = FALSE () )

Milestones = CALCULATE ( [Tasks], 'Fact Task'[Is Milestone] = TRUE () )

Milestones Completed = CALCULATE ( [Milestones], NOT ISBLANK ( 'Fact Task'[Actual Finish] ) )

Milestones On Time =
COUNTROWS (
    FILTER ( 'Fact Task',
        'Fact Task'[Is Milestone] && NOT 'Fact Task'[Is Summary]
            && NOT ISBLANK ( 'Fact Task'[Actual Finish] )
            && 'Fact Task'[Actual Finish] <= 'Fact Task'[Baseline Finish] ) )

Milestones On Time % = DIVIDE ( [Milestones On Time], [Milestones Completed] )

// Average finish variance in calendar days (positive = late), tasks with a baseline
Avg Slippage Days =
AVERAGEX (
    FILTER ( 'Fact Task', NOT 'Fact Task'[Is Summary] && NOT ISBLANK ( 'Fact Task'[Baseline Finish] ) ),
    INT ( 'Fact Task'[Finish] - 'Fact Task'[Baseline Finish] ) )

Max Slippage Days =
MAXX (
    FILTER ( 'Fact Task', NOT 'Fact Task'[Is Summary] && NOT ISBLANK ( 'Fact Task'[Baseline Finish] ) ),
    INT ( 'Fact Task'[Finish] - 'Fact Task'[Baseline Finish] ) )

Late Tasks =
COUNTROWS (
    FILTER ( 'Fact Task',
        NOT 'Fact Task'[Is Summary] && ISBLANK ( 'Fact Task'[Actual Finish] )
            && 'Fact Task'[Finish] > 'Fact Task'[Baseline Finish] ) )

// Not complete but forecast finish already in the past: schedule not maintained
Overdue Tasks =
VAR _s = [Status Date]
RETURN
    CALCULATE (
        COUNTROWS ( FILTER ( 'Fact Task',
            NOT 'Fact Task'[Is Summary] && ISBLANK ( 'Fact Task'[Actual Finish] ) && 'Fact Task'[Finish] < _s ) ),
        REMOVEFILTERS ( 'Dim Date' ) )

Work % Complete =
CALCULATE (
    DIVIDE ( SUM ( 'Fact Task'[Actual Work Hours] ), SUM ( 'Fact Task'[Work Hours] ) ),
    'Fact Task'[Is Summary] = FALSE () )

// Milestones by forecast finish month instead of baseline month
Milestones By Forecast = CALCULATE ( [Milestones], USERELATIONSHIP ( 'Fact Task'[Finish], 'Dim Date'[Date] ) )
```
The active date relationship is on `Baseline Finish`, so a month filter means "due in that month per baseline".

## P2. Earned Value (`Fact EVM Period`, cost in reporting currency or hours)
```dax
PV = SUM ( 'Fact EVM Period'[PV] )        // period amounts
EV = SUM ( 'Fact EVM Period'[EV] )
AC = SUM ( 'Fact EVM Period'[AC] )

BAC = CALCULATE ( [PV], REMOVEFILTERS ( 'Dim Date' ) )

PV Cumulative =
VAR _d = MAX ( 'Dim Date'[Date] )
RETURN CALCULATE ( [PV], REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] <= _d )

EV Cumulative =
VAR _d = MIN ( MAX ( 'Dim Date'[Date] ), [EVM Status Date] )
RETURN
    IF ( MIN ( 'Dim Date'[Date] ) <= [EVM Status Date],
        CALCULATE ( [EV], REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] <= _d ) )

AC Cumulative =
VAR _d = MIN ( MAX ( 'Dim Date'[Date] ), [EVM Status Date] )
RETURN
    IF ( MIN ( 'Dim Date'[Date] ) <= [EVM Status Date],
        CALCULATE ( [AC], REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] <= _d ) )

SV = [EV Cumulative] - [PV Cumulative]
CV = [EV Cumulative] - [AC Cumulative]
SPI = DIVIDE ( [EV Cumulative], [PV Cumulative] )
CPI = DIVIDE ( [EV Cumulative], [AC Cumulative] )

EAC = DIVIDE ( [BAC], [CPI] )                                   // default: CPI method

EAC CPI x SPI =
VAR _cpi = [CPI]
VAR _spi = [SPI]
RETURN [AC Cumulative] + DIVIDE ( [BAC] - [EV Cumulative], _cpi * _spi )

ETC = [EAC] - [AC Cumulative]
VAC = [BAC] - [EAC]
TCPI = DIVIDE ( [BAC] - [EV Cumulative], [BAC] - [AC Cumulative] )
EV % Complete = DIVIDE ( [EV Cumulative], [BAC] )
AC % Spent = DIVIDE ( [AC Cumulative], [BAC] )
```
On the S-curve, use a continuous `Week Start` axis with `PV Cumulative`, `EV Cumulative` and `AC Cumulative`. EV and AC return blank after the status date, so their lines stop there.

## P3. Agile Delivery (`Fact Sprint Commitment`, `Fact Work Item Daily`, `Dim Sprint`)
```dax
Committed Points = SUM ( 'Fact Sprint Commitment'[Committed Points] )
Added Points = SUM ( 'Fact Sprint Commitment'[Added Points] )
Removed Points = SUM ( 'Fact Sprint Commitment'[Removed Points] )
Completed Points = SUM ( 'Fact Sprint Commitment'[Completed Points] )    // = velocity in sprint context
Say Do % = DIVIDE ( SUM ( 'Fact Sprint Commitment'[Completed Committed Points] ), [Committed Points] )
Scope Change % = DIVIDE ( [Added Points] - [Removed Points], [Committed Points] )

// Average completed points of the last 3 closed sprints of ONE team, up to the sprint in context
Rolling Velocity 3 =
VAR _team = SELECTEDVALUE ( 'Dim Sprint'[Team Key] )
VAR _order = MAX ( 'Dim Sprint'[Sprint Order] )
RETURN
    IF ( NOT ISBLANK ( _team ),
        CALCULATE (
            AVERAGEX ( VALUES ( 'Dim Sprint'[Sprint Key] ), [Completed Points] ),
            REMOVEFILTERS ( 'Dim Sprint' ),
            'Dim Sprint'[Team Key] = _team,
            'Dim Sprint'[Sprint Order] <= _order,
            'Dim Sprint'[Sprint Order] > _order - 3,
            'Dim Sprint'[Sprint State] = "Closed" ) )

// Burndown (daily axis): open points on the date, snapshot
Remaining Points =
VAR _d = MAX ( 'Dim Date'[Date] )
RETURN
    IF ( _d <= [Status Date],
        CALCULATE ( SUM ( 'Fact Work Item Daily'[Story Points] ),
            REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d,
            'Dim State'[State Category] IN { "To Do", "In Progress" } ) )

// Ideal line: committed points burned evenly over the sprint's working days (one sprint in context)
Ideal Remaining Points =
VAR _start = MIN ( 'Dim Sprint'[Start Date] )
VAR _end = MAX ( 'Dim Sprint'[End Date] )
VAR _d = MAX ( 'Dim Date'[Date] )
VAR _total = CALCULATE ( COUNTROWS ( 'Dim Date' ), DATESBETWEEN ( 'Dim Date'[Date], _start, _end ), 'Dim Date'[Is Working Day] = TRUE () )
VAR _elapsed = CALCULATE ( COUNTROWS ( 'Dim Date' ), DATESBETWEEN ( 'Dim Date'[Date], _start, _d ), 'Dim Date'[Is Working Day] = TRUE () )
RETURN
    IF ( HASONEVALUE ( 'Dim Sprint'[Sprint Key] ) && _d >= _start && _d <= _end,
        [Committed Points] * ( 1 - DIVIDE ( _elapsed, _total ) ) )

// Burnup: cumulative completed and total scope on the date
Completed Points To Date =
VAR _d = MAX ( 'Dim Date'[Date] )
RETURN
    IF ( _d <= [Status Date],
        CALCULATE ( SUM ( 'Fact Work Item Daily'[Story Points] ),
            REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d, 'Dim State'[State Category] = "Done" ) )

Total Scope Points =
VAR _d = MAX ( 'Dim Date'[Date] )
RETURN
    IF ( _d <= [Status Date],
        CALCULATE ( SUM ( 'Fact Work Item Daily'[Story Points] ),
            REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d, 'Dim State'[State Category] <> "Removed" ) )
```
`Remaining Points` and the burnup measures need `Fact Work Item Daily` to keep Done items on later days (snapshot every item every day until sprint/release end). If the snapshot drops closed items, burnup can't be built from it. Use `Fact Work Item[Resolved Date]` cumulatively instead.

## P4. Flow (`Fact Work Item`, `Fact Work Item Daily`)
```dax
Items Created = CALCULATE ( COUNTROWS ( 'Fact Work Item' ), 'Dim State'[State Category] <> "Removed" )

Throughput =
CALCULATE ( COUNTROWS ( 'Fact Work Item' ),
    USERELATIONSHIP ( 'Fact Work Item'[Resolved Date], 'Dim Date'[Date] ),
    NOT ISBLANK ( 'Fact Work Item'[Resolved Date] ),
    'Dim State'[State Category] = "Done" )

Throughput Per Week = DIVIDE ( [Throughput], [Weeks In Context] )

Cycle Time Avg Days =
CALCULATE ( AVERAGE ( 'Fact Work Item'[Cycle Time Days] ),
    USERELATIONSHIP ( 'Fact Work Item'[Resolved Date], 'Dim Date'[Date] ) )

Cycle Time P50 Days =
CALCULATE (
    PERCENTILEX.INC ( FILTER ( 'Fact Work Item', NOT ISBLANK ( 'Fact Work Item'[Cycle Time Days] ) ), 'Fact Work Item'[Cycle Time Days], 0.50 ),
    USERELATIONSHIP ( 'Fact Work Item'[Resolved Date], 'Dim Date'[Date] ) )

Cycle Time P85 Days =
CALCULATE (
    PERCENTILEX.INC ( FILTER ( 'Fact Work Item', NOT ISBLANK ( 'Fact Work Item'[Cycle Time Days] ) ), 'Fact Work Item'[Cycle Time Days], 0.85 ),
    USERELATIONSHIP ( 'Fact Work Item'[Resolved Date], 'Dim Date'[Date] ) )

Lead Time P85 Days =
CALCULATE (
    PERCENTILEX.INC ( FILTER ( 'Fact Work Item', NOT ISBLANK ( 'Fact Work Item'[Lead Time Days] ) ), 'Fact Work Item'[Lead Time Days], 0.85 ),
    USERELATIONSHIP ( 'Fact Work Item'[Resolved Date], 'Dim Date'[Date] ) )

// Items in progress on the status date (snapshot)
WIP =
VAR _d = [Status Date]
RETURN CALCULATE ( COUNTROWS ( 'Fact Work Item Daily' ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d, 'Dim State'[State Category] = "In Progress" )

// CFD: put State Category (sorted by State Order) in the legend, Date on the axis
CFD Items =
VAR _d = MAX ( 'Dim Date'[Date] )
RETURN IF ( _d <= [Status Date], CALCULATE ( COUNTROWS ( 'Fact Work Item Daily' ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d ) )

// Average age of items in progress at the status date
Ageing WIP Days =
VAR _s = [Status Date]
RETURN
    CALCULATE (
        AVERAGEX (
            FILTER ( 'Fact Work Item',
                NOT ISBLANK ( 'Fact Work Item'[Started Date] ) && 'Fact Work Item'[Started Date] <= _s
                    && ( ISBLANK ( 'Fact Work Item'[Resolved Date] ) || 'Fact Work Item'[Resolved Date] > _s ) ),
            INT ( _s - 'Fact Work Item'[Started Date] ) ),
        REMOVEFILTERS ( 'Dim Date' ) )
```
With the aggregated daily grain (day × team × sprint × state with an `Item Count` column), replace `COUNTROWS ( 'Fact Work Item Daily' )` with `SUM ( 'Fact Work Item Daily'[Item Count] )`.

## P5. Capacity & Demand (`Fact Capacity`, `Fact Demand`, weekly hours)
```dax
Gross Hours = SUM ( 'Fact Capacity'[Gross Hours] )
Available Hours = SUM ( 'Fact Capacity'[Available Hours] )
Leave Hours = SUM ( 'Fact Capacity'[Leave Hours] ) + SUM ( 'Fact Capacity'[Holiday Hours] )

Allocated Hours = CALCULATE ( SUM ( 'Fact Demand'[Planned Hours] ), 'Fact Demand'[Demand Type] = "Allocated" )
Unassigned Demand Hours = CALCULATE ( SUM ( 'Fact Demand'[Planned Hours] ), 'Fact Demand'[Demand Type] = "Unassigned" )
Pipeline Hours Weighted =
SUMX ( FILTER ( 'Fact Demand', 'Fact Demand'[Demand Type] = "Pipeline" ),
    'Fact Demand'[Planned Hours] * 'Fact Demand'[Probability] )

Demand Hours = [Allocated Hours] + [Unassigned Demand Hours] + [Pipeline Hours Weighted]

// + spare capacity / − shortfall
Capacity Gap Hours = [Available Hours] - [Demand Hours]

Allocation % = DIVIDE ( [Allocated Hours], [Available Hours] )
Demand vs Capacity % = DIVIDE ( [Demand Hours], [Available Hours] )

Available FTE = DIVIDE ( [Available Hours], [Standard Weekly Hours] * [Weeks In Context] )
Demand FTE = DIVIDE ( [Demand Hours], [Standard Weekly Hours] * [Weeks In Context] )
Capacity Gap FTE = DIVIDE ( [Capacity Gap Hours], [Standard Weekly Hours] * [Weeks In Context] )

// Person-weeks above 100 % allocation (evaluated per person and week, not on period totals)
Over-allocated Person Weeks =
COUNTROWS (
    FILTER (
        CROSSJOIN ( VALUES ( 'Dim Person'[Person Key] ), FILTER ( VALUES ( 'Dim Date'[Date] ), WEEKDAY ( 'Dim Date'[Date], 2 ) = 1 ) ),
        [Allocated Hours] > [Available Hours] && [Available Hours] > 0 ) )

Over-allocated People =
COUNTROWS (
    FILTER ( VALUES ( 'Dim Person'[Person Key] ),
        'Dim Person'[Person Key] <> -1 && [Over-allocated Person Weeks] > 0 ) )

// Unused hours, summed per person-week so one person's overload doesn't hide another's bench
Bench Hours =
SUMX (
    CROSSJOIN ( VALUES ( 'Dim Person'[Person Key] ), FILTER ( VALUES ( 'Dim Date'[Date] ), WEEKDAY ( 'Dim Date'[Date], 2 ) = 1 ) ),
    MAX ( 0, [Available Hours] - [Allocated Hours] ) )
```
Role-level gap: put `Dim Role[Role Name]` on rows. Unassigned demand carries `Role Key`, so it shows against the right role even without a person.

## P6. Utilisation (`Fact Timesheet` against `Fact Capacity`)
```dax
Booked Hours = CALCULATE ( SUM ( 'Fact Timesheet'[Hours] ), 'Fact Timesheet'[Approval Status] = "Approved" )
Project Hours = CALCULATE ( [Booked Hours], 'Fact Timesheet'[Is Project Time] = TRUE () )
Billable Hours = CALCULATE ( [Booked Hours], 'Fact Timesheet'[Is Billable] = TRUE () )

Utilisation % = DIVIDE ( [Project Hours], [Available Hours] )
Billable Utilisation % = DIVIDE ( [Billable Hours], [Available Hours] )
Billable Mix % = DIVIDE ( [Billable Hours], [Booked Hours] )

// Target weighted by each person's available hours
Utilisation Target % =
DIVIDE (
    SUMX ( VALUES ( 'Dim Person'[Person Key] ), [Available Hours] * CALCULATE ( MAX ( 'Dim Person'[Utilisation Target %] ) ) ),
    [Available Hours] )

Utilisation vs Target = [Utilisation %] - [Utilisation Target %]

Expected Timesheet Hours = [Gross Hours] - [Leave Hours]
Timesheet Compliance % = DIVIDE ( [Booked Hours], [Expected Timesheet Hours] )

// Actual vs plan per project/week: + booked more than allocated
Plan Variance Hours = [Project Hours] - [Allocated Hours]
```
Variance colouring: `Utilisation vs Target` ≥ 0 is favourable. `Plan Variance Hours` is neutral by default (over-booking may be good or bad), so agree it with the user.
