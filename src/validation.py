from __future__ import annotations

import numpy as np
import pandas as pd


RATING_ORDER = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
    "F": 6,
    "Default": 7,
}


def assign_pd_rating_grade(pd_value: float) -> str:
    if pd_value < 0.005:
        return "A"
    if pd_value < 0.015:
        return "B"
    if pd_value < 0.035:
        return "C"
    if pd_value < 0.075:
        return "D"
    if pd_value < 0.150:
        return "E"
    return "F"


def build_pd_backtesting_by_rating(
    predictions: pd.DataFrame,
    pd_column: str,
    target_column: str = "target_default_12m",
) -> pd.DataFrame:
    data = predictions.copy()
    data[pd_column] = pd.to_numeric(data[pd_column], errors="coerce")
    data[target_column] = pd.to_numeric(data[target_column], errors="coerce")
    data = data.dropna(subset=[pd_column, target_column]).copy()

    data["rating_grade"] = data[pd_column].apply(assign_pd_rating_grade)
    data["rating_order"] = data["rating_grade"].map(RATING_ORDER)

    report = (
        data.groupby(["rating_grade", "rating_order"], as_index=False)
        .agg(
            facilities=("facility_id", "size"),
            defaults=(target_column, "sum"),
            observed_default_rate=(target_column, "mean"),
            avg_predicted_pd=(pd_column, "mean"),
            min_predicted_pd=(pd_column, "min"),
            max_predicted_pd=(pd_column, "max"),
        )
        .sort_values("rating_order")
    )

    report["calibration_error"] = report["avg_predicted_pd"] - report["observed_default_rate"]

    ci_values = report.apply(
        lambda row: wilson_confidence_interval(
            observed_defaults=row["defaults"],
            facilities=row["facilities"],
        ),
        axis=1,
    )

    report["observed_default_rate_lower_ci"] = [value[0] for value in ci_values]
    report["observed_default_rate_upper_ci"] = [value[1] for value in ci_values]

    return report.drop(columns=["rating_order"])


def check_rating_monotonicity(
    rating_report: pd.DataFrame,
    rating_column: str = "rating_grade",
    rate_column: str = "observed_default_rate",
    min_facilities: int = 1,
) -> pd.DataFrame:
    data = rating_report.copy()
    data["rating_order"] = data[rating_column].map(RATING_ORDER)
    data = data[data["facilities"] >= min_facilities].copy()
    data = data.sort_values("rating_order")

    rates = data[rate_column].to_numpy(dtype=float)

    is_monotonic = bool(np.all(np.diff(rates) >= -1e-12)) if len(rates) > 1 else True

    violations = []
    previous_grade = None
    previous_rate = None

    for _, row in data.iterrows():
        current_grade = row[rating_column]
        current_rate = float(row[rate_column])

        if previous_rate is not None and current_rate < previous_rate:
            violations.append(
                {
                    "previous_grade": previous_grade,
                    "current_grade": current_grade,
                    "previous_default_rate": previous_rate,
                    "current_default_rate": current_rate,
                    "violation": 1,
                }
            )

        previous_grade = current_grade
        previous_rate = current_rate

    summary = pd.DataFrame(
        [
            {
                "check_name": "rating_monotonicity",
                "ratings_checked": len(data),
                "is_monotonic": is_monotonic,
                "violations_count": len(violations),
            }
        ]
    )

    violations_df = pd.DataFrame(violations)

    if violations_df.empty:
        violations_df = pd.DataFrame(
            columns=[
                "previous_grade",
                "current_grade",
                "previous_default_rate",
                "current_default_rate",
                "violation",
            ]
        )

    return summary, violations_df


def build_pd_calibration_by_decile(
    predictions: pd.DataFrame,
    pd_column: str,
    target_column: str = "target_default_12m",
    n_bins: int = 10,
) -> pd.DataFrame:
    data = predictions.copy()
    data[pd_column] = pd.to_numeric(data[pd_column], errors="coerce")
    data[target_column] = pd.to_numeric(data[target_column], errors="coerce")
    data = data.dropna(subset=[pd_column, target_column]).copy()

    if data[pd_column].nunique(dropna=True) < 2:
        data["pd_decile"] = 1
    else:
        data["pd_decile"] = pd.qcut(
            data[pd_column].rank(method="first"),
            q=min(n_bins, len(data)),
            labels=False,
            duplicates="drop",
        ) + 1

    report = (
        data.groupby("pd_decile", as_index=False)
        .agg(
            facilities=("facility_id", "size"),
            defaults=(target_column, "sum"),
            observed_default_rate=(target_column, "mean"),
            avg_predicted_pd=(pd_column, "mean"),
            min_predicted_pd=(pd_column, "min"),
            max_predicted_pd=(pd_column, "max"),
        )
        .sort_values("pd_decile")
    )

    report["calibration_error"] = report["avg_predicted_pd"] - report["observed_default_rate"]

    return report


