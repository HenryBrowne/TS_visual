from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+psycopg2://ts_bench:ts_bench@localhost:5435/ts_bench"
    anthropic_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
