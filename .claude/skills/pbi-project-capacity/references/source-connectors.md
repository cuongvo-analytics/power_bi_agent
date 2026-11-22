# Source connectors for project & capacity data (M)

General M rules (typing, unknown members, select columns early) are in `pbi-power-query`. This file covers only what is specific to PM tools.

## 0. Parameters and credentials
Define the parameters in `expressions.tmdl`, next to `DataFolder`:
```tmdl
expression JiraBaseUrl = "https://your-site.atlassian.net" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression AdoOrganization = "your-org" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression AdoProject = "your-project" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression ProjectServerPwaUrl = "https://projectserver.contoso.local/pwa" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression DataverseUrl = "https://your-org.crm.dynamics.com" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
```
- **Never put tokens, passwords or e-mails in M or TMDL.** Credentials are set in Power BI Desktop → Data source settings, and in the Service → semantic model → Data source credentials.
  - Jira Cloud: **Basic** (account e-mail + API token).
  - Azure DevOps Analytics: **Organizational account**, or Basic with a PAT (username blank) that has the *Analytics (read)* scope.
  - Project Server: Windows / Organizational account, through an on-premises data gateway.
  - Dataverse: Organizational account.
- **Scheduled refresh in the Service:** keep the base URL static and pass the variable parts through `RelativePath` and `Query` in `Web.Contents`. A fully concatenated URL that depends on data can't be validated by the Service and won't refresh. URLs built only from parameters, as in the `OData.Feed` calls below, are fine.
- Set privacy levels (Organizational) consistently, or combining API queries with Excel files fails with a Formula.Firewall error.
- Limit volume at the source: OData `$select` / `$filter` / `$apply`, Jira JQL with `updated >= -365d` or a project list.

## 1. Exports (CSV / Excel)

### 1.1 Jira CSV export (Filters → Export → CSV, all fields)
Jira repeats a header for multi-value fields (`Sprint`, `Sprint_1`, `Labels`, `Labels_1` after promotion). Keep the **last non-empty** sprint as the current sprint, and all of them for `Fact Sprint Commitment`.
```m
let
    Source = Csv.Document(File.Contents(DataFolder & "jira_export.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    SprintCols = List.Select(Table.ColumnNames(Promoted), each Text.StartsWith(_, "Sprint")),
    WithCurrentSprint = Table.AddColumn(Promoted, "Current Sprint", each
        List.Last(List.RemoveItems(Record.FieldValues(Record.SelectFields(_, SprintCols)), {null, ""})), type text),
    Selected = Table.SelectColumns(WithCurrentSprint,
        {"Issue key", "Summary", "Issue Type", "Status", "Status Category", "Created", "Resolved",
         "Custom field (Story point estimate)", "Current Sprint", "Project key"}, MissingField.UseNull),
    Renamed = Table.RenameColumns(Selected, {
        {"Issue key", "Work Item Id"}, {"Summary", "Title"}, {"Issue Type", "Work Item Type"},
        {"Status", "State"}, {"Status Category", "State Category"}, {"Created", "Created At"}, {"Resolved", "Resolved At"},
        {"Custom field (Story point estimate)", "Story Points"}, {"Project key", "Project Code"}}),
    // Jira CSV dates look like "05/Jan/26 10:22 AM", depending on the user profile's format: check the file and set the culture
    Typed = Table.TransformColumnTypes(Renamed, {{"Created At", type datetime}, {"Resolved At", type datetime}, {"Story Points", type number}}, "en-GB"),
    Dates = Table.TransformColumns(Typed, {{"Created At", DateTime.Date, type date}, {"Resolved At", each if _ = null then null else DateTime.Date(_), type date}}),
    Final = Table.RenameColumns(Dates, {{"Created At", "Created Date"}, {"Resolved At", "Resolved Date"}})
in
    Final
```
`Status Category` is only in the export if it's added as a column in the issue navigator. Otherwise map `State` → category through `Dim State`. CSV exports have no changelog, so `Started Date` and cycle time need the API (§2.1) or a Jira automation that stamps a "Started" date field.

