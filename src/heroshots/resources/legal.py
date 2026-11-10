"""BYO compliance documents (portal JWT only, /api/legal/byo).

Real-person ("bring your own") avatars need the company manleva (once per
brand) and a signed liberatoria + identity document for each person.
"""

from __future__ import annotations

import os
from typing import Any, Optional, Union

from . import Resource, compact

Dest = Optional[Union[str, os.PathLike]]


class Legal(Resource):
    def byo_status(self) -> dict[str, Any]:
        """GET /api/legal/byo/status -> manleva status and ``can_create_byo``."""
        return self._get("/api/legal/byo/status")

    def manleva_template(self, dest: Dest = None) -> Union[bytes, str]:
        """GET /api/legal/byo/template -> company manleva template (DOCX)."""
        return self._client.download("/api/legal/byo/template", dest)

    def liberatoria_template(self, dest: Dest = None) -> Union[bytes, str]:
        """GET /api/legal/byo/liberatoria-template -> per-person liberatoria template (DOCX)."""
        return self._client.download("/api/legal/byo/liberatoria-template", dest)

    def upload_manleva(
        self,
        tenant_id: Union[int, str],
        file: Any,
        *,
        signed_by_name: Optional[str] = None,
        signed_by_role: Optional[str] = None,
        document_version: Optional[str] = None,
        template_download_reference: Optional[str] = None,
    ) -> dict[str, Any]:
        """POST /api/legal/byo/<tenant_id>/manleva (multipart) -> signed company manleva."""
        fields = compact(
            {
                "signed_by_name": signed_by_name,
                "signed_by_role": signed_by_role,
                "document_version": document_version,
                "template_download_reference": template_download_reference,
            }
        )
        return self._post(
            f"/api/legal/byo/{tenant_id}/manleva",
            data=fields,
            files=self._client._multipart_file(file),
        )

    def attach_liberatoria(
        self,
        tenant_id: Union[int, str],
        avatar_id: Union[int, str],
        *,
        release_doc_url: str,
        id_doc_url: str,
        model_email: str,
        model_dob: str,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /api/legal/byo/<tenant_id>/avatars -> attach a signed liberatoria to an avatar.

        Upload the signed release and the ID with ``client.uploads.consent_document``
        first and pass the returned URLs.
        """
        body = {
            "avatar_id": int(avatar_id),
            "release_doc_url": release_doc_url,
            "id_doc_url": id_doc_url,
            "model_email": model_email,
            "model_dob": model_dob,
            **payload,
        }
        return self._post(f"/api/legal/byo/{tenant_id}/avatars", json=body)
