from __future__ import annotations

import io
import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app


def test_production_rejects_placeholder_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env='production',
            jwt_secret_key='dev_aegent_jwt_secret_key_change_me',
            cors_allowed_origins=['https://app.example.com'],
        )


def test_production_rejects_wildcard_cors_with_credentials() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env='production',
            jwt_secret_key='a' * 64,
            cors_allowed_origins=['*'],
            cors_allow_credentials=True,
        )


def test_production_rejects_wildcard_trusted_hosts() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env='production',
            jwt_secret_key='a' * 64,
            cors_allowed_origins=['https://app.example.com'],
            trusted_hosts=['*'],
        )

    with pytest.raises(ValidationError):
        Settings(
            app_env='production',
            jwt_secret_key='a' * 64,
            cors_allowed_origins=['https://app.example.com'],
            trusted_hosts=['*.example.com'],
        )


def test_request_id_header_is_added() -> None:
    client = TestClient(app)
    response = client.get('/health')
    assert response.status_code == 200
    assert 'x-request-id' in response.headers
    assert response.headers['x-request-id']


def test_request_log_includes_request_id() -> None:
    logger = logging.getLogger('aegent')
    handler = next(h for h in logger.handlers if isinstance(h, logging.StreamHandler))
    buffer = io.StringIO()
    original_stream = handler.stream
    handler.setStream(buffer)
    try:
        client = TestClient(app)
        response = client.get('/health', headers={'x-request-id': 'trace-123'})
        assert response.status_code == 200
        assert 'trace-123' in buffer.getvalue()
    finally:
        handler.setStream(original_stream)
