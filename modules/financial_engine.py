"""
Module B — Financial Translation Engine
Implements the S3FRT framework's three financial metrics + tier propagation.

Formulas:
  CTL = (Cat1 + Cat4 + Cat12) x carbon_price x pass_through_rate
  CTL_adjusted = CTL x (1 + tier_propagation_weight)
  ES% = CTL_adjusted / EBITDA x 100
  CoC_uplift_bps = 6.705 x (total_scope3 / (revenue / 1000)) x scenario_multiplier
"""

import pandas as pd
import numpy as np
from modules.data_loader import (
    load_carbon_prices, get_carbon_price, get_scenario_multiplier,
    get_anchor_rows, SCENARIOS, HORIZONS,
)

BIS_COEFFICIENT = 6.705
DEFAULT_PASS_THROUGH = 0.70
DEFAULT_TIER_WEIGHT = 0.15


def compute_ctl(total_emissions: float, carbon_price: float, pass_through: float) -> float:
    if total_emissions <= 0 or carbon_price <= 0:
        return 0.0
    return total_emissions * carbon_price * pass_through


def compute_ctl_adjusted(ctl: float, tier_weight: float) -> float:
    return ctl * (1.0 + tier_weight)


def compute_ebitda_sensitivity(ctl_adjusted: float, ebitda: float) -> float:
    """Returns percentage. Returns NaN for negative EBITDA."""
    if pd.isna(ebitda) or ebitda <= 0:
        return np.nan
    return (ctl_adjusted / ebitda) * 100.0


def compute_coc_uplift(total_emissions: float, revenue: float, scenario_multiplier: float) -> float:
    if total_emissions <= 0 or pd.isna(revenue) or revenue <= 0:
        return 0.0
    scope3_intensity = total_emissions / (revenue / 1000.0)
    return BIS_COEFFICIENT * scope3_intensity * scenario_multiplier


def run_single_firm(row: pd.Series, carbon_price: float, scenario: str,
                    scenario_multiplier: float, horizon: str,
                    pass_through: float = DEFAULT_PASS_THROUGH,
                    tier_weight: float = DEFAULT_TIER_WEIGHT) -> dict:
    """Run S3FRT for one firm-row at one scenario/horizon."""
    cat1 = float(row.get("cat1_tco2e", 0) or 0)
    cat4 = float(row.get("cat4_tco2e", 0) or 0)
    cat12 = float(row.get("cat12_tco2e", 0) or 0)
    total_e = cat1 + cat4 + cat12
    ebitda = row.get("ebitda_usd")
    revenue = row.get("revenue_usd")
    debt = row.get("total_debt_usd", 0)

    ctl = compute_ctl(total_e, carbon_price, pass_through)
    ctl_adj = compute_ctl_adjusted(ctl, tier_weight)
    es_pct = compute_ebitda_sensitivity(ctl_adj, ebitda)
    coc_bps = compute_coc_uplift(total_e, revenue, scenario_multiplier)

    return {
        "firm": row["firm"],
        "year": int(row["year"]),
        "scenario": scenario,
        "horizon": horizon,
        "carbon_price": carbon_price,
        "cat1_tco2e": cat1,
        "cat4_tco2e": cat4,
        "cat12_tco2e": cat12,
        "cat12_imputed": bool(row.get("cat12_imputed", False)),
        "total_scope3_tco2e": total_e,
        "ebitda_usd": ebitda,
        "revenue_usd": revenue,
        "total_debt_usd": debt,
        "negative_ebitda": bool(row.get("negative_ebitda", False)),
        "ctl_usd": ctl,
        "ctl_adjusted_usd": ctl_adj,
        "ebitda_sensitivity_pct": es_pct,
        "coc_uplift_bps": coc_bps,
        "pass_through": pass_through,
        "tier_weight": tier_weight,
    }


def run_all_firms_all_scenarios(df: pd.DataFrame, prices_df: pd.DataFrame,
                                 pass_through: float = DEFAULT_PASS_THROUGH,
                                 tier_weight: float = DEFAULT_TIER_WEIGHT,
                                 firms_filter: list = None) -> pd.DataFrame:
    """Run S3FRT for all anchor rows × all scenarios × all horizons."""
    anchors = get_anchor_rows(df)
    if firms_filter:
        anchors = anchors[anchors["firm"].isin(firms_filter)]

    results = []
    for _, row in anchors.iterrows():
        for scenario in SCENARIOS:
            sm = get_scenario_multiplier(scenario)
            for horizon in HORIZONS:
                cp = get_carbon_price(prices_df, scenario, horizon)
                results.append(run_single_firm(
                    row, cp, scenario, sm, horizon, pass_through, tier_weight
                ))

    return pd.DataFrame(results)
