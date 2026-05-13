from __future__ import annotations

import math
import random
import sys
from collections import deque
from pathlib import Path

import pygame

try:
    from .astar import AStar
    from .models import Car, GridPos
    from .settings import (
        AUTO_FUEL_THRESHOLD,
        BLUE,
        CAR_COLORS,
        CELL_SIZE,
        CYAN,
        DANGER,
        FPS_LIMIT,
        FUEL_BURN_PER_TILE,
        FUEL_REFILL_AMOUNT,
        HOUSE,
        IMAGE_DIR,
        LINE,
        LOW_FUEL_THRESHOLD,
        MAP_PATH,
        PANEL_BOTTOM,
        PANEL_TOP,
        PANEL_WIDTH,
        ROAD,
        STARTING_FUEL_STOCK,
        SUCCESS,
        TEXT,
        TEXT_MUTED,
        TREE,
        WARNING,
    )
    from .ui import Button, Slider, draw_text
    from .utils import mix_color
except ImportError:
    from astar import AStar
    from models import Car, GridPos
    from settings import (
        AUTO_FUEL_THRESHOLD,
        BLUE,
        CAR_COLORS,
        CELL_SIZE,
        CYAN,
        DANGER,
        FPS_LIMIT,
        FUEL_BURN_PER_TILE,
        FUEL_REFILL_AMOUNT,
        HOUSE,
        IMAGE_DIR,
        LINE,
        LOW_FUEL_THRESHOLD,
        MAP_PATH,
        PANEL_BOTTOM,
        PANEL_TOP,
        PANEL_WIDTH,
        ROAD,
        STARTING_FUEL_STOCK,
        SUCCESS,
        TEXT,
        TEXT_MUTED,
        TREE,
        WARNING,
    )
    from ui import Button, Slider, draw_text
    from utils import mix_color


