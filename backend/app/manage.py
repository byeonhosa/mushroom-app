"""Server-side commands. Run inside the API container:

    python -m app.manage bootstrap-admin
        Create the first administrator from BOOTSTRAP_ADMIN_EMAIL and
        BOOTSTRAP_ADMIN_PASSWORD when no user exists. Safe to run on every
        deploy: it does nothing once any user exists.

    python -m app.manage smoke-session
        Print a session token, valid for two minutes, for the first active
        administrator. The deploy workflow uses it for one signed-in request
        and then signs out, so that the check never depends on anyone's
        password. Exits 3 when there is no administrator yet.

    python -m app.manage reset-password --email someone@example.com
        Set a new password from the NEW_PASSWORD environment variable and
        sign that user out everywhere. This is the way back in when the only
        administrator has lost a password.

Nothing here prints a password. A session token is printed only by
smoke-session, to the caller that asked for it.
"""

import argparse
import os
import sys
from datetime import timedelta

from sqlalchemy import select

from . import auth, models, security
from .db import SessionLocal


def bootstrap_admin() -> int:
    with SessionLocal() as db:
        try:
            outcome = auth.ensure_bootstrap_admin(db)
        except security.PasswordPolicyError as exc:
            print(f"bootstrap-admin: password refused: {exc}", file=sys.stderr)
            return 2
    messages = {
        "exists": "bootstrap-admin: users already exist, nothing to do",
        "created": "bootstrap-admin: first administrator created",
        "missing": (
            "bootstrap-admin: no user exists and BOOTSTRAP_ADMIN_EMAIL / "
            "BOOTSTRAP_ADMIN_PASSWORD are not set. Nobody can sign in yet."
        ),
    }
    print(messages[outcome])
    return 0


def smoke_session() -> int:
    with SessionLocal() as db:
        admin = db.execute(
            select(models.User)
            .where(models.User.role == models.UserRole.ADMIN.value, models.User.is_active.is_(True))
            .order_by(models.User.user_id)
        ).scalars().first()
        if admin is None:
            print("smoke-session: no active administrator", file=sys.stderr)
            return 3
        token = auth.create_session(db, admin, lifetime=timedelta(minutes=2))
        db.commit()
    print(token)
    return 0


def reset_password(email: str) -> int:
    new_password = os.environ.get("NEW_PASSWORD", "")
    if not new_password:
        print("reset-password: set NEW_PASSWORD in the environment", file=sys.stderr)
        return 2
    with SessionLocal() as db:
        user = auth.get_user_by_email(db, email)
        if user is None:
            print("reset-password: no user with that email", file=sys.stderr)
            return 3
        try:
            security.validate_new_password(new_password, email=user.email)
        except security.PasswordPolicyError as exc:
            print(f"reset-password: password refused: {exc}", file=sys.stderr)
            return 2
        user.password_hash = security.hash_password(new_password)
        user.must_change_password = True
        user.is_active = True
        auth.revoke_sessions(db, user.user_id)
        db.commit()
    print("reset-password: password set; the user must choose a new one at next sign-in")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.manage", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("bootstrap-admin")
    commands.add_parser("smoke-session")
    reset = commands.add_parser("reset-password")
    reset.add_argument("--email", required=True)
    args = parser.parse_args(argv)

    if args.command == "bootstrap-admin":
        return bootstrap_admin()
    if args.command == "smoke-session":
        return smoke_session()
    return reset_password(args.email)


if __name__ == "__main__":
    raise SystemExit(main())
