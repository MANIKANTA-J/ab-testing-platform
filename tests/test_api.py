from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Iterator
from urllib import request

import pytest

from ab_testing_platform.api import create_server


@pytest.fixture
def api_base_url(tmp_path: Path) -> Iterator[str]:
    data_dir = tmp_path / "data"
    report_root = tmp_path / "reports"
    server = create_server(host="127.0.0.1", port=0, data_dir=str(data_dir), report_root=str(report_root))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_api_create_run_and_fetch_flow(api_base_url: str) -> None:
    health = _request_json("GET", f"{api_base_url}/health")
    assert health["status"] == "ok"

    create_payload = {
        "experiment_id": "exp-api-checkout",
        "name": "API Checkout Experiment",
        "target_segments": {
            "device": ["mobile", "desktop"],
            "subscription_tier": ["free", "basic"],
        },
        "traffic_allocation": 0.85,
        "variants": {"control": 50, "variant_b": 50},
        "primary_metric": "purchase",
    }
    created = _request_json("POST", f"{api_base_url}/experiments", create_payload)
    assert created["experiment"]["experiment_id"] == "exp-api-checkout"

    experiments = _request_json("GET", f"{api_base_url}/experiments")
    experiment_ids = {item["experiment_id"] for item in experiments["experiments"]}
    assert "exp-api-checkout" in experiment_ids

    run = _request_json(
        "POST",
        f"{api_base_url}/experiments/exp-api-checkout/runs",
        {"user_count": 1200, "seed": 21},
    )
    assert run["experiment_id"] == "exp-api-checkout"
    assert "statistics" in run["summary"]
    assert "report_paths" in run["summary"]
    assert run["summary"]["total_events"] > 0
    assert Path(run["summary"]["report_paths"]["json"]).exists()

    runs = _request_json("GET", f"{api_base_url}/experiments/exp-api-checkout/runs")
    assert len(runs["runs"]) == 1

    run_id = run["run_id"]
    fetched_run = _request_json(
        "GET",
        f"{api_base_url}/experiments/exp-api-checkout/runs/{run_id}?view=summary",
    )
    assert fetched_run["run_id"] == run_id
    assert fetched_run["summary"]["experiment"]["name"] == "API Checkout Experiment"


def test_api_analyzes_actual_metrics_csv(api_base_url: str, tmp_path: Path) -> None:
    csv_path = tmp_path / "actual_metrics.csv"
    csv_path.write_text(
        "\n".join(
            [
                "user_id,variant,segment,converted,sessions,clicks,revenue",
                "u001,control,mobile-free,0,3,1,0",
                "u002,control,mobile-free,0,4,2,0",
                "u003,control,desktop-basic,1,5,2,80",
                "u004,smart_checkout,mobile-free,1,4,2,92",
                "u005,smart_checkout,mobile-free,1,5,3,110",
                "u006,smart_checkout,desktop-basic,0,2,1,0",
            ]
        ),
        encoding="utf-8",
    )

    analysis = _request_json(
        "POST",
        f"{api_base_url}/analysis/metrics-csv",
        {
            "csv_path": str(csv_path),
            "experiment_id": "exp-api-actual",
            "name": "API Actual Metrics",
        },
    )

    assert analysis["mode"] == "metrics"
    assert analysis["summary"]["experiment"]["id"] == "exp-api-actual"
    assert Path(analysis["summary"]["report_paths"]["json"]).exists()


def _request_json(method: str, url: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    headers = {"Content-Type": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url, method=method, headers=headers, data=data)
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))
