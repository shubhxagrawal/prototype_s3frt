"""
Module E — Intensity Normalisation View
CTL per $1M revenue for cross-firm comparison independent of firm size.
"""

import plotly.graph_objects as go
import pandas as pd
from modules.dashboard import COLORS, SCENARIO_COLORS, _apply


def compute_intensity_table(results_df: pd.DataFrame, scenario: str, horizon: str) -> pd.DataFrame:
    """Compute CTL per $1M revenue for all firms at given scenario/horizon."""
    mask = (results_df["scenario"] == scenario) & (results_df["horizon"] == horizon)
    data = results_df[mask].copy()
    data["ctl_per_1m_rev"] = data.apply(
        lambda r: (r["ctl_adjusted_usd"] / (r["revenue_usd"] / 1e6))
        if pd.notna(r["revenue_usd"]) and r["revenue_usd"] > 0 else 0.0,
        axis=1,
    )
    return data.sort_values("ctl_per_1m_rev", ascending=False)


def fig_intensity_bar(results_df: pd.DataFrame, scenario: str, horizon: str) -> go.Figure:
    """Ranked bar chart of CTL per $1M revenue."""
    data = compute_intensity_table(results_df, scenario, horizon)
    color = SCENARIO_COLORS.get(scenario, COLORS["emerald"])

    fig = go.Figure(go.Bar(
        x=data["firm"], y=data["ctl_per_1m_rev"] / 1e3,
        marker_color=color,
        hovertemplate="<b>%{x}</b><br>$%{y:.1f}K per $1M revenue<extra></extra>",
    ))
    return _apply(fig, f"Revenue-Normalised CTL — {scenario} @ {horizon} ($K per $1M Revenue)",
                  yaxis_title="CTL per $1M Revenue ($K)", xaxis_tickangle=-30)
