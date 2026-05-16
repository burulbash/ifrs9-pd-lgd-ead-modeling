from __future__ import annotations

from pathlib import Path

import pandas as pd


def status_min_good(value: float, green_min: float, amber_min: float) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    if value >= green_min:
        return "GREEN"
    if value >= amber_min:
        return "AMBER"
    return "RED"


def status_max_good(value: float, green_max: float, amber_max: float) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    if value <= green_max:
        return "GREEN"
    if value <= amber_max:
        return "AMBER"
    return "RED"


def status_band_good(
    value: float,
    green_low: float,
    green_high: float,
    amber_low: float,
    amber_high: float,
) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    if green_low <= value <= green_high:
        return "GREEN"
    if amber_low <= value <= amber_high:
        return "AMBER"
    return "RED"


def make_row(
    area: str,
    metric: str,
    value: object,
    green_threshold: str,
    amber_threshold: str,
    red_threshold: str,
    status: str,
    comment: str,
) -> dict[str, object]:
    return {
        "area": area,
        "metric": metric,
        "value": value,
        "green_threshold": green_threshold,
        "amber_threshold": amber_threshold,
        "red_threshold": red_threshold,
        "status": status,
        "comment": comment,
    }


def read_report(reports_dir: Path, filename: str) -> pd.DataFrame:
    path = reports_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Required report not found: {path}")
    return pd.read_csv(path)


