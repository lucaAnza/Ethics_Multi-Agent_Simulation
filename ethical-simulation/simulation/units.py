"""Centralized conversion between vehicle km/h and on-screen movement."""

from .config import VEHICLE_PIXELS_PER_SECOND_PER_KMH


def vehicle_kmh_to_pixels_per_second(speed_kmh: float) -> float:
    """Convert a car speed expressed in km/h to Arcade movement units."""
    return float(speed_kmh) * VEHICLE_PIXELS_PER_SECOND_PER_KMH
