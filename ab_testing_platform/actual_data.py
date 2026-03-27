from __future__ import annotations

import csv
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from .models import Event, ExperimentAssignment, ExperimentConfig, UserMetricSnapshot
from .pipeline import build_experiment_result

_USER_ID_ALIASES = ("user_id", "user", "member_id", "visitor_id")
_VARIANT_ALIASES = ("variant", "group", "arm", "bucket")
_SEGMENT_ALIASES = ("segment", "cohort")
_CONVERTED_ALIASES = ("converted", "conversion", "is_converted")
_SESSIONS_ALIASES = ("sessions", "session_count")
_CLICKS_ALIASES = ("clicks", "cta_clicks", "click_count")
_REVENUE_ALIASES = ("revenue", "value", "amount")
_EVENT_TYPE_ALIASES = ("event_type", "event", "metric")
_TIMESTAMP_ALIASES = ("occurred_at", "timestamp", "event_time")


def analyze_metrics_csv(
    csv_path: str | Path,
    report_dir: str | Path = "reports",
    experiment_id: str | None = None,
    experiment_name: str | None = None,
    primary_metric: str = "purchase",
    control_variant: str | None = None,
    treatment_variant: str | None = None,
):
    rows = _read_csv_rows(csv_path)
    if not rows:
        raise ValueError("Metrics CSV does not contain any rows.")

    user_metrics: list[UserMetricSnapshot] = []
    variant_counts: OrderedDict[str, int] = OrderedDict()
    assignments: list[ExperimentAssignment] = []

    for row in rows:
        user_id = _require_value(row, _USER_ID_ALIASES, "user_id")
        variant = _require_value(row, _VARIANT_ALIASES, "variant")
        converted = _parse_conversion_value(_require_value(row, _CONVERTED_ALIASES, "converted"))
        segment = _optional_value(row, _SEGMENT_ALIASES, default="all_users")
        sessions = int(_parse_float(_optional_value(row, _SESSIONS_ALIASES, default="0")))
        clicks = int(_parse_float(_optional_value(row, _CLICKS_ALIASES, default="0")))
        revenue = _parse_float(_optional_value(row, _REVENUE_ALIASES, default="0"))

        user_metrics.append(
            UserMetricSnapshot(
                user_id=user_id,
                variant=variant,
                segment=segment,
                converted=converted,
                sessions=sessions,
                clicks=clicks,
                revenue=revenue,
            )
        )
        assignments.append(
            ExperimentAssignment(
                user_id=user_id,
                experiment_id=experiment_id or Path(csv_path).stem,
                segment=segment,
                variant=variant,
                is_targeted=True,
                is_in_experiment=True,
            )
        )
        variant_counts[variant] = variant_counts.get(variant, 0) + 1

    config = _build_actual_config(
        variant_counts=variant_counts,
        experiment_id=experiment_id or Path(csv_path).stem,
        experiment_name=experiment_name or f"Actual Data Analysis - {Path(csv_path).stem}",
        primary_metric=primary_metric,
        control_variant=control_variant,
        treatment_variant=treatment_variant,
    )
    assignments = [
        ExperimentAssignment(
            user_id=assignment.user_id,
            experiment_id=config.experiment_id,
            segment=assignment.segment,
            variant=assignment.variant,
            is_targeted=True,
            is_in_experiment=True,
        )
        for assignment in assignments
    ]
    total_events = sum(
        snapshot.sessions + snapshot.clicks + (1 if snapshot.converted > 0 else 0)
        for snapshot in user_metrics
    )
    return build_experiment_result(
        config=config,
        assignments=assignments,
        user_metrics=user_metrics,
        total_events=total_events,
        report_dir=str(report_dir),
    )


def analyze_events_csv(
    csv_path: str | Path,
    report_dir: str | Path = "reports",
    experiment_id: str | None = None,
    experiment_name: str | None = None,
    primary_metric: str = "purchase",
    control_variant: str | None = None,
    treatment_variant: str | None = None,
):
    rows = _read_csv_rows(csv_path)
    if not rows:
        raise ValueError("Events CSV does not contain any rows.")

    total_events = 0
    variant_counts: OrderedDict[str, int] = OrderedDict()
    events: list[Event] = []
    user_metrics_by_id: OrderedDict[str, UserMetricSnapshot] = OrderedDict()

    for row in rows:
        user_id = _require_value(row, _USER_ID_ALIASES, "user_id")
        variant = _require_value(row, _VARIANT_ALIASES, "variant")
        event_type = _require_value(row, _EVENT_TYPE_ALIASES, "event_type")
        segment = _optional_value(row, _SEGMENT_ALIASES, default="all_users")
        revenue = _parse_float(_optional_value(row, _REVENUE_ALIASES, default="0"))
        occurred_at = _parse_timestamp(_optional_value(row, _TIMESTAMP_ALIASES, default=""))

        snapshot = user_metrics_by_id.get(user_id)
        if snapshot is None:
            snapshot = UserMetricSnapshot(
                user_id=user_id,
                variant=variant,
                segment=segment,
            )
            user_metrics_by_id[user_id] = snapshot
            variant_counts[variant] = variant_counts.get(variant, 0) + 1
        else:
            if snapshot.variant != variant:
                raise ValueError(f"User `{user_id}` appears in multiple variants.")
            if snapshot.segment == "all_users" and segment != "all_users":
                snapshot.segment = segment

        if event_type == "page_view":
            snapshot.sessions += 1
        elif event_type == "cta_click":
            snapshot.clicks += 1
        if event_type == primary_metric:
            snapshot.converted = 1.0
            snapshot.revenue += revenue

        events.append(
            Event(
                user_id=user_id,
                event_type=event_type,
                occurred_at=occurred_at,
                metadata={"variant": variant, "revenue": revenue},
            )
        )
        total_events += 1

    config = _build_actual_config(
        variant_counts=variant_counts,
        experiment_id=experiment_id or Path(csv_path).stem,
        experiment_name=experiment_name or f"Actual Event Analysis - {Path(csv_path).stem}",
        primary_metric=primary_metric,
        control_variant=control_variant,
        treatment_variant=treatment_variant,
    )
    assignments = [
        ExperimentAssignment(
            user_id=snapshot.user_id,
            experiment_id=config.experiment_id,
            segment=snapshot.segment,
            variant=snapshot.variant,
            is_targeted=True,
            is_in_experiment=True,
        )
        for snapshot in user_metrics_by_id.values()
    ]
    return build_experiment_result(
        config=config,
        assignments=assignments,
        user_metrics=list(user_metrics_by_id.values()),
        total_events=total_events,
        report_dir=str(report_dir),
        events=events,
    )


