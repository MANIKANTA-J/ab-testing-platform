---
name: ab-testing-platform
description: Use this plugin when the user wants to design, run, or analyze A/B tests in this workspace, launch the experimentation API, or summarize conversion uplift and significance.
---

# A/B Testing Platform

Use this plugin for product experimentation work powered by the local backend in `ab_testing_platform/`.

## When to use it

- the user wants to run an A/B test simulation
- the user wants a custom experiment config with segmentation and variants
- the user wants conversion uplift, p-values, confidence intervals, or a ship/no-ship readout
- the user gives a real CSV export and wants the platform to analyze actual results
- the user wants to start the local experimentation API

## Default workflow

1. For a quick demo run:
   `python plugins/ab-testing-platform/scripts/run_demo_experiment.py --users 5000 --seed 7 --report-dir reports/plugin-demo`
2. For a custom experiment:
   edit or duplicate `plugins/ab-testing-platform/examples/smart-checkout-experiment.json`
3. Execute the config:
   `python plugins/ab-testing-platform/scripts/run_experiment_from_config.py --config plugins/ab-testing-platform/examples/smart-checkout-experiment.json --users 3000 --seed 7 --report-dir reports/plugin-custom`
4. Summarize:
   control conversion, treatment conversion, absolute uplift, relative uplift, p-value, confidence interval, and recommendation
5. If code changed, verify with:
   `pytest -q`

## Actual data mode

If the user has a real experiment export, use:

`python plugins/ab-testing-platform/scripts/analyze_actual_data.py --csv <path-to-csv> --mode metrics --report-dir reports/plugin-actual-data`

Supported input modes:

- `metrics`: one row per user with `user_id`, `variant`, and `converted`
- `events`: one row per event with `user_id`, `variant`, and `event_type`

Helpful optional columns:

- `segment`
- `sessions`
- `clicks`
- `revenue`
- `occurred_at` for event CSVs

If there are more than two variants, pass `--control-variant` and `--treatment-variant`.

## API mode

To expose the platform as a local service:

`python plugins/ab-testing-platform/scripts/start_api_server.py --host 127.0.0.1 --port 8000`

Then use:

- `GET /health`
- `GET /experiments`
- `POST /experiments`
- `POST /analysis/metrics-csv`
- `POST /analysis/events-csv`
- `POST /experiments/{experiment_id}/runs`
- `GET /experiments/{experiment_id}/runs/{run_id}`

## Output locations

- reports are written under the `--report-dir` you pass in
- API runs are written under `reports/api` by default
- raw users, assignments, and events are exported as CSV alongside JSON and Markdown summaries
