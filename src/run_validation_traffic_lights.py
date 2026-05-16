from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import REPORTS_DIR  # noqa: E402
from src.validation_traffic_lights import build_validation_traffic_light_summary  # noqa: E402


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    summary = build_validation_traffic_light_summary(REPORTS_DIR)
    output_path = REPORTS_DIR / "validation_traffic_light_summary.csv"
    summary.to_csv(output_path, index=False)

    print("Validation traffic light summary")
    print(summary)
    print()
    print("Report saved to:", output_path)


if __name__ == "__main__":
    main()
