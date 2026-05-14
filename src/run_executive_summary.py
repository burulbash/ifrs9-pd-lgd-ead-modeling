from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"


def read_report(filename: str) -> pd.DataFrame:
    path = REPORTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Required report not found: {path}")
    return pd.read_csv(path)


def add_row(rows: list[dict[str, object]], area: str, metric: str, value: object, comment: str) -> None:
    rows.append(
        {
            "area": area,
            "metric": metric,
            "value": value,
            "comment": comment,
        }
    )


def build_executive_summary() -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    pd_metrics = read_report("pd_model_metrics.csv")
    pd_oot = pd_metrics[pd_metrics["split"].eq("oot")].copy()
    best_pd = pd_oot.sort_values("roc_auc", ascending=False).iloc[0]

    add_row(rows, "PD", "best_oot_model", best_pd["model"], "Best PD model selected by OOT ROC-AUC.")
    add_row(rows, "PD", "pd_oot_roc_auc", round(float(best_pd["roc_auc"]), 6), "PD model OOT ROC-AUC.")
    add_row(rows, "PD", "pd_oot_gini", round(float(best_pd["gini"]), 6), "PD model OOT Gini.")
    add_row(rows, "PD", "pd_oot_ks", round(float(best_pd["ks"]), 6), "PD model OOT KS.")
    if "brier_score" in best_pd.index:
        add_row(rows, "PD", "pd_oot_brier_score", round(float(best_pd["brier_score"]), 6), "PD probability calibration loss.")

    lgd_metrics = read_report("lgd_model_metrics.csv")
    lgd_oot = lgd_metrics[lgd_metrics["split"].eq("oot")].copy()
    best_lgd = lgd_oot.sort_values("weighted_mae", ascending=True).iloc[0]

    add_row(rows, "LGD", "best_oot_model", best_lgd["model"], "Best LGD model selected by OOT weighted MAE.")
    add_row(rows, "LGD", "lgd_oot_mae", round(float(best_lgd["mae"]), 6), "LGD OOT MAE.")
    add_row(rows, "LGD", "lgd_oot_rmse", round(float(best_lgd["rmse"]), 6), "LGD OOT RMSE.")
    add_row(rows, "LGD", "lgd_oot_weighted_mae", round(float(best_lgd["weighted_mae"]), 6), "LGD OOT weighted MAE.")

    ead_metrics = read_report("ead_ccf_model_metrics.csv")
    ead_oot = ead_metrics[ead_metrics["split"].eq("oot")].copy()
    best_ead = ead_oot.sort_values("weighted_mae", ascending=True).iloc[0]

    add_row(rows, "EAD_CCF", "best_oot_model", best_ead["model"], "Best EAD/CCF model selected by OOT weighted MAE.")
    add_row(rows, "EAD_CCF", "ead_ccf_oot_mae", round(float(best_ead["mae"]), 6), "EAD/CCF OOT MAE.")
    add_row(rows, "EAD_CCF", "ead_ccf_oot_rmse", round(float(best_ead["rmse"]), 6), "EAD/CCF OOT RMSE.")
    add_row(rows, "EAD_CCF", "ead_ccf_oot_weighted_mae", round(float(best_ead["weighted_mae"]), 6), "EAD/CCF OOT weighted MAE.")

    ecl = read_report("ifrs9_ecl_portfolio_summary.csv").iloc[0]

    add_row(rows, "IFRS9_ECL", "portfolio_facilities", int(ecl["facilities"]), "Number of facilities in the ECL portfolio.")
    add_row(rows, "IFRS9_ECL", "portfolio_total_ead", round(float(ecl["total_ead"]), 2), "Total EAD.")
    add_row(rows, "IFRS9_ECL", "portfolio_total_ecl", round(float(ecl["total_ecl"]), 2), "Scenario-weighted total ECL.")
    add_row(rows, "IFRS9_ECL", "portfolio_ecl_rate", round(float(ecl["ecl_rate"]), 6), "Total ECL divided by total EAD.")
    add_row(rows, "IFRS9_ECL", "stage_1_share", round(float(ecl["stage_1_share"]), 6), "Facility share in Stage 1.")
    add_row(rows, "IFRS9_ECL", "stage_2_share", round(float(ecl["stage_2_share"]), 6), "Facility share in Stage 2.")
    add_row(rows, "IFRS9_ECL", "stage_3_share", round(float(ecl["stage_3_share"]), 6), "Facility share in Stage 3.")

    stress = read_report("stress_scenario_summary.csv")
    severe = stress[stress["scenario"].eq("severe_downturn")].iloc[0]

    add_row(rows, "Stress", "severe_downturn_total_ecl", round(float(severe["total_ecl"]), 2), "Total ECL under severe downturn.")
    add_row(rows, "Stress", "severe_downturn_ecl_change_pct_vs_base", round(float(severe["ecl_change_pct_vs_base"]), 6), "ECL increase versus base.")

    psi = read_report("validation_psi_summary.csv")
    top_psi = psi.sort_values("psi", ascending=False).iloc[0]

    add_row(rows, "Monitoring", "max_psi_feature", top_psi["feature"], "Feature with the highest PSI.")
    add_row(rows, "Monitoring", "max_psi_value", round(float(top_psi["psi"]), 6), "Highest PSI value.")

    monotonicity = read_report("validation_rating_monotonicity_summary.csv").iloc[0]
    add_row(
        rows,
        "Validation",
        "rating_monotonicity_violations",
        int(monotonicity["violations_count"]),
        "Number of rating monotonicity violations.",
    )

    dq_path = REPORTS_DIR / "data_quality_summary.csv"
    if dq_path.exists():
        dq = pd.read_csv(dq_path)
        status_counts = dq["status"].value_counts().to_dict()

        add_row(rows, "Data Quality", "data_quality_fail_count", int(status_counts.get("FAIL", 0)), "Number of failed data quality checks.")
        add_row(rows, "Data Quality", "data_quality_warn_count", int(status_counts.get("WARN", 0)), "Number of warning data quality checks.")
        add_row(rows, "Data Quality", "data_quality_pass_count", int(status_counts.get("PASS", 0)), "Number of passed data quality checks.")

    return pd.DataFrame(rows, columns=["area", "metric", "value", "comment"])


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    summary = build_executive_summary()
    output_path = REPORTS_DIR / "executive_model_summary.csv"
    summary.to_csv(output_path, index=False)

    print("Executive model summary")
    print(summary)
    print()
    print("Saved to:", output_path)


if __name__ == "__main__":
    main()
