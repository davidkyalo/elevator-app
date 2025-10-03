from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["settings", "Settings"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env.local"))
    database_uri: PostgresDsn = Field(
        default=PostgresDsn("postgresql+asyncpg://user:password@localhost:5432/dbname"),
        validation_alias="db_uri",
    )


settings = Settings()
