#!/usr/bin/env python
"""Generate the synthetic liquidity demo dataset (LCR + maturity ladder) as star-schema CSVs.

Synthetic data for demonstrating the powerbi-developer agent. Bank only, USD reporting currency
(+ EUR), 12 month-end snapshots up to the as-of date, a contractual cash-flow ladder and a 90-day
stressed cash-flow projection for four scenarios. A reference table holds the LCR computed here,
so the DAX in Power BI can be reconciled against it.

    python scripts/generate_liquidity_sample.py [--seed 42] [--out data/liquidity_sample]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd

ASOF = pd.Timestamp("2026-10-31")
MONTH_ENDS = pd.date_range(end=ASOF, periods=12, freq="ME")
HORIZON_DAYS = 90
INSTALMENT_DAY = 28          # loan instalments and interest fall on the 28th: always 28-30 days after a month-end
SCENARIOS = ["BASE", "IDIO", "MARKET", "COMBINED"]
BASE_LCR_PATH = (1.42, 1.35)  # first and last month-end target for the BASE LCR
STRESS_TARGETS = {"IDIO": 1.15, "MARKET": 1.08, "COMBINED": 0.92}

# ---------------------------------------------------------------- reference data
SEGMENTS = [
    ("RET", "Retail"), ("SME", "SME"), ("CORP", "Corporate"),
    ("FI", "Financial institutions"), ("SOV", "Sovereign"), ("CB", "Central bank"),
]

# code, name, side, category, product_class, segment, lcr_group, lcr_basis, lcr_flow, lcr_rate, hqla_level, base_haircut
PRODUCTS = [
    ("RET_STABLE", "Retail stable deposits", "Liability", "Retail Deposits", "nmd", "RET", "Retail & SME deposits", "balance", "outflow", 0.05, "", 0.0),
    ("RET_LESS", "Retail less-stable deposits", "Liability", "Retail Deposits", "nmd", "RET", "Retail & SME deposits", "balance", "outflow", 0.10, "", 0.0),
    ("RET_TERM", "Retail term deposits", "Liability", "Retail Deposits", "term", "RET", "Retail & SME deposits", "due_30d", "outflow", 0.10, "", 0.0),
    ("SME_DEP", "SME deposits", "Liability", "Retail Deposits", "nmd", "SME", "Retail & SME deposits", "balance", "outflow", 0.10, "", 0.0),
    ("CORP_OPER", "Corporate operational deposits", "Liability", "Wholesale Deposits", "nmd", "CORP", "Corporate deposits", "balance", "outflow", 0.25, "", 0.0),
    ("CORP_NONOP", "Corporate non-operational deposits", "Liability", "Wholesale Deposits", "nmd", "CORP", "Corporate deposits", "balance", "outflow", 0.40, "", 0.0),
    ("CORP_TERM", "Corporate term deposits", "Liability", "Wholesale Deposits", "term", "CORP", "Corporate deposits", "due_30d", "outflow", 0.40, "", 0.0),
    ("FI_DEP", "Interbank deposits taken", "Liability", "Interbank", "term", "FI", "Wholesale funding", "due_30d", "outflow", 1.00, "", 0.0),
    ("DEBT_ISS", "Senior bonds issued", "Liability", "Debt Securities", "term", "FI", "Wholesale funding", "due_30d", "outflow", 1.00, "", 0.0),
    ("EQUITY", "Shareholders' equity", "Equity", "Equity", "other", "CORP", "Not in LCR", "none", "none", 0.0, "", 0.0),
    ("FAC_RET", "Retail credit lines (undrawn)", "Off-balance", "Commitments", "facility", "RET", "Committed facilities", "balance", "outflow", 0.05, "", 0.0),
    ("FAC_CORP", "Corporate credit facilities (undrawn)", "Off-balance", "Commitments", "facility", "CORP", "Committed facilities", "balance", "outflow", 0.10, "", 0.0),
    ("FAC_LIQ", "Corporate liquidity facilities (undrawn)", "Off-balance", "Commitments", "facility", "CORP", "Committed facilities", "balance", "outflow", 0.30, "", 0.0),
    ("LN_MORT", "Residential mortgages", "Asset", "Loans", "loan", "RET", "Loan inflows", "due_30d", "inflow", 0.50, "", 0.0),
    ("LN_CONS", "Consumer loans", "Asset", "Loans", "loan", "RET", "Loan inflows", "due_30d", "inflow", 0.50, "", 0.0),
    ("LN_SME", "SME loans", "Asset", "Loans", "loan", "SME", "Loan inflows", "due_30d", "inflow", 0.50, "", 0.0),
    ("LN_CORP", "Corporate loans", "Asset", "Loans", "loan", "CORP", "Loan inflows", "due_30d", "inflow", 0.50, "", 0.0),
    ("PLC_FI", "Interbank placements", "Asset", "Interbank", "term", "FI", "Interbank inflows", "due_30d", "inflow", 1.00, "", 0.0),
    ("CASH_CB", "Central bank reserves", "Asset", "Cash & Reserves", "hqla", "CB", "Central bank reserves", "hqla", "hqla", 1.00, "1", 0.0),
    ("HQLA_GOV", "Government bonds", "Asset", "HQLA Securities", "hqla", "SOV", "HQLA L1", "hqla", "hqla", 1.00, "1", 0.0),
    ("HQLA_COV", "Covered bonds", "Asset", "HQLA Securities", "hqla", "FI", "HQLA L2A", "hqla", "hqla", 1.00, "2A", 0.15),
    ("HQLA_CORPB", "Corporate bonds", "Asset", "HQLA Securities", "hqla", "CORP", "HQLA L2B", "hqla", "hqla", 1.00, "2B", 0.50),
    ("OTHER_ASSET", "Other assets", "Asset", "Other", "other", "CORP", "Not in LCR", "none", "none", 0.0, "", 0.0),
]
PRODUCT_COLS = ["product_code", "product_name", "side", "category", "product_class", "segment_code", "lcr_group",
                "lcr_basis", "lcr_flow", "lcr_rate", "hqla_level", "base_haircut"]

# contract generation: kind, active contracts at as-of, target as-of balance (USD), tenor spec, rate mean, monthly trend
CONTRACT_SPEC = {
    "RET_STABLE": ("nmd", 150, 9.0e9, None, 0.005, 0.002),
    "RET_LESS": ("nmd", 100, 4.0e9, None, 0.010, 0.001),
    "RET_TERM": ("bullet", 200, 5.0e9, [1, 3, 6, 12, 24], 0.030, None),
    "SME_DEP": ("nmd", 100, 2.5e9, None, 0.008, 0.001),
    "CORP_OPER": ("nmd", 80, 3.0e9, None, 0.010, 0.001),
    "CORP_NONOP": ("nmd", 100, 4.0e9, None, 0.020, 0.004),
    "CORP_TERM": ("bullet", 80, 2.5e9, [1, 3, 6, 12], 0.035, None),
    "FI_DEP": ("bullet", 40, 1.5e9, [1, 1, 3, 6], 0.040, None),
    "DEBT_ISS": ("bullet", 12, 3.0e9, [24, 36, 60, 84], 0.045, None),
    "EQUITY": ("single", 1, 3.5e9, None, 0.0, 0.002),
    "FAC_RET": ("facility", 50, 2.0e9, None, 0.0, 0.002),
    "FAC_CORP": ("facility", 80, 5.0e9, None, 0.0, 0.003),
    "FAC_LIQ": ("facility", 20, 1.0e9, None, 0.0, 0.002),
    "LN_MORT": ("amort", 200, 14.0e9, (10, 25), 0.045, None),
    "LN_CONS": ("amort", 150, 3.0e9, (2, 5), 0.080, None),
    "LN_SME": ("amort", 120, 4.0e9, (3, 7), 0.060, None),
    "LN_CORP": ("amort", 150, 9.0e9, (3, 7), 0.055, None),
    "PLC_FI": ("bullet", 30, 1.5e9, [1, 1, 3], 0.042, None),
    "OTHER_ASSET": ("single", 1, 2.0e9, None, 0.0, 0.001),
}

# stress pattern per lcr_group: (run-off multiplier, inflow multiplier, haircut add-on); scaled by a solved factor
STRESS_PATTERN = {
    "IDIO": {"Retail & SME deposits": (1.6, 1, 0), "Corporate deposits": (1.3, 1, 0), "Committed facilities": (1.5, 1, 0),
             "Loan inflows": (1, 1.0, 0), "Interbank inflows": (1, 1.0, 0)},
    "MARKET": {"Retail & SME deposits": (1.1, 1, 0), "Corporate deposits": (1.2, 1, 0), "Committed facilities": (1.5, 1, 0),
               "Loan inflows": (1, 0.8, 0), "Interbank inflows": (1, 0.8, 0),
               "HQLA L1": (1, 1, 0.02), "HQLA L2A": (1, 1, 0.10), "HQLA L2B": (1, 1, 0.20)},
    "COMBINED": {"Retail & SME deposits": (1.8, 1, 0), "Corporate deposits": (1.5, 1, 0), "Committed facilities": (2.0, 1, 0),
                 "Loan inflows": (1, 0.7, 0), "Interbank inflows": (1, 0.7, 0),
                 "HQLA L1": (1, 1, 0.02), "HQLA L2A": (1, 1, 0.10), "HQLA L2B": (1, 1, 0.20)},
}
LCR_GROUPS = ["Retail & SME deposits", "Corporate deposits", "Wholesale funding", "Committed facilities",
              "Loan inflows", "Interbank inflows", "Central bank reserves", "HQLA L1", "HQLA L2A", "HQLA L2B"]

BUCKETS = [  # key, label, sort, days_from, days_to, in_lcr_30d, in_1y
    ("ON", "O/N", 1, 0, 1, 1, 1), ("D7", "2-7D", 2, 2, 7, 1, 1), ("D30", "8-30D", 3, 8, 30, 1, 1),
    ("M3", "1-3M", 4, 31, 90, 0, 1), ("M6", "3-6M", 5, 91, 180, 0, 1), ("M12", "6-12M", 6, 181, 365, 0, 1),
    ("Y2", "1-2Y", 7, 366, 730, 0, 0), ("Y5", "2-5Y", 8, 731, 1825, 0, 0), ("Y5P", ">5Y", 9, 1826, 99999, 0, 0),
    ("NM", "Non-maturity", 10, None, None, 0, 0),
]

NAME_A = ["Northbridge", "Bluewater", "Silverline", "Redwood", "Harbor", "Summit", "Evergreen", "Granite", "Lakeside",
          "Pioneer", "Crescent", "Meridian", "Oakfield", "Riverstone", "Sterling", "Westgate", "Brightpath", "Cobalt"]
NAME_B = ["Logistics", "Foods", "Energy", "Retail", "Holdings", "Manufacturing", "Healthcare", "Shipping", "Textiles",
          "Construction", "Technologies", "Pharma", "Motors", "Airways", "Chemicals", "Media", "Telecom", "Hotels"]


def bucket_for(days: float | None) -> str:
    if days is None or pd.isna(days):
        return "NM"
    for key, _, _, lo, hi, _, _ in BUCKETS:
        if lo is not None and lo <= days <= hi:
            return key
    return "Y5P"


def month_end_28(d: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(d.year, d.month, INSTALMENT_DAY)


# ---------------------------------------------------------------- generation
def make_fx(rng):
    eur = np.linspace(1.05, 1.08, len(MONTH_ENDS)) + rng.normal(0, 0.004, len(MONTH_ENDS))
    eur[-1] = 1.08
    rows = [(d, "USD", 1.0) for d in MONTH_ENDS] + [(d, "EUR", round(r, 4)) for d, r in zip(MONTH_ENDS, eur)]
    return pd.DataFrame(rows, columns=["date", "currency_code", "rate_to_rc"])


def make_contracts(rng, products):
    rows, seq = [], 0
    for code, (kind, n_active, _, tenor, rate, _) in CONTRACT_SPEC.items():
        seg = products.loc[code, "segment_code"]
        if kind == "bullet":
            avg_t = float(np.mean(tenor))
            n = int(round(n_active * (12 + avg_t) / avg_t))
        else:
            n = n_active
        for _ in range(n):
            seq += 1
            ccy = "USD" if kind == "single" or rng.random() < 0.75 else "EUR"
            start = maturity = pd.NaT
            if kind == "bullet":
                t = int(rng.choice(tenor))
                window_start = MONTH_ENDS[0] - pd.DateOffset(months=1)
                window_end = ASOF + pd.DateOffset(months=t)
                maturity = window_start + pd.Timedelta(days=int(rng.integers(1, (window_end - window_start).days)))
                start = maturity - pd.DateOffset(months=t)
            elif kind == "amort":
                years = int(rng.integers(tenor[0], tenor[1] + 1))
                n_months = 12 * years
                elapsed = int(rng.integers(-11, n_months - 1))      # negative = originated during history
                start = month_end_28(ASOF - pd.DateOffset(months=elapsed))
                maturity = start + pd.DateOffset(months=n_months)
            if seg in ("RET", "SME") and kind in ("nmd", "facility"):
                cpty = f"{products.loc[code, 'product_name']} pool {seq:04d}"
            elif kind == "single":
                cpty = "Bank"
            else:
                cpty = f"{rng.choice(NAME_A)} {rng.choice(NAME_B)}"
                if seg == "FI":
                    cpty = f"{rng.choice(NAME_A)} Bank"
            rows.append({
                "contract_id": f"C{seq:05d}", "product_code": code, "segment_code": seg, "currency_code": ccy,
                "counterparty_name": cpty, "start_date": start, "maturity_date": maturity,
                "interest_rate": round(max(0.0, rate + rng.normal(0, rate * 0.15)), 4) if rate else 0.0,
                "notional_local": float(rng.lognormal(0, 0.6)),
            })
    return pd.DataFrame(rows)


def schedule(c) -> list[tuple[pd.Timestamp, float]]:
    """Principal events (date, positive amount) over the contract's life."""
    kind = CONTRACT_SPEC[c.product_code][0]
    if kind == "bullet":
        return [(c.maturity_date, c.notional_local)]
    if kind == "amort":
        n = (c.maturity_date.year - c.start_date.year) * 12 + c.maturity_date.month - c.start_date.month
        dates = [c.start_date + pd.DateOffset(months=i) for i in range(1, n + 1)]
        return [(d, c.notional_local / n) for d in dates]
    return []


