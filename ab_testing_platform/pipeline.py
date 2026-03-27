from __future__ import annotations

from .assignment import assign_users
from .models import Event, ExperimentAssignment, ExperimentConfig, ExperimentResult, User, UserMetricSnapshot
from .reporting import write_reports
from .simulation import build_demo_experiment_config, generate_users, simulate_events
from .statistics import welch_t_test
from .tracking import build_user_metric_snapshots, summarize_metrics_by_variant, summarize_segment_uplift


def build_experiment_result(
    config: ExperimentConfig,
    assignments: list[ExperimentAssignment],
    user_metrics: list[UserMetricSnapshot],
    total_events: int,
    report_dir: str = "reports",
    users: list[User] | None = None,
    events: list[Event] | None = None,
) -> ExperimentResult:
    control_variant, treatment_variant = list(config.variants.keys())[:2]
    metrics_by_variant = summarize_metrics_by_variant(user_metrics)
    metrics_by_segment = summarize_segment_uplift(user_metrics, control_variant, treatment_variant)

    control_values = [
        snapshot.converted for snapshot in user_metrics if snapshot.variant == control_variant
    ]
    treatment_values = [
        snapshot.converted for snapshot in user_metrics if snapshot.variant == treatment_variant
    ]
    stats = welch_t_test(
        control_values,
        treatment_values,
        control_variant=control_variant,
        treatment_variant=treatment_variant,
    )

    result = ExperimentResult(
        config=config,
        assignments=assignments,
        user_metrics=user_metrics,
        metrics_by_variant=metrics_by_variant,
        metrics_by_segment=metrics_by_segment,
        stats=stats,
        total_events=total_events,
    )
    result.report_paths = write_reports(
        result,
        report_dir=report_dir,
        users=users,
        events=events,
        user_metrics=user_metrics,
    )
    return result


def run_experiment(
    config: ExperimentConfig,
    user_count: int = 5000,
    seed: int = 7,
    report_dir: str = "reports",
) -> ExperimentResult:
    users = generate_users(user_count, seed=seed)
    assignments = assign_users(users, config)
    events = simulate_events(users, assignments, seed=seed + 101)
    user_metrics = build_user_metric_snapshots(assignments, events, primary_metric=config.primary_metric)
    return build_experiment_result(
        config=config,
        assignments=assignments,
        user_metrics=user_metrics,
        total_events=len(events),
        report_dir=report_dir,
        users=users,
        events=events,
    )


def run_demo_experiment(
    user_count: int = 5000,
    seed: int = 7,
    report_dir: str = "reports",
) -> ExperimentResult:
    return run_experiment(
        config=build_demo_experiment_config(),
        user_count=user_count,
        seed=seed,
        report_dir=report_dir,
    )
