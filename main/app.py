import random

import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UIHorizontalSlider
from astar import AStar
import os

# Constants
CELL_SIZE = 20
GRID_SIZE = 40
PANEL_WIDTH = 200
WIDTH = HEIGHT = CELL_SIZE * GRID_SIZE
SCREEN_WIDTH = GRID_SIZE * CELL_SIZE + PANEL_WIDTH
SCREEN_HEIGHT = GRID_SIZE * CELL_SIZE
FPS = 60
TREE = 1
HOUSE = 2
ROAD = 0

CAR_SPEED = 10  # Lower values will make the car move faster, higher values will make it move slower
NUM_CARS = 5  # Number of cars
FUEL_SPOT = 3

PANEL_COLOR = (200, 200, 200)
FONT_COLOR = (0, 0, 0)
FONT_SIZE = 22

# Colors
WHITE = (255, 255, 255)
GREEN = (0, 128, 0)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
YELLOW = (255, 255, 0, 100)
RED = (255, 0, 0, 100)

# Load images
car_image = pygame.image.load(os.path.join(os.path.dirname(__file__), "../images/car.png"))
car_image = pygame.transform.scale(car_image, (CELL_SIZE, CELL_SIZE))
house_image = pygame.image.load(os.path.join(os.path.dirname(__file__), "../images/house.png"))
house_image = pygame.transform.scale(house_image, (CELL_SIZE, CELL_SIZE))
tree_image = pygame.image.load(os.path.join(os.path.dirname(__file__), "../images/tree.png"))
tree_image = pygame.transform.scale(tree_image, (CELL_SIZE, CELL_SIZE))

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Cell Map")
clock = pygame.time.Clock()

# Initialize the GUI UIManager
ui_manager = pygame_gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT))
# Create the start/stop button
start_stop_button = UIButton(pygame.Rect(WIDTH + 20, 10, PANEL_WIDTH - 40, 40),
                             text="Start/Stop", manager=ui_manager)
# Create the slider
speed_slider = UIHorizontalSlider(pygame.Rect(WIDTH + 20, 50, PANEL_WIDTH - 40, 20),
                                  start_value=FPS, value_range=(10, 120), manager=ui_manager)
# Create the add car button
add_car_button = UIButton(pygame.Rect(WIDTH + 20, 70, PANEL_WIDTH - 40, 40),
                          text="Add Car", manager=ui_manager)

# Load map
with open("../maps/map.txt", "r") as file:
    map_data = [list(map(int, line.strip().split())) for line in file]

# A* pathfinding object
pathfinder = AStar(map_data, (0, 0), (GRID_SIZE - 1, GRID_SIZE - 1))


class Car:
    def __init__(self, position=None, target_house=None, origin=None, path=None, path_index=0, progress=0, fuel=100):
        self.position = position
        self.target_house = target_house
        self.origin = origin
        self.path = path
        self.path_index = path_index
        self.progress = progress
        self.fuel = fuel


def draw_grid():
    for x in range(0, WIDTH, CELL_SIZE):
        for y in range(0, HEIGHT, CELL_SIZE):
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, GRAY, rect, 1)


