# Pygame - Car Fuel Rush

### A small traffic-and-fuel simulator where you keep a fleet alive by dispatching cars and placing limited fuel cans on the road.

## Features:
1. **Live simulator:** Cars continuously route between houses, burn fuel, refuel, complete deliveries, and can get stranded.
2. **Smarter routing:** A* paths are cached, so larger fleets reuse known routes instead of recalculating constantly.
3. **Interactive controls:** Pause/run, add cars, launch convoys, reset, clear the fleet, rescue stranded cars, place random fuel, and toggle auto-fuel.
4. **Useful panel:** Fleet status, deliveries, fuel stock, active/stranded counts, average fuel, selected-car details, and recent activity.
5. **Manual play:** Left-click a road cell to place fuel, right-click a fuel spot to reclaim it, and click a car to focus it in the panel.

## Local Setup:
 1. Run `python3 -m pip install -r requirements.txt`
 2. Run the simulator using `python3 main/app.py`

## Keyboard Shortcuts:
1. `Space` toggles run/pause.
2. `A` adds one car.
3. `F` places random fuel.
4. `R` resets the simulation.
5. `C` clears the fleet.
