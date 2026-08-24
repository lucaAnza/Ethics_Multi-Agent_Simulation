"""Centralized conversion between vehicle km/h and on-screen movement."""

# Change this value to adjust the speed of all vehicles in the simulation.
VEHICLE_PIXELS_PER_SECOND_PER_KMH = 3


def vehicle_kmh_to_pixels_per_second(speed_kmh: float) -> float:
    """Convert a car speed expressed in km/h to Arcade movement units."""
    return float(speed_kmh) * VEHICLE_PIXELS_PER_SECOND_PER_KMH
