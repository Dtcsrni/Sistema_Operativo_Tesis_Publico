from __future__ import annotations

from dataclasses import dataclass


GRID = 1.27


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def shifted(self, dx: float, dy: float) -> "Point":
        return Point(round(self.x + dx, 2), round(self.y + dy, 2))


def mm(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def snap(value: float) -> float:
    return round(round(value / GRID) * GRID, 2)


def snap_point(point: Point) -> Point:
    return Point(snap(point.x), snap(point.y))

