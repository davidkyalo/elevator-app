from typing import Annotated

from pydantic import AliasChoices, BeforeValidator, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["env", "Env"]


class Env(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env.local"))

    debug: bool = False
    database_uri: PostgresDsn = Field(
        default=PostgresDsn("postgresql+asyncpg://user:password@localhost:5432/dbname"),
        validation_alias=AliasChoices("database_uri", "db_uri"),
    )


env = Env()
