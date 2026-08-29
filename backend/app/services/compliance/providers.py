from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.compliance import IdentifierVerification
from app.utils.time import utcnow

logger = get_logger(__name__)

GSTINCHECK_BASE = "https://sheet.gstincheck.co.in/check"
SANDBOX_TEST_BASE = "https://test-api.sandbox.co.in"
SANDBOX_LIVE_BASE = "https://api.sandbox.co.in"
SANDBOX_PAN_REASON = "Government bid compliance check of an uploaded Udyam certificate"
_PAN_DATE = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$")
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def verify_pan(
    value: str | None,
    format_status: str,
    settings: Settings,
    holder_name: str | None = None,
    registration_date: str | None = None,
) -> IdentifierVerification:
    blocked = _precheck("pan", value, format_status)
    if blocked:
        return blocked
    assert value is not None
    api_key = settings.pan_api_key.strip()
    api_secret = settings.pan_api_secret.strip()
    if not api_key or not api_secret:
        return _unavailable("pan", value, "PAN verification could not be completed because Sandbox API key and secret are not set.")
    name = (holder_name or "").strip()
    dob = _to_sandbox_date(registration_date)
    if len(name) < 2 or not dob:
        return IdentifierVerification(
            kind="pan",
            extracted_value=value,
            format_status="valid",
            outcome="error",
            limitation=(
                "Sandbox PAN verification requires a holder or enterprise name and a date of birth "
                "or incorporation (DD/MM/YYYY). Those fields were not both available on the certificate, "
                "so the PAN API was not called with placeholder identity data."
            ),
        )
    base = _sandbox_base(settings)
    try:
        with httpx.Client(timeout=settings.pan_api_timeout_seconds) as client:
            token = _sandbox_token(client, base, api_key, api_secret)
            if not token:
                return _unavailable("pan", value, "PAN verification could not be completed because Sandbox authentication failed.")
            response = client.post(
                f"{base}/kyc/pan/verify",
                headers={
                    "Authorization": token,
                    "x-api-key": api_key,
                    "x-api-version": "1.0",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "@entity": "in.co.sandbox.kyc.pan_verification.request",
                    "pan": value,
                    "name_as_per_pan": name,
                    "date_of_birth": dob,
                    "consent": "Y",
                    "reason": SANDBOX_PAN_REASON,
                },
            )
    except httpx.HTTPError:
        logger.warning("pan_verification_network_error")
        return _unavailable("pan", value, "PAN verification could not be completed because the configured verification service was unavailable.")
    return _from_http("pan", value, response, _interpret_sandbox_pan)


def verify_gstin(value: str | None, format_status: str, settings: Settings) -> IdentifierVerification:
    blocked = _precheck("gstin", value, format_status)
    if blocked:
        return blocked
    assert value is not None
    api_key = settings.gst_in_check.strip()
    if not api_key:
        return _unavailable(
            "gstin",
            value,
            "GSTIN verification could not be completed because GST_IN_CHECK is not set.",
        )
    url = f"{GSTINCHECK_BASE}/{quote(value, safe='')}"
    try:
        with httpx.Client(timeout=settings.gst_api_timeout_seconds) as client:
            response = client.get(
                url,
                headers={
                    "Accept": "application/json",
                    "x-api-key": api_key,
                },
            )
    except httpx.HTTPError:
        logger.warning("gstin_verification_network_error")
        return _unavailable(
            "gstin",
            value,
            "GSTIN verification could not be completed because the configured verification service was unavailable.",
        )
    return _from_http("gstin", value, response, _interpret_gstincheck)


def _precheck(kind: str, value: str | None, format_status: str) -> IdentifierVerification | None:
    if format_status == "not_extracted" or not value:
        return IdentifierVerification(
            kind=kind,  # type: ignore[arg-type]
            extracted_value=None,
            format_status="not_extracted",
            outcome="not_extracted",
            limitation=f"{kind.upper()} was not extracted, so the verification service was not called.",
        )
    if format_status == "invalid":
        return IdentifierVerification(
            kind=kind,  # type: ignore[arg-type]
            extracted_value=value,
            format_status="invalid",
            outcome="format_invalid",
            limitation=f"Extracted {kind.upper()} failed format validation. The verification service was not called.",
        )
    return None


def _sandbox_base(settings: Settings) -> str:
    if settings.pan_api_base_url.strip():
        return settings.pan_api_base_url.strip().rstrip("/")
    env = settings.pan_sandbox_env.strip().lower()
    key = settings.pan_api_key.strip()
    if env in {"live", "prod", "production"} or key.startswith("key_live"):
        return SANDBOX_LIVE_BASE
    return SANDBOX_TEST_BASE


def _sandbox_token(client: httpx.Client, base: str, api_key: str, api_secret: str) -> str | None:
    response = client.post(
        f"{base}/authenticate",
        headers={
            "x-api-key": api_key,
            "x-api-secret": api_secret,
            "x-api-version": "1.0",
            "Accept": "application/json",
        },
    )
    if response.status_code >= 400:
        logger.warning("pan_sandbox_auth_http_error status=%s", response.status_code)
        return None
    try:
        body = response.json()
    except ValueError:
        return None
    token = None
    if isinstance(body, dict):
        data = body.get("data") if isinstance(body.get("data"), dict) else body
        if isinstance(data, dict):
            token = data.get("access_token")
    return token.strip() if isinstance(token, str) and token.strip() else None


