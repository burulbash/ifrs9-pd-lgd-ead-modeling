from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
PLOTS_DIR = PROJECT_ROOT / "outputs" / "plots"


REQUIRED_REPORTS = {
    "pd_model_metrics.csv": {"model", "split", "roc_auc", "gini", "ks"},
    "lgd_model_metrics.csv": {"model", "split", "mae", "rmse", "weighted_mae"},
    "ead_ccf_model_metrics.csv": {"model", "split", "mae", "rmse", "weighted_mae"},
    "ifrs9_ecl_portfolio_summary.csv": {"facilities", "total_ead", "total_ecl", "ecl_rate"},
    "ifrs9_ecl_by_stage.csv": {"ifrs9_stage", "facilities", "total_ead", "total_ecl"},
    "stress_scenario_summary.csv": {"scenario", "total_ecl", "ecl_change_pct_vs_base"},
    "validation_summary.csv": {"area", "metric", "value"},
    "validation_psi_summary.csv": {"feature", "psi"},
    "validation_pd_backtesting_by_rating.csv": {
        "rating_grade",
        "facilities",
        "observed_default_rate",
        "avg_predicted_pd",
        "observed_default_rate_lower_ci",
        "observed_default_rate_upper_ci",
    },
    "validation_rating_binomial_backtesting.csv": {
        "rating_grade",
        "observed_defaults",
        "expected_defaults",
        "binomial_p_value",
        "traffic_light",
    },
    "validation_traffic_light_summary.csv": {
        "area",
        "metric",
        "value",
        "green_threshold",
        "amber_threshold",
        "red_threshold",
        "status",
        "comment",
    },
    "data_quality_summary.csv": {"check_group", "check_name", "metric_value", "status"},
    "executive_model_summary.csv": {"area", "metric", "value", "comment"},
    "leakage_exclusion_report.csv": {"column", "reason", "category"},
    "lgd_outlier_report.csv": {"area", "check_name", "metric_name", "metric_value", "status", "details"},
    "ead_ccf_outlier_report.csv": {"area", "check_name", "metric_name", "metric_value", "status", "details"},
}


REQUIRED_PLOTS = [
    "pd_model_oot_roc_auc.png",
    "pd_calibration_by_rating_grade.png",
    "rating_calibration_with_confidence_bands.png",
    "ifrs9_stage_distribution.png",
    "ifrs9_ecl_by_stage.png",
    "stress_scenario_ecl_comparison.png",
    "validation_top_psi_features.png",
]


def test_required_reports_exist_and_have_expected_columns() -> None:
    missing_files = []
    missing_columns = {}

    for filename, required_columns in REQUIRED_REPORTS.items():
        path = REPORTS_DIR / filename

        if not path.exists():
            missing_files.append(filename)
            continue

        columns = set(pd.read_csv(path, nrows=5).columns)
        missing = required_columns - columns

        if missing:
            missing_columns[filename] = sorted(missing)

    assert not missing_files, f"Missing report files: {missing_files}"
    assert not missing_columns, f"Missing report columns: {missing_columns}"


def test_required_plots_exist_and_are_not_empty() -> None:
    missing_or_empty = []

    for filename in REQUIRED_PLOTS:
        path = PLOTS_DIR / filename

        if not path.exists() or path.stat().st_size == 0:
            missing_or_empty.append(filename)

    assert not missing_or_empty, f"Missing or empty plot files: {missing_or_empty}"
