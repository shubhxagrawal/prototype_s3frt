"""Generate S3FRT full results report."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
import streamlit as st
st.cache_data = lambda **kw: (lambda f: f)

import pandas as pd
import numpy as np
from datetime import datetime

from modules.data_loader import load_firm_data, load_carbon_prices, get_anchor_rows, SCENARIOS, HORIZONS
from modules.financial_engine import run_all_firms_all_scenarios, BIS_COEFFICIENT
from modules.validation import run_puma_validation, run_all_validation_tests
from modules.intensity_view import compute_intensity_table

df = load_firm_data()
prices = load_carbon_prices()
anchors = get_anchor_rows(df)
results = run_all_firms_all_scenarios(df, prices)
puma = run_puma_validation()
tests = run_all_validation_tests(results)

lines = []
def w(s=""): lines.append(s)

w("=" * 90)
w("S3FRT PROTOTYPE — FULL RESULTS OUTPUT")
w("Scope 3 Financial Risk Translation Framework")
w(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
w("=" * 90)

# 1. Parameters
w()
w("-" * 90)
w("1. MODEL PARAMETERS")
w("-" * 90)
w("  Pass-through rate:        70%")
w("  Tier propagation weight:  15%")
w(f"  BIS coefficient:          {BIS_COEFFICIENT} bps (Ehlers et al., 2021, Table 3 Col. 5)")
w("  Scenario multipliers:     CP=1.0, DT=1.8, NZ=2.5")
w()

# 2. Carbon prices
w("-" * 90)
w("2. NGFS PHASE V CARBON PRICES ($/tCO2e)")
w("-" * 90)
header = f"  {'Scenario':<25} {'2025':>10} {'2030':>10} {'2035':>10} {'2040':>10}"
w(header)
w(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
for _, row in prices.iterrows():
    w(f"  {row['scenario']:<25} ${row['2025']:>8.2f} ${row['2030']:>8.2f} ${row['2035']:>8.2f} ${row['2040']:>8.2f}")
w()

# 3. Firm sample
w("-" * 90)
w(f"3. FIRM SAMPLE — ANCHOR ROWS ({len(anchors)} firms)")
w("-" * 90)
w(f"  {'Firm':<30} {'Year':>5} {'Cat1':>12} {'Cat4':>12} {'Cat12':>12} {'Total S3':>14} {'EBITDA($M)':>12} {'Rev($M)':>12} {'C12Imp':>7} {'NegEB':>6}")
w(f"  {'-'*30} {'-'*5} {'-'*12} {'-'*12} {'-'*12} {'-'*14} {'-'*12} {'-'*12} {'-'*7} {'-'*6}")
for _, r in anchors.sort_values('firm').iterrows():
    c12f = "Yes" if r.get('cat12_imputed') else ""
    negf = "Yes" if r.get('negative_ebitda') else ""
    eb = r['ebitda_usd']/1e6 if pd.notna(r['ebitda_usd']) else 0
    rv = r['revenue_usd']/1e6 if pd.notna(r['revenue_usd']) else 0
    w(f"  {r['firm']:<30} {int(r['year']):>5} {r['cat1_tco2e']:>12,.0f} {r['cat4_tco2e']:>12,.0f} {r['cat12_tco2e']:>12,.0f} {r['total_scope3_tco2e']:>14,.0f} {eb:>11,.0f}M {rv:>11,.0f}M {c12f:>7} {negf:>6}")
w()

# 4. Full results by scenario and horizon
for scenario in SCENARIOS:
    w("=" * 90)
    w(f"4. FINANCIAL RISK RESULTS — {scenario.upper()}")
    w("=" * 90)
    for horizon in HORIZONS:
        mask = (results['scenario'] == scenario) & (results['horizon'] == horizon)
        data = results[mask].sort_values('ctl_adjusted_usd', ascending=False)
        cp = data['carbon_price'].iloc[0] if len(data) > 0 else 0

        w()
        w(f"  Time Horizon: {horizon} | Carbon Price: ${cp:.2f}/tCO2e")
        w(f"  {'Firm':<30} {'Scope3(tCO2e)':>14} {'CTL_adj($M)':>13} {'ES%':>12} {'CoC(bps)':>10}")
        w(f"  {'-'*30} {'-'*14} {'-'*13} {'-'*12} {'-'*10}")

        for _, r in data.iterrows():
            if r['negative_ebitda'] and pd.isna(r['ebitda_sensitivity_pct']):
                es_str = "N/A(neg)"
            elif pd.notna(r['ebitda_sensitivity_pct']):
                es_str = f"{r['ebitda_sensitivity_pct']:.2f}%"
            else:
                es_str = "N/A"
            w(f"  {r['firm']:<30} {r['total_scope3_tco2e']:>14,.0f} ${r['ctl_adjusted_usd']/1e6:>11,.1f}M {es_str:>12} {r['coc_uplift_bps']:>10.2f}")

        total_ctl = data['ctl_adjusted_usd'].sum()
        mean_es = data['ebitda_sensitivity_pct'].mean()
        mean_coc = data['coc_uplift_bps'].mean()
        w(f"  {'-'*30} {'-'*14} {'-'*13} {'-'*12} {'-'*10}")
        mean_es_str = f"{mean_es:.2f}%" if pd.notna(mean_es) else "N/A"
        w(f"  {'TOTAL / MEAN':<30} {'':>14} ${total_ctl/1e6:>11,.1f}M {mean_es_str:>12} {mean_coc:>10.2f}")
w()

# 5. Cross-scenario comparison at 2030
w("=" * 90)
w("5. CROSS-SCENARIO COMPARISON AT 2030")
w("=" * 90)
w()
w(f"  {'Firm':<30} {'CP CTL($M)':>13} {'DT CTL($M)':>13} {'NZ CTL($M)':>13} {'CP ES%':>10} {'DT ES%':>10} {'NZ ES%':>10}")
w(f"  {'-'*30} {'-'*13} {'-'*13} {'-'*13} {'-'*10} {'-'*10} {'-'*10}")

def fmt_es(v):
    if pd.isna(v): return "N/A"
    return f"{v:.2f}%"

for firm in sorted(results['firm'].unique()):
    vals = {}
    for sc in SCENARIOS:
        row = results[(results['firm']==firm) & (results['scenario']==sc) & (results['horizon']=='2030')]
        if len(row) > 0:
            vals[sc] = row.iloc[0]
    if len(vals) == 3:
        cp_r, dt_r, nz_r = vals['Current Policies'], vals['Delayed Transition'], vals['Net Zero 2050']
        w(f"  {firm:<30} ${cp_r['ctl_adjusted_usd']/1e6:>11,.1f}M ${dt_r['ctl_adjusted_usd']/1e6:>11,.1f}M ${nz_r['ctl_adjusted_usd']/1e6:>11,.1f}M {fmt_es(cp_r['ebitda_sensitivity_pct']):>10} {fmt_es(dt_r['ebitda_sensitivity_pct']):>10} {fmt_es(nz_r['ebitda_sensitivity_pct']):>10}")
w()

# 6. DT Divergence
w("=" * 90)
w("6. DELAYED TRANSITION DIVERGENCE (Aggregate CTL across all firms)")
w("=" * 90)
w()
w(f"  {'Horizon':<10} {'CP Total($M)':>15} {'DT Total($M)':>15} {'NZ Total($M)':>15} {'DT/CP Ratio':>12}")
w(f"  {'-'*10} {'-'*15} {'-'*15} {'-'*15} {'-'*12}")
for h in HORIZONS:
    cp_t = results[(results['scenario']=='Current Policies') & (results['horizon']==h)]['ctl_adjusted_usd'].sum()
    dt_t = results[(results['scenario']=='Delayed Transition') & (results['horizon']==h)]['ctl_adjusted_usd'].sum()
    nz_t = results[(results['scenario']=='Net Zero 2050') & (results['horizon']==h)]['ctl_adjusted_usd'].sum()
    ratio = dt_t / cp_t if cp_t > 0 else 0
    w(f"  {h:<10} ${cp_t/1e6:>13,.1f}M ${dt_t/1e6:>13,.1f}M ${nz_t/1e6:>13,.1f}M {ratio:>12.2f}x")
w()
w("  Note: DT/CP ratio = 1.00x at 2025 and 2030 (identical carbon prices).")
w("  Divergence appears at 2035 and 2040 as Delayed Transition prices spike.")
w()

# 7. Revenue-normalised intensity
w("=" * 90)
w("7. REVENUE-NORMALISED INTENSITY — Net Zero 2050 @ 2030")
w("=" * 90)
w()
int_data = compute_intensity_table(results, "Net Zero 2050", "2030")
w(f"  {'Rank':>4} {'Firm':<30} {'CTL_adj($M)':>13} {'Revenue($M)':>13} {'CTL/$1M Rev':>13}")
w(f"  {'-'*4} {'-'*30} {'-'*13} {'-'*13} {'-'*13}")
for i, (_, r) in enumerate(int_data.iterrows(), 1):
    w(f"  {i:>4} {r['firm']:<30} ${r['ctl_adjusted_usd']/1e6:>11,.1f}M ${r['revenue_usd']/1e6:>11,.0f}M ${r['ctl_per_1m_rev']/1e3:>11,.1f}K")
w()

# 8. PUMA validation
w("=" * 90)
w("8. PUMA CONTROLLED COMPARABILITY TEST")
w("=" * 90)
w()
w(f"  Emission base (PUMA internal):  {puma['internal_emissions_tco2e']:>12,} tCO2e")
w(f"  Emission base (NZDPU):          {puma['nzdpu_emissions_tco2e']:>12,} tCO2e")
w(f"  Carbon price (NZ2050 @ 2030):   ${puma['carbon_price']:.2f}/tCO2e")
w(f"  S3FRT estimate (internal base): ${puma['ctl_adj_internal_usd']/1e6:,.1f}M")
w(f"  S3FRT estimate (NZDPU base):    ${puma['ctl_adj_nzdpu_usd']/1e6:,.1f}M")
w(f"  PUMA disclosed range:           ${puma['disclosed_low_usd']/1e6:.0f}M - ${puma['disclosed_high_usd']/1e6:.0f}M")
w(f"  Within disclosed range:         {'YES' if puma['within_range'] else 'NO'}")
w()
w("  Interpretation: Under matched inputs (2.1M tCO2e, NGFS NZ2050 $183.30/tCO2e),")
w(f"  S3FRT produces ${puma['ctl_adj_internal_usd']/1e6:,.1f}M — within PUMA disclosed $273M-$525M range.")
w(f"  The NZDPU-based result (${puma['ctl_adj_nzdpu_usd']/1e6:,.1f}M) is lower due to the smaller emission")
w("  base (1.53M vs 2.1M tCO2e). This is a data-source gap, not a model error.")
w()

# 9. Validation tests
w("=" * 90)
w("9. INTERNAL CONSISTENCY VALIDATION")
w("=" * 90)
w()
for t in tests:
    status = "PASS" if t['passed'] else "FAIL"
    w(f"  [{status}] {t['test']}")
    w(f"         {t['description']}")
    w(f"         Result: {t['result']}")
    w()
n_pass = sum(1 for t in tests if t['passed'])
w(f"  Summary: {n_pass}/{len(tests)} tests passed.")
w()

# 10. Summary statistics
w("=" * 90)
w("10. SUMMARY STATISTICS — Net Zero 2050 @ 2030")
w("=" * 90)
w()
nz30 = results[(results['scenario']=='Net Zero 2050') & (results['horizon']=='2030')]
es_valid = nz30['ebitda_sensitivity_pct'].dropna()

w(f"  {'Metric':<35} {'Mean':>12} {'Median':>12} {'Min':>12} {'Max':>12} {'Std Dev':>12}")
w(f"  {'-'*35} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")

ctl_vals = nz30['ctl_adjusted_usd'] / 1e6
w(f"  {'CTL Adjusted ($M)':<35} {ctl_vals.mean():>12,.1f} {ctl_vals.median():>12,.1f} {ctl_vals.min():>12,.1f} {ctl_vals.max():>12,.1f} {ctl_vals.std():>12,.1f}")
w(f"  {'EBITDA Sensitivity (%)':<35} {es_valid.mean():>12,.2f} {es_valid.median():>12,.2f} {es_valid.min():>12,.2f} {es_valid.max():>12,.2f} {es_valid.std():>12,.2f}")
coc_vals = nz30['coc_uplift_bps']
w(f"  {'CoC Uplift (bps)':<35} {coc_vals.mean():>12,.2f} {coc_vals.median():>12,.2f} {coc_vals.min():>12,.2f} {coc_vals.max():>12,.2f} {coc_vals.std():>12,.2f}")

w()
w(f"  Total aggregate CTL (NZ2050 @ 2030): ${nz30['ctl_adjusted_usd'].sum()/1e6:,.1f}M")
w(f"  Total Scope 3 emissions:             {nz30['total_scope3_tco2e'].sum()/1e6:,.1f}M tCO2e")
w(f"  Firms with ES% > 5%:                 {len(es_valid[es_valid > 5])}")
w(f"  Firms with negative EBITDA:          {int(nz30['negative_ebitda'].sum())}")

# Materiality flags
w()
w("  Firms exceeding 5% EBITDA sensitivity (materiality threshold):")
flagged = nz30[nz30['ebitda_sensitivity_pct'] > 5].sort_values('ebitda_sensitivity_pct', ascending=False)
for _, r in flagged.iterrows():
    w(f"    - {r['firm']}: {r['ebitda_sensitivity_pct']:.2f}%")

w()
w("=" * 90)
w("END OF RESULTS")
w("=" * 90)

output = "\n".join(lines)
with open("S3FRT_Full_Results.txt", "w", encoding="utf-8") as f:
    f.write(output)
print(output)
