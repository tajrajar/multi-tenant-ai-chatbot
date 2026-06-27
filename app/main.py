"""
Main FastAPI application entry point.

Sets up:
- CORS (only trusted origins allowed)
- Security headers middleware
- A global exception handler that never leaks internal errors in production
- A /health endpoint to verify the server is running
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.security import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the app starts, and once when it shuts down."""
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)


# CORS: only allow requests from the origins listed in ALLOWED_ORIGINS
# (never "*" — that would let any website call this API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Adds X-Content-Type-Options, X-Frame-Options, HSTS headers to every response
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches any unhandled error in the app.

    - Always logs the full error on the server (for debugging).
    - In production, returns a generic message to the client
      (never leaks stack traces, file paths, or internal details).
    - In development, returns the real error message to help debugging.
    """
    logger.exception("Unhandled exception occurred", exc_info=exc)

    if settings.ENVIRONMENT == "production":
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.get("/health")
async def health_check():
    """Simple endpoint to confirm the server is alive and responding."""
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
    }