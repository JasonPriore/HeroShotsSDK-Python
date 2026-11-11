"""Long / multi-segment video (API key or portal JWT, /api/v1/long-video)."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional, Union

from . import Resource, compact
from .. import _polling
from ..errors import ProviderError

# The job pauses here when every segment is rendered: the clips are ready
# (``segments[].video_url``) and the final cut is made by ``export()``.
SEGMENTS_READY = "segments_ready"
WAIT_OK = _polling.STORYBOARD_OK + (SEGMENTS_READY,)


class LongVideo(Resource):
    def start(
        self,
        image_url: Optional[str] = None,
        *,
        custom_prompt: Optional[str] = None,
        storyboard: Optional[dict] = None,
        duration_seconds: Optional[int] = None,
        ratio: str = "16:9",
        resolution: str = "1080p",
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /api/v1/long-video/start -> ``{job_id, status, segment_count, ...}``.

        Provide ``image_url`` (local paths auto-upload with a portal JWT) or
        ``image_generation_id`` / ``product_image_url`` + ``subject_image_url``.
        ``duration_seconds`` is 30, 45 or 60. Pass a ``storyboard`` produced by
        ``client.storyboard`` to drive a planned multi-segment render. Optional:
        ``reference_video_url``, ``script``, ``tts_voice_id``, ``language_code``.
        """
        body: dict[str, Any] = {"ratio": ratio, "resolution": resolution, **payload}
        if image_url is not None:
            body["image_url"] = self._resolve_image(image_url, "products")
        body.update(
            compact(
                {
                    "custom_prompt": custom_prompt,
                    "storyboard": storyboard,
                    "duration_seconds": duration_seconds,
                }
            )
        )
        return self._post("/api/v1/long-video/start", json=body)

    def status(self, job_id: Union[int, str]) -> dict[str, Any]:
        """GET /api/v1/long-video/status/<job_id> -> segments + ``final_video_url``."""
        return self._get(f"/api/v1/long-video/status/{job_id}")

    def regenerate_segment(
        self,
        job_id: Union[int, str],
        segment_index: int,
        *,
        comment: Optional[str] = None,
        cascade: Optional[bool] = None,
    ) -> dict[str, Any]:
        """POST /api/v1/long-video/<job_id>/segments/<i>/regenerate.

        ``comment`` tells the model what to change; ``cascade=True`` also
        re-renders the following segments so they stay continuous.
        """
        body = compact({"comment": comment, "cascade": cascade})
        return self._post(
            f"/api/v1/long-video/{job_id}/segments/{segment_index}/regenerate", json=body
        )

    def export(
        self,
        job_id: Union[int, str],
        *,
        segment_order: Optional[list[int]] = None,
        timeline: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """POST /api/auth/long-video/<job_id>/export -> joins the clips into ``final_video_url``.

        Portal JWT only. Needs every segment done (status ``segments_ready`` or
        ``done``). ``segment_order`` (1-based indexes) reorders the clips. Not billed.
        """
        body = compact({"segment_order": segment_order, "timeline": timeline})
        return self._post(f"/api/auth/long-video/{job_id}/export", json=body)

    def view(self, token: str) -> dict[str, Any]:
        """GET /api/auth/long-video/view/<token> (share link payload, portal JWT)."""
        return self._get(f"/api/auth/long-video/view/{token}")

    def wait(
        self,
        job_id: Union[int, str],
        *,
        interval: float = 5.0,
        timeout: float = 1800.0,
        on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """Poll until the clips are ready (``segments_ready``), ``done`` or ``failed``.

        At ``segments_ready`` every ``segments[i].video_url`` is set but
        ``final_video_url`` is still empty: call :meth:`export` (or use
        :meth:`render`) to get the joined video. Dubbed jobs go straight to ``done``.
        """
        return _polling.wait(
            lambda: self.status(job_id),
            terminal_ok=WAIT_OK,
            terminal_fail=_polling.STORYBOARD_FAIL,
            interval=interval,
            timeout=timeout,
            on_progress=on_progress,
        )

    def render(
        self,
        job_id: Union[int, str],
        *,
        segment_order: Optional[list[int]] = None,
        interval: float = 5.0,
        timeout: float = 2400.0,
        on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """Wait for the clips, export them and wait for ``final_video_url`` (portal JWT).

        Returns the final status payload (``status == "done"``).
        """
        deadline = time.monotonic() + timeout
        job = self.wait(job_id, interval=interval, timeout=timeout, on_progress=on_progress)
        if str(job.get("status")).lower() == "done" and job.get("final_video_url"):
            return job
        self.export(job_id, segment_order=segment_order)
        while True:
            job = self.status(job_id)
            if on_progress is not None:
                on_progress(job)
            status = str(job.get("status") or "").lower()
            if status == "done" and job.get("final_video_url"):
                return job
            if status in _polling.STORYBOARD_FAIL:
                raise ProviderError(job.get("error") or f"long video {status}", code="provider_error")
            if time.monotonic() >= deadline:
                raise _polling.TimeoutError(
                    f"long video export did not finish within {timeout:.0f}s (last status={status!r})"
                )
            time.sleep(interval)
