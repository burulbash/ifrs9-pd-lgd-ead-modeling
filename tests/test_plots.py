from __future__ import annotations

import pandas as pd

from src.plots import (
    save_actual_vs_predicted_plot,
    save_bar_plot,
    save_line_plot,
)


def test_save_bar_plot_creates_file(tmp_path) -> None:
    df = pd.DataFrame({"segment": ["A", "B"], "value": [1, 2]})
    output_path = tmp_path / "bar.png"

    save_bar_plot(
        df,
        x_col="segment",
        y_col="value",
        title="Test bar",
        output_path=output_path,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_save_line_plot_creates_file(tmp_path) -> None:
    df = pd.DataFrame({"month": [1, 2, 3], "value": [1, 3, 2]})
    output_path = tmp_path / "line.png"

    save_line_plot(
        df,
        x_col="month",
        y_col="value",
        title="Test line",
        output_path=output_path,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_save_actual_vs_predicted_plot_creates_file(tmp_path) -> None:
    df = pd.DataFrame(
        {
            "bucket": [1, 2, 3],
            "actual": [0.1, 0.2, 0.3],
            "predicted": [0.12, 0.18, 0.31],
        }
    )
    output_path = tmp_path / "actual_vs_predicted.png"

    save_actual_vs_predicted_plot(
        df,
        x_col="bucket",
        actual_col="actual",
        predicted_col="predicted",
        title="Test actual vs predicted",
        output_path=output_path,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
