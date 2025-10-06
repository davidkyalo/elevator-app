from asyncio import Event as AioEvent
from asyncio import gather, sleep
from collections.abc import Hashable
from contextlib import asynccontextmanager
from functools import cached_property, lru_cache
from time import monotonic_ns
from typing import Any, Literal, cast

import rich
from pytest import Dir
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import DbSession, db_session
from app.models import (
    Building,
    Direction,
    DoorState,
    Elevator,
    ElevatorState,
    Ride,
    RideStatus,
    Status,
    Trip,
    TripStatus,
)


class Controller:

    db: DbSession
    elevator: Elevator
    building: Building
    state: ElevatorState

    _tick_delay_map = {
        Status.IDLE: 0.5,
        Status.DISABLED: 5,
    }

    def __init__(self, elevator_id: int) -> None:
        self.elevator_id = elevator_id
        self._running = AioEvent()
        self.precision = 1
        self._tick_buffer = 0
        self._last_tick = 0

    @cached_property
    def _tick_delay(self):
        return [self.state.status]

    @asynccontextmanager
    async def lock_state(self):
        yield self.state

    async def _tick(self, *, delay: float | bool | None = True):
        if delay not in (None, False):
            if delay is True:
                delay = self._tick_delay_map.get(self.state.status)
            delay = delay or (self.precision)
            await sleep(delay)
            self._tick_buffer += delay

        buffer = self._tick_buffer
        now = monotonic_ns()

        last = self._last_tick or now
        self._last_tick = now

        if now - buffer >= 10:
            self.log(f"Ticking...")
            self._tick_buffer = now

        return last, now

    @asynccontextmanager
    async def __call__(self):
        async with db_session() as db:
            self.db = db

            if not self._running.is_set():
                self._running.set()

                state = (
                    await self.db.scalars(
                        select(ElevatorState).where(
                            ElevatorState.id == self.elevator_id
                        )
                    )
                ).one()
                self.state = state
                self.elevator = await state.awaitable_attrs.elevator
            yield self
            self._running.clear()

    async def _run(self):
        self.log(f"Starting...")
        while self._running.is_set():
            await self._tick()
            async with self.lock_state() as state:
                match state.status:
                    case Status.MOVING:
                        await self._run_moving()
                    case Status.DOCKING:
                        await self._run_docking()
                    case Status.DOCKED:
                        await self._run_docked()
                    case Status.UNDOCKING:
                        await self._run_undocking()
                    case Status.UNDOCKED:
                        await self._run_undocked()
                    case Status.IDLE:
                        await self._run_idle()
                    case Status.DISABLED:
                        await self._run_disabled()
                await self.db.commit()

    async def _run_moving(self):
        elevator, state = self.elevator, self.state

        # assert state.status is Status.MOVING

        speed = elevator.speed_per_floor

        last_tick = self._last_tick
        now = monotonic_ns()
        elapsed = now - last_tick
        remainder = max(speed - state.floor_time + elapsed, 0)

        self.log(f"Moving: {elapsed = },  {remainder = }")
        if remainder > 0:
            state.floor_time += elapsed
        else:
            if state.floor == len(elevator.doors):
                state.floor -= 1
                state.direction = Direction.DOWN
            elif not state.floor:
                state.floor += 1
                state.direction = Direction.UP
            else:
                state.floor = state.floor + state.direction.value
            state.floor_time = 0
            if await self._should_dock_to_floor():
                state.status = Status.DOCKING

    async def _run_docking(self):
        elevator, state = self.elevator, self.state
        # assert state.status is Status.DOCKING
        speed = elevator.docking_speed

        self.log(f"I am docking...")

        last_tick = self._last_tick
        now = monotonic_ns()
        elapsed = now - last_tick
        remainder = max(speed - state.door_time + elapsed, 0)
        match state.door_state:
            case DoorState.OPENING if remainder > 0:
                state.door_time += elapsed
            case DoorState.OPENING:
                state.status = Status.DOCKED
                state.door_state = DoorState.OPEN
                state.door_time = 0
            case DoorState.CLOSED:
                state.door_state = DoorState.OPENING

    async def _run_docked(self):
        elevator, state = self.elevator, self.state
        # assert state.status in Status.DOCKED

        last_tick = self._last_tick
        delay = elevator.time_on_dock
        trip = state.trip

        if trip.status in (TripStatus.DRAFT, TripStatus.ENROUTE):
            trip.status = TripStatus.STOPPED
            await gather(self._do_dropoffs(), self._do_pickups())

        self.log(f"I have docked...")

        now = monotonic_ns()
        elapsed = now - last_tick
        remainder = max(delay - state.docked_time + elapsed, 0)

        if remainder > 0:
            state.docked_time += elapsed
        else:
            state.docked_time = 0
            state.status = Status.UNDOCKING
            trip.status = TripStatus.ENROUTE

    async def _run_undocking(self):
        elevator, state = self.elevator, self.state
        # assert state.status is Status.UNDOCKING
        speed = elevator.docking_speed

        self.log(f"I am undocking...")

        last_tick = self._last_tick
        now = monotonic_ns()
        elapsed = now - last_tick
        remainder = max(speed - state.door_time + elapsed, 0)

        match state.door_state:
            case DoorState.CLOSING if remainder > 0:
                state.door_time += elapsed
            case DoorState.CLOSING:
                state.status = Status.UNDOCKED
                state.door_state = DoorState.CLOSED
                state.door_time = 0
            case DoorState.OPEN:
                state.door_state = DoorState.CLOSING

    async def _run_undocked(self):
        state = self.state
        where = and_(
            Ride.trip_id == state.trip_id,
            Ride.status == RideStatus.ENROUTE,
        )
        stmt = select(Ride.direction).select_from(Ride).where(where)
        db = self.db

        dirs = set((await db.scalars(stmt)).all())
        if not dirs:
            state.status = Status.IDLE
            return

        state.status = Status.MOVING
        if state.direction not in dirs:
            state.direction = Direction(state.direction.value * -1)

    async def _run_idle(self):
        state = self.state
        stmt = (
            select(Ride.pickup)
            .where(
                or_(
                    and_(
                        Ride.trip_id == None,
                        Ride.status == RideStatus.QUEUED,
                    )
                ),
            )
            .order_by(Ride.created_at)
        )

        db = self.db
        if pickup := (await db.scalars(stmt)).first():
            self.log(f"Found a ride. Waking up....")
            trip = Trip(elevator=state.elevator)
            state.trip = trip
            state.status = Status.MOVING
            state.direction = Direction.resolve(state.floor, pickup)

            # await db.flush()

    async def _run_disabled(self):
        pass

    ##
    ###################
    ##

    async def _do_pickups(self):
        state = self.state
        trip = state.trip
        assert trip and trip.status is TripStatus.STOPPED

        current = (
            select(func.count())
            .select_from(Ride)
            .where(
                Ride.trip_id == state.trip_id,
                Ride.status.in_([RideStatus.ENROUTE, RideStatus.QUEUED]),
            )
        )
        args = ()
        if not not (await self.db.scalar(current)):
            args = (Ride.direction == state.direction,)

        where = and_(
            Ride.trip_id == None,
            Ride.status == RideStatus.QUEUED,
            Ride.pickup == state.floor,
            *args,
        )

        stmt = select(Ride).where(where).order_by(Ride.created_at).with_for_update()
        db = self.db
        for ride in (await db.scalars(stmt)).all():
            ride.trip = trip
            ride.status = RideStatus.ENROUTE
            db.add(ride)
        # await db.flush()

    async def _do_dropoffs(self):
        state = self.state
        trip, floor = state.trip, state.floor
        assert trip and trip.status is TripStatus.STOPPED

        where = and_(
            Ride.trip_id == state.trip_id,
            Ride.dropoff == floor,
            Ride.status == RideStatus.ENROUTE,
        )
        stmt = select(Ride).where(where).order_by(Ride.created_at).with_for_update()
        db = self.db
        for ride in (await db.scalars(stmt)).all():
            ride.status = RideStatus.ARRIVED
            db.add(ride)
        # await db.flush()

    async def _should_dock_to_floor(self):
        state = self.state
        floor = state.floor

        if self.elevator.doors[floor]:

            current = (
                select(func.count())
                .select_from(Ride)
                .where(
                    Ride.trip_id == state.trip_id,
                    Ride.status.in_([RideStatus.ENROUTE, RideStatus.QUEUED]),
                )
            )
            args = ()
            if not not (await self.db.scalar(current)):
                args = (Ride.direction == state.direction,)
            stmt = (
                select(func.count())
                .select_from(Ride)
                .where(
                    or_(
                        and_(
                            Ride.trip_id == None,
                            Ride.status == RideStatus.QUEUED,
                            Ride.pickup == floor,
                            *args,
                        ),
                        and_(
                            Ride.trip_id == state.trip_id,
                            Ride.dropoff == floor,
                            Ride.status == RideStatus.ENROUTE,
                        ),
                    ),
                )
            )
            return not not (await self.db.scalar(stmt))

    async def emit(self, ev: "EventType", *args, **kwargs):
        pass

    def log(self, *args, pretty: bool = False, **kwargs):
        fn = rich.inspect if pretty else rich.print
        fn(*args, **kwargs)

    async def _shutdown(self):
        pass


type EventType = Literal["FLOOR_LEAVE"]
