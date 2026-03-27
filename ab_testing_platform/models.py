from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Mapping, Tuple


@dataclass(frozen=True)
class User:
    user_id: str
    country: str
    device: str
    acquisition_channel: str
    subscription_tier: str
    sessions_last_30d: int
    tenure_days: int


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str
    name: str
    target_segments: Mapping[str, Tuple[str, ...]]
    traffic_allocation: float
    variants: Mapping[str, float]
    primary_metric: str = "purchase"


@dataclass(frozen=True)
class ExperimentAssignment:
    user_id: str
    experiment_id: str
    segment: str
    variant: str
    is_targeted: bool
    is_in_experiment: bool


@dataclass(frozen=True)
class Event:
    user_id: str
    event_type: str
    occurred_at: datetime
    metadata: Mapping[str, float | str] = field(default_factory=dict)


@dataclass
class UserMetricSnapshot:
    user_id: str
    variant: str
    segment: str
    converted: float = 0.0
    sessions: int = 0
    clicks: int = 0
    revenue: float = 0.0


@dataclass(frozen=True)
class ExperimentStatistics:
    control_variant: str
    treatment_variant: str
    control_rate: float
    treatment_rate: float
    absolute_uplift: float
    relative_uplift: float
    p_value: float
    confidence_interval: Tuple[float, float]
    is_significant: bool
    t_statistic: float
    degrees_of_freedom: float
    sample_sizes: Mapping[str, int]


@dataclass
class ExperimentResult:
    config: ExperimentConfig
    assignments: list[ExperimentAssignment]
    user_metrics: list[UserMetricSnapshot]
    metrics_by_variant: Dict[str, Dict[str, float]]
    metrics_by_segment: Dict[str, Dict[str, float]]
    stats: ExperimentStatistics
    total_events: int
    generated_at: datetime = field(default_factory=datetime.utcnow)
    report_paths: Dict[str, str] = field(default_factory=dict)
