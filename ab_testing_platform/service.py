from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .actual_data import (
    analyze_events_csv,
    analyze_events_records,
    analyze_metrics_csv,
    analyze_metrics_records,
    extract_records,
)
from .pipeline import run_experiment
from .reporting import result_to_dict
from .serialization import experiment_config_from_dict, experiment_config_to_dict
from .simulation import build_demo_experiment_config
from .storage import FileBackedExperimentStore


class ServiceError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class ExperimentService:
    def __init__(self, data_dir: str | Path = "api_data", report_root: str | Path = "reports\\api") -> None:
        self.store = FileBackedExperimentStore(data_dir)
        self.report_root = Path(report_root)
        self.report_root.mkdir(parents=True, exist_ok=True)

    def ensure_demo_experiment(self) -> dict[str, Any]:
        demo_config = build_demo_experiment_config()
        if self.store.get_experiment_payload(demo_config.experiment_id) is None:
            payload = experiment_config_to_dict(demo_config)
            self.store.save_experiment_payload(demo_config.experiment_id, payload)
            return payload
        return self.get_experiment(demo_config.experiment_id)

    def list_experiments(self) -> list[dict[str, Any]]:
        return self.store.list_experiment_payloads()

    def create_experiment(self, payload: dict[str, Any]) -> dict[str, Any]:
        config = experiment_config_from_dict(payload)
        if self.store.get_experiment_payload(config.experiment_id) is not None:
            raise ServiceError(409, f"Experiment `{config.experiment_id}` already exists.")

        serialized = experiment_config_to_dict(config)
        self.store.save_experiment_payload(config.experiment_id, serialized)
        return serialized

    def get_experiment(self, experiment_id: str) -> dict[str, Any]:
        payload = self.store.get_experiment_payload(experiment_id)
        if payload is None:
            raise ServiceError(404, f"Experiment `{experiment_id}` was not found.")
        return payload

    def list_runs(self, experiment_id: str) -> list[dict[str, Any]]:
        self.get_experiment(experiment_id)
        return self.store.list_run_payloads(experiment_id)

    def get_run(self, experiment_id: str, run_id: str) -> dict[str, Any]:
        self.get_experiment(experiment_id)
        payload = self.store.get_run_payload(experiment_id, run_id)
        if payload is None:
            raise ServiceError(404, f"Run `{run_id}` for experiment `{experiment_id}` was not found.")
        return payload

    def run_experiment(self, experiment_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        experiment_payload = self.get_experiment(experiment_id)
        config = experiment_config_from_dict(experiment_payload)
        run_payload = payload or {}

        user_count = int(run_payload.get("user_count", 5000))
        seed = int(run_payload.get("seed", 7))
        if user_count <= 0:
            raise ServiceError(400, "`user_count` must be positive.")

        run_id = self._build_run_id(seed=seed, user_count=user_count)
        run_report_dir = self.report_root / self._safe_path_component(experiment_id) / run_id
        result = run_experiment(config=config, user_count=user_count, seed=seed, report_dir=str(run_report_dir))

        response_payload = {
            "run_id": run_id,
            "experiment_id": experiment_id,
            "user_count": user_count,
            "seed": seed,
            "created_at": datetime.utcnow().isoformat(),
            "summary": result_to_dict(result),
        }
        self.store.save_run_payload(experiment_id, run_id, response_payload)
        return response_payload

    def analyze_actual_data(
        self,
        payload: dict[str, Any] | None,
        mode: str,
        source: str = "csv",
    ) -> dict[str, Any]:
        request_payload = payload or {}
        experiment_id = str(request_payload.get("experiment_id", "")).strip() or None
        experiment_name = str(request_payload.get("name", "")).strip() or None
        primary_metric = str(request_payload.get("primary_metric", "purchase")).strip() or "purchase"
        control_variant = str(request_payload.get("control_variant", "")).strip() or None
        treatment_variant = str(request_payload.get("treatment_variant", "")).strip() or None

        run_id = self._build_actual_run_id(mode=mode, source=source)
        report_dir = self.report_root / "actual-data" / run_id

        try:
            if source == "csv":
                csv_path = self._resolve_csv_path(request_payload)
                result = self._analyze_csv(
                    mode=mode,
                    csv_path=csv_path,
                    report_dir=report_dir,
                    experiment_id=experiment_id,
                    experiment_name=experiment_name,
                    primary_metric=primary_metric,
                    control_variant=control_variant,
                    treatment_variant=treatment_variant,
                )
                response: dict[str, Any] = {
                    "run_id": run_id,
                    "mode": mode,
                    "source": source,
                    "source_csv": str(csv_path),
                    "created_at": datetime.utcnow().isoformat(),
                    "summary": result_to_dict(result),
                }
            elif source == "records":
                records = extract_records(request_payload, source_name="request body")
                result = self._analyze_records(
                    mode=mode,
                    records=records,
                    report_dir=report_dir,
                    experiment_id=experiment_id,
                    experiment_name=experiment_name,
                    primary_metric=primary_metric,
                    control_variant=control_variant,
                    treatment_variant=treatment_variant,
                )
                response = {
                    "run_id": run_id,
                    "mode": mode,
                    "source": source,
                    "record_count": len(records),
                    "created_at": datetime.utcnow().isoformat(),
                    "summary": result_to_dict(result),
                }
            else:
                raise ServiceError(400, f"Unsupported analysis source: {source}")
        except ValueError as error:
            raise ServiceError(400, str(error)) from error

        return response

    def _build_run_id(self, seed: int, user_count: int) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
        return f"run-{timestamp}-seed{seed}-users{user_count}"

    def _build_actual_run_id(self, mode: str, source: str) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
        return f"actual-{mode}-{source}-{timestamp}"

    def _resolve_csv_path(self, request_payload: dict[str, Any]) -> Path:
        raw_csv_path = str(request_payload.get("csv_path", "")).strip()
        if not raw_csv_path:
            raise ServiceError(400, "`csv_path` is required for actual-data analysis.")

        csv_path = Path(raw_csv_path)
        if not csv_path.is_absolute():
            csv_path = (Path.cwd() / csv_path).resolve()
        if not csv_path.exists():
            raise ServiceError(404, f"CSV file was not found: {csv_path}")
        return csv_path

    def _analyze_csv(
        self,
        mode: str,
        csv_path: Path,
        report_dir: Path,
        experiment_id: str | None,
        experiment_name: str | None,
        primary_metric: str,
        control_variant: str | None,
        treatment_variant: str | None,
    ):
        if mode == "metrics":
            return analyze_metrics_csv(
                csv_path=csv_path,
                report_dir=report_dir,
                experiment_id=experiment_id,
                experiment_name=experiment_name,
                primary_metric=primary_metric,
                control_variant=control_variant,
                treatment_variant=treatment_variant,
            )
        if mode == "events":
            return analyze_events_csv(
                csv_path=csv_path,
                report_dir=report_dir,
                experiment_id=experiment_id,
                experiment_name=experiment_name,
                primary_metric=primary_metric,
                control_variant=control_variant,
                treatment_variant=treatment_variant,
            )
        raise ServiceError(400, f"Unsupported analysis mode: {mode}")

    def _analyze_records(
        self,
        mode: str,
        records: list[dict[str, Any]],
        report_dir: Path,
        experiment_id: str | None,
        experiment_name: str | None,
        primary_metric: str,
        control_variant: str | None,
        treatment_variant: str | None,
    ):
        if mode == "metrics":
            return analyze_metrics_records(
                records=records,
                report_dir=report_dir,
                experiment_id=experiment_id,
                experiment_name=experiment_name,
                primary_metric=primary_metric,
                control_variant=control_variant,
                treatment_variant=treatment_variant,
            )
        if mode == "events":
            return analyze_events_records(
                records=records,
                report_dir=report_dir,
                experiment_id=experiment_id,
                experiment_name=experiment_name,
                primary_metric=primary_metric,
                control_variant=control_variant,
                treatment_variant=treatment_variant,
            )
        raise ServiceError(400, f"Unsupported analysis mode: {mode}")

    def _safe_path_component(self, value: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "_", value)
