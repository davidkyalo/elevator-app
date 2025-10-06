from collections.abc import Mapping
from dataclasses import KW_ONLY
from datetime import datetime
from enum import Enum, IntEnum, StrEnum, auto
from functools import cache, cached_property
from typing import Literal, Self

from pydantic import JsonValue
from sqlalchemy import (
    ARRAY,
    JSON,
    BigInteger,
    Column,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Table,
    UniqueConstraint,
    desc,
)
from sqlalchemy.dialects.postgresql import INT4RANGE, NUMRANGE
from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .base import Base, DataRecord, created_at_column, updated_at_column


class Direction(IntEnum):
    """Elevator direction"""

    NONE = 0
    UP = 1
    DOWN = -1

    @classmethod
    def resolve(cls, pickup: int, dropoff: int):
        diff = dropoff - pickup
        return cls(-1 if diff < 0 else 1 if diff else 0)


type UpOrDown = Literal[Direction.UP, Direction.DOWN]


class Status(StrEnum):
    IDLE = auto()
    MOVING = auto()
    DOCKING = auto()
    DOCKED = auto()
    UNDOCKING = auto()
    UNDOCKED = auto()
    DISABLED = auto()


class DoorState(StrEnum):
    CLOSED = auto()
    OPENING = auto()
    OPEN = auto()
    CLOSING = auto()


class ElevatorState(DataRecord):
    __tablename__ = "elevator_state"

    id: Mapped[int] = mapped_column(
        ForeignKey("elevator.id", ondelete="CASCADE"), init=False, primary_key=True
    )

    status: Mapped[Status] = mapped_column(default=Status.IDLE)
    door_state: Mapped[DoorState] = mapped_column(default=DoorState.CLOSED)

    direction: Mapped[Direction] = mapped_column(default=Direction.NONE)
    floor: Mapped[int] = mapped_column(SmallInteger, default=0)

    floor_time: Mapped[int] = mapped_column(BigInteger, default=0)
    door_time: Mapped[int] = mapped_column(BigInteger, default=0)
    docked_time: Mapped[int] = mapped_column(BigInteger, default=0)

    trip_id: Mapped[int | None] = mapped_column(
        ForeignKey("trip.id", ondelete="SET NULL"), default=None
    )
    trip: Mapped["Trip"] = relationship(default=None, lazy="joined")

    elevator: Mapped["Elevator"] = relationship(back_populates="state", default=None)

    created_at: Mapped[datetime] = created_at_column(init=False)
    updated_at: Mapped[datetime] = updated_at_column(init=False)


class RideStatus(StrEnum):
    QUEUED = auto()
    ENROUTE = auto()
    ARRIVED = auto()
    CANCELLED = auto()


class Ride(DataRecord):
    __tablename__ = "ride"

    id: Mapped[int] = mapped_column(BigInteger, init=False, primary_key=True)
    status: Mapped[RideStatus] = mapped_column(init=False, default=RideStatus.QUEUED)

    building_id: Mapped[str] = mapped_column(
        ForeignKey("building.id", onupdate="CASCADE"), init=False
    )
    building: Mapped["Building"] = relationship(backref="rides")

    pickup: Mapped[int] = mapped_column(SmallInteger)
    dropoff: Mapped[int | None] = mapped_column(SmallInteger, insert_default=None)
    direction: Mapped[Direction]

    trip_id: Mapped[int | None] = mapped_column(
        ForeignKey("trip.id"), init=False, default=None
    )

    created_at: Mapped[datetime] = created_at_column(init=False)
    updated_at: Mapped[datetime] = updated_at_column(init=False)

    trip: Mapped["Trip | None"] = relationship(
        back_populates="rides", init=False, default=None
    )


class TripStatus(StrEnum):
    DRAFT = auto()
    ENROUTE = auto()
    STOPPED = auto()
    ARRIVED = auto()
    CANCELLED = auto()


class Trip(DataRecord):
    __tablename__ = "trip"

    id: Mapped[int] = mapped_column(BigInteger, init=False, primary_key=True)
    # direction: Mapped[Direction]
    status: Mapped[TripStatus] = mapped_column(default=TripStatus.DRAFT)

    started_at: Mapped[datetime | None] = mapped_column(default=None, init=False)
    ended_at: Mapped[datetime | None] = mapped_column(default=None, init=False)

    created_at: Mapped[datetime] = created_at_column(init=False)
    updated_at: Mapped[datetime] = updated_at_column(init=False)

    elevator_id: Mapped[int] = mapped_column(ForeignKey("elevator.id"), default=None)
    elevator: Mapped["Elevator"] = relationship(back_populates="trips", default=None)

    rides: Mapped[list["Ride"]] = relationship(
        init=False,
        back_populates="trip",
        default_factory=list,
    )


class Elevator(DataRecord):
    __tablename__ = "elevator"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str | None] = mapped_column(String(100))

    building_id: Mapped[str] = mapped_column(ForeignKey("building.id"), default=None)
    building: Mapped["Building"] = relationship(
        back_populates="elevators", default=None
    )

    doors: Mapped[list[int]] = mapped_column(
        ARRAY(SmallInteger, dimensions=1), default_factory=list
    )

    speed_per_floor: Mapped[int] = mapped_column(default=5)
    docking_speed: Mapped[int] = mapped_column(default=2)
    time_on_dock: Mapped[int] = mapped_column(default=0)

    trips: Mapped[list["Trip"]] = relationship(default_factory=list)
    state: Mapped[ElevatorState] = relationship(default_factory=lambda: ElevatorState())

    created_at: Mapped[datetime] = created_at_column(init=False)
    updated_at: Mapped[datetime] = updated_at_column(init=False)

    @validates("doors")
    def validate_doors(self, key, value):
        building = self.building
        all_doors, floors = building.doors, building.floor_count
        if not value:
            return all_doors

        diff = floors - len(value)
        if 0 > diff:
            value = value[:floors]
        return [int(a and b) for a, b in zip(all_doors, value)]


class Building(DataRecord):
    __tablename__ = "building"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    floor_count: Mapped[int]

    elevators: Mapped[list["Elevator"]] = relationship(
        init=False,
        back_populates="building",
        cascade="all, delete-orphan",
        default_factory=list,
    )
    doors: Mapped[list[int]] = mapped_column(
        ARRAY(SmallInteger, dimensions=1), default_factory=list
    )

    created_at: Mapped[datetime] = created_at_column(init=False)
    updated_at: Mapped[datetime] = updated_at_column(init=False)

    @validates("doors")
    def validate_doors(self, key, value):
        floors = self.floor_count
        diff = floors - len(value)
        if 0 > diff:
            return value[:floors]
        else:
            return list(value) + [1] * diff


class User(DataRecord):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)


class Message[T_Payload: Mapping[str, JsonValue]](DataRecord):

    __tablename__ = "message"

    id: Mapped[int] = mapped_column(BigInteger, init=False, primary_key=True)
    address: Mapped[str]
    payload: Mapped[T_Payload] = mapped_column(JSON, default=dict)
    headers: Mapped[Mapping[str, JsonValue]] = mapped_column(JSON, default=dict)
    _: KW_ONLY

    timestamp: Mapped[float] = created_at_column()
    created_at: Mapped[float] = created_at_column(init=False)
