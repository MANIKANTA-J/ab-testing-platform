from __future__ import annotations

from pathlib import Path

from ab_testing_platform.actual_data import analyze_events_csv, analyze_metrics_csv


def test_analyze_metrics_csv_returns_statistical_summary(tmp_path: Path) -> None:
    csv_path = tmp_path / "actual_metrics.csv"
    csv_path.write_text(
        "\n".join(
            [
                "user_id,variant,segment,converted,sessions,clicks,revenue",
                "u001,control,mobile-free,0,3,1,0",
                "u002,control,mobile-free,0,4,2,0",
                "u003,control,desktop-basic,0,2,1,0",
                "u004,control,desktop-basic,1,5,2,80",
                "u005,smart_checkout,mobile-free,1,4,2,92",
                "u006,smart_checkout,mobile-free,1,5,3,110",
                "u007,smart_checkout,desktop-basic,1,4,2,84",
                "u008,smart_checkout,desktop-basic,0,2,1,0",
            ]
        ),
        encoding="utf-8",
    )

    result = analyze_metrics_csv(
        csv_path=csv_path,
        report_dir=tmp_path / "reports-metrics",
        experiment_id="exp-actual-metrics",
        experiment_name="Actual Metrics Test",
    )

    assert result.config.experiment_id == "exp-actual-metrics"
    assert result.metrics_by_variant["smart_checkout"]["conversion_rate"] > result.metrics_by_variant["control"]["conversion_rate"]
    assert Path(result.report_paths["json"]).exists()
    assert Path(result.report_paths["user_metrics_csv"]).exists()


def test_analyze_events_csv_returns_event_summary(tmp_path: Path) -> None:
    csv_path = tmp_path / "actual_events.csv"
    csv_path.write_text(
        "\n".join(
            [
                "user_id,variant,segment,event_type,occurred_at,revenue",
                "u001,control,mobile-free,page_view,2026-03-20T10:00:00,0",
                "u001,control,mobile-free,cta_click,2026-03-20T10:00:08,0",
                "u002,control,mobile-free,page_view,2026-03-20T11:00:00,0",
                "u002,control,mobile-free,purchase,2026-03-20T11:02:00,89.99",
                "u005,smart_checkout,mobile-free,page_view,2026-03-20T12:00:00,0",
                "u005,smart_checkout,mobile-free,cta_click,2026-03-20T12:00:05,0",
                "u005,smart_checkout,mobile-free,purchase,2026-03-20T12:02:00,92.50",
                "u006,smart_checkout,mobile-free,page_view,2026-03-20T13:00:00,0",
                "u006,smart_checkout,mobile-free,purchase,2026-03-20T13:03:00,110.00",
            ]
        ),
        encoding="utf-8",
    )

    result = analyze_events_csv(
        csv_path=csv_path,
        report_dir=tmp_path / "reports-events",
        experiment_id="exp-actual-events",
        experiment_name="Actual Events Test",
    )

    assert result.config.experiment_id == "exp-actual-events"
    assert result.total_events == 9
    assert result.metrics_by_variant["smart_checkout"]["conversion_rate"] > result.metrics_by_variant["control"]["conversion_rate"]
    assert Path(result.report_paths["events_csv"]).exists()
