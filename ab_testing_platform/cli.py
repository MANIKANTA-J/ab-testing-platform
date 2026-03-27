from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .actual_data import (
    analyze_events_csv,
    analyze_events_records,
    analyze_metrics_csv,
    analyze_metrics_records,
    extract_records,
)
from .api import create_server
from .pipeline import run_demo_experiment, run_experiment
from .reporting import result_to_dict
from .serialization import experiment_config_from_dict

_SUBCOMMANDS = {"demo", "run-config", "analyze", "api"}


def main(argv: Sequence[str] | None = None) -> None:
    args_list = list(argv) if argv is not None else sys.argv[1:]
    normalized_args = _normalize_argv(args_list)

    parser = argparse.ArgumentParser(
        prog="ab-testing-platform",
        description="A/B testing and experimentation toolkit.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser("demo", help="Run the synthetic demo experiment.")
    demo_parser.add_argument("--users", type=int, default=5000, help="Number of synthetic users to simulate.")
    demo_parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducible datasets.")
    demo_parser.add_argument("--report-dir", default="reports", help="Directory where reports will be written.")
    demo_parser.add_argument(
        "--output-format",
        choices=("text", "json"),
        default="text",
        help="How to print the command result.",
    )

    config_parser = subparsers.add_parser("run-config", help="Run an experiment from a JSON config file.")
    config_parser.add_argument("--config", required=True, help="Path to the experiment config JSON file.")
    config_parser.add_argument("--users", type=int, default=5000, help="Number of synthetic users to simulate.")
    config_parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducible datasets.")
    config_parser.add_argument("--report-dir", default="reports", help="Directory where reports will be written.")
    config_parser.add_argument(
        "--output-format",
        choices=("text", "json"),
        default="text",
        help="How to print the command result.",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze real experiment data from CSV or JSON records.",
    )
    input_group = analyze_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--csv", help="Path to the input CSV file.")
    input_group.add_argument(
        "--json",
        help="Path to a JSON file containing a record array or an object with records/data/items/results.",
    )
    analyze_parser.add_argument(
        "--mode",
        choices=("metrics", "events"),
        default="metrics",
        help="Whether the CSV contains user-level metrics or event rows.",
    )
    analyze_parser.add_argument("--experiment-id", default="", help="Optional experiment identifier override.")
    analyze_parser.add_argument("--name", default="", help="Optional experiment name override.")
    analyze_parser.add_argument("--primary-metric", default="purchase", help="Primary conversion event or metric.")
    analyze_parser.add_argument("--control-variant", default="", help="Optional control variant name override.")
    analyze_parser.add_argument("--treatment-variant", default="", help="Optional treatment variant name override.")
    analyze_parser.add_argument("--report-dir", default="reports", help="Directory where reports will be written.")
    analyze_parser.add_argument(
        "--output-format",
        choices=("text", "json"),
        default="text",
        help="How to print the command result.",
    )

    api_parser = subparsers.add_parser("api", help="Start the HTTP API server.")
    api_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    api_parser.add_argument("--data-dir", default="api_data", help="Directory for persisted experiments and runs.")
    api_parser.add_argument("--report-root", default="reports/api", help="Directory where API reports are written.")

    args = parser.parse_args(normalized_args)

    if args.command == "demo":
        result = run_demo_experiment(user_count=args.users, seed=args.seed, report_dir=args.report_dir)
        _emit_result(result_to_dict(result), args.output_format)
        return

    if args.command == "run-config":
        config_path = Path(args.config)
        config_payload = json.loads(config_path.read_text(encoding="utf-8"))
        config = experiment_config_from_dict(config_payload)
        result = run_experiment(config=config, user_count=args.users, seed=args.seed, report_dir=args.report_dir)
        _emit_result(result_to_dict(result), args.output_format)
        return

    if args.command == "analyze":
        kwargs = {
            "report_dir": args.report_dir,
            "experiment_id": args.experiment_id or None,
            "experiment_name": args.name or None,
            "primary_metric": args.primary_metric,
            "control_variant": args.control_variant or None,
            "treatment_variant": args.treatment_variant or None,
        }
        if args.csv:
            kwargs["csv_path"] = args.csv
            if args.mode == "metrics":
                result = analyze_metrics_csv(**kwargs)
            else:
                result = analyze_events_csv(**kwargs)
        else:
            records = _load_records_from_json(Path(args.json))
            kwargs["records"] = records
            if args.mode == "metrics":
                result = analyze_metrics_records(**kwargs)
            else:
                result = analyze_events_records(**kwargs)
        _emit_result(result_to_dict(result), args.output_format)
        return

    server = create_server(
        host=args.host,
        port=args.port,
        data_dir=args.data_dir,
        report_root=args.report_root,
    )
    print(f"A/B testing API server listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _normalize_argv(argv: list[str]) -> list[str]:
    if not argv:
        return ["demo"]
    if argv[0] in _SUBCOMMANDS:
        return argv
    return ["demo", *argv]


def _emit_result(payload: dict[str, object], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, indent=2))
        return

    statistics = payload["statistics"]
    report_paths = payload["report_paths"]
    print(payload["experiment"]["name"])
    print(f"Control conversion:   {statistics['control_rate']:.2%}")
    print(f"Treatment conversion: {statistics['treatment_rate']:.2%}")
    print(f"Absolute uplift:      {statistics['absolute_uplift']:.2%}")
    print(f"P-value:              {statistics['p_value']:.4f}")
    print(f"Significant:          {statistics['is_significant']}")
    print(f"Decision:             {payload['decision']}")
    print(f"Reports written to:   {report_paths}")


def _load_records_from_json(json_path: Path) -> list[dict[str, object]]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return list(extract_records(payload, source_name=f"JSON file `{json_path}`"))


if __name__ == "__main__":
    main()