def calculate_psi(
    expected: pd.Series,
    actual: pd.Series,
    bins: int = 10,
    epsilon: float = 1e-6,
) -> tuple[float, pd.DataFrame]:
    expected_clean = pd.to_numeric(expected, errors="coerce").dropna()
    actual_clean = pd.to_numeric(actual, errors="coerce").dropna()

    if expected_clean.empty or actual_clean.empty:
        empty_details = pd.DataFrame(
            columns=[
                "bin",
                "lower_bound",
                "upper_bound",
                "expected_count",
                "actual_count",
                "expected_share",
                "actual_share",
                "psi_component",
            ]
        )
        return float("nan"), empty_details

    if expected_clean.nunique() < 2:
        lower_bound = min(expected_clean.min(), actual_clean.min())
        upper_bound = max(expected_clean.max(), actual_clean.max())
        breakpoints = np.array([lower_bound, upper_bound])
    else:
        quantiles = np.linspace(0, 1, bins + 1)
        breakpoints = np.unique(expected_clean.quantile(quantiles).to_numpy())

    if len(breakpoints) < 2:
        breakpoints = np.array([expected_clean.min() - 1e-9, expected_clean.max() + 1e-9])

    breakpoints[0] = -np.inf
    breakpoints[-1] = np.inf

    expected_bins = pd.cut(expected_clean, bins=breakpoints, include_lowest=True)
    actual_bins = pd.cut(actual_clean, bins=breakpoints, include_lowest=True)

    expected_counts = expected_bins.value_counts(sort=False)
    actual_counts = actual_bins.value_counts(sort=False)

    details = pd.DataFrame(
        {
            "bin": range(1, len(expected_counts) + 1),
            "lower_bound": [interval.left for interval in expected_counts.index],
            "upper_bound": [interval.right for interval in expected_counts.index],
            "expected_count": expected_counts.to_numpy(),
            "actual_count": actual_counts.reindex(expected_counts.index, fill_value=0).to_numpy(),
        }
    )

    details["expected_share"] = details["expected_count"] / max(details["expected_count"].sum(), 1)
    details["actual_share"] = details["actual_count"] / max(details["actual_count"].sum(), 1)

    expected_share = details["expected_share"].clip(lower=epsilon)
    actual_share = details["actual_share"].clip(lower=epsilon)

    details["psi_component"] = (actual_share - expected_share) * np.log(actual_share / expected_share)

    total_psi = float(details["psi_component"].sum())

    return total_psi, details


