from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_session,
    async_sessionmaker,
    create_async_engine,
)

from app.env import env

__all__ = ["engine", "db_session", "DbSession"]


engine = create_async_engine(str(env.database_uri), echo=env.debug and "debug")

create_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def create_db_metadata(*, drop=False):
    from app.models.base import Base

    async with engine.begin() as conn:
        if drop:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def db_session():
    async with create_session() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(db_session)]
