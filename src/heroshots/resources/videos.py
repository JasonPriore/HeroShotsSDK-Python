"""Short video generation (API key or portal JWT, /api/v1/video)."""

from __future__ import annotations

import os
from typing import Any, Callable, Optional, Union

from . import Resource
from .. import _polling


class Videos(Resource):
    def generate(self, image_url: Optional[str] = None, **payload: Any) -> dict[str, Any]:
        """POST /api/v1/video/generate -> ``{video_id, status, ...}`` (async).

        Common fields: ``duration_seconds`` (15 / 30 / longer in 15 s blocks),
        ``custom_prompt``, ``product_image_url``, ``subject_image_url`` or
        ``avatar_id``, ``script``, ``tts_voice_id``, ``language_code``, ``ratio``,
        ``resolution``, ``reference_video_url``, usage rights. Local file paths in
        ``image_url``, ``product_image_url`` and ``subject_image_url`` are
        auto-uploaded (portal JWT only).
        """
        body = dict(payload)
        if image_url is not None:
            body["image_url"] = self._resolve_image(image_url, "products")
        for key, folder in (("product_image_url", "products"), ("subject_image_url", "subjects")):
            if key in body:
                body[key] = self._resolve_image(body[key], folder)
        return self._post("/api/v1/video/generate", json=body)

    def status(self, task_id: str, *, provider: Optional[str] = None) -> dict[str, Any]:
        """GET /api/v1/video/status/<task_id> -> ``{status, video_url, ...}``."""
        params = {"provider": provider} if provider else None
        return self._get(f"/api/v1/video/status/{task_id}", params=params)

    def wait(
        self,
        task_id: str,
        *,
        interval: float = 5.0,
        timeout: float = 900.0,
        on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """Poll video status until ``succeeded``/``failed`` -> payload with ``video_url``."""
        return _polling.wait(
            lambda: self.status(task_id),
            terminal_ok=_polling.MEDIA_OK,
            terminal_fail=_polling.MEDIA_FAIL,
            interval=interval,
            timeout=timeout,
            on_progress=on_progress,
        )

    def download(
        self, log_id: Union[int, str], dest: Optional[Union[str, os.PathLike]] = None
    ) -> Union[bytes, str]:
        """GET /api/v1/video/<log_id>/download -> MP4 bytes (or saved to ``dest``)."""
        return self._client.download(f"/api/v1/video/{log_id}/download", dest)
