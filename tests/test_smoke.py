from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import (
    MODELS_DIR,
    PLOTS_DIR,
    REPORTS_DIR,
    TARGET_DEFAULT_12M,
)
from src.db import read_csv_table
from src.metrics import compute_binary_metrics, compute_regression_metrics
from src.splitting import make_time_split


def test_project_output_paths_are_separate() -> None:
    assert REPORTS_DIR.name == "reports"
    assert PLOTS_DIR.name == "plots"
    assert MODELS_DIR.name == "models"


def test_read_csv_table_loads_file(tmp_path) -> None:
    csv_path = tmp_path / "sample.csv"
    pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_csv(csv_path, index=False)

    df = read_csv_table(str(csv_path))

    assert df.shape == (2, 2)
    assert list(df.columns) == ["a", "b"]


def test_time_split_keeps_chronological_order() -> None:
    df = pd.DataFrame(
        {
            "observation_date": pd.date_range("2024-01-01", periods=100, freq="D"),
            TARGET_DEFAULT_12M: [0] * 90 + [1] * 10,
        }
    )

    train_df, valid_df, oot_df, summary = make_time_split(df)

    assert len(train_df) == 70
    assert len(valid_df) == 15
    assert len(oot_df) == 15

    assert train_df["observation_date"].max() <= valid_df["observation_date"].min()
    assert valid_df["observation_date"].max() <= oot_df["observation_date"].min()

    assert set(summary["split"]) == {"train", "valid", "oot"}


def test_binary_metrics_for_perfect_ranking() -> None:
    y_true = np.array([0, 0, 1, 1])
    y_score = np.array([0.1, 0.2, 0.8, 0.9])

    metrics = compute_binary_metrics(y_true, y_score)

    assert metrics["roc_auc"] == 1.0
    assert metrics["gini"] == 1.0
    assert metrics["ks"] == 1.0
    assert metrics["observed_default_rate"] == 0.5


def test_regression_metrics_basic_values() -> None:
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.0, 2.5, 2.5])

    metrics = compute_regression_metrics(y_true, y_pred)

    assert round(metrics["mae"], 4) == 0.3333
    assert round(metrics["rmse"], 4) == 0.4082
    assert metrics["mean_actual"] == 2.0
    assert metrics["mean_predicted"] == 2.0
