"""HeroShots SDK - high-level Python client for the StudioHero platform (JWT/API key auth)."""

from __future__ import annotations

from .client import HeroShotsClient
from .errors import (
    ApiError,
    AuthError,
    ConflictError,
    ForbiddenError,
    HeroShotsError,
    InternalError,
    NotFoundError,
    PayloadTooLargeError,
    ProviderError,
    QuotaExceededError,
    RateLimitError,
    ServiceUnavailableError,
    TokenExpiredError,
    ValidationError,
)
from ._polling import TimeoutError as PollTimeoutError

__version__ = "0.2.5"

# Friendly alias.
Client = HeroShotsClient

__all__ = [
    "Client",
    "HeroShotsClient",
    "HeroShotsError",
    "ApiError",
    "AuthError",
    "TokenExpiredError",
    "ValidationError",
    "NotFoundError",
    "ForbiddenError",
    "ConflictError",
    "QuotaExceededError",
    "PayloadTooLargeError",
    "ProviderError",
    "ServiceUnavailableError",
    "RateLimitError",
    "InternalError",
    "PollTimeoutError",
    "__version__",
]
