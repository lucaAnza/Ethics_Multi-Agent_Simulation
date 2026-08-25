"""Shared simulation geometry and default values.

Values that affect both the interactive and headless simulation belong here so
that changing the model never requires synchronizing multiple modules.
"""

# Window and map layout
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
TOP_TOOLBAR_HEIGHT = 72
ROAD_HALF_HEIGHT = 90.0
LANE_OFFSET = 45.0
LANE_HALF_WIDTH = 30.0
TUNNEL_MARGIN = 105.0

# Entity geometry and movement
CAR_HALF_LENGTH = 38.0
CAR_HALF_WIDTH = 20.0
LANE_CHANGE_DURATION = 0.10
DEFAULT_CAR_START_X = 130.0
# Saved scenario values override this fallback for their individual vehicles.
DEFAULT_VEHICLE_SPEED_KMH = 50.0
MAX_CONFIGURABLE_VEHICLE_SPEED_KMH = 200.0
DEFAULT_PEDESTRIAN_SPEED = 55.0

# Vehicle perception and decisions
DEFAULT_VISION_DISTANCE = 300.0
DEFAULT_DECISION_DISTANCE = 120.0
DEFAULT_MAX_LANE_CHANGES = 2
MIN_VISION_DISTANCE = 50.0
MIN_DECISION_DISTANCE = 10.0

# Conversion between public vehicle km/h and on-screen distance.
VEHICLE_PIXELS_PER_SECOND_PER_KMH = 3
