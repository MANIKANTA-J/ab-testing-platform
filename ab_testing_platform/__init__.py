"""Backend A/B testing demo platform."""

from .actual_data import (
    analyze_events_csv,
    analyze_events_records,
    analyze_metrics_csv,
    analyze_metrics_records,
    extract_records,
)
from .pipeline import run_demo_experiment, run_experiment

__version__ = "0.2.1"

__all__ = [
    "__version__",
    "analyze_events_csv",
    "analyze_events_records",
    "analyze_metrics_csv",
    "analyze_metrics_records",
    "extract_records",
    "run_demo_experiment",
    "run_experiment",
]
