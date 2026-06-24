"""Still-life product video (portal JWT, /api/auth/stilllife-video)."""

from __future__ import annotations

from typing import Any, Callable, Optional

from . import Resource
from .. import _polling


class StillLife(Resource):
    def start(
        self,
        product_url: str,
        background_url: str,
        *,
        custom_prompt: Optional[str] = None,
        ratio: str = "16:9",
        resolution: str = "1080p",
        duration_seconds: int = 5,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /api/auth/stilllife-video/start -> ``{task_id, status, ...}``.

        ``product_url`` and ``background_url`` are required (local paths auto-upload).
        """
        body: dict[str, Any] = {
            "product_url": self._resolve_image(product_url, "products"),
            "background_url": self._resolve_image(background_url, "background"),
            "ratio": ratio,
            "resolution": resolution,
            "duration_seconds": duration_seconds,
            **payload,
        }
        if custom_prompt is not None:
            body["custom_prompt"] = custom_prompt
        return self._post("/api/auth/stilllife-video/start", json=body)

    def status(self, task_id: str) -> dict[str, Any]:
        """GET /api/auth/stilllife-video/status/<task_id>."""
        return self._get(f"/api/auth/stilllife-video/status/{task_id}")

    def wait(
        self,
        task_id: str,
        *,
        interval: float = 5.0,
        timeout: float = 900.0,
        on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """Poll until terminal -> payload with the finished video URL."""
        return _polling.wait(
            lambda: self.status(task_id),
            terminal_ok=_polling.MEDIA_OK,
            terminal_fail=_polling.MEDIA_FAIL,
            interval=interval,
            timeout=timeout,
            on_progress=on_progress,
        )

    def preview_background(self, task_id: str, **payload: Any) -> dict[str, Any]:
        """POST /api/auth/stilllife-video/<task_id>/preview-background."""
        return self._post(f"/api/auth/stilllife-video/{task_id}/preview-background", json=payload)

    def change_background(self, task_id: str, **payload: Any) -> dict[str, Any]:
        """POST /api/auth/stilllife-video/<task_id>/change-background."""
        return self._post(f"/api/auth/stilllife-video/{task_id}/change-background", json=payload)

    def change_background_status(self, task_id: str) -> dict[str, Any]:
        """GET /api/auth/stilllife-video/<task_id>/change-background/status."""
        return self._get(f"/api/auth/stilllife-video/{task_id}/change-background/status")
