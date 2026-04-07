"""
Module D — PUMA Validation Module
Controlled single-firm comparability test + internal consistency validation runner.
"""

import pandas as pd
import numpy as np
from modules.financial_engine import (
    compute_ctl, compute_ctl_adjusted, compute_ebitda_sensitivity,
    DEFAULT_PASS_THROUGH, DEFAULT_TIER_WEIGHT,
)

# PUMA validation constants
PUMA_INTERNAL_EMISSIONS = 2_100_000  # tCO2e (Cat1 only, PUMA internal figure)
PUMA_NZDPU_EMISSIONS = 1_533_896    # tCO2e (NZDPU-based total)
PUMA_NZ2050_PRICE_2030 = 183.30     # $/tCO2e
PUMA_DISCLOSED_LOW = 273_000_000    # $273M
PUMA_DISCLOSED_HIGH = 525_000_000   # $525M


def run_puma_validation(pass_through: float = DEFAULT_PASS_THROUGH,
                        tier_weight: float = DEFAULT_TIER_WEIGHT) -> dict:
    """Run S3FRT with PUMA's internal emission base at NZ2050 2030 pricing."""
    # Using PUMA internal emission base
    ctl_internal = compute_ctl(PUMA_INTERNAL_EMISSIONS, PUMA_NZ2050_PRICE_2030, pass_through)
    ctl_adj_internal = compute_ctl_adjusted(ctl_internal, tier_weight)

    # Using NZDPU emission base
    ctl_nzdpu = compute_ctl(PUMA_NZDPU_EMISSIONS, PUMA_NZ2050_PRICE_2030, pass_through)
    ctl_adj_nzdpu = compute_ctl_adjusted(ctl_nzdpu, tier_weight)

    within_range = PUMA_DISCLOSED_LOW <= ctl_adj_internal <= PUMA_DISCLOSED_HIGH

    return {
        "internal_emissions_tco2e": PUMA_INTERNAL_EMISSIONS,
        "nzdpu_emissions_tco2e": PUMA_NZDPU_EMISSIONS,
        "carbon_price": PUMA_NZ2050_PRICE_2030,
        "ctl_adj_internal_usd": ctl_adj_internal,
        "ctl_adj_nzdpu_usd": ctl_adj_nzdpu,
        "disclosed_low_usd": PUMA_DISCLOSED_LOW,
        "disclosed_high_usd": PUMA_DISCLOSED_HIGH,
        "within_range": within_range,
    }


# ── Internal consistency validation tests ─────────────────────────────────────

def test_boundary(pass_through: float = DEFAULT_PASS_THROUGH,
                  tier_weight: float = DEFAULT_TIER_WEIGHT) -> dict:
    """When total_scope3 = 0, CTL must = 0."""
    ctl = compute_ctl(0, 183.30, pass_through)
    ctl_adj = compute_ctl_adjusted(ctl, tier_weight)
    passed = ctl_adj == 0.0
    return {"test": "Boundary Test", "description": "total_scope3 = 0 → CTL = 0",
            "result": ctl_adj, "passed": passed}


def test_linearity(pass_through: float = DEFAULT_PASS_THROUGH,
                   tier_weight: float = DEFAULT_TIER_WEIGHT) -> dict:
    """Doubling emissions must exactly double CTL at fixed carbon price."""
    e1 = 1_000_000
    price = 100.0
    ctl1 = compute_ctl_adjusted(compute_ctl(e1, price, pass_through), tier_weight)
    ctl2 = compute_ctl_adjusted(compute_ctl(e1 * 2, price, pass_through), tier_weight)
    passed = abs(ctl2 - 2 * ctl1) < 0.01
    return {"test": "Linearity Test", "description": "2× emissions → 2× CTL",
            "result": f"CTL({e1:,})=${ctl1/1e6:.2f}M, CTL({2*e1:,})=${ctl2/1e6:.2f}M",
            "passed": passed}


def test_monotonicity(results_df: pd.DataFrame) -> dict:
    """For every firm at every horizon: NZ2050 CTL > DT CTL > CP CTL."""
    failures = []
    firms = results_df["firm"].unique()
    horizons = results_df["horizon"].unique()

    for firm in firms:
        for h in horizons:
            fd = results_df[(results_df["firm"] == firm) & (results_df["horizon"] == h)]
            cp_val = fd[fd["scenario"] == "Current Policies"]["ctl_adjusted_usd"].values
            dt_val = fd[fd["scenario"] == "Delayed Transition"]["ctl_adjusted_usd"].values
            nz_val = fd[fd["scenario"] == "Net Zero 2050"]["ctl_adjusted_usd"].values

            if len(cp_val) == 0 or len(dt_val) == 0 or len(nz_val) == 0:
                continue

            if not (nz_val[0] >= dt_val[0] >= cp_val[0]):
                failures.append(f"{firm} @ {h}")

    passed = len(failures) == 0
    desc = "NZ2050 ≥ DT ≥ CP for all firm-horizons"
    result = "All pass" if passed else f"Failures: {', '.join(failures)}"
    return {"test": "Monotonicity Test", "description": desc,
            "result": result, "passed": passed}


def test_scenario_divergence(results_df: pd.DataFrame) -> dict:
    """DT @ 2030 == CP @ 2030 (within rounding); DT @ 2035 >> CP @ 2035."""
    # Aggregate across all firms
    agg = results_df.groupby(["scenario", "horizon"])["ctl_adjusted_usd"].sum().reset_index()

    dt_2030 = agg[(agg["scenario"] == "Delayed Transition") & (agg["horizon"] == "2030")]["ctl_adjusted_usd"].values
    cp_2030 = agg[(agg["scenario"] == "Current Policies") & (agg["horizon"] == "2030")]["ctl_adjusted_usd"].values
    dt_2035 = agg[(agg["scenario"] == "Delayed Transition") & (agg["horizon"] == "2035")]["ctl_adjusted_usd"].values
    cp_2035 = agg[(agg["scenario"] == "Current Policies") & (agg["horizon"] == "2035")]["ctl_adjusted_usd"].values

    if len(dt_2030) == 0 or len(cp_2030) == 0 or len(dt_2035) == 0 or len(cp_2035) == 0:
        return {"test": "Scenario Divergence", "description": "DT=CP@2030, DT>>CP@2035",
                "result": "Insufficient data", "passed": False}

    # DT and CP use same carbon price at 2030
    match_2030 = abs(dt_2030[0] - cp_2030[0]) < 1.0  # within $1
    diverge_2035 = dt_2035[0] > cp_2035[0] * 3  # DT should be ~10x CP at 2035

    passed = match_2030 and diverge_2035
    result = (f"2030: DT=${dt_2030[0]/1e6:.1f}M vs CP=${cp_2030[0]/1e6:.1f}M "
              f"({'MATCH' if match_2030 else 'MISMATCH'}); "
              f"2035: DT=${dt_2035[0]/1e6:.1f}M vs CP=${cp_2035[0]/1e6:.1f}M "
              f"({'DIVERGED' if diverge_2035 else 'NOT DIVERGED'})")
    return {"test": "Scenario Divergence", "description": "DT=CP@2030, DT>>CP@2035",
            "result": result, "passed": passed}


def run_all_validation_tests(results_df: pd.DataFrame,
                              pass_through: float = DEFAULT_PASS_THROUGH,
                              tier_weight: float = DEFAULT_TIER_WEIGHT) -> list:
    """Run all four internal consistency tests."""
    return [
        test_boundary(pass_through, tier_weight),
        test_linearity(pass_through, tier_weight),
        test_monotonicity(results_df),
        test_scenario_divergence(results_df),
    ]
