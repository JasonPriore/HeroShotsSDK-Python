"""Avatars (JWT-or-API-key, /api/v1/avatar).

Read-only listing of your own + default avatars, plus on-demand generation.
(Editing/deleting avatars is intentionally not exposed.)
"""

from __future__ import annotations

from typing import Any

from . import Resource


class Avatars(Resource):
    def list(self, **params: Any) -> dict[str, Any]:
        """GET /api/v1/avatar/list -> your own and the default avatars."""
        return self._get("/api/v1/avatar/list", params=params or None)

    def get(self, avatar_id: int) -> dict[str, Any]:
        """GET /api/v1/avatar/<id>."""
        return self._get(f"/api/v1/avatar/{avatar_id}")

    def generate(self, **payload: Any) -> dict[str, Any]:
        """POST /api/v1/avatar/generate -> request a new avatar."""
        return self._post("/api/v1/avatar/generate", json=payload)