def balance_at(c, sched, t, nmd_factor):
    kind = CONTRACT_SPEC[c.product_code][0]
    if kind in ("nmd", "facility", "single"):
        return c.notional_local * nmd_factor
    if t < c.start_date or t >= c.maturity_date:
        return 0.0
    if kind == "bullet":
        return c.notional_local
    return c.notional_local - sum(a for d, a in sched if d <= t)


def make_positions(rng, contracts, fx):
    fx_map = fx.set_index(["date", "currency_code"])["rate_to_rc"]
    scheds = {c.contract_id: schedule(c) for c in contracts.itertuples()}
    # growth paths for non-maturing balances: factor relative to as-of
    k = np.arange(len(MONTH_ENDS)) - (len(MONTH_ENDS) - 1)
    paths = {code: (1 + spec[5]) ** k * (1 + rng.normal(0, 0.01, len(k))) if spec[5] is not None else None
             for code, spec in CONTRACT_SPEC.items()}
    for code, p in paths.items():
        if p is not None:
            p[-1] = 1.0
    noise = {c.contract_id: 1 + rng.normal(0, 0.02, len(MONTH_ENDS)) for c in contracts.itertuples()}
    rows = []
    for c in contracts.itertuples():
        sched = scheds[c.contract_id]
        for i, t in enumerate(MONTH_ENDS):
            factor = paths[c.product_code][i] * noise[c.contract_id][i] if paths[c.product_code] is not None else 1.0
            if i == len(MONTH_ENDS) - 1:
                factor = 1.0 if paths[c.product_code] is not None else factor
            bal = balance_at(c, sched, t, factor)
            if bal <= 0.005:
                continue
            due30 = sum(a for d, a in sched if t < d <= t + pd.Timedelta(days=30))
            rem = (c.maturity_date - t).days if pd.notna(c.maturity_date) else None
            rate = fx_map[(t, c.currency_code)]
            rows.append({
                "date": t, "contract_id": c.contract_id, "product_code": c.product_code,
                "currency_code": c.currency_code, "bucket_key": bucket_for(rem),
                "balance_local": bal, "balance_rc": bal * rate, "principal_due_30d_rc": due30 * rate,
                "remaining_maturity_days": rem,
            })
    return pd.DataFrame(rows)


