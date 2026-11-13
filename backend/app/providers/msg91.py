"""MSG91 Flow API adapter for DLT-approved transactional SMS templates."""

import httpx

from app.config import settings

MSG91_FLOW_URL = "https://control.msg91.com/api/v5/flow"


def send_transactional_sms(*, recipient: str, title: str, message: str) -> str:
    """Submit one recipient to a configured MSG91 Flow template.

    The configured DLT-approved template must contain the matching VAR1 and
    VAR2 placeholders. MSG91 expects the Indian country code without a plus.
    """
    if not settings.sms_notifications_enabled:
        raise RuntimeError("SMS notifications are disabled")
    if not settings.msg91_auth_key or not settings.msg91_flow_template_id:
        raise RuntimeError("MSG91 auth key and Flow template ID must be configured")

    mobile = recipient.strip().replace("+", "")
    if not mobile.startswith("91") or len(mobile) != 12 or not mobile.isdigit():
        raise RuntimeError("SMS recipient is not a valid normalized Indian mobile number")

    response = httpx.post(
        MSG91_FLOW_URL,
        headers={
            "accept": "application/json",
            "authkey": settings.msg91_auth_key,
            "content-type": "application/json",
        },
        json={
            "template_id": settings.msg91_flow_template_id,
            "short_url": "0",
            "recipients": [{
                "mobiles": mobile,
                "VAR1": title[:120],
                "VAR2": message[:450],
            }],
        },
        timeout=20.0,
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("MSG91 returned a non-JSON response") from exc

    if not isinstance(payload, dict) or str(payload.get("type", "")).lower() != "success":
        provider_message = payload.get("message", "unknown provider response") if isinstance(payload, dict) else "unknown provider response"
        raise RuntimeError(f"MSG91 rejected the SMS request: {str(provider_message)[:300]}")

    return str(payload.get("message", "")) or ""
