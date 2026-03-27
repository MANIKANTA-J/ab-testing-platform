# A/B Testing & Experimentation Platform

This project is a self-contained Python backend demo that simulates a realistic product experiment lifecycle:

- deterministic user segmentation and traffic allocation into control and treatment groups
- synthetic event generation for experiment exposures, clicks, and purchases
- backend metric aggregation for conversions, sessions, clicks, and revenue
- Welch's t-test significance checks and 95% confidence intervals for conversion uplift
- automated JSON and Markdown reports with decision-ready experiment insights
- a zero-dependency HTTP API for creating experiments and querying run results programmatically

## Install

After publishing, users can install it with:

```bash
pip install ab-testing-platform
```

From source during development:

```bash
pip install -e .[test,publish]
```

## Project Structure

```text
ab_testing_platform/
  actual_data.py
  assignment.py
  models.py
  pipeline.py
  reporting.py
  api.py
  serialization.py
  service.py
  storage.py
  segmentation.py
  simulation.py
  statistics.py
  tracking.py
tests/
reports/
```

## How It Works

1. `simulation.py` generates structured user datasets and experiment event streams.
2. `assignment.py` deterministically assigns eligible users to `control` or `smart_checkout`.
3. `tracking.py` aggregates user-level metrics from the event stream.
4. `statistics.py` runs Welch's t-test and builds a confidence interval around the uplift.
5. `reporting.py` exports JSON and Markdown reports for stakeholders.

## Run The Demo

Installed CLI:

```bash
ab-testing-platform demo --users 5000 --seed 7 --report-dir reports
```

Module form:

```powershell
python -m ab_testing_platform demo --users 5000 --seed 7 --report-dir reports
```

The command writes:

- `reports/exp-checkout-cta-2026-03.json`
- `reports/exp-checkout-cta-2026-03.md`
- `reports/exp-checkout-cta-2026-03_assignments.csv`
- `reports/exp-checkout-cta-2026-03_users.csv`
- `reports/exp-checkout-cta-2026-03_events.csv`

## Run Tests

```powershell
pytest
```

## Analyze Actual Data

If you have a real experiment export, you can analyze it directly from CSV.

Metrics CSV mode expects at least:

- `user_id`
- `variant`
- `converted`

Optional metrics columns:

- `segment`
- `sessions`
- `clicks`
- `revenue`

Event CSV mode expects at least:

- `user_id`
- `variant`
- `event_type`

Optional event columns:

- `segment`
- `occurred_at`
- `revenue`

Examples:

```bash
ab-testing-platform analyze --csv ./actual-user-metrics.csv --mode metrics --report-dir reports/actual-metrics
ab-testing-platform analyze --csv ./actual-events.csv --mode events --report-dir reports/actual-events
```

## Run The API

```bash
ab-testing-platform api --host 127.0.0.1 --port 8000
```

## Use As A Codex Plugin

This workspace now includes a repo-local Codex plugin at `plugins/ab-testing-platform`, with marketplace registration in `.agents/plugins/marketplace.json`.

Useful plugin wrapper commands:

```powershell
python plugins\ab-testing-platform\scripts\run_demo_experiment.py --users 5000 --seed 7 --report-dir reports\plugin-demo
python plugins\ab-testing-platform\scripts\run_experiment_from_config.py --config plugins\ab-testing-platform\examples\smart-checkout-experiment.json --users 3000 --seed 7 --report-dir reports\plugin-custom
python plugins\ab-testing-platform\scripts\analyze_actual_data.py --csv plugins\ab-testing-platform\examples\actual-user-metrics.csv --mode metrics --report-dir reports\plugin-actual-data
python plugins\ab-testing-platform\scripts\start_api_server.py --host 127.0.0.1 --port 8000
```

Available endpoints:

- `GET /health`
- `GET /experiments`
- `POST /experiments`
- `POST /analysis/metrics-csv`
- `POST /analysis/events-csv`
- `GET /experiments/{experiment_id}`
- `GET /experiments/{experiment_id}/runs`
- `POST /experiments/{experiment_id}/runs`
- `GET /experiments/{experiment_id}/runs/{run_id}`

Example PowerShell flow:

```powershell
$body = @{
  experiment_id = "exp-api-checkout"
  name = "API Checkout Experiment"
  target_segments = @{
    device = @("mobile", "desktop")
    subscription_tier = @("free", "basic")
  }
  traffic_allocation = 0.85
  variants = @{
    control = 50
    variant_b = 50
  }
  primary_metric = "purchase"
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/experiments" -Body $body -ContentType "application/json"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/experiments/exp-api-checkout/runs" -Body '{"user_count":1200,"seed":21}' -ContentType "application/json"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/analysis/metrics-csv" -Body '{"csv_path":"plugins\\ab-testing-platform\\examples\\actual-user-metrics.csv","experiment_id":"exp-actual-upload","name":"Actual Upload"}' -ContentType "application/json"
```

## Build And Publish

Build the distributable artifacts:

```bash
python -m build
```

Validate the metadata before upload:

```bash
python -m twine check dist/*
```

Upload to PyPI:

```bash
python -m twine upload dist/*
```

## Example Decision Logic

- ship the treatment when uplift is positive and statistically significant
- reject the treatment when it is significantly worse than control
- continue iterating when the result is directionally positive but inconclusive
