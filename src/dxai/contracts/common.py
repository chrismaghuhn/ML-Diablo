from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True, order=True)
class Vec2:
    x: int
    y: int

    def manhattan(self, other: Vec2) -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Vec2:
        return cls(x=int(value["x"]), y=int(value["y"]))
