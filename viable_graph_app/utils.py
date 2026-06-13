import logging
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)
RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


def verify_recaptcha(token: str, remoteip: Optional[str] = None, timeout: int = 5) -> dict:
    """
    Verify a reCAPTCHA token against Google's siteverify endpoint.

    Returns the parsed JSON response from Google on success, or a dictionary
    containing `success: False` and an `error-codes` list on failure.
    """
    if not token:
        return {"success": False, "error-codes": ["missing-input-response"]}

    secret = getattr(settings, "RECAPTCHA_SECRET_KEY", "")
    if not secret:
        logger.warning("RECAPTCHA_SECRET_KEY is not set in settings")
        return {"success": False, "error-codes": ["missing-input-secret"]}

    data = {"secret": secret, "response": token}
    if remoteip:
        data["remoteip"] = remoteip

    try:
        resp = requests.post(RECAPTCHA_VERIFY_URL, data=data, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.exception("reCAPTCHA verification request failed")
        return {"success": False, "error-codes": ["request-failed"], "exception": str(exc)}
