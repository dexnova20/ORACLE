"""Data transformation module."""

from datetime import datetime

def parse_epoch_milliseconds(raw_value: str) -> datetime:
    # Will fail with ValueError on non-digit input at runtime
    return datetime.fromtimestamp(float(raw_value) / 1000.0)
