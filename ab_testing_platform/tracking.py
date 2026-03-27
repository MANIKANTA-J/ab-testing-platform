from __future__ import annotations

from collections import defaultdict

from .models import Event, ExperimentAssignment, UserMetricSnapshot


def build_user_metric_snapshots(
    assignments: list[ExperimentAssignment],
    events: list[Event],
    primary_metric: str,
) -> list[UserMetricSnapshot]:
    included_assignments = {
        assignment.user_id: assignment for assignment in assignments if assignment.is_in_experiment
    }
    snapshots = {
        user_id: UserMetricSnapshot(
            user_id=user_id,
            variant=assignment.variant,
            segment=assignment.segment,
        )
        for user_id, assignment in included_assignments.items()
    }

    for event in events:
        snapshot = snapshots.get(event.user_id)
        if snapshot is None:
            continue

        if event.event_type == "page_view":
            snapshot.sessions += 1
        elif event.event_type == "cta_click":
            snapshot.clicks += 1

        if event.event_type == primary_metric:
            snapshot.converted = 1.0
            revenue = event.metadata.get("revenue", 0.0)
            if isinstance(revenue, (int, float)):
                snapshot.revenue += float(revenue)

    return list(snapshots.values())


def summarize_metrics_by_variant(user_metrics: list[UserMetricSnapshot]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[UserMetricSnapshot]] = defaultdict(list)
    for snapshot in user_metrics:
        grouped[snapshot.variant].append(snapshot)

    summary: dict[str, dict[str, float]] = {}
    for variant, snapshots in grouped.items():
        users = len(snapshots)
        conversions = sum(snapshot.converted for snapshot in snapshots)
        sessions = sum(snapshot.sessions for snapshot in snapshots)
        clicks = sum(snapshot.clicks for snapshot in snapshots)
        revenue = sum(snapshot.revenue for snapshot in snapshots)

        summary[variant] = {
            "users": float(users),
            "conversions": conversions,
            "conversion_rate": conversions / users if users else 0.0,
            "avg_sessions": sessions / users if users else 0.0,
            "avg_clicks": clicks / users if users else 0.0,
            "revenue_per_user": revenue / users if users else 0.0,
        }

    return summary


def summarize_segment_uplift(
    user_metrics: list[UserMetricSnapshot],
    control_variant: str,
    treatment_variant: str,
    min_users_per_variant: int = 10,
) -> dict[str, dict[str, float]]:
    segment_grouped: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {control_variant: [], treatment_variant: []}
    )

    for snapshot in user_metrics:
        if snapshot.variant in segment_grouped[snapshot.segment]:
            segment_grouped[snapshot.segment][snapshot.variant].append(snapshot.converted)

    summary: dict[str, dict[str, float]] = {}
    for segment, values in segment_grouped.items():
        control_values = values[control_variant]
        treatment_values = values[treatment_variant]
        if not control_values or not treatment_values:
            continue
        if len(control_values) < min_users_per_variant or len(treatment_values) < min_users_per_variant:
            continue

        control_rate = sum(control_values) / len(control_values)
        treatment_rate = sum(treatment_values) / len(treatment_values)
        uplift = treatment_rate - control_rate
        summary[segment] = {
            "control_rate": control_rate,
            "treatment_rate": treatment_rate,
            "absolute_uplift": uplift,
            "control_users": float(len(control_values)),
            "treatment_users": float(len(treatment_values)),
        }

    return dict(
        sorted(
            summary.items(),
            key=lambda item: abs(item[1]["absolute_uplift"]),
            reverse=True,
        )
    )
