from __future__ import annotations

from pathlib import Path

import pytest

from ab_testing_platform.actual_data import (
    analyze_events_csv,
    analyze_events_records,
    analyze_metrics_csv,
    analyze_metrics_records,
    extract_records,
)


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


def test_analyze_metrics_records_supports_api_style_payloads(tmp_path: Path) -> None:
    payload = {
        "data": [
            {"user_id": "u001", "variant": "control", "converted": 0, "sessions": 3, "clicks": 1},
            {"user_id": "u002", "variant": "control", "converted": 1, "sessions": 4, "clicks": 2, "revenue": 89.99},
            {"user_id": "u003", "variant": "smart_checkout", "converted": 1, "sessions": 4, "clicks": 2, "revenue": 92.50},
            {"user_id": "u004", "variant": "smart_checkout", "converted": 1, "sessions": 5, "clicks": 3, "revenue": 110.00},
        ]
    }

    result = analyze_metrics_records(
        records=extract_records(payload, source_name="API payload"),
        report_dir=tmp_path / "reports-records",
        experiment_id="exp-records-metrics",
        experiment_name="Records Metrics Test",
    )

    assert result.config.experiment_id == "exp-records-metrics"
    assert result.metrics_by_variant["smart_checkout"]["conversion_rate"] > result.metrics_by_variant["control"]["conversion_rate"]
    assert Path(result.report_paths["json"]).exists()


def test_analyze_events_records_supports_in_memory_records(tmp_path: Path) -> None:
    records = [
        {"user_id": "u001", "variant": "control", "event_type": "page_view", "occurred_at": "2026-03-20T10:00:00"},
        {"user_id": "u001", "variant": "control", "event_type": "cta_click", "occurred_at": "2026-03-20T10:02:00"},
        {"user_id": "u005", "variant": "smart_checkout", "event_type": "page_view", "occurred_at": "2026-03-20T12:00:00"},
        {"user_id": "u005", "variant": "smart_checkout", "event_type": "cta_click", "occurred_at": "2026-03-20T12:00:05"},
        {"user_id": "u005", "variant": "smart_checkout", "event_type": "purchase", "occurred_at": "2026-03-20T12:02:00", "revenue": 92.50},
        {"user_id": "u006", "variant": "smart_checkout", "event_type": "purchase", "occurred_at": "2026-03-20T13:03:00", "revenue": 110.0},
    ]

    result = analyze_events_records(
        records=records,
        report_dir=tmp_path / "reports-events-records",
        experiment_id="exp-records-events",
        experiment_name="Records Events Test",
    )

    assert result.config.experiment_id == "exp-records-events"
    assert result.total_events == 6
    assert result.metrics_by_variant["smart_checkout"]["conversion_rate"] > result.metrics_by_variant["control"]["conversion_rate"]
    assert Path(result.report_paths["events_csv"]).exists()


def test_extract_records_raises_for_missing_record_container() -> None:
    with pytest.raises(ValueError, match="must be a list of records or an object containing one of"):
        extract_records({"meta": {"page": 1}}, source_name="API payload")
