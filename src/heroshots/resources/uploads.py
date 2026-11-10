"""File uploads -> hosted URLs (portal JWT only)."""

from __future__ import annotations

from typing import Any, Optional

from . import Resource

# Allowed upload folders (backend sensitive_uploads.py).
FOLDERS = (
    "subjects",
    "products",
    "avatars",
    "avatar-consents",
    "references",
    "background",
    "body_posture",
    "reference-videos",
)


class Uploads(Resource):
    def image(self, file: Any, folder: Optional[str] = None) -> dict[str, Any]:
        """POST /upload/image (multipart ``file``) -> ``{public_url, filename, folder}``.

        ``file`` is a path, bytes or open binary file; ``folder`` one of
        :data:`FOLDERS` (or omitted).
        """
        files = self._client._multipart_file(file)
        data = {"folder": folder} if folder else None
        return self._post("/upload/image", files=files, data=data)

    def consent_document(self, file: Any) -> dict[str, Any]:
        """Upload a signed release or ID document (PDF, DOCX, JPEG, PNG, WebP).

        Stored privately and bound to your account; pass the returned URL as
        ``release_doc_url`` / ``id_doc_url``.
        """
        return self.image(file, folder="avatar-consents")

    def reference_audio(self, file: Any) -> dict[str, Any]:
        """POST /upload/reference-audio -> hosted MP3/WAV for video lip-sync."""
        return self._post("/upload/reference-audio", files=self._client._multipart_file(file))
