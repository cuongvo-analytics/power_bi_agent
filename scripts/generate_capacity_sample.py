#!/usr/bin/env python
"""Generate the synthetic capacity planning demo dataset (capacity, demand, timesheets) as star-schema CSVs.

Synthetic data for demonstrating the powerbi-developer agent: ~40 people in 4 teams and 6 roles,
12 projects, weekly capacity and demand (26 weeks of history + 13 weeks ahead of the status date)
and daily timesheets for the history weeks. Hours are the base unit; weeks start on Monday.

    python scripts/generate_capacity_sample.py [--seed 42] [--out data/capacity_planning_sample]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd

STATUS_DATE = pd.Timestamp("2026-11-20")               # Friday; history = weeks up to the one containing it
CURRENT_WEEK = STATUS_DATE - pd.Timedelta(days=STATUS_DATE.weekday())
HIST_WEEKS = pd.date_range(end=CURRENT_WEEK, periods=26, freq="7D")
FUT_WEEKS = pd.date_range(CURRENT_WEEK + pd.Timedelta(days=7), periods=13, freq="7D")
ALL_WEEKS = HIST_WEEKS.append(FUT_WEEKS)
DAY_HOURS = 8.0
STD_WEEK = 40.0


def week_n(n: int) -> pd.Timestamp:
    """Week +n after the status week (+1 = first future week)."""
    return CURRENT_WEEK + pd.Timedelta(days=7 * n)


TEAMS = [(1, "Data & Analytics", "Technology", "Head of Data"), (2, "Platform", "Technology", "Head of Platform"),
         (3, "Application Development", "Technology", "Head of Applications"), (4, "PMO", "Change", "Head of PMO")]
ROLES = [  # key, name, family, seniority, default non-project %, cost rate (USD/h)
    (1, "Data Engineer", "Data", "Mid", 0.10, 95), (2, "BI Developer", "Data", "Mid", 0.10, 85),
    (3, "Software Engineer", "Engineering", "Mid", 0.10, 90), (4, "Business Analyst", "Business", "Mid", 0.15, 80),
    (5, "Project Manager", "Delivery", "Senior", 0.20, 110), (6, "QA Engineer", "Engineering", "Mid", 0.10, 70),
]
ROLE = {r[0]: r for r in ROLES}

# (team, role, count)
HEADCOUNT = [(1, 1, 5), (1, 2, 5), (1, 4, 2), (2, 3, 6), (2, 1, 2), (2, 6, 2), (3, 3, 7), (3, 6, 2), (3, 4, 2),
             (4, 5, 4), (4, 4, 2)]

PROJECTS = [  # key, code, name, portfolio, methodology, status, rag, is_pipeline, probability, billable, start, finish
    (1, "P01", "Liquidity Data Platform", "Data", "Agile", "Active", "Green", 0, 1.0, 1, "2026-03-02", "2027-03-26"),
    (2, "P02", "Customer 360", "Data", "Agile", "Active", "Amber", 0, 1.0, 1, "2026-01-12", "2027-02-26"),
    (3, "P03", "Core Banking Upgrade", "Infrastructure", "Waterfall", "Active", "Red", 0, 1.0, 0, "2025-09-01", "2027-06-30"),
    (4, "P04", "Mobile App Release 5", "Digital", "Agile", "Active", "Green", 0, 1.0, 1, "2026-06-01", "2026-12-18"),
    (5, "P05", "Cloud Migration Wave 2", "Infrastructure", "Hybrid", "Active", "Amber", 0, 1.0, 0, "2026-04-06", "2027-03-31"),
    (6, "P06", "Finance Dashboard Refresh", "Data", "Agile", "Active", "Green", 0, 1.0, 1, "2026-07-06", "2026-12-18"),
    (7, "P07", "Payments Modernisation", "Change", "Waterfall", "Active", "Amber", 0, 1.0, 1, "2026-02-02", "2027-05-28"),
    (8, "P08", "Data Governance Programme", "Data", "Hybrid", "Active", "Green", 0, 1.0, 0, "2026-05-04", "2027-03-31"),
    (9, "P09", "Risk Model Automation", "Data", "Agile", "Not started", "Green", 0, 1.0, 1, "2026-12-07", "2027-04-30"),
    (10, "P10", "HR Self-Service Portal", "Digital", "Agile", "Completed", "Green", 0, 1.0, 0, "2026-03-02", "2026-09-30"),
    (11, "P11", "AI Analytics Pilot", "Data", "Agile", "Pipeline", "", 1, 0.7, 1, "2026-12-28", "2027-03-31"),
    (12, "P12", "Branch Network Analytics", "Data", "Agile", "Pipeline", "", 1, 0.4, 1, "2027-01-18", "2027-03-31"),
]
PROJ = {p[0]: p for p in PROJECTS}

# candidate projects (weights) per (team, role); total project share per (team, role)
CANDIDATES = {
    (1, 1): {1: 3, 2: 2, 8: 2}, (2, 1): {5: 3, 8: 1}, (1, 2): {1: 2, 2: 2, 6: 3}, (1, 4): {2: 2, 6: 1, 8: 2},
    (2, 3): {5: 3, 3: 1}, (2, 6): {5: 2, 3: 1}, (3, 3): {3: 2, 4: 2, 7: 2, 10: 2}, (3, 6): {3: 1, 4: 2, 7: 1, 10: 1},
    (3, 4): {7: 3, 3: 1}, (4, 4): {7: 2, 8: 1}, (4, 5): {1: 1, 2: 1, 3: 1, 5: 1, 7: 1, 8: 1},
}
BASE_SHARE = {1: 0.90, 2: 0.90, 3: 0.85, 4: 0.80, 5: 0.75, 6: 0.80}
PLATFORM_SHARE = 0.62      # Platform team is under-utilised

HOLIDAYS = [  # illustrative public holidays per location
    ("London", "2026-05-25", "Spring bank holiday"), ("London", "2026-08-31", "Summer bank holiday"),
    ("London", "2026-12-25", "Christmas Day"), ("London", "2026-12-28", "Boxing Day (substitute)"),
    ("London", "2027-01-01", "New Year's Day"),
    ("Singapore", "2026-06-01", "Vesak Day (observed)"), ("Singapore", "2026-08-10", "National Day (observed)"),
    ("Singapore", "2026-11-09", "Deepavali (observed)"), ("Singapore", "2026-12-25", "Christmas Day"),
    ("Singapore", "2027-01-01", "New Year's Day"), ("Singapore", "2027-02-08", "Chinese New Year"),
    ("Singapore", "2027-02-09", "Chinese New Year"),
]

FIRST = ["Alex", "Priya", "Wei", "Sam", "Nadia", "Tom", "Mei", "Arjun", "Chloe", "Daniel", "Hana", "Ravi", "Sofia", "Ben",
         "Lina", "Omar", "Grace", "Kenji", "Maya", "Ethan", "Aisha", "Lucas", "Ying", "Noah", "Zara", "Ivan", "Elena",
         "Marcus", "Farah", "Leo", "Ana", "Jun", "Isla", "Kiran", "Ruth", "Hugo", "Siti", "Jonah", "Tara", "Felix"]
LAST = ["Tan", "Smith", "Kumar", "Lim", "Patel", "Brown", "Wong", "Garcia", "Ng", "Taylor", "Chen", "Davies", "Rahman",
        "Wilson", "Lee", "Evans", "Nair", "Martin", "Goh", "Clarke", "Ong", "Hughes", "Singh", "Walker", "Teo", "Morris"]


# ---------------------------------------------------------------- people
def make_people(rng):
    names = set()
    rows, key = [], 0
    for team, role, count in HEADCOUNT:
        for i in range(count):
            key += 1
            while True:
                name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
                if name not in names:
                    names.add(name)
                    break
            fte = 1.0 if rng.random() > 0.12 else float(rng.choice([0.6, 0.8]))
            util_target = {5: 0.70, 4: 0.75}.get(role, 0.80)
            rows.append({"person_key": key, "person_name": name, "team_key_hist": team, "role_key": role,
                         "location": "Singapore" if rng.random() < 0.6 else "London",
                         "employment_type": "Contractor" if rng.random() < 0.15 else "Permanent",
                         "contract_fte": fte, "standard_weekly_hours": STD_WEEK, "cost_rate": ROLE[role][5],
                         "utilisation_target_pct": util_target, "billable_target_pct": round(util_target - 0.2, 2),
                         "start_date": pd.Timestamp("2024-01-01"), "end_date": pd.NaT, "move_date": pd.NaT, "new_team": None})
    # storyline: a BI joiner in week +3, a Platform data engineer who moves team, an app-dev leaver
    rows.append({"person_key": key + 1, "person_name": "Ines Moreau", "team_key_hist": 1, "role_key": 2,
                 "location": "London", "employment_type": "Permanent", "contract_fte": 1.0,
                 "standard_weekly_hours": STD_WEEK, "cost_rate": ROLE[2][5], "utilisation_target_pct": 0.8,
                 "billable_target_pct": 0.6, "start_date": week_n(3), "end_date": pd.NaT,
                 "move_date": pd.NaT, "new_team": None})
    people = pd.DataFrame(rows)
    mover = people[(people.team_key_hist == 2) & (people.role_key == 1)].index[0]
    people.loc[mover, ["move_date", "new_team"]] = [pd.Timestamp("2026-09-07"), 1]
    leaver = people[(people.team_key_hist == 3) & (people.role_key == 3)].index[-1]
    people.loc[leaver, "end_date"] = pd.Timestamp("2026-12-31")
    return people


def team_on(p, day):
    if pd.notna(p.move_date) and day >= p.move_date:
        return int(p.new_team)
    return int(p.team_key_hist)


def make_leave(rng, people):
    """Approved leave days per person (working days)."""
    leave = {}
    for p in people.itertuples():
        days = set()
        if rng.random() < 0.75:   # summer block, London mostly in August
            month_start = pd.Timestamp("2026-08-03") if p.location == "London" or rng.random() < 0.4 else pd.Timestamp("2026-06-15")
            start = month_start + pd.Timedelta(days=int(rng.integers(0, 20)))
            days |= set(pd.bdate_range(start, periods=int(rng.integers(5, 11))))
        if rng.random() < 0.6:    # year-end block
            start = pd.Timestamp("2026-12-21") + pd.Timedelta(days=int(rng.integers(0, 4)))
            days |= set(pd.bdate_range(start, periods=int(rng.integers(3, 6))))
        for _ in range(int(rng.integers(2, 6))):  # single days
            days.add(pd.bdate_range(ALL_WEEKS[0], ALL_WEEKS[-1] + pd.Timedelta(days=4))[int(rng.integers(0, 190))])
        leave[p.person_key] = days
    return leave


# ---------------------------------------------------------------- facts
def make_capacity(people, leave, holidays):
    hol = {(h.location, h.date) for h in holidays.itertuples()}
    rows = []
    for p in people.itertuples():
        for w in ALL_WEEKS:
            days = pd.bdate_range(w, periods=5)
            emp = [d for d in days if d >= p.start_date and (pd.isna(p.end_date) or d <= p.end_date)]
            if not emp:
                continue
            day_h = DAY_HOURS * p.contract_fte
            n_hol = sum((p.location, d) in hol for d in emp)
            n_leave = sum(d in leave[p.person_key] and (p.location, d) not in hol for d in emp)
            gross = day_h * len(emp)
            hol_h, leave_h = day_h * n_hol, day_h * n_leave
            non_proj = (gross - hol_h - leave_h) * ROLE[p.role_key][4]
            rows.append({"person_key": p.person_key, "team_key": team_on(p, w), "role_key": p.role_key, "week_start": w,
                         "gross_hours": gross, "holiday_hours": hol_h, "leave_hours": leave_h,
                         "non_project_hours": round(non_proj, 2), "available_hours": round(gross - hol_h - leave_h - non_proj, 2)})
    return pd.DataFrame(rows)


def active(project_key, w):
    p = PROJ[project_key]
    return pd.Timestamp(p[10]) <= w + pd.Timedelta(days=4) and w <= pd.Timestamp(p[11])


def person_shares(rng, people):
    """Project share of available hours per person × week (planned allocation)."""
    shares = {}
    for p in people.itertuples():
        weights = {k: v * rng.uniform(0.7, 1.3) for k, v in CANDIDATES[(p.team_key_hist, p.role_key)].items()}
        for w in ALL_WEEKS:
            team = team_on(p, w)
            cands = CANDIDATES[(team, p.role_key)] if team != p.team_key_hist else weights
            act = {k: v for k, v in cands.items() if active(k, w)}
            total = PLATFORM_SHARE if team == 2 else BASE_SHARE[p.role_key]
            alloc = {k: total * v / sum(act.values()) for k, v in act.items()} if act else {}
            if p.role_key == 1 and team == 1 and active(9, w):          # Risk Model Automation lands on data engineers
                alloc[9] = 0.30 if w <= week_n(8) else 0.10
            if p.role_key == 2 and active(9, w):
                alloc[9] = 0.05
            shares[(p.person_key, w)] = alloc
    return shares


def make_demand(rng, people, capacity, shares):
    cap = capacity.set_index(["person_key", "week_start"])
    rows = []
    for p in people.itertuples():
        for w in ALL_WEEKS:
            if (p.person_key, w) not in cap.index:
                continue
            c = cap.loc[(p.person_key, w)]
            for proj, s in shares[(p.person_key, w)].items():
                hours = round(c.available_hours * s * rng.uniform(0.95, 1.05) * 2) / 2
                if hours > 0:
                    rows.append({"project_key": proj, "person_key": p.person_key, "role_key": p.role_key,
                                 "team_key": int(c.team_key), "week_start": w, "demand_type": "Allocated",
                                 "planned_hours": hours, "probability": 1.0})
    role_fte_h = lambda role: STD_WEEK * (1 - ROLE[role][4])  # noqa: E731
    extra = [  # project, role, team, weeks, FTE, type
        (7, 4, 3, range(2, 14), 0.5, "Unassigned"), (9, 1, 1, range(3, 9), 1.0, "Unassigned"),
        (11, 2, 1, range(6, 14), 2.0, "Pipeline"), (11, 1, 1, range(6, 14), 1.0, "Pipeline"),
        (12, 2, 1, range(9, 14), 1.0, "Pipeline"), (12, 4, 1, range(9, 14), 0.5, "Pipeline"),
    ]
    for proj, role, team, weeks, fte, dtype in extra:
        for n in weeks:
            rows.append({"project_key": proj, "person_key": -1, "role_key": role, "team_key": team, "week_start": week_n(n),
                         "demand_type": dtype, "planned_hours": round(fte * role_fte_h(role), 1),
                         "probability": PROJ[proj][8]})
    return pd.DataFrame(rows)


def make_timesheets(rng, people, leave, holidays, shares):
    hol = {(h.location, h.date) for h in holidays.itertuples()}
    bias = {p.person_key: rng.normal(1.0, 0.06) for p in people.itertuples()}
    rows = []
    for p in people.itertuples():
        np_pct = ROLE[p.role_key][4]
        for w in HIST_WEEKS:
            alloc = shares[(p.person_key, w)]
            for d in pd.bdate_range(w, periods=5):
                if d > STATUS_DATE or d < p.start_date or (pd.notna(p.end_date) and d > p.end_date):
                    continue
                if (p.location, d) in hol or d in leave[p.person_key]:
                    continue
                miss = 0.02
                if pd.Timestamp("2026-08-03") <= d <= pd.Timestamp("2026-08-28"):
                    miss = 0.10
                elif pd.Timestamp("2026-10-26") <= d <= pd.Timestamp("2026-10-30"):
                    miss = 0.15
                if rng.random() < miss:
                    continue
                if w == CURRENT_WEEK:
                    status = rng.choice(["Approved", "Submitted", "Draft"], p=[0.3, 0.6, 0.1])
                else:
                    status = "Approved"
                day_h = DAY_HOURS * p.contract_fte
                proj_h = {k: round(day_h * (1 - np_pct) * s * bias[p.person_key] * rng.uniform(0.9, 1.1) * 2) / 2
                          for k, s in alloc.items()}
                total = sum(proj_h.values())
                if total > day_h:
                    proj_h = {k: round(v * day_h / total * 2) / 2 for k, v in proj_h.items()}
                team = team_on(p, d)
                for k, h in proj_h.items():
                    if h > 0:
                        rows.append({"person_key": p.person_key, "team_key": team, "role_key": p.role_key, "project_key": k,
                                     "date": d, "activity": "Delivery", "hours": h, "is_billable": PROJ[k][9],
                                     "is_project_time": 1, "approval_status": status})
                rest = day_h - sum(proj_h.values())
                if rest > 0:
                    rows.append({"person_key": p.person_key, "team_key": team, "role_key": p.role_key, "project_key": -1,
                                 "date": d, "activity": rng.choice(["Admin & meetings", "Training", "Support"], p=[0.6, 0.2, 0.2]),
                                 "hours": rest, "is_billable": 0, "is_project_time": 0, "approval_status": status})
    return pd.DataFrame(rows)


def make_dim_date():
    d = pd.DataFrame({"date": pd.date_range("2026-05-01", "2027-03-31", freq="D")})
    dt = d.date.dt
    iso = dt.isocalendar()
    d["date_key"] = dt.year * 10000 + dt.month * 100 + dt.day
    d["year"], d["quarter"], d["month_number"] = dt.year, "Q" + dt.quarter.astype(str), dt.month
    d["month"], d["year_month_key"], d["year_month"] = dt.strftime("%b"), dt.year * 100 + dt.month, dt.strftime("%Y-%m")
    d["week_start"] = d.date - pd.to_timedelta(dt.weekday, unit="D")
    d["iso_week"], d["iso_year"] = iso.week.astype(int), iso.year.astype(int)
    d["year_week"] = d.iso_year.astype(str) + "-W" + d.iso_week.astype(str).str.zfill(2)
    d["is_working_day"] = (dt.weekday < 5).astype(int)
    d["period_type"] = np.where(d.week_start <= CURRENT_WEEK, "History", "Plan")
    return d


# ---------------------------------------------------------------- checks, metrics, output
def story_metrics(t):
    cap, dem, ts = t["fact_capacity"], t["fact_demand"], t["fact_timesheet"]
    dem = dem.assign(weighted=np.where(dem.demand_type == "Pipeline", dem.planned_hours * dem.probability, dem.planned_hours))
    avail = cap.groupby(["role_key", "week_start"]).available_hours.sum()
    alloc = dem[dem.demand_type == "Allocated"].groupby(["role_key", "week_start"]).planned_hours.sum()
    demand = dem.groupby(["role_key", "week_start"]).weighted.sum()
    gap = (avail - demand.reindex(avail.index, fill_value=0)).unstack(0)
    alloc_pct = (alloc.reindex(avail.index, fill_value=0) / avail).unstack(0)
    hist_cap = cap[cap.week_start <= CURRENT_WEEK]
    proj_hours = ts[(ts.is_project_time == 1) & (ts.approval_status == "Approved")].groupby("team_key").hours.sum()
    util_team = proj_hours / hist_cap.groupby("team_key").available_hours.sum()   # same 26 weeks on both sides
    # both sides by the month of the week's Monday (a week that crosses a month boundary belongs to its Monday's month)
    ts_dates = pd.to_datetime(ts.date)
    ts = ts.assign(month=(ts_dates - pd.to_timedelta(ts_dates.dt.weekday, unit="D")).dt.strftime("%Y-%m"))
    hist_cap = hist_cap.assign(month=hist_cap.week_start.dt.strftime("%Y-%m"))
    expected = (hist_cap.gross_hours - hist_cap.holiday_hours - hist_cap.leave_hours).groupby(hist_cap.month).sum()
    compliance = ts.groupby("month").hours.sum() / expected
    return gap, alloc_pct, util_team, compliance


def run_checks(t, errors):
    def check(cond, msg):
        if not cond:
            errors.append(msg)

    for name, key in [("dim_person", ["person_key"]), ("dim_project", ["project_key"]), ("dim_team", ["team_key"]),
                      ("dim_role", ["role_key"]), ("dim_date", ["date"]), ("fact_capacity", ["person_key", "week_start"]),
                      ("fact_demand", ["project_key", "person_key", "role_key", "week_start", "demand_type"]),
                      ("fact_timesheet", ["person_key", "project_key", "date", "activity"])]:
        check(not t[name].duplicated(key).any(), f"{name}: duplicate key {key}")
    for name in ["fact_capacity", "fact_demand", "fact_timesheet"]:
        df = t[name]
        check(set(df.person_key) <= set(t["dim_person"].person_key), f"{name}: unknown person")
        check(set(df.team_key) <= set(t["dim_team"].team_key), f"{name}: unknown team")
        check(set(df.role_key) <= set(t["dim_role"].role_key), f"{name}: unknown role")
    for name in ["fact_demand", "fact_timesheet"]:
        check(set(t[name].project_key) <= set(t["dim_project"].project_key), f"{name}: unknown project")
    dates = set(t["dim_date"].date)
    check(set(t["fact_capacity"].week_start) <= dates and set(t["fact_timesheet"].date) <= dates, "dates outside dim_date")
    cap = t["fact_capacity"]
    check((cap[["gross_hours", "holiday_hours", "leave_hours", "available_hours"]] >= 0).all().all(), "negative hours")
    check((cap.available_hours <= cap.gross_hours + 1e-9).all(), "available > gross")
    gap, alloc_pct, util_team, _ = story_metrics(t)
    de = alloc_pct.loc[week_n(3):week_n(8), 1]
    check((de > 1.05).all(), f"Data Engineer allocation weeks +3..+8 not > 105 %: {de.round(2).tolist()}")
    bi = gap.loc[week_n(6):week_n(13), 2]
    check((bi < 0).all(), f"BI Developer gap not negative from week +6: {bi.round(0).tolist()}")
    check(0.55 <= util_team[2] <= 0.75, f"Platform utilisation {util_team[2]:.2f} outside 55-75 %")


def write_readme(out, t):
    gap, alloc_pct, util_team, compliance = story_metrics(t)
    roles = {r[0]: r[1] for r in ROLES}
    teams = {x[0]: x[1] for x in TEAMS}
    fut = gap.loc[FUT_WEEKS].rename(columns=roles).round(0).astype(int)
    lines = [
        "# Capacity planning sample dataset (synthetic)",
        "",
        "**Synthetic demo data** for the `powerbi-developer` agent: fictitious people and projects. Generated by",
        "`scripts/generate_capacity_sample.py` (seed 42). The CSVs are git-ignored; regenerate them with:",
        "",
        "```",
        "python scripts/generate_capacity_sample.py --seed 42 --out data/capacity_planning_sample",
        "```",
        "",
        f"- Status date **{STATUS_DATE:%Y-%m-%d}** (Friday). History: {len(HIST_WEEKS)} weeks from {HIST_WEEKS[0]:%Y-%m-%d};",
        f"  plan: {len(FUT_WEEKS)} weeks {FUT_WEEKS[0]:%Y-%m-%d} → {FUT_WEEKS[-1]:%Y-%m-%d}. Weeks start on Monday.",
        f"- Unit: **hours**. Standard week {STD_WEEK:.0f} h; FTE = hours ÷ ({STD_WEEK:.0f} × weeks).",
        "- Model with the `pbi-project-capacity` skill. Friendly names: `fact_capacity.csv` → `Fact Capacity`,",
        "  snake_case → Title Case (`available_hours` → `Available Hours`, `week_start` → `Week Start`).",
        "- `team_key` / `role_key` on the facts are point-in-time: one data engineer moved from Platform to Data & Analytics",
        "  on 2026-09-07. `dim_person` holds the current team and role as text only (no relationship).",
        "- `person_key = -1` = Unassigned (role-level or pipeline demand); `project_key = -1` = Internal (non-project time).",
        "",
        "## Tables",
        "| File | Grain | Key | Rows |",
        "|---|---|---|---|",
    ]
    grains = {
        "dim_date": ("day (with week columns)", "date"), "dim_team": ("team", "team_key"), "dim_role": ("role", "role_key"),
        "dim_person": ("person (+ -1 Unassigned)", "person_key"), "dim_project": ("project (+ -1 Internal)", "project_key"),
        "public_holiday": ("location × date", "location + date"),
        "fact_capacity": ("person × week", "person_key + week_start"),
        "fact_demand": ("project × person/role × week × demand type", "composite"),
        "fact_timesheet": ("person × project × day × activity (history only)", "composite"),
    }
    for name, (grain, key) in grains.items():
        lines.append(f"| `{name}.csv` | {grain} | {key} | {len(t[name]):,} |")
    lines += [
        "",
        "## Definitions used by the generator",
        "- `available_hours` = gross − holiday − leave − non-project (role's `default_non_project_pct`).",
        "- `demand_type`: **Allocated** (named person, probability 1), **Unassigned** (approved, role only),",
        "  **Pipeline** (not approved; weight by `probability`).",
        "- Timesheets: `is_project_time = 1` on project lines; internal lines use `project_key = -1`. The current week is",
        "  partly `Submitted` / `Draft`, so approved-only measures dip in the last week.",
        "",
        "## Expected results",
        "**Capacity gap by role, plan weeks** (available − allocated − unassigned − probability-weighted pipeline, hours;",
        "negative = shortfall):",
        "",
        "| Week start | " + " | ".join(fut.columns) + " |",
        "|---|" + "---|" * len(fut.columns),
    ]
    for w, r in fut.iterrows():
        lines.append(f"| {w:%Y-%m-%d} | " + " | ".join(f"{v:,}" for v in r) + " |")
    de = alloc_pct.loc[week_n(3):week_n(8), 1]
    lines += [
        "",
        f"- **Data Engineers** allocated {de.min():.0%}–{de.max():.0%} of available hours in weeks "
        f"{week_n(3):%Y-%m-%d} → {week_n(8):%Y-%m-%d} (Risk Model Automation starts).",
        f"- **BI Developers** go short from {week_n(6):%Y-%m-%d} when the AI Analytics Pilot (pipeline, 70 %) starts.",
        "- **Utilisation by team** (approved project hours ÷ available, history weeks): "
        + ", ".join(f"{teams[k]} {v:.0%}" for k, v in util_team.items()) + ".",
        "- **Timesheet compliance by week-start month** (all booked hours ÷ expected = gross − holiday − leave): "
        + ", ".join(f"{m} {v:.0%}" for m, v in compliance.items()) + ".",
        "  Dips in August and the last week of October. The current week includes not-yet-submitted days.",
        "  Grouping by calendar day instead of week-start month gives values above 100 % in some months.",
        "",
    ]
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(pathlib.Path(__file__).resolve().parents[1] / "data" / "capacity_planning_sample"))
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    people = make_people(rng)
    holidays = pd.DataFrame(HOLIDAYS, columns=["location", "date", "holiday_name"]).assign(date=lambda d: pd.to_datetime(d.date))
    leave = make_leave(rng, people)
    capacity = make_capacity(people, leave, holidays)
    shares = person_shares(rng, people)
    demand = make_demand(rng, people, capacity, shares)
    timesheet = make_timesheets(rng, people, leave, holidays, shares)

    teams = {x[0]: x[1] for x in TEAMS}
    roles = {r[0]: r[1] for r in ROLES}
    dim_person = people.assign(
        current_team=[teams[team_on(p, STATUS_DATE)] for p in people.itertuples()],
        current_role=people.role_key.map(roles),
        is_active=[int(pd.isna(p.end_date) or p.end_date >= STATUS_DATE) for p in people.itertuples()],
    )[["person_key", "person_name", "current_team", "current_role", "location", "employment_type", "contract_fte",
       "standard_weekly_hours", "cost_rate", "utilisation_target_pct", "billable_target_pct", "start_date", "end_date", "is_active"]]
    dim_person = pd.concat([pd.DataFrame([{"person_key": -1, "person_name": "Unassigned", "current_team": "", "current_role": "",
                                           "location": "", "employment_type": "", "contract_fte": 0.0,
                                           "standard_weekly_hours": 0.0, "cost_rate": 0.0, "utilisation_target_pct": 0.0,
                                           "billable_target_pct": 0.0, "start_date": pd.NaT, "end_date": pd.NaT,
                                           "is_active": 0}]), dim_person], ignore_index=True)
    pms = people[people.role_key == 5].person_name.tolist()
    dim_project = pd.DataFrame(PROJECTS, columns=["project_key", "project_code", "project_name", "portfolio", "methodology",
                                                  "status", "health_rag", "is_pipeline", "probability", "is_billable",
                                                  "start_date", "finish_date"])
    dim_project.insert(4, "project_manager", [pms[i % len(pms)] for i in range(len(dim_project))])
    dim_project = pd.concat([pd.DataFrame([{"project_key": -1, "project_code": "INT", "project_name": "Internal / non-project",
                                            "portfolio": "Internal", "project_manager": "", "methodology": "", "status": "",
                                            "health_rag": "", "is_pipeline": 0, "probability": 1.0, "is_billable": 0,
                                            "start_date": "", "finish_date": ""}]), dim_project], ignore_index=True)

    tables = {
        "dim_date": make_dim_date(),
        "dim_team": pd.DataFrame(TEAMS, columns=["team_key", "team_name", "department", "team_lead"]),
        "dim_role": pd.DataFrame(ROLES, columns=["role_key", "role_name", "role_family", "seniority",
                                                 "default_non_project_pct", "cost_rate"]),
        "dim_person": dim_person,
        "dim_project": dim_project,
        "public_holiday": holidays,
        "fact_capacity": capacity,
        "fact_demand": demand,
        "fact_timesheet": timesheet,
    }
    errors: list[str] = []
    run_checks(tables, errors)
    if errors:
        print("CHECKS FAILED:\n- " + "\n- ".join(errors))
        sys.exit(1)

    for old in out.glob("*.csv"):
        old.unlink()
    for name, df in tables.items():
        df = df.copy()
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")
        df.to_csv(out / f"{name}.csv", index=False)
    write_readme(out, tables)

    gap, alloc_pct, util_team, _ = story_metrics(tables)
    print(f"Wrote {len(tables)} tables to {out}")
    print(f"  Data Engineer allocation weeks +3..+8: {alloc_pct.loc[week_n(3):week_n(8), 1].round(2).tolist()}")
    print(f"  BI Developer gap weeks +1..+13 (h):   {gap.loc[FUT_WEEKS, 2].round(0).astype(int).tolist()}")
    print(f"  Utilisation by team: {({teams[k]: round(v, 2) for k, v in util_team.items()})}")
    print("All checks passed.")


if __name__ == "__main__":
    main()
