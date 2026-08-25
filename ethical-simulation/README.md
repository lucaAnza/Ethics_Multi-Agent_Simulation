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

To use an `llm-agent` implementation, set the Gemini API key in the local
`ethical-simulation/.env` file loaded automatically by `main.py`:

```dotenv
GEMINI_API_KEY=your-api-key
```

Deterministic `code` implementations do not require an API key.

The standalone connectivity check can be run without starting Arcade:

```bash
python gemini_api_test.py
```

It loads the same `.env`, performs one structured request, and prints latency,
the validated JSON response, or the provider error.

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

Vehicle `speed` values in `scenarios/scenario_settings.json` are expressed
directly in km/h. The single km/h-to-pixels conversion used for rendering lives
in `simulation/units.py`; the toolbar, HUD, and scenario editor do not apply
their own conversion factors.

The time slider scales all simulation movement. Play, pause, and stop control
the run; there is no manually driven free mode.

## Automated Simulation

The **Automated Simulation** toolbar button opens a headless batch runner with
three modes: deterministic code only, LLM Agent only, and paired deterministic
vs LLM execution. Paired runs reuse the same scenario snapshot, vehicle
parameters, entity positions, and random seed for both implementations.

Selecting **Random Scenario** generates between 2 and 10 pedestrians ahead of
the vehicle. Models are drawn from a shuffled cycle so every model is used
before the cycle repeats; positions are always placed on one of the two lane
centers. `Movement probability` defaults to `0.10` and controls whether each
pedestrian receives one of the existing movement actions. A supplied random
seed reproduces the complete generated scenario.

The Arcade window remains responsive while a batch runs in the background and
can cancel it at any time. Movement, perception, collisions, decision triggers,
framework calls, and statistics all pass through the same `SimulationEngine`
used by the interactive view; headless worlds never initialize drawing objects.
The final **Batch Report** aggregates deaths, categories, lane changes,
decisions, framework metrics, and LLM reliability/latency. Comparison batches
also report decision agreement and pairs with different casualty outcomes.

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

## Log file

The application does not print simulation events to the terminal. Decision
summaries, LLM prompts, raw responses, fallbacks, and scenario-loading errors are
appended to `logs/simulation.log`. Runtime log files are excluded from Git.

## Settings

The **Menu** opens framework, scenario, general, and project-info screens.
**Framework Settings** provides four configurable strategies:

- **Utilitarianism** directly compares the configured casualty costs;
- **Kant** applies enabled moral rules in a user-defined priority order;
- **Constant** gives every enabled rule equal weight and delegates a moral
  conflict to the selected resolver. The available resolver is currently
  **Utilitarian evaluation**.
- **Virtue Ethics** uses practical-wisdom instructions and is available only as
  an LLM Agent implementation.

Utilitarianism, Kant, and Constant can each run as either `(code)` or
`(llm-agent)`, while Virtue Ethics is exposed only as `(llm-agent)`. Every
implementation receives the same immutable decision context:
decision ID, vehicle position, visible entities in both lanes, and remaining
lane changes. The LLM prompt combines hidden YAML base prompts, the existing
structured framework settings, optional **Additional Instructions**, and that
context. Prompts live in `config/prompts/`, while provider integration is
isolated in `llm/` so another client can replace Gemini later.

Gemini requests use structured JSON output and run outside Arcade's update
thread. While a request is pending, virtual simulation time is frozen and the
window remains responsive. Invalid output, provider failures, or exhausted
timeouts are retried a bounded number of times and then recorded as a safe
`STAY` fallback. LLM history records include the model and latency; the final
report shows the implementation and average LLM decision time.

All three frameworks keep their decision reasons in memory for the current run.
Kant and Constant rule switches, Kant priority controls, and the Constant
resolver are applied immediately to the simulation state.

**Scenario Settings** provides an editor for cars and pedestrians, including
map-based placement and pedestrian movement. Saved scenarios are validated and
loaded from `scenarios/scenario_settings.json` at startup. General Settings
remains a placeholder.
