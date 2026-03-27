from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Event, ExperimentResult, User, UserMetricSnapshot


def _decision_summary(result: ExperimentResult) -> str:
    stats = result.stats
    if stats.is_significant and stats.absolute_uplift > 0:
        return "Ship the treatment. The experiment shows a statistically significant conversion lift."
    if stats.is_significant and stats.absolute_uplift < 0:
        return "Do not ship the treatment. The treatment underperforms the control with statistical significance."
    return "Keep collecting data or iterate on the treatment. The current lift is not statistically conclusive."


def result_to_dict(result: ExperimentResult) -> dict[str, object]:
    return {
        "experiment": {
            "id": result.config.experiment_id,
            "name": result.config.name,
            "primary_metric": result.config.primary_metric,
            "traffic_allocation": result.config.traffic_allocation,
            "variants": dict(result.config.variants),
        },
        "generated_at": result.generated_at.isoformat(),
        "report_paths": dict(result.report_paths),
        "total_assignments": len(result.assignments),
        "total_in_experiment": sum(1 for assignment in result.assignments if assignment.is_in_experiment),
        "total_events": result.total_events,
        "metrics_by_variant": result.metrics_by_variant,
        "metrics_by_segment": result.metrics_by_segment,
        "statistics": {
            "control_variant": result.stats.control_variant,
            "treatment_variant": result.stats.treatment_variant,
            "control_rate": result.stats.control_rate,
            "treatment_rate": result.stats.treatment_rate,
            "absolute_uplift": result.stats.absolute_uplift,
            "relative_uplift": result.stats.relative_uplift,
            "p_value": result.stats.p_value,
            "confidence_interval": list(result.stats.confidence_interval),
            "is_significant": result.stats.is_significant,
            "t_statistic": result.stats.t_statistic,
            "degrees_of_freedom": result.stats.degrees_of_freedom,
            "sample_sizes": dict(result.stats.sample_sizes),
        },
        "decision": _decision_summary(result),
    }


def render_markdown_report(result: ExperimentResult) -> str:
    stats = result.stats
    lines = [
        f"# {result.config.name}",
        "",
        "## Experiment Overview",
        f"- Experiment ID: `{result.config.experiment_id}`",
        f"- Primary metric: `{result.config.primary_metric}`",
        f"- Included users: {sum(1 for assignment in result.assignments if assignment.is_in_experiment)}",
        f"- Total tracked events: {result.total_events}",
        "",
        "## Variant Performance",
        "| Variant | Users | Conversion Rate | Avg Sessions | Avg Clicks | Revenue / User |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for variant, metrics in result.metrics_by_variant.items():
        lines.append(
            "| {variant} | {users:.0f} | {conversion_rate:.2%} | {avg_sessions:.2f} | {avg_clicks:.2f} | ${revenue_per_user:.2f} |".format(
                variant=variant,
                **metrics,
            )
        )

    lines.extend(
        [
            "",
            "## Statistical Readout",
            f"- Control: `{stats.control_variant}` at {stats.control_rate:.2%}",
            f"- Treatment: `{stats.treatment_variant}` at {stats.treatment_rate:.2%}",
            f"- Absolute uplift: {stats.absolute_uplift:.2%}",
            f"- Relative uplift: {stats.relative_uplift:.2%}",
            f"- Welch's t-test p-value: {stats.p_value:.4f}",
            (
                "- 95% confidence interval for uplift: "
                f"[{stats.confidence_interval[0]:.2%}, {stats.confidence_interval[1]:.2%}]"
            ),
            f"- Significant at 95% confidence: {'Yes' if stats.is_significant else 'No'}",
            "",
            "## Decision Insight",
            f"- {_decision_summary(result)}",
            "",
            "## Top Segment Shifts",
            "| Segment | Control Rate | Treatment Rate | Absolute Uplift | Control Users | Treatment Users |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for segment, metrics in list(result.metrics_by_segment.items())[:8]:
        lines.append(
            "| {segment} | {control_rate:.2%} | {treatment_rate:.2%} | {absolute_uplift:.2%} | {control_users:.0f} | {treatment_users:.0f} |".format(
                segment=segment,
                **metrics,
            )
        )

    return "\n".join(lines) + "\n"


def _write_users_csv(users: list[User], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "user_id",
                "country",
                "device",
                "acquisition_channel",
                "subscription_tier",
                "sessions_last_30d",
                "tenure_days",
            ]
        )
        for user in users:
            writer.writerow(
                [
                    user.user_id,
                    user.country,
                    user.device,
                    user.acquisition_channel,
                    user.subscription_tier,
                    user.sessions_last_30d,
                    user.tenure_days,
                ]
            )


def _write_events_csv(events: list[Event], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["user_id", "event_type", "occurred_at", "metadata"])
        for event in events:
            writer.writerow(
                [
                    event.user_id,
                    event.event_type,
                    event.occurred_at.isoformat(),
                    json.dumps(dict(event.metadata), sort_keys=True),
                ]
            )


def _write_assignments_csv(result: ExperimentResult, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "user_id",
                "experiment_id",
                "segment",
                "variant",
                "is_targeted",
                "is_in_experiment",
            ]
        )
        for assignment in result.assignments:
            writer.writerow(
                [
                    assignment.user_id,
                    assignment.experiment_id,
                    assignment.segment,
                    assignment.variant,
                    assignment.is_targeted,
                    assignment.is_in_experiment,
                ]
            )


def _write_user_metrics_csv(user_metrics: list[UserMetricSnapshot], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "user_id",
                "variant",
                "segment",
                "converted",
                "sessions",
                "clicks",
                "revenue",
            ]
        )
        for snapshot in user_metrics:
            writer.writerow(
                [
                    snapshot.user_id,
                    snapshot.variant,
                    snapshot.segment,
                    snapshot.converted,
                    snapshot.sessions,
                    snapshot.clicks,
                    snapshot.revenue,
                ]
            )


def write_reports(
    result: ExperimentResult,
    report_dir: str | Path,
    users: list[User] | None = None,
    events: list[Event] | None = None,
    user_metrics: list[UserMetricSnapshot] | None = None,
) -> dict[str, str]:
    report_root = Path(report_dir)
    report_root.mkdir(parents=True, exist_ok=True)
    base_name = result.config.experiment_id

    json_path = report_root / f"{base_name}.json"
    markdown_path = report_root / f"{base_name}.md"
    assignments_path = report_root / f"{base_name}_assignments.csv"

    json_path.write_text(json.dumps(result_to_dict(result), indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown_report(result), encoding="utf-8")
    _write_assignments_csv(result, assignments_path)

    output_paths = {
        "json": str(json_path),
        "markdown": str(markdown_path),
        "assignments_csv": str(assignments_path),
    }

    if users is not None:
        users_path = report_root / f"{base_name}_users.csv"
        _write_users_csv(users, users_path)
        output_paths["users_csv"] = str(users_path)

    if user_metrics is not None:
        user_metrics_path = report_root / f"{base_name}_user_metrics.csv"
        _write_user_metrics_csv(user_metrics, user_metrics_path)
        output_paths["user_metrics_csv"] = str(user_metrics_path)

    if events is not None:
        events_path = report_root / f"{base_name}_events.csv"
        _write_events_csv(events, events_path)
        output_paths["events_csv"] = str(events_path)

    return output_paths
