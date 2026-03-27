from __future__ import annotations

from .models import User


def user_matches_target_segments(user: User, target_segments: dict[str, tuple[str, ...]] | object) -> bool:
    if not isinstance(target_segments, dict):
        return True

    for attribute, allowed_values in target_segments.items():
        if allowed_values and getattr(user, attribute) not in allowed_values:
            return False
    return True


def derive_segment(user: User) -> str:
    if user.sessions_last_30d >= 20:
        lifecycle = "power"
    elif user.sessions_last_30d >= 8:
        lifecycle = "active"
    else:
        lifecycle = "new"

    return f"{user.country}-{user.device}-{user.subscription_tier}-{lifecycle}"
