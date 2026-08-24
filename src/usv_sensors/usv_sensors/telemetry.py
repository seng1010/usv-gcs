"""Validation helpers for sensor telemetry received through the Bridge.

Ported from gps_and_water_quality_and_ros (ros_led/telemetry.py).
"""

import math


def bounded_integer(value, minimum, maximum, default=0):
    """Convert a value to an integer and clamp it to the requested range."""
    try:
        if value is None or isinstance(value, bool):
            return default
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError, OverflowError):
        return default


def valid_coordinates(latitude, longitude):
    """Return whether latitude and longitude form a finite Earth coordinate."""
    if isinstance(latitude, bool) or isinstance(longitude, bool):
        return False
    if not isinstance(latitude, (int, float)):
        return False
    if not isinstance(longitude, (int, float)):
        return False
    return (
        math.isfinite(float(latitude))
        and math.isfinite(float(longitude))
        and -90.0 <= float(latitude) <= 90.0
        and -180.0 <= float(longitude) <= 180.0
    )
