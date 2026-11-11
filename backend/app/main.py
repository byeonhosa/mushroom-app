from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from . import api, api_auth, auth
from .config import settings
from .db import SessionLocal
from .errors import DomainError, is_unique_violation


@asynccontextmanager
async def lifespan(app: FastAPI):
    # First administrator from configuration, when no user exists (USR-3).
    # The deploy workflow normally does this with `python -m app.manage
    # bootstrap-admin`, so that the password is not left in the environment
    # of the long-running container; this covers local stacks, where the
    # values sit in .env. A database that is not migrated yet is not an error
    # here: the readiness check reports it.
    if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
        try:
            with SessionLocal() as db:
                outcome = auth.ensure_bootstrap_admin(db)
            if outcome == "created":
                print("bootstrap: first administrator created")
        except (SQLAlchemyError, ValueError) as exc:
            print(f"bootstrap: first administrator not created ({exc.__class__.__name__})")
    yield


# The interactive API documentation describes every route to anyone who asks.
# It is a development aid; production does not serve it.
_docs = {"docs_url": None, "redoc_url": None, "openapi_url": None} if settings.is_production else {}

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    **_docs,
    # Every state-changing request must come from the app's own pages.
    dependencies=[Depends(auth.enforce_same_origin)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Last line of defence: a constraint the route did not anticipate.

    The request is answered with a sentence, never with a server error, and
    the same way on PostgreSQL and on SQLite (SRS RUN-7).
    """
    if is_unique_violation(exc):
        return JSONResponse(status_code=409, content={"detail": "A record with that code or name already exists."})
    return JSONResponse(
        status_code=400,
        content={"detail": "The request refers to a record that does not exist or breaks a rule of the data."},
    )


# Without a session: health checks and the way in.
app.include_router(api.public_router, prefix="/api")
app.include_router(api_auth.public_router, prefix="/api")
# With a session.
app.include_router(api_auth.account_router, prefix="/api")
app.include_router(api_auth.users_router, prefix="/api")
app.include_router(api.router, prefix="/api")
