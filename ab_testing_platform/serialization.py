from __future__ import annotations

from typing import Any

from .models import ExperimentConfig, User

_SUPPORTED_METRICS = {"purchase", "cta_click"}
_USER_ATTRIBUTES = set(User.__dataclass_fields__.keys())


def experiment_config_to_dict(config: ExperimentConfig) -> dict[str, Any]:
    return {
        "experiment_id": config.experiment_id,
        "name": config.name,
        "target_segments": {key: list(values) for key, values in config.target_segments.items()},
        "traffic_allocation": config.traffic_allocation,
        "variants": dict(config.variants),
        "primary_metric": config.primary_metric,
    }


def experiment_config_from_dict(payload: dict[str, Any]) -> ExperimentConfig:
    if not isinstance(payload, dict):
        raise ValueError("Experiment payload must be a JSON object.")

    experiment_id = str(payload.get("experiment_id", "")).strip()
    name = str(payload.get("name", "")).strip()
    if not experiment_id:
        raise ValueError("`experiment_id` is required.")
    if not name:
        raise ValueError("`name` is required.")

    raw_target_segments = payload.get("target_segments", {})
    if raw_target_segments is None:
        raw_target_segments = {}
    if not isinstance(raw_target_segments, dict):
        raise ValueError("`target_segments` must be an object keyed by user attributes.")

    target_segments: dict[str, tuple[str, ...]] = {}
    for attribute, allowed_values in raw_target_segments.items():
        attribute_name = str(attribute)
        if attribute_name not in _USER_ATTRIBUTES:
            raise ValueError(f"Unsupported segmentation attribute: `{attribute_name}`.")

        if isinstance(allowed_values, str):
            values = (allowed_values,)
        elif isinstance(allowed_values, (list, tuple)):
            values = tuple(str(value) for value in allowed_values if str(value).strip())
        else:
            raise ValueError(f"Segment values for `{attribute_name}` must be a string or array.")

        target_segments[attribute_name] = values

    traffic_allocation = float(payload.get("traffic_allocation", 1.0))
    if not 0.0 < traffic_allocation <= 1.0:
        raise ValueError("`traffic_allocation` must be between 0 and 1.")

    raw_variants = payload.get("variants")
    if not isinstance(raw_variants, dict) or len(raw_variants) < 2:
        raise ValueError("`variants` must define at least two variants.")

    parsed_variants: dict[str, float] = {}
    total_weight = 0.0
    for variant_name, raw_weight in raw_variants.items():
        normalized_name = str(variant_name).strip()
        weight = float(raw_weight)
        if not normalized_name:
            raise ValueError("Variant names must be non-empty.")
        if weight <= 0.0:
            raise ValueError("Variant weights must be positive.")
        parsed_variants[normalized_name] = weight
        total_weight += weight

    variants = {
        variant_name: weight / total_weight
        for variant_name, weight in parsed_variants.items()
    }

    primary_metric = str(payload.get("primary_metric", "purchase")).strip() or "purchase"
    if primary_metric not in _SUPPORTED_METRICS:
        supported_metrics = ", ".join(sorted(_SUPPORTED_METRICS))
        raise ValueError(f"`primary_metric` must be one of: {supported_metrics}.")

    return ExperimentConfig(
        experiment_id=experiment_id,
        name=name,
        target_segments=target_segments,
        traffic_allocation=traffic_allocation,
        variants=variants,
        primary_metric=primary_metric,
    )
