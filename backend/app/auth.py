"""Who is making this request, and may they?

A request is made by a *principal*. Today there is one kind, a signed-in user
identified by the session cookie. The website integration (roadmap WP-9) adds
a second kind, a service identified by a bearer token, by appending one
function to `AUTHENTICATORS`. Routes never look at cookies or headers
themselves: they depend on `require_user` or `require_admin` (and, later,
`require_service`), so a service token can never satisfy an operator route.

Also here: the origin check on state-changing requests, sign-in rate limiting,
session creation and removal, and creation of the first administrator.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from . import models, security
from .config import settings
from .db import get_db

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# Writing last_seen_at on every request would turn each page view into a
# database write. Once in this many minutes is enough to keep a session alive.
_TOUCH_INTERVAL = timedelta(minutes=5)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def normalize_email(email: str) -> str:
    return email.strip().lower()


# --------------------------------------------------------------- principals

@dataclass(frozen=True)
class Principal:
    """The party a request acts for."""

    kind: str  # "user" today; "service" from WP-9
    user: models.User | None = None
    session: models.UserSession | None = None


def _user_from_session_cookie(request: Request, db: Session) -> Principal | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    session = db.execute(
        select(models.UserSession).where(models.UserSession.token_hash == security.token_digest(token))
    ).scalar_one_or_none()
    if session is None:
        return None

    now = _now()
    idle_deadline = _aware(session.last_seen_at) + timedelta(days=settings.session_idle_days)
    if now >= _aware(session.expires_at) or now >= idle_deadline or not session.user.is_active:
        db.delete(session)
        db.commit()
        return None

    if now - _aware(session.last_seen_at) >= _TOUCH_INTERVAL:
        session.last_seen_at = now
        db.commit()
    return Principal(kind="user", user=session.user, session=session)


# Tried in order; the first to recognise the request wins. WP-9 appends the
# bearer-token authenticator for the website here.
AUTHENTICATORS: list[Callable[[Request, Session], Principal | None]] = [_user_from_session_cookie]


def get_principal(request: Request, db: Session = Depends(get_db)) -> Principal | None:
    for authenticate in AUTHENTICATORS:
        principal = authenticate(request, db)
        if principal is not None:
            if principal.user is not None:
                # Picked up by crud_status._record_bag_event (USR-4).
                db.info["user_id"] = principal.user.user_id
            return principal
    return None


def require_user(principal: Principal | None = Depends(get_principal)) -> models.User:
    """Any signed-in person. Every route but the health checks and sign-in depends on this."""
    if principal is None or principal.kind != "user" or principal.user is None:
        raise HTTPException(401, "Sign in to continue.")
    return principal.user


def require_admin(user: models.User = Depends(require_user)) -> models.User:
    if user.role != models.UserRole.ADMIN.value:
        raise HTTPException(403, "Only an administrator can do that.")
    return user


# ------------------------------------------------------------- origin check

def _request_hosts(request: Request) -> set[str]:
    """Host names this request was addressed to, as the browser saw them.

    Behind the proxy the browser's host arrives in X-Forwarded-Host; the API's
    own port is published on the loopback interface only, so nothing but the
    proxy and the server itself can set these headers.
    """
    hosts = set()
    for header in ("host", "x-forwarded-host"):
        value = request.headers.get(header)
        if value:
            hosts.update(part.strip().lower() for part in value.split(",") if part.strip())
    return hosts


def enforce_same_origin(request: Request) -> None:
    """Refuse a state-changing request that did not come from the app's own pages.

    The session cookie is SameSite=Lax, which already keeps it off cross-site
    POSTs in current browsers. This is the second lock: the Origin header (or
    Referer) must name this app. A request with neither is refused; a browser
    always sends one on a POST.
    """
    if request.method in SAFE_METHODS:
        return
    source = request.headers.get("origin") or request.headers.get("referer")
    if not source or source == "null":
        raise HTTPException(403, "This request did not come from the app. Reload the page and try again.")
    parts = urlsplit(source)
    origin = f"{parts.scheme}://{parts.netloc}".lower()
    if origin in {o.lower() for o in settings.trusted_origins}:
        return
    if parts.netloc.lower() in _request_hosts(request):
        return
    raise HTTPException(403, "This request did not come from the app. Reload the page and try again.")


# ----------------------------------------------------------------- sessions

def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _is_public_address(ip: str | None) -> bool:
    if not ip:
        return False
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (address.is_private or address.is_loopback or address.is_link_local)


def is_secure_request(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    return forwarded == "https" or request.url.scheme == "https"


def refuse_plaintext_sign_in(request: Request) -> None:
    """SEC-1: in production a password never crosses the internet unencrypted.

    Plain HTTP is still accepted from the server itself and from private
    addresses, which is how the deploy checks and an SSH tunnel reach it.
    """
    if settings.is_production and not is_secure_request(request) and _is_public_address(client_ip(request)):
        raise HTTPException(
            403,
            "Sign-in needs an encrypted connection. Open the app at its https address.",
        )


def create_session(db: Session, user: models.User, request: Request | None = None, *, lifetime: timedelta | None = None) -> str:
    """Start a session and return the token to put in the cookie."""
    token = security.new_session_token()
    now = _now()
    db.add(
        models.UserSession(
            token_hash=security.token_digest(token),
            user_id=user.user_id,
            created_at=now,
            last_seen_at=now,
            expires_at=now + (lifetime or timedelta(days=settings.session_max_days)),
            user_agent=(request.headers.get("user-agent") or "")[:300] if request else None,
            ip_address=client_ip(request) if request else None,
        )
    )
    # Housekeeping that needs no schedule: expired rows go when someone signs in.
    db.execute(delete(models.UserSession).where(models.UserSession.expires_at < now))
    return token


def set_session_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_max_days * 24 * 3600,
        httponly=True,
        secure=is_secure_request(request),
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        httponly=True,
        secure=is_secure_request(request),
        samesite="lax",
        path="/",
    )


def revoke_sessions(db: Session, user_id: int, *, keep_session_id: int | None = None) -> None:
    statement = delete(models.UserSession).where(models.UserSession.user_id == user_id)
    if keep_session_id is not None:
        statement = statement.where(models.UserSession.session_id != keep_session_id)
    db.execute(statement)


# ------------------------------------------------------------ rate limiting

def _recent_failures(db: Session, column, value: str, since: datetime) -> int:
    return db.execute(
        select(func.count())
        .select_from(models.LoginAttempt)
        .where(column == value, models.LoginAttempt.succeeded.is_(False), models.LoginAttempt.attempted_at >= since)
    ).scalar_one()


def check_login_rate_limit(db: Session, email: str, ip: str | None) -> None:
    """Refuse further attempts after too many failures. Raises 429."""
    now = _now()
    window_start = now - timedelta(minutes=settings.login_window_minutes)

    # A successful sign-in wipes the slate for that address.
    last_success = db.execute(
        select(func.max(models.LoginAttempt.attempted_at)).where(
            models.LoginAttempt.email == email, models.LoginAttempt.succeeded.is_(True)
        )
    ).scalar_one()
    email_since = max(window_start, _aware(last_success)) if last_success else window_start

    too_many = _recent_failures(db, models.LoginAttempt.email, email, email_since) >= settings.login_max_failures_per_email
    if not too_many and ip:
        too_many = (
            _recent_failures(db, models.LoginAttempt.ip_address, ip, window_start)
            >= settings.login_max_failures_per_ip
        )
    if too_many:
        raise HTTPException(
            429,
            f"Too many failed sign-in attempts. Wait {settings.login_window_minutes} minutes and try again.",
            headers={"Retry-After": str(settings.login_window_minutes * 60)},
        )


def record_login_attempt(db: Session, email: str, ip: str | None, *, succeeded: bool) -> None:
    now = _now()
    db.add(models.LoginAttempt(email=email[:254], ip_address=ip, attempted_at=now, succeeded=succeeded))
    # Attempts older than a day serve no purpose.
    db.execute(delete(models.LoginAttempt).where(models.LoginAttempt.attempted_at < now - timedelta(days=1)))


# ------------------------------------------------------------------- users

def count_users(db: Session) -> int:
    return db.execute(select(func.count()).select_from(models.User)).scalar_one()


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.execute(
        select(models.User).where(models.User.email == normalize_email(email))
    ).scalar_one_or_none()


def active_admin_count(db: Session) -> int:
    return db.execute(
        select(func.count())
        .select_from(models.User)
        .where(models.User.role == models.UserRole.ADMIN.value, models.User.is_active.is_(True))
    ).scalar_one()


def ensure_bootstrap_admin(db: Session, email: str | None = None, password: str | None = None) -> str:
    """Create the first administrator when the users table is empty.

    Returns what happened as a short word for the log: `exists` (there is
    already at least one user, nothing changed), `missing` (no user and no
    credentials supplied), or `created`. Never logs the password.
    """
    if count_users(db) > 0:
        return "exists"
    email = normalize_email(email if email is not None else settings.bootstrap_admin_email)
    password = password if password is not None else settings.bootstrap_admin_password
    if not email or not password:
        return "missing"
    security.validate_new_password(password, email=email)
    db.add(
        models.User(
            email=email,
            display_name=settings.bootstrap_admin_name.strip() or "Owner",
            role=models.UserRole.ADMIN.value,
            password_hash=security.hash_password(password),
            is_active=True,
            # The first password travelled through deployment settings. The
            # screens ask for a new one at first sign-in.
            must_change_password=True,
        )
    )
    db.commit()
    return "created"
