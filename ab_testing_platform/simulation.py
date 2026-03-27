from __future__ import annotations

import random
from datetime import datetime, timedelta

from .models import Event, ExperimentAssignment, ExperimentConfig, User


def build_demo_experiment_config() -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id="exp-checkout-cta-2026-03",
        name="Smart Checkout CTA Experiment",
        target_segments={
            "device": ("mobile", "desktop"),
            "subscription_tier": ("free", "basic"),
        },
        traffic_allocation=0.9,
        variants={"control": 0.5, "smart_checkout": 0.5},
        primary_metric="purchase",
    )


def generate_users(count: int, seed: int = 7) -> list[User]:
    rng = random.Random(seed)

    countries = ["US", "IN", "UK", "DE", "BR"]
    devices = ["mobile", "desktop", "tablet"]
    channels = ["organic", "ads", "email", "referral"]
    subscription_tiers = ["free", "basic", "premium"]

    users: list[User] = []
    for index in range(1, count + 1):
        country = rng.choices(countries, weights=[30, 25, 15, 10, 20], k=1)[0]
        device = rng.choices(devices, weights=[55, 35, 10], k=1)[0]
        tier = rng.choices(subscription_tiers, weights=[65, 25, 10], k=1)[0]
        sessions = max(1, int(rng.gauss(10, 5)))
        tenure_days = max(1, int(rng.gauss(180, 120)))

        users.append(
            User(
                user_id=f"user-{index:05d}",
                country=country,
                device=device,
                acquisition_channel=rng.choice(channels),
                subscription_tier=tier,
                sessions_last_30d=sessions,
                tenure_days=tenure_days,
            )
        )

    return users


def _base_conversion_probability(user: User) -> float:
    probability = 0.035

    if user.device == "desktop":
        probability += 0.008
    elif user.device == "mobile":
        probability += 0.004

    if user.subscription_tier == "basic":
        probability += 0.012
    elif user.subscription_tier == "premium":
        probability += 0.02

    if user.acquisition_channel == "email":
        probability += 0.015
    elif user.acquisition_channel == "organic":
        probability += 0.008

    if user.sessions_last_30d >= 15:
        probability += 0.018
    elif user.sessions_last_30d <= 4:
        probability -= 0.01

    if user.tenure_days <= 45:
        probability += 0.006

    return min(max(probability, 0.01), 0.3)


def _variant_uplift(user: User, variant: str) -> float:
    if variant == "control":
        return 0.0

    uplift = 0.011
    if user.device == "mobile":
        uplift += 0.012
    if user.subscription_tier == "free":
        uplift += 0.006
    if user.acquisition_channel == "ads":
        uplift -= 0.003

    return uplift


def simulate_events(
    users: list[User],
    assignments: list[ExperimentAssignment],
    seed: int = 17,
) -> list[Event]:
    rng = random.Random(seed)
    user_by_id = {user.user_id: user for user in users}
    base_time = datetime(2026, 3, 1, 9, 0, 0)
    events: list[Event] = []

    for assignment in assignments:
        if not assignment.is_in_experiment:
            continue

        user = user_by_id[assignment.user_id]
        session_floor = max(1, user.sessions_last_30d // 6)
        session_ceiling = max(session_floor + 1, user.sessions_last_30d // 3 + 2)
        session_count = rng.randint(session_floor, session_ceiling)

        conversion_probability = min(
            max(_base_conversion_probability(user) + _variant_uplift(user, assignment.variant), 0.001),
            0.7,
        )
        click_probability = min(0.18 + conversion_probability * 1.4, 0.95)

        converted = False
        for session_index in range(session_count):
            session_time = base_time + timedelta(
                days=rng.randint(0, 27),
                hours=rng.randint(0, 23),
                minutes=rng.randint(0, 59),
            )

            events.append(
                Event(
                    user_id=user.user_id,
                    event_type="page_view",
                    occurred_at=session_time,
                    metadata={"variant": assignment.variant},
                )
            )

            if rng.random() <= click_probability:
                events.append(
                    Event(
                        user_id=user.user_id,
                        event_type="cta_click",
                        occurred_at=session_time + timedelta(seconds=10 + session_index),
                        metadata={"variant": assignment.variant},
                    )
                )

            if not converted and rng.random() <= conversion_probability / max(session_count * 0.8, 1):
                converted = True
                revenue = round(rng.uniform(30, 180), 2)
                events.append(
                    Event(
                        user_id=user.user_id,
                        event_type="purchase",
                        occurred_at=session_time + timedelta(minutes=2),
                        metadata={"variant": assignment.variant, "revenue": revenue},
                    )
                )

    return events
