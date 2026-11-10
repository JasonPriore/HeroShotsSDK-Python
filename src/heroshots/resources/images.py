"""Image generation (API key or portal JWT on /api/v1; candidates flow)."""

from __future__ import annotations

import os
from typing import Any, Callable, Optional, Union

from . import Resource, compact
from .. import _polling

_IMAGE_URL_FIELDS = (
    ("background_image_url", "background"),
    ("body_posture_image_url", "body_posture"),
    ("hairstyle_reference_image_url", "references"),
    ("text_detail_image_url", "products"),
    ("worn_scale_reference_url", "references"),
)


class Images(Resource):
    def generate(
        self,
        product_image_url: str,
        subject_image_url: Optional[str] = None,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /api/v1/image/generate (async) -> ``{generation_id, status, ...}``.

        Provide ``subject_image_url`` or ``avatar_id`` (``avatar_image_set``:
        ``original`` | ``generated``) unless ``still_life=True``. Other fields:
        ``custom_prompt``, ``size`` (720p | 1080p | 2K | 4K), ``aspect_ratio``,
        ``view_type``, ``background_image_url``, ``additional_product_image_urls``,
        ``quality_mode``, ``text_fidelity_mode``. To edit an earlier image pass
        ``edit_generation_id`` or ``previous_output_image_url``.
        Local file paths are auto-uploaded (portal JWT only).
        """
        body = self._image_body(product_image_url, subject_image_url, payload)
        return self._post("/api/v1/image/generate", json=body)

    def generate_background(
        self,
        prompt: str,
        *,
        aspect_ratio: Optional[str] = None,
        size: Optional[str] = None,
        async_generation: Optional[bool] = None,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /api/v1/background/generate -> AI background image (``size``: 2K | 4K)."""
        body = compact(
            {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "size": size,
                "async_generation": async_generation,
                **payload,
            }
        )
        return self._post("/api/v1/background/generate", json=body)

    def candidates(
        self,
        product_image_url: str,
        subject_image_url: Optional[str] = None,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /api/auth/image/generate/candidates -> persistent candidate batch."""
        body = self._image_body(product_image_url, subject_image_url, payload)
        return self._post("/api/auth/image/generate/candidates", json=body)

    def select_candidate(self, token: str, **payload: Any) -> dict[str, Any]:
        """POST /api/auth/image/generate/candidates/<token>/select (portal JWT)."""
        return self._post(f"/api/auth/image/generate/candidates/{token}/select", json=payload)

    def status(self, generation_id: str) -> dict[str, Any]:
        """GET /api/v1/image/status/<generation_id>."""
        return self._get(f"/api/v1/image/status/{generation_id}")

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

    def download(
        self, log_id: Union[int, str], dest: Optional[Union[str, os.PathLike]] = None
    ) -> Union[bytes, str]:
        """GET /api/v1/image/<log_id>/download -> image bytes (or saved to ``dest``).

        Same watermark and resolution as at generation time.
        """
        return self._client.download(f"/api/v1/image/{log_id}/download", dest)

    # -- usage rights -----------------------------------------------------------
    def usage_rights_quote(
        self,
        log_id: Union[int, str],
        usage_rights: Optional[list[dict[str, Any]]] = None,
        *,
        usage_rights_type: Optional[str] = None,
        usage_rights_duration: Optional[str] = None,
    ) -> dict[str, Any]:
        """Quote a usage-rights upgrade for an image -> ``{delta_eur, new_total_eur, ...}``.

        Pass a ``usage_rights`` list (POST body) or a single
        ``usage_rights_type`` (organic | paid_digital | broadcast) +
        ``usage_rights_duration`` (4_weeks | 6_months | 2_years | perpetual).
        """
        path = f"/api/v1/image/{log_id}/usage-rights/quote"
        if usage_rights is not None:
            return self._post(path, json={"usage_rights": usage_rights})
        params = compact(
            {"usage_rights_type": usage_rights_type, "usage_rights_duration": usage_rights_duration}
        )
        return self._get(path, params=params or None)

    def usage_rights_upgrade(
        self, log_id: Union[int, str], usage_rights: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """POST /api/v1/image/<log_id>/usage-rights/upgrade -> charges the difference."""
        return self._post(
            f"/api/v1/image/{log_id}/usage-rights/upgrade", json={"usage_rights": usage_rights}
        )

    def analyze_edit_region(self, crop_image: str, feedback: str) -> dict[str, Any]:
        """POST /api/v1/image/analyze-edit-region -> ``{edit_prompt}`` for a cropped area.

        ``crop_image`` is a data URI or URL of the area to change; ``feedback`` is
        what should change there.
        """
        return self._post(
            "/api/v1/image/analyze-edit-region",
            json={"crop_image": crop_image, "feedback": feedback},
        )

    # -- internal -------------------------------------------------------------
    def _image_body(
        self,
        product_image_url: str,
        subject_image_url: Optional[str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        body = {
            **payload,
            "product_image_url": self._resolve_image(product_image_url, "products"),
        }
        if subject_image_url is not None:
            body["subject_image_url"] = self._resolve_image(subject_image_url, "subjects")
        for key, folder in _IMAGE_URL_FIELDS:
            if key in body:
                body[key] = self._resolve_image(body[key], folder)
        extra = body.get("additional_product_image_urls")
        if isinstance(extra, list):
            body["additional_product_image_urls"] = [
                self._resolve_image(u, "products") for u in extra
            ]
        return body
