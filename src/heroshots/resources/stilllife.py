"""Still-life product video (API key or portal JWT, /api/v1/stilllife-video)."""

from __future__ import annotations

from typing import Any, Callable, Optional, Union

from . import Resource, compact
from .. import _polling


class StillLife(Resource):
    def start(
        self,
        product_url: str,
        background_url: str,
        *,
        custom_prompt: Optional[str] = None,
        detail_image_url: Optional[str] = None,
        reference_video_url: Optional[str] = None,
        ratio: str = "16:9",
        resolution: str = "1080p",
        duration_seconds: int = 5,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /api/v1/stilllife-video/start -> ``{task_id, status, ...}``.

        ``product_url`` and ``background_url`` are required (local paths
        auto-upload with a portal JWT).
        """
        body: dict[str, Any] = {
            "product_url": self._resolve_image(product_url, "products"),
            "background_url": self._resolve_image(background_url, "background"),
            "ratio": ratio,
            "resolution": resolution,
            "duration_seconds": duration_seconds,
            **payload,
        }
        body.update(
            compact(
                {
                    "custom_prompt": custom_prompt,
                    "detail_image_url": self._resolve_image(detail_image_url, "products"),
                    "reference_video_url": reference_video_url,
                }
            )
        )
        return self._post("/api/v1/stilllife-video/start", json=body)

    def status(self, task_id: Union[int, str]) -> dict[str, Any]:
        """GET /api/v1/stilllife-video/status/<task_id>."""
        return self._get(f"/api/v1/stilllife-video/status/{task_id}")

    def wait(
        self,
        task_id: Union[int, str],
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

    # -- background edits (portal JWT only) ------------------------------------
    def preview_background(self, task_id: Union[int, str], **payload: Any) -> dict[str, Any]:
        """POST /api/auth/stilllife-video/<task_id>/preview-background (portal JWT)."""
        return self._post(f"/api/auth/stilllife-video/{task_id}/preview-background", json=payload)

    def change_background(self, task_id: Union[int, str], **payload: Any) -> dict[str, Any]:
        """POST /api/auth/stilllife-video/<task_id>/change-background (portal JWT)."""
        return self._post(f"/api/auth/stilllife-video/{task_id}/change-background", json=payload)

    def change_background_status(self, task_id: Union[int, str]) -> dict[str, Any]:
        """GET /api/auth/stilllife-video/<task_id>/change-background/status (portal JWT)."""
        return self._get(f"/api/auth/stilllife-video/{task_id}/change-background/status")
