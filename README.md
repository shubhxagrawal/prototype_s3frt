# S3FRT — Scope 3 Financial Risk Translation Framework

🌍 **A novel framework for translating corporate Scope 3 GHG emissions into quantified financial risk metrics**

## Overview

S3FRT (Scope 3 Financial Risk Translation) is a research prototype that converts a firm's disclosed Scope 3 greenhouse gas emissions (in tCO₂e) into actionable financial risk metrics:

- **Carbon Tax Liability (CTL)** — Direct financial exposure in USD
- **EBITDA Sensitivity (%)** — Earnings impact as a percentage
- **Cost-of-Capital Uplift (bps)** — Financing cost premium in basis points

The framework applies NGFS Phase V carbon price scenarios across multiple time horizons (2025-2040), enabling firms to quantify their climate transition risk exposure.

## Key Features

- 📊 **Interactive Streamlit Dashboard** — Multi-page app with scenario analysis, visualizations, and firm comparisons
- 🔬 **18 Apparel Firms Analyzed** — Real-world data from H&M, Nike, Adidas, PUMA, Inditex, and more
- 📈 **3 NGFS Scenarios** — Current Policies, Delayed Transition, and Net Zero 2050
- ⏱️ **4 Time Horizons** — 2025, 2030, 2035, and 2040 projections
- ✅ **Validated Model** — PUMA controlled comparability test confirms estimates within disclosed range

## Installation

```bash
# Clone or download the repository
cd prototype

# Install dependencies
pip install -r requirements.txt
```

### Requirements

- Python 3.8+
- streamlit >= 1.32
- plotly >= 5.20
- pandas >= 2.0
- openpyxl >= 3.1
- numpy >= 1.26

## Usage

### Run the Interactive Dashboard

```bash
streamlit run app.py
```

This launches a multi-page Streamlit application with five modules:

| Module | Description |
|--------|-------------|
| **A - Data Ingestion** | Load and preview firm emission data |
| **B - Financial Engine** | Calculate CTL, EBITDA sensitivity, and CoC uplift |
| **C - Scenario Dashboard** | Interactive scenario analysis and visualizations |
| **D - PUMA Validation** | Controlled comparability validation test |
| **E - Intensity View** | Revenue-normalized intensity rankings |

### Generate Full Results Report

```bash
python generate_results.py
```

This produces `S3FRT_Full_Results.txt` with comprehensive results for all 18 firms across all scenarios and horizons (216 data points).

## Project Structure

```
prototype/
├── app.py                    # Main Streamlit application
├── generate_results.py       # Full results report generator
├── requirements.txt          # Python dependencies
├── data/
│   ├── s3frt_dataset_updated.xlsx   # Firm emission and financial data
│   └── ngfs_carbon_prices.csv       # NGFS Phase V carbon prices
├── modules/
│   ├── data_loader.py        # Data ingestion and preprocessing
│   ├── financial_engine.py   # Core financial calculation engine
│   ├── dashboard.py          # Visualization and charting functions
│   ├── validation.py         # PUMA validation and consistency tests
│   └── intensity_view.py     # Revenue-normalized intensity analysis
└── S3FRT_Full_Results.txt    # Generated results output
```

## The S3FRT Model

### Financial Translation Formulas

```
CTL = (Cat1 + Cat4 + Cat12) × carbon_price × pass_through_rate
CTL_adjusted = CTL × (1 + tier_propagation_weight)
ES% = CTL_adjusted / EBITDA × 100
CoC_uplift_bps = 6.705 × (total_scope3 / (revenue / 1000)) × scenario_multiplier
```

### Default Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Pass-through rate | 70% | Literature estimate |
| Tier propagation weight | 15% | Supply chain adjustment |
| BIS coefficient | 6.705 bps | Ehlers et al. (2021), Table 3 Col. 5 |

### Emission Categories Analyzed

- **Category 1** — Purchased goods (raw materials: cotton, synthetics, dyes)
- **Category 4** — Upstream transportation and distribution
- **Category 12** — End-of-life treatment of sold products

## NGFS Carbon Price Scenarios

| Scenario | 2025 | 2030 | 2035 | 2040 |
|----------|------|------|------|------|
| Current Policies | $10.69 | $10.30 | $10.16 | $10.25 |
| Delayed Transition | $10.69 | $10.30 | $98.90 | $160.20 |
| Net Zero 2050 | $98.38 | $183.30 | $294.95 | $433.77 |

## Validation

The prototype includes four internal consistency tests:

1. **Boundary Test** — Validates edge case handling
2. **Linearity Test** — Confirms proportional scaling
3. **Monotonicity Test** — Verifies increasing prices yield increasing CTL
4. **Scenario Divergence** — Confirms DT diverges from CP at 2035+

**PUMA Controlled Comparability Test:**
- S3FRT estimate: $309.9M (using 2.1M tCO₂e at $183.30/tCO₂e)
- PUMA disclosed range: $273M–$525M
- Result: ✅ Within range

## Research Context

This prototype operationalizes a research framework addressing a gap in sustainability accounting literature. While PCAF provides investor-side financed emissions accounting, no prior model translates a corporation's own Scope 3 value-chain emissions into firm-level financial risk metrics under regulatory carbon pricing scenarios.

**Theoretical Foundation:** Resource Dependence Theory (Pfeffer & Salancik, 1978)

**Sector Focus:** Apparel and fashion — chosen because Scope 3 represents 90-95% of total emissions, the highest share of any sector.

## License

Research prototype — for academic and research purposes.

## Acknowledgments

- NGFS for Phase V carbon price scenarios
- NZDPU and corporate sustainability reports for emission data
- BIS Working Paper 946 for the cost-of-capital coefficient