def scale_to_targets(contracts, positions):
    """Rescale notionals so each product's as-of balance (RC) hits its target."""
    asof = positions[positions.date == ASOF].groupby("product_code")["balance_rc"].sum()
    factors = {code: spec[2] / asof[code] for code, spec in CONTRACT_SPEC.items()}
    contracts["notional_local"] = contracts.apply(lambda r: r.notional_local * factors[r.product_code], axis=1)
    for col in ("balance_local", "balance_rc", "principal_due_30d_rc"):
        positions[col] = positions[col] * positions.product_code.map(factors)
    return contracts, positions


# ---------------------------------------------------------------- LCR engine
def multipliers(params, scenario):
    p = params[params.scenario_key == scenario].set_index("lcr_group")
    return p["runoff_multiplier"], p["inflow_multiplier"], p["haircut_addon"]


def flows_30d(pos_t, products, params, scenario):
    run, inf, _ = multipliers(params, scenario)
    df = pos_t.merge(products, left_on="product_code", right_index=True)
    base = np.where(df.lcr_basis == "balance", df.balance_rc, df.principal_due_30d_rc)
    out_mask = df.lcr_flow == "outflow"
    in_mask = df.lcr_flow == "inflow"
    out_rate = np.minimum(1.0, df.lcr_rate * df.lcr_group.map(run).fillna(1.0))
    in_rate = np.minimum(1.0, df.lcr_rate * df.lcr_group.map(inf).fillna(1.0))
    return float((base * out_rate)[out_mask].sum()), float((base * in_rate)[in_mask].sum())


