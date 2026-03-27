from __future__ import annotations

import pytest

from ab_testing_platform.statistics import inverse_student_t_cdf, student_t_cdf, welch_t_test


def test_student_t_cdf_and_inverse_align() -> None:
    quantile = inverse_student_t_cdf(0.975, 40)
    assert student_t_cdf(quantile, 40) == pytest.approx(0.975, abs=1e-4)


def test_welch_t_test_detects_positive_lift() -> None:
    control = [0.0] * 80 + [1.0] * 20
    treatment = [0.0] * 60 + [1.0] * 40

    result = welch_t_test(control, treatment, control_variant="control", treatment_variant="variant")

    assert result.absolute_uplift > 0.0
    assert result.p_value < 0.05
    assert result.is_significant is True
