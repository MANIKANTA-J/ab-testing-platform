from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _find_project_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").exists() and (candidate / "ab_testing_platform").exists():
            return candidate
    raise RuntimeError("Could not locate project root for the A/B testing platform.")


PROJECT_ROOT = _find_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ab_testing_platform.actual_data import (
    analyze_events_csv,
    analyze_events_records,
    analyze_metrics_csv,
    analyze_metrics_records,
    extract_records,
)
from ab_testing_platform.reporting import result_to_dict


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze real A/B testing data through the plugin."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--csv", help="Path to the input CSV file.")
    input_group.add_argument(
        "--json",
        help="Path to a JSON file containing a record array or an object with records/data/items/results.",
    )
    parser.add_argument(
        "--mode",
        choices=("metrics", "events"),
        default="metrics",
        help="Whether the CSV contains one row per user metric snapshot or one row per event.",
    )
    parser.add_argument("--experiment-id", default="", help="Optional experiment identifier override.")
    parser.add_argument("--name", default="", help="Optional experiment name override.")
    parser.add_argument("--primary-metric", default="purchase", help="Primary conversion event or metric name.")
    parser.add_argument("--control-variant", default="", help="Optional control variant name override.")
    parser.add_argument("--treatment-variant", default="", help="Optional treatment variant name override.")
    parser.add_argument(
        "--report-dir",
        default="reports/plugin-actual-data",
        help="Directory where reports will be written.",
    )
    args = parser.parse_args()

    report_dir = PROJECT_ROOT / args.report_dir
    kwargs = {
        "report_dir": report_dir,
        "experiment_id": args.experiment_id or None,
        "experiment_name": args.name or None,
        "primary_metric": args.primary_metric,
        "control_variant": args.control_variant or None,
        "treatment_variant": args.treatment_variant or None,
    }

    if args.csv:
        csv_path = (PROJECT_ROOT / args.csv).resolve() if not Path(args.csv).is_absolute() else Path(args.csv)
        kwargs["csv_path"] = csv_path
        if args.mode == "metrics":
            result = analyze_metrics_csv(**kwargs)
        else:
            result = analyze_events_csv(**kwargs)
    else:
        json_path = (PROJECT_ROOT / args.json).resolve() if not Path(args.json).is_absolute() else Path(args.json)
        kwargs["records"] = list(
            extract_records(
                json.loads(json_path.read_text(encoding="utf-8")),
                source_name=f"JSON file `{json_path}`",
            )
        )
        if args.mode == "metrics":
            result = analyze_metrics_records(**kwargs)
        else:
            result = analyze_events_records(**kwargs)

    print(json.dumps(result_to_dict(result), indent=2))


if __name__ == "__main__":
    main()
