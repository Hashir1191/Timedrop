"""MSG91-managed OTP send and verification adapter."""

import httpx

from app.config import settings

SEND_OTP_URL = "https://control.msg91.com/api/v5/otp"
VERIFY_OTP_URL = "https://control.msg91.com/api/v5/otp/verify"


def _mobile_for_msg91(phone_number: str) -> str:
    mobile = phone_number.strip().replace("+", "")
    if len(mobile) != 12 or not mobile.startswith("91") or not mobile.isdigit():
        raise ValueError("Phone number must be a normalized Indian mobile number")
    return mobile


def send_otp(phone_number: str) -> str:
    """Ask MSG91 to generate and send an OTP; return its request ID."""
    if not settings.msg91_auth_key or not settings.msg91_otp_template_id:
        raise RuntimeError("MSG91 OTP auth key and OTP template ID are not configured")
    response = httpx.post(
        SEND_OTP_URL,
        params={
            "template_id": settings.msg91_otp_template_id,
            "mobile": _mobile_for_msg91(phone_number),
            "otp_length": 6,
            "otp_expiry": settings.phone_otp_expire_minutes,
            "unicode": 0,
        },
        headers={"authkey": settings.msg91_auth_key, "content-type": "application/json"},
        json={},
        timeout=20.0,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"MSG91 OTP send failed with HTTP {exc.response.status_code}") from None
    except httpx.RequestError:
        raise RuntimeError("MSG91 OTP service could not be reached") from None
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("MSG91 OTP API returned a non-JSON response") from exc
    if not isinstance(payload, dict) or str(payload.get("type", "")).lower() != "success":
        detail = payload.get("message", "unknown provider response") if isinstance(payload, dict) else "unknown provider response"
        raise RuntimeError(f"MSG91 could not send OTP: {str(detail)[:250]}")
    return str(payload.get("request_id", ""))


def verify_otp(phone_number: str, code: str) -> bool:
    """Verify the user-entered code with MSG91; HTTP 200 can still mean failure."""
    if not settings.msg91_auth_key:
        raise RuntimeError("MSG91 OTP auth key is not configured")
    response = httpx.get(
        VERIFY_OTP_URL,
        params={"mobile": _mobile_for_msg91(phone_number), "otp": code},
        headers={"authkey": settings.msg91_auth_key, "accept": "application/json"},
        timeout=20.0,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"MSG91 OTP verification failed with HTTP {exc.response.status_code}") from None
    except httpx.RequestError:
        raise RuntimeError("MSG91 OTP service could not be reached") from None
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("MSG91 OTP verification API returned a non-JSON response") from exc
    return isinstance(payload, dict) and str(payload.get("type", "")).lower() == "success"
