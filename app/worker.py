from asyncio import sleep


async def run_worker():
    tick = 990
    while tick := tick + 1:
        print(f"Pulse:  {tick:>10,}")
        await sleep(1)
