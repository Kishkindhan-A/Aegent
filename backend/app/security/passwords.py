from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def validate_password_input(password: str) -> None:
    if password is None or password.strip() == '':
        raise ValueError('Password cannot be blank.')
    if len(password) < 8:
        raise ValueError('Password must be at least 8 characters long.')
    if len(password) > 128:
        raise ValueError('Password must be at most 128 characters long.')


def hash_password(password: str) -> str:
    validate_password_input(password)
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHash, VerificationError, ValueError):
        return False
