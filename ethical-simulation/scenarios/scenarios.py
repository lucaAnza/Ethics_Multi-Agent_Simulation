"""Factories for initial scenario state, kept separate from the UI."""

from dataclasses import dataclass

from simulation.entities import Car, Pedestrian


@dataclass
class Scenario:
    cars: list[Car]
    pedestrians: list[Pedestrian]


def create_scenario(name: str, road_y: float) -> Scenario:
    car = Car(x=130, y=road_y - 42)
    if name == "Scenario Free":
        car = Car(x=170, y=road_y, speed=0.0)
        pedestrians = [
            Pedestrian(x=560, y=road_y + 35, model="woman"),
            Pedestrian(x=760, y=road_y - 35, model="old_man"),
            Pedestrian(x=930, y=road_y + 20, model="boy"),
            Pedestrian(x=670, y=road_y + 145, model="custom", label="Sam"),
        ]
    elif name == "Scenario 2":
        pedestrians = [
            Pedestrian(x=400, y=road_y + 46, model="man"),
            Pedestrian(x=475, y=road_y + 46, model="woman"),
            Pedestrian(x=550, y=road_y + 46, model="old_man"),
            Pedestrian(x=625, y=road_y + 46, model="old_woman"),
            Pedestrian(x=700, y=road_y + 46, model="boy"),
            Pedestrian(x=775, y=road_y + 46, model="girl"),
            Pedestrian(
                x=760,
                y=road_y - 25,
                model="custom",
                label="Alex",
            ),
        ]
    else:
        pedestrians = [Pedestrian(x=720, y=road_y - 25, model="man")]
    return Scenario(cars=[car], pedestrians=pedestrians)