def draw_cells():
    for y, row in enumerate(map_data):
        for x, cell in enumerate(row):
            if cell == TREE:
                screen.blit(tree_image, (x * CELL_SIZE, y * CELL_SIZE))
            elif cell == HOUSE:
                screen.blit(house_image, (x * CELL_SIZE, y * CELL_SIZE))
            elif cell == ROAD:
                pygame.draw.rect(screen, WHITE, (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))
            elif cell == FUEL_SPOT:  # Draw fuel spots
                pygame.draw.circle(screen, (0, 0, 255),
                                   (x * CELL_SIZE + CELL_SIZE // 2, y * CELL_SIZE + CELL_SIZE // 2), CELL_SIZE // 2)


def draw_path(car, path):
    if path is not None:
        for i, node in enumerate(path):
            if i > car.path_index:  # Draw only the upcoming path
                x, y = node
                if map_data[y][x] != HOUSE:  # Exclude house cells
                    path_color = pygame.Color(*(YELLOW if car.fuel > 0 else RED))
                    path_rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    # Create surface with alpha channel
                    path_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                    path_surface.fill(path_color)  # Fill the surface with the semi-transparent color
                    screen.blit(path_surface, path_rect)  # Draw the surface on the screen


def draw_panel(cars, houses, fps, fuel_spots):
    panel_rect = pygame.Rect(SCREEN_WIDTH, 0, PANEL_WIDTH, SCREEN_HEIGHT)
    pygame.draw.rect(screen, PANEL_COLOR, panel_rect)

    font = pygame.font.Font(None, FONT_SIZE)
    general_text = f"Number of Cars: {len(cars)}\nNumber of Houses: {len(houses)}\nFPS: {fps}\nFuel Spots: {fuel_spots}"
    car_text = ""

    for i, car in enumerate(cars):
        if car.position and car.target_house:
            car_info = f"Car {i + 1}:\nOrigin: {car.origin}\nDestination: {car.target_house}\nFuel: {car.fuel}\n\n"
            car_text += car_info

    text = general_text + "\n\n" + car_text
    text_lines = text.splitlines()
    for i, line in enumerate(text_lines):
        text_surface = font.render(line, True, FONT_COLOR)
        screen.blit(text_surface, (WIDTH + 10, 120 + i * FONT_SIZE))


def main():
    global FPS
    running = True
    game_paused = False
    cars = []
    fuel_spots = 5  # Initialize the user's fuel spots

    while running:
        time_delta = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Handle mouse click events to add fuel spots
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    x, y = event.pos
                    if x < WIDTH:  # Make sure we're clicking on the grid
                        grid_x, grid_y = x // CELL_SIZE, y // CELL_SIZE
                        if map_data[grid_y][grid_x] == ROAD and fuel_spots > 0:
                            map_data[grid_y][grid_x] = FUEL_SPOT
                            fuel_spots -= 1

            # Handle UI events
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == start_stop_button:
                        game_paused = not game_paused
                        start_stop_button.set_text("Start" if game_paused else "Stop")
                    elif event.ui_element == add_car_button:
                        cars.append(Car())
                elif event.user_type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                    if event.ui_element == speed_slider:
                        FPS = event.value

            # Update the UIManager
            ui_manager.process_events(event)

        # Update the UIManager
        ui_manager.update(time_delta)

        screen.fill(WHITE)
        draw_cells()

        houses = [(x, y) for y, row in enumerate(map_data) for x, cell in enumerate(row) if cell == HOUSE]

        for car in cars:
            if car.position is not None:
                # Draw the path for the current car
                draw_path(car, car.path)
                screen.blit(car_image, car.position)

        if not game_paused:
            for car in cars:
                if car.position is None or car.target_house is None:
                    if not houses:
                        continue

                    car.position = random.choice(houses)
                    car.origin = car.position  # Set the origin attribute
                    car.target_house = random.choice([house for house in houses if house != car.position])

                    pathfinder = AStar(map_data, car.position, car.target_house)
                    car.path = pathfinder.find_path()
                    car.path_index = 0
                    car.progress = 0

                if car.path and car.path_index < len(car.path) - 1:
                    draw_path(car, car.path)  # Move the draw_path call outside the fuel check
                    if car.fuel > 0:  # Update the car's position only if it has enough fuel
                        current_node = car.path[car.path_index]
                        next_node = car.path[car.path_index + 1]
                        car.position = (
                            current_node[0] * CELL_SIZE + (
                                    next_node[0] - current_node[0]) * CELL_SIZE * car.progress / CAR_SPEED,
                            current_node[1] * CELL_SIZE + (
                                    next_node[1] - current_node[1]) * CELL_SIZE * car.progress / CAR_SPEED
                        )
                        screen.blit(car_image, car.position)
                        car.progress += 1
                        car.fuel -= 0.2  # Deduct a small amount of fuel after updating the car's position

                    if car.progress >= CAR_SPEED:
                        car.progress = 0
                        car.path_index += 1

                        # Refill the car's fuel if it passes through a fuel spot
                        current_node = car.path[car.path_index]
                        if map_data[current_node[1]][current_node[0]] == FUEL_SPOT:
                            car.fuel += 50
                            # Remove the fuel spot from the grid
                            map_data[current_node[1]][current_node[0]] = ROAD

                        # If the car reaches its destination, stop the car and add a fuel spot
                        if car.path_index == len(car.path) - 1:
                            car.position = None
                            car.target_house = None
                            fuel_spots += 1

                    if car.path_index == len(car.path) - 1:
                        car.position = None
                        car.target_house = None
                else:
                    car.position = None
                    car.target_house = None

        draw_grid()
        draw_panel(cars, houses, FPS, fuel_spots)

        # Draw the UIManager
        ui_manager.draw_ui(screen)

        pygame.display.flip()

        # Pause the game if the game_paused is True
        if game_paused:
            clock.tick(FPS)
            continue

        clock.tick(FPS)


if __name__ == "__main__":
    main()
