"""File uploads -> hosted public URLs (portal JWT)."""

from __future__ import annotations

from typing import Any, BinaryIO, Optional

from . import Resource

# Allowed upload folders (backend frontend_uploads.py).
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
    def image(self, file: "str | BinaryIO", folder: Optional[str] = None) -> dict[str, Any]:
        """POST /upload/image (multipart ``file``) -> ``{public_url, filename, folder}``.

        ``folder`` must be one of :data:`FOLDERS` (or omitted).
        """
        files = self._client._multipart_file(file)
        data = {"folder": folder} if folder else None
        return self._post("/upload/image", files=files, data=data)
