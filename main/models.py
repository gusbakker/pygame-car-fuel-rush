from dataclasses import dataclass, field

try:
    from .utils import clamp, lerp
except ImportError:
    from utils import clamp, lerp


GridPos = tuple[int, int]
Color = tuple[int, int, int]


@dataclass
class Car:
    id: int
    color: Color
    fuel: float = 100.0
    max_fuel: float = 100.0
    origin: GridPos | None = None
    destination: GridPos | None = None
    path: list[GridPos] = field(default_factory=list)
    path_index: int = 0
    progress: float = 0.0
    state: str = "idle"
    route_wait: float = 0.0
    deliveries: int = 0
    distance_traveled: float = 0.0
    fuel_used: float = 0.0
    stranded_time: float = 0.0

    def interpolated_cell(self) -> tuple[float, float]:
        if not self.path:
            if self.origin:
                return float(self.origin[0]), float(self.origin[1])
            return 0.0, 0.0

        if self.path_index >= len(self.path) - 1:
            node = self.path[-1]
            return float(node[0]), float(node[1])

        start = self.path[self.path_index]
        end = self.path[self.path_index + 1]
        return (
            lerp(start[0], end[0], self.progress),
            lerp(start[1], end[1], self.progress),
        )

    def center_px(self, cell_size: int) -> tuple[int, int]:
        x, y = self.interpolated_cell()
        return int((x + 0.5) * cell_size), int((y + 0.5) * cell_size)

    def current_cell(self) -> GridPos | None:
        if not self.path:
            return self.origin
        index = min(self.path_index, len(self.path) - 1)
        return self.path[index]

    def route_name(self) -> str:
        if self.origin is None or self.destination is None:
            return "Waiting"
        return f"{self.origin} -> {self.destination}"

    def fuel_ratio(self) -> float:
        return clamp(self.fuel / self.max_fuel, 0.0, 1.0)
