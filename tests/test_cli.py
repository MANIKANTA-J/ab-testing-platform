from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_module_cli_demo_json_output(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ab_testing_platform",
            "demo",
            "--users",
            "600",
            "--seed",
            "7",
            "--report-dir",
            str(tmp_path / "demo-reports"),
            "--output-format",
            "json",
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["experiment"]["id"] == "exp-checkout-cta-2026-03"
    assert Path(payload["report_paths"]["json"]).exists()


def test_module_cli_analyze_json_output(tmp_path: Path) -> None:
    csv_path = tmp_path / "actual_metrics.csv"
    csv_path.write_text(
        "\n".join(
            [
                "user_id,variant,segment,converted,sessions,clicks,revenue",
                "u001,control,mobile-free,0,3,1,0",
                "u002,control,mobile-free,1,4,2,89.99",
                "u003,smart_checkout,mobile-free,1,4,2,92.50",
                "u004,smart_checkout,mobile-free,1,5,3,110.00",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ab_testing_platform",
            "analyze",
            "--csv",
            str(csv_path),
            "--mode",
            "metrics",
            "--experiment-id",
            "exp-cli-actual",
            "--name",
            "CLI Actual",
            "--report-dir",
            str(tmp_path / "actual-reports"),
            "--output-format",
            "json",
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["experiment"]["id"] == "exp-cli-actual"
    assert Path(payload["report_paths"]["user_metrics_csv"]).exists()
