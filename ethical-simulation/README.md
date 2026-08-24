# Ethical Multi-Agent Simulation

An Arcade 3.3 simulation for comparing ethical decision strategies in a
two-lane autonomous-driving scenario. Physical state and perception are owned by
the simulation; ethical frameworks receive only the entities currently visible
in each lane and return one of two actions: `STAY` or `CHANGE_LANE`.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Simulation flow

The vehicle moves forward automatically at the configured speed. Its current
lane is outlined by cyan dashed vision lines, while the translucent area marks
the visible portion of the adjacent lane. When the closest possible collision
reaches `decision_distance`, the selected ethical framework is called once for
that incident. A lane change is a linear vertical movement lasting about
`0.10 s` and is allowed only while the configured `max_spostamenti` budget has
not been exhausted.

The **Vehicle Variables** toolbar section controls:

- initial speed in km/h;
- `vision_distance`, the maximum perception range in pixels;
- `decision_distance`, the threshold that triggers a decision;
- `max_spostamenti`, the maximum number of lane changes.

The time slider scales all simulation movement. Play, pause, and stop control
the run; there is no manually driven free mode.

The simulation ends only when the primary vehicle reaches the tunnel. The final
panel reports lane-change usage, victims grouped by category, and rows supplied
by the active framework. Utilitarianism reports its total casualty malus and the
number of decisions retained in its in-memory history.

The final panel also opens a paginated **Simulation Report** containing summary
cards, a casualty histogram, a lane-change usage pie chart, and the complete
decision history. Every history record stores the vehicle position, descriptions
of both visible lanes, the applied action, its reason, and optional
framework-specific details such as a Kant rule or Constant conflict resolver.
The report can return to the summary or restart the simulation directly.

## Settings

The **Menu** opens framework, scenario, general, and project-info screens.
**Framework Settings** provides three configurable strategies:

- **Utilitarianism** directly compares the configured casualty costs;
- **Kant** applies enabled moral rules in a user-defined priority order;
- **Constant** gives every enabled rule equal weight and delegates a moral
  conflict to the selected resolver. The available resolver is currently
  **Utilitarian evaluation**.

All three frameworks keep their decision reasons in memory for the current run.
Kant and Constant rule switches, Kant priority controls, and the Constant
resolver are applied immediately to the simulation state.

**Scenario Settings** provides an editor for cars and pedestrians, including
map-based placement and pedestrian movement. Saved scenarios are validated and
loaded from `scenarios/scenario_settings.json` at startup. Ross and General
Settings remain placeholders.
