import asyncio
from asyncio import gather, sleep
from random import randint

from sqlalchemy import select


async def main():

    from app.controller import Controller
    from app.db import create_db_metadata, db_session
    from app.models import Building, Direction, Elevator, Ride

    await create_db_metadata(drop=False)

    async with db_session() as db:
        floors = randint(1, 4) * 5
        # building = Building("B01", floors)
        # db.add(building)

        # elevators = []
        # for x in range(5):
        #     elevators.append(Elevator(f"E0{x}", building=building))
        # db.add_all(elevators)
        # await db.commit()

        # print(f" -->> {building}")

        # async def queue_rides():
        #     await sleep(2)
        #     i = 0
        #     for x in range(randint(10, 20)):
        #         # if x % 2:
        #         #     continue
        #         i += 1
        #         pickup = randint(0, floors - 1)
        #         dropoff = randint(0, floors - 1)

        #         ride = Ride(
        #             building=building,
        #             pickup=pickup,
        #             dropoff=dropoff,
        #             direction=Direction(max(-1, min(1, dropoff - pickup))),
        #         )
        #         db.add(ride)

        #     await db.commit()

        # await queue_rides()
        elevators = (await db.scalars(select(Elevator))).all()

        async def start(elevator: Elevator):
            ctrl = Controller(elevator.id)
            async with ctrl():
                await ctrl._run()

        tasks = []
        for e in elevators:
            tasks.append(start(e))

        await gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
