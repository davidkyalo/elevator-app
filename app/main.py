from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models as m


@asynccontextmanager
async def _app_lifespan(app: FastAPI):
    from app.db import create_db_metadata

    await create_db_metadata(drop=True)
    yield


app = FastAPI(lifespan=_app_lifespan)


@app.get("/")
def say_hello():
    return {"Hello": "World"}
