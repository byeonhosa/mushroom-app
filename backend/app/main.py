from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from .api import router
from .config import settings
from .errors import DomainError, is_unique_violation

app = FastAPI(title=settings.app_name, version=settings.app_version)

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


app.include_router(router, prefix="/api")
