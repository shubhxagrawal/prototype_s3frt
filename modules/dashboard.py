"""
Module C — Scenario Dashboard
Plotly chart builders for the S3FRT multi-scenario, multi-horizon dashboard.
"""

import plotly.graph_objects as go
import pandas as pd
import numpy as np

COLORS = {
    "emerald": "#10b981", "teal": "#14b8a6", "sky": "#0ea5e9",
    "violet": "#8b5cf6", "amber": "#f59e0b", "rose": "#f43f5e",
    "slate": "#64748b", "white": "#e2e8f0", "bg_dark": "#0f172a",
    "bg_card": "#1e293b",
}

SCENARIO_COLORS = {
    "Current Policies": "#f59e0b",
    "Delayed Transition": "#f97316",
    "Net Zero 2050": "#ef4444",
}

# Distinct colours for up to 20 firms
FIRM_PALETTE = [
    "#10b981", "#0ea5e9", "#8b5cf6", "#f59e0b", "#ef4444",
    "#ec4899", "#14b8a6", "#6366f1", "#f97316", "#84cc16",
    "#06b6d4", "#d946ef", "#eab308", "#22d3ee", "#a3e635",
    "#fb923c", "#c084fc", "#fbbf24", "#34d399", "#38bdf8",
]

_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=COLORS["white"], size=13),
    margin=dict(l=60, r=30, t=50, b=50),
    legend=dict(bgcolor="rgba(30,41,59,0.7)", bordercolor="rgba(100,116,139,0.3)",
                borderwidth=1, font=dict(size=11)),
    xaxis=dict(gridcolor="rgba(100,116,139,0.2)", zerolinecolor="rgba(100,116,139,0.3)"),
    yaxis=dict(gridcolor="rgba(100,116,139,0.2)", zerolinecolor="rgba(100,116,139,0.3)"),
)


def _apply(fig, title="", **kw):
    layout = {**_LAYOUT, **kw}
    if title:
        layout["title"] = dict(text=title, font=dict(size=16, color=COLORS["white"]), x=0.02)
    fig.update_layout(**layout)
    return fig