def build_psi_report(
    expected_df: pd.DataFrame,
    actual_df: pd.DataFrame,
    features: list[str],
    bins: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    detail_frames = []

    for feature in features:
        if feature not in expected_df.columns or feature not in actual_df.columns:
            continue

        psi_value, details = calculate_psi(
            expected=expected_df[feature],
            actual=actual_df[feature],
            bins=bins,
        )

        summary_rows.append(
            {
                "feature": feature,
                "psi": psi_value,
                "expected_missing_rate": expected_df[feature].isna().mean(),
                "actual_missing_rate": actual_df[feature].isna().mean(),
            }
        )

        details.insert(0, "feature", feature)
        detail_frames.append(details)

    summary = pd.DataFrame(summary_rows).sort_values("psi", ascending=False)
    details = pd.concat(detail_frames, ignore_index=True) if detail_frames else pd.DataFrame()

    return summary, details


def build_stage_validation_summary(staged_portfolio: pd.DataFrame) -> pd.DataFrame:
    data = staged_portfolio.copy()

    return (
        data.groupby("ifrs9_stage", as_index=False)
        .agg(
            facilities=("facility_id", "size"),
            total_outstanding=("outstanding_amount", "sum"),
            avg_current_pd=("current_pd_estimate", "mean"),
            avg_origination_pd=("origination_pd_estimate", "mean"),
            default_rate=("default_flag", "mean"),
        )
        .sort_values("ifrs9_stage")
    )


def build_ecl_validation_summary(ecl_portfolio: pd.DataFrame) -> pd.DataFrame:
    data = ecl_portfolio.copy()

    return pd.DataFrame(
        [
            {
                "facilities": len(data),
                "total_ead": pd.to_numeric(data["ead_base"], errors="coerce").sum(),
                "total_ecl": pd.to_numeric(data["scenario_weighted_ecl"], errors="coerce").sum(),
                "avg_pd_12m": pd.to_numeric(data["pd_12m_base"], errors="coerce").mean(),
                "avg_lgd": pd.to_numeric(data["lgd_base"], errors="coerce").mean(),
                "stage_1_share": (data["ifrs9_stage"] == 1).mean(),
                "stage_2_share": (data["ifrs9_stage"] == 2).mean(),
                "stage_3_share": (data["ifrs9_stage"] == 3).mean(),
            }
        ]
    )


def build_validation_summary(
    pd_backtesting: pd.DataFrame,
    monotonicity_summary: pd.DataFrame,
    psi_summary: pd.DataFrame,
    stage_summary: pd.DataFrame,
    ecl_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    rows.append(
        {
            "area": "pd_backtesting",
            "metric": "ratings_count",
            "value": len(pd_backtesting),
        }
    )

    rows.append(
        {
            "area": "pd_backtesting",
            "metric": "total_defaults",
            "value": pd_backtesting["defaults"].sum() if "defaults" in pd_backtesting.columns else np.nan,
        }
    )

    rows.append(
        {
            "area": "rating_monotonicity",
            "metric": "violations_count",
            "value": monotonicity_summary["violations_count"].iloc[0],
        }
    )

    rows.append(
        {
            "area": "psi",
            "metric": "max_feature_psi",
            "value": psi_summary["psi"].max() if not psi_summary.empty else np.nan,
        }
    )

    rows.append(
        {
            "area": "ifrs9_staging",
            "metric": "stage_2_share",
            "value": (
                stage_summary.loc[stage_summary["ifrs9_stage"].eq(2), "facilities"].sum()
                / max(stage_summary["facilities"].sum(), 1)
            ),
        }
    )

    rows.append(
        {
            "area": "ifrs9_ecl",
            "metric": "total_ecl",
            "value": ecl_summary["total_ecl"].iloc[0] if not ecl_summary.empty else np.nan,
        }
    )

    return pd.DataFrame(rows)


def approximate_binomial_two_sided_p_value(
    observed_defaults: float,
    facilities: float,
    expected_pd: float,
) -> float:
    """Normal approximation for a two-sided binomial backtesting p-value."""

    import math

    n = float(facilities)
    k = float(observed_defaults)
    p = float(expected_pd)

    if n <= 0:
        return float("nan")

    p = min(max(p, 1e-9), 1 - 1e-9)

    expected = n * p
    variance = n * p * (1 - p)

    if variance <= 0:
        return float("nan")

    z_score = (k - expected) / math.sqrt(variance)
    p_value = math.erfc(abs(z_score) / math.sqrt(2))

    return float(min(max(p_value, 0), 1))


def assign_backtesting_traffic_light(p_value: float) -> str:
    if pd.isna(p_value):
        return "UNKNOWN"
    if p_value >= 0.05:
        return "GREEN"
    if p_value >= 0.01:
        return "AMBER"
    return "RED"


def wilson_confidence_interval(
    observed_defaults: float,
    facilities: float,
    confidence_z: float = 1.96,
) -> tuple[float, float]:
    """Wilson confidence interval for observed default rate."""

    import math

    n = float(facilities)
    k = float(observed_defaults)

    if n <= 0:
        return float("nan"), float("nan")

    p_hat = k / n
    z = float(confidence_z)

    denominator = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denominator
    half_width = (
        z
        * math.sqrt((p_hat * (1 - p_hat) / n) + (z**2 / (4 * n**2)))
        / denominator
    )

    lower = max(0.0, center - half_width)
    upper = min(1.0, center + half_width)

    return float(lower), float(upper)


def build_rating_binomial_backtesting(
    rating_report: pd.DataFrame,
) -> pd.DataFrame:
    """Build rating-level observed defaults vs expected defaults backtesting report."""

    data = rating_report.copy()

    data["expected_defaults"] = (
        pd.to_numeric(data["facilities"], errors="coerce")
        * pd.to_numeric(data["avg_predicted_pd"], errors="coerce")
    )

    data["binomial_p_value"] = data.apply(
        lambda row: approximate_binomial_two_sided_p_value(
            observed_defaults=row["defaults"],
            facilities=row["facilities"],
            expected_pd=row["avg_predicted_pd"],
        ),
        axis=1,
    )

    data["traffic_light"] = data["binomial_p_value"].apply(assign_backtesting_traffic_light)

    columns = [
        "rating_grade",
        "facilities",
        "defaults",
        "expected_defaults",
        "avg_predicted_pd",
        "observed_default_rate",
        "binomial_p_value",
        "traffic_light",
    ]

    return data[columns].rename(columns={"defaults": "observed_defaults"})