def build_validation_traffic_light_summary(reports_dir: str | Path) -> pd.DataFrame:
    reports_dir = Path(reports_dir)
    rows: list[dict[str, object]] = []

    pd_metrics = read_report(reports_dir, "pd_model_metrics.csv")
    pd_oot = pd_metrics[pd_metrics["split"].eq("oot")].copy()
    best_pd = pd_oot.sort_values("roc_auc", ascending=False).iloc[0]

    pd_oot_gini = float(best_pd["gini"])
    rows.append(
        make_row(
            area="PD",
            metric="pd_oot_gini",
            value=round(pd_oot_gini, 6),
            green_threshold=">= 0.30",
            amber_threshold=">= 0.20",
            red_threshold="< 0.20",
            status=status_min_good(pd_oot_gini, green_min=0.30, amber_min=0.20),
            comment="OOT Gini for the best PD model.",
        )
    )

    pd_oot_ks = float(best_pd["ks"])
    rows.append(
        make_row(
            area="PD",
            metric="pd_oot_ks",
            value=round(pd_oot_ks, 6),
            green_threshold=">= 0.20",
            amber_threshold=">= 0.15",
            red_threshold="< 0.15",
            status=status_min_good(pd_oot_ks, green_min=0.20, amber_min=0.15),
            comment="OOT KS statistic for the best PD model.",
        )
    )

    if "brier_score" in best_pd.index:
        pd_brier = float(best_pd["brier_score"])
        rows.append(
            make_row(
                area="PD",
                metric="pd_brier_score",
                value=round(pd_brier, 6),
                green_threshold="<= 0.05",
                amber_threshold="<= 0.08",
                red_threshold="> 0.08",
                status=status_max_good(pd_brier, green_max=0.05, amber_max=0.08),
                comment="Brier score for PD probability calibration. Lower is better.",
            )
        )

    psi = read_report(reports_dir, "validation_psi_summary.csv")
    max_psi = float(psi["psi"].max())

    rows.append(
        make_row(
            area="Monitoring",
            metric="max_feature_psi",
            value=round(max_psi, 6),
            green_threshold="<= 0.10",
            amber_threshold="<= 0.25",
            red_threshold="> 0.25",
            status=status_max_good(max_psi, green_max=0.10, amber_max=0.25),
            comment="Maximum PSI across monitored features.",
        )
    )

    monotonicity = read_report(reports_dir, "validation_rating_monotonicity_summary.csv").iloc[0]
    monotonicity_violations = int(monotonicity["violations_count"])

    rows.append(
        make_row(
            area="Rating",
            metric="rating_monotonicity_violations",
            value=monotonicity_violations,
            green_threshold="= 0",
            amber_threshold="<= 1",
            red_threshold="> 1",
            status=status_max_good(monotonicity_violations, green_max=0, amber_max=1),
            comment="Number of rating monotonicity violations.",
        )
    )

    binomial_path = reports_dir / "validation_rating_binomial_backtesting.csv"
    if binomial_path.exists():
        binomial = pd.read_csv(binomial_path)
        red_count = int((binomial["traffic_light"] == "RED").sum())

        rows.append(
            make_row(
                area="Rating",
                metric="rating_binomial_red_count",
                value=red_count,
                green_threshold="= 0",
                amber_threshold="<= 2",
                red_threshold="> 2",
                status=status_max_good(red_count, green_max=0, amber_max=2),
                comment="Number of rating grades with RED binomial backtesting status.",
            )
        )

    ecl = read_report(reports_dir, "ifrs9_ecl_portfolio_summary.csv").iloc[0]

    stage_2_share = float(ecl["stage_2_share"])
    rows.append(
        make_row(
            area="IFRS9_Staging",
            metric="stage_2_share",
            value=round(stage_2_share, 6),
            green_threshold="0.05 - 0.35",
            amber_threshold="0.01 - 0.50",
            red_threshold="outside amber band",
            status=status_band_good(
                stage_2_share,
                green_low=0.05,
                green_high=0.35,
                amber_low=0.01,
                amber_high=0.50,
            ),
            comment="Stage 2 facility share. This is a portfolio sanity check, not a model performance metric.",
        )
    )

    stage_3_share = float(ecl["stage_3_share"])
    rows.append(
        make_row(
            area="IFRS9_Staging",
            metric="stage_3_share",
            value=round(stage_3_share, 6),
            green_threshold="0.01 - 0.15",
            amber_threshold="0.00 - 0.25",
            red_threshold="> 0.25",
            status=status_band_good(
                stage_3_share,
                green_low=0.01,
                green_high=0.15,
                amber_low=0.00,
                amber_high=0.25,
            ),
            comment="Stage 3 facility share. This is a portfolio sanity check.",
        )
    )

    stress = read_report(reports_dir, "stress_scenario_summary.csv")
    severe = stress[stress["scenario"].eq("severe_downturn")].iloc[0]
    severe_uplift = float(severe["ecl_change_pct_vs_base"])

    rows.append(
        make_row(
            area="Stress",
            metric="severe_downturn_ecl_change_pct",
            value=round(severe_uplift, 6),
            green_threshold="0.10 - 0.70",
            amber_threshold="0.00 - 1.00",
            red_threshold="outside amber band",
            status=status_band_good(
                severe_uplift,
                green_low=0.10,
                green_high=0.70,
                amber_low=0.00,
                amber_high=1.00,
            ),
            comment="ECL increase under severe downturn versus base scenario.",
        )
    )

    data_quality_path = reports_dir / "data_quality_summary.csv"
    if data_quality_path.exists():
        dq = pd.read_csv(data_quality_path)
        status_counts = dq["status"].value_counts().to_dict()

        fail_count = int(status_counts.get("FAIL", 0))
        warn_count = int(status_counts.get("WARN", 0))

        rows.append(
            make_row(
                area="Data Quality",
                metric="data_quality_fail_count",
                value=fail_count,
                green_threshold="= 0",
                amber_threshold="<= 1",
                red_threshold="> 1",
                status=status_max_good(fail_count, green_max=0, amber_max=1),
                comment="Number of failed SQL data quality checks.",
            )
        )

        rows.append(
            make_row(
                area="Data Quality",
                metric="data_quality_warn_count",
                value=warn_count,
                green_threshold="= 0",
                amber_threshold="<= 3",
                red_threshold="> 3",
                status=status_max_good(warn_count, green_max=0, amber_max=3),
                comment="Number of warning SQL data quality checks.",
            )
        )

    return pd.DataFrame(
        rows,
        columns=[
            "area",
            "metric",
            "value",
            "green_threshold",
            "amber_threshold",
            "red_threshold",
            "status",
            "comment",
        ],
    )
