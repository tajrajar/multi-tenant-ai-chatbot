"""
Security utilities for the application.

Contains:
- A helper to generate cryptographically secure secret keys.
- Middleware that adds standard security headers to every HTTP response.
"""

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def generate_secret_key(length: int = 64) -> str:
    """
    Generate a cryptographically secure secret key.

    Args:
        length: Number of random bytes to use as entropy source.

    Returns:
        A URL-safe secret string suitable for use as SECRET_KEY.
    """
    return secrets.token_urlsafe(length)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds standard security headers to every response:

    - X-Content-Type-Options: stops browsers from guessing content types
      (prevents certain MIME-sniffing attacks).
    - X-Frame-Options: prevents the site from being embedded in an iframe
      (protects against clickjacking).
    - Strict-Transport-Security: tells browsers to only use HTTPS
      (only added when the request actually came in over HTTPS).
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"

        if request.url.scheme == "https":
            response.headers[
                "Strict-Transport-Security"
            ] = "max-age=31536000; includeSubDomains"

        return response