### 1.2 MS Project desktop / Planner Excel export
Export with a map of Task fields: Unique ID, Name, Outline Level, Summary, Milestone, Critical, Baseline Start/Finish, Start, Finish, Actual Finish, % Work Complete, Baseline Work, Work, Actual Work, Total Slack. Load one sheet per project with the CSV-folder pattern from `pbi-power-query/references/source-patterns.md`, and add `Project Code` from the file name. Work exports as text like `"120 hrs"`, so strip the unit before typing:
```m
    WorkHours = Table.TransformColumns(Source, {{"Work", each Number.From(Text.BeforeDelimiter(Text.From(_), " ")), type number}})
```

### 1.3 Excel resource plan (wide weeks → long `Fact Demand`)
```m
let
    Source = Excel.Workbook(File.Contents(DataFolder & "resource_plan.xlsx"), null, true),
    Plan = Source{[Item = "Plan", Kind = "Table"]}[Data],
    IdCols = {"Person", "Role", "Team", "Project Code", "Demand Type", "Probability"},
    Long = Table.UnpivotOtherColumns(Plan, IdCols, "Week Label", "Planned Hours"),
    // Week headers are Monday dates; Excel may deliver them as serial numbers or text
    WithWeek = Table.AddColumn(Long, "Week Start", each
        let d = try Date.From([Week Label]) otherwise Date.From(Number.From([Week Label]))
        in Date.AddDays(d, - Date.DayOfWeek(d, Day.Monday)), type date),
    NoBlanks = Table.SelectRows(WithWeek, each [Planned Hours] <> null and [Planned Hours] <> 0),
    Typed = Table.TransformColumnTypes(NoBlanks, {{"Planned Hours", type number}, {"Probability", type number}}),
    Defaults = Table.ReplaceValue(Typed, null, 1, Replacer.ReplaceValue, {"Probability"}),
    Final = Table.RemoveColumns(Defaults, {"Week Label"})
in
    Final
```
Then merge `Person` → `Person Key` (`-1` when blank = unassigned), `Role` → `Role Key`, and `Team` → `Team Key`. If the plan is monthly in FTE, convert to weekly hours in M: FTE × Standard Weekly Hours, for each Monday in the month.

### 1.4 Capacity from people list + leave + holidays
Build `Fact Capacity` in M: cross-join active people with the Mondays between their start and end dates. Gross = Standard Weekly Hours × Contract FTE. Subtract holiday hours (holiday list by location × daily hours) and approved leave (leave export, split to working days, then grouped by week). Non-project hours = Gross × the role's `Default Non-Project %`.

## 2. APIs and OData

