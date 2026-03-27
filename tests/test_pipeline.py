from __future__ import annotations

from pathlib import Path

from ab_testing_platform.pipeline import run_demo_experiment


def test_demo_pipeline_writes_reports(tmp_path: Path) -> None:
    result = run_demo_experiment(user_count=2500, seed=11, report_dir=str(tmp_path))

    assert "control" in result.metrics_by_variant
    assert "smart_checkout" in result.metrics_by_variant
    assert result.total_events > 0
    assert Path(result.report_paths["json"]).exists()
    assert Path(result.report_paths["markdown"]).exists()
    assert Path(result.report_paths["assignments_csv"]).exists()
    assert Path(result.report_paths["users_csv"]).exists()
    assert Path(result.report_paths["events_csv"]).exists()
