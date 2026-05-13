# Pygame - Car Fuel Rush

A small Pygame traffic-and-fuel simulator where you keep a fleet alive by dispatching cars and placing a limited number of fuel cans on the road.

The original project was developed through GPT-assisted iteration. The latest simulator, UI, and README improvements were made with Codex GPT-5.5.

## Overview

Cars travel between houses using A* pathfinding. Each car burns fuel while moving, can refill from fuel spots, completes deliveries, and can become stranded if it runs out of fuel. The goal is to keep the fleet productive by placing fuel wisely, dispatching cars, and monitoring the right-side control panel.

The grid world keeps the original simple visual style: white roads, grey grid lines, tree and house tiles, blue fuel circles, and yellow/red route overlays.

## Features

1. **Live fleet simulation:** Cars route between houses, consume fuel, refuel, complete deliveries, and can get stranded.
2. **A* routing:** Cars use A* to find paths through the map while avoiding blocked cells.
3. **Cached paths:** Repeated routes are cached for better performance as the fleet grows.
4. **Improved control panel:** Shows deliveries, fleet size, active cars, stranded cars, fuel stock, average fuel, selected-car details, and recent activity.
5. **Driver focus controls:** Select cars from the grid, use the panel arrows, or use keyboard arrows to switch between drivers. The selected car is highlighted on the map.
6. **Simulation controls:** Pause/run, add a car, launch a convoy, rescue stranded cars, reset, clear the fleet, place random fuel, and toggle auto-fuel.
7. **Paused map state:** When paused, the grid is dimmed and map interactions are blocked, while the panel remains usable.

## Controls

### Mouse

1. Left-click a road cell to place fuel while the simulation is running.
2. Right-click a fuel spot to reclaim it while the simulation is running.
3. Click a car on the grid to focus it in the panel.
4. Use the `<` and `>` buttons in the driver card to switch the selected car.

### Keyboard

1. `Space` toggles run/pause.
2. `A` adds one car.
3. `F` places random fuel.
4. `R` resets the simulation.
5. `C` clears the fleet.
6. `Left Arrow` and `Right Arrow` switch the selected car.

## Local Setup

1. Install dependencies:

   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. Run the simulator:

   ```bash
   python3 main/app.py
   ```

## Project Structure

```text
main/
  app.py        Main Pygame application and simulation loop
  astar.py      A* pathfinding implementation
  models.py     Simulation data models
  settings.py   Constants, colors, paths, and tuning values
  ui.py         Button, slider, and text rendering helpers
  utils.py      Shared math/color helpers
images/         Car, house, and tree sprites
maps/           Grid map data
```

## Notes

- The current app intentionally keeps the original grid-world art direction while modernizing the right-side UI and simulation behavior.
- The project is meant to stay small, readable, and easy to experiment with.