### 2.1 Jira Cloud REST: enhanced search with token pagination
The old `GET /rest/api/3/search` (with `startAt`) has been removed from Jira Cloud. Use `GET /rest/api/3/search/jql`. It returns `issues`, `nextPageToken` and `isLast`, and doesn't return a total count.
```m
let
    Jql = "project in (ABC, XYZ) AND updated >= -365d ORDER BY key",
    // Look up the site's custom field ids once via GET /rest/api/3/field (story points, sprint)
    Fields = "summary,issuetype,status,created,resolutiondate,project,parent,assignee,customfield_10016,customfield_10020",
    GetPage = (token as nullable text) as record =>
        let
            Query = [jql = Jql, fields = Fields, maxResults = "100"]
                & (if token = null then [] else [nextPageToken = token]),
            Response = Json.Document(Web.Contents(JiraBaseUrl, [RelativePath = "rest/api/3/search/jql", Query = Query]))
        in
            Response,
    Pages = List.Generate(
        () => GetPage(null),
        each _ <> null,
        each if Record.FieldOrDefault(_, "isLast", true) or Record.FieldOrDefault(_, "nextPageToken", null) = null
             then null else GetPage(_[nextPageToken])),
    Issues = List.Combine(List.Transform(Pages, each _[issues])),
    ToDate = (t as nullable text) as nullable date => if t = null then null else Date.FromText(Text.Start(t, 10)),
    Rows = List.Transform(Issues, (i) =>
        let f = i[fields] in [
            #"Work Item Id" = i[key],
            Title = f[summary],
            #"Work Item Type" = f[issuetype][name],
            State = f[status][name],
            #"State Category" = f[status][statusCategory][name],
            #"Created Date" = ToDate(f[created]),
            #"Resolved Date" = ToDate(f[resolutiondate]),
            #"Story Points" = Record.FieldOrDefault(f, "customfield_10016", null),
            Sprints = Record.FieldOrDefault(f, "customfield_10020", null),     // list of sprint records or null
            #"Parent Id" = if Record.FieldOrDefault(f, "parent", null) = null then null else f[parent][key],
            #"Project Code" = f[project][key]
        ]),
    AsTable = Table.FromRecords(Rows),
    Typed = Table.TransformColumnTypes(AsTable, {
        {"Work Item Id", type text}, {"Title", type text}, {"Work Item Type", type text}, {"State", type text},
        {"State Category", type text}, {"Created Date", type date}, {"Resolved Date", type date}, {"Story Points", type number}, {"Project Code", type text}})
in
    Typed
```
- **Sprints:** expand the `Sprints` list (one row per issue × sprint) into the source for `Fact Sprint Commitment` and `Dim Sprint` (`id`, `name`, `state`, `startDate`, `endDate`, `boardId`). Then drop it from the work-item query.
- **Started Date:** add `expand = "changelog"` to `Query`, then take the earliest `histories[].created` where an item has `field = "status"` and the target status is in an In Progress category. Embedded changelogs can be truncated for issues with long histories. For those, call `GET /rest/api/3/issue/{key}/changelog` (paginated) or use a "Started" date field stamped by Jira automation.
- **Watch for:** community reports describe `nextPageToken` occasionally repeating a page. Deduplicate on `Work Item Id` after combining (`Table.Distinct`), and stop after a sane page limit when testing.
- Jira Data Center / Server still uses `/rest/api/2/search` with `startAt` / `total`.

### 2.2 Azure DevOps Analytics (OData v4)
Prefer Analytics OData over the work-item REST API: it's built for reporting and returns computed lead and cycle times.
```m
// Fact Work Item
let
    Url = "https://analytics.dev.azure.com/" & AdoOrganization & "/" & AdoProject & "/_odata/v4.0-preview/WorkItems?"
        & "$select=WorkItemId,Title,WorkItemType,State,StateCategory,CreatedDate,ActivatedDate,CompletedDate,"
        & "LeadTimeDays,CycleTimeDays,StoryPoints,IterationSK,AreaSK,ParentWorkItemId"
        & "&$filter=WorkItemType in ('User Story','Product Backlog Item','Bug') and StateCategory ne 'Removed'"
        & " and ChangedDate ge 2025-01-01Z",
    Source = OData.Feed(Url, null, [Implementation = "2.0", OmitValues = ODataOmitValues.Nulls, ODataVersion = 4]),
    Dates = Table.TransformColumns(Source, {
        {"CreatedDate", each DateTimeZone.RemoveZone(_), type datetime},
        {"ActivatedDate", each if _ = null then null else DateTimeZone.RemoveZone(_), type datetime},
        {"CompletedDate", each if _ = null then null else DateTimeZone.RemoveZone(_), type datetime}}),
    AsDate = Table.TransformColumnTypes(Dates, {{"CreatedDate", type date}, {"ActivatedDate", type date}, {"CompletedDate", type date}}),
    Category = Table.AddColumn(AsDate, "State Category Std", each
        if [StateCategory] = "Proposed" then "To Do"
        else if [StateCategory] = "InProgress" or [StateCategory] = "Resolved" then "In Progress"
        else if [StateCategory] = "Completed" then "Done" else "Removed", type text)
in
    Category
```
```m
// Fact Work Item Daily, aggregated in the service (day × iteration × area × state)
let
    Url = "https://analytics.dev.azure.com/" & AdoOrganization & "/" & AdoProject & "/_odata/v4.0-preview/WorkItemSnapshot?"
        & "$apply=filter(DateSK ge 20250101 and WorkItemType in ('User Story','Bug'))"
        & "/groupby((DateSK,State,StateCategory,IterationSK,AreaSK),"
        & "aggregate($count as ItemCount, StoryPoints with sum as StoryPoints))",
    Source = OData.Feed(Url, null, [Implementation = "2.0", ODataVersion = 4]),
    WithDate = Table.AddColumn(Source, "Date", each
        #date(Number.IntegerDivide([DateSK], 10000), Number.Mod(Number.IntegerDivide([DateSK], 100), 100), Number.Mod([DateSK], 100)), type date)
in
    WithDate
```
- `Dim Sprint` comes from `Iterations?$select=IterationSK,IterationName,IterationPath,StartDate,EndDate,IsEnded`. Map teams from `Teams` / `Areas` (a team owns area paths). Derive `Sprint Order` per team with `Table.Group` + `Table.AddIndexColumn` sorted by `StartDate`.
- Field names depend on the process template (`StoryPoints` Agile, `Effort` Scrum, `Size` CMMI). Check `/_odata/v4.0-preview/$metadata`.
- Large orgs: also consider the Azure DevOps **Analytics views** connector (`VSTS.AnalyticsViews`), which gives curated views without writing OData.

