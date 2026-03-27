"""Backend A/B testing demo platform."""

from .actual_data import analyze_events_csv, analyze_metrics_csv
from .pipeline import run_demo_experiment, run_experiment

__version__ = "0.2.1"

__all__ = ["__version__", "analyze_events_csv", "analyze_metrics_csv", "run_demo_experiment", "run_experiment"]
