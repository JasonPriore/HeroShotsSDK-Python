"""Account endpoints on the public API (API key or portal JWT)."""

from __future__ import annotations

from typing import Any

from . import Resource


class Account(Resource):
    def me(self) -> dict[str, Any]:
        """GET /api/v1/me -> ``{user, credits_remaining: {hs_credits, currency_credit}}``."""
        return self._get("/api/v1/me")

    def health(self) -> dict[str, Any]:
        """GET /api/v1/health -> service health (no auth needed)."""
        return self._get("/api/v1/health", auth=False)
