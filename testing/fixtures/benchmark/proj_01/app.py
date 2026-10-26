"""Clean healthy module for control testing."""

import math
import sys

def compute_square_root(value: float) -> float:
    """Return square root of a positive number."""
    if value < 0:
        raise ValueError("Value must be non-negative")
    return math.sqrt(value)

def format_python_version() -> str:
    """Return running python version string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"
