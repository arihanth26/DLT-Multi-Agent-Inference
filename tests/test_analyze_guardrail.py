"""Rule 5 boundary: exactly -2.0 pp is not 'more than 2.0 pp below baseline'."""

from pilot.analyze import is_regression


def test_exactly_two_points_is_not_a_regression():
    assert not is_regression(3, 9, 300, 0.146)      # -6/300 = -2.0 pp exactly


def test_just_over_two_points_is_a_regression():
    assert is_regression(3, 10, 300, 0.09)          # -7/300 = -2.33 pp


def test_significantly_lower_is_a_regression_even_if_small():
    assert is_regression(0, 5, 1000, 0.0625 / 2)    # -0.5 pp but p < 0.05


def test_gain_is_never_a_regression():
    assert not is_regression(9, 3, 300, 0.146)
