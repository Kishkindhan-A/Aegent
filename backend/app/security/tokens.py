from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.models.enums import UserRole


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def create_access_token(
    user_id: UUID,
    organization_id: UUID,
    role: UserRole,
    *,
    token_type: str = 'access',
) -> str:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError('JWT_SECRET_KEY is not configured. Set it in backend/.env or the environment.')
    if len(settings.jwt_secret_key.encode('utf-8')) < 32:
        raise RuntimeError('JWT_SECRET_KEY must be at least 32 bytes long to meet minimum HMAC security requirements.')

    issued_at = now_utc()
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        'sub': str(user_id),
        'organization_id': str(organization_id),
        'role': role.value,
        'token_type': token_type,
        'iat': int(issued_at.timestamp()),
        'exp': int(expires_at.timestamp()),
        'jti': str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str) -> dict:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise ValueError('JWT_SECRET_KEY is not configured. Set it in backend/.env or the environment.')
    if len(settings.jwt_secret_key.encode('utf-8')) < 32:
        raise ValueError('JWT_SECRET_KEY must be at least 32 bytes long to meet minimum HMAC security requirements.')

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={'require': ['exp', 'sub', 'organization_id', 'role', 'token_type', 'iat']},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token has expired.',
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token.',
        ) from exc

    if payload.get('token_type') != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect token type.',
        )

    return payload
