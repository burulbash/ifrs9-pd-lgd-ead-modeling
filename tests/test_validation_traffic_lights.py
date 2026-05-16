from __future__ import annotations

from src.validation_traffic_lights import (
    status_band_good,
    status_max_good,
    status_min_good,
)


def test_status_min_good() -> None:
    assert status_min_good(0.35, green_min=0.30, amber_min=0.20) == "GREEN"
    assert status_min_good(0.25, green_min=0.30, amber_min=0.20) == "AMBER"
    assert status_min_good(0.10, green_min=0.30, amber_min=0.20) == "RED"


def test_status_max_good() -> None:
    assert status_max_good(0, green_max=0, amber_max=1) == "GREEN"
    assert status_max_good(1, green_max=0, amber_max=1) == "AMBER"
    assert status_max_good(2, green_max=0, amber_max=1) == "RED"


def test_status_band_good() -> None:
    assert status_band_good(0.20, green_low=0.10, green_high=0.30, amber_low=0.05, amber_high=0.50) == "GREEN"
    assert status_band_good(0.40, green_low=0.10, green_high=0.30, amber_low=0.05, amber_high=0.50) == "AMBER"
    assert status_band_good(0.80, green_low=0.10, green_high=0.30, amber_low=0.05, amber_high=0.50) == "RED"
