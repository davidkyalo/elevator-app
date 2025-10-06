from collections.abc import Sequence
from datetime import datetime
from functools import partial, wraps
from typing import Any, Literal, cast

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column

_db_timestamp = func.localtimestamp()


created_at_column = partial(
    mapped_column,
    default=_db_timestamp,
    insert_default=_db_timestamp,
)

updated_at_column = partial(
    mapped_column,
    default=_db_timestamp,
    insert_default=_db_timestamp,
    onupdate=_db_timestamp,
)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Record(Base):
    __abstract__ = True


class DataRecord(MappedAsDataclass, Record):
    __abstract__ = True
