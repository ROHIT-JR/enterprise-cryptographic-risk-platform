from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from backend.app.config import Settings, get_settings


class TokenError(ValueError):
    pass


def _encode_segment(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_segment(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_token(
    *,
    user_id: str,
    organization_id: str,
    role: str,
    token_type: Literal["access", "refresh"],
    settings: Settings | None = None,
) -> tuple[str, datetime, str]:
    config = settings or get_settings()
    now = datetime.now(UTC)
    lifetime = (
        timedelta(minutes=config.access_token_minutes)
        if token_type == "access"
        else timedelta(days=config.refresh_token_days)
    )
    expires = now + lifetime
    jti = str(uuid4())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "org": organization_id,
        "role": role,
        "type": token_type,
        "jti": jti,
        "iss": config.jwt_issuer,
        "aud": config.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    signing_input = ".".join(
        (
            _encode_segment(json.dumps(header, separators=(",", ":")).encode()),
            _encode_segment(json.dumps(payload, separators=(",", ":")).encode()),
        )
    )
    signature = hmac.new(
        config.secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{signing_input}.{_encode_segment(signature)}", expires, jti


def decode_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    config = settings or get_settings()
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        header = json.loads(_decode_segment(encoded_header))
        payload = json.loads(_decode_segment(encoded_payload))
    except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise TokenError("Malformed token") from exc
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise TokenError("Malformed token claims")
    if header != {"alg": "HS256", "typ": "JWT"}:
        raise TokenError("Unsupported token header")
    signing_input = f"{encoded_header}.{encoded_payload}"
    expected = hmac.new(
        config.secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
    ).digest()
    try:
        supplied = _decode_segment(encoded_signature)
    except ValueError as exc:
        raise TokenError("Malformed signature") from exc
    if not hmac.compare_digest(expected, supplied):
        raise TokenError("Invalid signature")
    required = {"sub", "org", "role", "type", "jti", "iat", "exp"}
    if not required.issubset(payload):
        raise TokenError("Token is missing required claims")
    if not isinstance(payload["exp"], int) or not isinstance(payload["iat"], int):
        raise TokenError("Token timestamps are invalid")
    now = int(datetime.now(UTC).timestamp())
    if payload["exp"] <= now:
        raise TokenError("Token expired")
    if payload["iat"] > now + 60:
        raise TokenError("Token issue time is invalid")
    if payload.get("iss") != config.jwt_issuer or payload.get("aud") != config.jwt_audience:
        raise TokenError("Invalid token issuer or audience")
    return payload


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
