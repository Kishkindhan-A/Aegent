from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, require_roles
from app.database.session import get_db
from app.models import AuthSession, Organization, User
from app.models.enums import ActorType, AuditEventType, OrganizationStatus, UserRole, UserStatus
from app.schemas.auth import (
    AuthStatusResponse,
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.security.passwords import hash_password, verify_password
from app.security.tokens import create_access_token, decode_token, generate_refresh_token, hash_token, now_utc

router = APIRouter(prefix='/auth', tags=['auth'])


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _normalize_slug(value: str | None) -> str | None:
    if value is None:
        return None
    slug = value.strip().lower().replace(' ', '-')
    return slug or None


def _active_user_query(db: Session, email: str, organization_id: UUID | None = None, organization_slug: str | None = None):
    stmt = select(User).where(User.email == email.lower())
    if organization_id is not None:
        stmt = stmt.where(User.organization_id == organization_id)
    elif organization_slug:
        stmt = stmt.join(Organization, User.organization_id == Organization.id).where(Organization.slug == organization_slug)
    return stmt


@router.post('/register', status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    normalized_email = normalize_email(str(request.owner_email))
    if not normalized_email:
        raise HTTPException(status_code=400, detail='Email is required.')
    normalized_slug = _normalize_slug(request.organization_slug or request.organization_name)
    if not normalized_slug:
        raise HTTPException(status_code=400, detail='Organization slug is required.')

    existing_org = db.execute(select(Organization).where(Organization.slug == normalized_slug)).scalar_one_or_none()
    if existing_org is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Organization slug already exists.')

    organization = Organization(name=request.organization_name.strip(), slug=normalized_slug, status=OrganizationStatus.ACTIVE)
    db.add(organization)
    db.flush()

    hashed = hash_password(request.password.get_secret_value())
    user = User(
        organization_id=organization.id,
        email=normalized_email,
        password_hash=hashed,
        full_name=request.owner_full_name.strip(),
        role=UserRole.OWNER,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()

    refresh_token = generate_refresh_token()
    refresh_hash = hash_token(refresh_token)
    session = AuthSession(
        user_id=user.id,
        organization_id=organization.id,
        token_hash=refresh_hash,
        expires_at=now_utc() + timedelta(days=7),
    )
    db.add(session)
    db.flush()
    db.commit()
    db.refresh(user)
    db.refresh(organization)

    access_token = create_access_token(user.id, organization.id, user.role)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type='bearer',
        expires_in=15 * 60,
        user=CurrentUserResponse.model_validate(user),
    )


@router.post('/login', response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    normalized_email = normalize_email(str(request.email))
    if not normalized_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials.')
    organization_slug = _normalize_slug(request.organization_slug)
    organization_id = request.organization_id

    if organization_slug is None and organization_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Organization context is required.')

    stmt = select(User).join(Organization, User.organization_id == Organization.id)
    stmt = stmt.where(User.email == normalized_email)
    if organization_id is not None:
        stmt = stmt.where(User.organization_id == organization_id)
    elif organization_slug:
        stmt = stmt.where(Organization.slug == organization_slug)
    user = db.execute(stmt).scalar_one_or_none()

    if user is None or not verify_password(request.password.get_secret_value(), user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials.')

    if user.status not in {UserStatus.ACTIVE}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Account is not active.')

    org = db.get(Organization, user.organization_id)
    if org is None or org.status != OrganizationStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization is not active.')

    access_token = create_access_token(user.id, user.organization_id, user.role)
    refresh_token = generate_refresh_token()
    refresh_hash = hash_token(refresh_token)

    session = AuthSession(
        user_id=user.id,
        organization_id=user.organization_id,
        token_hash=refresh_hash,
        expires_at=now_utc() + timedelta(days=7),
    )
    db.add(session)
    db.flush()
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type='bearer',
        expires_in=15 * 60,
        user=CurrentUserResponse.model_validate(user),
    )


@router.get('/me', response_model=CurrentUserResponse)
def get_current_user_endpoint(current_user: User = Depends(get_current_active_user)) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)


@router.post('/refresh', response_model=TokenResponse)
def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token = request.refresh_token.get_secret_value().strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token is required.')

    token_hash = hash_token(token)
    with db.begin():
        session = db.execute(
            select(AuthSession)
            .where(AuthSession.token_hash == token_hash)
            .with_for_update()
            .order_by(AuthSession.created_at.desc())
        ).scalar_one_or_none()
        if session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token is invalid.')

        if session.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token has been revoked.')

        if session.expires_at < now_utc():
            session.revoked_at = now_utc()
            db.flush()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token has expired.')

        user = db.get(User, session.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found.')
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User account is not active.')

        organization = db.get(Organization, session.organization_id)
        if organization is None or organization.status != OrganizationStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization is not active.')

        session.revoked_at = now_utc()
        session.last_used_at = now_utc()

        new_refresh = generate_refresh_token()
        new_refresh_hash = hash_token(new_refresh)
        rotated_session = AuthSession(
            user_id=user.id,
            organization_id=user.organization_id,
            token_hash=new_refresh_hash,
            expires_at=now_utc() + timedelta(days=7),
        )
        db.add(rotated_session)
        db.flush()

        access_token = create_access_token(user.id, user.organization_id, user.role)
        response = TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            token_type='bearer',
            expires_in=15 * 60,
            user=CurrentUserResponse.model_validate(user),
        )

    return response


@router.post('/logout', response_model=AuthStatusResponse)
def logout(request: LogoutRequest, db: Session = Depends(get_db)) -> AuthStatusResponse:
    token = request.refresh_token.get_secret_value().strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Refresh token is required.')

    token_hash = hash_token(token)
    with db.begin():
        session = db.execute(
            select(AuthSession)
            .where(AuthSession.token_hash == token_hash)
            .with_for_update()
        ).scalar_one_or_none()
        if session is None:
            return AuthStatusResponse(status='success', message='Refresh token already invalid.')

        if session.revoked_at is None:
            session.revoked_at = now_utc()
        db.flush()
        return AuthStatusResponse(status='success', message='Logged out successfully.')


@router.get('/health/roles')
def health_roles(current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER))):
    return {'status': 'ok', 'role': current_user.role.value, 'organization_id': str(current_user.organization_id)}
