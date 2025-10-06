import asyncio
from collections.abc import Hashable, Mapping
from dataclasses import KW_ONLY, dataclass, field
from time import monotonic
from typing import Any, Awaitable, Callable, Literal, Self, cast
from uuid import uuid4

from pydantic import JsonValue

Type = type


@dataclass(frozen=True, slots=True)
class Consumer(asyncio.Queue):

    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    callback: Callable[[Message]] | None = None
    teardown: Callable[[Exception | None]] | None = None


class EventBus:
    """Event bus"""

    def __init__(self) -> None:
        self._consumers: list[Consumer] = []

    def connect(self, *args, **kwargs):
        s = Consumer(*args, **kwargs)
        self._consumers.append(s)
        return s

    async def emit(self, event: Message):
        return await self.publish(event)

    async def publish(self, event: Message) -> None:
        for q in self._consumers:
            try:
                q.queue.put_nowait(event)
            except Exception:
                pass


class EventHub[K: Hashable, V: "EventBus"](Mapping[K, V]):
    """Event bus"""

    bus_class: type[V] = cast(type[V], EventBus)

    def __init__(self) -> None:
        self._buses: dict[K, V] = {}

    def __getitem__(self, key: K):
        try:
            return self._buses[key]
        except KeyError:
            return self._buses.setdefault(key, self.bus_class())


class Producer:

    async def push(self):
        pass
