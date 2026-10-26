"""Core engine implementation."""
from dataclasses import dataclass
from typing import List

@dataclass
class Engine:
    name: str
    capacity: int

    def process(self, batch: List[int]) -> int:
        return sum(batch) * self.capacity