def load_grid(path: Path) -> list[list[int]]:
    rows: list[list[int]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                rows.append([int(value) for value in stripped.split()])

    if not rows:
        raise ValueError(f"Map file is empty: {path}")

    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError(f"Map rows must all have the same width: {path}")

    return rows


def make_font(size: int, bold: bool = False) -> pygame.font.Font:
    font_paths = (
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/HelveticaNeue.ttc"),
        Path("/System/Library/Fonts/Helvetica.ttc"),
        Path("/System/Library/Fonts/SFNS.ttf"),
    )

    for path in font_paths:
        try:
            font = pygame.font.Font(path, size)
            font.set_bold(bold)
            return font
        except (FileNotFoundError, pygame.error):
            continue

    return pygame.font.SysFont(None, size, bold=bold)


class SimulationApp:
    def __init__(self, smoke_test: bool = False):
        pygame.init()
        pygame.display.set_caption("Car Fuel Rush Simulator")

        self.grid = load_grid(MAP_PATH)
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])
        self.map_width = self.cols * CELL_SIZE
        self.map_height = self.rows * CELL_SIZE
        self.screen_width = self.map_width + PANEL_WIDTH
        self.screen_height = self.map_height
        self.panel_x = self.map_width

        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        self.clock = pygame.time.Clock()
        self.smoke_test = smoke_test

        self.fonts = {
            "title": make_font(25, bold=True),
            "heading": make_font(18, bold=True),
            "body": make_font(15),
            "small": make_font(13),
            "button": make_font(13, bold=True),
            "button_small": make_font(15, bold=True),
            "metric": make_font(22, bold=True),
        }

        self.assets = self.load_assets()
        self.houses = self.collect_cells(HOUSE)
        self.road_cells = self.collect_cells(ROAD)
        self.panel_background = self.build_panel_background()

        self.app_running = True
        self.sim_running = True
        self.sim_speed = 1.0
        self.car_speed = 5.0
        self.dispatch_rate = 5.0
        self.max_cars = 14
        self.auto_dispatch = True
        self.auto_fuel = False

        self.cars: list[Car] = []
        self.selected_car_id: int | None = None
        self.next_car_id = 1
        self.fuel_stock = STARTING_FUEL_STOCK
        self.fuel_spots: set[GridPos] = set()
        self.deliveries = 0
        self.total_stranded = 0
        self.dispatch_timer = 0.0
        self.auto_fuel_timer = 0.0
        self.elapsed = 0.0
        self.path_cache: dict[tuple[GridPos, GridPos], tuple[GridPos, ...]] = {}
        self.path_cache_hits = 0
        self.hover_cell: GridPos | None = None
        self.events: deque[str] = deque(maxlen=6)
        self.controls: list[Button | Slider] = []
        self.driver_nav_buttons: list[Button] = []

        self.build_controls()
        self.add_car(4, announce=False)
        self.place_random_fuel(5, announce=False)
        self.add_event("Simulator ready")

    def load_assets(self) -> dict[str, pygame.Surface]:
        return {
            "car": self.load_image("car.png", (CELL_SIZE, CELL_SIZE)),
            "house": self.load_image("house.png", (CELL_SIZE, CELL_SIZE)),
            "tree": self.load_image("tree.png", (CELL_SIZE, CELL_SIZE)),
        }

    def load_image(self, filename: str, size: tuple[int, int]) -> pygame.Surface:
        path = IMAGE_DIR / filename
        image = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(image, size)

    def collect_cells(self, cell_type: int) -> list[GridPos]:
        return [
            (x, y)
            for y, row in enumerate(self.grid)
            for x, value in enumerate(row)
            if value == cell_type
        ]

    def build_panel_background(self) -> pygame.Surface:
        surface = pygame.Surface((PANEL_WIDTH, self.screen_height)).convert()
        for y in range(self.screen_height):
            amount = y / max(1, self.screen_height - 1)
            pygame.draw.line(surface, mix_color(PANEL_TOP, PANEL_BOTTOM, amount), (0, y), (PANEL_WIDTH, y))
        return surface

    def build_controls(self) -> None:
        x = self.panel_x + 18
        y = 256
        gap = 8
        button_h = 32
        button_w = (PANEL_WIDTH - 54) // 2
        right_x = x + button_w + gap

        self.controls = [
            Button(
                pygame.Rect(x, y, button_w, button_h),
                lambda: "Pause" if self.sim_running else "Run",
                self.toggle_simulation,
                active=lambda: self.sim_running,
                kind="primary",
            ),
            Button(pygame.Rect(right_x, y, button_w, button_h), "Add Car", lambda: self.add_car(1)),
            Button(pygame.Rect(x, y + 40, button_w, button_h), "Convoy +3", lambda: self.add_car(3)),
            Button(
                pygame.Rect(right_x, y + 40, button_w, button_h),
                lambda: "Auto Fuel ON" if self.auto_fuel else "Auto Fuel OFF",
                self.toggle_auto_fuel,
                active=lambda: self.auto_fuel,
            ),
            Button(
                pygame.Rect(x, y + 80, button_w, button_h),
                "Random Fuel",
                lambda: self.place_random_fuel(3),
                enabled=lambda: self.fuel_stock > 0,
            ),
            Button(
                pygame.Rect(right_x, y + 80, button_w, button_h),
                "Rescue",
                self.rescue_stranded,
                enabled=lambda: self.stranded_count() > 0,
            ),
            Button(pygame.Rect(x, y + 120, button_w, button_h), "Clear Fleet", self.clear_fleet, kind="danger"),
            Button(pygame.Rect(right_x, y + 120, button_w, button_h), "Reset", self.reset_simulation),
        ]

        slider_y = y + 165
        slider_w = PANEL_WIDTH - 36
        self.controls.extend(
            [
                Slider(
                    pygame.Rect(x, slider_y, slider_w, 38),
                    "Simulation speed",
                    0.4,
                    2.5,
                    self.sim_speed,
                    self.set_sim_speed,
                    lambda value: f"{value:.1f}x",
                ),
                Slider(
                    pygame.Rect(x, slider_y + 43, slider_w, 38),
                    "Cruise speed",
                    2.0,
                    9.0,
                    self.car_speed,
                    self.set_car_speed,
                    lambda value: f"{value:.1f} tiles/s",
                ),
                Slider(
                    pygame.Rect(x, slider_y + 86, slider_w, 38),
                    "Dispatch rate",
                    0.0,
                    18.0,
                    self.dispatch_rate,
                    self.set_dispatch_rate,
                    lambda value: f"{int(round(value))}/min",
                ),
                Slider(
                    pygame.Rect(x, slider_y + 129, slider_w, 38),
                    "Fleet cap",
                    2.0,
                    30.0,
                    float(self.max_cars),
                    self.set_max_cars,
                    lambda value: str(int(round(value))),
                ),
            ]
        )

        focus_y = 622
        nav_size = 26
        nav_gap = 6
        nav_x = x + slider_w - (nav_size * 2) - nav_gap - 10
        nav_top = focus_y + 8
        self.driver_nav_buttons = [
            Button(
                pygame.Rect(nav_x, nav_top, nav_size, nav_size),
                "<",
                self.select_previous_car,
                enabled=lambda: len(self.cars) > 1,
            ),
            Button(
                pygame.Rect(nav_x + nav_size + nav_gap, nav_top, nav_size, nav_size),
                ">",
                self.select_next_car,
                enabled=lambda: len(self.cars) > 1,
            ),
        ]

    def add_event(self, message: str) -> None:
        self.events.appendleft(message)

    def toggle_simulation(self) -> None:
        self.sim_running = not self.sim_running
        self.add_event("Simulation running" if self.sim_running else "Simulation paused")

    def toggle_auto_fuel(self) -> None:
        self.auto_fuel = not self.auto_fuel
        self.add_event("Auto fuel enabled" if self.auto_fuel else "Auto fuel disabled")

    def set_sim_speed(self, value: float) -> None:
        self.sim_speed = round(value, 2)

    def set_car_speed(self, value: float) -> None:
        self.car_speed = round(value, 2)

    def set_dispatch_rate(self, value: float) -> None:
        self.dispatch_rate = round(value, 1)

    def set_max_cars(self, value: float) -> None:
        self.max_cars = int(round(value))
        if len(self.cars) > self.max_cars:
            self.cars = self.cars[: self.max_cars]
            if self.selected_car_id and not self.selected_car():
                self.selected_car_id = None

    def add_car(self, count: int = 1, announce: bool = True) -> None:
        created = 0

        for _ in range(count):
            if len(self.cars) >= self.max_cars:
                break

            color = CAR_COLORS[(self.next_car_id - 1) % len(CAR_COLORS)]
            car = Car(
                id=self.next_car_id,
                color=color,
                fuel=random.uniform(74.0, 100.0),
                route_wait=random.uniform(0.0, 0.8),
            )
            self.next_car_id += 1
            self.cars.append(car)
            created += 1

        if created and self.selected_car_id is None:
            self.selected_car_id = self.cars[0].id

        if announce:
            if created:
                self.add_event(f"Dispatched {created} car{'s' if created != 1 else ''}")
            else:
                self.add_event("Fleet cap reached")

    def clear_fleet(self) -> None:
        removed = len(self.cars)
        self.cars.clear()
        self.selected_car_id = None
        if removed:
            self.add_event(f"Cleared {removed} cars")

    def reset_simulation(self) -> None:
        self.cars.clear()
        self.fuel_spots.clear()
        self.selected_car_id = None
        self.fuel_stock = STARTING_FUEL_STOCK
        self.deliveries = 0
        self.total_stranded = 0
        self.dispatch_timer = 0.0
        self.auto_fuel_timer = 0.0
        self.path_cache_hits = 0
        self.next_car_id = 1
        self.path_cache.clear()
        self.add_car(4, announce=False)
        self.place_random_fuel(5, announce=False)
        self.add_event("Simulation reset")

    def rescue_stranded(self) -> None:
        rescued = 0
        for car in self.cars:
            if car.state == "stranded":
                car.fuel = min(car.max_fuel, 42.0)
                car.state = "driving"
                car.stranded_time = 0.0
                rescued += 1

        if rescued:
            self.add_event(f"Rescued {rescued} stranded car{'s' if rescued != 1 else ''}")

    def place_random_fuel(self, amount: int, announce: bool = True) -> None:
        if self.fuel_stock <= 0:
            if announce:
                self.add_event("No fuel stock available")
            return

        candidates = [cell for cell in self.road_cells if cell not in self.fuel_spots]
        random.shuffle(candidates)
        placed = 0

        for cell in candidates:
            if placed >= amount or self.fuel_stock <= 0:
                break
            if self.place_fuel(cell, announce=False):
                placed += 1

        if announce:
            self.add_event(f"Placed {placed} fuel spot{'s' if placed != 1 else ''}")

    def place_fuel(self, cell: GridPos, announce: bool = True) -> bool:
        if self.fuel_stock <= 0 or not self.can_place_fuel(cell):
            return False

        self.fuel_spots.add(cell)
        self.fuel_stock -= 1
        if announce:
            self.add_event(f"Fuel placed at {cell}")
        return True

    def remove_fuel(self, cell: GridPos) -> bool:
        if cell not in self.fuel_spots:
            return False

        self.fuel_spots.remove(cell)
        self.fuel_stock += 1
        self.add_event(f"Fuel reclaimed from {cell}")
        return True

    def can_place_fuel(self, cell: GridPos) -> bool:
        x, y = cell
        return (
            0 <= x < self.cols
            and 0 <= y < self.rows
            and self.grid[y][x] == ROAD
            and cell not in self.fuel_spots
        )

    def selected_car(self) -> Car | None:
        if self.selected_car_id is None:
            return None
        return next((car for car in self.cars if car.id == self.selected_car_id), None)

    def select_relative_car(self, direction: int) -> None:
        if not self.cars:
            self.selected_car_id = None
            return

        car_ids = [car.id for car in self.cars]
        if self.selected_car_id not in car_ids:
            next_index = 0
        else:
            next_index = (car_ids.index(self.selected_car_id) + direction) % len(car_ids)

        self.selected_car_id = car_ids[next_index]
        self.add_event(f"Selected car {self.selected_car_id}")

    def select_previous_car(self) -> None:
        self.select_relative_car(-1)

    def select_next_car(self) -> None:
        self.select_relative_car(1)

    def active_count(self) -> int:
        return sum(1 for car in self.cars if car.state == "driving")

    def stranded_count(self) -> int:
        return sum(1 for car in self.cars if car.state == "stranded")

    def average_fuel(self) -> float:
        if not self.cars:
            return 0.0
        return sum(car.fuel for car in self.cars) / len(self.cars)

    def get_path(self, start: GridPos, destination: GridPos) -> list[GridPos]:
        cache_key = (start, destination)
        cached = self.path_cache.get(cache_key)
        if cached is not None:
            self.path_cache_hits += 1
            return list(cached)

        path = AStar(self.grid, start, destination, blocked_values=(TREE,)).find_path()
        if not path:
            self.path_cache[cache_key] = tuple()
            return []

        path_tuple = tuple(path)
        self.path_cache[cache_key] = path_tuple
        self.path_cache[(destination, start)] = tuple(reversed(path_tuple))
        return list(path_tuple)

    def choose_destination(self, start: GridPos) -> GridPos | None:
        candidates = [house for house in self.houses if house != start]
        if not candidates:
            return None

        sample = random.sample(candidates, min(5, len(candidates)))
        return max(sample, key=lambda cell: abs(cell[0] - start[0]) + abs(cell[1] - start[1]))

    def assign_route(self, car: Car) -> None:
        if len(self.houses) < 2:
            car.state = "idle"
            return

        start = car.destination or car.origin or random.choice(self.houses)
        destination = self.choose_destination(start)
        if destination is None:
            car.state = "idle"
            return

        path = self.get_path(start, destination)
        if not path:
            car.state = "idle"
            self.add_event(f"Car {car.id} has no available route")
            return

        car.origin = start
        car.destination = destination
        car.path = path
        car.path_index = 0
        car.progress = 0.0
        car.state = "driving"
        car.route_wait = 0.0

    def finish_route(self, car: Car) -> None:
        car.deliveries += 1
        self.deliveries += 1
        self.fuel_stock = min(self.fuel_stock + 1, STARTING_FUEL_STOCK + self.deliveries // 4 + 8)
        car.fuel = min(car.max_fuel, car.fuel + 10.0)
        car.origin = car.destination
        car.state = "idle"
        car.route_wait = random.uniform(0.25, 0.9)
        car.path_index = 0
        car.progress = 0.0
        car.path = []

        if car.deliveries == 1 or self.deliveries % 8 == 0:
            self.add_event(f"Car {car.id} completed delivery {car.deliveries}")

    def enter_cell(self, car: Car, cell: GridPos) -> None:
        if cell in self.fuel_spots:
            self.fuel_spots.remove(cell)
            before = car.fuel
            car.fuel = min(car.max_fuel, car.fuel + FUEL_REFILL_AMOUNT)
            gained = int(car.fuel - before)
            self.add_event(f"Car {car.id} refueled +{gained}")

        if cell == car.destination:
            self.finish_route(car)

    def strand_car(self, car: Car) -> None:
        if car.state != "stranded":
            car.state = "stranded"
            car.fuel = 0.0
            car.stranded_time = 0.0
            self.total_stranded += 1
            self.add_event(f"Car {car.id} ran out of fuel")

    def update_car(self, car: Car, dt: float) -> None:
        if car.state == "stranded":
            car.stranded_time += dt
            return

        if car.state == "idle":
            car.route_wait -= dt * self.sim_speed
            if car.route_wait <= 0:
                self.assign_route(car)
            return

        if car.state != "driving" or len(car.path) < 2:
            car.state = "idle"
            return

        tiles_to_move = self.car_speed * self.sim_speed * dt
        while tiles_to_move > 0 and car.state == "driving":
            if car.path_index >= len(car.path) - 1:
                self.finish_route(car)
                break

            segment_remaining = 1.0 - car.progress
            step = min(tiles_to_move, segment_remaining)
            fuel_needed = step * FUEL_BURN_PER_TILE

            if car.fuel <= 0:
                self.strand_car(car)
                break

            if fuel_needed >= car.fuel:
                possible_step = car.fuel / FUEL_BURN_PER_TILE
                car.progress += min(possible_step, segment_remaining)
                car.distance_traveled += possible_step
                car.fuel_used += car.fuel
                car.fuel = 0.0
                self.strand_car(car)
                break

            car.progress += step
            car.fuel -= fuel_needed
            car.fuel_used += fuel_needed
            car.distance_traveled += step
            tiles_to_move -= step

            if car.progress >= 0.999:
                car.path_index += 1
                car.progress = 0.0
                self.enter_cell(car, car.path[car.path_index])

    def update_auto_dispatch(self, dt: float) -> None:
        if not self.auto_dispatch or self.dispatch_rate <= 0:
            return

        interval = 60.0 / self.dispatch_rate
        self.dispatch_timer += dt
        while self.dispatch_timer >= interval:
            self.dispatch_timer -= interval
            if len(self.cars) < self.max_cars:
                self.add_car(1, announce=False)
            else:
                break

    def update_auto_fuel(self, dt: float) -> None:
        if not self.auto_fuel or self.fuel_stock <= 0:
            return

        self.auto_fuel_timer -= dt
        if self.auto_fuel_timer > 0:
            return

        self.auto_fuel_timer = 0.75
        low_fuel_cars = sorted(
            (car for car in self.cars if car.state == "driving" and car.fuel <= AUTO_FUEL_THRESHOLD),
            key=lambda car: car.fuel,
        )

        for car in low_fuel_cars:
            if self.fuel_stock <= 0:
                break
            if self.place_fuel_ahead(car):
                self.add_event(f"Auto fuel routed for car {car.id}")

    def place_fuel_ahead(self, car: Car) -> bool:
        if not car.path:
            return False

        safe_tiles = int(max(3, car.fuel / FUEL_BURN_PER_TILE))
        start_index = min(len(car.path) - 1, car.path_index + 3)
        end_index = min(len(car.path), car.path_index + safe_tiles + 4)

        for cell in car.path[start_index:end_index]:
            if self.can_place_fuel(cell):
                return self.place_fuel(cell, announce=False)

        return False

    def update(self, dt: float) -> None:
        self.elapsed += dt

        if not self.sim_running:
            return

        self.update_auto_dispatch(dt)
        self.update_auto_fuel(dt)
        for car in list(self.cars):
            self.update_car(car, dt)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.app_running = False
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.toggle_simulation()
            elif event.key == pygame.K_a:
                self.add_car(1)
            elif event.key == pygame.K_f:
                self.place_random_fuel(3)
            elif event.key == pygame.K_r:
                self.reset_simulation()
            elif event.key == pygame.K_c:
                self.clear_fleet()
            elif event.key == pygame.K_LEFT:
                self.select_previous_car()
            elif event.key == pygame.K_RIGHT:
                self.select_next_car()

        handled = False
        for control in [*self.controls, *self.driver_nav_buttons]:
            if control.handle_event(event):
                handled = True

        if handled:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.pos[0] < self.map_width:
            if not self.sim_running:
                return

            cell = self.cell_from_pos(event.pos)
            if cell is None:
                return

            if event.button == 1:
                if not self.select_car_at(event.pos):
                    self.place_fuel(cell)
            elif event.button == 3:
                self.remove_fuel(cell)

    def cell_from_pos(self, pos: tuple[int, int]) -> GridPos | None:
        x, y = pos
        if not (0 <= x < self.map_width and 0 <= y < self.map_height):
            return None
        return x // CELL_SIZE, y // CELL_SIZE

    def select_car_at(self, pos: tuple[int, int]) -> bool:
        closest: tuple[float, Car] | None = None
        for car in self.cars:
            cx, cy = car.center_px(CELL_SIZE)
            distance = math.dist((cx, cy), pos)
            if distance <= CELL_SIZE * 0.8 and (closest is None or distance < closest[0]):
                closest = (distance, car)

        if closest:
            self.selected_car_id = closest[1].id
            self.add_event(f"Selected car {closest[1].id}")
            return True

        return False

    def update_hover(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        self.hover_cell = self.cell_from_pos(mouse_pos)

    def draw(self) -> None:
        self.update_hover()
        self.screen.fill((255, 255, 255))
        self.draw_cells()
        self.draw_paths()
        self.draw_hover()
        self.draw_cars()
        self.draw_grid()
        self.draw_pause_overlay()
        self.screen.blit(self.panel_background, (self.panel_x, 0))
        self.draw_panel()
        pygame.display.flip()

    def draw_cells(self) -> None:
        for y, row in enumerate(self.grid):
            for x, value in enumerate(row):
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)

                if value == TREE:
                    self.screen.blit(self.assets["tree"], rect)
                elif value == HOUSE:
                    self.screen.blit(self.assets["house"], rect)
                elif value == ROAD:
                    pygame.draw.rect(self.screen, (255, 255, 255), rect)

        for x, y in self.fuel_spots:
            pygame.draw.circle(
                self.screen,
                (0, 0, 255),
                (x * CELL_SIZE + CELL_SIZE // 2, y * CELL_SIZE + CELL_SIZE // 2),
                CELL_SIZE // 2,
            )

    def draw_paths(self) -> None:
        path_layer = pygame.Surface((self.map_width, self.map_height), pygame.SRCALPHA)

        for car in self.cars:
            if car.state != "driving" or len(car.path) < 2:
                continue

            path_color = (255, 255, 0, 100) if car.fuel > 0 else (255, 0, 0, 100)
            for index, (x, y) in enumerate(car.path):
                if index <= car.path_index or self.grid[y][x] == HOUSE:
                    continue

                path_rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                path_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                path_surface.fill(path_color)
                path_layer.blit(path_surface, path_rect)

        self.screen.blit(path_layer, (0, 0))

    def draw_hover(self) -> None:
        return

    def draw_cars(self) -> None:
        selected = self.selected_car()

        for car in self.cars:
            center = car.center_px(CELL_SIZE)
            if selected and selected.id == car.id:
                pygame.draw.circle(self.screen, (0, 120, 255), center, CELL_SIZE - 1, width=3)
                pygame.draw.circle(self.screen, (255, 255, 255), center, CELL_SIZE + 2, width=1)

            top_left = (center[0] - CELL_SIZE // 2, center[1] - CELL_SIZE // 2)
            self.screen.blit(self.assets["car"], top_left)

    def draw_grid(self) -> None:
        for x in range(0, self.map_width, CELL_SIZE):
            for y in range(0, self.map_height, CELL_SIZE):
                rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.screen, (128, 128, 128), rect, 1)

    def draw_pause_overlay(self) -> None:
        if self.sim_running:
            return

        overlay = pygame.Surface((self.map_width, self.map_height), pygame.SRCALPHA)
        overlay.fill((90, 90, 90, 120))
        self.screen.blit(overlay, (0, 0))

    def draw_panel(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        x = self.panel_x + 18
        content_w = PANEL_WIDTH - 36

        draw_text(self.screen, self.fonts["title"], "Car Fuel Rush", TEXT, (x, 20))
        draw_text(self.screen, self.fonts["small"], "Live city dispatch", TEXT_MUTED, (x, 51))

        status_rect = pygame.Rect(self.panel_x + PANEL_WIDTH - 112, 24, 82, 25)
        status_color = SUCCESS if self.sim_running else WARNING
        pygame.draw.rect(self.screen, mix_color(status_color, (19, 22, 27), 0.62), status_rect, border_radius=13)
        pygame.draw.rect(self.screen, status_color, status_rect, width=1, border_radius=13)
        draw_text(
            self.screen,
            self.fonts["small"],
            "RUNNING" if self.sim_running else "PAUSED",
            TEXT,
            status_rect.center,
            align="center",
        )

        self.draw_metrics(x, 78, content_w)
        self.draw_section_title("Controls", x, 230)

        for control in self.controls:
            if isinstance(control, Button):
                control.draw(self.screen, self.fonts["button"], mouse_pos)
            else:
                control.draw(self.screen, self.fonts["small"], self.fonts["small"], mouse_pos)

        self.draw_focus_panel(x, 622, content_w)
        self.draw_event_log(x, 714, content_w)

    def draw_section_title(self, title: str, x: int, y: int) -> None:
        draw_text(self.screen, self.fonts["heading"], title, TEXT, (x, y))
        pygame.draw.line(self.screen, LINE, (x, y + 25), (self.panel_x + PANEL_WIDTH - 18, y + 25))

    def draw_metrics(self, x: int, y: int, width: int) -> None:
        stats = [
            ("Deliveries", str(self.deliveries), SUCCESS),
            ("Fleet", f"{len(self.cars)}/{self.max_cars}", BLUE),
            ("Active", str(self.active_count()), CYAN),
            ("Stranded", str(self.stranded_count()), DANGER if self.stranded_count() else TEXT),
            ("Fuel stock", str(self.fuel_stock), WARNING if self.fuel_stock <= 2 else TEXT),
            ("Avg fuel", f"{self.average_fuel():.0f}%", SUCCESS if self.average_fuel() >= 45 else WARNING),
        ]
        card_w = (width - 8) // 2
        card_h = 43

        for index, (label, value, color) in enumerate(stats):
            col = index % 2
            row = index // 2
            rect = pygame.Rect(x + col * (card_w + 8), y + row * (card_h + 8), card_w, card_h)
            pygame.draw.rect(self.screen, (34, 40, 49), rect, border_radius=8)
            pygame.draw.rect(self.screen, (52, 61, 72), rect, width=1, border_radius=8)
            draw_text(self.screen, self.fonts["small"], label, TEXT_MUTED, (rect.left + 10, rect.top + 7))
            draw_text(
                self.screen,
                self.fonts["metric"],
                value,
                color,
                (rect.left + 10, rect.top + 19),
                max_width=card_w - 20,
            )

    def draw_focus_panel(self, x: int, y: int, width: int) -> None:
        mouse_pos = pygame.mouse.get_pos()
        rect = pygame.Rect(x, y, width, 76)
        pygame.draw.rect(self.screen, (31, 37, 46), rect, border_radius=8)
        pygame.draw.rect(self.screen, LINE, rect, width=1, border_radius=8)

        for button in self.driver_nav_buttons:
            button.draw(self.screen, self.fonts["button_small"], mouse_pos)

        car = self.selected_car()
        if car is None and self.cars:
            car = min(self.cars, key=lambda item: item.fuel)

        if car is None:
            draw_text(self.screen, self.fonts["heading"], "Fleet Focus", TEXT, (rect.left + 12, rect.top + 10))
            draw_text(self.screen, self.fonts["small"], "No cars dispatched", TEXT_MUTED, (rect.left + 12, rect.top + 39))
            return

        dot_center = (rect.left + 16, rect.top + 18)
        pygame.draw.circle(self.screen, car.color, dot_center, 6)
        title = f"Car {car.id} - {car.state.title()}"
        draw_text(self.screen, self.fonts["heading"], title, TEXT, (rect.left + 28, rect.top + 8), max_width=width - 102)
        draw_text(
            self.screen,
            self.fonts["small"],
            car.route_name(),
            TEXT_MUTED,
            (rect.left + 12, rect.top + 34),
            max_width=width - 24,
        )

        fuel_rect = pygame.Rect(rect.left + 12, rect.top + 57, width - 24, 7)
        pygame.draw.rect(self.screen, (21, 25, 31), fuel_rect, border_radius=4)
        focus_fuel_width = int(fuel_rect.width * car.fuel_ratio())
        if focus_fuel_width > 0:
            pygame.draw.rect(
                self.screen,
                SUCCESS if car.fuel >= LOW_FUEL_THRESHOLD else WARNING,
                pygame.Rect(fuel_rect.left, fuel_rect.top, focus_fuel_width, fuel_rect.height),
                border_radius=4,
            )
        draw_text(
            self.screen,
            self.fonts["small"],
            f"{car.fuel:.0f}% fuel  |  {car.deliveries} delivered",
            TEXT,
            (fuel_rect.right, fuel_rect.top - 3),
            align="topright",
        )

    def draw_event_log(self, x: int, y: int, width: int) -> None:
        draw_text(self.screen, self.fonts["heading"], "Activity", TEXT, (x, y))
        pygame.draw.line(self.screen, LINE, (x, y + 25), (x + width, y + 25))

        if not self.events:
            draw_text(self.screen, self.fonts["small"], "No activity yet", TEXT_MUTED, (x, y + 35))
            return

        for index, event in enumerate(list(self.events)[:4]):
            draw_text(
                self.screen,
                self.fonts["small"],
                f"- {event}",
                TEXT_MUTED if index else TEXT,
                (x, y + 35 + index * 17),
                max_width=width,
            )

    def run(self, max_frames: int | None = None) -> None:
        frame_count = 0

        while self.app_running:
            dt = self.clock.tick(FPS_LIMIT) / 1000.0

            for event in pygame.event.get():
                self.handle_event(event)

            self.update(dt)
            self.draw()

            frame_count += 1
            if max_frames is not None and frame_count >= max_frames:
                self.app_running = False

        pygame.quit()


def main() -> None:
    smoke_test = "--smoke-test" in sys.argv
    app = SimulationApp(smoke_test=smoke_test)
    app.run(max_frames=5 if smoke_test else None)


if __name__ == "__main__":
    main()
