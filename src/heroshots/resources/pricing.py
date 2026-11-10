"""Public price list and quotes (API key or portal JWT, /api/v1/pricing)."""

from __future__ import annotations

from typing import Any, Optional

from . import Resource, compact


class Pricing(Resource):
    def catalog(self) -> dict[str, Any]:
        """GET /api/v1/pricing/catalog -> image/video prices for the caller's plan."""
        return self._get("/api/v1/pricing/catalog")

    def quote(self, call_type: str, **payload: Any) -> dict[str, Any]:
        """POST /api/v1/pricing/quote -> cost of one generation before running it.

        ``call_type`` is ``"image"``, ``"video"`` or ``"background"``. For videos
        pass ``duration_seconds``; usage-rights fields are accepted as well.
        """
        return self._post("/api/v1/pricing/quote", json={"call_type": call_type, **payload})

    def video_packages_catalog(self) -> dict[str, Any]:
        """GET /api/v1/pricing/video-packages/catalog -> volume package tiers."""
        return self._get("/api/v1/pricing/video-packages/catalog")

    def video_packages_quote(
        self,
        tier: str,
        *,
        usage_rights: Optional[list[dict[str, Any]]] = None,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /api/v1/pricing/video-packages/quote (``tier``: starter | growth | scale)."""
        body = compact({"tier": tier, "usage_rights": usage_rights, **payload})
        return self._post("/api/v1/pricing/video-packages/quote", json=body)

    def usage_rights_rules(self) -> dict[str, Any]:
        """GET /api/v1/pricing/usage-rights/rules -> allowed usage-rights combinations."""
        return self._get("/api/v1/pricing/usage-rights/rules")
