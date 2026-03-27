# A/B Testing Platform Plugin

This local Codex plugin wraps the workspace A/B testing backend so you can use it as an installable analytics tool.

## What it gives you

- a plugin skill for A/B testing and experiment analysis
- helper scripts to run the demo pipeline, analyze actual CSV data, or execute a custom experiment config
- a wrapper to start the local experimentation API

## Quick commands

```powershell
python plugins\ab-testing-platform\scripts\run_demo_experiment.py --users 5000 --seed 7 --report-dir reports\plugin-demo
python plugins\ab-testing-platform\scripts\run_experiment_from_config.py --config plugins\ab-testing-platform\examples\smart-checkout-experiment.json --users 3000 --seed 7 --report-dir reports\plugin-custom
python plugins\ab-testing-platform\scripts\analyze_actual_data.py --csv plugins\ab-testing-platform\examples\actual-user-metrics.csv --mode metrics --report-dir reports\plugin-actual-metrics
python plugins\ab-testing-platform\scripts\analyze_actual_data.py --csv plugins\ab-testing-platform\examples\actual-events.csv --mode events --report-dir reports\plugin-actual-events
python plugins\ab-testing-platform\scripts\start_api_server.py --host 127.0.0.1 --port 8000
```
