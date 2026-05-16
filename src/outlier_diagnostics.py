from __future__ import annotations

import numpy as np
import pandas as pd


def find_first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def add_check(
    rows: list[dict[str, object]],
    area: str,
    check_name: str,
    metric_name: str,
    metric_value: float,
    status: str,
    details: str,
) -> None:
    rows.append(
        {
            "area": area,
            "check_name": check_name,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "status": status,
            "details": details,
        }
    )


def status_from_count(count: int, positive_status: str = "FAIL") -> str:
    return "PASS" if count == 0 else positive_status


def build_lgd_outlier_report(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    rows: list[dict[str, object]] = []
    total_rows = len(data)

    lgd_col = find_first_existing_column(data, ["realized_lgd", "lgd", "actual_lgd"])
    ead_col = find_first_existing_column(data, ["ead_at_default", "ead", "total_ead"])
    recovery_col = find_first_existing_column(data, ["total_recovery_amount", "recovery_amount", "recoveries_amount"])
    cost_col = find_first_existing_column(data, ["total_collection_cost", "collection_cost", "collection_costs"])

    add_check(rows, "LGD", "rows", "rows", total_rows, "INFO", "Rows in LGD diagnostics input.")

    if lgd_col is not None:
        lgd = pd.to_numeric(data[lgd_col], errors="coerce")
        invalid_lgd_count = int(((lgd < 0) | (lgd > 1)).sum())
        add_check(
            rows,
            "LGD",
            "lgd outside 0 1 bounds",
            "invalid_count",
            invalid_lgd_count,
            status_from_count(invalid_lgd_count, "FAIL"),
            f"{lgd_col} should be between 0 and 1.",
        )

    if ead_col is not None:
        ead = pd.to_numeric(data[ead_col], errors="coerce")
        non_positive_ead_count = int((ead <= 0).sum())
        add_check(
            rows,
            "LGD",
            "non positive ead",
            "invalid_count",
            non_positive_ead_count,
            status_from_count(non_positive_ead_count, "FAIL"),
            f"{ead_col} should be positive.",
        )

        q99 = float(ead.quantile(0.99)) if ead.notna().any() else np.nan
        if pd.notna(q99) and q99 > 0:
            high_ead_count = int((ead > q99 * 3).sum())
            add_check(
                rows,
                "LGD",
                "very high ead",
                "outlier_count",
                high_ead_count,
                status_from_count(high_ead_count, "WARN"),
                f"{ead_col} greater than 3x p99 is treated as an exposure outlier.",
            )

    if recovery_col is not None:
        recovery = pd.to_numeric(data[recovery_col], errors="coerce")
        negative_recovery_count = int((recovery < 0).sum())
        add_check(
            rows,
            "LGD",
            "negative recoveries",
            "invalid_count",
            negative_recovery_count,
            status_from_count(negative_recovery_count, "FAIL"),
            f"{recovery_col} should not be negative.",
        )

        if ead_col is not None:
            ead = pd.to_numeric(data[ead_col], errors="coerce")
            recovery_gt_ead_count = int((recovery > ead).sum())
            add_check(
                rows,
                "LGD",
                "recovery greater than ead",
                "warning_count",
                recovery_gt_ead_count,
                status_from_count(recovery_gt_ead_count, "WARN"),
                "Total recovery greater than EAD is possible in synthetic data but should be reviewed.",
            )

    if cost_col is not None:
        cost = pd.to_numeric(data[cost_col], errors="coerce")
        negative_cost_count = int((cost < 0).sum())
        add_check(
            rows,
            "LGD",
            "negative collection cost",
            "invalid_count",
            negative_cost_count,
            status_from_count(negative_cost_count, "FAIL"),
            f"{cost_col} should not be negative.",
        )

        if ead_col is not None:
            ead = pd.to_numeric(data[ead_col], errors="coerce")
            extreme_cost_count = int((cost > ead * 0.5).sum())
            add_check(
                rows,
                "LGD",
                "extreme collection cost",
                "warning_count",
                extreme_cost_count,
                status_from_count(extreme_cost_count, "WARN"),
                "Collection cost greater than 50% of EAD is treated as an outlier.",
            )

    return pd.DataFrame(rows, columns=["area", "check_name", "metric_name", "metric_value", "status", "details"])


def build_ead_ccf_outlier_report(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    rows: list[dict[str, object]] = []
    total_rows = len(data)

    ccf_col = find_first_existing_column(data, ["realized_ccf", "ccf", "actual_ccf"])
    ead_col = find_first_existing_column(data, ["ead_at_default", "ead", "total_ead"])
    undrawn_col = find_first_existing_column(data, ["undrawn_amount", "undrawn_balance"])
    outstanding_col = find_first_existing_column(data, ["outstanding_amount", "drawn_amount", "outstanding_balance"])
    limit_col = find_first_existing_column(data, ["limit_amount", "credit_limit"])

    add_check(rows, "EAD_CCF", "rows", "rows", total_rows, "INFO", "Rows in EAD/CCF diagnostics input.")

    if ccf_col is not None:
        ccf = pd.to_numeric(data[ccf_col], errors="coerce")
        invalid_ccf_count = int(((ccf < 0) | (ccf > 1.5)).sum())
        add_check(
            rows,
            "EAD_CCF",
            "ccf outside 0 1.5 bounds",
            "invalid_count",
            invalid_ccf_count,
            status_from_count(invalid_ccf_count, "FAIL"),
            f"{ccf_col} should be between 0 and 1.5.",
        )

    if ead_col is not None:
        ead = pd.to_numeric(data[ead_col], errors="coerce")
        non_positive_ead_count = int((ead <= 0).sum())
        add_check(
            rows,
            "EAD_CCF",
            "non positive ead",
            "invalid_count",
            non_positive_ead_count,
            status_from_count(non_positive_ead_count, "FAIL"),
            f"{ead_col} should be positive.",
        )

        q99 = float(ead.quantile(0.99)) if ead.notna().any() else np.nan
        if pd.notna(q99) and q99 > 0:
            high_ead_count = int((ead > q99 * 3).sum())
            add_check(
                rows,
                "EAD_CCF",
                "very high ead",
                "outlier_count",
                high_ead_count,
                status_from_count(high_ead_count, "WARN"),
                f"{ead_col} greater than 3x p99 is treated as an exposure outlier.",
            )

    if undrawn_col is not None:
        undrawn = pd.to_numeric(data[undrawn_col], errors="coerce")
        non_positive_undrawn_count = int((undrawn <= 0).sum())
        add_check(
            rows,
            "EAD_CCF",
            "zero or negative undrawn amount",
            "warning_count",
            non_positive_undrawn_count,
            status_from_count(non_positive_undrawn_count, "WARN"),
            f"{undrawn_col} should be positive for CCF modeling rows.",
        )

    if outstanding_col is not None:
        outstanding = pd.to_numeric(data[outstanding_col], errors="coerce")
        negative_outstanding_count = int((outstanding < 0).sum())
        add_check(
            rows,
            "EAD_CCF",
            "negative outstanding amount",
            "invalid_count",
            negative_outstanding_count,
            status_from_count(negative_outstanding_count, "FAIL"),
            f"{outstanding_col} should not be negative.",
        )

    if limit_col is not None and ead_col is not None:
        limit_amount = pd.to_numeric(data[limit_col], errors="coerce")
        ead = pd.to_numeric(data[ead_col], errors="coerce")

        ead_gt_limit_count = int((ead > limit_amount * 1.5).sum())
        add_check(
            rows,
            "EAD_CCF",
            "ead materially greater than limit",
            "warning_count",
            ead_gt_limit_count,
            status_from_count(ead_gt_limit_count, "WARN"),
            "EAD greater than 1.5x limit amount should be reviewed.",
        )

    return pd.DataFrame(rows, columns=["area", "check_name", "metric_name", "metric_value", "status", "details"])
