from __future__ import annotations

import hashlib

from .models import ExperimentAssignment, ExperimentConfig, User
from .segmentation import derive_segment, user_matches_target_segments


def _hash_to_unit_interval(*parts: str) -> float:
    digest = hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:15], 16) / float(0xFFFFFFFFFFFFFFF)


def assign_user(user: User, config: ExperimentConfig) -> ExperimentAssignment:
    segment = derive_segment(user)
    is_targeted = user_matches_target_segments(user, dict(config.target_segments))

    if not is_targeted:
        return ExperimentAssignment(
            user_id=user.user_id,
            experiment_id=config.experiment_id,
            segment=segment,
            variant="not_targeted",
            is_targeted=False,
            is_in_experiment=False,
        )

    experiment_bucket = _hash_to_unit_interval(user.user_id, config.experiment_id, "traffic")
    if experiment_bucket > config.traffic_allocation:
        return ExperimentAssignment(
            user_id=user.user_id,
            experiment_id=config.experiment_id,
            segment=segment,
            variant="holdout",
            is_targeted=True,
            is_in_experiment=False,
        )

    variant_bucket = _hash_to_unit_interval(user.user_id, config.experiment_id, "variant")
    cumulative_weight = 0.0
    chosen_variant = "control"
    for variant, weight in config.variants.items():
        cumulative_weight += weight
        if variant_bucket <= cumulative_weight:
            chosen_variant = variant
            break

    return ExperimentAssignment(
        user_id=user.user_id,
        experiment_id=config.experiment_id,
        segment=segment,
        variant=chosen_variant,
        is_targeted=True,
        is_in_experiment=True,
    )


def assign_users(users: list[User], config: ExperimentConfig) -> list[ExperimentAssignment]:
    return [assign_user(user, config) for user in users]
