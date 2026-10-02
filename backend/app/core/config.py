from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_csv(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(',') if item.strip()]
    return [str(value)]


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
    debug: bool = False
    database_url: str = 'postgresql+psycopg://username:password@localhost:5432/aegent'
    jwt_secret_key: str = 'dev_aegent_jwt_secret_key_change_me'
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    password_max_length: int = 128
    approval_request_expire_minutes: int = 60
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ['http://localhost:5173', 'http://127.0.0.1:5173'])
    cors_allow_credentials: bool = False
    trusted_hosts: list[str] = Field(default_factory=lambda: ['localhost', '127.0.0.1', '[::1]', 'testserver'])
    max_request_size_bytes: int = 1_048_576
    rate_limit_requests_per_minute: int = 60
    log_level: str = 'INFO'

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == 'production'

    @field_validator('cors_allowed_origins', 'trusted_hosts', mode='before')
    @classmethod
    def parse_csv_lists(cls, value: Any) -> list[str]:
        return _parse_csv(value)

    @field_validator('app_env')
    @classmethod
    def normalize_app_env(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret(cls, value: str, info: Any) -> str:
        if value is None:
            raise ValueError('JWT secret is required.')
        secret = value.strip()
        if not secret:
            raise ValueError('JWT secret must not be empty.')

        app_env = str(info.data.get('app_env', 'development')).lower()
        placeholder_values = {
            'dev_aegent_jwt_secret_key_change_me',
            'change-me',
            'your-secret-key',
            'replace-me',
            'example-secret',
            'jwt-secret-key',
        }
        if app_env == 'production':
            if secret.lower() in placeholder_values:
                raise ValueError('Production JWT secret must not use a placeholder value.')
            if len(secret.encode('utf-8')) < 32:
                raise ValueError('Production JWT secret must be at least 32 characters long.')

        return secret

    @model_validator(mode='after')
    def validate_production_security(self) -> 'Settings':
        if self.app_env.lower() != 'production':
            return self

        if not self.cors_allowed_origins:
            raise ValueError('Production must define at least one allowed CORS origin.')
        if '*' in self.cors_allowed_origins and self.cors_allow_credentials:
            raise ValueError('Production CORS cannot allow wildcard origins when credentials are enabled.')
        if '*' in self.cors_allowed_origins:
            raise ValueError('Production CORS cannot use a wildcard origin.')
        if not self.trusted_hosts or any(not host.strip() for host in self.trusted_hosts):
            raise ValueError('Production must define explicit trusted hosts.')
        if self.max_request_size_bytes <= 0:
            raise ValueError('max_request_size_bytes must be positive.')
        if self.rate_limit_requests_per_minute <= 0:
            raise ValueError('rate_limit_requests_per_minute must be positive.')
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
