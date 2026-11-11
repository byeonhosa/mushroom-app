"""Password hashing and session tokens. No request or database code here."""

import hashlib
import secrets

import bcrypt

from .config import settings

PASSWORD_MIN_LENGTH = 10
# bcrypt reads at most 72 bytes of a password. A longer one is refused rather
# than silently cut short.
PASSWORD_MAX_BYTES = 72


class PasswordPolicyError(ValueError):
    """The proposed password does not meet the policy. The message is for the user."""


def validate_new_password(password: str, *, email: str | None = None) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise PasswordPolicyError(f"Use a password of at least {PASSWORD_MIN_LENGTH} characters.")
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise PasswordPolicyError(f"Use a password of at most {PASSWORD_MAX_BYTES} characters.")
    if not password.strip():
        raise PasswordPolicyError("A password cannot be only spaces.")
    if email and password.strip().lower() == email.strip().lower():
        raise PasswordPolicyError("The password cannot be the same as the email address.")


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.password_hash_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > PASSWORD_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("ascii"))
    except ValueError:
        # A stored value that is not a bcrypt hash can never match.
        return False


# Checked when the email is unknown, so that an unknown address takes as long
# to refuse as a wrong password.
_DUMMY_HASH: str | None = None


def burn_password_check(password: str) -> None:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password(secrets.token_urlsafe(16))
    verify_password(password, _DUMMY_HASH)


def new_session_token() -> str:
    """256 bits from the operating system's generator, URL-safe."""
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
