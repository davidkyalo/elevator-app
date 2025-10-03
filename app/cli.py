import asyncio

from app.worker import run_worker


def worker():
    asyncio.run(run_worker())