def hqla_value(hq_t, products, params, scenario):
    _, _, add = multipliers(params, scenario)
    df = hq_t[hq_t.encumbered == 0].merge(products[["lcr_group"]], left_on="product_code", right_index=True)
    hc = np.clip(df.base_haircut + df.lcr_group.map(add).fillna(0.0), 0, 1)
    df = df.assign(post=df.market_value_rc * (1 - hc))
    l1 = float(df.loc[df.hqla_level == "1", "post"].sum())
    l2a = float(df.loc[df.hqla_level == "2A", "post"].sum())
    l2b = float(df.loc[df.hqla_level == "2B", "post"].sum())
    return l1, l2a, l2b, apply_caps(l1, l2a, l2b)


def apply_caps(l1, l2a, l2b):
    """Simplified Basel caps: Level 2B <= 15 % and Level 2 <= 40 % of the stock (no unwind adjustment)."""
    l2b_c = min(l2b, 15 / 85 * (l1 + l2a))
    l2_c = min(l2a + l2b_c, 2 / 3 * l1)
    return l1 + l2_c


def lcr(hqla, out, inflow):
    capped = min(inflow, 0.75 * out)
    net = out - capped
    return hqla / net, capped, net


def make_hqla(rng, products, positions, params):
    sec = []
    specs = [("CASH_CB", "Central bank reserves", 2), ("HQLA_GOV", "Govt bond", 20), ("HQLA_COV", "Covered bond", 10),
             ("HQLA_CORPB", "Corporate bond", 8)]
    for code, label, n in specs:
        for j in range(n):
            ccy = "USD" if j % 4 != 3 else "EUR"
            if code == "CASH_CB":
                ccy = "USD" if j == 0 else "EUR"
            sec.append({"security_id": f"S{len(sec) + 1:03d}", "product_code": code,
                        "security_name": f"{label} {ccy} {2027 + j % 8}" if code != "CASH_CB" else f"{label} {ccy}",
                        "currency_code": ccy, "hqla_level": products.loc[code, "hqla_level"],
                        "base_haircut": products.loc[code, "base_haircut"],
                        "encumbered": 1 if code == "HQLA_GOV" and j in (2, 9, 15) else 0,
                        "weight": rng.uniform(0.5, 1.5)})
    sec = pd.DataFrame(sec)
    lcr_path = np.linspace(*BASE_LCR_PATH, len(MONTH_ENDS)) + rng.normal(0, 0.008, len(MONTH_ENDS))
    lcr_path[-1] = BASE_LCR_PATH[1]
    rows = []
    for i, t in enumerate(MONTH_ENDS):
        out, inflow = flows_30d(positions[positions.date == t], products, params, "BASE")
        _, _, net = lcr(1.0, out, inflow)
        h = lcr_path[i] * net
        targets_post = {"CASH_CB": 0.72 * h * 0.30, "HQLA_GOV": 0.72 * h * 0.70, "HQLA_COV": 0.20 * h, "HQLA_CORPB": 0.08 * h}
        for code, post in targets_post.items():
            s = sec[(sec.product_code == code) & (sec.encumbered == 0)]
            w = s.weight * (1 + rng.normal(0, 0.03, len(s)))
            mv = post / (1 - products.loc[code, "base_haircut"]) * w / w.sum()
            for r, v in zip(s.itertuples(), mv):
                rows.append((t, r.security_id, v))
        enc = sec[sec.encumbered == 1]
        for r in enc.itertuples():
            rows.append((t, r.security_id, 0.72 * h * 0.70 * 0.025 * r.weight))
    hq = pd.DataFrame(rows, columns=["date", "security_id", "market_value_rc"]).merge(sec.drop(columns="weight"), on="security_id")
    return hq


