"""
S3FRT — Scope 3 Financial Risk Translation Framework
=====================================================
Single multi-page Streamlit app with five modules:
  A - Data Ingestion    B - Financial Engine    C - Scenario Dashboard
  D - PUMA Validation   E - Intensity Normalisation
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from modules.data_loader import (
    load_firm_data, load_carbon_prices, get_anchor_rows, get_firm_list,
    SCENARIOS, HORIZONS,
)
from modules.financial_engine import (
    run_all_firms_all_scenarios, BIS_COEFFICIENT,
    DEFAULT_PASS_THROUGH, DEFAULT_TIER_WEIGHT,
)
from modules.dashboard import (
    COLORS, SCENARIO_COLORS, fig_carbon_price_curves,
    fig_ctl_bar, fig_ctl_trajectory, fig_ctl_trajectory_all_scenarios,
    build_metrics_table, get_materiality_flags,
)
from modules.validation import (
    run_puma_validation, run_all_validation_tests,
    PUMA_INTERNAL_EMISSIONS, PUMA_NZDPU_EMISSIONS, PUMA_NZ2050_PRICE_2030,
    PUMA_DISCLOSED_LOW, PUMA_DISCLOSED_HIGH,
)
from modules.intensity_view import fig_intensity_bar, compute_intensity_table

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="S3FRT — Scope 3 Financial Risk Translation",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .main .block-container { padding-top: 1.5rem; max-width: 1200px; }
    .glass-card {
        background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(12px);
        border: 1px solid rgba(100, 116, 139, 0.2); border-radius: 16px;
        padding: 1.5rem; margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(14, 165, 233, 0.1));
        border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 12px;
        padding: 1rem; text-align: center;
    }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #10b981; }
    .metric-label { font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
    .main-title {
        font-size: 2.2rem; font-weight: 700;
        background: linear-gradient(135deg, #10b981, #0ea5e9);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .sub-title { font-size: 1rem; color: #94a3b8; margin-bottom: 1.5rem; }
    .section-divider { border-top: 1px solid rgba(100,116,139,0.2); margin: 1.5rem 0; }
    .flag-red { color: #ef4444; font-weight: 600; }
    .flag-amber { color: #f59e0b; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(30, 41, 59, 0.6); border-radius: 8px;
        border: 1px solid rgba(100, 116, 139, 0.2); color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(16, 185, 129, 0.15) !important;
        border-color: rgba(16, 185, 129, 0.4) !important;
        color: #10b981 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Load data ────────────────────────────────────────────────────────────────
df = load_firm_data()
prices_df = load_carbon_prices()
all_firms = get_firm_list(df)
anchors = get_anchor_rows(df)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:0.5rem 0;">
        <div style="font-size:2rem;">🌍</div>
        <div style="font-size:1.2rem; font-weight:700;
             background:linear-gradient(135deg,#10b981,#0ea5e9);
             -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
            S3FRT Framework</div>
        <div style="font-size:0.7rem; color:#64748b;">Scope 3 Financial Risk Translation</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("**Model Parameters**")
    pass_through = st.slider("Pass-through rate", 0.0, 1.0, DEFAULT_PASS_THROUGH, 0.05,
                             help="Fraction of carbon cost passed through supply chain")
    tier_weight = st.slider("Tier propagation weight", 0.0, 0.50, DEFAULT_TIER_WEIGHT, 0.05,
                            help="Tier-2 supplier risk propagation multiplier")
    st.markdown(f"**BIS coefficient:** `{BIS_COEFFICIENT} bps` *(fixed — Ehlers et al. 2021)*",
                help="Applied to Scope 3 intensity as lower-bound proxy for credit risk premium")
    st.markdown("---")

    selected_firms = st.multiselect("Firms", all_firms, default=all_firms,
                                    help="Select firms for analysis")
    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.7rem; color:#475569;">
        Data: NZDPU, Corporate Reports, NGFS Phase V<br>
        Calibration: BIS WP 946 (Ehlers et al., 2021)<br>
        Sector: Apparel & Fashion
    </div>
    """, unsafe_allow_html=True)

