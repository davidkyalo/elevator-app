from typing import Annotated, Generic, cast, overload

from fastapi import Depends

from app.db import DbSession
from app.models import Building, DbModel, Direction, Ride, UpOrDown


async def get_building(building_id: str, db: DbSession):
    return


BuildingDep = Annotated[Building, Depends(get_building)]


class RideManager:

    def __init__(self, building: BuildingDep, db: DbSession) -> None:
        self.db = db
        self.building = building

    @overload
    def create_ride(
        self, pickup: int, dropoff: int, *, direction: UpOrDown | None = None
    ): ...
    @overload
    def create_ride(self, pickup: int, *, direction: UpOrDown): ...

    def create_ride(
        self,
        pickup: int,
        dropoff: int | None = None,
        *,
        direction: Direction | None = None,
    ):
        if direction is None:
            direction = Direction.resolve(pickup, dropoff or pickup)

        if direction is Direction.NONE:
            raise ValueError(f"Invalid destination")

        ride = Ride(
            building=self.building,
            pickup=pickup,
            dropoff=dropoff,
            direction=direction,
        )

        return ride
