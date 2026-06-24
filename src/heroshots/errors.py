"""Exception hierarchy for the HeroShots SDK.

Every structured API error returns ``{"success": false, "error": {"code", "message",
"details"}}`` (see backend ``api_error_response.py``). :func:`error_from_response`
maps the ``code`` to a specific exception class so callers can ``except`` precisely.
"""

from __future__ import annotations

from typing import Any, Optional


class HeroShotsError(Exception):
    """Base class for every error raised by the SDK."""


class ApiError(HeroShotsError):
    """An error returned by the HeroShots API.

    Attributes:
        code: machine-readable error code (e.g. ``"validation_error"``).
        message: human-readable message.
        status: HTTP status code.
        details: optional structured details dict.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        status: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        prefix = f"[{self.status} {self.code}] " if self.code else ""
        return f"{prefix}{self.message}"


class AuthError(ApiError):
    """Missing/invalid bearer token or unknown user."""


class TokenExpiredError(AuthError):
    """The portal JWT expired. There is no refresh endpoint - re-login to renew."""


class ValidationError(ApiError):
    """The request payload failed validation."""


class NotFoundError(ApiError):
    """The requested resource does not exist (or a job expired)."""


class ForbiddenError(ApiError):
    """Authenticated but not allowed (plan/scope/tenant gating)."""


class ConflictError(ApiError):
    """Resource conflict (e.g. email already registered)."""


class QuotaExceededError(ApiError):
    """Credit/quota limit reached."""


class PayloadTooLargeError(ApiError):
    """Uploaded payload exceeded the size limit."""


class ProviderError(ApiError):
    """An upstream generation provider failed (also raised for failed jobs)."""


class ServiceUnavailableError(ApiError):
    """A backend dependency is not configured or temporarily unavailable."""


class RateLimitError(ApiError):
    """HTTP 429 - too many requests. Back off and retry."""


class InternalError(ApiError):
    """Unexpected server error (HTTP 5xx)."""


# code -> exception class. Codes mirror backend api_error_response.py CODE_* values.
_CODE_MAP: dict[str, type[ApiError]] = {
    "missing_api_key": AuthError,
    "missing_authorization": AuthError,
    "missing_bearer_token": AuthError,
    "invalid_api_key": AuthError,
    "invalid_token": AuthError,
    "invalid_or_expired_token": AuthError,
    "unauthorized": AuthError,
    "user_not_found": AuthError,
    "token_expired": TokenExpiredError,
    "validation_error": ValidationError,
    "not_found": NotFoundError,
    "resource_gone": NotFoundError,
    "forbidden": ForbiddenError,
    "plan_not_allowed": ForbiddenError,
    "insufficient_scope": ForbiddenError,
    "conflict": ConflictError,
    "quota_exceeded": QuotaExceededError,
    "payload_too_large": PayloadTooLargeError,
    "provider_error": ProviderError,
    "service_unavailable": ServiceUnavailableError,
    "pricing_not_configured": ServiceUnavailableError,
    "stripe_not_configured": ServiceUnavailableError,
    "internal_error": InternalError,
}


def error_from_response(status: int, body: Any) -> ApiError:
    """Build the most specific :class:`ApiError` for an HTTP error response."""
    code = None
    message = None
    details = None
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            code = err.get("code")
            message = err.get("message")
            details = err.get("details")
        elif isinstance(err, str):
            message = err
        message = message or body.get("message")
    if status == 429:
        cls: type[ApiError] = RateLimitError
    elif code and code in _CODE_MAP:
        cls = _CODE_MAP[code]
    elif status and status >= 500:
        cls = InternalError
    elif status == 404:
        cls = NotFoundError
    elif status in (401, 403):
        cls = AuthError
    else:
        cls = ApiError
    return cls(
        message or f"HTTP {status}",
        code=code,
        status=status,
        details=details if isinstance(details, dict) else None,
    )