def solve_stress(products, positions, hq, params):
    pos_t, hq_t = positions[positions.date == ASOF], hq[hq.date == ASOF]
    for s, target in STRESS_TARGETS.items():
        pattern = STRESS_PATTERN[s]

        def lcr_for(k):
            p = params.copy()
            for g, (r, i, a) in pattern.items():
                m = (p.scenario_key == s) & (p.lcr_group == g)
                p.loc[m, ["runoff_multiplier", "inflow_multiplier", "haircut_addon"]] = [1 + k * (r - 1), i, a]
            out, inflow = flows_30d(pos_t, products, p, s)
            return lcr(hqla_value(hq_t, products, p, s)[3], out, inflow)[0], p

        lo, hi = 0.0, 20.0
        if lcr_for(lo)[0] < target:
            sys.exit(f"{s}: target {target} not reachable (LCR at k=0 is {lcr_for(lo)[0]:.3f})")
        for _ in range(60):
            mid = (lo + hi) / 2
            if lcr_for(mid)[0] > target:
                lo = mid
            else:
                hi = mid
        params = lcr_for(lo)[1]
    params[["runoff_multiplier", "inflow_multiplier", "haircut_addon"]] = params[
        ["runoff_multiplier", "inflow_multiplier", "haircut_addon"]].round(4)
    return params


def make_contractual_cf(contracts, positions, fx):
    rate = fx[fx.date == ASOF].set_index("currency_code")["rate_to_rc"]
    active = positions[positions.date == ASOF].set_index("contract_id")
    side = dict(zip([p[0] for p in PRODUCTS], [p[2] for p in PRODUCTS]))
    rows = []
    for c in contracts[contracts.contract_id.isin(active.index)].itertuples():
        kind = CONTRACT_SPEC[c.product_code][0]
        sign = 1 if side[c.product_code] == "Asset" else -1
        if kind == "nmd":
            rows.append((ASOF + pd.Timedelta(days=1), c.product_code, c.currency_code, "NMD_ON_DEMAND",
                         sign * active.loc[c.contract_id, "balance_local"]))
            continue
        if kind not in ("bullet", "amort"):
            continue
        sched = [(d, a) for d, a in schedule(c) if d > ASOF]
        for d, a in sched:
            rows.append((d, c.product_code, c.currency_code, "PRINCIPAL", sign * a))
        outstanding = active.loc[c.contract_id, "balance_local"]
        for m in range(1, 13):
            d = month_end_28(ASOF + pd.DateOffset(months=m))
            if d > c.maturity_date:
                break
            rows.append((d, c.product_code, c.currency_code, "INTEREST", sign * outstanding * c.interest_rate / 12))
            outstanding -= sum(a for dd, a in sched if month_end_28(ASOF + pd.DateOffset(months=m - 1)) < dd <= d)
    cf = pd.DataFrame(rows, columns=["date", "product_code", "currency_code", "flow_type", "amount_local"])
    cf = cf.groupby(["date", "product_code", "currency_code", "flow_type"], as_index=False)["amount_local"].sum()
    cf["amount_rc"] = cf.amount_local * cf.currency_code.map(rate)
    cf["bucket_key"] = [bucket_for((d - ASOF).days) for d in cf.date]
    return cf


