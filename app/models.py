import time
from datetime import datetime
from enum import Enum, StrEnum, auto
from typing import Literal

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Float,
    ForeignKey,
    SmallInteger,
    String,
    desc,
    func,
)
from sqlalchemy.dialects.postgresql import INT4RANGE
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

_db_timestamp = func.localtimestamp()


class Direction(Enum):
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
    DOOR_OPENING = auto()
    DOOR_OPEN = auto()
    DOOR_CLOSING = auto()
    PAUSED = auto()
    """Made an emergency stop
    """
    OFFLINE = auto()
    """Elevator is not available for service.
    """


class DoorState(StrEnum):
    CLOSED = auto()
    OPEN = auto()
    OPENING = auto()
    CLOSING = auto()


class DbModel(AsyncAttrs, DeclarativeBase):
    pass


class Snapshot(DbModel):
    __tablename__ = "snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    elevator_id: Mapped[int] = mapped_column(ForeignKey("elevator.id"))
    elevator: Mapped["Elevator"] = relationship(back_populates="snapshots")

    trip_id: Mapped[int | None] = mapped_column(
        ForeignKey("trip.id", ondelete="RESTRICT")
    )
    trip: Mapped["Trip | None"] = relationship(back_populates="snapshots")

    status: Mapped[Status] = mapped_column(default=Status.OFFLINE)
    door_state: Mapped[DoorState] = mapped_column(default=DoorState.CLOSED)
    direction: Mapped[Direction] = mapped_column(default=Direction.NONE)
    floor: Mapped[int] = mapped_column(SmallInteger, default=0)
    position: Mapped[float] = mapped_column(Float(precision=4), default=0)

    next_door: Mapped[int | None]
    next_Stop: Mapped[int | None]

    timestamp: Mapped[datetime] = mapped_column(default=_db_timestamp, index=True)
    created_at: Mapped[datetime] = mapped_column(default=_db_timestamp)


class Ride(DbModel):
    __tablename__ = "ride"

    class Status(StrEnum):

        REQUESTED = auto()
        PICKUP = auto()
        ENROUTE = auto()
        COMPLETED = auto()
        CANCELLED = auto()

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    status: Mapped[Status] = mapped_column(default=Status.REQUESTED)

    building_id: Mapped[str] = mapped_column(
        ForeignKey("building.id", onupdate="CASCADE", ondelete="RESTRICT")
    )
    building: Mapped["Building"] = relationship(back_populates="rides")
    direction: Mapped[Direction]
    pickup: Mapped[int] = mapped_column(SmallInteger)
    dropoff: Mapped[int | None] = mapped_column(SmallInteger)

    created_at: Mapped[datetime] = mapped_column(default=_db_timestamp)
    updated_at: Mapped[datetime] = mapped_column(
        default=_db_timestamp, onupdate=_db_timestamp
    )

    trip_id: Mapped[int | None] = mapped_column(
        ForeignKey("trip.id", ondelete="RESTRICT")
    )
    trip: Mapped["Trip | None"] = relationship(back_populates="rides")


class Trip(DbModel):
    __tablename__ = "trip"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    elevator_id: Mapped[int | None] = mapped_column(ForeignKey("elevator.id"))
    elevator: Mapped["Elevator| None"] = relationship(back_populates="trips")

    rides: Mapped[list["Ride"]] = relationship(back_populates="trip")
    snapshots: Mapped["Snapshot"] = relationship(
        back_populates="trip", order_by=desc("Snapshot.timestamp")
    )

    created_at: Mapped[datetime] = mapped_column(default=_db_timestamp)
    updated_at: Mapped[datetime] = mapped_column(
        default=_db_timestamp, onupdate=_db_timestamp
    )


class Elevator(DbModel):
    __tablename__ = "elevator"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(100))

    building_id: Mapped[str] = mapped_column(ForeignKey("building.id"))
    building: Mapped["Building"] = relationship(back_populates="elevators")

    floors: Mapped[list[int]] = mapped_column(
        ARRAY(SmallInteger, dimensions=1, as_tuple=True),
        comment="All floors and their accessibility.",
    )
    speed_per_floor: Mapped[int]
    door_transition_speed: Mapped[int]
    door_hold_time: Mapped[tuple[int, int]] = mapped_column(INT4RANGE)

    trips: Mapped[list["Trip"]] = relationship(back_populates="elevator")
    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="elevator")


class Building(DbModel):
    __tablename__ = "building"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    floors: Mapped[int] = mapped_column(nullable=False)
    """Number of floors in the building.
    """

    elevators: Mapped[list["Elevator"]] = relationship(
        back_populates="building", cascade="all, delete-orphan"
    )


class User(DbModel):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)
