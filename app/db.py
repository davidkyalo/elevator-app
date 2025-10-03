from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.env import env

__all__ = ["engine", "db_session", "DbSession"]


engine = create_async_engine(str(env.database_uri), echo=env.debug and "debug")

create_session = async_sessionmaker(engine)


async def create_db_metadata(*, drop=False):
    from app.models import DbModel

    if drop:
        async with engine.begin() as conn:
            await conn.run_sync(DbModel.metadata.drop_all)

    async with engine.begin() as conn:
        await conn.run_sync(DbModel.metadata.create_all)


@asynccontextmanager
async def db_session():
    async with create_session() as session:
        async with session.begin():
            yield session


DbSession = Annotated[AsyncSession, Depends(db_session)]
