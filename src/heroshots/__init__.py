"""HeroShots SDK - Python client for the HeroShots / StudioHero API (API key or portal JWT)."""

from __future__ import annotations

from .client import HeroShotsClient
from .errors import (
    ApiError,
    AuthError,
    BillingError,
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
    "BillingError",
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