# ── Carbon price curves ──────────────────────────────────────────────────────
def fig_carbon_price_curves(prices_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    horizons = ["2025", "2030", "2035", "2040"]
    for _, row in prices_df.iterrows():
        sc = row["scenario"]
        fig.add_trace(go.Scatter(
            x=horizons, y=[row[y] for y in horizons], name=sc, mode="lines+markers",
            line=dict(width=3, color=SCENARIO_COLORS.get(sc, COLORS["slate"])),
            marker=dict(size=8),
            hovertemplate=f"<b>{sc}</b><br>%{{x}}: $%{{y:.1f}}/tCO₂e<extra></extra>",
        ))
    return _apply(fig, "NGFS Phase V Carbon Price Trajectories ($/tCO₂e)",
                  yaxis_title="Carbon Price ($/tCO₂e)", xaxis_title="Year")


# ── Bar chart: CTL_adjusted by firm for a selected scenario/horizon ──────────
def fig_ctl_bar(results_df: pd.DataFrame, scenario: str, horizon: str) -> go.Figure:
    mask = (results_df["scenario"] == scenario) & (results_df["horizon"] == horizon)
    data = results_df[mask].sort_values("ctl_adjusted_usd", ascending=False)
    fig = go.Figure(go.Bar(
        x=data["firm"], y=data["ctl_adjusted_usd"] / 1e6,
        marker_color=SCENARIO_COLORS.get(scenario, COLORS["emerald"]),
        hovertemplate="<b>%{x}</b><br>$%{y:.1f}M<extra></extra>",
    ))
    return _apply(fig, f"Adjusted CTL by Firm — {scenario} @ {horizon} ($M)",
                  yaxis_title="CTL Adjusted ($M)", xaxis_tickangle=-30)


# ── Line chart: CTL_adjusted over horizons for selected firms ────────────────
def fig_ctl_trajectory(results_df: pd.DataFrame, scenario: str, firms: list) -> go.Figure:
    fig = go.Figure()
    mask = (results_df["scenario"] == scenario) & (results_df["firm"].isin(firms))
    data = results_df[mask]
    for i, firm in enumerate(sorted(firms)):
        fd = data[data["firm"] == firm].sort_values("horizon")
        color = FIRM_PALETTE[i % len(FIRM_PALETTE)]
        fig.add_trace(go.Scatter(
            x=fd["horizon"], y=fd["ctl_adjusted_usd"] / 1e6, name=firm,
            mode="lines+markers", line=dict(width=3, color=color), marker=dict(size=8),
            hovertemplate=f"<b>{firm}</b><br>%{{x}}: $%{{y:.1f}}M<extra></extra>",
        ))
    return _apply(fig, f"CTL Adjusted Trajectory — {scenario}",
                  yaxis_title="CTL Adjusted ($M)", xaxis_title="Time Horizon")


# ── Line chart: CTL_adjusted over horizons, all 3 scenarios overlaid (DT divergence) ──
def fig_ctl_trajectory_all_scenarios(results_df: pd.DataFrame, firms: list) -> go.Figure:
    fig = go.Figure()
    mask = results_df["firm"].isin(firms)
    data = results_df[mask]

    # Aggregate across selected firms per scenario/horizon
    agg = data.groupby(["scenario", "horizon"])["ctl_adjusted_usd"].sum().reset_index()

    for sc in ["Current Policies", "Delayed Transition", "Net Zero 2050"]:
        sd = agg[agg["scenario"] == sc].sort_values("horizon")
        color = SCENARIO_COLORS[sc]
        dash = "dash" if sc == "Delayed Transition" else "solid"
        fig.add_trace(go.Scatter(
            x=sd["horizon"], y=sd["ctl_adjusted_usd"] / 1e6, name=sc,
            mode="lines+markers", line=dict(width=3, color=color, dash=dash),
            marker=dict(size=9),
            hovertemplate=f"<b>{sc}</b><br>%{{x}}: $%{{y:.1f}}M<extra></extra>",
        ))

    title_suffix = f"({len(firms)} firms)" if len(firms) > 1 else firms[0]
    return _apply(fig, f"Scenario Divergence — Aggregate CTL ({title_suffix})",
                  yaxis_title="Total CTL Adjusted ($M)", xaxis_title="Time Horizon")


# ── Metrics summary table ────────────────────────────────────────────────────
def build_metrics_table(results_df: pd.DataFrame, scenario: str, horizon: str) -> pd.DataFrame:
    mask = (results_df["scenario"] == scenario) & (results_df["horizon"] == horizon)
    data = results_df[mask].sort_values("ctl_adjusted_usd", ascending=False).copy()

    table = pd.DataFrame({
        "Firm": data["firm"],
        "Scope 3 (tCO₂e)": data["total_scope3_tco2e"].apply(lambda x: f"{x:,.0f}"),
        "CTL Adjusted ($M)": data["ctl_adjusted_usd"].apply(lambda x: f"${x/1e6:,.1f}M"),
        "EBITDA Sens. (%)": data.apply(
            lambda r: "N/A (negative EBITDA)" if r["negative_ebitda"]
            else (f"{r['ebitda_sensitivity_pct']:.2f}%" if pd.notna(r["ebitda_sensitivity_pct"]) else "N/A"),
            axis=1
        ),
        "CoC Uplift (bps)": data["coc_uplift_bps"].apply(lambda x: f"{x:.2f}"),
        "Cat12 Imputed": data["cat12_imputed"].apply(lambda x: "⚠️ Yes" if x else ""),
    })
    return table.reset_index(drop=True)


def get_materiality_flags(results_df: pd.DataFrame, scenario: str, horizon: str,
                          threshold: float = 5.0) -> list:
    """Return firm names where ES% exceeds materiality threshold."""
    mask = (results_df["scenario"] == scenario) & (results_df["horizon"] == horizon)
    data = results_df[mask]
    flagged = data[data["ebitda_sensitivity_pct"] > threshold]["firm"].tolist()
    return flagged