def make_stressed_cf(contracts, positions, products, params):
    pos = positions[positions.date == ASOF].merge(products, left_on="product_code", right_index=True)
    w30 = np.exp(-np.arange(1, 31) / 10.0)
    w30 = w30 / w30.sum()
    days = pd.date_range(ASOF + pd.Timedelta(days=1), periods=HORIZON_DAYS, freq="D")
    end = days[-1]
    side = products["side"]
    rows = []
    sched_rows = []
    for c in contracts[contracts.contract_id.isin(pos.contract_id)].itertuples():
        if CONTRACT_SPEC[c.product_code][0] in ("bullet", "amort"):
            ccy_rate = pos.loc[pos.contract_id == c.contract_id, "balance_rc"].iloc[0] / \
                pos.loc[pos.contract_id == c.contract_id, "balance_local"].iloc[0]
            for d, a in schedule(c):
                if ASOF < d <= end:
                    sched_rows.append((d, c.product_code, c.currency_code, a * ccy_rate))
    sched = pd.DataFrame(sched_rows, columns=["date", "product_code", "currency_code", "principal_rc"])
    sched = sched.groupby(["date", "product_code", "currency_code"], as_index=False).principal_rc.sum()
    for s in SCENARIOS:
        run, inf, _ = multipliers(params, s)
        # run-off and drawdowns on balances
        bal = pos[pos.lcr_basis == "balance"].groupby(["product_code", "currency_code", "product_class", "lcr_group", "lcr_rate"],
                                                       as_index=False).balance_rc.sum()
        for b in bal.itertuples():
            r = min(1.0, b.lcr_rate * run.get(b.lcr_group, 1.0))
            ftype, tail = ("RUNOFF", 0.5) if b.product_class == "nmd" else ("DRAWDOWN", 0.3)
            for i, d in enumerate(days):
                amt = -b.balance_rc * r * (w30[i] if i < 30 else tail / (HORIZON_DAYS - 30))
                rows.append((s, d, b.product_code, b.currency_code, ftype, amt))
        # contractual maturities and rollovers
        for e in sched.merge(products, left_on="product_code", right_index=True).itertuples():
            sign = 1 if side[e.product_code] == "Asset" else -1
            rows.append((s, e.date, e.product_code, e.currency_code, "CONTRACTUAL", sign * e.principal_rc))
            if e.lcr_flow == "outflow":
                keep = 1 - min(1.0, e.lcr_rate * run.get(e.lcr_group, 1.0))
            else:
                keep = 1 - min(1.0, e.lcr_rate * inf.get(e.lcr_group, 1.0))
            if keep > 0:
                rows.append((s, e.date, e.product_code, e.currency_code, "ROLLOVER", -sign * e.principal_rc * keep))
    cf = pd.DataFrame(rows, columns=["scenario_key", "date", "product_code", "currency_code", "flow_type", "amount_rc"])
    return cf.groupby(["scenario_key", "date", "product_code", "currency_code", "flow_type"], as_index=False).amount_rc.sum()


def make_ref_metrics(products, positions, hq, params, stressed):
    rows = []
    for t in MONTH_ENDS:
        for s in SCENARIOS:
            out, inflow = flows_30d(positions[positions.date == t], products, params, s)
            l1, l2a, l2b, h = hqla_value(hq[hq.date == t], products, params, s)
            ratio, capped, net = lcr(h, out, inflow)
            surv = None
            if t == ASOF:
                cum = stressed[stressed.scenario_key == s].groupby("date").amount_rc.sum().sort_index().cumsum()
                breach = cum[h + cum < 0]
                surv = (breach.index[0] - ASOF).days - 1 if len(breach) else None
            rows.append({"date": t, "scenario_key": s, "hqla_l1_rc": l1, "hqla_l2a_rc": l2a, "hqla_l2b_rc": l2b,
                         "hqla_after_haircut_caps_rc": h, "outflows_30d_rc": out, "inflows_30d_rc": inflow,
                         "inflows_capped_rc": capped, "net_outflows_rc": net, "lcr_pct": ratio, "survival_days": surv})
    return pd.DataFrame(rows)


def make_dim_date(last_date):
    d = pd.DataFrame({"date": pd.date_range("2025-11-01", pd.Timestamp(last_date.year, 12, 31), freq="D")})
    dt = d.date.dt
    d["date_key"] = dt.year * 10000 + dt.month * 100 + dt.day
    d["year"], d["quarter"], d["month_number"] = dt.year, "Q" + dt.quarter.astype(str), dt.month
    d["month"], d["year_month_key"], d["year_month"] = dt.strftime("%b"), dt.year * 100 + dt.month, dt.strftime("%Y-%m")
    d["month_end"] = d.date + pd.offsets.MonthEnd(0)
    d["is_month_end"] = (d.date == d.month_end).astype(int)
    d["week_start"] = d.date - pd.to_timedelta(dt.weekday, unit="D")
    d["iso_week"] = dt.isocalendar().week.astype(int)
    d["is_working_day"] = (dt.weekday < 5).astype(int)
    d["days_from_asof"] = (d.date - ASOF).dt.days
    d["period_type"] = np.select([d.date < ASOF, d.date == ASOF, d.days_from_asof <= HORIZON_DAYS],
                                 ["History", "As-of", "Projection"], "Beyond horizon")
    return d


# ---------------------------------------------------------------- checks and output
def check(cond, msg, errors):
    if not cond:
        errors.append(msg)


