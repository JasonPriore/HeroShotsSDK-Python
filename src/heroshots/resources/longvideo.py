"""Long / multi-segment video (API key or portal JWT, /api/v1/long-video)."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional, Union

from . import Resource, compact
from .. import _polling, _studiohero
from ..errors import ProviderError, ValidationError

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
        montage: Union[dict, bool, None] = None,
        voiceover_cast: Optional[Union[dict, list]] = None,
        **payload: Any,
    ) -> dict[str, Any]:
        """POST /api/v1/long-video/start -> ``{job_id, status, segment_count, ...}``.

        Provide ``image_url`` (local paths auto-upload with a portal JWT) or
        ``image_generation_id`` / ``product_image_url`` + ``subject_image_url``.
        ``duration_seconds`` is 30, 45 or 60.

        ``storyboard`` (from ``client.storyboard.wait`` / ``revise``) is turned into
        the fields the portal sends: ``custom_prompt`` = its ``optimized_prompt``,
        ``studiohero_segment_prompts``, ``studiohero_segment_reference_image_urls``
        and ``duration_seconds``. Explicit arguments win. The raw storyboard is not
        sent (the backend does not read it). For the whole portal render (inputs,
        reference images, voices, montage) use :meth:`start_from_storyboard`.

        ``montage`` asks the auto-edit after the export (graphics, karaoke
        captions, logo, end card): ``{"brief", "language_code", "logo_url",
        "logo_mode": "in_video"|"end_only"|"off", "inserts": [{"url", "label"}]}``.
        The edited video arrives in ``captioned_final_video_url``.

        ``voiceover_cast`` is one voice per speaking role (build it with
        ``client.storyboard.voice_cast``); ``tts_voice_id`` defaults to its first
        voice. Optional: ``reference_video_url``, ``script``, ``tts_voice_id``,
        ``language_code``, ``captions``.
        """
        body: dict[str, Any] = {"ratio": ratio, "resolution": resolution}
        if storyboard is not None:
            body.update(_studiohero.storyboard_start_fields(storyboard))
        body.update(payload)
        if image_url is not None:
            body["image_url"] = self._resolve_image(image_url, "products")
        body.update(compact({"custom_prompt": custom_prompt, "duration_seconds": duration_seconds}))
        if montage is not None and montage is not False:
            body["montage"] = montage
        if voiceover_cast:
            body["voiceover_cast"] = voiceover_cast
            voice = _studiohero.first_voice_id(voiceover_cast)
            if voice and not body.get("tts_voice_id"):
                body["tts_voice_id"] = voice
        return self._post("/api/v1/long-video/start", json=body)

    def start_from_storyboard(
        self,
        storyboard: dict,
        *,
        product_image_url: Optional[str] = None,
        subject_image_url: Optional[str] = None,
        image_url: Optional[str] = None,
        avatar_id: Optional[Union[int, str]] = None,
        avatar_view_type: Optional[str] = None,
        avatar_image_set: Optional[str] = None,
        additional_product_image_urls: Optional[list[str]] = None,
        product_box_closed_url: Optional[str] = None,
        product_box_open_url: Optional[str] = None,
        extra_products: Optional[list[dict]] = None,
        brand_logo_url: Optional[str] = None,
        brand_logo_mode: Optional[str] = None,
        background_image_url: Optional[str] = None,
        body_posture_image_url: Optional[str] = None,
        voice_id: Union[str, dict, None] = None,
        language_code: Optional[str] = None,
        montage: Union[dict, bool, None] = None,
        brief: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        ratio: str = "16:9",
        resolution: str = "1080p",
        **payload: Any,
    ) -> dict[str, Any]:
        """Start the long video exactly like the StudioHero portal's render.

        ``storyboard`` is the accepted storyboard (``storyboard.wait`` payload or
        the storyboard itself, after :meth:`Storyboard.merge` for frames / board).
        Builds: the inputs (product, subject or avatar + ``avatar_view_type``,
        extra product views, product boxes, ``extra_products``, brand logo),
        ``custom_prompt`` = ``optimized_prompt``, ``duration`` +
        ``duration_seconds``, ``ratio``, ``resolution``, the per-segment prompts and
        reference frames, ``reference_image_urls`` (board image, product, extra
        views, subject, background, posture), the voice cast and the montage.

        ``voice_id``: one voice for every speaking role, or ``{role_key: voice_id}``
        (keys from ``storyboard.voice_roles``; ids from ``client.audio.voices()``).
        A mapping must cover every speaking role. ``language_code`` is the spoken
        language (default ``"it"``, as the storyboard endpoints).

        ``montage``: ``True`` for the auto-edit with the defaults the portal uses
        (``brief``, ``language_code``, the brand logo and its mode), or a dict to
        set the fields yourself (missing ones are filled the same way). With no
        montage and ``brand_logo_mode="end_only"`` the animated logo closing is
        asked alone (``kind: "outro"``), like the portal.

        ``avatar_view_type`` must be a real view of the avatar (``fullbody``,
        ``mezzo_busto``, ``closeup``...): ``"avatar"`` is rejected. Extra keyword
        arguments are forwarded verbatim and win over everything.
        """
        sb = _studiohero.unwrap_storyboard(storyboard)
        if not sb.get("segments"):
            raise ValidationError("start_from_storyboard: the storyboard has no segments", code="validation_error")
        view = (avatar_view_type or "").strip() or None
        if view == "avatar":
            raise ValidationError(
                "avatar_view_type must be a view of the avatar (e.g. "
                + ", ".join(_studiohero.AVATAR_VIEW_TYPES[:5]) + "), not 'avatar'",
                code="validation_error",
            )
        if brand_logo_mode is not None and brand_logo_mode not in _studiohero.LOGO_MODES:
            raise ValidationError(
                "brand_logo_mode must be one of " + ", ".join(_studiohero.LOGO_MODES), code="validation_error"
            )

        product = self._resolve_image(product_image_url, "products")
        subject = self._resolve_image(subject_image_url, "subjects")
        extras = [self._resolve_image(u, "products") for u in additional_product_image_urls or [] if u]
        background = self._resolve_image(background_image_url, "background")
        posture = self._resolve_image(body_posture_image_url, "body_posture")
        logo = self._resolve_image(brand_logo_url, "references")
        logo_mode = brand_logo_mode or ("in_video" if logo else None)
        language = language_code or "it"
        duration = duration_seconds or sb.get("duration_seconds")
        fields = _studiohero.storyboard_start_fields(sb)

        body: dict[str, Any] = {}
        if image_url is not None:
            body["image_url"] = self._resolve_image(image_url, "products")
        body.update(compact({
            "product_image_url": product,
            "subject_image_url": subject,
            "avatar_id": avatar_id,
            "avatar_view_type": view if avatar_id is not None else None,
            "avatar_image_set": avatar_image_set if avatar_id is not None else None,
            "additional_product_image_urls": extras or None,
            "background_image_url": background,
            "body_posture_image_url": posture,
            "brand_logo_url": logo,
            "brand_logo_mode": logo_mode if logo else None,
            "product_box_closed_url": self._resolve_image(product_box_closed_url, "products"),
            "product_box_open_url": self._resolve_image(product_box_open_url, "products"),
            "extra_products": extra_products or None,
            "custom_prompt": fields.get("custom_prompt") or brief,
            "duration": duration,
            "duration_seconds": duration,
            "ratio": ratio,
            "resolution": resolution,
            "studiohero_segment_prompts": fields.get("studiohero_segment_prompts"),
            "studiohero_segment_reference_image_urls": fields.get("studiohero_segment_reference_image_urls"),
        }))
        refs = _studiohero.dedupe_urls(
            [sb.get("storyboard_board_image_url"), product, *extras, subject, background, posture]
        )
        if refs:
            body["reference_image_urls"] = refs

        if voice_id:
            missing = _studiohero.missing_voice_roles(sb, voice_id)
            if missing:
                raise ValidationError(
                    "voice_id has no voice for the speaking role(s): " + ", ".join(missing),
                    code="validation_error",
                )
            cast = _studiohero.voice_cast(sb, voice_id)
            if cast:
                body["voiceover_cast"] = cast
                body["tts_voice_id"] = _studiohero.first_voice_id(cast)
                body["language_code"] = language

        montage_body = _montage_request(
            montage, brief=brief, language_code=language, logo_url=logo, logo_mode=logo_mode
        )
        if montage_body is not None:
            body["montage"] = montage_body

        body.update(payload)
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

    def montage(
        self,
        job_id: Union[int, str],
        *,
        brief: Optional[str] = None,
        language_code: Optional[str] = None,
        logo_url: Optional[str] = None,
        logo_mode: Optional[str] = None,
        inserts: Optional[list[dict]] = None,
        **fields: Any,
    ) -> dict[str, Any]:
        """POST /api/auth/long-video/<job_id>/montage -> auto-edit a generated video (portal JWT).

        Graphics, karaoke captions, logo and end card on the exported video; the
        result lands in ``captioned_final_video_url`` (``final_video_url`` stays the
        plain cut). Omitted fields take the job's defaults. Returns the job status:
        HTTP 202 when it starts now (status ``captioning``), or ``needs_export: true``
        when the video is not exported yet (the next :meth:`export` runs it).
        Follow it with :meth:`render` (or :meth:`wait`) until ``montage_done``.
        """
        body = compact({
            "brief": brief,
            "language_code": language_code,
            "logo_url": logo_url,
            "logo_mode": logo_mode,
            "inserts": inserts,
            **fields,
        })
        return self._post(f"/api/auth/long-video/{job_id}/montage", json=body)

    def montage_available(self) -> bool:
        """GET /api/auth/studio/montage-availability -> can this server run the auto-edit?"""
        resp = self._get("/api/auth/studio/montage-availability")
        return bool(resp.get("available")) if isinstance(resp, dict) else False

    @staticmethod
    def montage_settled(job: dict[str, Any]) -> bool:
        """True when no auto-edit is asked, it is done, or it stopped (failed / expired)."""
        return montage_settled(job)

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
        When an auto-edit was asked (``montage_requested``), a ``done`` job is
        returned only once the montage has finished (see :func:`montage_settled`).
        """
        return _polling.wait(
            lambda: self.status(job_id),
            terminal_ok=WAIT_OK,
            terminal_fail=_polling.STORYBOARD_FAIL,
            interval=interval,
            timeout=timeout,
            on_progress=on_progress,
            ready=_done_and_settled_or_not_done,
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

        Returns the final status payload (``status == "done"``). With an auto-edit
        asked (``montage=`` at start, or :meth:`montage`) it also waits for it
        (status ``done`` -> ``captioning`` -> ``done``): the edited video is
        ``captioned_final_video_url`` and ``montage_done`` is true. A failed
        auto-edit returns with ``montage_done`` false, ``montage_report.error`` and
        the plain ``final_video_url``.
        """
        deadline = time.monotonic() + timeout
        job = self.wait(job_id, interval=interval, timeout=timeout, on_progress=on_progress)
        if str(job.get("status")).lower() == "done" and job.get("final_video_url") and montage_settled(job):
            return job
        self.export(job_id, segment_order=segment_order)
        while True:
            job = self.status(job_id)
            if on_progress is not None:
                on_progress(job)
            status = str(job.get("status") or "").lower()
            if status == "done" and job.get("final_video_url") and montage_settled(job):
                return job
            if status in _polling.STORYBOARD_FAIL:
                raise ProviderError(job.get("error") or f"long video {status}", code="provider_error")
            if time.monotonic() >= deadline:
                raise _polling.TimeoutError(
                    f"long video export did not finish within {timeout:.0f}s (last status={status!r})"
                )
            time.sleep(interval)


def montage_settled(job: dict[str, Any]) -> bool:
    """True when no auto-edit is asked, it is done, or it stopped (failed / expired)."""
    if not job.get("montage_requested"):
        return True
    if job.get("montage_done"):
        return True
    return not job.get("montage_pending")


def _done_and_settled_or_not_done(job: dict[str, Any]) -> bool:
    if str(job.get("status") or "").lower() != "done":
        return True
    return montage_settled(job)


def _montage_request(
    montage: Union[dict, bool, None],
    *,
    brief: Optional[str],
    language_code: Optional[str],
    logo_url: Optional[str],
    logo_mode: Optional[str],
) -> Optional[dict[str, Any]]:
    """The ``montage`` field as the portal builds it (None when nothing is asked)."""
    portal_logo = logo_url if logo_url and logo_mode != "off" else None
    if montage is None or montage is False:
        if portal_logo and logo_mode == "end_only":
            return compact({"kind": "outro", "language_code": language_code,
                            "logo_url": portal_logo, "logo_mode": logo_mode})
        return None
    asked = dict(montage) if isinstance(montage, dict) else {}
    defaults = compact({
        "brief": (brief or "").strip(),
        "language_code": language_code,
        "logo_url": portal_logo,
        "logo_mode": logo_mode,
    })
    for key, value in defaults.items():
        asked.setdefault(key, value)
    return asked
