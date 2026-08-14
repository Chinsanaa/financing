"""Transactional email via Resend's HTTP API.

Backend has no MCP access at runtime, so this calls Resend directly rather
than through any connector. Fails soft everywhere: an unset RESEND_API_KEY,
a network error, or a non-2xx response all just log and return — a failed
or skipped email must never break the caller's request/background task.
"""
import httpx

from config import settings
from errors import logger

RESEND_API_URL = "https://api.resend.com/emails"
FROM_ADDRESS = "alerts@financing.app"  # placeholder; must match a domain verified in Resend


async def send_alert_email(to_email: str, subject: str, body: str) -> None:
    """Send a plain-text alert email. No-ops if RESEND_API_KEY is unset."""
    if not settings.resend_api_key:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                RESEND_API_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": FROM_ADDRESS,
                    "to": [to_email],
                    "subject": subject,
                    "text": body,
                },
            )
            if response.status_code >= 400:
                logger.error("Resend send failed (%s): %s", response.status_code, response.text)
    except Exception as e:
        logger.exception("Resend send raised: %s", e)
