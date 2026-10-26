"""Downstream component that imports upstream AND has its own syntax error."""
from .upstream import get_base_rate

def compute_total(base: float) -> float:
    # Injected syntax defect in downstream component itself: invalid token syntax
    return base * % 10.0
