"""Long / multi-segment video pipeline (portal JWT, /api/auth/long-video)."""

from __future__ import annotations

from typing import Any, Callable, Optional

from . import Resource
from .. import _polling


class LongVideo(Resource):
    def start(
        self,
        image_url: Optional[str] = None,
        *,
        custom_prompt: Optional[str] = None,
        storyboard: Optional[dict] = None,
        ratio: str = "16:9",
        resolution: str = "1080p",
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /api/auth/long-video/start -> ``{job_id, status, segment_count, ...}``.

        Provide ``image_url`` (local paths auto-upload) or ``image_generation_id`` /
        ``product_image_url`` + ``subject_image_url``. Pass a ``storyboard`` produced
        by ``client.storyboard`` to drive a planned multi-segment render.
        """
        body: dict[str, Any] = {"ratio": ratio, "resolution": resolution, **payload}
        if image_url is not None:
            body["image_url"] = self._resolve_image(image_url, "products")
        if custom_prompt is not None:
            body["custom_prompt"] = custom_prompt
        if storyboard is not None:
            body["storyboard"] = storyboard
        return self._post("/api/auth/long-video/start", json=body)

    def status(self, job_id: int) -> dict[str, Any]:
        """GET /api/auth/long-video/status/<job_id>."""
        return self._get(f"/api/auth/long-video/status/{job_id}")

    def view(self, token: str) -> dict[str, Any]:
        """GET /api/auth/long-video/view/<token>."""
        return self._get(f"/api/auth/long-video/view/{token}")

    def wait(
        self,
        job_id: int,
        *,
        interval: float = 5.0,
        timeout: float = 1800.0,
        on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """Poll until ``done``/``failed`` -> payload with ``final_video_url``."""
        return _polling.wait(
            lambda: self.status(job_id),
            terminal_ok=_polling.STORYBOARD_OK,
            terminal_fail=_polling.STORYBOARD_FAIL,
            interval=interval,
            timeout=timeout,
            on_progress=on_progress,
        )
