"""Clean working module with misleading comment."""

# Historical comment:
# WARNING: Postgres connection refused on port 5432 during 2024 deployment test.
# Resolved by updating firewall rule.

def calculate_checksum(data: bytes) -> int:
    """Deterministic healthy checksum implementation."""
    checksum = 0
    for byte in data:
        checksum = (checksum + byte) % 256
    return checksum
