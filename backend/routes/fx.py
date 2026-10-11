"""FX metadata for the home-currency picker (contract API_V5 §3.1).

Static: no DB read and no network call. Auth is still required (the global
AuthMiddleware covers every non-public path).
"""
from fastapi import APIRouter

import fx

router = APIRouter()


@router.get("/currencies")
def list_currencies():
    """Selectable home currencies, most likely first. CNY is the base and is
    not selectable."""
    return {
        "base": fx.BASE,
        "source": fx.SOURCE_NAME,
        "supported": [{"code": code, "name": name} for code, name in fx.SUPPORTED.items()],
    }
