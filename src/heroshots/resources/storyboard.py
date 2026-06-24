"""StudioHero storyboard intelligence (portal JWT only).

This is the creative brain the web app uses: brief suggestions -> selectable
candidates -> full storyboard (async) -> deferred 4K reference frames (async) ->
optional revision. Feed the resulting storyboard into ``client.longvideo.start``.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from . import Resource
from .. import _polling

# Valid durations accepted by the backend storyboard endpoints.
DURATIONS = (6, 8, 12, 15, 30, 45, 60)


class Storyboard(Resource):
    def brief_suggestions(
        self,
        product_image_url: Optional[str] = None,
        subject_image_url: Optional[str] = None,
        **payload: Any,
    ) -> list[str]:
        """POST /video/storyboard/brief-suggestions -> list of short brief strings."""
        body = self._image_body(product_image_url, subject_image_url, payload)
        resp = self._post("/video/storyboard/brief-suggestions", json=body)
        return resp.get("suggestions", resp) if isinstance(resp, dict) else resp

    def candidates(
        self,
        custom_prompt: str,
        duration_seconds: int,
        product_image_url: Optional[str] = None,
        subject_image_url: Optional[str] = None,
        *,
        async_storyboard: bool = False,
        **payload: Any,
    ) -> Any:
        """POST /video/storyboard/candidates -> selectable concept candidates.

        Set ``async_storyboard=True`` to get a ``{job_id}`` instead (poll with
        :meth:`wait`); otherwise returns the candidates inline.
        """
        body = self._image_body(product_image_url, subject_image_url, payload)
        body.update(custom_prompt=custom_prompt, duration_seconds=duration_seconds)
        if async_storyboard:
            body["async_storyboard"] = True
        resp = self._post("/video/storyboard/candidates", json=body)
        if isinstance(resp, dict) and "candidates" in resp:
            return resp["candidates"]
        return resp

    def generate(
        self,
        custom_prompt: str,
        duration_seconds: int,
        selected_candidate: Optional[dict] = None,
        product_image_url: Optional[str] = None,
        subject_image_url: Optional[str] = None,
        *,
        async_storyboard: bool = True,
        defer_reference_frames: bool = True,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /video/storyboard -> storyboard (async by default -> ``{job_id}``)."""
        body = self._image_body(product_image_url, subject_image_url, payload)
        body.update(
            custom_prompt=custom_prompt,
            duration_seconds=duration_seconds,
            async_storyboard=async_storyboard,
            defer_reference_frames=defer_reference_frames,
        )
        if selected_candidate is not None:
            body["selected_candidate"] = selected_candidate
        return self._post("/video/storyboard", json=body)

    def frames(
        self,
        storyboard: dict,
        product_image_url: Optional[str] = None,
        subject_image_url: Optional[str] = None,
        *,
        async_storyboard: bool = True,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /video/storyboard/frames -> renders deferred 4K reference frames."""
        body = self._image_body(product_image_url, subject_image_url, payload)
        body.update(storyboard=storyboard, async_storyboard=async_storyboard)
        return self._post("/video/storyboard/frames", json=body)

    def revise(self, revision_request: str, custom_prompt: str, duration_seconds: int,
               storyboard: dict, **payload: Any) -> dict[str, Any]:
        """POST /video/storyboard/revise -> revised storyboard."""
        body = {
            "revision_request": revision_request,
            "custom_prompt": custom_prompt,
            "duration_seconds": duration_seconds,
            "storyboard": storyboard,
            **payload,
        }
        return self._post("/video/storyboard/revise", json=body)

    def status(self, job_id: str) -> dict[str, Any]:
        """GET /video/storyboard/status/<job_id>."""
        return self._get(f"/video/storyboard/status/{job_id}")

    def wait(
        self,
        job_id: str,
        *,
        interval: float = 3.0,
        timeout: float = 300.0,
        on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """Poll a storyboard/frames job until ``done``/``failed``.

        ``on_progress`` receives each status payload (storyboard frame jobs expose
        ``frames_partial`` for progressive rendering).
        """
        return _polling.wait(
            lambda: self.status(job_id),
            terminal_ok=_polling.STORYBOARD_OK,
            terminal_fail=_polling.STORYBOARD_FAIL,
            interval=interval,
            timeout=timeout,
            on_progress=on_progress,
        )

    # -- creative helpers -----------------------------------------------------
    def subject_measurements(self, **payload: Any) -> dict[str, Any]:
        """POST /subject/estimate-measurements."""
        return self._post("/subject/estimate-measurements", json=payload)

    def analyze_product(self, **payload: Any) -> dict[str, Any]:
        """POST /product/analyze."""
        return self._post("/product/analyze", json=payload)

    def creativity(self, **payload: Any) -> dict[str, Any]:
        """POST /creativity/generate."""
        return self._post("/creativity/generate", json=payload)

    # -- internal -------------------------------------------------------------
    def _image_body(
        self,
        product_image_url: Optional[str],
        subject_image_url: Optional[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        body = dict(payload)
        if product_image_url is not None:
            body["product_image_url"] = self._resolve_image(product_image_url, "products")
        if subject_image_url is not None:
            body["subject_image_url"] = self._resolve_image(subject_image_url, "subjects")
        if "image_url" in body:
            body["image_url"] = self._resolve_image(body["image_url"], "references")
        return body
