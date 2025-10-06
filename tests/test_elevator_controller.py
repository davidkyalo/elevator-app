import asyncio
from asyncio import gather, sleep
from random import randint

from sqlalchemy.ext.asyncio import AsyncSession

from app.controller import Controller
from app.models import Building, Direction, Elevator, Ride


async def test_basic(db_session: AsyncSession):
    floors = randint(1, 10) * 5
    building = Building("B01", floors)
    db_session.add(building)

    elevator = Elevator("E01", building=building)
    db_session.add(elevator)
    await db_session.commit()

    print(f" -->> {building}")
    print(f" -->> {elevator}")

    ctrl = Controller(elevator.id, db_session)

    async def queue_rides():
        await sleep(2)
        i = 0
        for x in range(randint(10, 100)):
            if x % 2:
                continue
            i += 1
            pickup = randint(0, floors - 1)
            dropoff = randint(0, floors - 1)

            ride = Ride(
                building=building,
                pickup=pickup,
                dropoff=dropoff,
                direction=Direction(min(-1, max(1, dropoff - pickup))),
            )
            db_session.add(ride)

        await db_session.commit()

    await queue_rides()
    await ctrl._run()
    await sleep(20)
    assert 0
