"""Brand side of an agency relationship (brand API key or JWT, /api/v1/brand)."""

from __future__ import annotations

from typing import Any, Optional

from . import Resource, compact


class Brand(Resource):
    def accept_manager_invite(self, token: str) -> dict[str, Any]:
        """POST /api/v1/brand/manager-invite/<token>/accept."""
        return self._post(f"/api/v1/brand/manager-invite/{token}/accept")

    def reject_manager_invite(self, token: str) -> dict[str, Any]:
        """POST /api/v1/brand/manager-invite/<token>/reject."""
        return self._post(f"/api/v1/brand/manager-invite/{token}/reject")

    def manager_relationship(self) -> dict[str, Any]:
        """GET /api/v1/brand/manager-relationship -> current managing agency, if any."""
        return self._get("/api/v1/brand/manager-relationship")

    def manager_relationships(self) -> dict[str, Any]:
        """GET /api/v1/brand/manager-relationships -> relationship history."""
        return self._get("/api/v1/brand/manager-relationships")

    def request_termination(self, reason: str) -> dict[str, Any]:
        """POST /api/v1/brand/manager-relationship/termination."""
        return self._post("/api/v1/brand/manager-relationship/termination", json={"reason": reason})

    def respond_termination(self, accept: bool, *, reason: Optional[str] = None) -> dict[str, Any]:
        """POST /api/v1/brand/manager-relationship/termination/respond."""
        body = compact({"accept": bool(accept), "response_reason": reason})
        return self._post("/api/v1/brand/manager-relationship/termination/respond", json=body)

    def cancel_termination(self) -> dict[str, Any]:
        """POST /api/v1/brand/manager-relationship/termination/cancel."""
        return self._post("/api/v1/brand/manager-relationship/termination/cancel")
