# Ethical Multi-Agent Simulation

An initial Arcade prototype with a resizable toolbar, switchable scenarios, and a
minimal top-down world. Simulation state and scenario construction are separate
from the window so the project can later grow a headless runner.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Scenario Free controls

Select **Scenario Free**, press **Play**, then use:

- `W` to accelerate
- `S` to brake
- `A` to steer left
- `D` to steer right

The dashboard in the upper-right corner shows speed, steering percentages, and
brake status in every scenario. The WASD reminder is shown only in Scenario Free.

Use the **Time** slider in the top toolbar to change the simulation speed from
`x0.25` to `x2`. The time scale affects movement, acceleration, braking, and
steering together.

The toolbar is divided into scenario, playback, vehicle-variable, and application
sections. Use `▶` to play, `||` to pause, and `■` to stop and restore the current
scenario. The **Initial** slider sets the current scenario's initial speed in km/h.

The **Menu** opens framework, scenario, general, and project-info screens.
Utilitarianism values can be edited and saved from **Framework Settings**;
the other settings screens are placeholders for future versions.