def _to_sandbox_date(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.strip()
    iso = _ISO_DATE.match(text)
    if iso:
        return f"{iso.group(3)}/{iso.group(2)}/{iso.group(1)}"
    match = _PAN_DATE.match(text)
    if not match:
        return None
    day, month, year = match.group(1), match.group(2), match.group(3)
    if len(year) == 2:
        year = f"20{year}"
    return f"{int(day):02d}/{int(month):02d}/{year}"


def _from_http(kind: str, value: str, response: httpx.Response, interpreter) -> IdentifierVerification:
    if response.status_code >= 500 or response.status_code in {401, 403, 429}:
        logger.warning("%s_verification_http_error status=%s", kind, response.status_code)
        return _unavailable(
            kind,
            value,
            f"{kind.upper()} verification could not be completed because the configured verification service was unavailable.",
            provider_status=str(response.status_code),
        )
    try:
        body = response.json()
    except ValueError:
        return IdentifierVerification(
            kind=kind,  # type: ignore[arg-type]
            extracted_value=value,
            format_status="valid",
            outcome="error",
            provider_status=str(response.status_code),
            limitation=f"{kind.upper()} verification returned an unusable response.",
            verified_at=utcnow(),
        )
    passed, failed, details = interpreter(body, response.status_code)
    if passed:
        return IdentifierVerification(
            kind=kind,  # type: ignore[arg-type]
            extracted_value=value,
            format_status="valid",
            outcome="passed",
            provider_status="verified",
            details=details,
            verified_at=utcnow(),
        )
    if failed:
        return IdentifierVerification(
            kind=kind,  # type: ignore[arg-type]
            extracted_value=value,
            format_status="valid",
            outcome="failed",
            provider_status="not_verified",
            details=details,
            verified_at=utcnow(),
            limitation=f"The configured {kind.upper()} verification service did not verify this identifier.",
        )
    return IdentifierVerification(
        kind=kind,  # type: ignore[arg-type]
        extracted_value=value,
        format_status="valid",
        outcome="error",
        provider_status=str(response.status_code),
        details=details,
        verified_at=utcnow(),
        limitation=f"{kind.upper()} verification returned an ambiguous response.",
    )


def _interpret_sandbox_pan(body: Any, status_code: int) -> tuple[bool, bool, dict[str, Any]]:
    details = _safe_details(body)
    if not isinstance(body, dict):
        return False, False, details
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    status_text = str((data or {}).get("status") or body.get("status") or "").lower()
    if status_text == "valid":
        return True, False, details
    if status_text == "invalid":
        return False, True, details
    if status_code in {400, 404, 422}:
        return False, False, details
    if status_code == 200 and data:
        return True, False, details
    return False, False, details


def _interpret_gstincheck(body: Any, status_code: int) -> tuple[bool, bool, dict[str, Any]]:
    details = _safe_details(body)
    if not isinstance(body, dict):
        return False, False, details
    if isinstance(body.get("message"), str) and "message" not in details:
        details["message"] = body["message"]
    message = str(body.get("message") or body.get("error") or "").lower()
    if any(token in message for token in ("api key", "unauthorized", "invalid key", "expired")):
        return False, False, details
    payload = body.get("data")
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    if isinstance(payload, dict):
        details = {**details, **_safe_details({"data": payload})}
        status = str(payload.get("sts") or payload.get("status") or "").lower()
        if status in {"cancelled", "inactive", "suspended", "cancelled suo-moto"}:
            return False, True, details
        if payload.get("lgnm") or payload.get("tradeNam") or payload.get("gstin") or status in {"active", "provisional"}:
            return True, False, details
    if body.get("flag") is True:
        return True, False, details
    if body.get("flag") is False or body.get("error") is True:
        return False, True, details
    if status_code in {400, 404, 422}:
        return False, True, details
    return False, False, details


def _unavailable(kind: str, value: str | None, limitation: str, provider_status: str | None = None) -> IdentifierVerification:
    return IdentifierVerification(
        kind=kind,  # type: ignore[arg-type]
        extracted_value=value,
        format_status="valid",
        outcome="unavailable",
        provider_status=provider_status,
        limitation=limitation,
        verified_at=utcnow(),
    )


def _safe_details(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        return {}
    blocked = {"key", "token", "secret", "authorization", "password", "api_key", "access_token"}
    data = body.get("data") if isinstance(body.get("data"), dict) else body
    if isinstance(data.get("data"), dict):
        data = data["data"]
    aliases = {
        "lgnm": "legal_name",
        "tradeNam": "trade_name",
        "sts": "gstin_status",
        "rgdt": "registration_date",
        "gstin": "gstin",
        "pan": "pan",
        "name": "name",
        "full_name": "full_name",
        "legal_name": "legal_name",
        "trade_name": "trade_name",
        "status": "status",
        "category": "category",
        "remarks": "remarks",
        "aadhaar_seeding_status": "aadhaar_seeding_status",
        "name_as_per_pan_match": "name_as_per_pan_match",
        "date_of_birth_match": "date_of_birth_match",
        "message": "message",
        "state": "state",
        "registration_date": "registration_date",
    }
    allowed: dict[str, Any] = {}
    for source, target in aliases.items():
        if source in data and isinstance(data[source], (str, int, float, bool)) and target not in blocked:
            allowed[target] = data[source]
    for key in list(allowed):
        if key.lower() in blocked:
            allowed.pop(key, None)
    return allowed