# ─── Compute results ─────────────────────────────────────────────────────────
results = run_all_firms_all_scenarios(df, prices_df, pass_through, tier_weight,
                                      firms_filter=selected_firms if selected_firms else None)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_home, tab_scenario, tab_validation, tab_intensity = st.tabs([
    "🏠 Overview", "📊 Scenario Dashboard", "✅ PUMA Validation", "📈 Intensity View"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB: Overview
# ═══════════════════════════════════════════════════════════════════════════════
with tab_home:
    st.markdown('<div class="main-title">S3FRT Framework</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Translating Scope 3 value-chain emissions into '
        'carbon tax liability, EBITDA sensitivity, and cost-of-capital uplift for apparel firms.</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{len(anchors)}</div>'
                    f'<div class="metric-label">Firms (anchor rows)</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="metric-card"><div class="metric-value">3</div>'
                    '<div class="metric-label">NGFS Scenarios</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="metric-card"><div class="metric-value">4</div>'
                    '<div class="metric-label">Time Horizons</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="metric-card"><div class="metric-value">3</div>'
                    '<div class="metric-label">Financial Metrics</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Framework steps
    st.markdown("### The S3FRT Model — Four Steps")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="glass-card">
            <b style="color:#10b981;">Step 1 — Emission Input</b><br>
            <span style="color:#cbd5e1; font-size:0.9rem;">
            Cat 1 (Purchased Goods), Cat 4 (Upstream Transport), Cat 12 (End-of-Life).
            Cat 12 nulls imputed as 0 and flagged.</span>
        </div>
        <div class="glass-card">
            <b style="color:#10b981;">Step 2 — Carbon Price Mapping</b><br>
            <span style="color:#cbd5e1; font-size:0.9rem;">
            Three NGFS Phase V trajectories: Current Policies, Delayed Transition, Net Zero 2050
            across 2025/2030/2035/2040.</span>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="glass-card">
            <b style="color:#10b981;">Step 3 — Financial Metrics</b><br>
            <span style="color:#cbd5e1; font-size:0.9rem;">
            CTL = E × P × pass-through<br>
            ES% = CTL_adj / EBITDA × 100<br>
            CoC = 6.705 × intensity × multiplier (bps)</span>
        </div>
        <div class="glass-card">
            <b style="color:#10b981;">Step 4 — Tier Propagation</b><br>
            <span style="color:#cbd5e1; font-size:0.9rem;">
            CTL_adjusted = CTL × (1 + tier_weight). Captures Tier-2 upstream risk.</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Carbon price chart
    st.markdown("### NGFS Carbon Price Scenarios")
    st.plotly_chart(fig_carbon_price_curves(prices_df), use_container_width=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Firm sample table
    st.markdown("### Firm Sample (Anchor Rows)")
    summary_rows = []
    for _, r in anchors.iterrows():
        summary_rows.append({
            "Firm": r["firm"],
            "Anchor Year": int(r["year"]),
            "Cat 1 (tCO₂e)": f"{r['cat1_tco2e']:,.0f}" if pd.notna(r["cat1_tco2e"]) else "—",
            "Cat 4 (tCO₂e)": f"{r['cat4_tco2e']:,.0f}" if pd.notna(r["cat4_tco2e"]) else "—",
            "Cat 12 (tCO₂e)": f"{r['cat12_tco2e']:,.0f}" + (" ⚠️" if r.get("cat12_imputed") else ""),
            "Total Scope 3": f"{r['total_scope3_tco2e']:,.0f}",
            "EBITDA ($M)": f"${r['ebitda_usd']/1e6:,.0f}M" + (" ⚠️neg" if r.get("negative_ebitda") else ""),
            "Revenue ($M)": f"${r['revenue_usd']/1e6:,.0f}M",
        })
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
    st.caption("⚠️ = Cat 12 imputed as 0 (conservative) or negative EBITDA year")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB: Scenario Dashboard (Module C)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_scenario:
    st.markdown("### Scenario Dashboard")

    if results.empty:
        st.warning("No results — check firm selection.")
    else:
        sc1, sc2 = st.columns(2)
        with sc1:
            sel_scenario = st.selectbox("Scenario", SCENARIOS, index=2)
        with sc2:
            sel_horizon = st.selectbox("Time Horizon", HORIZONS, index=1)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # Bar chart: CTL by firm
        st.plotly_chart(fig_ctl_bar(results, sel_scenario, sel_horizon), use_container_width=True)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # Line chart: CTL trajectory over horizons — THE critical chart for DT divergence
        st.markdown("#### CTL Trajectory Over Time Horizons")
        st.caption("This chart reveals the Delayed Transition divergence at 2035/2040.")
        if selected_firms:
            st.plotly_chart(fig_ctl_trajectory_all_scenarios(results, selected_firms),
                            use_container_width=True)
            st.plotly_chart(fig_ctl_trajectory(results, sel_scenario, selected_firms),
                            use_container_width=True)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # Metrics table
        st.markdown(f"#### Full Metrics — {sel_scenario} @ {sel_horizon}")
        metrics_tbl = build_metrics_table(results, sel_scenario, sel_horizon)

        # Materiality flagging
        flagged = get_materiality_flags(results, sel_scenario, sel_horizon, threshold=5.0)
        if flagged:
            st.warning(f"⚠️ **Materiality threshold exceeded (ES% > 5%):** {', '.join(flagged)}")

        # Highlight rows with ES% > 5% using Streamlit's built-in styling
        def highlight_materiality(row):
            es_val = row["EBITDA Sens. (%)"]
            try:
                val = float(es_val.replace("%", ""))
                if val > 5.0:
                    return ["background-color: rgba(239, 68, 68, 0.2)"] * len(row)
            except (ValueError, AttributeError):
                pass
            return [""] * len(row)

        styled = metrics_tbl.style.apply(highlight_materiality, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)

        st.caption("Red highlight = EBITDA sensitivity > 5% (materiality threshold). "
                   "CoC uplift uses BIS Scope 1 coefficient (6.705 bps) applied to Scope 3 intensity "
                   "as a lower-bound proxy.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB: PUMA Validation (Module D)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_validation:
    st.markdown("### PUMA Controlled Comparability Test")

    puma = run_puma_validation(pass_through, tier_weight)

    st.markdown("""
    <div class="glass-card">
        <b style="color:#10b981;">Methodology</b><br>
        <span style="color:#cbd5e1; font-size:0.9rem;">
        PUMA uses IEA NZE by 2050 scenario ($130–$250/tCO₂e at 2030). S3FRT uses NGFS NZ2050
        at $183.30 — within that range. Matched emission base: 2.1M tCO₂e (PUMA internal figure,
        not NZDPU). Result falls within disclosed range, confirming directional consistency.
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Metrics
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">'
                    f'${puma["ctl_adj_internal_usd"]/1e6:,.1f}M</div>'
                    f'<div class="metric-label">S3FRT Estimate (Internal Base)</div></div>',
                    unsafe_allow_html=True)
    with c2:
        range_str = f"${PUMA_DISCLOSED_LOW/1e6:.0f}M – ${PUMA_DISCLOSED_HIGH/1e6:.0f}M"
        st.markdown(f'<div class="metric-card"><div class="metric-value">{range_str}</div>'
                    f'<div class="metric-label">PUMA Disclosed Range</div></div>',
                    unsafe_allow_html=True)
    with c3:
        status = "✅ Within Range" if puma["within_range"] else "❌ Outside Range"
        color = "#10b981" if puma["within_range"] else "#ef4444"
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{color}">'
                    f'{status}</div><div class="metric-label">Validation Result</div></div>',
                    unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Horizontal bar: PUMA range with S3FRT estimate plotted
    fig_puma = go.Figure()

    # Range bar
    fig_puma.add_trace(go.Bar(
        y=["PUMA Disclosed Range"], x=[(PUMA_DISCLOSED_HIGH - PUMA_DISCLOSED_LOW) / 1e6],
        base=[PUMA_DISCLOSED_LOW / 1e6], orientation="h",
        marker_color="rgba(249, 115, 22, 0.3)", marker_line=dict(color="#f97316", width=2),
        name="PUMA Range ($273M–$525M)",
        hovertemplate="Range: $273M–$525M<extra></extra>",
    ))

    # S3FRT internal estimate marker
    fig_puma.add_trace(go.Scatter(
        y=["PUMA Disclosed Range"], x=[puma["ctl_adj_internal_usd"] / 1e6],
        mode="markers+text", marker=dict(size=16, color="#10b981", symbol="diamond"),
        text=[f"${puma['ctl_adj_internal_usd']/1e6:,.1f}M"], textposition="top center",
        textfont=dict(color="#10b981", size=13),
        name="S3FRT (Internal Base)",
        hovertemplate="S3FRT Internal: $%{x:.1f}M<extra></extra>",
    ))

    # NZDPU estimate marker
    fig_puma.add_trace(go.Scatter(
        y=["PUMA Disclosed Range"], x=[puma["ctl_adj_nzdpu_usd"] / 1e6],
        mode="markers+text", marker=dict(size=14, color="#8b5cf6", symbol="circle"),
        text=[f"${puma['ctl_adj_nzdpu_usd']/1e6:,.1f}M"], textposition="bottom center",
        textfont=dict(color="#8b5cf6", size=12),
        name="S3FRT (NZDPU Base)",
        hovertemplate="S3FRT NZDPU: $%{x:.1f}M<extra></extra>",
    ))

    fig_puma.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#e2e8f0", size=13),
        margin=dict(l=60, r=40, t=50, b=40),
        title=dict(text="PUMA Validation — S3FRT vs Disclosed Range", font=dict(size=16), x=0.02),
        xaxis=dict(title="Carbon Tax Liability ($M)", gridcolor="rgba(100,116,139,0.2)"),
        yaxis=dict(gridcolor="rgba(100,116,139,0.2)"),
        legend=dict(bgcolor="rgba(30,41,59,0.7)", bordercolor="rgba(100,116,139,0.3)", borderwidth=1),
        height=250,
    )
    st.plotly_chart(fig_puma, use_container_width=True)

    # NZDPU vs Internal comparison
    st.markdown(f"""
    <div class="glass-card">
        <b style="color:#8b5cf6;">NZDPU-based result:</b>
        <span style="color:#cbd5e1;">${puma['ctl_adj_nzdpu_usd']/1e6:,.1f}M</span>
        — lower because NZDPU reports {PUMA_NZDPU_EMISSIONS/1e6:.1f}M tCO₂e vs PUMA's internal
        {PUMA_INTERNAL_EMISSIONS/1e6:.1f}M tCO₂e. This is a data-source gap, not a model error.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Validation tests
    st.markdown("### Internal Consistency Validation")
    if st.button("Run validation checks", type="primary"):
        tests = run_all_validation_tests(results, pass_through, tier_weight)
        for t in tests:
            icon = "✅" if t["passed"] else "❌"
            st.markdown(f"**{icon} {t['test']}** — {t['description']}")
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;Result: `{t['result']}`")
            st.markdown("")

        n_pass = sum(1 for t in tests if t["passed"])
        if n_pass == len(tests):
            st.success(f"All {len(tests)} validation tests passed.")
        else:
            st.error(f"{n_pass}/{len(tests)} tests passed.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB: Intensity View (Module E)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_intensity:
    st.markdown("### Revenue-Normalised Intensity View")
    st.caption("CTL per $1M revenue — enables cross-firm comparison independent of firm size.")

    if results.empty:
        st.warning("No results — check firm selection.")
    else:
        ic1, ic2 = st.columns(2)
        with ic1:
            int_scenario = st.selectbox("Scenario ", SCENARIOS, index=2, key="int_sc")
        with ic2:
            int_horizon = st.selectbox("Time Horizon ", HORIZONS, index=1, key="int_hz")

        st.plotly_chart(fig_intensity_bar(results, int_scenario, int_horizon),
                        use_container_width=True)

        # Table
        int_data = compute_intensity_table(results, int_scenario, int_horizon)
        int_tbl = pd.DataFrame({
            "Firm": int_data["firm"],
            "CTL Adjusted ($M)": int_data["ctl_adjusted_usd"].apply(lambda x: f"${x/1e6:,.1f}M"),
            "Revenue ($M)": int_data["revenue_usd"].apply(lambda x: f"${x/1e6:,.0f}M"),
            "CTL per $1M Rev ($K)": int_data["ctl_per_1m_rev"].apply(lambda x: f"${x/1e3:,.1f}K"),
        })
        st.dataframe(int_tbl, use_container_width=True, hide_index=True)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center; color:#475569; font-size:0.75rem; padding:0.5rem 0;">
    S3FRT Framework Prototype · Research Paper Companion Tool<br>
    Scope 3 Financial Risk Translation for Apparel Supply Chains<br>
    Built with Streamlit + Plotly · Data: NZDPU, NGFS Phase V, BIS WP 946
</div>
""", unsafe_allow_html=True)
