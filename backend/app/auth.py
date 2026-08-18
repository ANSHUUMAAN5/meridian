"""JWT issue and verify.

The token carries `tid` (tenant id). That claim is the only thing that decides
which rows a request can see, so it is never taken from a header, query string,
or request body — only from a signed token.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config import get_settings


class AuthError(Exception):
    """Raised when a token is missing, malformed, expired, or wrongly signed."""


def create_token(*, tenant_id: str, user_id: str, role: str = "agent") -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=s.jwt_ttl_minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    s = get_settings()
    try:
        claims = jwt.decode(
            token,
            s.jwt_secret,
            algorithms=[s.jwt_algorithm],
            options={"require": ["exp", "sub", "tid"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise AuthError("token expired") from e
    except jwt.InvalidTokenError as e:
        raise AuthError("invalid token") from e

    # Defence in depth: a token whose tenant claim is not a UUID must never
    # reach set_config, where it would simply select no rows and look like an
    # empty tenant rather than an attack.
    tid = claims.get("tid")
    if not isinstance(tid, str) or len(tid) != 36:
        raise AuthError("invalid tenant claim")
    return claims
