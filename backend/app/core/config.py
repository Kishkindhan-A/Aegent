from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    app_name: str = 'Aegent'
    app_version: str = '0.1.0'
    app_env: str = 'development'
    database_url: str = 'postgresql+psycopg://username:password@localhost:5432/aegent'


@lru_cache
def get_settings() -> Settings:
    return Settings()
