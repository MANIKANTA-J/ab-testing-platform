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

from ab_testing_platform.pipeline import run_demo_experiment
from ab_testing_platform.reporting import result_to_dict


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the demo A/B testing experiment through the plugin.")
    parser.add_argument("--users", type=int, default=5000, help="Number of synthetic users to simulate.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducible runs.")
    parser.add_argument(
        "--report-dir",
        default="reports/plugin-demo",
        help="Directory where reports will be written.",
    )
    args = parser.parse_args()

    report_dir = PROJECT_ROOT / args.report_dir
    result = run_demo_experiment(user_count=args.users, seed=args.seed, report_dir=str(report_dir))
    print(json.dumps(result_to_dict(result), indent=2))


if __name__ == "__main__":
    main()
