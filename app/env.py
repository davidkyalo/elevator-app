from pydantic import AliasChoices, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["env", "Env"]


class Env(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env.local"))

    debug: bool = False
    database_uri: PostgresDsn = Field(
        default=PostgresDsn("postgresql+psycopg://user:password@localhost:5432/dbname"),
        validation_alias=AliasChoices("database_uri", "db_uri"),
    )
    test_database_uri: PostgresDsn = Field(
        default=PostgresDsn("postgresql+psycopg://user:password@host:5432/test_dbname"),
        validation_alias=AliasChoices("test_database_uri", "test_db_uri"),
    )


env = Env()