### 2.3 Project Server Subscription Edition (`ProjectData` OData v3)
**Project Online was retired on 30 Sep 2026.** The same `ProjectData` service is still available in on-premises Project Server SE (through a gateway). Migrated customers use Planner premium (§2.4).
```m
let
    Source = OData.Feed(ProjectServerPwaUrl & "/_api/ProjectData/[en-us]", null, [Implementation = "2.0"]),
    Tasks = Source{[Name = "Tasks", Signature = "table"]}[Data],
    Selected = Table.SelectColumns(Tasks, {
        "ProjectId", "TaskId", "ParentTaskId", "TaskName", "TaskOutlineLevel", "TaskIsSummary", "TaskIsMilestone", "TaskIsCritical",
        "TaskBaselineStartDate", "TaskBaselineFinishDate", "TaskStartDate", "TaskFinishDate", "TaskActualFinishDate",
        "TaskPercentCompleted", "TaskBaselineWork", "TaskWork", "TaskActualWork", "TaskTotalSlack",
        "TaskBCWS", "TaskBCWP", "TaskACWP"}, MissingField.UseNull)
in
    Selected
```
- Time-phased EVM per week: `AssignmentTimephasedDataSet` (`TimeByDay`, `AssignmentBaselineCost`, `AssignmentActualCost`, `AssignmentBaselineWork`, `AssignmentActualWork`). Filter at source to keep it small (`?$filter=TimeByDay ge datetime'2025-01-01T00:00:00'`), then group by project and Monday.
- Timesheets: `TimesheetLineActualDataSet` (`TimeByDay`, `ActualWorkBillable`, `ActualWorkNonBillable`) joined to `TimesheetLines` for project and resource.
- Check names in `/_api/ProjectData/[en-us]/$metadata` (custom fields appear with their display names).

### 2.4 Planner premium plans (Dataverse)
Premium plans (formerly Project for the web) store data in Dataverse tables. Use the **Dataverse** connector (`CommonDataService.Database(DataverseUrl)` for TDS/DirectQuery-capable access, or the `Dataverse` connector in Desktop) and select `msdyn_project`, `msdyn_projecttask`, `msdyn_resourceassignment`, `bookableresource` and `msdyn_projectteam`. Choice and lookup columns arrive as ids, so join `*name` columns or the lookup tables. Verify column names in the maker portal's table designer. Baselines aren't available as stable columns, so snapshot `msdyn_projecttask` weekly (dataflow or Fabric) to measure slippage.

Basic Planner plans have no Power BI connector. Use Export to Excel, or a Power Automate flow that writes tasks to a SharePoint list / Dataverse, and read that.