def run_checks(t, errors):
    for name, key in [("dim_product", ["product_code"]), ("dim_contract", ["contract_id"]), ("dim_date", ["date"]),
                      ("fact_bank_position", ["date", "contract_id"]), ("fact_hqla_holding", ["date", "security_id"]),
                      ("fact_bank_cf_contractual", ["date", "product_code", "currency_code", "flow_type"]),
                      ("fact_bank_cf_stressed", ["scenario_key", "date", "product_code", "currency_code", "flow_type"]),
                      ("ref_liquidity_metrics", ["date", "scenario_key"])]:
        check(not t[name].duplicated(key).any(), f"{name}: duplicate key {key}", errors)
    prods = set(t["dim_product"].product_code)
    for name in ["dim_contract", "fact_bank_position", "fact_hqla_holding", "fact_bank_cf_contractual", "fact_bank_cf_stressed"]:
        check(set(t[name].product_code) <= prods, f"{name}: unknown product_code", errors)
    check(set(t["fact_bank_position"].contract_id) <= set(t["dim_contract"].contract_id), "positions: unknown contract", errors)
    dates = set(t["dim_date"].date)
    for name in ["fact_bank_position", "fact_hqla_holding", "fact_bank_cf_contractual", "fact_bank_cf_stressed"]:
        check(set(t[name].date) <= dates, f"{name}: date outside dim_date", errors)
    check((t["fact_bank_position"].balance_rc > 0).all(), "positions: non-positive balance", errors)
    ref = t["ref_liquidity_metrics"]
    at = ref[ref.date == ASOF].set_index("scenario_key").lcr_pct
    check(abs(at["BASE"] - BASE_LCR_PATH[1]) < 0.005, f"BASE LCR {at['BASE']:.3f} off target", errors)
    for s, target in STRESS_TARGETS.items():
        check(abs(at[s] - target) < 0.005, f"{s} LCR {at[s]:.3f} off target {target}", errors)
    check((ref.hqla_l2b_rc <= 0.15 * ref.hqla_after_haircut_caps_rc + 1).all(), "L2B cap breached", errors)
    # consistency: 30-day contractual principal in positions == stressed CONTRACTUAL flows within 30 days
    pos = t["fact_bank_position"]
    p30 = pos[pos.date == ASOF].principal_due_30d_rc.sum()
    st = t["fact_bank_cf_stressed"]
    s30 = st[(st.scenario_key == "BASE") & (st.flow_type == "CONTRACTUAL") &
             (st.date <= ASOF + pd.Timedelta(days=30))].amount_rc.abs().sum()
    check(abs(p30 - s30) / p30 < 1e-6, f"30-day principal mismatch {p30:,.0f} vs {s30:,.0f}", errors)


