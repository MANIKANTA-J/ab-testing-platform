from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_plugin_demo_wrapper_runs(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "plugins" / "ab-testing-platform" / "scripts" / "run_demo_experiment.py"),
            "--users",
            "600",
            "--seed",
            "9",
            "--report-dir",
            str(tmp_path / "plugin-demo"),
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["experiment"]["id"] == "exp-checkout-cta-2026-03"
    assert Path(payload["report_paths"]["json"]).exists()


def test_plugin_config_wrapper_runs(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "plugins" / "ab-testing-platform" / "scripts" / "run_experiment_from_config.py"),
            "--config",
            str(
                PROJECT_ROOT
                / "plugins"
                / "ab-testing-platform"
                / "examples"
                / "smart-checkout-experiment.json"
            ),
            "--users",
            "600",
            "--seed",
            "12",
            "--report-dir",
            str(tmp_path / "plugin-custom"),
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["experiment"]["id"] == "exp-smart-checkout-plugin"
    assert Path(payload["report_paths"]["markdown"]).exists()


def test_plugin_actual_data_wrapper_runs(tmp_path: Path) -> None:
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
            str(PROJECT_ROOT / "plugins" / "ab-testing-platform" / "scripts" / "analyze_actual_data.py"),
            "--csv",
            str(csv_path),
            "--mode",
            "metrics",
            "--experiment-id",
            "exp-plugin-actual",
            "--name",
            "Plugin Actual Metrics",
            "--report-dir",
            str(tmp_path / "plugin-actual"),
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["experiment"]["id"] == "exp-plugin-actual"
    assert Path(payload["report_paths"]["user_metrics_csv"]).exists()


def test_plugin_api_wrapper_help_text() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "plugins" / "ab-testing-platform" / "scripts" / "start_api_server.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        check=True,
    )

    assert "Start the A/B testing API server through the plugin." in result.stdout
