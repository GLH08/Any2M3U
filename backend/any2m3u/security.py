from __future__ import annotations
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


def new_pull_token() -> str:
    return secrets.token_urlsafe(32)
