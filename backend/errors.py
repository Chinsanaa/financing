"""Shared error handling for route handlers.

Route handlers wrap their logic in try/except. HTTPExceptions raised inside
must pass through untouched (a 404 is a 404, not a 500), and unexpected
exceptions must be logged server-side but NEVER leak internals (str(e)) to
the client.
"""
import logging

from fastapi import HTTPException

logger = logging.getLogger("financing")
logging.basicConfig(level=logging.INFO)


def internal_error(e: Exception, context: str = "") -> HTTPException:
    """Log the real exception, return a generic 500 for the client."""
    logger.exception("Internal error%s: %s", f" in {context}" if context else "", e)
    return HTTPException(status_code=500, detail="Internal server error")
