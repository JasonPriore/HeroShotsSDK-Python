"""Agency: managed brands (agency API key or JWT, /api/v1/agency).

To generate *as* a managed brand, set ``managed_user_id`` on the client
(``client.with_managed_user(...)``) and call the normal resources.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from . import Resource, compact

RelId = Union[int, str]
_BASE = "/api/v1/agency/managed-clients"


class Agency(Resource):
    def clients(self) -> dict[str, Any]:
        """GET /api/v1/agency/managed-clients -> ``{clients: [...]}``."""
        return self._get(_BASE)

    def client(self, relationship_id: RelId) -> dict[str, Any]:
        """GET /api/v1/agency/managed-clients/<id> -> relationship, wallet, generations."""
        return self._get(f"{_BASE}/{relationship_id}")

    def invite_client(self, invite_email: str, **terms: Any) -> dict[str, Any]:
        """POST /api/v1/agency/managed-clients/invite -> invite a brand by email.

        Optional markup terms: ``markup_terms`` or the flat ``image_fixed``,
        ``image_pct``, ``video_short_fixed``... fields.
        """
        return self._post(f"{_BASE}/invite", json={"invite_email": invite_email, **terms})

    def create_client(
        self,
        company_name: str,
        company_country: str,
        legal_consents: dict[str, Any],
        *,
        vat_number: Optional[str] = None,
        **terms: Any,
    ) -> dict[str, Any]:
        """POST /api/v1/agency/managed-clients/direct -> create a brand without invite."""
        body = compact(
            {
                "company_name": company_name,
                "company_country": company_country,
                "legal_consents": legal_consents,
                "vat_number": vat_number,
                **terms,
            }
        )
        return self._post(f"{_BASE}/direct", json=body)

    def update_client(self, relationship_id: RelId, *, access_mode: str) -> dict[str, Any]:
        """PATCH /api/v1/agency/managed-clients/<id> (``access_mode``: autonomous | read_only)."""
        return self._patch(f"{_BASE}/{relationship_id}", json={"access_mode": access_mode})

    def resend_invite(self, relationship_id: RelId) -> dict[str, Any]:
        """POST /api/v1/agency/managed-clients/<id>/resend-invite."""
        return self._post(f"{_BASE}/{relationship_id}/resend-invite")

    def claim_invite(self, relationship_id: RelId, invite_email: str) -> dict[str, Any]:
        """POST /api/v1/agency/managed-clients/<id>/claim-invite -> portal access link."""
        return self._post(f"{_BASE}/{relationship_id}/claim-invite", json={"invite_email": invite_email})

    def topup(self, relationship_id: RelId, amount: float) -> dict[str, Any]:
        """POST /api/v1/agency/managed-clients/<id>/topup -> move EUR from agency wallet."""
        return self._post(f"{_BASE}/{relationship_id}/topup", json={"amount": amount})

    def request_termination(self, relationship_id: RelId, reason: str) -> dict[str, Any]:
        """POST /api/v1/agency/managed-clients/<id>/termination."""
        return self._post(f"{_BASE}/{relationship_id}/termination", json={"reason": reason})

    def respond_termination(
        self, relationship_id: RelId, accept: bool, *, reason: Optional[str] = None
    ) -> dict[str, Any]:
        """POST /api/v1/agency/managed-clients/<id>/termination/respond."""
        body = compact({"accept": bool(accept), "response_reason": reason})
        return self._post(f"{_BASE}/{relationship_id}/termination/respond", json=body)

    def cancel_termination(self, relationship_id: RelId) -> dict[str, Any]:
        """POST /api/v1/agency/managed-clients/<id>/termination/cancel."""
        return self._post(f"{_BASE}/{relationship_id}/termination/cancel")
