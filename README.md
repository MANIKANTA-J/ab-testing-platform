# A/B Testing & Experimentation Platform

Python toolkit for running synthetic A/B tests and analyzing real experiment data from CSV files, JSON records, API responses, or your own backend pipelines.

## Install

Published package:

```bash
pip install ab-testing-platform
```

Development install:

```bash
pip install -e .[test,publish]
```

## Quick Start

Run the demo experiment:

```bash
ab-testing-platform demo --users 5000 --seed 7 --report-dir reports
```

Analyze real data from CSV:

```bash
ab-testing-platform analyze --csv ./actual-user-metrics.csv --mode metrics --report-dir reports/actual-metrics
```

Analyze real data from JSON records:

```bash
ab-testing-platform analyze --json ./actual-user-metrics.json --mode metrics --report-dir reports/actual-metrics
```

Start the API server:

```bash
ab-testing-platform api --host 127.0.0.1 --port 8000
```

## Real Data

Supported real-data inputs:

- CSV exports
- JSON files with a top-level `records`, `data`, `items`, or `results` array
- Python `list[dict]` records from APIs, databases, or internal services
- HTTP API analysis routes for CSV and in-memory records

Use these package helpers when your data already lives in Python:

```python
from ab_testing_platform import analyze_metrics_records, extract_records

api_response = {
    "data": [
        {"user_id": "u001", "variant": "control", "converted": 0},
        {"user_id": "u002", "variant": "smart_checkout", "converted": 1},
    ]
}

result = analyze_metrics_records(
    records=extract_records(api_response, source_name="checkout API response"),
    experiment_id="exp-real-data",
    experiment_name="Checkout CTA Test",
    report_dir="reports/real-data",
)
```

For the full real-data guide, examples, field mappings, and `try/except` cases, see [docs/real-data.md](docs/real-data.md).

## HTTP API

Available routes:

- `GET /health`
- `GET /experiments`
- `POST /experiments`
- `POST /analysis/metrics-csv`
- `POST /analysis/events-csv`
- `POST /analysis/metrics-records`
- `POST /analysis/events-records`
- `GET /experiments/{experiment_id}`
- `GET /experiments/{experiment_id}/runs`
- `POST /experiments/{experiment_id}/runs`
- `GET /experiments/{experiment_id}/runs/{run_id}`

## Tests

```bash
pytest -q
```

## Release

Build locally:

```bash
python -m build
python -m twine check dist/*
```

This repository also includes GitHub Actions for CI and Trusted Publishing:

- `.github/workflows/ci.yml`
- `.github/workflows/publish.yml`
