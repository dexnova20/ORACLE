"""Downstream component importing upstream module."""
from .upstream import calculate_tax

def process_order(price: float) -> float:
    """Processes order total using upstream tax calculation."""
    return calculate_tax(price)

def get_fallback_discount(rate: float) -> float:
    """Independent pure calculation that does not invoke upstream."""
    return 100.0 * (1.0 - rate)
