"""Module with an intentional syntax defect."""

def calculate_total(items: list[float]) -> float:
    total = 0.0
    for item in items:
        total += item(
    return total
