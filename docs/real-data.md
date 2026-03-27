# Real Data Guide

Use this guide when your experiment data is not synthetic and already comes from a product API, warehouse export, backend job, or JSON payload.

## Supported Inputs

You can analyze real data in four ways:

- CSV file with user metrics
- CSV file with event rows
- JSON records file
- Python records already loaded in memory

The package also supports HTTP API analysis if you want to post records to the local server.

## Input Shapes

Metrics mode expects one row or record per user.

Required fields:

- `user_id` or `user` or `member_id` or `visitor_id`
- `variant` or `group` or `arm` or `bucket`
- `converted` or `conversion` or `is_converted`

Optional fields:

- `segment` or `cohort`
- `sessions` or `session_count`
- `clicks` or `cta_clicks` or `click_count`
- `revenue` or `value` or `amount`

Events mode expects one row or record per event.

Required fields:

- `user_id` or `user` or `member_id` or `visitor_id`
- `variant` or `group` or `arm` or `bucket`
- `event_type` or `event` or `metric`

Optional fields:

- `segment` or `cohort`
- `occurred_at` or `timestamp` or `event_time`
- `revenue` or `value` or `amount`

## CSV Examples

Metrics CSV:

```bash
ab-testing-platform analyze --csv ./actual-user-metrics.csv --mode metrics --report-dir reports/actual-metrics
```

Events CSV:

```bash
ab-testing-platform analyze --csv ./actual-events.csv --mode events --report-dir reports/actual-events
```

## JSON File Examples

If you do not have CSV and your source already returns JSON, save the records as a JSON file and use `--json`.

Accepted top-level shapes:

- a raw array: `[{"user_id": "...", ...}]`
- an object with `records`
- an object with `data`
- an object with `items`
- an object with `results`

Metrics JSON:

```bash
ab-testing-platform analyze --json ./actual-user-metrics.json --mode metrics --report-dir reports/actual-metrics
```

Events JSON:

```bash
ab-testing-platform analyze --json ./actual-events.json --mode events --report-dir reports/actual-events
```

Example JSON file:

```json
{
  "results": [
    {"user_id": "u001", "variant": "control", "converted": 0, "sessions": 3},
    {"user_id": "u002", "variant": "smart_checkout", "converted": 1, "sessions": 4}
  ]
}
```

## Python API Examples

If your data already exists in Python, you do not need to write a CSV first.

### Metrics Records From an API

```python
from ab_testing_platform import analyze_metrics_records, extract_records

checkout_api_response = {
    "data": [
        {"user_id": "u001", "variant": "control", "converted": 0, "sessions": 3},
        {"user_id": "u002", "variant": "control", "converted": 1, "sessions": 4},
        {"user_id": "u003", "variant": "smart_checkout", "converted": 1, "sessions": 4},
        {"user_id": "u004", "variant": "smart_checkout", "converted": 1, "sessions": 5}
    ]
}

result = analyze_metrics_records(
    records=extract_records(checkout_api_response, source_name="checkout API response"),
    experiment_id="exp-checkout-api",
    experiment_name="Checkout API Data",
    report_dir="reports/actual-metrics",
)

print(result.statistics.absolute_uplift)
print(result.report_paths["json"])
```

### Event Records From an Internal Service

```python
from ab_testing_platform import analyze_events_records

records = [
    {"user_id": "u001", "variant": "control", "event_type": "page_view", "occurred_at": "2026-03-20T10:00:00"},
    {"user_id": "u001", "variant": "control", "event_type": "purchase", "occurred_at": "2026-03-20T10:02:00", "revenue": 49.0},
    {"user_id": "u005", "variant": "smart_checkout", "event_type": "page_view", "occurred_at": "2026-03-20T12:00:00"},
    {"user_id": "u005", "variant": "smart_checkout", "event_type": "purchase", "occurred_at": "2026-03-20T12:02:00", "revenue": 92.5}
]

result = analyze_events_records(
    records=records,
    experiment_id="exp-events-api",
    experiment_name="Purchase Funnel Events",
    report_dir="reports/actual-events",
)
```

## HTTP API Examples

Start the server:

```bash
ab-testing-platform api --host 127.0.0.1 --port 8000
```

Post metrics records:

```powershell
$body = @{
  experiment_id = "exp-api-metrics"
  name = "API Metrics Upload"
  records = @(
    @{ user_id = "u001"; variant = "control"; converted = 0; sessions = 3; clicks = 1 },
    @{ user_id = "u002"; variant = "control"; converted = 1; sessions = 4; clicks = 2; revenue = 89.99 },
    @{ user_id = "u003"; variant = "smart_checkout"; converted = 1; sessions = 4; clicks = 2; revenue = 92.50 },
    @{ user_id = "u004"; variant = "smart_checkout"; converted = 1; sessions = 5; clicks = 3; revenue = 110.00 }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/analysis/metrics-records" -Body $body -ContentType "application/json"
```

Post event records:

```powershell
$body = @{
  experiment_id = "exp-api-events"
  name = "API Events Upload"
  records = @(
    @{ user_id = "u001"; variant = "control"; event_type = "page_view"; occurred_at = "2026-03-20T10:00:00" },
    @{ user_id = "u001"; variant = "control"; event_type = "purchase"; occurred_at = "2026-03-20T10:02:00"; revenue = 49.0 },
    @{ user_id = "u005"; variant = "smart_checkout"; event_type = "page_view"; occurred_at = "2026-03-20T12:00:00" },
    @{ user_id = "u005"; variant = "smart_checkout"; event_type = "purchase"; occurred_at = "2026-03-20T12:02:00"; revenue = 92.5 }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/analysis/events-records" -Body $body -ContentType "application/json"
```

## Exception Handling

The package raises `ValueError` for invalid local input. The HTTP API returns `400` with the same message in the response body.

### Recommended `try/except`

```python
from ab_testing_platform import analyze_metrics_records, extract_records

try:
    result = analyze_metrics_records(
        records=extract_records(api_response, source_name="checkout API response"),
        experiment_id="exp-real-data",
        experiment_name="Checkout API Data",
        report_dir="reports/actual-metrics",
    )
except ValueError as error:
    print(f"Could not analyze experiment data: {error}")
else:
    print(result.decision)
```

### Common Failure Cases

- Missing required fields:
  `Missing required 'user_id' column` or `Missing required 'variant' column`
- Empty input:
  `Metrics data does not contain any rows.` or `Event data does not contain any rows.`
- Invalid conversion values:
  `converted` must be `0`, `1`, `true`, `false`, or a float between `0` and `1`
- Invalid timestamp:
  unsupported `occurred_at` format
- Cross-variant user collisions in event mode:
  the same user cannot appear in multiple variants
- Too few variants:
  at least two variants are required
- Multiple treatment variants:
  specify `treatment_variant` when there is more than one non-control group

## Multi-Variant Data

If your dataset contains more than two variants, explicitly choose the pair you want to compare:

```python
result = analyze_metrics_records(
    records=records,
    experiment_id="exp-checkout-multi-arm",
    experiment_name="Checkout Multi-Arm Test",
    control_variant="control",
    treatment_variant="variant_b",
    report_dir="reports/multi-arm",
)
```

The same `control_variant` and `treatment_variant` options are available in CLI and HTTP API requests.