def _read_csv_rows(csv_path: str | Path) -> list[dict[str, str]]:
    path = Path(csv_path)
    if not path.exists():
        raise ValueError(f"CSV file was not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV file must include a header row.")
        return [_normalize_row(row) for row in reader]


def _normalize_row(row: dict[str, str | None]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized[key.strip().lower()] = "" if value is None else str(value).strip()
    return normalized


def _require_value(row: dict[str, str], aliases: tuple[str, ...], field_name: str) -> str:
    value = _optional_value(row, aliases)
    if not value:
        alias_list = ", ".join(aliases)
        raise ValueError(f"Missing required `{field_name}` column. Accepted headers: {alias_list}.")
    return value


def _optional_value(
    row: dict[str, str],
    aliases: tuple[str, ...],
    default: str = "",
) -> str:
    for alias in aliases:
        value = row.get(alias)
        if value not in (None, ""):
            return value
    return default


def _parse_conversion_value(value: str) -> float:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return 1.0
    if normalized in {"0", "false", "no", "n"}:
        return 0.0

    parsed = float(value)
    if not 0.0 <= parsed <= 1.0:
        raise ValueError("`converted` values must be between 0 and 1.")
    return parsed


def _parse_float(value: str) -> float:
    if not value:
        return 0.0
    return float(value)


def _parse_timestamp(value: str) -> datetime:
    if not value:
        return datetime.utcnow()

    cleaned = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError as error:
        raise ValueError(f"Unsupported timestamp value: {value}") from error


def _build_actual_config(
    variant_counts: OrderedDict[str, int],
    experiment_id: str,
    experiment_name: str,
    primary_metric: str,
    control_variant: str | None,
    treatment_variant: str | None,
) -> ExperimentConfig:
    if len(variant_counts) < 2:
        raise ValueError("Actual-data analysis requires at least two variants.")

    ordered_variants = _resolve_variant_order(
        variant_names=list(variant_counts.keys()),
        control_variant=control_variant,
        treatment_variant=treatment_variant,
    )
    total_users = float(sum(variant_counts.values()))
    variants = {
        variant_name: variant_counts[variant_name] / total_users
        for variant_name in ordered_variants
    }

    return ExperimentConfig(
        experiment_id=experiment_id,
        name=experiment_name,
        target_segments={},
        traffic_allocation=1.0,
        variants=variants,
        primary_metric=primary_metric,
    )


def _resolve_variant_order(
    variant_names: list[str],
    control_variant: str | None,
    treatment_variant: str | None,
) -> list[str]:
    unique_variants = list(dict.fromkeys(variant_names))

    if control_variant is None:
        for variant_name in unique_variants:
            if variant_name.lower() == "control":
                control_variant = variant_name
                break
        else:
            control_variant = unique_variants[0]
    elif control_variant not in unique_variants:
        raise ValueError(f"Control variant `{control_variant}` was not found in the data.")

    remaining = [variant for variant in unique_variants if variant != control_variant]
    if not remaining:
        raise ValueError("Actual-data analysis requires a treatment variant.")

    if treatment_variant is None:
        if len(remaining) == 1:
            treatment_variant = remaining[0]
        else:
            candidate = next(
                (
                    variant
                    for variant in remaining
                    if variant.lower() in {"variant", "treatment", "test"}
                ),
                None,
            )
            if candidate is None:
                raise ValueError(
                    "Multiple treatment variants were found. Please specify `treatment_variant`."
                )
            treatment_variant = candidate
    elif treatment_variant not in unique_variants:
        raise ValueError(f"Treatment variant `{treatment_variant}` was not found in the data.")

    ordered_variants = [control_variant, treatment_variant]
    ordered_variants.extend(
        variant for variant in unique_variants if variant not in ordered_variants
    )
    return ordered_variants
