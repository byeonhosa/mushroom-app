"""Sign-in, sign-out, the signed-in user's own account, and user management."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import auth, models, schemas, security
from .db import get_db

# Reachable without a session: the way in, and whether a way in exists yet.
public_router = APIRouter(prefix="/auth", tags=["auth"])
# Needs a session.
account_router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(auth.require_user)])
# Needs an administrator.
users_router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(auth.require_admin)])

_BAD_CREDENTIALS = "The email or password is not right."


@public_router.get("/status", response_model=schemas.AuthStatusOut)
def auth_status(db: Session = Depends(get_db)):
    """Whether anyone can sign in at all. False until the first administrator exists."""
    return {"setup_required": auth.count_users(db) == 0}


@public_router.post("/login", response_model=schemas.CurrentUserOut)
def login(payload: schemas.LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    auth.refuse_plaintext_sign_in(request)
    email = auth.normalize_email(payload.email)
    ip = auth.client_ip(request)
    auth.check_login_rate_limit(db, email, ip)

    user = auth.get_user_by_email(db, email)
    if user is None or not user.is_active:
        # Spend the same time as a real check, and give the same answer.
        security.burn_password_check(payload.password)
        password_ok = False
    else:
        password_ok = security.verify_password(payload.password, user.password_hash)

    auth.record_login_attempt(db, email, ip, succeeded=password_ok)
    if not password_ok:
        db.commit()
        raise HTTPException(401, _BAD_CREDENTIALS)

    user.last_login_at = datetime.now(timezone.utc)
    token = auth.create_session(db, user, request)
    db.commit()
    auth.set_session_cookie(response, request, token)
    return user


@public_router.post("/logout", status_code=204)
def logout(request: Request, response: Response, principal: auth.Principal | None = Depends(auth.get_principal), db: Session = Depends(get_db)):
    """Ends the session if there is one. Never an error: signing out twice is fine."""
    if principal is not None and principal.session is not None:
        db.delete(principal.session)
        db.commit()
    auth.clear_session_cookie(response, request)
    response.status_code = 204
    return response


@account_router.get("/me", response_model=schemas.CurrentUserOut)
def me(user: models.User = Depends(auth.require_user)):
    return user


@account_router.patch("/me", response_model=schemas.CurrentUserOut)
def update_me(payload: schemas.AccountUpdate, user: models.User = Depends(auth.require_user), db: Session = Depends(get_db)):
    """The name shown in the menu and beside the events this person enters."""
    name = payload.display_name.strip()
    if not name:
        raise HTTPException(400, "Enter a name.")
    user.display_name = name
    db.commit()
    db.refresh(user)
    return user


@account_router.post("/change-password", response_model=schemas.CurrentUserOut)
def change_password(
    payload: schemas.ChangePasswordIn,
    principal: auth.Principal = Depends(auth.get_principal),
    db: Session = Depends(get_db),
):
    user = principal.user
    if not security.verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, "The current password is not right.")
    if payload.new_password == payload.current_password:
        raise HTTPException(400, "Choose a password different from the current one.")
    try:
        security.validate_new_password(payload.new_password, email=user.email)
    except security.PasswordPolicyError as exc:
        raise HTTPException(400, str(exc))
    user.password_hash = security.hash_password(payload.new_password)
    user.must_change_password = False
    # Every other browser signed in with the old password is signed out.
    auth.revoke_sessions(db, user.user_id, keep_session_id=principal.session.session_id if principal.session else None)
    db.commit()
    db.refresh(user)
    return user


# ------------------------------------------------------------ user management

@users_router.get("", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.execute(select(models.User).order_by(models.User.display_name, models.User.user_id)).scalars().all()


@users_router.post("", response_model=schemas.UserOut, status_code=201)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    email = auth.normalize_email(payload.email)
    if auth.get_user_by_email(db, email) is not None:
        raise HTTPException(409, "A user with that email already exists.")
    try:
        security.validate_new_password(payload.password, email=email)
    except security.PasswordPolicyError as exc:
        raise HTTPException(400, str(exc))
    user = models.User(
        email=email,
        display_name=payload.display_name.strip(),
        role=payload.role,
        password_hash=security.hash_password(payload.password),
        is_active=True,
        # The administrator chose this password; the person it is for picks their own.
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@users_router.patch("/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    payload: schemas.UserUpdate,
    acting: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    changes = payload.model_dump(exclude_unset=True)

    demoting = "role" in changes and changes["role"] != models.UserRole.ADMIN.value
    deactivating = changes.get("is_active") is False
    if user.user_id == acting.user_id and (demoting or deactivating):
        raise HTTPException(400, "You cannot remove your own administrator access. Ask another administrator.")
    if (
        user.role == models.UserRole.ADMIN.value
        and user.is_active
        and (demoting or deactivating)
        and auth.active_admin_count(db) <= 1
    ):
        raise HTTPException(400, "This is the only administrator. Make another user an administrator first.")

    if "display_name" in changes:
        user.display_name = changes["display_name"].strip()
    if "role" in changes:
        user.role = changes["role"]
    if "is_active" in changes:
        user.is_active = changes["is_active"]
    if changes.get("password"):
        try:
            security.validate_new_password(changes["password"], email=user.email)
        except security.PasswordPolicyError as exc:
            raise HTTPException(400, str(exc))
        user.password_hash = security.hash_password(changes["password"])
        user.must_change_password = True

    # A deactivated user, or one whose password was reset, is signed out everywhere.
    if deactivating or changes.get("password"):
        auth.revoke_sessions(db, user.user_id)
    db.commit()
    db.refresh(user)
    return user
