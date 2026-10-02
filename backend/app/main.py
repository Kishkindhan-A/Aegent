from __future__ import annotations

import logging
import logging.config
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.agents import router as agents_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.policies import router as policies_router
from app.core.config import get_settings
from app.database.session import SessionLocal

settings = get_settings()

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'logging.Formatter',
            'format': '%(asctime)s %(levelname)s %(message)s %(request_id)s %(method)s %(path)s %(status_code)s %(duration_ms)s',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'stream': 'ext://sys.stdout',
        }
    },
    'loggers': {
        'aegent': {
            'handlers': ['console'],
            'level': settings.log_level.upper(),
            'propagate': False,
        }
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('aegent')

_SENSITIVE_KEYWORDS = (
    'password',
    'password_hash',
    'authorization',
    'token',
    'access_token',
    'refresh_token',
    'api_key',
    'secret',
    'cookie',
    'set-cookie',
    'connection_string',
    'jwt',
)

REQUEST_LIMIT_PATHS = {
    '/api/v1/auth/login',
    '/api/v1/auth/register',
    '/api/v1/auth/refresh',
}

_rate_buckets: dict[tuple[str, str], list[float]] = defaultdict(list)


def _redact_sensitive_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, nested_value in value.items():
            lowered = str(key).lower()
            if any(keyword in lowered for keyword in _SENSITIVE_KEYWORDS):
                redacted[key] = '[REDACTED]'
            else:
                redacted[key] = _redact_sensitive_value(nested_value)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_sensitive_value(item) for item in value)
    return value


def _normalize_request_id(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    candidate = raw_value.strip()
    if not candidate:
        return None
    if len(candidate) > 128:
        return None
    if re.fullmatch(r'[A-Za-z0-9._\-]+', candidate):
        return candidate
    return None


def _log_http_event(request: Request, response: Any, started_at: float, request_id: str) -> None:
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    log_payload = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'level': 'INFO',
        'request_id': request_id,
        'method': request.method,
        'path': request.url.path,
        'status_code': getattr(response, 'status_code', 500),
        'duration_ms': duration_ms,
    }
    logger.info('http_request', extra=log_payload)


def _is_rate_limited(request: Request) -> bool:
    if request.url.path not in REQUEST_LIMIT_PATHS:
        return False
    client_ip = request.client.host if request.client else 'unknown'
    window = time.monotonic()
    bucket_key = (request.url.path, client_ip)
    bucket = _rate_buckets[bucket_key]
    bucket[:] = [timestamp for timestamp in bucket if window - timestamp < 60]
    if len(bucket) >= settings.rate_limit_requests_per_minute:
        return True
    bucket.append(window)
    return False


def _validation_error_details(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for error in errors:
        item = dict(error)
        if 'input' in item:
            item['input'] = '[REDACTED]' if item['input'] is not None else None
        if 'ctx' in item and isinstance(item['ctx'], dict):
            cleaned_ctx: dict[str, Any] = {}
            for key, value in item['ctx'].items():
                if isinstance(value, Exception):
                    cleaned_ctx[key] = str(value)
                else:
                    cleaned_ctx[key] = _redact_sensitive_value(value)
            item['ctx'] = cleaned_ctx
        sanitized.append(item)
    return sanitized


app = FastAPI(
    title='Aegent',
    description='Security and Governance for Autonomous AI Agents',
    version='0.1.0',
    docs_url='/docs',
    redoc_url='/redoc',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)


@app.middleware('http')
async def request_security_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    request_id = _normalize_request_id(request.headers.get('x-request-id')) or uuid4().hex
    request.state.request_id = request_id
    response_headers = {
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'X-Frame-Options': 'DENY',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        'Content-Security-Policy': "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:5173 http://127.0.0.1:5173; font-src 'self' data:",
        'X-Request-ID': request_id,
    }

    if request.headers.get('content-length') is not None:
        try:
            content_length = int(request.headers['content-length'])
        except ValueError:
            content_length = 0
        if content_length > settings.max_request_size_bytes:
            payload = {'detail': 'Request body exceeds the configured size limit.'}
            response = JSONResponse(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, content=payload)
            for key, value in response_headers.items():
                response.headers.setdefault(key, value)
            _log_http_event(request, response, started_at, request_id)
            return response

    if _is_rate_limited(request):
        payload = {'detail': 'Too many requests. Please try again later.'}
        response = JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, content=payload)
        for key, value in response_headers.items():
            response.headers.setdefault(key, value)
        _log_http_event(request, response, started_at, request_id)
        return response

    try:
        response = await call_next(request)
    except Exception:
        logger.exception('request_failed', extra={'request_id': request_id, 'method': request.method, 'path': request.url.path})
        raise

    for key, value in response_headers.items():
        response.headers.setdefault(key, value)
    response.headers['X-Request-ID'] = request_id
    _log_http_event(request, response, started_at, request_id)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={'detail': _validation_error_details(exc.errors())},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        detail = _redact_sensitive_value(detail)
    if exc.status_code >= 500:
        detail = 'An unexpected error occurred.'
    return JSONResponse(status_code=exc.status_code, content={'detail': detail})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception('unhandled_exception', extra={'request_id': getattr(request.state, 'request_id', None)})
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={'detail': 'An unexpected error occurred.'})


app.include_router(auth_router, prefix='/api/v1')
app.include_router(organizations_router, prefix='/api/v1')
app.include_router(agents_router, prefix='/api/v1')
app.include_router(policies_router, prefix='/api/v1')
app.include_router(approvals_router, prefix='/api/v1')
app.include_router(audit_router, prefix='/api/v1')


@app.get('/')
def root():
    return {
        'name': 'Aegent',
        'version': '0.1.0',
        'status': 'running',
    }


@app.get('/health')
def health():
    return {
        'status': 'healthy',
        'app': settings.app_name,
        'environment': settings.app_env,
    }


@app.get('/health/database')
def database_health():
    try:
        with SessionLocal() as session:
            session.execute(text('SELECT 1'))
        return {
            'status': 'healthy',
            'database': 'reachable',
        }
    except Exception as exc:
        logger.exception('database_health_check_failed')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                'status': 'unhealthy',
                'database': 'unreachable',
                'message': 'Database connection is unavailable.',
            },
        ) from exc
