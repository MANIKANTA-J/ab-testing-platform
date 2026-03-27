from __future__ import annotations

import pytest

from ab_testing_platform.assignment import assign_user
from ab_testing_platform.models import ExperimentConfig, User


@pytest.fixture
def experiment_config() -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id="exp-1",
        name="assignment-test",
        target_segments={"device": ("mobile", "desktop")},
        traffic_allocation=1.0,
        variants={"control": 0.5, "variant": 0.5},
    )


def test_assignment_is_deterministic(experiment_config: ExperimentConfig) -> None:
    user = User(
        user_id="user-100",
        country="US",
        device="mobile",
        acquisition_channel="organic",
        subscription_tier="free",
        sessions_last_30d=12,
        tenure_days=60,
    )

    first = assign_user(user, experiment_config)
    second = assign_user(user, experiment_config)

    assert first.variant == second.variant
    assert first.is_in_experiment is True


def test_non_targeted_user_is_excluded(experiment_config: ExperimentConfig) -> None:
    user = User(
        user_id="user-200",
        country="US",
        device="tablet",
        acquisition_channel="organic",
        subscription_tier="free",
        sessions_last_30d=8,
        tenure_days=30,
    )

    assignment = assign_user(user, experiment_config)

    assert assignment.variant == "not_targeted"
    assert assignment.is_in_experiment is False
