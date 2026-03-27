from __future__ import annotations

import math

from .models import ExperimentStatistics

_EPSILON = 3.0e-14
_FPMIN = 1.0e-300
_MAX_ITERATIONS = 200


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _sample_variance(values: list[float], mean_value: float) -> float:
    if len(values) < 2:
        return 0.0
    return sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - (qab * x / qap)
    if abs(d) < _FPMIN:
        d = _FPMIN
    d = 1.0 / d
    h = d

    for iteration in range(1, _MAX_ITERATIONS + 1):
        step = 2 * iteration

        aa = iteration * (b - iteration) * x / ((qam + step) * (a + step))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        h *= d * c

        aa = -((a + iteration) * (qab + iteration) * x) / ((a + step) * (qap + step))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta

        if abs(delta - 1.0) < _EPSILON:
            break

    return h


def _regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    log_beta = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    beta_term = math.exp(log_beta)

    if x < (a + 1.0) / (a + b + 2.0):
        return beta_term * _beta_continued_fraction(a, b, x) / a
    return 1.0 - (beta_term * _beta_continued_fraction(b, a, 1.0 - x) / b)


def student_t_cdf(t_statistic: float, degrees_of_freedom: float) -> float:
    if degrees_of_freedom <= 0:
        raise ValueError("Degrees of freedom must be positive.")

    if t_statistic == 0:
        return 0.5

    x = degrees_of_freedom / (degrees_of_freedom + t_statistic**2)
    beta_value = _regularized_incomplete_beta(degrees_of_freedom / 2.0, 0.5, x)

    if t_statistic > 0:
        return 1.0 - 0.5 * beta_value
    return 0.5 * beta_value


def inverse_student_t_cdf(probability: float, degrees_of_freedom: float) -> float:
    if not 0.0 < probability < 1.0:
        raise ValueError("Probability must be between 0 and 1.")

    if probability == 0.5:
        return 0.0

    negative = probability < 0.5
    target = probability if not negative else 1.0 - probability
    low = 0.0
    high = 1.0

    while student_t_cdf(high, degrees_of_freedom) < target:
        high *= 2.0
        if high > 1_000:
            break

    for _ in range(100):
        midpoint = (low + high) / 2.0
        cdf = student_t_cdf(midpoint, degrees_of_freedom)
        if cdf < target:
            low = midpoint
        else:
            high = midpoint

    quantile = (low + high) / 2.0
    return -quantile if negative else quantile


def welch_t_test(
    control_values: list[float],
    treatment_values: list[float],
    control_variant: str = "control",
    treatment_variant: str = "variant",
    alpha: float = 0.05,
) -> ExperimentStatistics:
    if not control_values or not treatment_values:
        raise ValueError("Both control and treatment groups must contain at least one observation.")

    control_mean = _mean(control_values)
    treatment_mean = _mean(treatment_values)
    control_variance = _sample_variance(control_values, control_mean)
    treatment_variance = _sample_variance(treatment_values, treatment_mean)

    control_count = len(control_values)
    treatment_count = len(treatment_values)
    absolute_uplift = treatment_mean - control_mean
    relative_uplift = (
        absolute_uplift / control_mean
        if control_mean
        else (math.inf if absolute_uplift > 0 else 0.0)
    )

    variance_term = (control_variance / control_count) + (treatment_variance / treatment_count)
    if variance_term == 0.0:
        p_value = 0.0 if absolute_uplift else 1.0
        confidence_interval = (absolute_uplift, absolute_uplift)
        t_statistic = math.inf if absolute_uplift > 0 else (-math.inf if absolute_uplift < 0 else 0.0)
        degrees_of_freedom = float(control_count + treatment_count - 2)
    else:
        t_statistic = absolute_uplift / math.sqrt(variance_term)
        numerator = variance_term**2
        denominator = 0.0
        if control_count > 1:
            denominator += ((control_variance / control_count) ** 2) / (control_count - 1)
        if treatment_count > 1:
            denominator += ((treatment_variance / treatment_count) ** 2) / (treatment_count - 1)
        degrees_of_freedom = numerator / denominator if denominator else float(control_count + treatment_count - 2)
        p_value = max(0.0, min(1.0, 2.0 * (1.0 - student_t_cdf(abs(t_statistic), degrees_of_freedom))))

        critical_value = inverse_student_t_cdf(1.0 - (alpha / 2.0), degrees_of_freedom)
        margin = critical_value * math.sqrt(variance_term)
        confidence_interval = (absolute_uplift - margin, absolute_uplift + margin)

    return ExperimentStatistics(
        control_variant=control_variant,
        treatment_variant=treatment_variant,
        control_rate=control_mean,
        treatment_rate=treatment_mean,
        absolute_uplift=absolute_uplift,
        relative_uplift=relative_uplift,
        p_value=p_value,
        confidence_interval=confidence_interval,
        is_significant=p_value < alpha and confidence_interval[0] * confidence_interval[1] > 0,
        t_statistic=t_statistic,
        degrees_of_freedom=degrees_of_freedom,
        sample_sizes={control_variant: control_count, treatment_variant: treatment_count},
    )
