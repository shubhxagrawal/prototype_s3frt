"""
Module A — Data Ingestion
Loads and cleans the S3FRT firm dataset and NGFS carbon price scenarios.
Selects anchor rows (latest year with complete Cat1+Cat4 data per firm).
"""

import pandas as pd
import numpy as np
import os
import streamlit as st

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_FIRM_FILE = os.path.join(_DATA_DIR, "s3frt_dataset_updated.xlsx")
_NGFS_FILE = os.path.join(_DATA_DIR, "ngfs_carbon_prices.csv")

_COL_RENAME = {
    0: "firm",
    1: "year",
    2: "cat1_tco2e",
    3: "cat4_tco2e",
    4: "cat12_tco2e",
    5: "ebitda_usd",
    6: "revenue_usd",
    7: "total_debt_usd",
    8: "tcfd_risk_low_usd",
    9: "tcfd_risk_high_usd",
}

SCENARIO_MULTIPLIERS = {
    "Current Policies": 1.0,
    "Delayed Transition": 1.8,
    "Net Zero 2050": 2.5,
}

SCENARIOS = ["Current Policies", "Delayed Transition", "Net Zero 2050"]
HORIZONS = ["2025", "2030", "2035", "2040"]


@st.cache_data(ttl=3600)
def load_firm_data() -> pd.DataFrame:
    """Load and clean firm dataset. Returns all firm-year rows with derived columns."""
    df = pd.read_excel(_FIRM_FILE, sheet_name="S3FRT_Dataset", header=0)
    df.columns = [_COL_RENAME[i] for i in range(len(df.columns))]

    # Drop sub-header row
    df = df[df["firm"].notna() & df["year"].notna()].copy()

    numeric_cols = ["year", "cat1_tco2e", "cat4_tco2e", "cat12_tco2e",
                    "ebitda_usd", "revenue_usd", "total_debt_usd"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["year"] = df["year"].astype("Int64")

    for col in ["tcfd_risk_low_usd", "tcfd_risk_high_usd"]:
        df.loc[df[col] == "NO_QUANT", col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Cat12 nulls: impute as 0 (conservative)
    df["cat12_imputed"] = df["cat12_tco2e"].isna()
    df["cat12_tco2e"] = df["cat12_tco2e"].fillna(0.0)

    # Flag rows with complete Cat1+Cat4 data (required for anchor selection)
    df["has_cat1_cat4"] = df["cat1_tco2e"].notna() & df["cat4_tco2e"].notna()

    # Total Scope 3
    df["total_scope3_tco2e"] = (
        df["cat1_tco2e"].fillna(0) + df["cat4_tco2e"].fillna(0) + df["cat12_tco2e"].fillna(0)
    )

    # Flag negative EBITDA
    df["negative_ebitda"] = df["ebitda_usd"].notna() & (df["ebitda_usd"] < 0)

    df = df.reset_index(drop=True)
    return df


def get_anchor_rows(df: pd.DataFrame) -> pd.DataFrame:
    """For each firm, select the latest year with complete Cat1+Cat4 data."""
    anchor = (
        df[df["has_cat1_cat4"]]
        .sort_values("year", ascending=False)
        .groupby("firm")
        .first()
        .reset_index()
    )
    return anchor


@st.cache_data(ttl=3600)
def load_carbon_prices() -> pd.DataFrame:
    """Load NGFS carbon price scenarios."""
    df = pd.read_csv(_NGFS_FILE)
    df = df.rename(columns={"Scenario": "scenario"})
    for col in HORIZONS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def get_carbon_price(prices_df: pd.DataFrame, scenario: str, horizon: str) -> float:
    row = prices_df[prices_df["scenario"] == scenario]
    if row.empty:
        return 0.0
    return float(row[horizon].iloc[0])


def get_scenario_multiplier(scenario: str) -> float:
    return SCENARIO_MULTIPLIERS.get(scenario, 1.0)


def get_firm_list(df: pd.DataFrame) -> list:
    return sorted(df["firm"].dropna().unique().tolist())
