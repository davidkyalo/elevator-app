from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from app.env import Env


def pytest_configure(config):
    pass


@pytest.fixture(scope="session")
def env() -> "Env":
    from app.env import env

    return env


@pytest.fixture(scope="session")
async def db_engine(env: "Env"):
    engine = create_async_engine(str(env.test_database_uri), echo=env.debug and "debug")

    from app.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def db_session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest_asyncio.fixture()
async def db_session(db_session_factory):
    ses = db_session_factory
    async with db_session_factory() as ses:
        try:
            yield ses
        finally:
            ses.rollback()
