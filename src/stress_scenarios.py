from __future__ import annotations

import numpy as np
import pandas as pd

from src.ecl import (
    calculate_lifetime_pd,
    calculate_stage_ecl,
    clip_probability,
    prepare_ecl_base_columns,
)


STRESS_SCENARIOS = {
    "base": {
        "pd_multiplier": 1.00,
        "lgd_multiplier": 1.00,
        "ccf_multiplier": 1.00,
        "industry_stress_multiplier": 1.00,
    },
    "downside": {
        "pd_multiplier": 1.35,
        "lgd_multiplier": 1.10,
        "ccf_multiplier": 1.15,
        "industry_stress_multiplier": 1.15,
    },
    "severe_downturn": {
        "pd_multiplier": 1.90,
        "lgd_multiplier": 1.25,
        "ccf_multiplier": 1.30,
        "industry_stress_multiplier": 1.35,
    },
    "rate_shock": {
        "pd_multiplier": 1.45,
        "lgd_multiplier": 1.08,
        "ccf_multiplier": 1.10,
        "industry_stress_multiplier": 1.10,
    },
    "fx_shock": {
        "pd_multiplier": 1.30,
        "lgd_multiplier": 1.12,
        "ccf_multiplier": 1.12,
        "industry_stress_multiplier": 1.15,
    },
}


INDUSTRY_STRESS_SENSITIVITY = {
    "construction": 1.35,
    "real_estate": 1.30,
    "trade": 1.15,
    "transport": 1.12,
    "agriculture": 1.10,
    "manufacturing": 1.08,
    "services": 1.00,
    "energy": 0.95,
}


FX_SENSITIVE_INDUSTRIES = {
    "trade",
    "manufacturing",
    "transport",
    "agriculture",
}


def get_industry_stress_multiplier(
    industry: pd.Series,
    scenario_name: str,
    scenario_industry_multiplier: float,
) -> pd.Series:
    industry_clean = industry.fillna("unknown").astype(str)

    base_sensitivity = industry_clean.map(INDUSTRY_STRESS_SENSITIVITY).fillna(1.0)

    multiplier = 1 + (base_sensitivity - 1) * scenario_industry_multiplier

    if scenario_name == "fx_shock":
        fx_extra = industry_clean.isin(FX_SENSITIVE_INDUSTRIES).astype(float) * 0.20
        multiplier = multiplier + fx_extra

    return multiplier.clip(lower=0.75, upper=2.50)


def calculate_stress_scenario_ecl(
    df: pd.DataFrame,
    scenarios: dict[str, dict[str, float]] = STRESS_SCENARIOS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = prepare_ecl_base_columns(df)

    current_outstanding = pd.to_numeric(
        data.get("current_outstanding_balance", data.get("outstanding_amount", 0)),
        errors="coerce",
    ).fillna(0).clip(lower=0)

    undrawn_amount = pd.to_numeric(data.get("undrawn_amount", 0), errors="coerce").fillna(0).clip(lower=0)

    scenario_summary_rows = []
    by_stage_rows = []
    by_industry_rows = []

    for scenario_name, params in scenarios.items():
        industry_multiplier = get_industry_stress_multiplier(
            data["industry"],
            scenario_name=scenario_name,
            scenario_industry_multiplier=params["industry_stress_multiplier"],
        )

        pd_col = f"stress_pd_12m_{scenario_name}"
        lifetime_pd_col = f"stress_lifetime_pd_{scenario_name}"
        lgd_col = f"stress_lgd_{scenario_name}"
        ccf_col = f"stress_ccf_{scenario_name}"
        ead_col = f"stress_ead_{scenario_name}"
        ecl_col = f"stress_ecl_{scenario_name}"

        data[pd_col] = clip_probability(
            data["pd_12m_base"] * params["pd_multiplier"] * industry_multiplier
        )

        data[lifetime_pd_col] = calculate_lifetime_pd(
            data[pd_col],
            data["remaining_life_years"],
        )

        data[lgd_col] = clip_probability(data["lgd_base"] * params["lgd_multiplier"])

        data[ccf_col] = pd.to_numeric(
            data["ccf_base"] * params["ccf_multiplier"],
            errors="coerce",
        ).clip(lower=0, upper=1.5)

        data[ead_col] = current_outstanding + data[ccf_col] * undrawn_amount

        data[ecl_col] = calculate_stage_ecl(
            stage=data["ifrs9_stage"],
            pd_12m=data[pd_col],
            lifetime_pd=data[lifetime_pd_col],
            lgd=data[lgd_col],
            ead=data[ead_col],
        )

        scenario_summary_rows.append(
            {
                "scenario": scenario_name,
                "facilities": len(data),
                "total_ead": data[ead_col].sum(),
                "total_ecl": data[ecl_col].sum(),
                "ecl_rate": data[ecl_col].sum() / data[ead_col].sum() if data[ead_col].sum() else 0,
                "avg_pd_12m": data[pd_col].mean(),
                "avg_lgd": data[lgd_col].mean(),
                "avg_ccf": data[ccf_col].mean(),
            }
        )

        stage_report = (
            data.groupby("ifrs9_stage", as_index=False)
            .agg(
                facilities=("facility_id", "size"),
                total_ead=(ead_col, "sum"),
                total_ecl=(ecl_col, "sum"),
                avg_pd_12m=(pd_col, "mean"),
                avg_lgd=(lgd_col, "mean"),
            )
        )
        stage_report.insert(0, "scenario", scenario_name)
        by_stage_rows.append(stage_report)

        industry_report = (
            data.groupby("industry", dropna=False, as_index=False)
            .agg(
                facilities=("facility_id", "size"),
                total_ead=(ead_col, "sum"),
                total_ecl=(ecl_col, "sum"),
                avg_pd_12m=(pd_col, "mean"),
                avg_lgd=(lgd_col, "mean"),
            )
        )
        industry_report.insert(0, "scenario", scenario_name)
        by_industry_rows.append(industry_report)

    scenario_summary = pd.DataFrame(scenario_summary_rows).sort_values("total_ecl", ascending=False)
    by_stage = pd.concat(by_stage_rows, ignore_index=True)
    by_industry = pd.concat(by_industry_rows, ignore_index=True)

    base_total_ecl = scenario_summary.loc[
        scenario_summary["scenario"].eq("base"),
        "total_ecl",
    ].iloc[0]

    scenario_summary["ecl_change_vs_base"] = scenario_summary["total_ecl"] - base_total_ecl
    scenario_summary["ecl_change_pct_vs_base"] = np.where(
        base_total_ecl != 0,
        scenario_summary["ecl_change_vs_base"] / base_total_ecl,
        0,
    )

    return data, scenario_summary, by_stage, by_industry
