from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
PLOTS_DIR = PROJECT_ROOT / "outputs" / "plots"
MODELS_DIR = PROJECT_ROOT / "outputs" / "models"

RANDOM_STATE = 42

DATE_COL = "observation_date"
TARGET_DEFAULT_12M = "target_default_12m"

TRAIN_SIZE = 0.70
VALID_SIZE = 0.15
OOT_SIZE = 0.15

RATING_GRADES = ["A", "B", "C", "D", "E", "F", "Default"]

SCENARIO_WEIGHTS = {
    "base": 0.60,
    "downside": 0.25,
    "upside": 0.15,
}

IFRS9_STAGE_LABELS = {
    1: "Stage 1",
    2: "Stage 2",
    3: "Stage 3",
}