def write_readme(out, t):
    ref = t["ref_liquidity_metrics"]
    at = ref[ref.date == ASOF].set_index("scenario_key")
    first = ref[ref.date == MONTH_ENDS[0]].set_index("scenario_key")
    lines = [
        "# Liquidity sample dataset (synthetic)",
        "",
        "**Synthetic demo data** for the `powerbi-developer` agent: a fictitious bank, not real figures. Generated by",
        "`scripts/generate_liquidity_sample.py` (seed 42). The CSVs are git-ignored; regenerate them with:",
        "",
        "```",
        "python scripts/generate_liquidity_sample.py --seed 42 --out data/liquidity_sample",
        "```",
        "",
        f"- As-of date **{ASOF:%Y-%m-%d}**; 12 month-end snapshots {MONTH_ENDS[0]:%Y-%m-%d} → {ASOF:%Y-%m-%d}.",
        f"- Reporting currency **USD** (`*_rc` columns); EUR positions converted at month-end rates (`fact_fx_rate.csv`).",
        f"- Stress horizon {HORIZON_DAYS} days from the as-of date. Cash flows are **+ in / − out**; balances are positive.",
        "- Model with the `pbi-treasury-liquidity` skill. Friendly names: `fact_bank_position.csv` → `Fact Bank Position`,",
        "  snake_case → Title Case, acronyms kept (`balance_rc` → `Balance RC`, `lcr_rate` → `LCR Rate`, `hqla_level` → `HQLA Level`).",
        "",
        "## Tables",
        "| File | Grain | Key | Rows |",
        "|---|---|---|---|",
    ]
    grains = {
        "dim_date": ("day", "date"), "dim_scenario": ("scenario", "scenario_key"), "dim_currency": ("currency", "currency_code"),
        "dim_segment": ("segment", "segment_code"), "dim_product": ("product (LCR parameters)", "product_code"),
        "dim_time_bucket": ("maturity bucket", "bucket_key"), "dim_contract": ("contract", "contract_id"),
        "fact_fx_rate": ("month-end × currency", "date + currency_code"),
        "fact_bank_position": ("contract × month-end (snapshot, semi-additive)", "date + contract_id"),
        "fact_hqla_holding": ("security × month-end (snapshot)", "date + security_id"),
        "fact_bank_cf_contractual": ("as-of ladder: date × product × currency × flow type", "composite"),
        "fact_bank_cf_stressed": ("scenario × day × product × currency × flow type (90 days)", "composite"),
        "scenario_parameter": ("scenario × LCR group", "scenario_key + lcr_group"),
        "ref_liquidity_metrics": ("month-end × scenario (reconciliation only)", "date + scenario_key"),
    }
    for name, (grain, key) in grains.items():
        lines.append(f"| `{name}.csv` | {grain} | {key} | {len(t[name]):,} |")
    lines += [
        "",
        "## LCR method (replicate in DAX, reconcile to `ref_liquidity_metrics`)",
        "- **HQLA:** unencumbered securities (`encumbered = 0`) at market value × (1 − `base_haircut` − scenario `haircut_addon`",
        "  for the product's `lcr_group`). Caps: L2B ≤ 15/85 × (L1 + L2A); L2A + L2B ≤ 2/3 × L1. HQLA = L1 + capped L2.",
        "- **Outflows (30 days):** per position, base × min(1, `lcr_rate` × `runoff_multiplier`), where base = `balance_rc` if",
        "  `lcr_basis = balance` (non-maturity deposits, undrawn facilities) else `principal_due_30d_rc` (term funding).",
        "- **Inflows (30 days):** `principal_due_30d_rc` × min(1, `lcr_rate` × `inflow_multiplier`) for `lcr_flow = inflow`;",
        "  capped at 75 % of outflows.",
        "- **LCR** = HQLA ÷ (outflows − capped inflows). BASE = Basel rates (multipliers 1).",
        "- **Survival days** (as-of only): days until HQLA + cumulative stressed net cash flow (`fact_bank_cf_stressed`) < 0;",
        f"  blank = survives the {HORIZON_DAYS}-day horizon.",
        "",
        "## Expected results",
        "| Scenario | LCR first month-end | LCR as-of | HQLA as-of (USD bn) | Net outflows as-of (USD bn) | Survival days |",
        "|---|---|---|---|---|---|",
    ]
    for s in SCENARIOS:
        sd = at.loc[s, "survival_days"]
        lines.append(f"| {s} | {first.loc[s, 'lcr_pct']:.1%} | {at.loc[s, 'lcr_pct']:.1%} | "
                     f"{at.loc[s, 'hqla_after_haircut_caps_rc'] / 1e9:,.2f} | {at.loc[s, 'net_outflows_rc'] / 1e9:,.2f} | "
                     f"{'> ' + str(HORIZON_DAYS) if pd.isna(sd) else int(sd)} |")
    lines += [
        "",
        "Storyline: the LCR drifts down over the year; all scenarios stay above 100 % except **COMBINED**, which breaches.",
        "Corporate non-operational deposits and committed facilities are the main stress drivers. The contractual ladder",
        "(`fact_bank_cf_contractual`) puts non-maturity deposits in O/N, so the cumulative contractual gap is negative in the",
        "short buckets; the stressed projection shows how long the HQLA buffer lasts.",
        "",
    ]
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(pathlib.Path(__file__).resolve().parents[1] / "data" / "liquidity_sample"))
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    products = pd.DataFrame(PRODUCTS, columns=PRODUCT_COLS).set_index("product_code", drop=False)
    fx = make_fx(rng)
    contracts = make_contracts(rng, products)
    positions = make_positions(rng, contracts, fx)
    contracts, positions = scale_to_targets(contracts, positions)

    params = pd.DataFrame([(s, g, 1.0, 1.0, 0.0) for s in SCENARIOS for g in LCR_GROUPS],
                          columns=["scenario_key", "lcr_group", "runoff_multiplier", "inflow_multiplier", "haircut_addon"])
    hq = make_hqla(rng, products, positions, params)
    params = solve_stress(products, positions, hq, params)
    contractual = make_contractual_cf(contracts, positions, fx)
    stressed = make_stressed_cf(contracts, positions, products, params)
    ref = make_ref_metrics(products, positions, hq, params, stressed)

    hq["market_value_local"] = hq.market_value_rc / hq.merge(fx, on=["date", "currency_code"]).rate_to_rc.values
    tables = {
        "dim_date": make_dim_date(max(contractual.date.max(), ASOF + pd.Timedelta(days=HORIZON_DAYS))),
        "dim_scenario": pd.DataFrame([("ACT", "Actual", "actual", 0), ("BASE", "Baseline (Basel rates)", "baseline", 1),
                                      ("IDIO", "Idiosyncratic stress", "stress", 2), ("MARKET", "Market-wide stress", "stress", 3),
                                      ("COMBINED", "Combined stress", "stress", 4)],
                                     columns=["scenario_key", "scenario_name", "scenario_type", "sort_order"]),
        "dim_currency": pd.DataFrame([("USD", "US dollar", 1.0, 1), ("EUR", "Euro", fx[(fx.date == ASOF) & (fx.currency_code == "EUR")].rate_to_rc.iloc[0], 0)],
                                     columns=["currency_code", "currency_name", "rate_to_rc_asof", "is_reporting_currency"]),
        "dim_segment": pd.DataFrame(SEGMENTS, columns=["segment_code", "segment_name"]),
        "dim_product": products.reset_index(drop=True),
        "dim_time_bucket": pd.DataFrame(BUCKETS, columns=["bucket_key", "bucket_label", "sort_order", "days_from", "days_to",
                                                          "in_lcr_30d", "in_1y"]),
        "dim_contract": contracts,
        "fact_fx_rate": fx,
        "fact_bank_position": positions,
        "fact_hqla_holding": hq[["date", "security_id", "security_name", "product_code", "currency_code", "hqla_level",
                                 "market_value_local", "market_value_rc", "base_haircut", "encumbered"]],
        "fact_bank_cf_contractual": contractual,
        "fact_bank_cf_stressed": stressed,
        "scenario_parameter": params,
        "ref_liquidity_metrics": ref,
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
            elif pd.api.types.is_float_dtype(df[col]) and col.endswith(("_rc", "_local")):
                df[col] = df[col].round(2)
        df.to_csv(out / f"{name}.csv", index=False)
    write_readme(out, tables)

    at = ref[ref.date == ASOF].set_index("scenario_key")
    print(f"Wrote {len(tables)} tables to {out}")
    for s in SCENARIOS:
        sd = at.loc[s, "survival_days"]
        print(f"  {s:<9} LCR {at.loc[s, 'lcr_pct']:6.1%}   survival {'>' + str(HORIZON_DAYS) if pd.isna(sd) else int(sd)} days")
    print("All checks passed.")


if __name__ == "__main__":
    main()
