"""Image generation (JWT-or-API-key on /api/v1, portal candidates flow)."""

from __future__ import annotations

from typing import Any, Callable, Optional

from . import Resource
from .. import _polling


class Images(Resource):
    def generate(
        self,
        product_image_url: str,
        subject_image_url: Optional[str] = None,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /api/v1/image/generate (async) -> ``{generation_id, status, ...}``.

        Local file paths are auto-uploaded. Provide ``subject_image_url``/``avatar_id``
        unless ``still_life=True``.
        """
        body = {
            "product_image_url": self._resolve_image(product_image_url, "products"),
            **payload,
        }
        if subject_image_url is not None:
            body["subject_image_url"] = self._resolve_image(subject_image_url, "subjects")
        return self._post("/api/v1/image/generate", json=body)

    def candidates(
        self,
        product_image_url: str,
        subject_image_url: Optional[str] = None,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /api/auth/image/generate/candidates -> persistent candidate batch."""
        body = {
            "product_image_url": self._resolve_image(product_image_url, "products"),
            **payload,
        }
        if subject_image_url is not None:
            body["subject_image_url"] = self._resolve_image(subject_image_url, "subjects")
        return self._post("/api/auth/image/generate/candidates", json=body)

    def select_candidate(self, token: str, **payload: Any) -> dict[str, Any]:
        """POST /api/auth/image/generate/candidates/<token>/select."""
        return self._post(f"/api/auth/image/generate/candidates/{token}/select", json=payload)

    def status(self, generation_id: str) -> dict[str, Any]:
        """GET /api/v1/image/status/<generation_id>."""
        return self._get(f"/api/v1/image/status/{generation_id}")

    def download(self, log_id: str) -> dict[str, Any]:
        """GET /api/v1/image/<log_id>/download."""
        return self._get(f"/api/v1/image/{log_id}/download")

    def wait(
        self,
        generation_id: str,
        *,
        interval: float = 3.0,
        timeout: float = 600.0,
        on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """Poll image status until ``succeeded``/``failed``."""
        return _polling.wait(
            lambda: self.status(generation_id),
            terminal_ok=_polling.MEDIA_OK,
            terminal_fail=_polling.MEDIA_FAIL,
            interval=interval,
            timeout=timeout,
            on_progress=on_progress,
        )
