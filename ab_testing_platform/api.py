from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .service import ExperimentService, ServiceError


class ExperimentAPIHandler(BaseHTTPRequestHandler):
    service: ExperimentService

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _dispatch(self, method: str) -> None:
        try:
            parsed_url = urlparse(self.path)
            path_parts = [unquote(part) for part in parsed_url.path.strip("/").split("/") if part]
            query = parse_qs(parsed_url.query)
            payload = self._read_json_payload() if method == "POST" else None

            if method == "GET" and path_parts == ["health"]:
                self._send_json(200, {"status": "ok"})
                return

            if method == "GET" and path_parts == ["experiments"]:
                self._send_json(200, {"experiments": self.service.list_experiments()})
                return

            if method == "POST" and path_parts == ["experiments"]:
                experiment = self.service.create_experiment(payload or {})
                self._send_json(201, {"experiment": experiment})
                return

            if method == "POST" and path_parts == ["analysis", "metrics-csv"]:
                analysis = self.service.analyze_actual_data(payload, mode="metrics", source="csv")
                self._send_json(201, analysis)
                return

            if method == "POST" and path_parts == ["analysis", "events-csv"]:
                analysis = self.service.analyze_actual_data(payload, mode="events", source="csv")
                self._send_json(201, analysis)
                return

            if method == "POST" and path_parts == ["analysis", "metrics-records"]:
                analysis = self.service.analyze_actual_data(payload, mode="metrics", source="records")
                self._send_json(201, analysis)
                return

            if method == "POST" and path_parts == ["analysis", "events-records"]:
                analysis = self.service.analyze_actual_data(payload, mode="events", source="records")
                self._send_json(201, analysis)
                return

            if len(path_parts) == 2 and path_parts[0] == "experiments" and method == "GET":
                experiment = self.service.get_experiment(path_parts[1])
                runs = self.service.list_runs(path_parts[1])
                self._send_json(200, {"experiment": experiment, "runs": runs})
                return

            if len(path_parts) == 3 and path_parts[0] == "experiments" and path_parts[2] == "runs":
                experiment_id = path_parts[1]
                if method == "GET":
                    runs = self.service.list_runs(experiment_id)
                    self._send_json(200, {"experiment_id": experiment_id, "runs": runs})
                    return
                if method == "POST":
                    run = self.service.run_experiment(experiment_id, payload)
                    self._send_json(201, run)
                    return

            if len(path_parts) == 4 and path_parts[0] == "experiments" and path_parts[2] == "runs" and method == "GET":
                run = self.service.get_run(path_parts[1], path_parts[3])
                if query.get("view") == ["summary"]:
                    self._send_json(200, {"run_id": run["run_id"], "summary": run["summary"]})
                    return
                self._send_json(200, run)
                return

            self._send_json(404, {"error": "Route not found."})
        except ServiceError as error:
            self._send_json(error.status_code, {"error": error.message})
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Request body must contain valid JSON."})
        except Exception as error:  # pragma: no cover - defensive fallback
            self._send_json(500, {"error": f"Internal server error: {error}"})

    def _read_json_payload(self) -> dict[str, Any] | None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return None

        raw_body = self.rfile.read(content_length).decode("utf-8")
        if not raw_body.strip():
            return None
        payload = json.loads(raw_body)
        if payload is not None and not isinstance(payload, dict):
            raise ValueError("JSON request body must be an object.")
        return payload

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    data_dir: str = "api_data",
    report_root: str = "reports\\api",
) -> ThreadingHTTPServer:
    service = ExperimentService(data_dir=data_dir, report_root=report_root)
    service.ensure_demo_experiment()

    class Handler(ExperimentAPIHandler):
        pass

    Handler.service = service
    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the A/B testing platform API server.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    parser.add_argument("--data-dir", default="api_data", help="Directory used to persist experiments and runs.")
    parser.add_argument("--report-root", default="reports\\api", help="Directory where run reports are written.")
    args = parser.parse_args()

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


if __name__ == "__main__":
    main()
