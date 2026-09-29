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
    jwt_secret_key: str = 'dev_aegent_jwt_secret_key_change_me'
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    password_max_length: int = 128
    approval_request_expire_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
