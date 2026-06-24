"""Short video generation (JWT-or-API-key on /api/v1; portal status poll)."""

from __future__ import annotations

from typing import Any, Callable, Optional

from . import Resource
from .. import _polling


class Videos(Resource):
    def generate(self, image_url: Optional[str] = None, **payload: Any) -> dict[str, Any]:
        """POST /api/v1/video/generate -> ``{task_id, status, ...}``.

        Local file paths in ``image_url`` are auto-uploaded.
        """
        body = dict(payload)
        if image_url is not None:
            body["image_url"] = self._resolve_image(image_url, "products")
        return self._post("/api/v1/video/generate", json=body)

    def status(self, task_id: str) -> dict[str, Any]:
        """GET /video/status/<task_id> (portal JWT) -> ``{task_id, status, video_url}``."""
        return self._get(f"/video/status/{task_id}")

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
