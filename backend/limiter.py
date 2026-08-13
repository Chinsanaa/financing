"""Shared slowapi Limiter instance.

Route modules import `limiter` from here (not `Limiter(...)` per-module) so
every `@limiter.limit(...)` decorator across the app shares one counter.
main.py attaches this same instance to `app.state.limiter` for the
exception handler.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
