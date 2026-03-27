from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote


class FileBackedExperimentStore:
    def __init__(self, root_dir: str | Path = "api_data") -> None:
        self.root_dir = Path(root_dir)
        self.experiments_dir = self.root_dir / "experiments"
        self.runs_dir = self.root_dir / "runs"
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def _file_name(self, identifier: str) -> str:
        return f"{quote(identifier, safe='')}.json"

    def _run_dir(self, experiment_id: str) -> Path:
        directory = self.runs_dir / quote(experiment_id, safe="")
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def list_experiment_payloads(self) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for path in sorted(self.experiments_dir.glob("*.json")):
            payloads.append(json.loads(path.read_text(encoding="utf-8")))
        return payloads

    def save_experiment_payload(self, experiment_id: str, payload: dict[str, Any]) -> None:
        path = self.experiments_dir / self._file_name(experiment_id)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_experiment_payload(self, experiment_id: str) -> dict[str, Any] | None:
        path = self.experiments_dir / self._file_name(experiment_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_run_payloads(self, experiment_id: str) -> list[dict[str, Any]]:
        run_dir = self._run_dir(experiment_id)
        payloads: list[dict[str, Any]] = []
        for path in sorted(run_dir.glob("*.json")):
            payloads.append(json.loads(path.read_text(encoding="utf-8")))
        return payloads

    def save_run_payload(self, experiment_id: str, run_id: str, payload: dict[str, Any]) -> None:
        path = self._run_dir(experiment_id) / self._file_name(run_id)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_run_payload(self, experiment_id: str, run_id: str) -> dict[str, Any] | None:
        path = self._run_dir(experiment_id) / self._file_name(run_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
