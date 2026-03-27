from __future__ import annotations

import argparse
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

from ab_testing_platform.api import create_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the A/B testing API server through the plugin.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    parser.add_argument("--data-dir", default="api_data", help="Directory for persisted experiments and runs.")
    parser.add_argument("--report-root", default="reports/api", help="Directory where API reports are written.")
    args = parser.parse_args()

    data_dir = PROJECT_ROOT / args.data_dir
    report_root = PROJECT_ROOT / args.report_root
    server = create_server(
        host=args.host,
        port=args.port,
        data_dir=str(data_dir),
        report_root=str(report_root),
    )

    print(f"A/B testing plugin API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
