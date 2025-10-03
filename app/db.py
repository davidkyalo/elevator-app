from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.settings import settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


engine = create_async_engine(
    str(settings.database_uri),
    echo=True,
)

sessionmaker = async_sessionmaker(engine)


async def create_db_metadata(*, drop=False):
    if drop:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def open_session():
    async with sessionmaker() as session:
        async with session.begin():
            yield session


DbSessionDep = Annotated[AsyncSession, Depends(open_session)]
