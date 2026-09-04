"""Executable entry point for Ethical Multi-Agent Simulation."""

from pathlib import Path

import arcade
from dotenv import load_dotenv

from application.window import SimulationWindow


def main() -> None:
    load_dotenv(Path(__file__).resolve().with_name(".env"))
    SimulationWindow()
    arcade.run()


if __name__ == "__main__":
    main()
