from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Owner:
    owner_id: int
    name: str
    email: str
    phone: str
    pets: list[Pet] = field(default_factory=list)

    def add_owner(self) -> Owner:
        pass

    def edit_owner(self, name: str, email: str, phone: str) -> None:
        pass

    def remove_owner(self) -> None:
        pass

    def add_pet(self, pet: Pet) -> None:
        pass


@dataclass
class Pet:
    pet_id: int
    name: str
    species: str
    breed: str
    age: int
    owner: Optional[Owner] = None

    def add_pet(self, owner: Owner) -> Pet:
        pass

    def edit_pet(self, name: str, species: str, breed: str, age: int) -> None:
        pass

    def remove_pet(self) -> None:
        pass


@dataclass
class Walk:
    walk_id: int
    pet: Pet
    start_time: datetime
    duration_minutes: int
    status: str = "scheduled"

    def schedule(self) -> None:
        pass

    def cancel(self) -> None:
        pass


@dataclass
class WalkScheduler:
    walks: list[Walk] = field(default_factory=list)

    def schedule_walk(self, pet: Pet, start_time: datetime, duration_minutes: int) -> Walk:
        pass

    def cancel_walk(self, walk_id: int) -> None:
        pass

    def reschedule_walk(self, walk_id: int, new_start_time: datetime) -> None:
        pass

    def edit_walk(self, walk_id: int, duration_minutes: int) -> None:
        pass

    def get_walks_for_pet(self, pet_id: int) -> list[Walk]:
        pass
