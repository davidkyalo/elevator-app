from asyncio import sleep

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Building


async def test_buildings(db_session: AsyncSession):
    obj = Building("building-one", 10)
    obj.elevators = []
    async with db_session.begin():
        db_session.add(obj)

    print(f">> { obj:}")

    assert 0
