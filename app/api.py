from pydantic import BaseModel
from sqlalchemy import select

from app.db import DbSession
from app.models import Building, Direction, Ride

from .main import app


@app.post("/{building_id}/request-ride")
async def request_ride(building_id: str, pickup: int, dropoff: int, db: DbSession):

    async with db as db:
        building = await db.scalar(select(Building).where(Building.id == building_id))

        ride = Ride(
            building=building,
            pickup=pickup,
            dropoff=dropoff,
            direction=Direction(max(-1, min(1, dropoff - pickup))),
        )
        db.add(ride)
        await db.commit()
        return ride.id
